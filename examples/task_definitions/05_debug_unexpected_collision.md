# Task 05: Debug an unexpected collision

## Task objective

A user reports: "My external agent collided with a forklift even though `MOVE_FORWARD` was in
`available_actions` in the observation it used." Find out whether this can happen, explain
why, and fix the agent or the documentation accordingly.

## Environment setup

- Scenario: `obstacle-navigation`, seed 7, external agent mode.
- The user's agent caches an observation and sends two actions for it.

## Initial state

- `available_actions` describes the world at the moment the observation was built.
- Forklifts move after each robot action.

## Required actions

1. Reproduce: start an episode, read one observation, send two `MOVE_FORWARD` actions towards
   a cell a forklift is about to enter, without reading the new observation in between.
2. Inspect the events of the run through `GET /api/v1/episodes/{id}/events/?category=collision`.
3. Decide where the fault lies: the simulation, the observation, or the agent's use of it.
4. Write a regression test that documents the behaviour.
5. Update the agent template or the docs so the mistake is harder to make.

## Expected final state

- A written explanation: an observation is valid for exactly one action; `next_position`
  shows where each forklift will try to go.
- A test proving that an action chosen from a fresh observation never collides when it is
  listed in `available_actions` and the target cell is not a forklift's `next_position`.
- A note in the template next to the main loop.

## Success criteria

- The reproduction produces the collision deterministically.
- The explanation matches the event log (the collision event names the forklift and the cell).
- No change to simulation rules is needed, and none is made.

## Failure conditions

- "Fixing" the report by making forklifts yield before the robot acts, which would change
  every seeded run.
- A conclusion that is not backed by a reproducing test.

## Validation method

```powershell
cd backend
python -m pytest tests/test_world_and_actions.py -k forklift
```

Then inspect the run in the web interface: Live activity, filter **Collisions**, and the
Route replay map in the evaluation report.

## Prompt for an AI coding agent

> Investigate a reported collision in SIMFORGE. An external agent collided with a forklift
> although `MOVE_FORWARD` was listed in `available_actions`. Read
> `WarehouseEnvironment.step` and `World.advance_obstacles` and state the exact order of
> events within one step. Write a test in `tests/test_world_and_actions.py` that reproduces
> the collision by reusing a stale observation for two consecutive actions, using the
> forklift's `next_position` to pick the cell. Then write a second test showing that using a
> fresh observation each step and treating `next_position` as blocked avoids it. Do not
> change simulation rules. Add a two-line comment above the loop in
> `examples/agents/custom_agent_template.py` warning that an observation is valid for one
> action only. Summarise the root cause in three sentences.
