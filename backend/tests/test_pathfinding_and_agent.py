import pytest

from agents.astar_agent import AStarAgent
from simulation.agent import ALLOWED_TRANSITIONS, AgentStateMachine, InvalidTransitionError
from simulation.baseline import baseline_route_length
from simulation.events import EventType
from simulation.observation import MovingObstacleView
from simulation.pathfinding import facing_poses, path_cells, plan_actions
from simulation.scenarios import list_scenarios
from simulation.types import Action, AgentState, EpisodeStatus, Orientation, Pose
from tests.helpers import drive, event_types, make_env, run_agent


def open_grid(width: int, height: int, walls: set = frozenset()):
    return lambda cell: 0 <= cell[0] < width and 0 <= cell[1] < height and cell not in walls


class TestPathfinding:
    def test_straight_line_needs_one_action_per_cell(self):
        plan = plan_actions(Pose((0, 0), Orientation.EAST), [Pose((4, 0), Orientation.EAST)], open_grid(5, 5))

        assert plan == [Action.MOVE_FORWARD] * 4

    def test_turning_costs_an_action(self):
        plan = plan_actions(Pose((0, 0), Orientation.EAST), [Pose((0, 3), Orientation.NORTH)], open_grid(5, 5))

        assert plan == [Action.TURN_LEFT, Action.MOVE_FORWARD, Action.MOVE_FORWARD, Action.MOVE_FORWARD]

    def test_reversing_is_used_when_it_is_shorter_than_turning_around(self):
        plan = plan_actions(Pose((2, 0), Orientation.EAST), [Pose((1, 0), Orientation.EAST)], open_grid(5, 5))

        assert plan == [Action.MOVE_BACKWARD]

    def test_route_goes_around_walls_and_never_through_them(self):
        walls = {(2, 0), (2, 1), (2, 2)}
        start = Pose((0, 0), Orientation.EAST)

        plan = plan_actions(
            start, [Pose((4, 0), Orientation.EAST), Pose((4, 0), Orientation.SOUTH)], open_grid(5, 5, walls)
        )

        cells = path_cells(start, plan)
        assert cells[0] == (0, 0) and cells[-1] == (4, 0)
        assert not set(cells) & walls
        assert (2, 3) in cells
        assert len(plan) == 13  # 10 moves and 3 turns is the minimum around the wall

    def test_unreachable_goal_returns_none_and_reached_goal_returns_empty(self):
        sealed = {(1, 0), (0, 1), (1, 1)}
        start = Pose((0, 0), Orientation.EAST)

        assert plan_actions(start, [Pose((3, 3), Orientation.NORTH)], open_grid(5, 5, sealed)) is None
        assert plan_actions(start, [], open_grid(5, 5)) is None
        assert plan_actions(start, [start], open_grid(5, 5)) == []

    def test_facing_poses_stand_next_to_the_target_and_look_at_it(self):
        poses = facing_poses([(0, 0)], open_grid(3, 3))

        assert set(poses) == {Pose((1, 0), Orientation.WEST), Pose((0, 1), Orientation.SOUTH)}
        assert all(pose.front == (0, 0) for pose in poses)

    @pytest.mark.parametrize("scenario", list_scenarios(), ids=lambda scenario: scenario.id)
    def test_every_scenario_has_a_baseline_route(self, scenario):
        length = baseline_route_length(make_env(scenario, start=False).world)

        assert length is not None and 20 < length < scenario.max_steps


class TestStateMachine:
    def test_only_documented_transitions_are_allowed(self):
        for state, allowed in ALLOWED_TRANSITIONS.items():
            for target in AgentState:
                machine = AgentStateMachine()
                machine.state = state
                assert machine.can_transition(target) is (target in allowed)

    def test_illegal_transition_raises_and_keeps_the_state(self):
        machine = AgentStateMachine()

        with pytest.raises(InvalidTransitionError):
            machine.transition(AgentState.COMPLETED)

        assert machine.state is AgentState.IDLE

    def test_transient_states_settle_on_the_next_step(self):
        machine = AgentStateMachine()
        machine.transition(AgentState.NAVIGATING_TO_OBJECT)
        assert machine.settle() is False

        machine.transition(AgentState.PICKING_UP)
        assert machine.settle() is True
        assert machine.state is AgentState.NAVIGATING_TO_TARGET

    def test_a_full_delivery_visits_every_state_in_order(self):
        env = make_env()

        run_agent(env)

        assert env.tasks.fsm.history == [
            AgentState.IDLE,
            AgentState.NAVIGATING_TO_OBJECT,
            AgentState.PICKING_UP,
            AgentState.NAVIGATING_TO_TARGET,
            AgentState.DROPPING_OBJECT,
            AgentState.COMPLETED,
        ]
        assert event_types(env).count("STATE_CHANGED") == 5


class TestAStarAgent:
    @pytest.mark.parametrize("scenario", [scenario.id for scenario in list_scenarios()])
    @pytest.mark.parametrize("seed", [1, 7, 23])
    def test_agent_completes_every_scenario_without_incidents(self, scenario, seed):
        env = make_env(scenario, seed=seed)

        run_agent(env)

        summary = env.summary()
        assert env.status is EpisodeStatus.COMPLETED
        assert summary["packages_delivered"] == summary["packages_total"]
        assert summary["collisions"] == summary["restricted_entries"] == summary["invalid_actions"] == 0
        assert summary["steps"] >= summary["baseline_steps"]

    def test_agent_matches_the_baseline_when_nothing_moves(self):
        env = make_env("basic-delivery")

        run_agent(env)

        assert env.world.step_count == env.baseline_steps

    def test_agent_moves_one_cell_at_a_time_and_never_teleports(self):
        env = make_env("obstacle-navigation")

        run_agent(env)

        points = env.trajectory
        for (_, x0, y0, _), (_, x1, y1, _) in zip(points, points[1:], strict=False):
            assert abs(x1 - x0) + abs(y1 - y0) <= 1

    def test_first_decision_announces_the_planned_route(self):
        env = make_env()

        decision = AStarAgent().decide(env.observe())

        assert decision.action in (Action.MOVE_FORWARD, Action.TURN_LEFT, Action.TURN_RIGHT)
        assert decision.planned_path[0] == (0, 0)
        assert [note.event_type for note in decision.notes] == [EventType.PATH_PLANNED]

    def test_agent_replans_when_a_moving_obstacle_blocks_the_route(self):
        env = make_env()
        agent = AStarAgent()
        first = agent.decide(env.observe())
        env.step(first.action)
        blocked_cell = first.planned_path[3]
        observation = env.observe()
        observation.obstacles.moving.append(
            MovingObstacleView(id="forklift-x", name="Test forklift", position=blocked_cell, next_position=blocked_cell)
        )

        second = agent.decide(observation)

        assert blocked_cell not in second.planned_path
        assert [note.event_type for note in second.notes] == [EventType.OBSTACLE_DETECTED, EventType.PATH_RECALCULATED]

    def test_replanning_is_recorded_in_the_event_log_of_a_real_run(self):
        env = make_env("obstacle-navigation", seed=7)

        run_agent(env)

        assert "PATH_RECALCULATED" in event_types(env)
        assert env.world.step_count > env.baseline_steps

    def test_agent_waits_when_no_route_exists(self):
        env = make_env()
        observation = env.observe()
        observation.obstacles.static.extend([(1, 0), (0, 1)])

        decision = AStarAgent().decide(observation)

        assert decision.action is Action.WAIT
        assert decision.notes[0].event_type is EventType.OBSTACLE_DETECTED

    def test_agent_avoids_the_restricted_area(self):
        env = make_env("multi-step-delivery")

        run_agent(env)

        visited = {(x, y) for _, x, y, _ in env.trajectory}
        assert not visited & env.scenario.restricted_cells


class TestObservation:
    def test_observation_reflects_the_actual_world_state(self):
        env = make_env("obstacle-navigation")
        drive(env, "FFL")

        observation = env.observe()

        assert observation.step == 3
        assert observation.agent.position == env.world.robot.position == (2, 0)
        assert observation.agent.orientation is Orientation.NORTH
        assert observation.agent.state is AgentState.NAVIGATING_TO_OBJECT
        assert observation.target.position == env.world.packages["package-001"].position
        assert set(observation.obstacles.static) == env.scenario.static_blocked
        assert [(o.position, o.next_position) for o in observation.obstacles.moving] == [
            (o.position, o.next_position) for o in env.world.obstacles
        ]
        assert observation.available_actions == env.legal_actions()
        assert len(observation.recent_events) == 5
        assert observation.recent_events[-1].description.startswith("Turned left")

    def test_target_is_cleared_when_everything_is_delivered(self):
        env = make_env()

        run_agent(env)

        observation = env.observe()
        assert observation.target is None
        assert observation.available_actions == []
        assert observation.task.progress == 100
        assert observation.status is EpisodeStatus.COMPLETED
