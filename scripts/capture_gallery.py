"""Capture the six portfolio screenshots from the real, running application.

Start the server first (``python backend/run.py``), then run::

    python scripts/capture_gallery.py

Nothing is mocked. The script launches real episodes through the interface and
the API, waits for the simulation to produce the state being photographed, and
saves 1600 x 900 PNG files to ``gallery/``. Screenshot 03 is written by the
Panda3D engine itself, straight from its frame buffer.
"""

from __future__ import annotations

import argparse
import json
import queue
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

PROJECT_DIR = Path(__file__).resolve().parent.parent
GALLERY_DIR = PROJECT_DIR / "gallery"
VIEWPORT = {"width": 1600, "height": 900}
RENDER_SIZE = (1600, 900)
RENDER_SCENARIO = "obstacle-navigation"
RENDER_STEPS = 34


class Api:
    def __init__(self, base_url: str) -> None:
        self.base = base_url.rstrip("/") + "/api/v1"

    def call(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else (b"" if method == "POST" else None)
        request = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read())

    def run_to_completion(self, scenario: str, seed: int) -> str:
        episode = self.call(
            "POST",
            "/episodes/",
            {"scenario_id": scenario, "agent_mode": "astar", "seed": seed},
        )
        self.call("POST", f"/episodes/{episode['id']}/start/")
        self.call("POST", f"/episodes/{episode['id']}/speed/", {"speed": 4})
        self.wait_for(episode["id"], lambda item: item["status"] in ("completed", "failed"))
        return episode["id"]

    def wait_for(self, episode_id: str, condition, timeout: float = 120) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            episode = self.call("GET", f"/episodes/{episode_id}/")
            if condition(episode):
                return episode
            time.sleep(0.2)
        raise TimeoutError(f"Episode {episode_id} did not reach the expected state")


def run_manual_with_mistakes(api: Api) -> str:
    """A manual run that hits the wall until the safety limit fails it. Gives the history a failed run."""
    episode = api.call("POST", "/episodes/", {"scenario_id": "basic-delivery", "agent_mode": "manual"})
    api.call("POST", f"/episodes/{episode['id']}/start/")
    for action in ("MOVE_FORWARD", "MOVE_FORWARD", "PICK_UP", "TURN_RIGHT"):
        api.call("POST", f"/episodes/{episode['id']}/actions/", {"action": action})
    done = False
    while not done:
        done = api.call("POST", f"/episodes/{episode['id']}/actions/", {"action": "MOVE_FORWARD"})["done"]
    return episode["id"]


def capture_panda_render(target: Path) -> None:
    """Render the warehouse in a dedicated off-screen Panda3D engine and save its frame buffer."""
    sys.path.insert(0, str(PROJECT_DIR / "backend"))
    from simulation.engine import EngineConfig, SimulationEngine

    commands: queue.Queue = queue.Queue()
    engine = SimulationEngine(
        commands,
        queue.Queue(),
        None,
        EngineConfig(width=RENDER_SIZE[0], height=RENDER_SIZE[1]),
    )
    commands.put(
        {
            "type": "load",
            "episode_id": "gallery",
            "scenario_id": RENDER_SCENARIO,
            "agent_mode": "astar",
        }
    )
    commands.put({"type": "start"})
    commands.put({"type": "pause"})
    for _ in range(RENDER_STEPS):
        commands.put({"type": "step"})
    for _ in range(60):
        engine.base.taskMgr.step()
    commands.put({"type": "screenshot", "path": str(target)})
    engine.base.taskMgr.step()


def settle(page: Page, milliseconds: int = 900) -> None:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(milliseconds)


def capture_browser_screens(base_url: str, api: Api) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT)

        page.goto(f"{base_url}/")
        page.get_by_role("heading", name="Welcome to SIMFORGE").wait_for()
        settle(page)
        page.screenshot(path=GALLERY_DIR / "01_simforge_dashboard.png")

        page.goto(f"{base_url}/scenarios")
        page.get_by_role("heading", name="Multi-Step Delivery").wait_for()
        settle(page)
        page.screenshot(path=GALLERY_DIR / "02_scenario_library.png")

        # 04: launch through the interface and photograph the agent mid-run.
        page.goto(f"{base_url}/scenarios/multi-step-delivery")
        page.get_by_label("Built-in A* agent").check()
        page.get_by_role("button", name="Launch simulation").click()
        page.wait_for_url("**/simulation/ep-*")
        episode_id = page.url.rsplit("/", 1)[1]
        page.get_by_role("button", name="Start", exact=True).click()
        api.wait_for(episode_id, lambda item: item["progress"] >= 50)
        page.wait_for_timeout(1500)
        page.screenshot(path=GALLERY_DIR / "04_agent_execution.png")
        api.call("POST", f"/episodes/{episode_id}/speed/", {"speed": 4})
        api.wait_for(episode_id, lambda item: item["status"] in ("completed", "failed"))

        # 05: the evaluation report of a run with re-planning, so the efficiency line is informative.
        report_episode = api.run_to_completion("obstacle-navigation", seed=7)
        page.goto(f"{base_url}/evaluations/{report_episode}")
        page.get_by_role("heading", name="Performance score").wait_for()
        settle(page)
        page.screenshot(path=GALLERY_DIR / "05_evaluation_report.png")

        page.goto(f"{base_url}/agents")
        page.get_by_role("heading", name="How every agent works").wait_for()
        settle(page)
        page.screenshot(path=GALLERY_DIR / "06_agent_studio_and_api.png")
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    base_url = parser.parse_args().base_url.rstrip("/")
    GALLERY_DIR.mkdir(exist_ok=True)
    api = Api(base_url)

    # Give the dashboard and charts real history: clean runs, a run with re-planning, and a failed run.
    api.run_to_completion("basic-delivery", seed=7)
    run_manual_with_mistakes(api)
    api.run_to_completion("multi-step-delivery", seed=3)

    capture_browser_screens(base_url, api)
    capture_panda_render(GALLERY_DIR / "03_live_panda3d_simulation.png")
    for image in sorted(GALLERY_DIR.glob("*.png")):
        print(f"Saved {image}")


if __name__ == "__main__":
    main()
