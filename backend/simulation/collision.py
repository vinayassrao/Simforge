"""Collision queries: what, if anything, occupies a cell."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from simulation.types import Cell
from simulation.world import World


class BlockerKind(StrEnum):
    WALL = "wall"
    SHELF = "shelf"
    STATIC_OBSTACLE = "static_obstacle"
    PACKAGE = "package"
    MOVING_OBSTACLE = "moving_obstacle"


@dataclass(frozen=True)
class Blocker:
    kind: BlockerKind
    entity_id: str
    description: str


def find_blocker(world: World, cell: Cell) -> Blocker | None:
    """Return whatever prevents the robot from entering ``cell``, or None if it is free."""
    if not world.in_bounds(cell):
        return Blocker(BlockerKind.WALL, "warehouse-wall", "the warehouse wall")
    if cell in world.scenario.shelves:
        return Blocker(BlockerKind.SHELF, f"shelf-{cell[0]}-{cell[1]}", "a shelving unit")
    if cell in world.scenario.static_obstacles:
        return Blocker(BlockerKind.STATIC_OBSTACLE, f"pallet-{cell[0]}-{cell[1]}", "a pallet stack")
    package = world.package_at(cell)
    if package is not None:
        return Blocker(BlockerKind.PACKAGE, package.id, f"the {package.spec.name.lower()}")
    obstacle = world.obstacle_at(cell)
    if obstacle is not None:
        return Blocker(BlockerKind.MOVING_OBSTACLE, obstacle.id, obstacle.spec.name)
    return None


def is_free(world: World, cell: Cell) -> bool:
    return find_blocker(world, cell) is None
