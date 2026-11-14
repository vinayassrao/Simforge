"""Task progress: which package is next, which milestones are done, and the checklist."""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.actions import ActionOutcome
from simulation.agent import AgentStateMachine
from simulation.types import AgentState, PackageState, manhattan
from simulation.world import Package, World

MILESTONES = ("reach_object", "collect", "reach_destination", "deliver")


@dataclass
class Objective:
    """One package to deliver, with the milestones reached so far."""

    package_id: str
    done: set[str] = field(default_factory=set)

    @property
    def complete(self) -> bool:
        return "deliver" in self.done


@dataclass(frozen=True)
class ChecklistItem:
    id: str
    label: str
    done: bool
    current: bool


class TaskManager:
    """Follows the task from the first package to the last delivery."""

    def __init__(self, world: World) -> None:
        self._world = world
        self.fsm = AgentStateMachine()
        self.objectives = [Objective(spec.id) for spec in world.scenario.packages]
        self.collected_ids: set[str] = set()
        self.delivered_ids: set[str] = set()

    # -- current target ----------------------------------------------------

    @property
    def current_objective(self) -> Objective | None:
        for objective in self.objectives:
            if not objective.complete:
                return objective
        return None

    @property
    def current_package(self) -> Package | None:
        objective = self.current_objective
        return self._world.packages[objective.package_id] if objective else None

    @property
    def is_complete(self) -> bool:
        return self.current_objective is None

    # -- lifecycle ---------------------------------------------------------

    def start(self) -> None:
        self.fsm.transition(AgentState.NAVIGATING_TO_OBJECT)
        self.update_milestones()

    def fail(self) -> None:
        if not self.fsm.is_terminal:
            self.fsm.transition(AgentState.FAILED)

    def begin_step(self) -> None:
        """Leave one-step states (picking up, dropping) before the next action."""
        self.fsm.settle()

    def apply(self, outcome: ActionOutcome) -> list[str]:
        """Update the task after an action. Returns the milestones newly reached."""
        objective = self.current_objective
        if outcome.picked_up is not None and objective is not None:
            self.collected_ids.add(outcome.picked_up.id)
            self.fsm.transition(AgentState.PICKING_UP)
        elif outcome.dropped is not None:
            self.fsm.transition(AgentState.DROPPING_OBJECT)
            if outcome.delivered and objective is not None:
                self.delivered_ids.add(outcome.dropped.id)
                newly = self._mark(objective, "reach_destination", "deliver")
                if self.is_complete:
                    self.fsm.transition(AgentState.COMPLETED)
                return newly
            if objective is not None:
                # Dropped outside the zone: the package must be collected again.
                objective.done -= {"collect", "reach_destination"}
        return self.update_milestones()

    def update_milestones(self) -> list[str]:
        """Mark position-based milestones for the current objective."""
        objective = self.current_objective
        package = self.current_package
        if objective is None or package is None:
            return []
        robot = self._world.robot
        newly: list[str] = []
        if package.state is PackageState.CARRIED:
            newly += self._mark(objective, "reach_object", "collect")
            zone = self._world.scenario.zone(package.spec.destination_zone_id)
            if min(manhattan(robot.position, cell) for cell in zone.cells) <= 1:
                newly += self._mark(objective, "reach_destination")
        elif package.position is not None and manhattan(robot.position, package.position) <= 1:
            newly += self._mark(objective, "reach_object")
        return newly

    @staticmethod
    def _mark(objective: Objective, *milestones: str) -> list[str]:
        newly = [m for m in milestones if m not in objective.done]
        objective.done.update(newly)
        return newly

    # -- reporting ---------------------------------------------------------

    @property
    def progress(self) -> int:
        total = len(self.objectives) * len(MILESTONES)
        done = sum(len(objective.done) for objective in self.objectives)
        return round(100 * done / total)

    @property
    def completed_objectives(self) -> int:
        return sum(1 for objective in self.objectives if objective.complete)

    def checklist(self) -> list[ChecklistItem]:
        items: list[ChecklistItem] = []
        current_assigned = False
        for objective in self.objectives:
            package = self._world.packages[objective.package_id]
            zone = self._world.scenario.zone(package.spec.destination_zone_id)
            name = package.spec.name.lower()
            labels = {
                "reach_object": f"Reach the {name}",
                "collect": f"Collect the {name}",
                "reach_destination": f"Navigate to the {zone.name.lower()}",
                "deliver": f"Deliver the {name}",
            }
            for milestone in MILESTONES:
                done = milestone in objective.done
                is_current = not done and not current_assigned and not self.fsm.is_terminal
                current_assigned = current_assigned or is_current
                items.append(ChecklistItem(f"{objective.package_id}:{milestone}", labels[milestone], done, is_current))
        return items

    def describe_current_objective(self) -> str:
        if self.fsm.state is AgentState.COMPLETED:
            return "All packages delivered. Task complete."
        if self.fsm.state is AgentState.FAILED:
            return "The task failed."
        for item in self.checklist():
            if item.current:
                return item.label
        return "Waiting to start."
