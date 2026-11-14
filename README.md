# SIMFORGE - AI Simulation & Training Lab

**Build worlds. Train agents. Evaluate intelligence.**

SIMFORGE is a local platform for testing AI agents in a real 3D simulation. A warehouse robot
lives in a Panda3D world; you give it a delivery task, choose who controls it, watch every
action live in the browser, and get an objective evaluation at the end.

It is an original portfolio project that shows Panda3D environment development, agent
integration, evaluation, backend and frontend engineering, testing and technical writing.

## What you can do with it

1. Pick one of three warehouse scenarios and read its task.
2. Choose the agent: the built-in A* agent, manual control, or your own Python program.
3. Watch the run in a live Panda3D view, with the task checklist and every event.
4. Pause, single-step, change speed, reset, and switch on debug overlays.
5. Read the evaluation report: success, a 100-point score with its breakdown, the route and
   the collision locations.
6. Compare runs, browse the history and export a run as JSON or CSV.

## Architecture

```text
Browser (React)  <-- REST, WebSocket, MJPEG -->  FastAPI backend  <-- queues -->  Panda3D process
                                                   |                                (rules + scene)
External agent   <-- REST ------------------------>+--> SQLite (runs, events, evaluations)
```

- **Panda3D is the simulation.** A dedicated process owns the episode state and the scene
  graph, renders off-screen and streams its frames to the browser. There is no second 3D
  engine in the browser.
- **Web requests never touch the scene.** They enqueue commands, which the Panda3D task loop
  executes; results come back on a second queue.
- **The rules are pure Python**, deterministic for a given scenario and seed, and testable
  without a GPU.

More detail: [docs/architecture/overview.md](docs/architecture/overview.md).

## Technology

| Area | Stack |
|---|---|
| Simulation | Python 3.12+ (developed on 3.14), Panda3D 1.10.16 |
| Backend | FastAPI, Pydantic 2, SQLAlchemy 2, SQLite, WebSockets, NumPy (installed; not needed by the current rules) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, React Router, Recharts, Lucide icons |
| Testing | pytest, Coverage.py, Vitest, Testing Library, Playwright |
| Tooling | Ruff |

The interface components (buttons, cards, badges, tabs) are written in the shadcn/ui style
with Tailwind classes; the shadcn generator itself is not used.

## Project structure

```text
simforge/
├── backend/
│   ├── run.py                  # start the server
│   ├── app/                    # FastAPI: api/, services/, evaluation/, models/, schemas/, websocket/
│   ├── simulation/             # rules, controller, Panda3D engine, scene, scenarios, native viewer
│   ├── agents/                 # agent interface and the built-in A* agent
│   └── tests/                  # unit, API, Panda3D and browser (e2e) tests
├── frontend/src/               # pages/, components/, layouts/, hooks/, services/, types/
├── examples/
│   ├── agents/                 # API client, baseline agent, custom agent template
│   └── task_definitions/       # six task specifications with prompts for AI coding agents
├── docs/                       # workflows/ (12 guides), architecture/, api/, debugging/
├── scripts/                    # capture_gallery.py, record_demo.py
├── gallery/                    # six screenshots and their captions
└── recordings/                 # demo video and narration script
```

## Getting started

Requirements: Python 3.12 or newer, Node.js 20 or newer, and a graphics driver with OpenGL.
The commands are for Windows PowerShell; on macOS or Linux use `source .venv/bin/activate`.

```powershell
# 1. Backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt

# 2. Frontend (build once; the backend serves the result)
cd frontend
npm install
npm run build
cd ..

# 3. Run
cd backend
python run.py
```

Open <http://127.0.0.1:8000>. The first start takes a few seconds while Panda3D renders the
scenario previews. Data is stored in `data/` and no account or API key is needed.

For frontend development with hot reload, keep `python run.py` running and start
`npm run dev` in `frontend/`, then open <http://localhost:5173>.

### Native Panda3D viewer

The same engine in a desktop window, without the web stack:

```powershell
cd backend
python -m simulation.panda_viewer --scenario obstacle-navigation --agent astar
```

Keys: arrows or WASD drive (with `--agent manual`), E pick up, Q drop, Space pause, N step,
R reset, 1-5 speed, G grid, P path, C collision shapes, L labels, V camera, Esc quit.

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `SIMFORGE_DB` | `data/simforge.sqlite3` | SQLite database file |
| `SIMFORGE_CACHE` | `data/cache` | Rendered scenario previews |
| `SIMFORGE_SIMULATION` | `process` | `inline` runs the rules without rendering (no GPU needed) |
| `SIMFORGE_RENDER_WIDTH` / `_HEIGHT` | `960` / `540` | Size of the streamed render |
| `SIMFORGE_LOG_LEVEL` | `INFO` | Log level |

## Scenarios

| Scenario | Difficulty | Task | Moving obstacles |
|---|---|---|---:|
| Basic Delivery | Beginner | Take the blue package to the green delivery zone | 0 |
| Obstacle Navigation | Intermediate | Deliver across the warehouse while forklifts patrol | 3 |
| Multi-Step Delivery | Advanced | Deliver two packages, in order, to two zones | 1 |

Each scenario has a default seed. The seed decides where packages start and where the
forklifts begin; the same scenario and seed always give the same run.

## Agents and actions

Seven actions: `MOVE_FORWARD`, `MOVE_BACKWARD`, `TURN_LEFT`, `TURN_RIGHT`, `PICK_UP`, `DROP`,
`WAIT`. Each has preconditions; a failed action returns the reason and still uses one step.

- **Manual control** - on-screen control pad or keyboard.
- **Built-in A\* agent** - plans over position and heading, re-plans around forklifts, and
  acts only through the normal action rules.
- **External Python agent** - any program using the REST API.

### Connect an external agent

With the server running:

```powershell
python examples\agents\baseline_agent.py --scenario obstacle-navigation --seed 7
python examples\agents\custom_agent_template.py --scenario basic-delivery
```

The loop is four calls (see [docs/api/reference.md](docs/api/reference.md)):

```python
from simforge_client import SimforgeClient

client = SimforgeClient("http://127.0.0.1:8000")
episode_id = client.create_episode("basic-delivery", seed=7)
observation = client.start(episode_id)
done = False
while not done:
    result = client.act(episode_id, choose_action(observation))
    observation, done = result["observation"], result["done"]
print(client.evaluation(episode_id)["score"])
```

Watch the robot on the Live Simulation page while the script runs.

## Evaluation

| Criterion | Points | Formula |
|---|---:|---|
| Task completion | 50 | 50 if every package is delivered, else 0 |
| Correct pickup | 10 | 10 x collected / assigned |
| Correct delivery | 10 | 10 x delivered / assigned |
| Collision safety | 15 | max(0, 15 - 3 x (collisions + restricted-area entries)) |
| Path efficiency | 10 | 10 x min(1, baseline steps / steps used); completed runs only |
| Valid actions | 5 | 5 x valid actions / total actions |

Task success is a separate yes/no result: a run can earn partial points and still fail.
The baseline is the route an informed planner needs on the starting map without forklifts.

## API

Interactive documentation: <http://127.0.0.1:8000/api/docs>. Main routes under `/api/v1`:

| Route | Purpose |
|---|---|
| `GET /scenarios/`, `GET /scenarios/{id}/` | Scenarios and their layout |
| `POST /episodes/`, `GET /episodes/`, `GET /episodes/{id}/` | Create and query runs |
| `POST /episodes/{id}/start\|pause\|resume\|reset\|step/` | Control a run |
| `GET /episodes/{id}/observation/`, `POST /episodes/{id}/actions/` | The agent loop |
| `GET /episodes/{id}/events/`, `GET /episodes/{id}/evaluation/` | Results |
| `GET /evaluations/`, `GET /episodes/{id}/export/` | Aggregates and export |
| `WS /ws/episodes/{id}/` | Live state, events and the final evaluation |

## Testing

```powershell
cd backend
python -m pytest -m "not e2e"                    # rules, agent, evaluation, API, Panda3D
python -m pytest -m e2e                          # browser tests against the real server
python -m coverage run -m pytest -m "not e2e"
python -m coverage report                        # or: python -m coverage html
cd ..\frontend
npm test
```

Results on the development machine:

| Suite | Tests | Result |
|---|---:|---|
| Backend: rules, agent, controller, evaluation, API, Panda3D scene and engine | 139 | all pass |
| End-to-end: Chromium against the real server and Panda3D process | 9 | all pass |
| Frontend unit and component tests (Vitest) | 28 | all pass |

Backend coverage is **92%** (statements and branches) from the 139 non-browser tests. The
code that talks to the separate Panda3D process (`app/services/gateway.py` `ProcessGateway`,
`simulation/process.py`) is exercised by the end-to-end tests, which run it in another
process and are therefore not counted in that figure. The Panda3D engine tests skip
themselves on a machine without a graphics pipe; the browser tests need the built frontend
and `python -m playwright install chromium`.

## Documentation

- [docs/workflows/](docs/workflows/) - twelve step-by-step guides (environment, scene, agent,
  pathfinding, collisions, interaction, task execution, observations, API integration,
  evaluation, debugging, testing). Each lists objective, steps, files, design decisions,
  problems met, debugging approach and validation.
- [docs/architecture/overview.md](docs/architecture/overview.md)
- [docs/api/reference.md](docs/api/reference.md)
- [docs/debugging/common_failures.md](docs/debugging/common_failures.md)
- [examples/task_definitions/](examples/task_definitions/) - six task specifications, each
  with a prompt for an AI coding agent.

The same documents are readable inside the application under **Workflows & Tutorials**.

## Portfolio evidence

- `gallery/` - six 1600 x 900 screenshots with captions in
  [gallery/GALLERY_CAPTIONS.md](gallery/GALLERY_CAPTIONS.md). Regenerate with
  `python scripts/capture_gallery.py` while the server runs.
- `recordings/simforge_demo.mp4` - a 3 minute 17 second walkthrough recorded from the running
  application, without audio. The narration is in
  [recordings/narration_script.md](recordings/narration_script.md). Regenerate with
  `python scripts/record_demo.py`.

## Known limitations

- **One live episode at a time.** A single Panda3D scene is authoritative. Starting a new run
  stops an unfinished one (it stays in the history as "Stopped").
- **Discrete grid world.** Movement is cell by cell with four headings. There is no continuous
  physics; Panda3D's collision system is used as a cross-check and for debug views.
- **Full observability.** The agent sees the whole warehouse.
- **No machine-learning model is trained.** This is an environment for integrating, testing
  and evaluating agents. The built-in agent is classical A* search.
- **Local use only.** No authentication; the server binds to 127.0.0.1.
- **The browser view is an MJPEG stream** at 960 x 540 and 15 frames per second. It is not
  interactive 3D: the camera is changed with the buttons, not by dragging.
- **Replay is 2D.** Finished runs replay as a top-down route map, not as a 3D playback.
- **The demo video has no audio**, and its caption bar is added by the recording script.
- **Rendering needs a working OpenGL driver.** Without one, use `SIMFORGE_SIMULATION=inline`.

## Possible next steps

Parallel episodes with one engine process each, 3D replay from the stored action list,
partial observability, time-aware pathfinding (task 04), a weight-limited lift (task 02), and
profiling with Panda3D's PStats.
