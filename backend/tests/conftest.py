from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.gateway import InlineGateway


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Settings that keep every test in its own temporary database, without rendering."""
    return replace(
        Settings(),
        database_path=tmp_path / "simforge.sqlite3",
        cache_dir=tmp_path / "cache",
        frontend_dist=tmp_path / "dist",
        simulation_backend="inline",
        log_level="WARNING",
    )


@pytest.fixture
def client(settings: Settings):
    """A test client wired to the real API, database and simulation rules."""
    with TestClient(create_app(settings, InlineGateway())) as test_client:
        yield test_client
