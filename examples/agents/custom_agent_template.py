"""Template for your own SIMFORGE agent.

Copy this file, then replace the body of ``choose_action``. The loop around it
never changes: read the observation, pick an action, send it, repeat.

    python examples/agents/custom_agent_template.py --scenario basic-delivery

The example policy below is deliberately simple (and not very good): it walks
at random among the actions that would succeed, and picks up or drops whenever
that is possible. Run it once, read its evaluation report, then make it smarter.
"""

from __future__ import annotations

import argparse
import random
import sys

from simforge_client import SimforgeClient, SimforgeError


def choose_action(observation: dict, rng: random.Random) -> str:
    """Decide the next action.

    Useful fields in ``observation``:

    - ``agent``: position [x, y], orientation (NORTH/EAST/SOUTH/WEST), state, carrying
    - ``target``: the package to fetch next, its position, and its delivery cells
    - ``obstacles.static``: cells that are always blocked
    - ``obstacles.moving``: forklifts, with their position and next_position
    - ``zones``: collection, delivery and restricted areas with their cells
    - ``available_actions``: the actions that would succeed right now
    - ``task``: instructions, progress percentage and the checklist
    """
    available = observation["available_actions"]

    # Interactions first: PICK_UP is only available when the target is directly ahead.
    if "PICK_UP" in available:
        return "PICK_UP"

    # DROP is available whenever the cell ahead is free, so check that it is a delivery cell.
    if "DROP" in available and faces_delivery_cell(observation):
        return "DROP"

    # Otherwise wander, preferring to drive forward.
    moves = [action for action in available if action in ("MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT")]
    if "MOVE_FORWARD" in moves and rng.random() < 0.7:
        return "MOVE_FORWARD"
    return rng.choice(moves) if moves else "WAIT"


def faces_delivery_cell(observation: dict) -> bool:
    vectors = {"NORTH": (0, 1), "EAST": (1, 0), "SOUTH": (0, -1), "WEST": (-1, 0)}
    x, y = observation["agent"]["position"]
    dx, dy = vectors[observation["agent"]["orientation"]]
    target = observation["target"]
    return target is not None and [x + dx, y + dy] in target["delivery_cells"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a custom agent against a SIMFORGE server.")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--scenario", default="basic-delivery")
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="World seed. The same seed gives the same world.",
    )
    arguments = parser.parse_args()
    rng = random.Random(arguments.seed)

    try:
        client = SimforgeClient(arguments.url)
        episode_id = client.create_episode(arguments.scenario, arguments.seed)
        observation = client.start(episode_id)
        done = False
        while not done:
            result = client.act(episode_id, choose_action(observation, rng))
            observation, done = result["observation"], result["done"]
        report = client.evaluation(episode_id)
    except SimforgeError as error:
        print(f"SIMFORGE error: {error}", file=sys.stderr)
        return 2

    print(f"Episode {episode_id}: success={report['success']} score={report['score']}/100")
    print("Recommendations:")
    for tip in report["recommendations"]:
        print(f"  - {tip}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
