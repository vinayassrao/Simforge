"""The evaluation engine: turns the raw results of an episode into a 100-point report.

The scoring is a pure function of the episode summary, so the same run always
receives the same score. Task success is reported separately from the score: a
run can earn partial points and still be a failure.
"""

from __future__ import annotations

from typing import Any

COMPLETION_POINTS = 50.0
PICKUP_POINTS = 10.0
DELIVERY_POINTS = 10.0
SAFETY_POINTS = 15.0
SAFETY_PENALTY_PER_INCIDENT = 3.0
EFFICIENCY_POINTS = 10.0
VALIDITY_POINTS = 5.0

SCORING_RULES: list[dict[str, Any]] = [
    {
        "key": "completion",
        "label": "Task completion",
        "max_points": COMPLETION_POINTS,
        "rule": "All 50 points if every package is delivered, otherwise 0.",
    },
    {
        "key": "pickup",
        "label": "Correct pickup",
        "max_points": PICKUP_POINTS,
        "rule": "10 x (packages collected / packages assigned).",
    },
    {
        "key": "delivery",
        "label": "Correct delivery",
        "max_points": DELIVERY_POINTS,
        "rule": "10 x (packages delivered / packages assigned).",
    },
    {
        "key": "safety",
        "label": "Collision safety",
        "max_points": SAFETY_POINTS,
        "rule": "15 minus 3 per collision or restricted-area entry, never below 0.",
    },
    {
        "key": "efficiency",
        "label": "Path efficiency",
        "max_points": EFFICIENCY_POINTS,
        "rule": "10 x (baseline route steps / steps used), capped at 10. Only for completed tasks.",
    },
    {
        "key": "validity",
        "label": "Valid actions",
        "max_points": VALIDITY_POINTS,
        "rule": "5 x (valid actions / total actions).",
    },
]

FAILURE_EXPLANATIONS = {
    "step_limit_exceeded": "The step limit was reached before every package was delivered.",
    "collision_limit_exceeded": "Too many collisions or restricted-area entries.",
    "time_limit_exceeded": "The time limit ran out.",
    "aborted": "The run was stopped before it finished.",
}


def _ratio(part: float, whole: float) -> float:
    return part / whole if whole else 0.0


def evaluate_episode(summary: dict[str, Any]) -> dict[str, Any]:
    """Score one finished episode. ``summary`` comes from ``WarehouseEnvironment.summary``."""
    completed = bool(summary["completed"])
    total_packages = summary["packages_total"]
    collected = summary["packages_collected"]
    delivered = summary["packages_delivered"]
    incidents = summary["collisions"] + summary["restricted_entries"]
    total_actions = summary["total_actions"]
    invalid = summary["invalid_actions"]
    steps = summary["steps"]
    baseline = summary.get("baseline_steps")

    efficiency = min(1.0, _ratio(baseline, steps)) if completed and baseline else None
    valid_rate = _ratio(total_actions - invalid, total_actions)

    points = {
        "completion": COMPLETION_POINTS if completed else 0.0,
        "pickup": PICKUP_POINTS * _ratio(collected, total_packages),
        "delivery": DELIVERY_POINTS * _ratio(delivered, total_packages),
        "safety": max(0.0, SAFETY_POINTS - SAFETY_PENALTY_PER_INCIDENT * incidents),
        "efficiency": EFFICIENCY_POINTS * efficiency if efficiency is not None else 0.0,
        "validity": VALIDITY_POINTS * valid_rate,
    }
    explanations = {
        "completion": "Every package was delivered." if completed else "The task was not completed.",
        "pickup": f"{collected} of {total_packages} packages collected.",
        "delivery": f"{delivered} of {total_packages} packages delivered.",
        "safety": (
            "No collisions or restricted-area entries."
            if incidents == 0
            else f"{summary['collisions']} collision(s) and {summary['restricted_entries']} restricted-area entry(ies)."
        ),
        "efficiency": (
            f"Used {steps} steps; the baseline route needs {baseline}."
            if efficiency is not None
            else "Only scored when the task is completed."
        ),
        "validity": (
            f"{total_actions - invalid} of {total_actions} actions were valid."
            if total_actions
            else "No actions were submitted."
        ),
    }
    breakdown = [
        {
            "key": rule["key"],
            "label": rule["label"],
            "points": round(points[rule["key"]], 2),
            "max_points": rule["max_points"],
            "rule": rule["rule"],
            "explanation": explanations[rule["key"]],
        }
        for rule in SCORING_RULES
    ]
    failure_reason = None if completed else (summary.get("failure_reason") or "aborted")
    metrics = {
        "task_completed": completed,
        "packages_total": total_packages,
        "packages_collected": collected,
        "packages_delivered": delivered,
        "collisions": summary["collisions"],
        "restricted_entries": summary["restricted_entries"],
        "invalid_actions": invalid,
        "total_actions": total_actions,
        "steps": steps,
        "max_steps": summary.get("max_steps"),
        "elapsed_seconds": summary.get("elapsed_seconds", 0.0),
        "baseline_steps": baseline,
        "path_efficiency": round(efficiency, 4) if efficiency is not None else None,
        "valid_action_rate": round(valid_rate, 4),
        "progress": summary.get("progress", 0),
    }
    return {
        "episode_id": summary["episode_id"],
        "score": round(sum(points.values()), 1),
        "max_score": 100.0,
        "success": completed,
        "failure_reason": failure_reason,
        "failure_explanation": FAILURE_EXPLANATIONS.get(failure_reason) if failure_reason else None,
        "breakdown": breakdown,
        "metrics": metrics,
        "behaviour_summary": _behaviour_summary(summary, metrics),
        "recommendations": _recommendations(metrics, failure_reason),
        "incident_locations": summary.get("incident_locations", []),
    }


def _behaviour_summary(summary: dict[str, Any], metrics: dict[str, Any]) -> str:
    agent = {
        "astar": "The built-in A* agent",
        "manual": "The manual operator",
        "external": "The external agent",
    }.get(summary.get("agent_mode", ""), "The agent")
    outcome = (
        f"completed the task in {metrics['steps']} steps"
        if metrics["task_completed"]
        else f"did not complete the task ({metrics['progress']}% of milestones reached in {metrics['steps']} steps)"
    )
    safety = (
        "without any safety incident"
        if metrics["collisions"] + metrics["restricted_entries"] == 0
        else f"with {metrics['collisions']} collision(s) and {metrics['restricted_entries']} restricted-area entry(ies)"
    )
    delivered = f"{metrics['packages_delivered']} of {metrics['packages_total']} package(s)"
    return f"{agent} {outcome}, {safety}, delivering {delivered}."


def _recommendations(metrics: dict[str, Any], failure_reason: str | None) -> list[str]:
    tips: list[str] = []
    if failure_reason == "step_limit_exceeded":
        tips.append("Plan the whole route before moving; the run ended at the step limit.")
    if failure_reason == "collision_limit_exceeded":
        tips.append("Check 'available_actions' before moving: a move that is not listed will collide.")
    if metrics["collisions"]:
        tips.append("Treat shelves, pallets, packages and forklifts as blocked cells when planning.")
    if metrics["restricted_entries"]:
        tips.append("Route around the restricted area; each entry costs 3 safety points.")
    if metrics["invalid_actions"]:
        tips.append("Only pick up when the target package is directly in front, and drop only into a free cell.")
    efficiency = metrics["path_efficiency"]
    if efficiency is not None and efficiency < 0.85:
        tips.append("The route was noticeably longer than the baseline; fewer turns and detours would raise the score.")
    if not metrics["task_completed"] and metrics["packages_collected"] > metrics["packages_delivered"]:
        tips.append("A package was collected but not delivered: drop it while facing a cell inside its delivery zone.")
    if not tips:
        tips.append("Clean run. Try a harder scenario or a different seed to test robustness.")
    return tips
