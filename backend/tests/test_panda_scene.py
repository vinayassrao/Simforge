"""Tests that exercise real Panda3D objects.

The scene-graph tests need no window. The engine tests render off-screen and are
skipped automatically where no graphics pipe is available.
"""

from __future__ import annotations

import queue

import pytest
from panda3d.core import NodePath

from simulation.controller import SimulationController
from simulation.geometry import hex_color, make_box, make_cylinder, make_floor_texture, make_hazard_texture
from simulation.scene import WarehouseScene
from simulation.types import Orientation

pytestmark = pytest.mark.panda


def loaded_state(scenario: str = "obstacle-navigation", mode: str = "astar"):
    controller = SimulationController()
    controller.handle({"type": "load", "episode_id": "scene", "scenario_id": scenario, "agent_mode": mode})
    controller.handle({"type": "start"})
    return controller


@pytest.fixture
def scene():
    return WarehouseScene(NodePath("render"))


class TestGeometry:
    def test_box_has_the_requested_size_and_sits_on_the_floor(self):
        box = make_box(2, 4, 6, hex_color("#ff0000"))
        low, high = box.getTightBounds()

        assert tuple(round(v, 3) for v in low) == (-1, -2, 0)
        assert tuple(round(v, 3) for v in high) == (1, 2, 6)
        assert box.node().getGeom(0).getPrimitive(0).getNumFaces() == 12

    def test_cylinder_is_bounded_by_its_radius_and_height(self):
        low, high = make_cylinder(0.5, 2, hex_color("#00ff00"), segments=24).getTightBounds()

        assert round(high.z - low.z, 3) == 2
        assert round(high.x, 2) == 0.5 and round(low.y, 2) == -0.5

    def test_hex_colours_and_procedural_textures(self):
        assert hex_color("#3366ff", 0.5) == (0.2, 0.4, 1.0, 0.5)
        assert make_floor_texture(64).getXSize() == 64
        assert make_hazard_texture(32).getNumComponents() == 4


class TestSceneGraph:
    def test_build_creates_every_entity_of_the_scenario(self, scene):
        controller = loaded_state()

        scene.build(controller.snapshot())

        root = scene.root
        scenario = controller.env.scenario
        assert root.findAllMatches("**/shelf-*;+h").getNumPaths() >= len(scenario.shelves)
        assert root.findAllMatches("**/pallet-*;+h").getNumPaths() >= len(scenario.static_obstacles)
        assert not root.find("**/robot").isEmpty()
        assert not root.find("**/package-001").isEmpty()
        for patrol in scenario.patrols:
            assert not root.find(f"**/{patrol.id}").isEmpty()

    def test_sync_moves_the_robot_node_to_the_simulation_position(self, scene):
        controller = loaded_state(mode="manual")
        scene.build(controller.snapshot())
        for action in ("MOVE_FORWARD", "MOVE_FORWARD", "TURN_LEFT"):
            controller.handle({"type": "action", "action": action})

        scene.sync(controller.snapshot())
        for _ in range(120):
            scene.animate(1 / 30, 1.0)

        robot = scene.root.find("**/robot")
        assert (round(robot.getX(), 2), round(robot.getY(), 2)) == (2.0, 0.0)
        assert round(robot.getH()) % 360 == Orientation.NORTH.heading_degrees

    def test_carried_package_is_attached_to_the_robot(self, scene):
        controller = loaded_state("basic-delivery")
        scene.build(controller.snapshot())
        while not controller.env.world.robot.carrying:
            controller.handle({"type": "step"})

        scene.sync(controller.snapshot())

        package = scene.root.find("**/package-001")
        assert package.getParent().getName() == "carry-slot"
        assert scene.root.find("**/robot").isAncestorOf(package)

    def test_planned_path_and_incident_markers_follow_the_state(self, scene):
        controller = loaded_state(mode="manual")
        scene.build(controller.snapshot())
        controller.handle({"type": "action", "action": "MOVE_BACKWARD"})
        state = controller.snapshot()
        state["planned_path"] = [[0, 0], [1, 0], [2, 0]]

        scene.sync(state)

        assert scene.root.find("**/path").getNumChildren() == 3  # one line and two way-points
        assert scene.root.find("**/incidents").getNumChildren() == 1

    def test_overlay_options_show_and_hide_groups(self, scene):
        scene.build(loaded_state().snapshot())
        assert scene.root.find("**/grid").isHidden()

        scene.options.grid, scene.options.labels = True, False
        scene.apply_options()

        assert not scene.root.find("**/grid").isHidden()
        assert scene.root.find("**/labels").isHidden()

    def test_panda_collision_system_agrees_with_the_grid_rules(self, scene):
        """Independent check with CollisionTraverser: legal positions never overlap an obstacle."""
        controller = loaded_state("basic-delivery", mode="manual")
        scene.build(controller.snapshot())
        assert scene.physical_contacts() == []

        robot = scene.root.find("**/robot")
        robot.setPos(1, 6, 0)  # force the model into a shelf cell

        assert scene.physical_contacts() == ["shelf-1-6"]

    def test_rebuilding_replaces_the_previous_scene(self, scene):
        scene.build(loaded_state("obstacle-navigation").snapshot())
        scene.build(loaded_state("basic-delivery").snapshot())

        assert scene.root.findAllMatches("**/forklift-*").getNumPaths() == 0
        assert scene.root.findAllMatches("**/robot").getNumPaths() == 1


@pytest.fixture(scope="module")
def engine(tmp_path_factory):
    from simulation.engine import EngineConfig, SimulationEngine

    commands, outputs, frames = queue.Queue(), queue.Queue(), queue.Queue(maxsize=2)
    thumbnails = tmp_path_factory.mktemp("thumbnails")
    try:
        instance = SimulationEngine(
            commands, outputs, frames, EngineConfig(width=480, height=270, thumbnail_dir=thumbnails)
        )
    except Exception as error:  # no graphics pipe on this machine
        pytest.skip(f"Panda3D cannot open an off-screen buffer here: {error}")
    instance.test_queues = (commands, outputs, frames)
    instance.thumbnail_dir = thumbnails
    return instance


def pump(engine, frames: int = 3) -> list[dict]:
    for _ in range(frames):
        engine.base.taskMgr.step()
    outputs = engine.test_queues[1]
    drained = []
    while not outputs.empty():
        drained.append(outputs.get())
    return drained


def send(engine, command_type: str, **params) -> dict:
    engine.test_queues[0].put({"type": command_type, "request_id": command_type, **params})
    replies = [message for message in pump(engine) if message["type"] == "reply"]
    assert replies, f"no reply to {command_type}"
    return replies[-1]


class TestEngine:
    def test_engine_renders_thumbnails_for_every_scenario_at_startup(self, engine):
        names = sorted(path.name for path in engine.thumbnail_dir.glob("*.jpg"))

        assert names == ["basic-delivery.jpg", "multi-step-delivery.jpg", "obstacle-navigation.jpg"]
        assert all(path.stat().st_size > 2000 for path in engine.thumbnail_dir.glob("*.jpg"))

    def test_commands_run_inside_the_task_loop_and_frames_are_real_jpegs(self, engine):
        reply = send(engine, "load", episode_id="engine", scenario_id="basic-delivery", agent_mode="astar")
        assert reply["ok"] and reply["data"]["status"] == "created"
        assert send(engine, "start")["data"]["status"] == "running"

        frame = engine.capture_jpeg()

        assert frame[:3] == b"\xff\xd8\xff" and len(frame) > 3000
        assert engine.scene.scenario.id == "basic-delivery"

    def test_rendered_frame_changes_when_the_robot_moves(self, engine):
        send(engine, "load", episode_id="engine-2", scenario_id="basic-delivery", agent_mode="astar")
        send(engine, "start")
        send(engine, "pause")  # stop the real-time agent so only explicit steps advance the run
        pump(engine, 5)
        before = engine.capture_jpeg()
        steps_before = engine.controller.env.world.step_count

        for _ in range(12):
            send(engine, "step")
        pump(engine, 40)

        assert engine.capture_jpeg() != before
        assert engine.controller.env.world.step_count == steps_before + 12

    def test_view_camera_and_screenshot_commands(self, engine, tmp_path):
        view = send(engine, "set_view", grid=True, collision_shapes=True)["data"]
        assert view["grid"] is True and view["collision_shapes"] is True

        assert send(engine, "camera", action="preset", preset="top")["data"]["camera"] == "top"
        assert send(engine, "camera", action="zoom_in")["data"]["zoom"] < 1
        assert send(engine, "camera", action="reset")["data"] == {**view, "camera": "perspective", "zoom": 1.0}
        bad = send(engine, "camera", action="spin")
        assert not bad["ok"] and bad["error"]["code"] == "invalid_camera"

        target = tmp_path / "shot.png"
        assert send(engine, "screenshot", path=str(target))["ok"]
        assert target.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_command_errors_are_reported_without_stopping_the_loop(self, engine):
        failed = send(engine, "action", action="WAIT", episode_id="someone-else")

        assert not failed["ok"] and failed["error"]["code"] == "episode_not_active"
        assert send(engine, "snapshot")["ok"]
