from dataclasses import replace

import pytest

from simulation import scenarios
from simulation.controller import BASE_ACTIONS_PER_SECOND, CommandError, SimulationController
from simulation.types import EpisodeStatus


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def load(controller: SimulationController, mode: str = "manual", scenario: str = "basic-delivery", **extra):
    return controller.handle(
        {"type": "load", "episode_id": "ep-test", "scenario_id": scenario, "agent_mode": mode, **extra}
    )


def messages(controller: SimulationController, kind: str) -> list[dict]:
    return [message for message in controller.drain_outputs() if message["type"] == kind]


def expect_error(controller: SimulationController, command: dict, code: str) -> None:
    with pytest.raises(CommandError) as raised:
        controller.handle(command)
    assert raised.value.code == code


class TestLifecycle:
    def test_load_publishes_the_initial_state(self):
        controller = SimulationController()

        state = load(controller)

        assert state["status"] == "created"
        assert state["mode"] == "manual"
        assert state["seed"] == scenarios.get_scenario("basic-delivery").default_seed
        assert state["metrics"]["steps"] == 0
        outputs = controller.drain_outputs()
        assert [message["type"] for message in outputs] == ["events", "state"]

    def test_unknown_scenario_and_unknown_command_are_rejected(self):
        controller = SimulationController()

        expect_error(controller, {"type": "load", "episode_id": "x", "scenario_id": "nope"}, "unknown_scenario")
        expect_error(controller, {"type": "teleport"}, "unknown_command")
        expect_error(controller, {"type": "start"}, "no_active_episode")

    def test_actions_need_a_started_unpaused_running_episode(self):
        controller = SimulationController()
        load(controller)
        action = {"type": "action", "action": "MOVE_FORWARD"}

        expect_error(controller, action, "invalid_state")
        controller.handle({"type": "start"})
        assert controller.handle(action)["success"] is True

        controller.handle({"type": "pause"})
        assert controller.status is EpisodeStatus.PAUSED
        expect_error(controller, action, "invalid_state")
        expect_error(controller, {"type": "pause"}, "invalid_state")

        controller.handle({"type": "resume"})
        assert controller.handle(action)["observation"]["agent"]["position"] == [2, 0]
        expect_error(controller, {"type": "resume"}, "invalid_state")
        expect_error(controller, {"type": "start"}, "invalid_state")

    def test_commands_for_another_episode_are_rejected(self):
        controller = SimulationController()
        load(controller)

        expect_error(controller, {"type": "start", "episode_id": "ep-other"}, "episode_not_active")

    def test_unknown_action_and_invalid_speed_are_rejected(self):
        controller = SimulationController()
        load(controller)
        controller.handle({"type": "start"})

        expect_error(controller, {"type": "action", "action": "JUMP"}, "unknown_action")
        expect_error(controller, {"type": "set_speed", "speed": 3}, "invalid_speed")
        assert controller.handle({"type": "set_speed", "speed": 4}) == {"speed": 4.0}

    def test_reset_restores_the_starting_state_and_restarts_the_event_log(self):
        controller = SimulationController()
        initial = load(controller, seed=5)
        controller.handle({"type": "start"})
        for _ in range(3):
            controller.handle({"type": "action", "action": "MOVE_FORWARD"})
        controller.drain_outputs()

        state = controller.handle({"type": "reset"})

        assert state["status"] == "created" and state["seed"] == 5
        assert state["observation"]["agent"] == initial["observation"]["agent"]
        assert state["observation"]["objects"] == initial["observation"]["objects"]
        events = [event for message in messages(controller, "events") for event in message["events"]]
        assert events[0]["seq"] == 1
        assert events[-1]["type"] == "SIMULATION_RESET"

    def test_step_makes_the_robot_wait_in_manual_mode(self):
        controller = SimulationController()
        load(controller)
        controller.handle({"type": "start"})

        result = controller.handle({"type": "step"})

        assert result["action"] == "WAIT"
        assert result["observation"]["step"] == 1


class TestBuiltInAgent:
    def test_manual_actions_are_refused_while_the_agent_drives(self):
        controller = SimulationController()
        load(controller, mode="astar")
        controller.handle({"type": "start"})

        expect_error(controller, {"type": "action", "action": "WAIT"}, "agent_controlled")

    def test_tick_advances_the_agent_at_the_selected_speed(self):
        controller = SimulationController()
        load(controller, mode="astar")
        controller.handle({"type": "start"})

        controller.tick(1.0)
        assert controller.env.world.step_count == BASE_ACTIONS_PER_SECOND

        controller.handle({"type": "set_speed", "speed": 2})
        controller.tick(1.0)
        assert controller.env.world.step_count == BASE_ACTIONS_PER_SECOND * 3
        assert controller.planned_path, "the agent should publish its planned route"

    def test_tick_does_nothing_while_paused_or_before_start(self):
        controller = SimulationController()
        load(controller, mode="astar")
        controller.tick(5.0)
        assert controller.env.world.step_count == 0

        controller.handle({"type": "start"})
        controller.handle({"type": "pause"})
        controller.tick(5.0)
        assert controller.env.world.step_count == 0

    def test_finishing_reports_the_summary_exactly_once(self):
        controller = SimulationController()
        load(controller, mode="astar")
        controller.handle({"type": "start"})
        controller.drain_outputs()

        for _ in range(200):
            controller.tick(1.0)

        finished = messages(controller, "finished")
        assert len(finished) == 1
        summary = finished[0]["summary"]
        assert summary["completed"] is True and summary["agent_mode"] == "astar"
        assert summary["steps"] == summary["baseline_steps"]
        assert controller.status is EpisodeStatus.COMPLETED
        expect_error(controller, {"type": "step"}, "invalid_state")


class TestClock:
    def test_elapsed_time_counts_only_while_running(self):
        clock = FakeClock()
        controller = SimulationController(clock)
        load(controller)
        controller.handle({"type": "start"})

        clock.now += 4
        controller.handle({"type": "pause"})
        clock.now += 60
        controller.handle({"type": "resume"})
        clock.now += 2

        assert controller.elapsed_seconds == pytest.approx(6)
        assert controller.snapshot()["metrics"]["elapsed_seconds"] == 6

    def test_time_limit_fails_the_episode(self, monkeypatch):
        timed = replace(scenarios.get_scenario("basic-delivery"), id="timed", time_limit_s=10.0)
        monkeypatch.setitem(scenarios.SCENARIOS, "timed", timed)
        clock = FakeClock()
        controller = SimulationController(clock)
        load(controller, scenario="timed")
        controller.handle({"type": "start"})

        clock.now += 9
        controller.tick(0.1)
        assert controller.status is EpisodeStatus.RUNNING

        clock.now += 2
        controller.tick(0.1)

        assert controller.status is EpisodeStatus.FAILED
        assert controller.env.failure_reason == "time_limit_exceeded"
        assert messages(controller, "finished")[0]["summary"]["failure_reason"] == "time_limit_exceeded"
