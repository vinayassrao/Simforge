"""The Panda3D simulation engine.

One ``ShowBase`` owns the controller (the authoritative episode state) and the
scene graph. Commands arrive on a queue and are executed inside the Panda3D
task loop, so nothing outside this process or thread ever touches the scene.
Each rendered frame can be captured and handed to the web backend.
"""

from __future__ import annotations

import logging
import math
import queue
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from panda3d.core import ClockObject, Filename, PNMImage, Point3, StringStream, loadPrcFileData

from simulation.controller import CommandError, SimulationController
from simulation.scenarios import list_scenarios

logger = logging.getLogger(__name__)

FRAME_RATE = 30
STREAM_FRAME_INTERVAL = 1 / 15
PERF_INTERVAL = 1.0
ZOOM_LIMITS = (0.55, 1.8)
CAMERA_PRESETS = {
    "perspective": {"azimuth": 0.0, "pitch": 57.0},
    "isometric": {"azimuth": -38.0, "pitch": 42.0},
    "top": {"azimuth": 0.0, "pitch": 89.0},
}


class QueueLike(Protocol):
    def get_nowait(self) -> Any: ...

    def put_nowait(self, item: Any) -> None: ...


@dataclass(frozen=True)
class EngineConfig:
    width: int = 960
    height: int = 540
    offscreen: bool = True
    title: str = "SIMFORGE - Panda3D viewer"
    thumbnail_dir: Path | None = None


def configure_panda(config: EngineConfig) -> None:
    """Panda3D reads its settings when ShowBase starts, so this must run first."""
    settings = [
        f"window-type {'offscreen' if config.offscreen else 'onscreen'}",
        f"win-size {config.width} {config.height}",
        f"window-title {config.title}",
        "audio-library-name null",
        "sync-video 0",
        "clock-mode limited",
        f"clock-frame-rate {FRAME_RATE}",
        "textures-power-2 none",
        "notify-level-display error",
        "jpeg-quality 82",
    ]
    loadPrcFileData("simforge", "\n".join(settings))


class CameraRig:
    """An orbit camera that always looks at the centre of the warehouse."""

    def __init__(self, camera, lens, aspect: float) -> None:
        self._camera = camera
        self._aspect = aspect
        lens.setFov(42)
        lens.setNearFar(0.5, 200)
        self._centre = Point3(0, 0, 0)
        self._base_distance = 20.0
        self.zoom = 1.0
        self.preset = "perspective"

    def frame(self, width: int, height: int) -> None:
        self._centre = Point3(width / 2 - 0.5, height / 2 - 0.5, 0)
        self._base_distance = max(width / self._aspect, height) * 2.6
        self.apply()

    def set_preset(self, preset: str) -> None:
        if preset not in CAMERA_PRESETS:
            raise CommandError("invalid_camera", f"Camera preset must be one of {list(CAMERA_PRESETS)}.")
        self.preset = preset
        self.apply()

    def zoom_by(self, factor: float) -> None:
        self.zoom = min(ZOOM_LIMITS[1], max(ZOOM_LIMITS[0], self.zoom * factor))
        self.apply()

    def reset(self) -> None:
        self.zoom = 1.0
        self.preset = "perspective"
        self.apply()

    def apply(self) -> None:
        preset = CAMERA_PRESETS[self.preset]
        azimuth, pitch = math.radians(preset["azimuth"]), math.radians(preset["pitch"])
        distance = self._base_distance * self.zoom
        offset = Point3(
            distance * math.cos(pitch) * math.sin(azimuth),
            -distance * math.cos(pitch) * math.cos(azimuth),
            distance * math.sin(pitch),
        )
        self._camera.setPos(self._centre + offset)
        self._camera.lookAt(self._centre + Point3(0, -0.7, 0))


class SimulationEngine:
    """Runs the controller and scene inside Panda3D's task loop."""

    def __init__(
        self,
        commands: QueueLike,
        outputs: QueueLike,
        frames: QueueLike | None,
        config: EngineConfig | None = None,
    ) -> None:
        self.config = config or EngineConfig()
        configure_panda(self.config)
        # Imported here because ShowBase reads the configuration at import time.
        from direct.showbase.ShowBase import ShowBase

        from simulation.scene import BACKGROUND, WarehouseScene

        self.base = ShowBase()
        self._clock = ClockObject.getGlobalClock()
        self.base.disableMouse()
        self.base.setBackgroundColor(*BACKGROUND)
        self.controller = SimulationController()
        self.scene = WarehouseScene(self.base.render)
        self.camera = CameraRig(self.base.camera, self.base.camLens, self.config.width / self.config.height)
        self._commands = commands
        self._outputs = outputs
        self._frames = frames
        self._state: dict[str, Any] | None = None
        self._collision_shapes = False
        self._last_frame_time = 0.0
        self._last_perf_time = 0.0
        self._engine_commands = {
            "set_view": self._set_view,
            "camera": self._move_camera,
            "screenshot": self._screenshot,
            "shutdown": self._shutdown,
        }
        if self.config.thumbnail_dir is not None:
            self._render_thumbnails(self.config.thumbnail_dir)
        self.base.taskMgr.add(self._update, "simforge-update", sort=-10)
        logger.info(
            "Panda3D engine ready (%s, %dx%d, %s)",
            self.base.win.getGsg().getDriverRenderer(),
            self.config.width,
            self.config.height,
            "offscreen" if self.config.offscreen else "window",
        )

    def run(self) -> None:
        self.base.run()

    # -- per-frame update ------------------------------------------------------

    def _update(self, task):
        dt = min(self._clock.getDt(), 0.25)
        self._process_commands()
        self.controller.tick(dt)
        self._forward_outputs()
        self.scene.animate(dt, self.controller.speed)
        now = time.monotonic()
        if self._frames is not None and now - self._last_frame_time >= STREAM_FRAME_INTERVAL:
            self._last_frame_time = now
            self._publish_frame()
        if now - self._last_perf_time >= PERF_INTERVAL:
            self._last_perf_time = now
            self._publish_perf()
        return task.cont

    def _process_commands(self) -> None:
        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                return
            self._execute(command)

    def _execute(self, command: dict[str, Any]) -> None:
        reply: dict[str, Any] = {"type": "reply", "request_id": command.get("request_id")}
        try:
            handler = self._engine_commands.get(command.get("type", ""))
            data = handler(command) if handler else self.controller.handle(command)
            reply.update(ok=True, data=data)
        except CommandError as error:
            reply.update(ok=False, error={"code": error.code, "message": error.message})
        except Exception:  # the loop must survive a faulty command
            logger.exception("Command failed: %s", command.get("type"))
            reply.update(ok=False, error={"code": "internal_error", "message": "The simulation hit an internal error."})
        self._forward_outputs()
        self._emit(reply)

    def _forward_outputs(self) -> None:
        for message in self.controller.drain_outputs():
            if message["type"] == "state":
                self._apply_state(message["state"])
            self._emit(message)

    def _apply_state(self, state: dict[str, Any]) -> None:
        previous = self._state
        self._state = state
        rebuilt = (
            previous is None
            or previous["episode_id"] != state["episode_id"]
            or state["metrics"]["steps"] < previous["metrics"]["steps"]
        )
        if rebuilt:
            self.scene.build(state)
            self.scene.show_collision_shapes(self._collision_shapes)
            self.camera.frame(self.scene.scenario.width, self.scene.scenario.height)
        else:
            self.scene.sync(state)

    def _emit(self, message: dict[str, Any]) -> None:
        try:
            self._outputs.put_nowait(message)
        except queue.Full:
            logger.warning("Output queue is full; dropped a '%s' message", message.get("type"))

    # -- frames and performance ------------------------------------------------

    def capture_jpeg(self) -> bytes:
        image = PNMImage()
        self.base.win.getScreenshot(image)
        stream = StringStream()
        image.write(stream, "frame.jpg")
        return bytes(stream.getData())

    def _publish_frame(self) -> None:
        assert self._frames is not None
        frame = self.capture_jpeg()
        try:
            self._frames.put_nowait(frame)
        except queue.Full:
            try:
                self._frames.get_nowait()
                self._frames.put_nowait(frame)
            except (queue.Empty, queue.Full):
                pass

    def _publish_perf(self) -> None:
        clock = self._clock
        self._emit(
            {
                "type": "perf",
                "perf": {
                    "fps": round(clock.getAverageFrameRate(), 1),
                    "frame_ms": round(clock.getDt() * 1000, 2),
                    "physical_contacts": self.scene.physical_contacts() if self._state else [],
                    "renderer": self.base.win.getGsg().getDriverRenderer(),
                    "resolution": [self.config.width, self.config.height],
                },
            }
        )

    # -- engine commands -------------------------------------------------------

    def _set_view(self, command: dict[str, Any]) -> dict[str, Any]:
        options = self.scene.options
        for name in ("grid", "paths", "collisions", "labels"):
            if name in command:
                setattr(options, name, bool(command[name]))
        if "collision_shapes" in command:
            self._collision_shapes = bool(command["collision_shapes"])
            self.scene.show_collision_shapes(self._collision_shapes)
        self.scene.apply_options()
        return self.view_settings()

    def view_settings(self) -> dict[str, Any]:
        options = self.scene.options
        return {
            "grid": options.grid,
            "paths": options.paths,
            "collisions": options.collisions,
            "labels": options.labels,
            "collision_shapes": self._collision_shapes,
            "camera": self.camera.preset,
            "zoom": round(self.camera.zoom, 2),
        }

    def _move_camera(self, command: dict[str, Any]) -> dict[str, Any]:
        move = command.get("action")
        if move == "reset":
            self.camera.reset()
        elif move == "zoom_in":
            self.camera.zoom_by(0.85)
        elif move == "zoom_out":
            self.camera.zoom_by(1 / 0.85)
        elif move == "preset":
            self.camera.set_preset(command.get("preset", ""))
        else:
            raise CommandError("invalid_camera", "Camera action must be reset, zoom_in, zoom_out or preset.")
        return self.view_settings()

    def _screenshot(self, command: dict[str, Any]) -> dict[str, Any]:
        path = Path(command["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        self.base.graphicsEngine.renderFrame()
        image = PNMImage()
        self.base.win.getScreenshot(image)
        if not image.write(Filename.fromOsSpecific(str(path))):
            raise CommandError("screenshot_failed", f"Could not write {path}.")
        return {"path": str(path)}

    def _shutdown(self, _command: dict[str, Any]) -> dict[str, Any]:
        self.base.taskMgr.doMethodLater(0.05, lambda _task: self.base.userExit(), "simforge-exit")
        return {}

    def _render_thumbnails(self, directory: Path) -> None:
        """Render each scenario's starting scene once, for the scenario cards."""
        directory.mkdir(parents=True, exist_ok=True)
        preview = SimulationController()
        for scenario in list_scenarios():
            target = directory / f"{scenario.id}.jpg"
            if target.exists():
                continue
            state = preview.handle(
                {
                    "type": "load",
                    "episode_id": "thumbnail",
                    "scenario_id": scenario.id,
                    "agent_mode": "manual",
                }
            )
            self.scene.build(state)
            self.camera.frame(scenario.width, scenario.height)
            for _ in range(2):
                self.base.graphicsEngine.renderFrame()
            target.write_bytes(self.capture_jpeg())
