"""Baseline autonomous agent: plans with A* and re-plans when the world changes.

The agent sees only the observation, exactly like an external agent, and every
decision is a normal action that goes through the same rules as manual control.
"""

from __future__ import annotations

from agents.base import AgentNote, Decision
from simulation.events import EventType
from simulation.observation import Observation
from simulation.pathfinding import facing_poses, path_cells, plan_actions
from simulation.types import Action, Cell, PackageState, Pose, ZoneKind


class AStarAgent:
    name = "astar"

    def __init__(self) -> None:
        self._remaining: list[Action] = []
        self._leg: tuple[str, bool] | None = None

    def reset(self) -> None:
        self._remaining = []
        self._leg = None

    def decide(self, observation: Observation) -> Decision:
        target = observation.target
        if target is None:
            return Decision(Action.WAIT)

        agent = observation.agent
        pose = Pose(agent.position, agent.orientation)
        moving_cells = self._moving_obstacle_cells(observation)
        blocked = self._blocked_cells(observation) | moving_cells
        width, height = observation.grid.width, observation.grid.height

        def passable(cell: Cell) -> bool:
            return 0 <= cell[0] < width and 0 <= cell[1] < height and cell not in blocked

        if agent.carrying:
            free_zone_cells = [cell for cell in target.delivery_cells if passable(cell)]
            goals = facing_poses(free_zone_cells, passable)
            final_action, goal_name = Action.DROP, target.delivery_zone_name.lower()
        else:
            goals = facing_poses([target.position] if target.position else [], passable)
            final_action, goal_name = Action.PICK_UP, target.name.lower()

        plan = plan_actions(pose, goals, passable)
        leg = (target.object_id, agent.carrying)
        notes = self._explain(plan, leg, pose, moving_cells, goal_name)
        self._leg = leg

        if plan is None:
            self._remaining = []
            return Decision(Action.WAIT, notes=notes)
        if not plan:
            self._remaining = []
            return Decision(final_action, notes=notes)
        self._remaining = plan[1:]
        return Decision(plan[0], planned_path=path_cells(pose, plan), notes=notes)

    # -- world model -------------------------------------------------------

    @staticmethod
    def _blocked_cells(observation: Observation) -> set[Cell]:
        blocked: set[Cell] = set(observation.obstacles.static)
        for zone in observation.zones:
            if zone.kind is ZoneKind.RESTRICTED:
                blocked.update(zone.cells)
        for item in observation.objects:
            if item.position is not None and item.state is not PackageState.CARRIED:
                blocked.add(item.position)
        return blocked

    @staticmethod
    def _moving_obstacle_cells(observation: Observation) -> set[Cell]:
        """Cells a moving obstacle occupies now or will try to enter next."""
        cells: set[Cell] = set()
        for obstacle in observation.obstacles.moving:
            cells.add(obstacle.position)
            cells.add(obstacle.next_position)
        return cells

    # -- explanations ------------------------------------------------------

    def _explain(
        self,
        plan: list[Action] | None,
        leg: tuple[str, bool],
        pose: Pose,
        moving_cells: set[Cell],
        goal_name: str,
    ) -> list[AgentNote]:
        if plan is None:
            return [
                AgentNote(
                    EventType.OBSTACLE_DETECTED,
                    f"No free route to the {goal_name} right now; waiting for the way to clear.",
                )
            ]
        if leg != self._leg:
            return [
                AgentNote(
                    EventType.PATH_PLANNED,
                    f"Planned a {len(plan)}-action route to the {goal_name}.",
                    {"actions": len(plan), "path": [list(c) for c in path_cells(pose, plan)]},
                )
            ]
        old_path = set(path_cells(pose, self._remaining))
        blocking = sorted(old_path & moving_cells)
        if not blocking and len(plan) == len(self._remaining):
            return []
        notes: list[AgentNote] = []
        if blocking:
            notes.append(
                AgentNote(
                    EventType.OBSTACLE_DETECTED,
                    f"Moving obstacle detected on the planned route at {list(blocking[0])}.",
                    {"cells": [list(cell) for cell in blocking]},
                )
            )
        notes.append(
            AgentNote(
                EventType.PATH_RECALCULATED,
                f"Route recalculated: {len(plan)} actions to the {goal_name}.",
                {"actions": len(plan), "path": [list(c) for c in path_cells(pose, plan)]},
            )
        )
        return notes
