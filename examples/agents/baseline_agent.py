"""External baseline agent: plans with breadth-first search and acts through the REST API.

It runs in its own process and knows nothing about the simulation's internals.
Everything it uses comes from the observation JSON.

Run it while the SIMFORGE server is up::

    python examples/agents/baseline_agent.py --scenario obstacle-navigation --seed 7

Open the Live Simulation page in the browser to watch the robot move.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque

from simforge_client import SimforgeClient, SimforgeError

Cell = tuple[int, int]
Pose = tuple[int, int, str]

VECTORS = {"NORTH": (0, 1), "EAST": (1, 0), "SOUTH": (0, -1), "WEST": (-1, 0)}
CLOCKWISE = ["NORTH", "EAST", "SOUTH", "WEST"]


def turn(orientation: str, step: int) -> str:
    return CLOCKWISE[(CLOCKWISE.index(orientation) + step) % 4]


def blocked_cells(observation: dict) -> set[Cell]:
    """Every cell the robot must not drive onto right now."""
    blocked = {tuple(cell) for cell in observation["obstacles"]["static"]}
    for zone in observation["zones"]:
        if zone["kind"] == "restricted":
            blocked.update(tuple(cell) for cell in zone["cells"])
    for item in observation["objects"]:
        if item["position"] is not None and item["state"] != "carried":
            blocked.add(tuple(item["position"]))
    for obstacle in observation["obstacles"]["moving"]:
        blocked.add(tuple(obstacle["position"]))
        blocked.add(tuple(obstacle["next_position"]))
    return blocked


def goal_poses(targets: list[Cell], passable) -> set[Pose]:
    """Poses next to a target cell, facing it."""
    poses = set()
    for x, y in targets:
        for orientation, (dx, dy) in VECTORS.items():
            stand = (x - dx, y - dy)
            if passable(stand):
                poses.add((stand[0], stand[1], orientation))
    return poses


def plan(start: Pose, goals: set[Pose], passable) -> list[str] | None:
    """Shortest list of movement actions from ``start`` to any goal pose."""
    queue = deque([start])
    came_from: dict[Pose, tuple[Pose, str] | None] = {start: None}
    while queue:
        pose = queue.popleft()
        if pose in goals:
            actions = []
            while came_from[pose] is not None:
                pose, action = came_from[pose]
                actions.append(action)
            return actions[::-1]
        x, y, orientation = pose
        dx, dy = VECTORS[orientation]
        successors = [
            ((x + dx, y + dy, orientation), "MOVE_FORWARD"),
            ((x - dx, y - dy, orientation), "MOVE_BACKWARD"),
            ((x, y, turn(orientation, -1)), "TURN_LEFT"),
            ((x, y, turn(orientation, 1)), "TURN_RIGHT"),
        ]
        for successor, action in successors:
            moved = successor[:2] != (x, y)
            if successor in came_from or (moved and not passable(successor[:2])):
                continue
            came_from[successor] = (pose, action)
            queue.append(successor)
    return None


def choose_action(observation: dict) -> str:
    """Observation in, one action out. This is the whole agent."""
    target = observation["target"]
    if target is None:
        return "WAIT"
    blocked = blocked_cells(observation)
    width, height = observation["grid"]["width"], observation["grid"]["height"]

    def passable(cell: Cell) -> bool:
        return 0 <= cell[0] < width and 0 <= cell[1] < height and cell not in blocked

    agent = observation["agent"]
    start: Pose = (agent["position"][0], agent["position"][1], agent["orientation"])
    if agent["carrying"]:
        free_zone = [tuple(cell) for cell in target["delivery_cells"] if passable(tuple(cell))]
        goals, final_action = goal_poses(free_zone, passable), "DROP"
    else:
        goals, final_action = (
            goal_poses([tuple(target["position"])], passable),
            "PICK_UP",
        )

    actions = plan(start, goals, passable)
    if actions is None:
        return "WAIT"  # A forklift is in the way; try again next step.
    return actions[0] if actions else final_action


def run(base_url: str, scenario: str, seed: int | None, delay: float) -> int:
    client = SimforgeClient(base_url)
    episode_id = client.create_episode(scenario, seed)
    observation = client.start(episode_id)
    print(f"Episode {episode_id} started: {observation['task']['instructions']}")

    done = False
    while not done:
        action = choose_action(observation)
        result = client.act(episode_id, action)
        observation, done = result["observation"], result["done"]
        if not result["success"]:
            print(f"  step {observation['step']}: {action} failed - {result['message']}")
        time.sleep(delay)

    report = client.evaluation(episode_id)
    print(f"Finished in {observation['step']} steps. Success: {report['success']}. Score: {report['score']}/100")
    for item in report["breakdown"]:
        print(f"  {item['label']:<20} {item['points']:>5} / {item['max_points']}")
    return 0 if report["success"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the external baseline agent against a SIMFORGE server.")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="Base URL of the SIMFORGE server.",
    )
    parser.add_argument("--scenario", default="basic-delivery")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--delay", type=float, default=0.15, help="Seconds to wait between actions.")
    arguments = parser.parse_args()
    try:
        return run(arguments.url, arguments.scenario, arguments.seed, arguments.delay)
    except SimforgeError as error:
        print(f"SIMFORGE error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
