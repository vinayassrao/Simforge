"""The three built-in warehouse scenarios. They share one floor plan."""

from __future__ import annotations

from simulation.scenarios.base import (
    PackageSpec,
    PatrolSpec,
    ScenarioDefinition,
    ZoneSpec,
    parse_layout,
    rectangle,
)
from simulation.types import Orientation, ZoneKind

# '#' shelf, 'X' static obstacle, 'R' restricted floor, '.' open floor.
# The first row is the north wall (y = 11); the last row is y = 0.
BASE_LAYOUT = (
    "................",
    ".##.##.##.##....",
    ".##.##.##.##....",
    "................",
    ".##.##.##.##....",
    ".##.##.##.##....",
    "................",
    "................",
    "...X....RR......",
    "........RR..X...",
    "................",
    "................",
)

# Scenario 2 adds pallets that close some aisles and force detours.
OBSTACLE_LAYOUT = (
    "......X.........",
    ".##.##.##.##....",
    ".##.##.##.##....",
    "......X.........",
    ".##.##.##.##....",
    ".##.##.##.##X...",
    "................",
    "....X...........",
    "...X....RR......",
    "........RR..X...",
    "................",
    "................",
)

LOADING_DOCK = ZoneSpec("zone-loading", "Loading dock", ZoneKind.LOADING, rectangle(0, 0, 1, 1), "#64748b")
COLLECTION = ZoneSpec("zone-collection", "Collection bay", ZoneKind.COLLECTION, rectangle(13, 8, 15, 11), "#38bdf8")
DELIVERY_GREEN = ZoneSpec(
    "zone-delivery-green", "Green delivery zone", ZoneKind.DELIVERY, rectangle(13, 0, 14, 1), "#22c55e"
)
DELIVERY_ORANGE = ZoneSpec(
    "zone-delivery-orange", "Orange delivery zone", ZoneKind.DELIVERY, rectangle(0, 10, 0, 11), "#f97316"
)
CHECKPOINTS = ((3, 5), (6, 5), (9, 5), (12, 5), (3, 8), (9, 8))

BLUE_PACKAGE = PackageSpec(
    id="package-001",
    name="Blue package",
    category="electronics",
    color="#3b82f6",
    weight_kg=2.5,
    candidate_cells=((14, 10), (15, 9), (14, 8)),
    destination_zone_id=DELIVERY_GREEN.id,
)
AMBER_PACKAGE = PackageSpec(
    id="package-002",
    name="Amber package",
    category="fragile",
    color="#f59e0b",
    weight_kg=4.0,
    candidate_cells=((13, 11), (15, 11), (13, 9)),
    destination_zone_id=DELIVERY_ORANGE.id,
)

SHARED_FAILURES = (
    "The step limit is reached before every package is delivered.",
    "The robot causes too many collisions or restricted-area entries.",
)


def _restricted_zone(cells: frozenset) -> ZoneSpec:
    return ZoneSpec("zone-restricted", "Restricted area", ZoneKind.RESTRICTED, cells, "#ef4444")


def _build(layout_rows: tuple[str, ...], **fields) -> ScenarioDefinition:
    layout = parse_layout(layout_rows)
    zones = (*fields.pop("zones"), _restricted_zone(layout.restricted))
    return ScenarioDefinition(
        width=layout.width,
        height=layout.height,
        shelves=layout.shelves,
        static_obstacles=layout.static_obstacles,
        zones=zones,
        checkpoints=CHECKPOINTS,
        start_cell=(0, 0),
        start_orientation=Orientation.EAST,
        failure_conditions=SHARED_FAILURES,
        **fields,
    )


BASIC_DELIVERY = _build(
    BASE_LAYOUT,
    id="basic-delivery",
    name="Basic Delivery",
    summary="Collect one package and deliver it. The introductory tutorial.",
    description=(
        "A quiet warehouse with nothing moving. The robot leaves the loading dock, drives to "
        "the collection bay, picks up the blue package and brings it to the green delivery zone."
    ),
    instructions=("Navigate to the blue package, collect it, and deliver it to the green delivery zone."),
    difficulty="Beginner",
    task_type="Single delivery",
    complexity="Low",
    estimated_minutes=1,
    zones=(LOADING_DOCK, COLLECTION, DELIVERY_GREEN),
    packages=(BLUE_PACKAGE,),
    max_steps=150,
    completion_conditions=("The blue package rests inside the green delivery zone.",),
)

OBSTACLE_NAVIGATION = _build(
    OBSTACLE_LAYOUT,
    id="obstacle-navigation",
    name="Obstacle Navigation",
    summary="Deliver across the warehouse while forklifts patrol the aisles.",
    description=(
        "Pallets block some aisles and two forklifts patrol the cross aisles. The robot must "
        "carry the package from the collection bay to the orange delivery zone on the far side, "
        "re-planning its route whenever a forklift gets in the way."
    ),
    instructions=("Collect the assigned package and deliver it while avoiding moving warehouse obstacles."),
    difficulty="Intermediate",
    task_type="Dynamic navigation",
    complexity="Medium",
    estimated_minutes=2,
    zones=(LOADING_DOCK, COLLECTION, DELIVERY_ORANGE),
    packages=(
        PackageSpec(
            id="package-001",
            name="Blue package",
            category="electronics",
            color="#3b82f6",
            weight_kg=2.5,
            candidate_cells=BLUE_PACKAGE.candidate_cells,
            destination_zone_id=DELIVERY_ORANGE.id,
        ),
    ),
    patrols=(
        PatrolSpec("forklift-001", "Forklift A", (1, 5), (11, 5), period=2),
        PatrolSpec("forklift-002", "Forklift B", (3, 6), (3, 10), period=2),
        PatrolSpec("forklift-003", "Forklift C", (12, 7), (12, 11), period=3),
    ),
    max_steps=220,
    completion_conditions=("The blue package rests inside the orange delivery zone.",),
)

MULTI_STEP_DELIVERY = _build(
    BASE_LAYOUT,
    id="multi-step-delivery",
    name="Multi-Step Delivery",
    summary="Deliver two packages, in order, to two different zones.",
    description=(
        "Two packages wait in the collection bay. The blue package must reach the green zone "
        "first; only then can the amber package be collected and taken to the orange zone. "
        "One forklift patrols the central aisle."
    ),
    instructions=(
        "Collect two assigned packages in the correct order and deliver both to their designated destinations."
    ),
    difficulty="Advanced",
    task_type="Sequenced delivery",
    complexity="High",
    estimated_minutes=3,
    zones=(LOADING_DOCK, COLLECTION, DELIVERY_GREEN, DELIVERY_ORANGE),
    packages=(BLUE_PACKAGE, AMBER_PACKAGE),
    patrols=(PatrolSpec("forklift-001", "Forklift A", (3, 4), (11, 4), period=2),),
    max_steps=320,
    completion_conditions=(
        "The blue package rests inside the green delivery zone.",
        "The amber package rests inside the orange delivery zone.",
        "The blue package was delivered before the amber package was collected.",
    ),
)
