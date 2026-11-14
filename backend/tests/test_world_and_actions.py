from dataclasses import replace

import pytest

from simulation.collision import BlockerKind, find_blocker
from simulation.environment import EpisodeNotRunningError
from simulation.scenarios import get_scenario, list_scenarios
from simulation.scenarios.base import parse_layout
from simulation.types import Action, AgentState, EpisodeStatus, Orientation, PackageState
from simulation.world import World, straight_route
from tests.helpers import drive, drive_to_face, event_types, make_env


class TestEnvironmentCreation:
    def test_three_scenarios_are_registered_with_valid_layouts(self):
        scenarios = list_scenarios()

        assert [scenario.id for scenario in scenarios] == [
            "basic-delivery",
            "obstacle-navigation",
            "multi-step-delivery",
        ]
        for scenario in scenarios:
            blocked = scenario.static_blocked
            assert scenario.start_cell not in blocked
            assert not blocked & scenario.restricted_cells
            for zone in scenario.zones:
                assert not zone.cells & blocked, f"{zone.id} overlaps an obstacle"
            for patrol in scenario.patrols:
                assert not set(straight_route(patrol.start, patrol.end)) & blocked

    def test_layout_parser_maps_rows_to_cells_with_north_first(self):
        layout = parse_layout(("#..", ".X.", "..R"))

        assert (layout.width, layout.height) == (3, 3)
        assert layout.shelves == {(0, 2)}
        assert layout.static_obstacles == {(1, 1)}
        assert layout.restricted == {(2, 0)}

    def test_layout_parser_rejects_ragged_rows(self):
        with pytest.raises(ValueError):
            parse_layout(("...", ".."))

    def test_robot_starts_at_the_loading_dock_and_idle(self):
        env = make_env(start=False)

        assert env.world.robot.position == (0, 0)
        assert env.world.robot.orientation is Orientation.EAST
        assert env.world.robot.carrying is None
        assert env.tasks.fsm.state is AgentState.IDLE
        assert env.status is EpisodeStatus.CREATED
        assert event_types(env) == ["AGENT_SPAWNED"]

    def test_packages_start_on_candidate_cells_inside_the_collection_bay(self):
        env = make_env("multi-step-delivery")
        bay = env.scenario.zone("zone-collection").cells

        positions = [package.position for package in env.world.packages.values()]

        assert len(set(positions)) == 2
        for package in env.world.packages.values():
            assert package.position in package.spec.candidate_cells
            assert package.position in bay
            assert package.state is PackageState.AVAILABLE


class TestDeterminism:
    def test_same_seed_recreates_the_same_world_and_behaviour(self):
        moves = "LFFRFFFFWWWWLFF"
        first, second = make_env("obstacle-navigation", seed=11), make_env("obstacle-navigation", seed=11)

        drive(first, moves)
        drive(second, moves)

        assert first.trajectory == second.trajectory
        assert [o.position for o in first.world.obstacles] == [o.position for o in second.world.obstacles]
        assert event_types(first) == event_types(second)
        dump_a, dump_b = (env.observe().model_dump(exclude={"recent_events"}) for env in (first, second))
        assert dump_a == dump_b

    def test_different_seeds_change_the_starting_conditions(self):
        scenario = get_scenario("obstacle-navigation")

        starts = {
            (
                tuple(p.position for p in World(scenario, seed).packages.values()),
                tuple(o.position for o in World(scenario, seed).obstacles),
            )
            for seed in range(8)
        }

        assert len(starts) > 1


class TestMovement:
    def test_forward_and_backward_move_one_cell(self):
        env = make_env()

        drive(env, "FF")
        assert env.world.robot.position == (2, 0)
        result = drive(env, "B")

        assert result.outcome.success
        assert env.world.robot.position == (1, 0)
        assert env.world.robot.orientation is Orientation.EAST
        assert env.world.step_count == 3

    def test_turning_changes_only_the_orientation(self):
        env = make_env()
        seen = []

        for _ in range(4):
            drive(env, "L")
            seen.append(env.world.robot.orientation)

        assert seen == [Orientation.NORTH, Orientation.WEST, Orientation.SOUTH, Orientation.EAST]
        assert env.world.robot.position == (0, 0)
        drive(env, "R")
        assert env.world.robot.orientation is Orientation.SOUTH

    def test_driving_into_the_wall_is_a_collision_and_the_robot_stays(self):
        env = make_env()

        result = drive(env, "B")

        assert not result.outcome.success
        assert result.outcome.collision.kind is BlockerKind.WALL
        assert env.world.robot.position == (0, 0)
        assert env.metrics.collisions == 1
        assert env.metrics.invalid_actions == 0
        assert env.metrics.incident_locations[0]["cell"] == [-1, 0]
        assert env.events.all[-1].category.value == "collision"

    def test_driving_into_a_shelf_is_a_collision(self):
        env = make_env()

        result = drive(env, "LFFFFFFRF")

        assert env.world.robot.position == (0, 6)
        assert result.outcome.collision.kind is BlockerKind.SHELF
        assert result.outcome.error_code == "collision"

    def test_entering_the_restricted_area_is_allowed_but_recorded(self):
        env = make_env()

        drive(env, "LFFRFFFFFFFF")

        assert env.world.robot.position == (8, 2)
        assert env.metrics.restricted_entries == 1
        assert env.metrics.collisions == 0
        assert "RESTRICTED_AREA_ENTERED" in event_types(env)

    def test_legal_actions_exclude_blocked_moves(self):
        env = make_env()

        legal = env.legal_actions()

        assert Action.MOVE_FORWARD in legal
        assert Action.MOVE_BACKWARD not in legal
        assert Action.PICK_UP not in legal and Action.DROP not in legal
        assert {Action.TURN_LEFT, Action.TURN_RIGHT, Action.WAIT} <= set(legal)

    def test_actions_are_rejected_before_start_and_after_the_end(self):
        env = make_env(start=False)
        with pytest.raises(EpisodeNotRunningError):
            env.step(Action.WAIT)
        assert env.legal_actions() == []

        env.start()
        env.fail("step_limit_exceeded")
        with pytest.raises(EpisodeNotRunningError):
            env.step(Action.WAIT)


class TestPickUpAndDrop:
    def test_pick_up_fails_when_nothing_is_in_range(self):
        env = make_env()

        result = drive(env, "P")

        assert not result.outcome.success
        assert result.outcome.error_code == "no_object_in_range"
        assert env.metrics.invalid_actions == 1
        assert env.world.robot.carrying is None
        assert event_types(env)[-1] == "PICKUP_FAILED"

    def test_pick_up_lifts_the_target_package(self):
        env = make_env()
        package = env.world.packages["package-001"]
        drive_to_face(env, package.position)

        result = drive(env, "P")

        assert result.outcome.success
        assert env.world.robot.carrying == "package-001"
        assert package.state is PackageState.CARRIED and package.position is None
        assert env.tasks.fsm.state is AgentState.PICKING_UP
        assert env.observe().agent.carrying is True

    def test_pick_up_fails_while_already_carrying(self):
        env = make_env("multi-step-delivery")
        drive_to_face(env, env.world.packages["package-001"].position)
        drive(env, "P")
        drive_to_face(env, env.world.packages["package-002"].position)

        result = drive(env, "P")

        assert result.outcome.error_code == "already_carrying"
        assert env.world.robot.carrying == "package-001"

    def test_pick_up_fails_for_a_package_that_is_not_the_current_target(self):
        env = make_env("multi-step-delivery")
        drive_to_face(env, env.world.packages["package-002"].position)

        result = drive(env, "P")

        assert result.outcome.error_code == "object_unavailable"
        assert env.world.packages["package-002"].state is PackageState.AVAILABLE
        assert Action.PICK_UP not in env.legal_actions()

    def test_drop_fails_when_not_carrying_or_when_the_cell_is_blocked(self):
        env = make_env()
        assert drive(env, "D").outcome.error_code == "not_carrying"

        drive_to_face(env, env.world.packages["package-001"].position)
        drive(env, "P")
        drive_to_face(env, (12, 2))  # a pallet stack
        result = drive(env, "D")

        assert result.outcome.error_code == "drop_blocked"
        assert env.world.robot.carrying == "package-001"
        assert env.metrics.invalid_actions == 2

    def test_dropping_outside_the_zone_puts_the_package_down_for_another_try(self):
        env = make_env()
        package = env.world.packages["package-001"]
        drive_to_face(env, package.position)
        drive(env, "P")
        drive(env, "B")
        dropped_at = env.world.robot.pose.front

        result = drive(env, "D")

        assert result.outcome.success and not result.outcome.delivered
        assert package.state is PackageState.AVAILABLE and package.position == dropped_at
        assert env.tasks.fsm.state is AgentState.DROPPING_OBJECT
        assert not env.done
        drive(env, "P")
        assert env.world.robot.carrying == "package-001"

    def test_dropping_into_the_delivery_zone_completes_the_task(self):
        env = make_env()
        package = env.world.packages["package-001"]
        drive_to_face(env, package.position)
        drive(env, "P")
        drive_to_face(env, (13, 1))

        result = drive(env, "D")

        assert result.outcome.delivered and result.done
        assert package.state is PackageState.DELIVERED and package.position == (13, 1)
        assert env.status is EpisodeStatus.COMPLETED
        assert env.tasks.fsm.state is AgentState.COMPLETED
        assert env.tasks.progress == 100
        assert event_types(env)[-1] == "TASK_COMPLETED"
        assert find_blocker(env.world, (13, 1)).kind is BlockerKind.PACKAGE


class TestTaskProgressAndFailure:
    def test_progress_and_checklist_follow_the_milestones(self):
        env = make_env()
        package = env.world.packages["package-001"]
        assert env.tasks.progress == 0
        assert [item.current for item in env.tasks.checklist()] == [True, False, False, False]

        drive_to_face(env, package.position)
        assert env.tasks.progress == 25
        drive(env, "P")
        assert env.tasks.progress == 50
        drive_to_face(env, (13, 1))
        assert env.tasks.progress == 75

        checklist = env.tasks.checklist()
        assert [item.done for item in checklist] == [True, True, True, False]
        assert checklist[3].current and checklist[3].label == "Deliver the blue package"

    def test_multi_step_task_requires_both_deliveries_in_order(self):
        env = make_env("multi-step-delivery")
        blue, amber = env.world.packages["package-001"], env.world.packages["package-002"]

        drive_to_face(env, blue.position)
        drive(env, "P")
        drive_to_face(env, (13, 1))
        drive(env, "D")
        assert not env.done
        assert env.tasks.completed_objectives == 1 and env.tasks.progress == 50
        assert env.observe().target.object_id == "package-002"

        drive_to_face(env, amber.position)
        drive(env, "P")
        drive_to_face(env, (0, 10))
        drive(env, "D")

        assert env.status is EpisodeStatus.COMPLETED
        assert env.summary()["packages_delivered"] == 2

    def test_reaching_the_step_limit_fails_the_task(self):
        env = make_env(replace(get_scenario("basic-delivery"), max_steps=4))

        drive(env, "WWWW")

        assert env.status is EpisodeStatus.FAILED
        assert env.failure_reason == "step_limit_exceeded"
        assert env.tasks.fsm.state is AgentState.FAILED
        assert event_types(env)[-1] == "TASK_FAILED"

    def test_too_many_collisions_fail_the_task(self):
        env = make_env(replace(get_scenario("basic-delivery"), max_collisions=2))

        drive(env, "BB")

        assert env.status is EpisodeStatus.FAILED
        assert env.failure_reason == "collision_limit_exceeded"
        assert env.summary()["completed"] is False


class TestMovingObstacles:
    def test_forklifts_patrol_back_and_forth_along_their_route(self):
        env = make_env("obstacle-navigation")
        forklift = env.world.obstacles[0]
        route = set(forklift.route)
        visited = {forklift.position}

        for _ in range(60):
            drive(env, "W")
            visited.add(forklift.position)

        assert visited == route
        assert not route & env.scenario.static_blocked

    def test_forklift_moves_only_on_its_period(self):
        env = make_env("obstacle-navigation")
        slow = next(o for o in env.world.obstacles if o.spec.period == 3)
        positions = [slow.position]

        for _ in range(6):
            drive(env, "W")
            positions.append(slow.position)

        changes = sum(1 for before, after in zip(positions, positions[1:], strict=False) if before != after)
        assert changes == 2

    def test_forklift_yields_when_the_robot_is_in_its_way(self):
        env = make_env("obstacle-navigation")
        forklift = env.world.obstacles[0]
        env.world.robot.position = forklift.next_position
        before = forklift.position

        drive(env, "WWWW")

        assert forklift.position == before

    def test_driving_into_a_forklift_is_a_collision(self):
        env = make_env("obstacle-navigation")
        forklift = next(o for o in env.world.obstacles if o.id == "forklift-001")
        x, y = forklift.position
        env.world.robot.position = (x, y - 1)
        env.world.robot.orientation = Orientation.NORTH

        result = drive(env, "F")

        assert result.outcome.collision.kind is BlockerKind.MOVING_OBSTACLE
        assert result.outcome.entity_id == "forklift-001"
        assert env.world.robot.position == (x, y - 1)
