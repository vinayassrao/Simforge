# 03. Agent implementation

## 1. Objective

Give the robot a discrete action set with explicit rules, a finite-state machine that tracks
the task, and three ways to drive it: manual, the built-in A* agent, and external code.

## 2. Technical requirements

- Seven actions: `MOVE_FORWARD`, `MOVE_BACKWARD`, `TURN_LEFT`, `TURN_RIGHT`, `PICK_UP`, `DROP`, `WAIT`.
- Seven states: `IDLE`, `NAVIGATING_TO_OBJECT`, `PICKING_UP`, `NAVIGATING_TO_TARGET`,
  `DROPPING_OBJECT`, `COMPLETED`, `FAILED`.
- Every agent goes through the same code path. No mode may bypass a rule.

## 3. Implementation steps

1. `ActionExecutor.execute` dispatches an action to `_move`, `_turn`, `_pick_up` or `_drop`.
   Each returns an `ActionOutcome` with `success`, a message, an error code and an event type.
2. `ActionExecutor.legal_actions` reuses the same precondition checks to list what would
   succeed right now. The observation publishes it as `available_actions`.
3. `AgentStateMachine` holds `ALLOWED_TRANSITIONS`. `transition` raises on anything else.
4. `PICKING_UP` and `DROPPING_OBJECT` are transient: `settle()` leaves them at the start of
   the next step.
5. The `Agent` protocol is one method: `decide(observation) -> Decision`.
6. `SimulationController` owns the mode. In A* mode it calls the agent on a timer; in manual
   and external mode it accepts actions from the API.

## 4. Relevant files

- `backend/simulation/actions.py` - rules and `ACTION_DESCRIPTIONS`
- `backend/simulation/agent.py` - the state machine
- `backend/agents/base.py`, `backend/agents/astar_agent.py` - the agent interface and baseline
- `backend/simulation/controller.py` - modes, speed, stepping

## 5. Important code sections

```python
ALLOWED_TRANSITIONS = {
    S.IDLE: frozenset({S.NAVIGATING_TO_OBJECT, S.FAILED}),
    S.NAVIGATING_TO_OBJECT: frozenset({S.PICKING_UP, S.FAILED}),
    S.PICKING_UP: frozenset({S.NAVIGATING_TO_TARGET, S.FAILED}),
    S.NAVIGATING_TO_TARGET: frozenset({S.DROPPING_OBJECT, S.FAILED}),
    S.DROPPING_OBJECT: frozenset({S.NAVIGATING_TO_OBJECT, S.COMPLETED, S.FAILED}),
}

def _apply(self, env, action):        # controller: every mode ends up here
    result = env.step(action)
```

## 6. Design decisions

- **A blocked move is a collision, not an invalid action.** The request was well formed; the
  outcome was unsafe. Invalid actions are failed pick-ups and drops.
- **The built-in agent sees only the observation.** It has no reference to the world, so it
  cannot cheat and it is a fair baseline for external agents.
- **A failed action still costs a step.** Otherwise an agent could probe the world for free.
- **`legal_actions` and `execute` share their checks**, so the list can never disagree with
  what actually happens.

## 7. Problems encountered

- The last drop moved the state from `NAVIGATING_TO_TARGET` through `DROPPING_OBJECT` to
  `COMPLETED` inside one step, and only one state-change event was logged. A test counting
  the events caught it; the logger now emits one event per entry in the state history.

## 8. Debugging approach

The state machine keeps a `history` list. Asserting on the full history of a real run is a
compact way to check every transition at once.

## 9. Validation steps

```powershell
cd backend
python -m pytest tests/test_world_and_actions.py tests/test_pathfinding_and_agent.py -k "PickUp or StateMachine or Movement"
```

## 10. Expected result

A complete delivery visits the six states in order. A failed action returns a clear reason
such as `no_object_in_range`, `already_carrying`, `object_unavailable` or `drop_blocked`.
