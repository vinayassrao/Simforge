"""Uniform JSON errors: every failure is ``{"error": {"code", "message", "details"}}``."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.episodes import EpisodeNotFoundError
from app.services.gateway import SimulationError, SimulationUnavailableError
from simulation.scenarios import UnknownScenarioError

SIMULATION_ERROR_STATUS = {
    "unknown_scenario": 404,
    "unknown_action": 422,
    "invalid_speed": 422,
    "invalid_camera": 422,
    "episode_not_active": 409,
    "no_active_episode": 409,
    "invalid_state": 409,
    "agent_controlled": 409,
}


def error_response(status: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message, "details": details}}, status_code=status)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(EpisodeNotFoundError)
    async def episode_not_found(_request: Request, error: EpisodeNotFoundError) -> JSONResponse:
        return error_response(404, "episode_not_found", str(error))

    @app.exception_handler(UnknownScenarioError)
    async def scenario_not_found(_request: Request, error: UnknownScenarioError) -> JSONResponse:
        return error_response(404, "unknown_scenario", f"Scenario '{error.args[0]}' does not exist.")

    @app.exception_handler(SimulationError)
    async def simulation_error(_request: Request, error: SimulationError) -> JSONResponse:
        return error_response(SIMULATION_ERROR_STATUS.get(error.code, 400), error.code, error.message)

    @app.exception_handler(SimulationUnavailableError)
    async def simulation_unavailable(_request: Request, error: SimulationUnavailableError) -> JSONResponse:
        return error_response(503, "simulation_unavailable", str(error))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(part) for part in item["loc"][1:]), "message": item["msg"]}
            for item in error.errors()
        ]
        return error_response(422, "validation_error", "The request data is invalid.", details)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, error: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(error.status_code, "http_error")
        return error_response(error.status_code, code, str(error.detail))
