"""Episode controller: turns commands into simulation changes and output messages.

The controller owns the live episode. It is driven by exactly one thread: the
Panda3D task loop in production, or the caller's thread in tests. It never
touches rendering, so the same logic runs with or without a window.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from agents.astar_agent import AStarAgent
from agents.base import Agent
from simulation.environment import EpisodeNotRunningError, WarehouseEnvironment
from simulation.events import EventType
from simulation.scenarios import UnknownScenarioError, get_scenario
from simulation.types import Action, AgentMode, Cell, EpisodeStatus

logger = logging.getLogger(__name__)

SPEEDS = (0.25, 0.5, 1.0, 2.0, 4.0)
BASE_ACTIONS_PER_SECOND = 3.0


class CommandError(Exception):
    """A command could not be carried out. ``code`` is stable and machine readable."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class SimulationController:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._outputs: list[dict[str, Any]] = []
        self.env: WarehouseEnvironment | None = None
        self.mode = AgentMode.MANUAL
        self.speed = 1.0
        self.paused = False
        self.planned_path: list[Cell] = []
        self._agent: Agent | None = None
        self._tick_budget = 0.0
        self._elapsed = 0.0
        self._running_since: float | None = None
        self._finish_reported = False
        self._last_action_latency_ms = 0.0
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "load": self._load,
            "start": self._start,
            "pause": self._pause,
            "resume": self._resume,
            "reset": self._reset,
            "step": self._step,
            "action": self._action,
            "set_speed": self._set_speed,
            "observation": self._observation,
            "snapshot": lambda _command: self.snapshot(),
            "unload": self._unload,
        }

    # -- command entry point -------------------------------------------------

    def handle(self, command: dict[str, Any]) -> dict[str, Any]:
        """Execute one command and return its reply data. Raises CommandError."""
        handler = self._handlers.get(command.get("type", ""))
        if handler is None:
            raise CommandError("unknown_command", f"Unknown command '{command.get('type')}'.")
        return handler(command)

    def drain_outputs(self) -> list[dict[str, Any]]:
        outputs, self._outputs = self._outputs, []
        return outputs

    # -- status --------------------------------------------------------------

    @property
    def status(self) -> EpisodeStatus | None:
        if self.env is None:
            return None
        if self.env.status is EpisodeStatus.RUNNING and self.paused:
            return EpisodeStatus.PAUSED
        return self.env.status

    @property
    def elapsed_seconds(self) -> float:
        running = self._clock() - self._running_since if self._running_since is not None else 0.0
        return self._elapsed + running

    def _require_env(self, command: dict[str, Any]) -> WarehouseEnvironment:
        if self.env is None:
            raise CommandError("no_active_episode", "No episode is loaded in the simulation.")
        requested = command.get("episode_id")
        if requested is not None and requested != self.env.episode_id:
            raise CommandError(
                "episode_not_active",
                f"Episode '{requested}' is not the active episode ('{self.env.episode_id}').",
            )
        return self.env

    # -- lifecycle commands --------------------------------------------------

    def _load(self, command: dict[str, Any]) -> dict[str, Any]:
        try:
            scenario = get_scenario(command["scenario_id"])
        except UnknownScenarioError:
            raise CommandError("unknown_scenario", f"Unknown scenario '{command['scenario_id']}'.") from None
        self.mode = AgentMode(command.get("agent_mode", AgentMode.MANUAL))
        seed = command.get("seed")
        self._build(scenario, scenario.default_seed if seed is None else int(seed), command["episode_id"])
        logger.info("Loaded episode %s (%s, %s)", command["episode_id"], scenario.id, self.mode.value)
        return self.snapshot()

    def _build(self, scenario, seed: int, episode_id: str) -> None:
        self.env = WarehouseEnvironment(scenario, seed, episode_id)
        self._agent = AStarAgent() if self.mode is AgentMode.ASTAR else None
        self.paused = False
        self.planned_path = []
        self._tick_budget = 0.0
        self._elapsed = 0.0
        self._running_since = None
        self._finish_reported = False
        self._publish()

    def _unload(self, _command: dict[str, Any]) -> dict[str, Any]:
        self.env = None
        self._agent = None
        self.planned_path = []
        return {}

    def _start(self, command: dict[str, Any]) -> dict[str, Any]:
        env = self._require_env(command)
        try:
            env.start()
        except EpisodeNotRunningError as error:
            raise CommandError("invalid_state", str(error)) from None
        self._running_since = self._clock()
        self._publish()
        return self.snapshot()

    def _pause(self, command: dict[str, Any]) -> dict[str, Any]:
        env = self._require_env(command)
        if env.status is not EpisodeStatus.RUNNING or self.paused:
            raise CommandError("invalid_state", "Only a running episode can be paused.")
        self.paused = True
        self._stop_clock()
        env.note(EventType.SIMULATION_PAUSED, "Simulation paused.")
        self._publish()
        return self.snapshot()

    def _resume(self, command: dict[str, Any]) -> dict[str, Any]:
        env = self._require_env(command)
        if env.status is not EpisodeStatus.RUNNING or not self.paused:
            raise CommandError("invalid_state", "Only a paused episode can be resumed.")
        self.paused = False
        self._running_since = self._clock()
        env.note(EventType.SIMULATION_RESUMED, "Simulation resumed.")
        self._publish()
        return self.snapshot()

    def _reset(self, command: dict[str, Any]) -> dict[str, Any]:
        """Rebuild the episode from its scenario and seed. The episode id is kept."""
        env = self._require_env(command)
        self._build(env.scenario, env.seed, env.episode_id)
        assert self.env is not None
        self.env.note(EventType.SIMULATION_RESET, "Simulation reset to its starting state.")
        self._publish()
        return self.snapshot()

    def _set_speed(self, command: dict[str, Any]) -> dict[str, Any]:
        speed = float(command.get("speed", 1.0))
        if speed not in SPEEDS:
            raise CommandError("invalid_speed", f"Speed must be one of {list(SPEEDS)}.")
        self.speed = speed
        self._publish(state_only=True)
        return {"speed": self.speed}

    # -- acting --------------------------------------------------------------

    def _action(self, command: dict[str, Any]) -> dict[str, Any]:
        """An action submitted by a manual user or an external agent."""
        env = self._require_env(command)
        if self.mode is AgentMode.ASTAR:
            raise CommandError(
                "agent_controlled", "This episode is driven by the built-in agent; actions are not accepted."
            )
        try:
            action = Action(command.get("action"))
        except ValueError:
            raise CommandError("unknown_action", f"Unknown action '{command.get('action')}'.") from None
        self._require_accepting_actions(env)
        return self._apply(env, action)

    def _step(self, command: dict[str, Any]) -> dict[str, Any]:
        """Advance exactly one step: the built-in agent decides, or the robot waits."""
        env = self._require_env(command)
        if env.status is not EpisodeStatus.RUNNING:
            raise CommandError("invalid_state", f"The episode is {env.status.value}; it cannot be stepped.")
        return self._apply(env, self._agent_action(env))

    def _require_accepting_actions(self, env: WarehouseEnvironment) -> None:
        if env.status is EpisodeStatus.CREATED:
            raise CommandError("invalid_state", "Start the episode before sending actions.")
        if env.done:
            raise CommandError("invalid_state", f"The episode is {env.status.value}; no more actions.")
        if self.paused:
            raise CommandError("invalid_state", "The episode is paused. Resume it to send actions.")

    def _agent_action(self, env: WarehouseEnvironment) -> Action:
        if self._agent is None:
            return Action.WAIT
        decision = self._agent.decide(env.observe())
        self.planned_path = decision.planned_path
        for note in decision.notes:
            env.note(note.event_type, note.description, note.data)
        return decision.action

    def _apply(self, env: WarehouseEnvironment, action: Action) -> dict[str, Any]:
        started = time.perf_counter()
        result = env.step(action)
        self._last_action_latency_ms = (time.perf_counter() - started) * 1000
        if self._agent is None:
            self.planned_path = []
        if env.done:
            self._stop_clock()
        self._publish()
        outcome = result.outcome
        return {
            "action": outcome.action.value,
            "success": outcome.success,
            "message": outcome.message,
            "error_code": outcome.error_code,
            "done": result.done,
            "observation": env.observe(self.status).model_dump(mode="json"),
        }

    def tick(self, dt: float) -> None:
        """Advance real time. Drives the built-in agent and enforces the time limit."""
        env = self.env
        if env is None or env.status is not EpisodeStatus.RUNNING or self.paused:
            return
        limit = env.scenario.time_limit_s
        if limit is not None and self.elapsed_seconds >= limit:
            env.fail("time_limit_exceeded")
            self._stop_clock()
            self._publish()
            return
        if self._agent is None:
            return
        self._tick_budget += dt * self.speed * BASE_ACTIONS_PER_SECOND
        while self._tick_budget >= 1.0 and env.status is EpisodeStatus.RUNNING:
            self._tick_budget -= 1.0
            self._apply(env, self._agent_action(env))

    def _stop_clock(self) -> None:
        if self._running_since is not None:
            self._elapsed += self._clock() - self._running_since
            self._running_since = None

    # -- outputs -------------------------------------------------------------

    def _observation(self, command: dict[str, Any]) -> dict[str, Any]:
        env = self._require_env(command)
        return env.observe(self.status).model_dump(mode="json")

    def snapshot(self) -> dict[str, Any]:
        """The full live state: what the WebSocket and the 3D scene both consume."""
        env = self.env
        if env is None:
            return {"episode_id": None}
        metrics = env.metrics
        return {
            "episode_id": env.episode_id,
            "scenario_id": env.scenario.id,
            "seed": env.seed,
            "mode": self.mode.value,
            "status": self.status.value if self.status else None,
            "speed": self.speed,
            "observation": env.observe(self.status).model_dump(mode="json"),
            "planned_path": [list(cell) for cell in self.planned_path],
            "incidents": list(metrics.incident_locations),
            "metrics": {
                "steps": env.world.step_count,
                "max_steps": env.scenario.max_steps,
                "actions": metrics.actions,
                "collisions": metrics.collisions,
                "restricted_entries": metrics.restricted_entries,
                "invalid_actions": metrics.invalid_actions,
                "progress": env.tasks.progress,
                "elapsed_seconds": round(self.elapsed_seconds, 2),
                "step_duration_ms": round(metrics.last_step_ms, 3),
                "action_latency_ms": round(self._last_action_latency_ms, 3),
            },
        }

    def _publish(self, state_only: bool = False) -> None:
        env = self.env
        if env is None:
            return
        if not state_only:
            fresh = env.events.drain()
            if fresh:
                self._outputs.append(
                    {
                        "type": "events",
                        "episode_id": env.episode_id,
                        "events": [event.to_dict() for event in fresh],
                    }
                )
        self._outputs.append({"type": "state", "episode_id": env.episode_id, "state": self.snapshot()})
        if env.done and not self._finish_reported:
            self._finish_reported = True
            summary = env.summary()
            summary["elapsed_seconds"] = round(self.elapsed_seconds, 2)
            summary["agent_mode"] = self.mode.value
            self._outputs.append({"type": "finished", "episode_id": env.episode_id, "summary": summary})
