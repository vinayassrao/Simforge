"""Record the demo walkthrough of the real application as recordings/simforge_demo.mp4.

Start the server first (``python backend/run.py``), then run::

    python scripts/record_demo.py

Playwright drives the real interface and records the browser. The video is then
converted from WebM to MP4 with the ffmpeg binary bundled with imageio-ffmpeg.
The caption bar at the bottom is added by this script for the recording only;
everything else on screen is the application. There is no audio: read
recordings/narration_script.md alongside it.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import Page, sync_playwright

PROJECT_DIR = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_DIR / "recordings" / "simforge_demo.mp4"
SIZE = {"width": 1600, "height": 900}
SCENARIO_NAME = "Obstacle Navigation"

CAPTION_SCRIPT = """
window.__simforgeCaption = (text) => {
  let bar = document.getElementById('demo-caption');
  if (!bar) {
    const style = document.createElement('style');
    style.textContent = `#demo-caption { position: fixed; left: 50%; bottom: 22px; transform: translateX(-50%);
      z-index: 9999; max-width: 1100px; padding: 12px 22px; border-radius: 12px;
      font: 600 19px/1.35 'Segoe UI', sans-serif; color: #e8eef9; background: rgba(8, 13, 24, 0.92);
      border: 1px solid #22d3ee; text-align: center;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5); pointer-events: none; }`;
    document.head.appendChild(style);
    bar = document.createElement('div');
    bar.id = 'demo-caption';
    bar.setAttribute('aria-hidden', 'true');
    document.body.appendChild(bar);
  }
  bar.textContent = text;
};
"""


def caption(page: Page, text: str, seconds: float) -> None:
    """Show a caption for the recording and hold the shot."""
    page.evaluate("text => window.__simforgeCaption(text)", text)
    page.wait_for_timeout(int(seconds * 1000))


def episode_status(base_url: str, episode_id: str) -> str:
    with urllib.request.urlopen(f"{base_url}/api/v1/episodes/{episode_id}/", timeout=20) as response:
        return json.loads(response.read())["status"]


def wait_until_finished(page: Page, base_url: str, episode_id: str, timeout: float = 180) -> None:
    deadline = time.monotonic() + timeout
    while episode_status(base_url, episode_id) not in ("completed", "failed"):
        if time.monotonic() > deadline:
            raise TimeoutError("The demo episode did not finish")
        page.wait_for_timeout(400)


def scroll_to(page: Page, text: str) -> None:
    page.get_by_text(text, exact=False).first.scroll_into_view_if_needed()
    page.wait_for_timeout(600)


def walkthrough(page: Page, base_url: str) -> None:
    navigation = page.get_by_role("navigation", name="Main")

    page.goto(f"{base_url}/")
    page.get_by_role("heading", name="Welcome to SIMFORGE").wait_for()
    caption(page, "SIMFORGE: a lab for testing AI agents in a real Panda3D simulation.", 6)
    caption(
        page,
        "The dashboard is built from stored runs: scenarios, runs, successes and the average score.",
        6,
    )

    navigation.get_by_role("link", name="Scenario Library").click()
    page.get_by_role("heading", name=SCENARIO_NAME).wait_for()
    caption(
        page,
        "Three warehouse scenarios. The previews are rendered by the Panda3D engine.",
        6,
    )

    page.get_by_role("link", name=f"Open {SCENARIO_NAME}").click()
    page.get_by_role("heading", name=SCENARIO_NAME, level=1).wait_for()
    caption(
        page,
        "The task: collect the package and deliver it while forklifts patrol the aisles.",
        7,
    )
    scroll_to(page, "How success is measured")
    caption(page, "Success is measured with a transparent 100-point score.", 6)

    scroll_to(page, "Launch this scenario")
    page.get_by_label("Built-in A* agent").check()
    caption(
        page,
        "Choose who controls the robot: the built-in A* agent, yourself, or your own Python code.",
        6,
    )
    page.get_by_role("button", name="Launch simulation").click()
    page.wait_for_url("**/simulation/ep-*")
    episode_id = page.url.rsplit("/", 1)[1]
    page.get_by_alt_text("Live Panda3D render of the warehouse simulation").wait_for()

    caption(
        page,
        "This view is streamed from Panda3D: shelves, pallets, zones, forklifts and the robot.",
        6,
    )
    page.get_by_role("button", name="Legend").click()
    caption(
        page,
        "The legend explains every marking. The task and its checklist are on the right.",
        6,
    )
    page.get_by_role("button", name="Legend").click()

    page.get_by_role("button", name="Start", exact=True).click()
    caption(
        page,
        "Start. The A* agent plans a route (cyan line) and issues one real action per step.",
        9,
    )
    caption(
        page,
        "Forklifts move every few steps. The agent treats their current and next cell as blocked.",
        9,
    )

    page.get_by_role("button", name="Pause").click()
    caption(page, "Pause, then step forward to follow the agent one decision at a time.", 4)
    for _ in range(4):
        page.get_by_role("button", name="Step forward").click()
        page.wait_for_timeout(900)
    page.get_by_role("button", name="Collision shapes").click()
    page.get_by_role("button", name="Grid").click()
    caption(page, "Debug overlays: the navigation grid and the Panda3D collision solids.", 6)
    page.get_by_role("button", name="Collision shapes").click()
    page.get_by_role("button", name="Grid").click()

    page.get_by_role("button", name="Resume").click()
    page.get_by_label("Speed").select_option("2")
    caption(
        page,
        "Resume at 2x. Watch for 'Route recalculated' when a forklift blocks the plan.",
        10,
    )
    caption(
        page,
        "Pick-up and delivery are actions too, with preconditions that can fail.",
        8,
    )
    wait_until_finished(page, base_url, episode_id)
    page.get_by_text("Task succeeded").first.wait_for()
    caption(page, "Task complete. Every step was recorded and scored.", 5)

    scroll_to(page, "Live activity")
    page.get_by_role("tab", name="Task milestones").click()
    caption(page, "Live activity: every action and event, filterable by type.", 6)
    page.get_by_role("tab", name="Observation").click()
    caption(
        page,
        "What the agent sees: position, target, obstacles and the actions that are legal now.",
        6,
    )
    page.get_by_role("tab", name="Raw JSON").click()
    caption(
        page,
        "The same observation as raw JSON, exactly as an external agent receives it.",
        6,
    )
    page.get_by_role("tab", name="Performance").click()
    caption(
        page,
        "Engine figures: frame rate, step duration, action latency, collision counters.",
        6,
    )

    page.evaluate("window.scrollTo(0, 0)")
    page.get_by_role("link", name="Open evaluation report").click()
    page.get_by_role("heading", name="Performance score").wait_for()
    caption(
        page,
        "The evaluation report: success is yes or no, and the score is separate.",
        7,
    )
    caption(
        page,
        "Path efficiency compares the steps used with a baseline route for this exact world.",
        8,
    )
    scroll_to(page, "Route replay")
    slider = page.get_by_label("Replay position")
    last_step = int(slider.get_attribute("max") or "0")
    for step in range(0, last_step + 1, max(1, last_step // 14)):
        slider.fill(str(step))
        page.wait_for_timeout(280)
    slider.fill(str(last_step))
    caption(page, "The route replay and the full event log are stored with the run.", 6)

    navigation.get_by_role("link", name="Evaluations").click()
    page.get_by_role("heading", name="Score comparison").wait_for()
    caption(page, "Evaluations: charts and comparisons across every stored run.", 7)

    navigation.get_by_role("link", name="Agent Studio").click()
    page.get_by_role("heading", name="How every agent works").wait_for()
    caption(
        page,
        "Agent Studio: observation, decision, action, environment update, new observation.",
        7,
    )
    scroll_to(page, "Connect an external Python agent")
    caption(
        page,
        "An external Python agent needs four HTTP calls. No API key. Example scripts are included.",
        8,
    )

    navigation.get_by_role("link", name="API Documentation").click()
    page.get_by_text("/api/v1/episodes/{episode_id}/actions/").wait_for()
    caption(page, "The REST API is documented from the server's own OpenAPI schema.", 6)

    navigation.get_by_role("link", name="Workflows & Tutorials").click()
    page.get_by_role("heading", name="01. Environment creation", level=1).wait_for()
    caption(
        page,
        "Twelve workflow guides explain how each part was built, debugged and validated.",
        7,
    )


def convert_to_mp4(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(source),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "24", "-movflags", "+faststart", "-an", str(target),
    ]  # fmt: skip
    subprocess.run(command, check=True)  # noqa: S603  (fixed arguments)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    base_url = parser.parse_args().base_url.rstrip("/")

    video_dir = Path(tempfile.mkdtemp(prefix="simforge-video-"))
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport=SIZE, record_video_dir=str(video_dir), record_video_size=SIZE)
            context.add_init_script(CAPTION_SCRIPT)
            page = context.new_page()
            walkthrough(page, base_url)
            context.close()
            browser.close()
        convert_to_mp4(next(video_dir.glob("*.webm")), OUTPUT)
    finally:
        shutil.rmtree(video_dir, ignore_errors=True)
    print(f"Saved {OUTPUT} ({OUTPUT.stat().st_size / 1_000_000:.1f} MB)")


if __name__ == "__main__":
    main()
