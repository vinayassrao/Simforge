from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from app.api.deps import Episodes
from app.api.errors import error_response
from app.schemas import (
    ActionRequest,
    ActionResult,
    EpisodeCreate,
    EpisodeDetail,
    EpisodeOut,
    ErrorResponse,
    EvaluationReport,
    EvaluationsOut,
    EventOut,
    LiveState,
    SpeedRequest,
)
from simulation.observation import Observation

router = APIRouter(tags=["Episodes"])
NOT_FOUND = {404: {"model": ErrorResponse, "description": "The episode does not exist."}}
CONFLICT = {409: {"model": ErrorResponse, "description": "The episode is not in a state that allows this."}}
EventCategoryParam = Literal["action", "collision", "error", "milestone", "info"]


@router.post(
    "/episodes/",
    response_model=EpisodeDetail,
    status_code=201,
    responses={404: {"model": ErrorResponse, "description": "Unknown scenario."}},
    summary="Create an episode and load it into the simulation",
)
def create_episode(body: EpisodeCreate, episodes: Episodes):
    """Only one episode is live at a time. Creating a new one aborts an unfinished one."""
    return episodes.create(body.scenario_id, body.agent_mode, body.seed)


@router.get("/episodes/", response_model=list[EpisodeOut], summary="List episodes, newest first")
def list_episodes(
    episodes: Episodes,
    scenario_id: str | None = None,
    agent_mode: str | None = None,
    status: str | None = None,
    min_score: Annotated[float | None, Query(ge=0, le=100)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    return episodes.list(scenario_id, agent_mode, status, min_score, limit)


@router.get("/episodes/{episode_id}/", response_model=EpisodeDetail, responses=NOT_FOUND, summary="Get one episode")
def read_episode(episode_id: str, episodes: Episodes):
    return episodes.get(episode_id)


def _control(name: str, summary: str, description: str):
    @router.post(
        f"/episodes/{{episode_id}}/{name}/",
        response_model=LiveState,
        responses={**NOT_FOUND, **CONFLICT},
        summary=summary,
        description=description,
        name=f"{name}_episode",
    )
    def control(episode_id: str, episodes: Episodes):
        if name == "reset":
            return episodes.reset(episode_id)
        return episodes.command(episode_id, name)

    return control


_control("start", "Start the episode", "The robot leaves the idle state and the clock starts.")
_control("pause", "Pause a running episode", "Actions are rejected while paused.")
_control("resume", "Resume a paused episode", "Continues from exactly where it was paused.")
_control("reset", "Reset the episode to its starting state", "Rebuilds the world from the same seed.")


@router.post(
    "/episodes/{episode_id}/step/",
    response_model=ActionResult,
    responses={**NOT_FOUND, **CONFLICT},
    summary="Advance exactly one step",
)
def step_episode(episode_id: str, episodes: Episodes):
    """The built-in agent makes one decision. In manual and external mode the robot waits."""
    return episodes.command(episode_id, "step")


@router.post(
    "/episodes/{episode_id}/speed/",
    responses={**NOT_FOUND, 422: {"model": ErrorResponse}},
    summary="Set the playback speed of the built-in agent",
)
def set_speed(episode_id: str, body: SpeedRequest, episodes: Episodes):
    return episodes.command(episode_id, "set_speed", speed=body.speed)


@router.get(
    "/episodes/{episode_id}/observation/",
    response_model=Observation,
    responses={**NOT_FOUND, **CONFLICT},
    tags=["Agent interaction"],
    summary="What the agent currently sees",
)
def read_observation(episode_id: str, episodes: Episodes):
    return episodes.command(episode_id, "observation")


@router.post(
    "/episodes/{episode_id}/actions/",
    response_model=ActionResult,
    responses={**NOT_FOUND, **CONFLICT, 422: {"model": ErrorResponse}},
    tags=["Agent interaction"],
    summary="Submit one action for the robot",
)
def submit_action(episode_id: str, body: ActionRequest, episodes: Episodes):
    """A rejected action still returns 200 with ``success: false`` and the reason, and it uses one step."""
    return episodes.command(episode_id, "action", action=body.action.value)


@router.get(
    "/episodes/{episode_id}/state/",
    response_model=LiveState,
    responses={**NOT_FOUND, **CONFLICT},
    summary="The full live snapshot of the active episode",
)
def read_state(episode_id: str, episodes: Episodes):
    episodes.get(episode_id)
    state = episodes.live_state(episode_id)
    if state is None:
        return error_response(409, "episode_not_active", "This episode is not loaded in the simulation.")
    return state


@router.get(
    "/episodes/{episode_id}/events/",
    response_model=list[EventOut],
    responses=NOT_FOUND,
    tags=["Events"],
    summary="The recorded events of an episode",
)
def read_events(
    episode_id: str,
    episodes: Episodes,
    category: EventCategoryParam | None = None,
    after_seq: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=5000)] = 2000,
):
    return episodes.events(episode_id, category, after_seq, limit)


@router.get(
    "/episodes/{episode_id}/evaluation/",
    response_model=EvaluationReport,
    responses={**NOT_FOUND, 409: {"model": ErrorResponse, "description": "The episode has not finished."}},
    tags=["Evaluation"],
    summary="The evaluation report of a finished episode",
)
def read_evaluation(episode_id: str, episodes: Episodes):
    report = episodes.evaluation(episode_id)
    if report is None:
        return error_response(409, "not_evaluated", "This episode has no evaluation yet; it has not finished.")
    return report


@router.get(
    "/evaluations/",
    response_model=EvaluationsOut,
    tags=["Evaluation"],
    summary="All evaluated episodes with aggregate statistics",
)
def read_evaluations(episodes: Episodes):
    return episodes.evaluations()


@router.get(
    "/episodes/{episode_id}/export/",
    responses=NOT_FOUND,
    summary="Download an episode as JSON (everything) or CSV (events)",
)
def export_episode(episode_id: str, episodes: Episodes, format: Literal["json", "csv"] = "json"):
    if format == "csv":
        return PlainTextResponse(
            episodes.export_csv(episode_id),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{episode_id}-events.csv"'},
        )
    return JSONResponse(
        episodes.export_json(episode_id),
        headers={"Content-Disposition": f'attachment; filename="{episode_id}.json"'},
    )
