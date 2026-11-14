"""Scenario definitions: the static description of a warehouse task."""

from __future__ import annotations

from dataclasses import dataclass, field

from simulation.types import Cell, Orientation, ZoneKind

SHELF = "#"
OBSTACLE = "X"
RESTRICTED = "R"

EVALUATION_CRITERIA: tuple[tuple[str, int, str], ...] = (
    ("Complete the task", 50, "Every assigned package is delivered to its destination."),
    ("Correct pickup and delivery", 20, "10 points for collecting, 10 for delivering."),
    ("Collision safety", 15, "3 points are lost per collision or restricted-area entry."),
    ("Path efficiency", 10, "Baseline route length divided by the steps actually used."),
    ("Valid actions", 5, "Share of submitted actions whose preconditions were met."),
)


@dataclass(frozen=True)
class ZoneSpec:
    id: str
    name: str
    kind: ZoneKind
    cells: frozenset[Cell]
    color: str


@dataclass(frozen=True)
class PackageSpec:
    """A package to deliver. The seed picks one of ``candidate_cells`` as its start."""

    id: str
    name: str
    category: str
    color: str
    weight_kg: float
    candidate_cells: tuple[Cell, ...]
    destination_zone_id: str


@dataclass(frozen=True)
class PatrolSpec:
    """A moving obstacle that shuttles between two cells on a straight line."""

    id: str
    name: str
    start: Cell
    end: Cell
    period: int = 2


@dataclass(frozen=True)
class ScenarioDefinition:
    id: str
    name: str
    summary: str
    description: str
    instructions: str
    difficulty: str
    task_type: str
    complexity: str
    estimated_minutes: int
    width: int
    height: int
    shelves: frozenset[Cell]
    static_obstacles: frozenset[Cell]
    zones: tuple[ZoneSpec, ...]
    checkpoints: tuple[Cell, ...]
    start_cell: Cell
    start_orientation: Orientation
    packages: tuple[PackageSpec, ...]
    patrols: tuple[PatrolSpec, ...] = ()
    max_steps: int = 200
    max_collisions: int = 8
    time_limit_s: float | None = None
    default_seed: int = 7
    completion_conditions: tuple[str, ...] = ()
    failure_conditions: tuple[str, ...] = ()
    evaluation_criteria: tuple[tuple[str, int, str], ...] = field(default=EVALUATION_CRITERIA)

    def zone(self, zone_id: str) -> ZoneSpec:
        for zone in self.zones:
            if zone.id == zone_id:
                return zone
        raise KeyError(f"Unknown zone '{zone_id}' in scenario '{self.id}'")

    @property
    def restricted_cells(self) -> frozenset[Cell]:
        cells: set[Cell] = set()
        for zone in self.zones:
            if zone.kind is ZoneKind.RESTRICTED:
                cells |= zone.cells
        return frozenset(cells)

    @property
    def static_blocked(self) -> frozenset[Cell]:
        return self.shelves | self.static_obstacles


@dataclass(frozen=True)
class ParsedLayout:
    width: int
    height: int
    shelves: frozenset[Cell]
    static_obstacles: frozenset[Cell]
    restricted: frozenset[Cell]


def parse_layout(rows: tuple[str, ...]) -> ParsedLayout:
    """Turn an ASCII floor plan into cell sets. The first row is the north edge."""
    height = len(rows)
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("Every layout row must have the same width")

    cells: dict[str, set[Cell]] = {SHELF: set(), OBSTACLE: set(), RESTRICTED: set()}
    for row_index, row in enumerate(rows):
        y = height - 1 - row_index
        for x, symbol in enumerate(row):
            if symbol in cells:
                cells[symbol].add((x, y))
    return ParsedLayout(
        width=width,
        height=height,
        shelves=frozenset(cells[SHELF]),
        static_obstacles=frozenset(cells[OBSTACLE]),
        restricted=frozenset(cells[RESTRICTED]),
    )


def rectangle(x0: int, y0: int, x1: int, y1: int) -> frozenset[Cell]:
    """All cells in the inclusive rectangle from (x0, y0) to (x1, y1)."""
    return frozenset((x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1))
