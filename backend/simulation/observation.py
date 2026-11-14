"""The observation schema: everything an agent is told about the world each step."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from simulation.types import Action, AgentState, EpisodeStatus, Orientation, PackageState, ZoneKind

CellModel = tuple[int, int]


class AgentView(BaseModel):
    position: CellModel
    orientation: Orientation
    state: AgentState
    carrying: bool
    carrying_object_id: str | None = None


class TargetView(BaseModel):
    """The package the task wants next and where it must go."""

    object_id: str
    name: str
    position: CellModel | None = Field(description="None while the robot carries the package.")
    delivery_zone_id: str
    delivery_zone_name: str
    delivery_cells: list[CellModel]


class ObjectView(BaseModel):
    id: str
    name: str
    category: str
    color: str
    weight_kg: float
    position: CellModel | None
    state: PackageState
    destination_zone_id: str


class ZoneView(BaseModel):
    id: str
    name: str
    kind: ZoneKind
    color: str
    cells: list[CellModel]


class MovingObstacleView(BaseModel):
    id: str
    name: str
    position: CellModel
    next_position: CellModel = Field(description="The cell the obstacle will try to enter next.")


class ObstaclesView(BaseModel):
    static: list[CellModel] = Field(description="Shelves and pallet stacks. Never passable.")
    moving: list[MovingObstacleView]


class GridView(BaseModel):
    width: int
    height: int


class ChecklistItemView(BaseModel):
    id: str
    label: str
    done: bool
    current: bool


class TaskView(BaseModel):
    name: str
    instructions: str
    progress: int = Field(ge=0, le=100, description="Percentage of task milestones reached.")
    current_objective: str
    objectives_total: int
    objectives_completed: int
    checklist: list[ChecklistItemView]


class EventView(BaseModel):
    seq: int
    episode_id: str
    step: int
    type: str
    category: str
    description: str
    entity_id: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str


class Observation(BaseModel):
    episode_id: str
    scenario_id: str
    step: int
    max_steps: int
    status: EpisodeStatus
    agent: AgentView
    target: TargetView | None = Field(description="None once every package is delivered.")
    objects: list[ObjectView]
    zones: list[ZoneView]
    obstacles: ObstaclesView
    grid: GridView
    checkpoints: list[CellModel]
    available_actions: list[Action]
    task: TaskView
    recent_events: list[EventView]
