# Task 02: Implement a weight-limited pickup interaction

## Task objective

Make package weight matter: the robot may lift at most 5 kg. A `PICK_UP` on a heavier package
must fail with a clear reason.

## Environment setup

- Scenario: `multi-step-delivery`. The blue package weighs 2.5 kg and the amber one 4.0 kg.
- For the test, a scenario copy with the amber package set to 8.0 kg (`dataclasses.replace`).

## Initial state

- `PackageSpec.weight_kg` exists and is shown in the observation, but no rule reads it.
- `_pickup_error` checks carrying, range, delivered and target order.

## Required actions

1. Add `MAX_LIFT_KG = 5.0` to `simulation/actions.py`.
2. In `_pickup_error`, after the existing checks, return
   `("object_too_heavy", "...")` when the package is heavier than the limit.
3. Add the precondition to `ACTION_DESCRIPTIONS[Action.PICK_UP]`.
4. Add tests for the failing and the passing case.

## Expected final state

- Picking up the 8 kg package fails: `success` is false, `error_code` is `object_too_heavy`,
  the package stays `available`, and one invalid action is counted.
- `PICK_UP` is not in `available_actions` while facing that package.
- The two built-in scenarios behave exactly as before.

## Success criteria

- New tests pass; all existing tests pass unchanged.
- The Agent Studio action table shows the new precondition without frontend changes.

## Failure conditions

- The check is placed in the API or the agent instead of the action rules.
- `legal_actions` and `execute` disagree about the heavy package.
- An existing scenario can no longer be completed.

## Validation method

```powershell
cd backend
python -m pytest tests/test_world_and_actions.py -k PickUp
```

## Prompt for an AI coding agent

> Add a lifting limit to the robot in `backend/simulation/actions.py`. Define
> `MAX_LIFT_KG = 5.0`. Extend `ActionExecutor._pickup_error` so that a package heavier than
> the limit returns the error code `object_too_heavy` with a message that names the package
> and both weights. Keep the existing order of checks and add this one last. Because
> `legal_actions` already calls `_pickup_error`, do not add a second check anywhere else.
> Update the `PICK_UP` entry in `ACTION_DESCRIPTIONS`. Write two tests in
> `tests/test_world_and_actions.py`: one with a scenario copy where package-002 weighs 8 kg
> (expect the failure, an unchanged package state and `invalid_actions == 1`), and one
> confirming the default 4 kg package can still be lifted. Run the suite and report.
