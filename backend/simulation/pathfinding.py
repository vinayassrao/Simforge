"""A* search over robot poses (cell + orientation).

Searching poses rather than cells means turning costs one action, exactly as it
does for the robot, so the plan length equals the number of actions needed.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable, Collection, Iterable
from itertools import count

from simulation.types import Action, Cell, Orientation, Pose, manhattan

Passable = Callable[[Cell], bool]

MOVE_ACTIONS = (Action.MOVE_FORWARD, Action.MOVE_BACKWARD, Action.TURN_LEFT, Action.TURN_RIGHT)


def apply_move(pose: Pose, action: Action) -> Pose:
    """The pose that results from a movement action, ignoring obstacles."""
    if action is Action.MOVE_FORWARD:
        return Pose(pose.front, pose.orientation)
    if action is Action.MOVE_BACKWARD:
        return Pose(pose.back, pose.orientation)
    if action is Action.TURN_LEFT:
        return Pose(pose.cell, pose.orientation.left)
    if action is Action.TURN_RIGHT:
        return Pose(pose.cell, pose.orientation.right)
    return pose


def plan_actions(start: Pose, goals: Collection[Pose], passable: Passable) -> list[Action] | None:
    """Shortest action sequence from ``start`` to any goal pose, or None if unreachable.

    ``passable`` decides whether the robot may stand on a cell. The start cell is
    always allowed, because the robot is already there.
    """
    goal_set = set(goals)
    if not goal_set:
        return None
    if start in goal_set:
        return []
    goal_cells = {goal.cell for goal in goal_set}

    def heuristic(cell: Cell) -> int:
        return min(manhattan(cell, goal_cell) for goal_cell in goal_cells)

    tie_breaker = count()
    frontier: list[tuple[int, int, int, Pose]] = [(heuristic(start.cell), next(tie_breaker), 0, start)]
    best_cost: dict[Pose, int] = {start: 0}
    came_from: dict[Pose, tuple[Pose, Action]] = {}

    while frontier:
        _, _, cost, pose = heapq.heappop(frontier)
        if pose in goal_set:
            return _reconstruct(came_from, pose)
        if cost > best_cost[pose]:
            continue
        for action in MOVE_ACTIONS:
            successor = apply_move(pose, action)
            if successor.cell != pose.cell and not passable(successor.cell):
                continue
            new_cost = cost + 1
            if new_cost < best_cost.get(successor, new_cost + 1):
                best_cost[successor] = new_cost
                came_from[successor] = (pose, action)
                priority = new_cost + heuristic(successor.cell)
                heapq.heappush(frontier, (priority, next(tie_breaker), new_cost, successor))
    return None


def _reconstruct(came_from: dict[Pose, tuple[Pose, Action]], pose: Pose) -> list[Action]:
    actions: list[Action] = []
    while pose in came_from:
        pose, action = came_from[pose]
        actions.append(action)
    actions.reverse()
    return actions


def path_cells(start: Pose, actions: Iterable[Action]) -> list[Cell]:
    """The cells visited when ``actions`` are executed from ``start`` (start included)."""
    cells = [start.cell]
    pose = start
    for action in actions:
        pose = apply_move(pose, action)
        if pose.cell != cells[-1]:
            cells.append(pose.cell)
    return cells


def facing_poses(targets: Iterable[Cell], passable: Passable) -> list[Pose]:
    """Poses from which the robot faces one of ``targets`` from an adjacent passable cell."""
    poses: list[Pose] = []
    for target in targets:
        for orientation in Orientation:
            dx, dy = orientation.vector
            stand = (target[0] - dx, target[1] - dy)
            if passable(stand):
                poses.append(Pose(stand, orientation))
    return poses
