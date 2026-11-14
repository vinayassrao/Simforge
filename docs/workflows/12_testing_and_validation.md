# 12. Testing and validation

## 1. Objective

Prove that the rules, the agent, the evaluation, the API and the interface behave as
described, with tests that check behaviour and not just status codes.

## 2. Technical requirements

- pytest and Coverage.py for the backend; Vitest for frontend logic and components;
  Playwright for end-to-end tests against the real server and the real Panda3D process.
- Tests must not depend on each other or on a shared database.

## 3. Implementation steps

1. **Rule tests** build a `WarehouseEnvironment` directly and drive it with shorthand strings
   such as `"LFFRF"`. They cover creation, movement, collisions, pick-up, drop, progress,
   failure, determinism and forklifts.
2. **Agent tests** cover A* plans, the state machine, re-planning and full runs of every
   scenario on several seeds.
3. **Controller tests** cover commands, modes, speed, reset and the clock, using a fake clock.
4. **Evaluation tests** cover each scoring rule with parametrised cases and two real runs.
5. **API tests** use FastAPI's `TestClient` with the `InlineGateway` and a temporary SQLite
   file per test. They include the WebSocket and a restart of the application.
6. **Panda3D tests** build the real scene graph, run the collision traverser, and render
   frames off-screen through the engine. They skip themselves where no graphics pipe exists.
7. **Frontend unit tests** cover formatting, filters, the WebSocket reducer and key components.
8. **End-to-end tests** start `run.py` on a spare port with a temporary database and drive
   Chromium: dashboard, navigation, launching a scenario, controls, live updates, manual
   keyboard control and the evaluation report.

## 4. Relevant files

- `backend/tests/` - `test_world_and_actions.py`, `test_pathfinding_and_agent.py`,
  `test_controller.py`, `test_evaluation.py`, `test_api.py`, `test_panda_scene.py`
- `backend/tests/e2e/test_frontend.py`
- `frontend/src/**/*.test.ts(x)`
- `backend/pyproject.toml` - pytest markers and coverage settings

## 5. Important code sections

```python
def test_failed_run_keeps_partial_points_but_is_not_a_success():
    report = evaluate_episode(summary(completed=False, failure_reason="step_limit_exceeded", ...))
    assert report["success"] is False
    assert report["score"] == 30.0

def test_panda_collision_system_agrees_with_the_grid_rules(self, scene):
    assert scene.physical_contacts() == []
    robot.setPos(1, 6, 0)                       # force the model into a shelf
    assert scene.physical_contacts() == ["shelf-1-6"]
```

## 6. Design decisions

- **Real components wherever possible.** The API tests use the real rules, database and
  evaluation; only rendering is left out. The end-to-end tests leave nothing out.
- **No hardcoded success.** Expected scores are derived from the scenario (for example, the
  A* agent must equal the baseline route), not copied from a previous run.
- **Markers, not skips by default.** `panda` and `e2e` tests can be deselected on a machine
  without a GPU or a browser: `pytest -m "not e2e"`.

## 7. Problems encountered

- A UTF-8 byte-order mark written into `pyproject.toml` by a shell command made pytest refuse
  to start with "Invalid statement at line 1". Rewriting the file without the mark fixed it.
- The first full run had six failures. Five were real findings (see workflows 03, 04, 05
  and 07); one was this documentation not existing yet.

## 8. Debugging approach

Run one test with `-x -k name` and read the assertion diff. For browser tests, Playwright can
save a screenshot at the point of failure.

## 9. Validation steps

```powershell
cd backend
python -m pytest -m "not e2e"                 # rules, agent, API, Panda3D
python -m pytest -m e2e                       # browser tests (needs the built frontend)
python -m coverage run -m pytest -m "not e2e"
python -m coverage report
cd ../frontend
npm test
```

## 10. Expected result

Every test passes. The coverage report is written to `backend/htmlcov/index.html`. The exact
counts and the coverage percentage are recorded in the project README.
