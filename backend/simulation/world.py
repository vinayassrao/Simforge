"""Mutable world state for one episode: robot, packages and moving obstacles."""

from __future__ import annotations

import random
from dataclasses import dataclass

from simulation.scenarios.base import PackageSpec, PatrolSpec, ScenarioDefinition, ZoneSpec
from simulation.types import Cell, Orientation, PackageState, Pose


@dataclass
class Robot:
    position: Cell
    orientation: Orientation
    carrying: str | None = None

    @property
    def pose(self) -> Pose:
        return Pose(self.position, self.orientation)


@dataclass
class Package:
    spec: PackageSpec
    position: Cell | None
    state: PackageState = PackageState.AVAILABLE

    @property
    def id(self) -> str:
        return self.spec.id


@dataclass
class MovingObstacle:
    """A forklift that shuttles along a fixed straight route."""

    spec: PatrolSpec
    route: list[Cell]
    index: int
    direction: int

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def position(self) -> Cell:
        return self.route[self.index]

    def _next_index(self) -> tuple[int, int]:
        direction = self.direction
        if not 0 <= self.index + direction < len(self.route):
            direction = -direction
        return self.index + direction, direction

    @property
    def next_position(self) -> Cell:
        """The cell this obstacle will try to enter on its next move."""
        return self.route[self._next_index()[0]]

    def advance(self) -> None:
        self.index, self.direction = self._next_index()


def straight_route(start: Cell, end: Cell) -> list[Cell]:
    """Cells on the axis-aligned segment from ``start`` to ``end``, inclusive."""
    if start[0] != end[0] and start[1] != end[1]:
        raise ValueError("Patrol routes must be horizontal or vertical")
    step_x = (end[0] > start[0]) - (end[0] < start[0])
    step_y = (end[1] > start[1]) - (end[1] < start[1])
    length = abs(end[0] - start[0]) + abs(end[1] - start[1])
    return [(start[0] + step_x * i, start[1] + step_y * i) for i in range(length + 1)]


class World:
    """Everything that can change during an episode.

    The same scenario and seed always produce the same starting world.
    """

    def __init__(self, scenario: ScenarioDefinition, seed: int) -> None:
        self.scenario = scenario
        self.seed = seed
        rng = random.Random(seed)
        self.robot = Robot(scenario.start_cell, scenario.start_orientation)
        self.packages = self._spawn_packages(rng)
        self.obstacles = [self._spawn_obstacle(patrol, rng) for patrol in scenario.patrols]
        self.step_count = 0

    def _spawn_packages(self, rng: random.Random) -> dict[str, Package]:
        packages: dict[str, Package] = {}
        taken: set[Cell] = set()
        for spec in self.scenario.packages:
            free = [cell for cell in spec.candidate_cells if cell not in taken]
            cell = rng.choice(free)
            taken.add(cell)
            packages[spec.id] = Package(spec, cell)
        return packages

    @staticmethod
    def _spawn_obstacle(patrol: PatrolSpec, rng: random.Random) -> MovingObstacle:
        route = straight_route(patrol.start, patrol.end)
        return MovingObstacle(
            spec=patrol,
            route=route,
            index=rng.randrange(len(route)),
            direction=rng.choice((1, -1)),
        )

    # -- queries -----------------------------------------------------------

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.scenario.width and 0 <= cell[1] < self.scenario.height

    def package_at(self, cell: Cell) -> Package | None:
        for package in self.packages.values():
            if package.position == cell and package.state is not PackageState.CARRIED:
                return package
        return None

    def obstacle_at(self, cell: Cell) -> MovingObstacle | None:
        for obstacle in self.obstacles:
            if obstacle.position == cell:
                return obstacle
        return None

    def zone_containing(self, cell: Cell) -> ZoneSpec | None:
        for zone in self.scenario.zones:
            if cell in zone.cells:
                return zone
        return None

    def is_restricted(self, cell: Cell) -> bool:
        return cell in self.scenario.restricted_cells

    @property
    def carried_package(self) -> Package | None:
        return self.packages[self.robot.carrying] if self.robot.carrying else None

    # -- moving obstacles --------------------------------------------------

    def advance_obstacles(self) -> None:
        """Move each obstacle whose turn it is. Obstacles yield to anything in their way."""
        for obstacle in self.obstacles:
            if self.step_count % obstacle.spec.period != 0:
                continue
            target = obstacle.next_position
            blocked = (
                target == self.robot.position
                or self.package_at(target) is not None
                or any(other is not obstacle and other.position == target for other in self.obstacles)
            )
            if not blocked:
                obstacle.advance()
