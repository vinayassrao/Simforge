"""End-to-end tests: the browser against the real server and the real Panda3D simulation."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.e2e


def launch(page: Page, scenario_name: str, agent_label: str) -> str:
    """Pick a scenario and an agent in the interface and return the new episode id."""
    page.goto("/scenarios")
    page.get_by_role("link", name=f"Open {scenario_name}").click()
    expect(page.get_by_role("heading", name=scenario_name, level=1)).to_be_visible()
    page.get_by_label(agent_label).check()
    page.get_by_role("button", name="Launch simulation").click()
    page.wait_for_url(re.compile(r"/simulation/ep-[0-9a-f]{8}$"))
    return page.url.rsplit("/", 1)[1]


def stat(page: Page, label: str):
    """The value shown under a small labelled figure in the agent panel."""
    return page.locator("dt", has_text=re.compile(f"^{re.escape(label)}$")).first.locator("xpath=following-sibling::dd")


def test_dashboard_loads_with_figures_from_the_server(page: Page, server):
    overview = server.call("GET", "/overview/")

    page.goto("/")

    expect(page.get_by_role("heading", name="Welcome to SIMFORGE")).to_be_visible()
    expect(page.get_by_text("Your workspace for building, testing and evaluating intelligent agents.")).to_be_visible()
    figures = page.get_by_role("region", name="Key figures")
    expect(figures.get_by_text("Available scenarios")).to_be_visible()
    expect(figures.locator("p.text-2xl").first).to_have_text(str(overview["scenarios"]))
    expect(page.get_by_role("heading", name="Basic Delivery")).to_be_visible()
    thumbnail = page.get_by_alt_text("Panda3D render of the Basic Delivery warehouse")
    expect(thumbnail).to_be_visible()
    assert thumbnail.evaluate("image => image.naturalWidth") > 100, "the Panda3D thumbnail did not load"


def test_sidebar_navigation_reaches_every_page(page: Page):
    page.goto("/")
    destinations = {
        "Scenario Library": "Scenario Library",
        "Agent Studio": "Agent Studio",
        "Evaluations": "Evaluations",
        "Run History": "Run History",
        "API Documentation": "API Documentation",
        "Workflows & Tutorials": "Workflows & Tutorials",
        "Overview": "Welcome to SIMFORGE",
    }
    navigation = page.get_by_role("navigation", name="Main")

    for link_name, heading in destinations.items():
        link = navigation.get_by_role("link", name=re.compile(f"^{re.escape(link_name)}"))
        link.click()
        expect(page.get_by_role("heading", name=heading, level=1)).to_be_visible()
        expect(link).to_have_attribute("aria-current", "page")


def test_scenario_search_and_detail_explain_the_task(page: Page):
    page.goto("/scenarios")
    expect(page.get_by_role("heading", name="Multi-Step Delivery")).to_be_visible()

    page.get_by_label("Search").fill("forklifts patrol")
    expect(page.get_by_role("heading", name="Obstacle Navigation")).to_be_visible()
    expect(page.get_by_role("heading", name="Basic Delivery")).to_have_count(0)

    page.get_by_role("link", name="Open Obstacle Navigation").click()
    expect(page.get_by_text("Collect the assigned package and deliver it while avoiding moving")).to_be_visible()
    expect(page.get_by_text("How success is measured")).to_be_visible()
    expect(page.get_by_text("50 pts")).to_be_visible()


def test_manual_controls_drive_the_robot_and_updates_arrive_live(page: Page):
    launch(page, "Basic Delivery", "Manual control")
    expect(page.get_by_text("Live connection")).to_be_visible()
    stream = page.get_by_alt_text("Live Panda3D render of the warehouse simulation")
    expect(stream).to_be_visible()
    expect(stat(page, "Position (x, y)")).to_have_text("(0, 0)")
    forward = page.get_by_role("button", name=re.compile("^Forward"))
    expect(forward).to_be_disabled()

    page.get_by_role("button", name="Start", exact=True).click()
    expect(page.get_by_text("Running", exact=True)).to_be_visible()
    forward.click()
    expect(stat(page, "Position (x, y)")).to_have_text("(1, 0)")

    page.keyboard.press("ArrowUp")
    page.keyboard.press("a")
    expect(stat(page, "Position (x, y)")).to_have_text("(2, 0)")
    expect(stat(page, "Facing")).to_have_text("North")

    page.get_by_role("button", name=re.compile("^Pick up")).click()
    expect(page.get_by_role("status").filter(has_text="Pick-up failed")).to_be_visible()
    page.get_by_role("tab", name=re.compile("^Errors")).click()
    failed_events = page.get_by_role("listitem").filter(has_text="There is no package directly in front of the robot")
    expect(failed_events).to_have_count(1)


def test_pause_step_and_reset_control_the_built_in_agent(page: Page):
    launch(page, "Obstacle Navigation", "Built-in A* agent")
    steps = stat(page, "Steps")
    expect(steps).to_have_text("0 / 220")

    page.get_by_role("button", name="Start", exact=True).click()
    page.get_by_role("button", name="Pause").click()
    expect(page.get_by_text("Paused", exact=True)).to_be_visible()
    paused_at = int(steps.inner_text().split(" / ")[0])

    page.get_by_role("button", name="Step forward").click()
    expect(steps).to_have_text(f"{paused_at + 1} / 220")
    page.wait_for_timeout(700)
    expect(steps).to_have_text(f"{paused_at + 1} / 220")

    page.get_by_role("button", name="Reset", exact=True).click()
    expect(steps).to_have_text("0 / 220")
    expect(page.get_by_text("Ready", exact=True)).to_be_visible()


def test_observation_panel_shows_the_real_observation(page: Page, server):
    episode_id = launch(page, "Basic Delivery", "Manual control")
    page.get_by_role("button", name="Start", exact=True).click()
    expect(page.get_by_text("Running", exact=True)).to_be_visible()

    page.get_by_role("tab", name="Observation").click()
    expect(page.get_by_role("heading", name="What the agent currently sees")).to_be_visible()
    page.get_by_role("tab", name="Raw JSON").click()

    observation = server.call("GET", f"/episodes/{episode_id}/observation/")
    code = page.locator("pre code")
    expect(code).to_contain_text(f'"episode_id": "{episode_id}"')
    expect(code).to_contain_text(f'"object_id": "{observation["target"]["object_id"]}"')


def test_finished_run_shows_its_evaluation_report(page: Page, server):
    episode_id = launch(page, "Basic Delivery", "Built-in A* agent")
    page.get_by_role("button", name="Start", exact=True).click()
    page.get_by_label("Speed").select_option("4")
    episode = server.wait_until_finished(episode_id)
    report = server.call("GET", f"/episodes/{episode_id}/evaluation/")

    expect(page.get_by_text("Task succeeded")).to_be_visible()
    expect(page.get_by_text("Deliver the blue package")).to_be_visible()
    page.get_by_role("link", name="Open evaluation report").click()

    expect(page.get_by_role("heading", name="Basic Delivery", level=1)).to_be_visible()
    expect(page.get_by_role("img", name=f"Score {report['score']:.1f} out of 100")).to_be_visible()
    expect(page.get_by_text(f"completed the task in {report['metrics']['steps']} steps")).to_be_visible()
    expect(page.get_by_text("50.0 / 50")).to_be_visible()
    expect(page.get_by_text("Task completed in")).to_be_visible()
    assert episode["score"] == report["score"]

    page.goto("/evaluations")
    expect(page.get_by_role("heading", name="Score comparison")).to_be_visible()
    expect(page.get_by_role("link", name=episode_id)).to_be_visible()
    page.goto("/history")
    expect(page.get_by_role("cell", name=re.compile(episode_id))).to_be_visible()


def test_agent_studio_and_api_pages_use_live_server_data(page: Page):
    page.goto("/agents")
    expect(page.get_by_role("heading", name="Built-in A* agent")).to_be_visible()
    expect(page.get_by_role("rowheader", name="PICK_UP")).to_be_visible()
    expect(page.get_by_text("examples/agents/baseline_agent.py").first).to_be_visible()

    page.goto("/api-docs")
    expect(page.get_by_text("/api/v1/episodes/{episode_id}/actions/")).to_be_visible()
    expect(page.get_by_role("link", name="Open Swagger UI")).to_have_attribute("href", "/api/docs")

    page.goto("/workflows")
    expect(page.get_by_role("heading", name="01. Environment creation", level=1)).to_be_visible()
    page.get_by_role("link", name="10. Evaluation engine").click()
    expect(page.get_by_role("heading", name="10. Evaluation engine", level=1)).to_be_visible()


def test_layout_has_no_horizontal_scroll_on_a_phone(browser, server):
    context = browser.new_context(viewport={"width": 390, "height": 800}, base_url=server.base_url)
    phone = context.new_page()
    try:
        for path in ("/", "/scenarios", "/agents", "/evaluations", "/simulation"):
            phone.goto(path)
            phone.wait_for_load_state("networkidle")
            widths = phone.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
            assert widths[0] <= widths[1], f"{path} scrolls horizontally: {widths}"
        phone.goto("/")
        phone.get_by_role("button", name="Open navigation").click()
        drawer = phone.get_by_role("dialog", name="Navigation")
        drawer.get_by_role("link", name=re.compile("^Agent Studio")).click()
        expect(phone.get_by_role("heading", name="Agent Studio", level=1)).to_be_visible()
        expect(drawer).to_have_count(0)
    finally:
        context.close()
