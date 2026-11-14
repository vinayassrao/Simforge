"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api import catalog, episodes, scenarios, simulation
from app.api.errors import error_response, register_error_handlers
from app.config import Settings
from app.database import Database
from app.services.episodes import EpisodeService
from app.services.gateway import InlineGateway, ProcessGateway, SimulationGateway
from app.websocket import ConnectionManager

API_PREFIX = "/api/v1"
DESCRIPTION = """
SIMFORGE runs warehouse robot simulations in Panda3D and lets agents act in them.

**The agent loop:** read `GET /episodes/{id}/observation/`, choose an action, send it to
`POST /episodes/{id}/actions/`, and repeat until the response says `done`.
Live updates are pushed over the WebSocket `/ws/episodes/{id}/`.
"""


def build_gateway(settings: Settings) -> SimulationGateway:
    if settings.simulation_backend == "inline":
        return InlineGateway()
    return ProcessGateway(settings.render_width, settings.render_height, settings.thumbnail_dir, settings.log_level)


def create_app(settings: Settings | None = None, gateway: SimulationGateway | None = None) -> FastAPI:
    settings = settings or Settings()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    database = Database(settings.database_url)
    gateway = gateway or build_gateway(settings)
    connections = ConnectionManager()
    episode_service = EpisodeService(database, gateway, connections.publish)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        database.create_tables()
        connections.bind_loop(asyncio.get_running_loop())
        await asyncio.to_thread(gateway.start)
        episode_service.startup()
        yield
        await asyncio.to_thread(gateway.stop)
        database.dispose()

    app = FastAPI(
        title="SIMFORGE API",
        version="1.0.0",
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    app.state.settings = settings
    app.state.database = database
    app.state.gateway = gateway
    app.state.connections = connections
    app.state.episodes = episode_service

    app.add_middleware(
        CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"]
    )
    register_error_handlers(app)

    api = APIRouter(prefix=API_PREFIX)
    for module in (simulation, scenarios, episodes, catalog):
        api.include_router(module.router)
    app.include_router(api)
    app.include_router(simulation.ws_router)
    _serve_frontend(app, settings)
    return app


def _serve_frontend(app: FastAPI, settings: Settings) -> None:
    """Serve the built single-page app, if it has been built."""
    dist = settings.frontend_dist
    index = dist / "index.html"

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith(("api/", "ws/")):
            return error_response(404, "not_found", f"No such endpoint: /{path}")
        if not index.exists():
            return error_response(
                404,
                "frontend_not_built",
                "The web interface has not been built. Run 'npm run build' in frontend/.",
            )
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist):
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})
