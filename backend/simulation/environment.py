"""The warehouse environment: one episode from reset to completion or failure."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from simulation.actions import ActionExecutor, ActionOutcome
from simulation.baseline import baseline_route_length
from simulation.events import EventCategory, EventLog, EventType, SimEvent
from simulation.observation import Observation
from simulation.scenarios.base import ScenarioDefinition
from simulation.task_manager import TaskManager
from simulation.types import Action, AgentState, Cell, EpisodeStatus, PackageState
from simulation.world import World

RECENT_EVENT_COUNT = 5

FAILURE_MESSAGES = {
    "step_limit_exceeded": "The step limit was reached before the task was finished.",
    "collision_limit_exceeded": "Too many collisions or restricted-area entries.",
    "time_limit_exceeded": "The time limit ran out before the task was finished.",
}


class EpisodeNotRunningError(RuntimeError):
    """Raised when an action is sent to an episode that is not accepting actions."""


@dataclass
class EpisodeMetrics:
    actions: int = 0
    collisions: int = 0
    restricted_entries: int = 0
    invalid_actions: int = 0
    last_step_ms: float = 0.0
    incident_locations: list[dict[str, Any]] = field(default_factory=list)

    @property
    def safety_incidents(self) -> int:
        return self.collisions + self.restricted_entries


@dataclass(frozen=True)
class StepResult:
    outcome: ActionOutcome
    done: bool


class WarehouseEnvironment:
    """Runs one episode of a scenario. Deterministic for a given scenario and seed."""

    def __init__(self, scenario: ScenarioDefinition, seed: int, episode_id: str) -> None:
        self.scenario = scenario
        self.seed = seed
        self.episode_id = episode_id
        self.world = World(scenario, seed)
        self.tasks = TaskManager(self.world)
        self.executor = ActionExecutor(self.world)
        self.events = EventLog(episode_id)
        self.metrics = EpisodeMetrics()
        self.status = EpisodeStatus.CREATED
        self.failure_reason: str | None = None
        self.baseline_steps = baseline_route_length(self.world)
        self.trajectory: list[list[Any]] = [self._trajectory_point()]
        robot = self.world.robot
        self._record(
            EventType.AGENT_SPAWNED,
            EventCategory.INFO,
            f"Robot placed at {list(robot.position)} facing {robot.orientation.value.lower()}.",
            entity_id="robot",
        )

    # -- lifecycle ---------------------------------------------------------

    @property
    def done(self) -> bool:
        return self.status.is_finished

    def start(self) -> None:
        if self.status is not EpisodeStatus.CREATED:
            raise EpisodeNotRunningError("The episode has already been started.")
        self.status = EpisodeStatus.RUNNING
        self._record(
            EventType.SIMULATION_STARTED,
            EventCategory.INFO,
            f"Simulation started: {self.scenario.name} (seed {self.seed}).",
        )
        self._transition_logged(self.tasks.start)

    def fail(self, reason: str) -> None:
        if self.done:
            return
        self.failure_reason = reason
        self.status = EpisodeStatus.FAILED
        self._transition_logged(self.tasks.fail)
        self._record(
            EventType.TASK_FAILED,
            EventCategory.ERROR,
            f"Task failed: {FAILURE_MESSAGES.get(reason, reason)}",
            data={"reason": reason},
        )

    # -- stepping ----------------------------------------------------------

    def step(self, action: Action) -> StepResult:
        if self.status is not EpisodeStatus.RUNNING:
            raise EpisodeNotRunningError(f"The episode is {self.status.value} and cannot accept actions.")
        started = time.perf_counter()
        self._transition_logged(self.tasks.begin_step)
        self.world.step_count += 1

        target = self.tasks.current_package
        outcome = self.executor.execute(action, target.id if target else None)
        self._account(outcome)
        self._transition_logged(lambda: self._apply_to_task(outcome))

        self.trajectory.append(self._trajectory_point())
        self.world.advance_obstacles()
        self._check_end_conditions()
        self.metrics.last_step_ms = (time.perf_counter() - started) * 1000
        return StepResult(outcome, self.done)

    def _account(self, outcome: ActionOutcome) -> None:
        metrics = self.metrics
        metrics.actions += 1
        self._record(
            outcome.event_type,
            outcome.category,
            outcome.message,
            entity_id=outcome.entity_id,
            data={"action": outcome.action.value, "error_code": outcome.error_code, **outcome.data},
        )
        if outcome.collision is not None and outcome.collision_cell is not None:
            metrics.collisions += 1
            self._add_incident("collision", outcome.collision_cell, outcome.collision.kind.value)
        elif outcome.is_invalid:
            metrics.invalid_actions += 1
        if outcome.restricted_entry:
            metrics.restricted_entries += 1
            cell = self.world.robot.position
            self._add_incident("restricted_area", cell, "restricted_area")
            self._record(
                EventType.RESTRICTED_AREA_ENTERED,
                EventCategory.COLLISION,
                f"Safety violation: the robot entered the restricted area at {list(cell)}.",
                entity_id="zone-restricted",
                data={"cell": list(cell)},
            )

    def _apply_to_task(self, outcome: ActionOutcome) -> None:
        labels = {item.id: item.label for item in self.tasks.checklist()}
        objective = self.tasks.current_objective
        for milestone in self.tasks.apply(outcome):
            if milestone in ("reach_object", "reach_destination") and objective is not None:
                self._record(
                    EventType.MILESTONE_REACHED,
                    EventCategory.MILESTONE,
                    f"Milestone reached: {labels[f'{objective.package_id}:{milestone}']}.",
                    entity_id=objective.package_id,
                    data={"milestone": milestone},
                )

    def _check_end_conditions(self) -> None:
        if self.tasks.is_complete:
            self.status = EpisodeStatus.COMPLETED
            self._record(
                EventType.TASK_COMPLETED,
                EventCategory.MILESTONE,
                f"Task completed in {self.world.step_count} steps.",
                data={"steps": self.world.step_count},
            )
        elif self.metrics.safety_incidents >= self.scenario.max_collisions:
            self.fail("collision_limit_exceeded")
        elif self.world.step_count >= self.scenario.max_steps:
            self.fail("step_limit_exceeded")

    # -- agent-originated events ---------------------------------------------

    def note(
        self,
        event_type: EventType,
        description: str,
        data: dict[str, Any] | None = None,
        category: EventCategory = EventCategory.INFO,
    ) -> None:
        """Record something an agent reports about its own reasoning, such as a re-plan."""
        self._record(event_type, category, description, entity_id="robot", data=data)

    # -- helpers -----------------------------------------------------------

    def _record(
        self,
        event_type: EventType,
        category: EventCategory,
        description: str,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> SimEvent:
        return self.events.record(self.world.step_count, event_type, category, description, entity_id, data)

    def _transition_logged(self, change) -> None:
        """Run ``change`` and log one event for every agent state transition it caused."""
        history = self.tasks.fsm.history
        seen = len(history)
        change()
        for before, after in zip(history[seen - 1 :], history[seen:], strict=False):
            self._record(
                EventType.STATE_CHANGED,
                EventCategory.INFO,
                f"Agent state: {_readable(before)} -> {_readable(after)}.",
                entity_id="robot",
                data={"from": before.value, "to": after.value},
            )

    def _add_incident(self, kind: str, cell: Cell, blocker: str) -> None:
        self.metrics.incident_locations.append(
            {"kind": kind, "cell": list(cell), "step": self.world.step_count, "blocker": blocker}
        )

    def _trajectory_point(self) -> list[Any]:
        robot = self.world.robot
        return [self.world.step_count, robot.position[0], robot.position[1], robot.orientation.value]

    # -- observation and summary ---------------------------------------------

    def legal_actions(self) -> list[Action]:
        if self.status is not EpisodeStatus.RUNNING:
            return []
        target = self.tasks.current_package
        return self.executor.legal_actions(target.id if target else None)

    def observe(self, status: EpisodeStatus | None = None) -> Observation:
        world = self.world
        scenario = self.scenario
        robot = world.robot
        target = self.tasks.current_package
        target_view = None
        if target is not None:
            zone = scenario.zone(target.spec.destination_zone_id)
            target_view = {
                "object_id": target.id,
                "name": target.spec.name,
                "position": target.position,
                "delivery_zone_id": zone.id,
                "delivery_zone_name": zone.name,
                "delivery_cells": sorted(zone.cells),
            }
        return Observation.model_validate(
            {
                "episode_id": self.episode_id,
                "scenario_id": scenario.id,
                "step": world.step_count,
                "max_steps": scenario.max_steps,
                "status": status or self.status,
                "agent": {
                    "position": robot.position,
                    "orientation": robot.orientation,
                    "state": self.tasks.fsm.state,
                    "carrying": robot.carrying is not None,
                    "carrying_object_id": robot.carrying,
                },
                "target": target_view,
                "objects": [
                    {
                        "id": package.id,
                        "name": package.spec.name,
                        "category": package.spec.category,
                        "color": package.spec.color,
                        "weight_kg": package.spec.weight_kg,
                        "position": package.position,
                        "state": package.state,
                        "destination_zone_id": package.spec.destination_zone_id,
                    }
                    for package in world.packages.values()
                ],
                "zones": [
                    {
                        "id": zone.id,
                        "name": zone.name,
                        "kind": zone.kind,
                        "color": zone.color,
                        "cells": sorted(zone.cells),
                    }
                    for zone in scenario.zones
                ],
                "obstacles": {
                    "static": sorted(scenario.static_blocked),
                    "moving": [
                        {
                            "id": obstacle.id,
                            "name": obstacle.spec.name,
                            "position": obstacle.position,
                            "next_position": obstacle.next_position,
                        }
                        for obstacle in world.obstacles
                    ],
                },
                "grid": {"width": scenario.width, "height": scenario.height},
                "checkpoints": list(scenario.checkpoints),
                "available_actions": self.legal_actions(),
                "task": {
                    "name": scenario.name,
                    "instructions": scenario.instructions,
                    "progress": self.tasks.progress,
                    "current_objective": self.tasks.describe_current_objective(),
                    "objectives_total": len(self.tasks.objectives),
                    "objectives_completed": self.tasks.completed_objectives,
                    "checklist": [vars(item) for item in self.tasks.checklist()],
                },
                "recent_events": [event.to_dict() for event in self.events.recent(RECENT_EVENT_COUNT)],
            }
        )

    def summary(self) -> dict[str, Any]:
        """Raw results of the episode, used by the evaluation engine."""
        packages = self.world.packages.values()
        return {
            "episode_id": self.episode_id,
            "scenario_id": self.scenario.id,
            "seed": self.seed,
            "completed": self.status is EpisodeStatus.COMPLETED,
            "failure_reason": self.failure_reason,
            "final_agent_state": self.tasks.fsm.state.value,
            "packages_total": len(self.world.packages),
            "packages_collected": len(self.tasks.collected_ids),
            "packages_delivered": sum(1 for p in packages if p.state is PackageState.DELIVERED),
            "collisions": self.metrics.collisions,
            "restricted_entries": self.metrics.restricted_entries,
            "invalid_actions": self.metrics.invalid_actions,
            "total_actions": self.metrics.actions,
            "steps": self.world.step_count,
            "max_steps": self.scenario.max_steps,
            "baseline_steps": self.baseline_steps,
            "progress": self.tasks.progress,
            "incident_locations": list(self.metrics.incident_locations),
            "trajectory": list(self.trajectory),
        }


def _readable(state: AgentState) -> str:
    return state.value.replace("_", " ").lower()
