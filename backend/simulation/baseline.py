"""Baseline route length used to score path efficiency."""

from __future__ import annotations

from simulation.pathfinding import apply_move, facing_poses, plan_actions
from simulation.types import Cell, Pose
from simulation.world import World


def baseline_route_length(world: World) -> int | None:
    """Actions an informed planner needs on the starting map, ignoring moving obstacles.

    For each package in order: drive to it, pick it up, drive to its zone, drop it.
    Returns None if some leg has no route.
    """
    scenario = world.scenario
    package_cells = {package.id: package.position for package in world.packages.values()}
    delivered_cells: set[Cell] = set()
    pose = world.robot.pose
    total = 0

    for spec in scenario.packages:
        blocked = scenario.static_blocked | scenario.restricted_cells | delivered_cells
        blocked |= {cell for cell in package_cells.values() if cell is not None}

        def passable(cell: Cell, blocked: frozenset[Cell] | set[Cell] = blocked) -> bool:
            return world.in_bounds(cell) and cell not in blocked

        package_cell = package_cells[spec.id]
        if package_cell is None:
            return None
        to_package = plan_actions(pose, facing_poses([package_cell], passable), passable)
        if to_package is None:
            return None
        pose = _follow(pose, to_package)
        package_cells[spec.id] = None
        blocked_after_pickup = blocked - {package_cell}

        def passable_carrying(cell: Cell, blocked: frozenset[Cell] | set[Cell] = blocked_after_pickup) -> bool:
            return world.in_bounds(cell) and cell not in blocked

        zone_cells = [cell for cell in scenario.zone(spec.destination_zone_id).cells if passable_carrying(cell)]
        to_zone = plan_actions(pose, facing_poses(zone_cells, passable_carrying), passable_carrying)
        if to_zone is None:
            return None
        pose = _follow(pose, to_zone)
        delivered_cells.add(pose.front)
        total += len(to_package) + 1 + len(to_zone) + 1
    return total


def _follow(pose: Pose, actions: list) -> Pose:
    for action in actions:
        pose = apply_move(pose, action)
    return pose
