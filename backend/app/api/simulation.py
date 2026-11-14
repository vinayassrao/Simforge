from __future__ import annotations

import asyncio
import logging
import subprocess
import sys

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response, StreamingResponse

from app.api.deps import AppSettings, Episodes, Gateway
from app.api.errors import error_response
from app.config import BACKEND_DIR
from app.schemas import CameraRequest, ErrorResponse, HealthOut, NativeViewerRequest, OverviewOut, ViewRequest
from app.services.episodes import EpisodeNotFoundError
from app.services.gateway import SimulationError, SimulationUnavailableError
from simulation.scenarios import get_scenario

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Simulation"])
ws_router = APIRouter()
STREAM_BOUNDARY = "simforge-frame"
STREAM_POLL_SECONDS = 0.04


@router.get("/health/", response_model=HealthOut, tags=["Health"], summary="Service and simulation status")
def health(episodes: Episodes, gateway: Gateway, settings: AppSettings):
    return {
        "status": "ok",
        "simulation": settings.simulation_backend if gateway.renders_frames else "inline",
        "rendering": gateway.renders_frames,
        "active_episode_id": episodes.active_episode_id,
        "performance": gateway.perf,
    }


@router.get("/overview/", response_model=OverviewOut, summary="Dashboard figures from stored runs")
def overview(episodes: Episodes):
    return episodes.overview()


@router.post("/simulation/view/", summary="Toggle overlays in the 3D view")
def set_view(body: ViewRequest, gateway: Gateway):
    return gateway.request({"type": "set_view", **body.model_dump(exclude_none=True)})


@router.post("/simulation/camera/", summary="Move the 3D camera")
def move_camera(body: CameraRequest, gateway: Gateway):
    return gateway.request({"type": "camera", **body.model_dump(exclude_none=True)})


@router.get(
    "/simulation/frame/",
    responses={200: {"content": {"image/jpeg": {}}}, 503: {"model": ErrorResponse}},
    summary="The latest frame rendered by Panda3D",
)
def latest_frame(gateway: Gateway):
    frame = gateway.latest_frame()
    if frame is None:
        return error_response(503, "rendering_unavailable", "No rendered frame is available.")
    return Response(frame[1], media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.get(
    "/simulation/stream/",
    responses={200: {"content": {"multipart/x-mixed-replace": {}}}, 503: {"model": ErrorResponse}},
    summary="Live MJPEG stream of the Panda3D render",
)
async def stream(request: Request, gateway: Gateway):
    if not gateway.renders_frames:
        return error_response(503, "rendering_unavailable", "This server runs the simulation without rendering.")

    async def frames():
        last_sequence = -1
        while not await request.is_disconnected():
            frame = gateway.latest_frame()
            if frame is not None and frame[0] != last_sequence:
                last_sequence = frame[0]
                header = f"--{STREAM_BOUNDARY}\r\nContent-Type: image/jpeg\r\nContent-Length: {len(frame[1])}\r\n\r\n"
                yield header.encode() + frame[1] + b"\r\n"
            await asyncio.sleep(STREAM_POLL_SECONDS)

    return StreamingResponse(
        frames(),
        media_type=f"multipart/x-mixed-replace; boundary={STREAM_BOUNDARY}",
        headers={"Cache-Control": "no-store"},
    )


@router.post(
    "/simulation/native-viewer/",
    status_code=202,
    summary="Open the native Panda3D viewer window on the server machine",
)
def launch_native_viewer(body: NativeViewerRequest):
    """Starts a separate Panda3D window running the same engine. Local use only."""
    scenario = get_scenario(body.scenario_id)
    command = [
        sys.executable,
        "-m",
        "simulation.panda_viewer",
        "--scenario",
        scenario.id,
        "--agent",
        body.agent_mode,
    ]
    if body.seed is not None:
        command += ["--seed", str(body.seed)]
    process = subprocess.Popen(command, cwd=BACKEND_DIR)  # noqa: S603  (fixed argument list)
    logger.info("Launched native viewer (pid %s) for %s", process.pid, scenario.id)
    return {"launched": True, "pid": process.pid, "command": "python -m simulation.panda_viewer"}


@ws_router.websocket("/ws/episodes/{episode_id}/")
async def episode_socket(websocket: WebSocket, episode_id: str) -> None:
    """Pushes state, events, performance and the final evaluation for one episode."""
    app = websocket.app
    episodes = app.state.episodes
    manager = app.state.connections
    try:
        episode = await asyncio.to_thread(episodes.get, episode_id)
    except EpisodeNotFoundError:
        await websocket.accept()
        await websocket.close(code=4404, reason="Episode not found")
        return
    await manager.connect(episode_id, websocket)
    try:
        try:
            state = await asyncio.to_thread(episodes.live_state, episode_id)
        except (SimulationError, SimulationUnavailableError):
            state = None
        await websocket.send_json({"type": "hello", "episode": episode, "state": state})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(episode_id, websocket)
