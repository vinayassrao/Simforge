"""Scenario registry."""

from __future__ import annotations

from simulation.scenarios.base import ScenarioDefinition
from simulation.scenarios.warehouse import BASIC_DELIVERY, MULTI_STEP_DELIVERY, OBSTACLE_NAVIGATION

SCENARIOS: dict[str, ScenarioDefinition] = {
    scenario.id: scenario for scenario in (BASIC_DELIVERY, OBSTACLE_NAVIGATION, MULTI_STEP_DELIVERY)
}


class UnknownScenarioError(KeyError):
    """Raised when a scenario id is not registered."""


def get_scenario(scenario_id: str) -> ScenarioDefinition:
    try:
        return SCENARIOS[scenario_id]
    except KeyError:
        raise UnknownScenarioError(scenario_id) from None


def list_scenarios() -> list[ScenarioDefinition]:
    return list(SCENARIOS.values())


__all__ = ["SCENARIOS", "ScenarioDefinition", "UnknownScenarioError", "get_scenario", "list_scenarios"]
