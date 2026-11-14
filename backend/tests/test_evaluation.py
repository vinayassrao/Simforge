import pytest

from app.evaluation import SCORING_RULES, evaluate_episode
from tests.helpers import drive, drive_to_face, make_env, run_agent


def summary(**overrides) -> dict:
    """A clean, completed single-package run. Override fields to model other outcomes."""
    base = {
        "episode_id": "ep-1",
        "agent_mode": "astar",
        "completed": True,
        "failure_reason": None,
        "packages_total": 1,
        "packages_collected": 1,
        "packages_delivered": 1,
        "collisions": 0,
        "restricted_entries": 0,
        "invalid_actions": 0,
        "total_actions": 40,
        "steps": 40,
        "max_steps": 150,
        "baseline_steps": 40,
        "progress": 100,
        "elapsed_seconds": 12.5,
        "incident_locations": [],
    }
    return {**base, **overrides}


def points(report: dict) -> dict[str, float]:
    return {item["key"]: item["points"] for item in report["breakdown"]}


def test_scoring_rules_add_up_to_one_hundred():
    assert sum(rule["max_points"] for rule in SCORING_RULES) == 100


def test_clean_optimal_run_scores_one_hundred():
    report = evaluate_episode(summary())

    assert report["score"] == 100.0 and report["success"] is True
    assert report["failure_reason"] is None
    assert points(report) == {
        "completion": 50,
        "pickup": 10,
        "delivery": 10,
        "safety": 15,
        "efficiency": 10,
        "validity": 5,
    }
    assert report["recommendations"] == ["Clean run. Try a harder scenario or a different seed to test robustness."]


def test_failed_run_keeps_partial_points_but_is_not_a_success():
    report = evaluate_episode(
        summary(completed=False, failure_reason="step_limit_exceeded", packages_delivered=0, steps=150, progress=50)
    )

    assert report["success"] is False
    assert report["failure_reason"] == "step_limit_exceeded"
    assert points(report) == {
        "completion": 0,
        "pickup": 10,
        "delivery": 0,
        "safety": 15,
        "efficiency": 0,
        "validity": 5,
    }
    assert report["score"] == 30.0
    assert report["metrics"]["path_efficiency"] is None
    assert any("step limit" in tip for tip in report["recommendations"])
    assert any("collected but not delivered" in tip for tip in report["recommendations"])


@pytest.mark.parametrize(
    ("collisions", "restricted", "expected"),
    [(0, 0, 15), (1, 0, 12), (2, 1, 6), (5, 0, 0), (9, 4, 0)],
)
def test_each_safety_incident_costs_three_points_down_to_zero(collisions, restricted, expected):
    report = evaluate_episode(summary(collisions=collisions, restricted_entries=restricted))

    assert points(report)["safety"] == expected


@pytest.mark.parametrize(("steps", "expected"), [(40, 10.0), (50, 8.0), (80, 5.0), (30, 10.0)])
def test_path_efficiency_compares_steps_with_the_baseline(steps, expected):
    report = evaluate_episode(summary(steps=steps, total_actions=steps))

    assert points(report)["efficiency"] == expected
    assert report["metrics"]["path_efficiency"] == pytest.approx(min(1, 40 / steps))


def test_invalid_actions_reduce_the_validity_score():
    report = evaluate_episode(summary(invalid_actions=10, total_actions=40))

    assert points(report)["validity"] == 3.75
    assert report["metrics"]["valid_action_rate"] == 0.75
    assert evaluate_episode(summary(total_actions=0, steps=0))["breakdown"][-1]["points"] == 0


def test_partial_delivery_is_scored_proportionally():
    report = evaluate_episode(
        summary(
            completed=False,
            failure_reason="collision_limit_exceeded",
            packages_total=2,
            packages_collected=2,
            packages_delivered=1,
            collisions=8,
        )
    )

    assert points(report)["pickup"] == 10 and points(report)["delivery"] == 5
    assert points(report)["safety"] == 0
    assert report["failure_explanation"] == "Too many collisions or restricted-area entries."


def test_score_always_equals_the_sum_of_its_breakdown_and_stays_in_range():
    cases = [
        summary(),
        summary(collisions=3, invalid_actions=7, steps=90, total_actions=90),
        summary(completed=False, failure_reason="step_limit_exceeded", packages_collected=0, packages_delivered=0),
        summary(completed=False, failure_reason=None, packages_delivered=0),
    ]
    for case in cases:
        report = evaluate_episode(case)
        assert report["score"] == pytest.approx(sum(points(report).values()), abs=0.05)
        assert 0 <= report["score"] <= 100
        assert all(0 <= item["points"] <= item["max_points"] for item in report["breakdown"])
    assert evaluate_episode(cases[-1])["failure_reason"] == "aborted"


def test_same_summary_always_gets_the_same_report():
    assert evaluate_episode(summary(collisions=2)) == evaluate_episode(summary(collisions=2))


def test_real_agent_run_is_scored_from_its_actual_summary():
    env = make_env("obstacle-navigation", seed=7)
    run_agent(env)

    report = evaluate_episode({**env.summary(), "agent_mode": "astar", "elapsed_seconds": 3.0})

    assert report["success"] is True
    assert report["metrics"]["steps"] == env.world.step_count
    assert points(report)["efficiency"] == pytest.approx(10 * env.baseline_steps / env.world.step_count, abs=0.01)
    assert "built-in A* agent completed the task" in report["behaviour_summary"]


def test_real_manual_run_with_mistakes_loses_the_matching_points():
    env = make_env()
    drive(env, "BPD")  # one wall collision and two invalid actions
    drive_to_face(env, env.world.packages["package-001"].position)
    drive(env, "P")
    drive_to_face(env, (13, 1))
    drive(env, "D")

    report = evaluate_episode({**env.summary(), "agent_mode": "manual"})

    assert report["success"] is True
    assert points(report)["safety"] == 12
    assert points(report)["validity"] == pytest.approx(5 * (env.metrics.actions - 2) / env.metrics.actions, abs=0.01)
    assert report["incident_locations"] == [{"kind": "collision", "cell": [-1, 0], "step": 1, "blocker": "wall"}]
    assert report["score"] < 100
