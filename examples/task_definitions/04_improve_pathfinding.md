# Task 04: Improve pathfinding around moving obstacles

## Task objective

Reduce the steps the A* agent spends waiting or detouring in the Obstacle Navigation
scenario by predicting forklift positions over the next few steps, instead of blocking only
their current and next cell.

## Environment setup

- Scenario: `obstacle-navigation`, seeds 1, 7 and 2.
- Reference results with the current agent: 54, 66 and 58 steps against a baseline of 50.

## Initial state

- `AStarAgent._moving_obstacle_cells` returns each forklift's `position` and `next_position`.
- The observation does not expose a forklift's full route or period.

## Required actions

1. Extend `MovingObstacleView` with `route` (list of cells) and `period`, and fill them in
   `WarehouseEnvironment.observe`.
2. In the agent, predict each forklift's cell for the next `LOOKAHEAD_STEPS` steps.
3. Make the search time-aware: a cell is blocked for a pose only if a forklift is predicted
   to be there when the robot would arrive.
4. Keep the fallback: if no time-aware route exists, wait.
5. Add tests and record the new step counts.

## Expected final state

- The agent completes every seed without a collision.
- The total steps over the three reference seeds are lower than 178.
- The baseline and the scoring are unchanged.

## Success criteria

- `collisions == 0` and `invalid_actions == 0` on seeds 1, 7, 2 and at least five more.
- Average steps on the reference seeds decrease.
- Planning one step takes under 5 ms (measured with `time.perf_counter`).

## Failure conditions

- Any collision on any tested seed.
- The agent reads forklift state from the world instead of the observation.
- The Basic Delivery result changes from 34 steps.

## Validation method

```powershell
cd backend
python -m pytest tests/test_pathfinding_and_agent.py
```

Compare the Evaluations page before and after: path efficiency for A* runs on Obstacle
Navigation should increase.

## Prompt for an AI coding agent

> Improve `backend/agents/astar_agent.py` so it predicts forklift motion. First extend the
> observation: add `route` and `period` to `MovingObstacleView` in
> `simulation/observation.py` and populate them in `WarehouseEnvironment.observe`. Then
> implement a helper that, given a forklift view and the current step, returns its predicted
> cell at step `t` assuming it never has to yield. Change the planner call so a cell is
> considered blocked at arrival time `t` if any forklift is predicted on it at `t` or `t+1`,
> for `t` up to 8 steps ahead; beyond that, fall back to the current behaviour. Do not import
> anything from `simulation.world`. Report steps for seeds 1, 7, 2 before and after, and
> confirm zero collisions on ten seeds.
