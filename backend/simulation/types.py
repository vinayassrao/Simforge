"""Core enumerations and value types shared by the whole simulation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

Cell = tuple[int, int]


class Orientation(StrEnum):
    NORTH = "NORTH"
    EAST = "EAST"
    SOUTH = "SOUTH"
    WEST = "WEST"

    @property
    def vector(self) -> Cell:
        return _VECTORS[self]

    @property
    def left(self) -> Orientation:
        return _CLOCKWISE[(_CLOCKWISE.index(self) - 1) % 4]

    @property
    def right(self) -> Orientation:
        return _CLOCKWISE[(_CLOCKWISE.index(self) + 1) % 4]

    @property
    def heading_degrees(self) -> float:
        """Panda3D heading (H) for this orientation; 0 faces +Y (north)."""
        return _HEADINGS[self]


_CLOCKWISE = [Orientation.NORTH, Orientation.EAST, Orientation.SOUTH, Orientation.WEST]
_VECTORS = {
    Orientation.NORTH: (0, 1),
    Orientation.EAST: (1, 0),
    Orientation.SOUTH: (0, -1),
    Orientation.WEST: (-1, 0),
}
_HEADINGS = {
    Orientation.NORTH: 0.0,
    Orientation.WEST: 90.0,
    Orientation.SOUTH: 180.0,
    Orientation.EAST: 270.0,
}


class Action(StrEnum):
    MOVE_FORWARD = "MOVE_FORWARD"
    MOVE_BACKWARD = "MOVE_BACKWARD"
    TURN_LEFT = "TURN_LEFT"
    TURN_RIGHT = "TURN_RIGHT"
    PICK_UP = "PICK_UP"
    DROP = "DROP"
    WAIT = "WAIT"


class AgentState(StrEnum):
    IDLE = "IDLE"
    NAVIGATING_TO_OBJECT = "NAVIGATING_TO_OBJECT"
    PICKING_UP = "PICKING_UP"
    NAVIGATING_TO_TARGET = "NAVIGATING_TO_TARGET"
    DROPPING_OBJECT = "DROPPING_OBJECT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EpisodeStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"

    @property
    def is_finished(self) -> bool:
        return self in {EpisodeStatus.COMPLETED, EpisodeStatus.FAILED, EpisodeStatus.ABORTED}


class AgentMode(StrEnum):
    MANUAL = "manual"
    ASTAR = "astar"
    EXTERNAL = "external"


class PackageState(StrEnum):
    AVAILABLE = "available"
    CARRIED = "carried"
    DELIVERED = "delivered"


class ZoneKind(StrEnum):
    LOADING = "loading"
    COLLECTION = "collection"
    DELIVERY = "delivery"
    RESTRICTED = "restricted"


@dataclass(frozen=True)
class Pose:
    """A robot position together with the direction it faces."""

    cell: Cell
    orientation: Orientation

    @property
    def front(self) -> Cell:
        return add(self.cell, self.orientation.vector)

    @property
    def back(self) -> Cell:
        dx, dy = self.orientation.vector
        return (self.cell[0] - dx, self.cell[1] - dy)


def add(cell: Cell, vector: Cell) -> Cell:
    return (cell[0] + vector[0], cell[1] + vector[1])


def manhattan(a: Cell, b: Cell) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbours(cell: Cell) -> list[Cell]:
    return [add(cell, orientation.vector) for orientation in Orientation]
