"""Gateways between the web backend and the simulation.

``ProcessGateway`` talks to the Panda3D process over multiprocessing queues.
``InlineGateway`` runs the same controller in-process without rendering, which
keeps the API testable on machines without a GPU. Web request threads only ever
enqueue commands; they never touch simulation or scene objects directly.
"""

from __future__ import annotations

import logging
import multiprocessing
import queue
import threading
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any

from simulation.controller import CommandError, SimulationController

logger = logging.getLogger(__name__)

Listener = Callable[[dict[str, Any]], None]
REQUEST_TIMEOUT_SECONDS = 8.0
STARTUP_TIMEOUT_SECONDS = 90.0
VIEW_DEFAULTS = {
    "grid": False,
    "paths": True,
    "collisions": True,
    "labels": True,
    "collision_shapes": False,
    "camera": "perspective",
    "zoom": 1.0,
}


class SimulationError(Exception):
    """The simulation rejected a command."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SimulationUnavailableError(Exception):
    """The simulation process is not running or did not answer in time."""


class SimulationGateway(ABC):
    renders_frames = False

    def __init__(self) -> None:
        self._listeners: list[Listener] = []
        self.perf: dict[str, Any] = {}

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def _dispatch(self, message: dict[str, Any]) -> None:
        for listener in self._listeners:
            try:
                listener(message)
            except Exception:
                logger.exception("A simulation listener failed on a '%s' message", message.get("type"))

    def start(self) -> None:  # noqa: B027  (optional hook)
        """Bring the simulation up."""

    def stop(self) -> None:  # noqa: B027  (optional hook)
        """Shut the simulation down."""

    @abstractmethod
    def request(self, command: dict[str, Any]) -> dict[str, Any]:
        """Send a command and wait for its reply data. Raises SimulationError."""

    def latest_frame(self) -> tuple[int, bytes] | None:
        """The newest rendered frame as (sequence number, JPEG bytes), if rendering."""
        return None


class InlineGateway(SimulationGateway):
    """Runs the controller in the calling thread. No rendering."""

    def __init__(self) -> None:
        super().__init__()
        self.controller = SimulationController()
        self._lock = threading.Lock()
        self._view = dict(VIEW_DEFAULTS)

    def request(self, command: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if command.get("type") in ("set_view", "camera"):
                self._view.update(
                    {key: value for key, value in command.items() if key in self._view and key != "camera"}
                )
                return dict(self._view)
            try:
                return self.controller.handle(command)
            except CommandError as error:
                raise SimulationError(error.code, error.message) from None
            finally:
                for message in self.controller.drain_outputs():
                    self._dispatch(message)


class ProcessGateway(SimulationGateway):
    """Owns the Panda3D simulation process and its queues."""

    renders_frames = True

    def __init__(self, width: int, height: int, thumbnail_dir: Path | None, log_level: str = "INFO") -> None:
        super().__init__()
        self._options = {
            "width": width,
            "height": height,
            "thumbnail_dir": str(thumbnail_dir) if thumbnail_dir else None,
            "log_level": log_level,
        }
        context = multiprocessing.get_context("spawn")
        self._commands = context.Queue()
        self._outputs = context.Queue()
        self._frames = context.Queue(maxsize=2)
        self._context = context
        self._process: multiprocessing.process.BaseProcess | None = None
        self._pending: dict[str, tuple[threading.Event, dict[str, Any]]] = {}
        self._pending_lock = threading.Lock()
        self._ready = threading.Event()
        self._stopping = threading.Event()
        self._fatal: str | None = None
        self._frame: tuple[int, bytes] | None = None
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        from simulation.process import run_simulation_process

        self._process = self._context.Process(
            target=run_simulation_process,
            args=(self._commands, self._outputs, self._frames, self._options),
            name="simforge-simulation",
            daemon=True,
        )
        self._process.start()
        for target, name in (
            (self._pump_outputs, "simforge-outputs"),
            (self._pump_frames, "simforge-frames"),
        ):
            thread = threading.Thread(target=target, name=name, daemon=True)
            thread.start()
            self._threads.append(thread)
        if not self._ready.wait(STARTUP_TIMEOUT_SECONDS) or self._fatal:
            self.stop()
            raise SimulationUnavailableError(self._fatal or "The simulation process did not start in time.")
        logger.info("Simulation process ready (pid %s)", self._process.pid)

    def stop(self) -> None:
        if self._process is None:
            return
        self._stopping.set()
        if self._process.is_alive():
            self._commands.put({"type": "shutdown"})
            self._process.join(timeout=5)
        if self._process.is_alive():
            self._process.terminate()
        self._process = None

    def request(self, command: dict[str, Any]) -> dict[str, Any]:
        if self._process is None or not self._process.is_alive():
            raise SimulationUnavailableError("The simulation process is not running.")
        request_id = uuid.uuid4().hex
        done = threading.Event()
        slot: dict[str, Any] = {}
        with self._pending_lock:
            self._pending[request_id] = (done, slot)
        self._commands.put({**command, "request_id": request_id})
        if not done.wait(REQUEST_TIMEOUT_SECONDS):
            with self._pending_lock:
                self._pending.pop(request_id, None)
            raise SimulationUnavailableError("The simulation did not answer in time.")
        reply = slot["reply"]
        if not reply["ok"]:
            raise SimulationError(reply["error"]["code"], reply["error"]["message"])
        return reply["data"]

    def latest_frame(self) -> tuple[int, bytes] | None:
        return self._frame

    def _pump_outputs(self) -> None:
        while not self._stopping.is_set():
            try:
                message = self._outputs.get(timeout=0.5)
            except queue.Empty:
                continue
            except (EOFError, OSError):
                return
            kind = message.get("type")
            if kind == "reply":
                with self._pending_lock:
                    pending = self._pending.pop(message.get("request_id"), None)
                if pending is not None:
                    pending[1]["reply"] = message
                    pending[0].set()
            elif kind == "ready":
                self._ready.set()
            elif kind == "fatal":
                self._fatal = message.get("message")
                self._ready.set()
            elif kind == "perf":
                self.perf = message["perf"]
                self._dispatch(message)
            else:
                self._dispatch(message)

    def _pump_frames(self) -> None:
        sequence = 0
        while not self._stopping.is_set():
            try:
                frame = self._frames.get(timeout=0.5)
            except queue.Empty:
                continue
            except (EOFError, OSError):
                return
            sequence += 1
            self._frame = (sequence, frame)
