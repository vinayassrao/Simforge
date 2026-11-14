"""Application settings, read from environment variables with local defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


def _path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name, default)).resolve()


@dataclass(frozen=True)
class Settings:
    database_path: Path = field(default_factory=lambda: _path("SIMFORGE_DB", PROJECT_DIR / "data" / "simforge.sqlite3"))
    cache_dir: Path = field(default_factory=lambda: _path("SIMFORGE_CACHE", PROJECT_DIR / "data" / "cache"))
    frontend_dist: Path = field(default_factory=lambda: _path("SIMFORGE_FRONTEND", PROJECT_DIR / "frontend" / "dist"))
    docs_dir: Path = PROJECT_DIR / "docs"
    examples_dir: Path = PROJECT_DIR / "examples"
    simulation_backend: str = field(default_factory=lambda: os.environ.get("SIMFORGE_SIMULATION", "process"))
    render_width: int = field(default_factory=lambda: int(os.environ.get("SIMFORGE_RENDER_WIDTH", "960")))
    render_height: int = field(default_factory=lambda: int(os.environ.get("SIMFORGE_RENDER_HEIGHT", "540")))
    log_level: str = field(default_factory=lambda: os.environ.get("SIMFORGE_LOG_LEVEL", "INFO"))
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")

    @property
    def thumbnail_dir(self) -> Path:
        return self.cache_dir / "thumbnails"

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"
