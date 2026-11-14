"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings
from app.services.episodes import EpisodeService
from app.services.gateway import SimulationGateway


def get_episodes(request: Request) -> EpisodeService:
    return request.app.state.episodes


def get_gateway(request: Request) -> SimulationGateway:
    return request.app.state.gateway


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


Episodes = Annotated[EpisodeService, Depends(get_episodes)]
Gateway = Annotated[SimulationGateway, Depends(get_gateway)]
AppSettings = Annotated[Settings, Depends(get_settings)]
