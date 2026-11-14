# Debugging common simulation failures

Each entry lists the symptom, the likely cause and how to confirm it.

## The server starts but the 3D view is empty or says "not available"

- **Cause:** the Panda3D process could not open an off-screen buffer, or the server runs with
  `SIMFORGE_SIMULATION=inline`.
- **Check:** `GET /api/v1/health/` shows `"rendering": false`. The server console shows lines
  prefixed `[simulation]`; a failed start logs "The Panda3D engine could not start".
- **Fix:** update the graphics driver, or run the native viewer to see Panda3D's own error:
  `python -m simulation.panda_viewer`.

## "The simulation did not answer in time" (HTTP 503)

- **Cause:** the simulation process stopped or is blocked.
- **Check:** look for a traceback above the message in the console.
- **Fix:** restart `python run.py`. Unfinished runs are marked as stopped and stay in the
  history.

## An action returns 409 `invalid_state`

- **Cause:** the episode is not started, is paused, or has finished.
- **Check:** the `message` says which. The toolbar badge in the live view shows the status.
- **Fix:** call `start` or `resume`, or create a new episode.

## An action returns 409 `episode_not_active`

- **Cause:** a newer episode was created. Only one episode is loaded in the simulation.
- **Fix:** create a new episode for the agent, and avoid launching another run from the
  browser while it works.

## The agent keeps collecting collisions

- **Cause:** it sends moves that are not in `available_actions`, or reuses an old observation.
- **Check:** filter the event feed by **Collisions**. Each event names the blocker and the cell.
  The evaluation report lists the collision locations and draws them on the route map.
- **Fix:** read a fresh observation after every action, and treat each forklift's
  `next_position` as blocked.

## `PICK_UP` fails although the robot is next to the package

- **Cause:** the robot must *face* the package: the package has to be in the cell directly in
  front. In the multi-step scenario the package may also not be the current target yet.
- **Check:** the error code is `no_object_in_range` or `object_unavailable`.

## The package was dropped but the task did not complete

- **Cause:** it was dropped outside its delivery zone. `DROP` succeeds on any free cell.
- **Check:** the event says "Dropped ... outside its delivery zone".
- **Fix:** before dropping, check that the cell in front is in `target.delivery_cells`.

## The A* agent stands still

- **Cause:** every route is blocked by a forklift for the moment, so it waits.
- **Check:** the event feed shows "No free route ... waiting for the way to clear".
- **Note:** forklifts yield to the robot, so the wait ends on its own.

## Two runs with the same seed differ

- **Cause:** the action sequences differ. The world is deterministic; an agent using its own
  unseeded randomness is not.
- **Check:** export both runs as JSON and compare the `trajectory` arrays.

## Tests fail with "Invalid statement (at line 1, column 1)" in pyproject.toml

- **Cause:** a byte-order mark at the start of the file, usually from a PowerShell redirect.
- **Fix:** save the file as UTF-8 without BOM.

## Useful tools

- **Pause + Step forward:** follow the agent one decision at a time.
- **Raw JSON observation:** the exact input the agent had at that step.
- **Collision shapes overlay:** shows the Panda3D collision solids.
- **Performance tab:** FPS, frame time, step duration, action latency, physical overlaps.
- **Export JSON:** the full run, for offline comparison.
