"""Helpers shared by the simulation tests."""

from __future__ import annotations

from agents.astar_agent import AStarAgent
from simulation.environment import WarehouseEnvironment
from simulation.pathfinding import facing_poses, plan_actions
from simulation.scenarios import get_scenario
from simulation.scenarios.base import ScenarioDefinition
from simulation.types import Action, Cell

SHORTHAND = {
    "F": Action.MOVE_FORWARD,
    "B": Action.MOVE_BACKWARD,
    "L": Action.TURN_LEFT,
    "R": Action.TURN_RIGHT,
    "P": Action.PICK_UP,
    "D": Action.DROP,
    "W": Action.WAIT,
}


def make_env(scenario: str | ScenarioDefinition = "basic-delivery", seed: int = 7, start: bool = True):
    definition = get_scenario(scenario) if isinstance(scenario, str) else scenario
    env = WarehouseEnvironment(definition, seed, "test-episode")
    if start:
        env.start()
    return env


def drive(env: WarehouseEnvironment, moves: str):
    """Apply a string of shorthand actions, e.g. ``"LFFR"``. Returns the last step result."""
    result = None
    for symbol in moves:
        result = env.step(SHORTHAND[symbol])
    return result


def static_passable(env: WarehouseEnvironment):
    world = env.world
    blocked = set(world.scenario.static_blocked)
    blocked |= {package.position for package in world.packages.values() if package.position}

    def passable(cell: Cell) -> bool:
        return world.in_bounds(cell) and cell not in blocked

    return passable


def drive_to_face(env: WarehouseEnvironment, target: Cell) -> None:
    """Drive the robot until ``target`` is the cell directly in front of it."""
    passable = static_passable(env)
    actions = plan_actions(env.world.robot.pose, facing_poses([target], passable), passable)
    assert actions is not None, f"no route to face {target}"
    for action in actions:
        result = env.step(action)
        assert result.outcome.success, result.outcome.message
    assert env.world.robot.pose.front == target


def run_agent(env: WarehouseEnvironment, max_steps: int = 600) -> AStarAgent:
    """Let the A* agent drive until the episode ends."""
    agent = AStarAgent()
    for _ in range(max_steps):
        if env.done:
            break
        decision = agent.decide(env.observe())
        for note in decision.notes:
            env.note(note.event_type, note.description, note.data)
        env.step(decision.action)
    return agent


def event_types(env: WarehouseEnvironment) -> list[str]:
    return [event.type.value for event in env.events.all]
