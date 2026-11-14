# Task 03: Change the robot movement mechanics

## Task objective

Add two strafing actions, `MOVE_LEFT` and `MOVE_RIGHT`, that slide the robot one cell
sideways without changing its orientation, as an omnidirectional drive would.

## Environment setup

- Scenario: `basic-delivery`, seed 7, robot at `(0, 0)` facing east.

## Initial state

- `Action` has seven members. `apply_move` and `MOVE_ACTIONS` in `pathfinding.py` know four
  movement actions. The frontend control pad has seven buttons.

## Required actions

1. Add the two actions to `simulation/types.py`.
2. Handle them in `ActionExecutor._move` (target cell is the left or right neighbour) and in
   `legal_actions`.
3. Add them to `apply_move` and `MOVE_ACTIONS` so A* can plan with them.
4. Add entries to `ACTION_DESCRIPTIONS`.
5. Add the two buttons and key bindings to `CONTROLS` in `AgentPanel.tsx` and to the
   `ActionName` type.
6. Add tests for movement, collision and planning.

## Expected final state

- From `(0, 0)` facing east, `MOVE_LEFT` moves to `(0, 1)` and the robot still faces east.
- `MOVE_RIGHT` at `(0, 0)` facing east is a collision with the wall.
- The baseline route for Basic Delivery becomes shorter than 34 steps, because fewer turns
  are needed, and the A* agent still equals the baseline.

## Success criteria

- All tests pass, including the test that the A* agent matches the baseline.
- The observation schema lists nine actions.
- The robot never changes orientation during a strafe.

## Failure conditions

- The agent's step count is higher than the new baseline in the static scenario.
- A strafe passes through an obstacle.
- The frontend type check fails because `ActionName` was not updated.

## Validation method

```powershell
cd backend
python -m pytest tests/test_world_and_actions.py tests/test_pathfinding_and_agent.py
cd ../frontend
npm run typecheck
```

## Prompt for an AI coding agent

> Add strafing to the warehouse robot. Introduce `MOVE_LEFT` and `MOVE_RIGHT` in
> `backend/simulation/types.py`. A strafe moves the robot one cell to its left or right
> (relative to its orientation) and keeps the orientation. Implement it in
> `ActionExecutor._move` by generalising how the target cell is computed, and make
> `legal_actions` report it. Extend `apply_move` and `MOVE_ACTIONS` in `pathfinding.py`.
> Add descriptions to `ACTION_DESCRIPTIONS`. In the frontend, extend the `ActionName` union
> and the `CONTROLS` list with labelled buttons (keys Z and C). Add tests: a successful
> strafe, a strafe into the wall, and a pathfinding case where strafing gives a shorter plan
> than turning. Report the old and new baseline step counts for all three scenarios.
