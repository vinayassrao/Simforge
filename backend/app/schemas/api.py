"""Request and response schemas for the REST API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from simulation.observation import EventView, Observation
from simulation.types import Action, AgentMode


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthOut(BaseModel):
    status: Literal["ok"]
    simulation: Literal["process", "inline"]
    rendering: bool
    active_episode_id: str | None
    performance: dict[str, Any]


class ScenarioOut(BaseModel):
    id: str
    name: str
    summary: str
    description: str
    instructions: str
    difficulty: str
    task_type: str
    complexity: str
    estimated_minutes: int
    objectives: int
    moving_obstacles: int
    static_obstacles: int
    grid: dict[str, int]
    max_steps: int
    default_seed: int
    available_agents: list[str]
    thumbnail_url: str


class ScenarioDetail(ScenarioOut):
    max_collisions: int
    time_limit_s: float | None
    completion_conditions: list[str]
    failure_conditions: list[str]
    evaluation_criteria: list[dict[str, Any]]
    packages: list[dict[str, Any]]
    layout: dict[str, Any]


class EpisodeCreate(BaseModel):
    scenario_id: str = Field(examples=["basic-delivery"])
    agent_mode: AgentMode = Field(default=AgentMode.MANUAL, description="manual, astar or external.")
    seed: int | None = Field(default=None, ge=0, le=2**31 - 1, description="Omit to use the scenario default.")


class EpisodeOut(BaseModel):
    id: str
    scenario_id: str
    scenario_name: str
    agent_mode: str
    seed: int
    status: str
    created_at: str | None
    started_at: str | None
    finished_at: str | None
    steps: int
    progress: int
    collisions: int
    invalid_actions: int
    elapsed_seconds: float
    score: float | None
    success: bool | None
    failure_reason: str | None


class EpisodeDetail(EpisodeOut):
    is_active: bool
    trajectory: list[Any]
    incidents: list[Any]


class LiveState(BaseModel):
    """The live snapshot of the active episode."""

    episode_id: str
    scenario_id: str
    seed: int
    mode: str
    status: str
    speed: float
    observation: Observation
    planned_path: list[list[int]]
    incidents: list[dict[str, Any]]
    metrics: dict[str, Any]


class ActionRequest(BaseModel):
    action: Action = Field(examples=["MOVE_FORWARD"])


class ActionResult(BaseModel):
    action: Action
    success: bool
    message: str
    error_code: str | None
    done: bool
    observation: Observation


class SpeedRequest(BaseModel):
    speed: float = Field(examples=[1.0], description="One of 0.25, 0.5, 1, 2 or 4.")


class ViewRequest(BaseModel):
    grid: bool | None = None
    paths: bool | None = None
    collisions: bool | None = None
    labels: bool | None = None
    collision_shapes: bool | None = None


class CameraRequest(BaseModel):
    action: Literal["reset", "zoom_in", "zoom_out", "preset"]
    preset: Literal["perspective", "isometric", "top"] | None = None


class NativeViewerRequest(BaseModel):
    scenario_id: str = "basic-delivery"
    agent_mode: Literal["manual", "astar"] = "astar"
    seed: int | None = None


class EventOut(EventView):
    pass


class BreakdownItem(BaseModel):
    key: str
    label: str
    points: float
    max_points: float
    rule: str
    explanation: str


class EvaluationReport(BaseModel):
    episode_id: str
    score: float
    max_score: float
    success: bool
    failure_reason: str | None
    failure_explanation: str | None
    breakdown: list[BreakdownItem]
    metrics: dict[str, Any]
    behaviour_summary: str
    recommendations: list[str]
    incident_locations: list[dict[str, Any]]


class EvaluationsOut(BaseModel):
    summary: dict[str, Any]
    items: list[dict[str, Any]]


class OverviewOut(BaseModel):
    scenarios: int
    total_runs: int
    successful_runs: int
    average_score: float | None
    recent_episodes: list[EpisodeOut]
    recent_events: list[EventOut]
    active_episode_id: str | None
