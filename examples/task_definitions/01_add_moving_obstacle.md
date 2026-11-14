# Task 01: Add a moving obstacle to the warehouse

## Task objective

Add a fourth forklift to the Obstacle Navigation scenario that patrols the bottom aisle
between `(2, 1)` and `(11, 1)`, moving one cell every two steps.

## Environment setup

- Repository at its current main branch, backend virtual environment active.
- Scenario: `obstacle-navigation`, default seed 7.

## Initial state

- Three forklifts are defined in `OBSTACLE_NAVIGATION.patrols`.
- Row `y = 1` is open floor from `x = 0` to `x = 15`.

## Required actions

1. Add `PatrolSpec("forklift-004", "Forklift D", (2, 1), (11, 1), period=2)` to the scenario.
2. Do not change `World`, the scene or the agent: they must pick the new patrol up from data.
3. Extend the scenario test so it expects four moving obstacles through the API.

## Expected final state

- The observation lists four entries under `obstacles.moving`, each with `position` and
  `next_position`.
- The 3D scene shows a fourth labelled forklift on the bottom aisle.
- The A* agent still completes the scenario without a collision.

## Success criteria

- `pytest -m "not e2e"` passes.
- `GET /api/v1/scenarios/obstacle-navigation/` returns `"moving_obstacles": 4`.
- A* runs on seeds 1, 7 and 23 finish with `collisions == 0`.

## Failure conditions

- The patrol route crosses a shelf, pallet or zone that must stay clear.
- Any code outside the scenario definition and tests had to change to render the forklift.
- The agent deadlocks (reaches the step limit while waiting).

## Validation method

```powershell
cd backend
python -m pytest tests/test_world_and_actions.py tests/test_pathfinding_and_agent.py
python -m simulation.panda_viewer --scenario obstacle-navigation --agent astar
```

## Prompt for an AI coding agent

> In `backend/simulation/scenarios/warehouse.py`, add a fourth forklift to the
> `OBSTACLE_NAVIGATION` scenario. It patrols between cells (2, 1) and (11, 1) with period 2,
> id `forklift-004`, name `Forklift D`. Before editing, confirm from `OBSTACLE_LAYOUT` that
> every cell on that row segment is open floor. Change only the scenario data and the tests.
> Update `test_scenarios_are_listed_with_their_task_information` to expect 4 moving obstacles
> for this scenario. Run `pytest -m "not e2e"` and report the result. Then report the step
> counts of the A* agent for seeds 1, 7 and 23 before and after your change.
