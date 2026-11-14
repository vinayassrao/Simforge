"""The robot's finite-state machine."""

from __future__ import annotations

from simulation.types import AgentState

S = AgentState

ALLOWED_TRANSITIONS: dict[AgentState, frozenset[AgentState]] = {
    S.IDLE: frozenset({S.NAVIGATING_TO_OBJECT, S.FAILED}),
    S.NAVIGATING_TO_OBJECT: frozenset({S.PICKING_UP, S.FAILED}),
    S.PICKING_UP: frozenset({S.NAVIGATING_TO_TARGET, S.FAILED}),
    S.NAVIGATING_TO_TARGET: frozenset({S.DROPPING_OBJECT, S.FAILED}),
    S.DROPPING_OBJECT: frozenset({S.NAVIGATING_TO_OBJECT, S.COMPLETED, S.FAILED}),
    S.COMPLETED: frozenset(),
    S.FAILED: frozenset(),
}

# States that last for exactly one step and then move on by themselves.
TRANSIENT_STATES: dict[AgentState, AgentState] = {
    S.PICKING_UP: S.NAVIGATING_TO_TARGET,
    S.DROPPING_OBJECT: S.NAVIGATING_TO_OBJECT,
}


class InvalidTransitionError(RuntimeError):
    def __init__(self, current: AgentState, target: AgentState) -> None:
        super().__init__(f"Illegal agent state transition: {current} -> {target}")
        self.current = current
        self.target = target


class AgentStateMachine:
    """Tracks the robot's task state and rejects transitions that make no sense."""

    def __init__(self) -> None:
        self.state = AgentState.IDLE
        self.history: list[AgentState] = [AgentState.IDLE]

    def can_transition(self, target: AgentState) -> bool:
        return target in ALLOWED_TRANSITIONS[self.state]

    def transition(self, target: AgentState) -> None:
        if not self.can_transition(target):
            raise InvalidTransitionError(self.state, target)
        self.state = target
        self.history.append(target)

    def settle(self) -> bool:
        """Leave a transient state. Returns True if the state changed."""
        follow_up = TRANSIENT_STATES.get(self.state)
        if follow_up is None:
            return False
        self.transition(follow_up)
        return True

    @property
    def is_terminal(self) -> bool:
        return self.state in {AgentState.COMPLETED, AgentState.FAILED}
