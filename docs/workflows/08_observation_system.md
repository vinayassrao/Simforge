# 08. Observation system

## 1. Objective

Give every agent the same structured, validated description of the world on each step, and
show it in the interface both as readable text and as raw JSON.

## 2. Technical requirements

- A Pydantic schema, so the structure is validated and documented automatically.
- The observation must be built from the live simulation state, never from a cache.
- It must contain enough information to plan without any other endpoint.

## 3. Implementation steps

1. `simulation/observation.py` defines the models: `AgentView`, `TargetView`, `ObjectView`,
   `ZoneView`, `ObstaclesView`, `GridView`, `TaskView`, `EventView` and `Observation`.
2. `WarehouseEnvironment.observe()` fills a dictionary from the world, the task manager and
   the event log, then validates it with `Observation.model_validate`.
3. `available_actions` comes from `ActionExecutor.legal_actions`, the same checks the action
   system uses.
4. Each forklift reports `position` and `next_position`, so a planner can avoid the cell it
   is about to enter.
5. The controller includes the observation in every `state` message and in every action reply.
6. The API returns it from `GET /api/v1/episodes/{id}/observation/`. The JSON Schema is
   published in the Agent Studio and in the OpenAPI document.

## 4. Relevant files

- `backend/simulation/observation.py` - the schema
- `backend/simulation/environment.py` - `observe`
- `frontend/src/components/live/ObservationPanel.tsx` - readable and raw views

## 5. Important code sections

```json
{
  "episode_id": "ep-2763cbd0",
  "step": 12,
  "agent": {"position": [4, 2], "orientation": "EAST", "state": "NAVIGATING_TO_OBJECT", "carrying": false},
  "target": {"object_id": "package-001", "position": [14, 10], "delivery_cells": [[13, 0], [13, 1], [14, 0], [14, 1]]},
  "obstacles": {"static": [[1, 6], [1, 7]], "moving": [{"id": "forklift-001", "position": [5, 5], "next_position": [6, 5]}]},
  "available_actions": ["MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT", "WAIT"],
  "task": {"progress": 25, "current_objective": "Collect the blue package"}
}
```

## 6. Design decisions

- **Full observability.** The agent sees the whole grid. The project is about integration and
  evaluation, not perception. A partial view would be a new scenario option.
- **The schema lives with the simulation**, not with the web layer, because the simulation is
  what guarantees it.
- **Plain-language labels in the interface.** The panel is titled "What the agent currently
  sees"; the technical term and the raw JSON are one click away.

## 7. Problems encountered

- Tuples become JSON arrays. Tests that compare an observation from the API with internal
  state have to compare `[1, 0]` with `(1, 0)` deliberately, or re-validate the JSON through
  the Pydantic model first.

## 8. Debugging approach

The **Raw JSON** tab in the live workspace shows the exact payload an agent receives at that
moment, with a copy button. Pasting it into a test reproduces any decision.

## 9. Validation steps

```powershell
cd backend
python -m pytest tests/test_pathfinding_and_agent.py -k Observation
python -m pytest tests/test_api.py -k observation
```

## 10. Expected result

The observation validates against the schema, matches the world state field by field, and
lists only actions that would really succeed.
