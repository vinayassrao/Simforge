"""The interface every agent implements: observation in, decision out."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from simulation.events import EventType
from simulation.observation import Observation
from simulation.types import Action, Cell


@dataclass(frozen=True)
class AgentNote:
    """Something the agent wants logged about its reasoning, such as a re-plan."""

    event_type: EventType
    description: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Decision:
    action: Action
    planned_path: list[Cell] = field(default_factory=list)
    notes: list[AgentNote] = field(default_factory=list)


class Agent(Protocol):
    name: str

    def reset(self) -> None:
        """Forget everything from the previous episode."""

    def decide(self, observation: Observation) -> Decision:
        """Choose the next action from what the agent can currently observe."""
