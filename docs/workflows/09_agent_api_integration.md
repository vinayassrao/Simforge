# 09. Agent API integration

## 1. Objective

Connect the Panda3D simulation to the web: a REST API for commands and queries, a WebSocket
for live updates, a frame stream for the 3D view, and a clean path for external agents.

## 2. Technical requirements

- FastAPI, Pydantic, SQLAlchemy with SQLite, WebSockets.
- Panda3D scene objects must never be touched from a web request thread.
- The API must be testable without a GPU.

## 3. Implementation steps

1. `ProcessGateway` starts the simulation in its own process (`multiprocessing`, spawn) with
   three queues: commands in, messages out, frames out.
2. Inside that process, `SimulationEngine._update` runs as a Panda3D task every frame: drain
   the command queue, tick the controller, forward its messages, animate, capture a frame.
3. Each command carries a `request_id`. The gateway's pump thread matches the `reply` message
   to the waiting request, so an HTTP call returns the real result.
4. `EpisodeService.handle_output` persists `events`, `state` and `finished` messages and
   passes them to the `ConnectionManager`, which broadcasts over `/ws/episodes/{id}/`.
5. `GET /api/v1/simulation/stream/` serves the newest frames as an MJPEG stream.
6. `InlineGateway` runs the same controller in the calling thread, without rendering. The
   API tests use it.
7. `examples/agents/simforge_client.py` wraps the four calls an agent needs.

## 4. Relevant files

- `backend/app/services/gateway.py` - `ProcessGateway`, `InlineGateway`
- `backend/simulation/process.py`, `backend/simulation/engine.py` - the other side of the queues
- `backend/app/services/episodes.py`, `backend/app/websocket/manager.py`
- `backend/app/api/` - routes, error handling
- `examples/agents/` - client, baseline agent, template

## 5. Important code sections

```python
# web side: enqueue and wait
self._commands.put({**command, "request_id": request_id})
if not done.wait(REQUEST_TIMEOUT_SECONDS):
    raise SimulationUnavailableError("The simulation did not answer in time.")

# simulation side: executed inside the Panda3D task loop
def _update(self, task):
    self._process_commands()
    self.controller.tick(dt)
    self._forward_outputs()
    self.scene.animate(dt, self.controller.speed)
```

An external agent:

```python
client = SimforgeClient("http://127.0.0.1:8000")
episode_id = client.create_episode("basic-delivery", seed=7)
observation = client.start(episode_id)
while True:
    result = client.act(episode_id, choose_action(observation))
    observation = result["observation"]
    if result["done"]:
        break
```

## 6. Design decisions

- **A separate process, not a thread.** Panda3D wants its own main loop, and a renderer crash
  must not take the API down.
- **Events are forwarded before the reply.** By the time an HTTP call returns, its events are
  already stored, so a client can read them immediately.
- **One error shape.** Every failure is `{"error": {"code", "message", "details"}}`, with 404
  for unknown things, 409 for wrong state and 422 for invalid input.
- **A rejected action is a 200.** The request was valid; the outcome (`success: false`) is
  information for the agent.

## 7. Problems encountered

- The smoke test's first "frame" was 137 kB at JPEG quality 95. Setting `jpeg-quality 82`
  roughly halved the stream without a visible difference.
- An MJPEG generator that never checks for disconnects keeps the server from shutting down.
  The stream loop polls `request.is_disconnected()`.

## 8. Debugging approach

`GET /api/v1/health/` reports whether rendering is on, the active episode and the engine's
FPS. The simulation process logs with a `[simulation]` prefix in the same console.

## 9. Validation steps

```powershell
cd backend
python -m pytest tests/test_api.py
python run.py                      # then, in another terminal:
python ../examples/agents/baseline_agent.py --scenario obstacle-navigation
```

## 10. Expected result

The external agent completes the task through HTTP alone while the browser shows the robot
moving, and its run appears in Run History with agent type "External agent".
