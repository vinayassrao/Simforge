"""Native Panda3D viewer: the same engine in a desktop window, without the web stack.

Run from the ``backend`` folder::

    python -m simulation.panda_viewer --scenario obstacle-navigation --agent astar

Keys: arrows or WASD drive (manual mode), E pick up, Q drop, X wait, Space pause/resume,
R reset, N single step, 1-5 speed, G grid, P path, C collision shapes, L labels,
V next camera, +/- zoom, Esc quit.
"""

from __future__ import annotations

import argparse
import logging
import queue
from functools import partial
from typing import Any

from simulation.controller import SPEEDS
from simulation.engine import CAMERA_PRESETS, EngineConfig, SimulationEngine
from simulation.scenarios import SCENARIOS
from simulation.types import Action

EPISODE_ID = "native-viewer"
ACTION_KEYS = {
    "arrow_up": Action.MOVE_FORWARD,
    "w": Action.MOVE_FORWARD,
    "arrow_down": Action.MOVE_BACKWARD,
    "s": Action.MOVE_BACKWARD,
    "arrow_left": Action.TURN_LEFT,
    "a": Action.TURN_LEFT,
    "arrow_right": Action.TURN_RIGHT,
    "d": Action.TURN_RIGHT,
    "e": Action.PICK_UP,
    "q": Action.DROP,
    "x": Action.WAIT,
}
VIEW_KEYS = {"g": "grid", "p": "paths", "l": "labels"}


class NativeViewer:
    """Binds the keyboard and an on-screen status line to a windowed engine."""

    def __init__(self, scenario_id: str, agent_mode: str, seed: int | None) -> None:
        self._commands: queue.Queue[dict[str, Any]] = queue.Queue()
        self._outputs: queue.Queue[dict[str, Any]] = queue.Queue()
        self.engine = SimulationEngine(
            self._commands, self._outputs, None, EngineConfig(width=1280, height=720, offscreen=False)
        )
        self._send("load", scenario_id=scenario_id, agent_mode=agent_mode, seed=seed)
        self._send("start")
        self._build_hud()
        self._bind_keys()
        self.engine.base.taskMgr.add(self._refresh_hud, "viewer-hud")

    def run(self) -> None:
        self.engine.run()

    def _send(self, command_type: str, **params: Any) -> None:
        self._commands.put({"type": command_type, "episode_id": EPISODE_ID, **params})

    def _build_hud(self) -> None:
        from direct.gui.OnscreenText import OnscreenText
        from panda3d.core import TextNode

        self._hud = OnscreenText(
            text="",
            pos=(-1.72, 0.92),
            scale=0.045,
            fg=(0.9, 0.96, 1, 1),
            shadow=(0, 0, 0, 0.8),
            align=TextNode.ALeft,
            mayChange=True,
        )
        self._message = ""

    def _bind_keys(self) -> None:
        base = self.engine.base
        for key, action in ACTION_KEYS.items():
            base.accept(key, partial(self._send, "action", action=action.value))
        for index, speed in enumerate(SPEEDS, start=1):
            base.accept(str(index), partial(self._send, "set_speed", speed=speed))
        for key, option in VIEW_KEYS.items():
            base.accept(key, self._toggle_view, [option])
        base.accept("c", self._toggle_view, ["collision_shapes"])
        base.accept("space", self._toggle_pause)
        base.accept("r", self._send, ["reset"])
        base.accept("n", self._send, ["step"])
        base.accept("v", self._next_camera)
        for key in ("+", "="):
            base.accept(key, partial(self._send, "camera", action="zoom_in"))
        base.accept("-", partial(self._send, "camera", action="zoom_out"))
        base.accept("escape", base.userExit)

    def _toggle_view(self, option: str) -> None:
        current = self.engine.view_settings()[option]
        self._send("set_view", **{option: not current})

    def _toggle_pause(self) -> None:
        controller = self.engine.controller
        if controller.env is not None and controller.env.status.value == "created":
            self._send("start")
        else:
            self._send("resume" if controller.paused else "pause")

    def _next_camera(self) -> None:
        presets = list(CAMERA_PRESETS)
        following = presets[(presets.index(self.engine.camera.preset) + 1) % len(presets)]
        self._send("camera", action="preset", preset=following)

    def _refresh_hud(self, task):
        while True:
            try:
                message = self._outputs.get_nowait()
            except queue.Empty:
                break
            if message["type"] == "reply" and not message["ok"]:
                self._message = message["error"]["message"]
            elif message["type"] == "events":
                self._message = message["events"][-1]["description"]
        controller = self.engine.controller
        if controller.env is not None:
            snapshot = controller.snapshot()
            metrics = snapshot["metrics"]
            task_view = snapshot["observation"]["task"]
            self._hud.setText(
                f"{task_view['name']}  |  {snapshot['mode']}  |  {snapshot['status']}  |  speed {snapshot['speed']}x\n"
                f"Step {metrics['steps']}/{metrics['max_steps']}   Progress {metrics['progress']}%   "
                f"Collisions {metrics['collisions']}   Invalid {metrics['invalid_actions']}\n"
                f"Objective: {task_view['current_objective']}\n{self._message}"
            )
        return task.cont


def main() -> None:
    parser = argparse.ArgumentParser(description="Open the SIMFORGE warehouse in a native Panda3D window.")
    parser.add_argument("--scenario", default="basic-delivery", choices=sorted(SCENARIOS))
    parser.add_argument("--agent", default="astar", choices=("astar", "manual"))
    parser.add_argument("--seed", type=int, default=None)
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    NativeViewer(arguments.scenario, arguments.agent, arguments.seed).run()


if __name__ == "__main__":
    main()
