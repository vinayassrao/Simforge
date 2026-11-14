"""Episode lifecycle: create, control, persist and query simulation runs."""

from __future__ import annotations

import csv
import io
import logging
import threading
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy import delete, func, select

from app.database import Database
from app.evaluation import evaluate_episode
from app.models import EpisodeRecord, EvaluationRecord, EventRecord
from app.models.records import utc_now
from app.services.gateway import SimulationGateway
from app.services.serializers import episode_to_dict, event_to_dict
from simulation.scenarios import get_scenario, list_scenarios
from simulation.types import AgentMode, EpisodeStatus

logger = logging.getLogger(__name__)

Publisher = Callable[[str | None, dict[str, Any]], None]
FINISHED = {status.value for status in EpisodeStatus if status.is_finished}
EVENT_CSV_COLUMNS = ("seq", "step", "timestamp", "category", "type", "description", "entity_id")


class EpisodeNotFoundError(LookupError):
    def __init__(self, episode_id: str) -> None:
        super().__init__(f"Episode '{episode_id}' does not exist.")
        self.episode_id = episode_id


class EpisodeService:
    def __init__(self, database: Database, gateway: SimulationGateway, publish: Publisher) -> None:
        self._db = database
        self._gateway = gateway
        self._publish = publish
        self._create_lock = threading.Lock()
        self.active_episode_id: str | None = None

    def startup(self) -> None:
        """Close episodes left open by a previous server run and start listening."""
        with self._db.session() as session:
            stale = session.scalars(select(EpisodeRecord).where(EpisodeRecord.status.not_in(FINISHED))).all()
            for record in stale:
                self._mark_aborted(record)
        self._gateway.subscribe(self.handle_output)

    # -- commands ------------------------------------------------------------

    def create(self, scenario_id: str, agent_mode: AgentMode, seed: int | None) -> dict[str, Any]:
        scenario = get_scenario(scenario_id)
        resolved_seed = scenario.default_seed if seed is None else seed
        with self._create_lock:
            self._abort_active()
            episode_id = f"ep-{uuid.uuid4().hex[:8]}"
            with self._db.session() as session:
                session.add(
                    EpisodeRecord(
                        id=episode_id,
                        scenario_id=scenario.id,
                        scenario_name=scenario.name,
                        agent_mode=agent_mode.value,
                        seed=resolved_seed,
                    )
                )
            self.active_episode_id = episode_id
            self._gateway.request(
                {
                    "type": "load",
                    "episode_id": episode_id,
                    "scenario_id": scenario.id,
                    "agent_mode": agent_mode.value,
                    "seed": resolved_seed,
                }
            )
        return self.get(episode_id)

    def command(self, episode_id: str, command_type: str, **params: Any) -> dict[str, Any]:
        """Send a control command or an action to the live episode."""
        self._require(episode_id)
        return self._gateway.request({"type": command_type, "episode_id": episode_id, **params})

    def reset(self, episode_id: str) -> dict[str, Any]:
        """Restart the episode from its seed. Its earlier events and evaluation are discarded."""
        self._require(episode_id)
        with self._db.session() as session:
            session.execute(delete(EventRecord).where(EventRecord.episode_id == episode_id))
            session.execute(delete(EvaluationRecord).where(EvaluationRecord.episode_id == episode_id))
            record = session.get(EpisodeRecord, episode_id)
            if record is not None:
                record.status = EpisodeStatus.CREATED.value
                record.started_at = record.finished_at = None
                record.score = record.success = record.failure_reason = None
                record.trajectory, record.incidents = [], []
        return self._gateway.request({"type": "reset", "episode_id": episode_id})

    def live_state(self, episode_id: str) -> dict[str, Any] | None:
        """The current snapshot if this episode is loaded in the simulation."""
        if episode_id != self.active_episode_id:
            return None
        state = self._gateway.request({"type": "snapshot"})
        return state if state.get("episode_id") == episode_id else None

    def _abort_active(self) -> None:
        if self.active_episode_id is None:
            return
        with self._db.session() as session:
            record = session.get(EpisodeRecord, self.active_episode_id)
            if record is not None and record.status not in FINISHED:
                self._mark_aborted(record)
                self._publish(record.id, {"type": "status", "status": record.status})
        self.active_episode_id = None

    @staticmethod
    def _mark_aborted(record: EpisodeRecord) -> None:
        record.status = EpisodeStatus.ABORTED.value
        record.finished_at = utc_now()
        record.failure_reason = "aborted"

    # -- simulation output -----------------------------------------------------

    def handle_output(self, message: dict[str, Any]) -> None:
        """Persist and broadcast one message from the simulation. Runs on the pump thread."""
        kind = message["type"]
        if kind == "perf":
            self._publish(None, message)
            return
        episode_id = message["episode_id"]
        if kind == "events":
            self._store_events(episode_id, message["events"])
        elif kind == "state":
            self._store_state(episode_id, message["state"])
        elif kind == "finished":
            message = {"type": "finished", "evaluation": self._store_result(episode_id, message["summary"])}
        self._publish(episode_id, message)

    def _store_events(self, episode_id: str, events: list[dict[str, Any]]) -> None:
        with self._db.session() as session:
            if session.get(EpisodeRecord, episode_id) is None:
                return
            session.add_all(
                EventRecord(
                    episode_id=episode_id,
                    seq=event["seq"],
                    step=event["step"],
                    type=event["type"],
                    category=event["category"],
                    description=event["description"],
                    entity_id=event["entity_id"],
                    data=event["data"],
                    timestamp=event["timestamp"],
                )
                for event in events
            )

    def _store_state(self, episode_id: str, state: dict[str, Any]) -> None:
        metrics = state["metrics"]
        with self._db.session() as session:
            record = session.get(EpisodeRecord, episode_id)
            if record is None or record.status == EpisodeStatus.ABORTED.value:
                return
            record.status = state["status"]
            record.steps = metrics["steps"]
            record.progress = metrics["progress"]
            record.collisions = metrics["collisions"] + metrics["restricted_entries"]
            record.invalid_actions = metrics["invalid_actions"]
            record.elapsed_seconds = metrics["elapsed_seconds"]
            if record.started_at is None and state["status"] != EpisodeStatus.CREATED.value:
                record.started_at = utc_now()

    def _store_result(self, episode_id: str, summary: dict[str, Any]) -> dict[str, Any]:
        report = evaluate_episode(summary)
        with self._db.session() as session:
            record = session.get(EpisodeRecord, episode_id)
            if record is None:
                return report
            record.finished_at = utc_now()
            record.score = report["score"]
            record.success = report["success"]
            record.failure_reason = report["failure_reason"]
            record.trajectory = summary["trajectory"]
            record.incidents = summary["incident_locations"]
            session.merge(
                EvaluationRecord(episode_id=episode_id, score=report["score"], success=report["success"], report=report)
            )
        logger.info("Episode %s finished: score %.1f, success=%s", episode_id, report["score"], report["success"])
        return report

    # -- queries -------------------------------------------------------------

    def _require(self, episode_id: str) -> None:
        with self._db.session() as session:
            if session.get(EpisodeRecord, episode_id) is None:
                raise EpisodeNotFoundError(episode_id)

    def get(self, episode_id: str) -> dict[str, Any]:
        with self._db.session() as session:
            record = session.get(EpisodeRecord, episode_id)
            if record is None:
                raise EpisodeNotFoundError(episode_id)
            payload = episode_to_dict(record)
            payload["is_active"] = episode_id == self.active_episode_id
            payload["trajectory"] = record.trajectory
            payload["incidents"] = record.incidents
            return payload

    def list(
        self,
        scenario_id: str | None = None,
        agent_mode: str | None = None,
        status: str | None = None,
        min_score: float | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        query = select(EpisodeRecord).order_by(EpisodeRecord.created_at.desc()).limit(limit)
        if scenario_id:
            query = query.where(EpisodeRecord.scenario_id == scenario_id)
        if agent_mode:
            query = query.where(EpisodeRecord.agent_mode == agent_mode)
        if status:
            query = query.where(EpisodeRecord.status == status)
        if min_score is not None:
            query = query.where(EpisodeRecord.score >= min_score)
        with self._db.session() as session:
            return [episode_to_dict(record) for record in session.scalars(query)]

    def events(
        self, episode_id: str, category: str | None = None, after_seq: int = 0, limit: int = 2000
    ) -> list[dict[str, Any]]:
        self._require(episode_id)
        query = (
            select(EventRecord)
            .where(EventRecord.episode_id == episode_id, EventRecord.seq > after_seq)
            .order_by(EventRecord.seq)
            .limit(limit)
        )
        if category:
            query = query.where(EventRecord.category == category)
        with self._db.session() as session:
            return [event_to_dict(record) for record in session.scalars(query)]

    def evaluation(self, episode_id: str) -> dict[str, Any] | None:
        self._require(episode_id)
        with self._db.session() as session:
            record = session.get(EvaluationRecord, episode_id)
            return record.report if record else None

    def evaluations(self) -> dict[str, Any]:
        """Every evaluated episode plus aggregate figures for the evaluations dashboard."""
        with self._db.session() as session:
            rows = session.execute(
                select(EpisodeRecord, EvaluationRecord)
                .join(EvaluationRecord, EvaluationRecord.episode_id == EpisodeRecord.id)
                .order_by(EpisodeRecord.created_at)
            ).all()
            items = []
            for episode, evaluation in rows:
                item = episode_to_dict(episode)
                item["metrics"] = evaluation.report["metrics"]
                item["breakdown"] = evaluation.report["breakdown"]
                items.append(item)
        return {"summary": _aggregate(items), "items": items}

    def overview(self) -> dict[str, Any]:
        """Figures for the dashboard, all computed from stored runs."""
        with self._db.session() as session:
            total_runs = session.scalar(select(func.count()).select_from(EpisodeRecord)) or 0
            successful = (
                session.scalar(select(func.count()).select_from(EpisodeRecord).where(EpisodeRecord.success.is_(True)))
                or 0
            )
            average = session.scalar(select(func.avg(EvaluationRecord.score)))
            recent_events = session.scalars(
                select(EventRecord)
                .where(EventRecord.category.in_(("milestone", "collision", "error")))
                .order_by(EventRecord.id.desc())
                .limit(8)
            ).all()
            events = [event_to_dict(record) for record in recent_events]
        return {
            "scenarios": len(list_scenarios()),
            "total_runs": total_runs,
            "successful_runs": successful,
            "average_score": round(average, 1) if average is not None else None,
            "recent_episodes": self.list(limit=6),
            "recent_events": events,
            "active_episode_id": self.active_episode_id,
        }

    # -- export --------------------------------------------------------------

    def export_json(self, episode_id: str) -> dict[str, Any]:
        return {
            "episode": self.get(episode_id),
            "evaluation": self.evaluation(episode_id),
            "events": self.events(episode_id, limit=100_000),
        }

    def export_csv(self, episode_id: str) -> str:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=EVENT_CSV_COLUMNS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(self.events(episode_id, limit=100_000))
        return buffer.getvalue()


def _aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(items)
    if count == 0:
        return {
            "total_episodes": 0,
            "success_rate": None,
            "average_score": None,
            "average_completion_steps": None,
            "collision_rate": None,
        }
    successes = [item for item in items if item["success"]]
    with_incident = sum(1 for item in items if item["collisions"] > 0)
    return {
        "total_episodes": count,
        "success_rate": round(len(successes) / count, 4),
        "average_score": round(sum(item["score"] for item in items) / count, 1),
        "average_completion_steps": (
            round(sum(item["steps"] for item in successes) / len(successes), 1) if successes else None
        ),
        "collision_rate": round(with_incident / count, 4),
    }
