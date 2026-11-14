"""Structured simulation events."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class EventCategory(StrEnum):
    ACTION = "action"
    COLLISION = "collision"
    ERROR = "error"
    MILESTONE = "milestone"
    INFO = "info"


class EventType(StrEnum):
    SIMULATION_STARTED = "SIMULATION_STARTED"
    SIMULATION_PAUSED = "SIMULATION_PAUSED"
    SIMULATION_RESUMED = "SIMULATION_RESUMED"
    SIMULATION_RESET = "SIMULATION_RESET"
    AGENT_SPAWNED = "AGENT_SPAWNED"
    STATE_CHANGED = "STATE_CHANGED"
    MOVE_COMPLETED = "MOVE_COMPLETED"
    TURN_COMPLETED = "TURN_COMPLETED"
    WAITED = "WAITED"
    COLLISION = "COLLISION"
    RESTRICTED_AREA_ENTERED = "RESTRICTED_AREA_ENTERED"
    OBSTACLE_DETECTED = "OBSTACLE_DETECTED"
    PATH_PLANNED = "PATH_PLANNED"
    PATH_RECALCULATED = "PATH_RECALCULATED"
    PICKUP_SUCCESS = "PICKUP_SUCCESS"
    PICKUP_FAILED = "PICKUP_FAILED"
    DROP_FAILED = "DROP_FAILED"
    OBJECT_DROPPED = "OBJECT_DROPPED"
    DELIVERY_SUCCESS = "DELIVERY_SUCCESS"
    MILESTONE_REACHED = "MILESTONE_REACHED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"


@dataclass(frozen=True)
class SimEvent:
    seq: int
    episode_id: str
    step: int
    type: EventType
    category: EventCategory
    description: str
    entity_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["type"] = self.type.value
        payload["category"] = self.category.value
        return payload


class EventLog:
    """Append-only event list for one episode, with a cursor for unread events."""

    def __init__(self, episode_id: str) -> None:
        self._episode_id = episode_id
        self._events: list[SimEvent] = []
        self._cursor = 0

    def record(
        self,
        step: int,
        event_type: EventType,
        category: EventCategory,
        description: str,
        entity_id: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> SimEvent:
        event = SimEvent(
            seq=len(self._events) + 1,
            episode_id=self._episode_id,
            step=step,
            type=event_type,
            category=category,
            description=description,
            entity_id=entity_id,
            data=data or {},
        )
        self._events.append(event)
        return event

    def drain(self) -> list[SimEvent]:
        """Return events recorded since the previous call."""
        fresh = self._events[self._cursor :]
        self._cursor = len(self._events)
        return fresh

    def recent(self, count: int) -> list[SimEvent]:
        return self._events[-count:]

    @property
    def all(self) -> list[SimEvent]:
        return list(self._events)
