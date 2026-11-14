"""Fixtures for the browser tests: a real server, a real Panda3D process, a real browser."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
FRONTEND_INDEX = BACKEND_DIR.parent / "frontend" / "dist" / "index.html"
STARTUP_TIMEOUT_SECONDS = 120


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def stop_process_tree(process: subprocess.Popen) -> None:
    """Stop the server and the Panda3D process it started.

    On Windows a terminated parent does not take its children with it, so the
    whole tree is ended explicitly.
    """
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(  # noqa: S603, S607  (fixed arguments)
            ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


class LiveServer:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else (b"" if method == "POST" else None)
        request = urllib.request.Request(
            f"{self.base_url}/api/v1{path}", data=data, method=method, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read())

    def wait_until_finished(self, episode_id: str, timeout: float = 90) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            episode = self.call("GET", f"/episodes/{episode_id}/")
            if episode["status"] in ("completed", "failed"):
                return episode
            time.sleep(0.25)
        raise AssertionError(f"episode {episode_id} did not finish in {timeout}s")


@pytest.fixture(scope="session")
def server(tmp_path_factory) -> LiveServer:
    if not FRONTEND_INDEX.exists():
        pytest.skip("The frontend is not built. Run 'npm run build' in frontend/ first.")
    data_dir = tmp_path_factory.mktemp("simforge-e2e")
    port = free_port()
    environment = {
        **os.environ,
        "SIMFORGE_DB": str(data_dir / "e2e.sqlite3"),
        "SIMFORGE_CACHE": str(data_dir / "cache"),
        "SIMFORGE_LOG_LEVEL": "WARNING",
    }
    process = subprocess.Popen(  # noqa: S603  (fixed argument list)
        [sys.executable, "run.py", "--port", str(port)], cwd=BACKEND_DIR, env=environment
    )
    live = LiveServer(f"http://127.0.0.1:{port}")
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
    try:
        while True:
            try:
                if live.call("GET", "/health/")["rendering"]:
                    break
            except (urllib.error.URLError, ConnectionError):
                pass
            if process.poll() is not None or time.monotonic() > deadline:
                pytest.skip("The SIMFORGE server with Panda3D rendering could not start on this machine.")
            time.sleep(0.5)
        yield live
    finally:
        stop_process_tree(process)


@pytest.fixture(scope="session")
def browser():
    playwright_api = pytest.importorskip("playwright.sync_api")
    with playwright_api.sync_playwright() as playwright:
        try:
            instance = playwright.chromium.launch()
        except playwright_api.Error as error:
            pytest.skip(f"Chromium is not installed for Playwright: {error}")
        yield instance
        instance.close()


@pytest.fixture
def page(browser, server):
    context = browser.new_context(viewport={"width": 1440, "height": 900}, base_url=server.base_url)
    context.set_default_timeout(15_000)
    new_page = context.new_page()
    yield new_page
    context.close()
