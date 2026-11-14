# Architecture overview

SIMFORGE has three parts that talk through narrow interfaces: a Panda3D simulation process,
a FastAPI backend, and a React frontend.

```text
 Browser (React + TypeScript)                      External Python agent
   |  REST  /api/v1/...                               |  REST  /api/v1/...
   |  WebSocket  /ws/episodes/{id}/                   |
   |  MJPEG  /api/v1/simulation/stream/               |
   v                                                  v
+---------------------------------------------------------------------+
| FastAPI backend (app/)                                              |
|   api/        routes, validation, uniform errors                    |
|   services/   EpisodeService, gateway to the simulation             |
|   evaluation/ scoring engine (pure function)                        |
|   models/     SQLAlchemy tables -> SQLite                           |
|   websocket/  ConnectionManager                                     |
+------------------------------+--------------------------------------+
        commands queue |  ^ messages queue      ^ frames queue (JPEG)
                       v  |                     |
+---------------------------------------------------------------------+
| Simulation process (simulation/)            one Panda3D task loop   |
|   engine.py      ShowBase, command handling, frame capture          |
|   controller.py  episode lifecycle, built-in agent, outputs         |
|   environment.py step loop, metrics, observation                    |
|   world.py, actions.py, collision.py, task_manager.py   the rules   |
|   scene.py, geometry.py                    the Panda3D scene graph  |
+---------------------------------------------------------------------+
```

## Who owns what

| Concern | Owner | Notes |
|---|---|---|
| Authoritative episode state | `SimulationController` inside the Panda3D process | One live episode at a time |
| 3D scene graph and rendering | `WarehouseScene`, `SimulationEngine` | Only touched from the Panda3D task loop |
| Rules (movement, pick-up, collisions, task) | `simulation/` rule modules | Pure Python, no Panda3D import |
| Scoring | `app/evaluation/engine.py` | Pure function of the episode summary |
| History | SQLite through SQLAlchemy | Episodes, events, evaluations |
| Presentation | React frontend | Shows frames and state; decides nothing |

## Is the browser view really Panda3D?

Yes. The simulation process renders the scene into an off-screen Panda3D buffer. The engine
reads each frame back, encodes it as JPEG and puts it on a queue; the backend serves the
newest frames as an MJPEG stream; the browser shows them in an `<img>` element. There is no
second 3D engine in the browser. Two things in the interface are 2D summaries drawn from
stored data and are labelled as such: the route replay map and the charts.

The same engine also runs in a normal desktop window:
`python -m simulation.panda_viewer --scenario obstacle-navigation --agent astar`.

## The command path

1. An HTTP request reaches a route, for example `POST /episodes/{id}/actions/`.
2. `EpisodeService.command` calls `gateway.request({"type": "action", ...})`.
3. `ProcessGateway` adds a `request_id`, puts the command on the queue and waits.
4. In the simulation process, the `simforge-update` task drains the queue on the next frame
   and calls `SimulationController.handle`.
5. The controller applies the action through `WarehouseEnvironment.step` and queues `events`
   and `state` messages. The engine forwards them, then sends the `reply`.
6. The gateway's pump thread stores events and state through `EpisodeService.handle_output`,
   broadcasts them over the WebSocket, and finally releases the waiting request.

Web threads never hold a reference to a scene node or to the world. They can only enqueue.

## Running without a GPU

`SIMFORGE_SIMULATION=inline` (and the test suite) uses `InlineGateway`: the same controller
and rules run inside the web process with no rendering. The API behaves identically; the
frame endpoints answer 503 and the interface says the 3D view is unavailable.

## Data model

- `episodes`: id, scenario, agent mode, seed, status, timestamps, live counters, score,
  success, failure reason, trajectory, incident locations.
- `events`: one row per simulation event with sequence number, step, type, category,
  description, entity id, structured data and timestamp.
- `evaluations`: one JSON report per finished episode.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `SIMFORGE_DB` | `data/simforge.sqlite3` | SQLite file |
| `SIMFORGE_CACHE` | `data/cache` | Rendered scenario thumbnails |
| `SIMFORGE_SIMULATION` | `process` | `process` (Panda3D) or `inline` (no rendering) |
| `SIMFORGE_RENDER_WIDTH`, `SIMFORGE_RENDER_HEIGHT` | 960, 540 | Off-screen buffer size |
| `SIMFORGE_LOG_LEVEL` | `INFO` | Log level of both processes |
