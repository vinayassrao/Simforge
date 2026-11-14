# API reference

Base URL: `http://127.0.0.1:8000/api/v1`. Interactive documentation (Swagger UI) is served at
`/api/docs`, and the OpenAPI schema at `/api/openapi.json`. No authentication: the server is
meant for local use.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health/` | Service status, active episode, engine performance |
| GET | `/overview/` | Dashboard figures computed from stored runs |
| GET | `/scenarios/` | List scenarios |
| GET | `/scenarios/{id}/` | Scenario detail: task, layout, scoring |
| GET | `/scenarios/{id}/thumbnail/` | Panda3D render of the starting scene (JPEG) |
| POST | `/episodes/` | Create an episode and load it into the simulation |
| GET | `/episodes/` | List episodes; filters `scenario_id`, `agent_mode`, `status`, `min_score`, `limit` |
| GET | `/episodes/{id}/` | One episode with trajectory and incidents |
| POST | `/episodes/{id}/start/` | Start |
| POST | `/episodes/{id}/pause/` | Pause |
| POST | `/episodes/{id}/resume/` | Resume |
| POST | `/episodes/{id}/reset/` | Rebuild from the same seed |
| POST | `/episodes/{id}/step/` | Advance exactly one step |
| POST | `/episodes/{id}/speed/` | Playback speed of the built-in agent |
| GET | `/episodes/{id}/state/` | Full live snapshot |
| GET | `/episodes/{id}/observation/` | What the agent sees |
| POST | `/episodes/{id}/actions/` | Submit one action |
| GET | `/episodes/{id}/events/` | Events; filters `category`, `after_seq`, `limit` |
| GET | `/episodes/{id}/evaluation/` | Evaluation report |
| GET | `/episodes/{id}/export/?format=json|csv` | Download the run |
| GET | `/evaluations/` | All evaluated runs with aggregates |
| POST | `/simulation/view/` | Toggle overlays in the 3D view |
| POST | `/simulation/camera/` | Reset, zoom or change the camera preset |
| GET | `/simulation/frame/` | Latest rendered frame (JPEG) |
| GET | `/simulation/stream/` | Live MJPEG stream |
| POST | `/simulation/native-viewer/` | Open the desktop Panda3D viewer on the server machine |
| GET | `/agents/` | Agent types, action schema, state machine, scoring rules |
| GET | `/documents/`, `/documents/{slug}/` | The built-in guides |

WebSocket: `ws://127.0.0.1:8000/ws/episodes/{id}/`. Messages are JSON objects with a `type`
of `hello`, `state`, `events`, `finished`, `status` or `perf`.

## The agent loop

```bash
# create an episode for an external agent
curl -X POST http://127.0.0.1:8000/api/v1/episodes/ \
  -H "Content-Type: application/json" \
  -d '{"scenario_id": "basic-delivery", "agent_mode": "external", "seed": 7}'
```

```json
{"id": "ep-3f9a1c2e", "scenario_id": "basic-delivery", "agent_mode": "external", "seed": 7,
 "status": "created", "steps": 0, "score": null, "is_active": true}
```

```bash
curl -X POST http://127.0.0.1:8000/api/v1/episodes/ep-3f9a1c2e/start/
curl -X POST http://127.0.0.1:8000/api/v1/episodes/ep-3f9a1c2e/actions/ \
  -H "Content-Type: application/json" -d '{"action": "MOVE_FORWARD"}'
```

```json
{"action": "MOVE_FORWARD", "success": true, "message": "Moved forward from [0, 0] to [1, 0].",
 "error_code": null, "done": false, "observation": {"step": 1, "agent": {"position": [1, 0]}}}
```

A rejected action is still a `200`. It uses one step and explains itself:

```json
{"action": "PICK_UP", "success": false, "error_code": "no_object_in_range",
 "message": "Pick-up failed: There is no package directly in front of the robot.", "done": false}
```

## Errors

Every error has the same shape:

```json
{"error": {"code": "invalid_state", "message": "Start the episode before sending actions.", "details": null}}
```

| Status | Codes | Meaning |
|---|---|---|
| 404 | `episode_not_found`, `unknown_scenario`, `document_not_found`, `not_found` | The thing does not exist |
| 409 | `invalid_state`, `episode_not_active`, `agent_controlled`, `not_evaluated` | Wrong moment for this request |
| 422 | `validation_error`, `invalid_speed`, `invalid_camera` | The request data is invalid; `details` lists the fields |
| 503 | `simulation_unavailable`, `rendering_unavailable` | The simulation process or the renderer is not available |

## Action error codes

| Code | Action | Reason |
|---|---|---|
| `collision` | moves | The target cell is blocked; counted as a collision |
| `no_object_in_range` | `PICK_UP` | Nothing in the cell in front |
| `already_carrying` | `PICK_UP` | The robot already holds a package |
| `object_unavailable` | `PICK_UP` | Already delivered, or not the current target |
| `not_carrying` | `DROP` | Nothing to drop |
| `drop_blocked` | `DROP` | The cell in front is occupied |
