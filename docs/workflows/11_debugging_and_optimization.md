# 11. Debugging and optimization

## 1. Objective

Make problems in the simulation visible, measure where time goes, and keep the normal view
free of debug clutter.

## 2. Technical requirements

- Live numbers: render FPS, frame time, step duration, action latency, collision and
  invalid-action counters, simulation state.
- Optional overlays: grid, planned route, collision marks, labels, collision shapes.
- Recovery: reset the episode; survive a failing command.

## 3. Implementation steps

1. The engine sends a `perf` message once a second with `fps` and `frame_ms` from Panda3D's
   global clock, the renderer name, the resolution and `physical_contacts`.
2. The environment times each `step` with `time.perf_counter`; the controller times the full
   handling of an action. Both appear in the snapshot as `step_duration_ms` and
   `action_latency_ms`.
3. `set_view` toggles the overlay groups; `collision_shapes` shows the Panda3D solids.
4. `SimulationEngine._execute` wraps every command. A `CommandError` becomes an error reply;
   any other exception is logged with a traceback and the task loop keeps running.
5. `ProcessGateway.request` times out after eight seconds and reports
   `simulation_unavailable` (HTTP 503) instead of hanging the request.
6. The frame clock is limited to 30 FPS and frames are streamed at 15 FPS, so the simulation
   does not occupy a full CPU core.

## 4. Relevant files

- `backend/simulation/engine.py` - `_publish_perf`, `_execute`, `_set_view`
- `backend/simulation/scene.py` - overlays, `show_collision_shapes`, `physical_contacts`
- `frontend/src/components/live/PerformancePanel.tsx`, `Viewport.tsx`
- `docs/debugging/common_failures.md`

## 5. Important code sections

```python
try:
    data = handler(command) if handler else self.controller.handle(command)
    reply.update(ok=True, data=data)
except CommandError as error:
    reply.update(ok=False, error={"code": error.code, "message": error.message})
except Exception:                       # the loop must survive a faulty command
    logger.exception("Command failed: %s", command.get("type"))
```

## 6. Design decisions

- **Measure inside the simulation process.** Timings taken in the browser would mostly
  measure the network and the WebSocket.
- **Rebuild overlays only when their data changes.** The route line is rebuilt when the
  planned path changes, the incident marks when the count changes.
- **Limit the clock.** An unlimited loop rendered hundreds of frames a second that nobody saw.
- **Panda3D's PStats** was considered for profiling. It needs the separate `pstats` server
  and a connection from the engine; it is documented as a next step rather than wired in.

## 7. Problems encountered

- Measured on the development laptop (integrated Intel GPU, 960 x 540): about 28 ms to render
  and JPEG-encode a frame, well inside the 33 ms budget. A simulation step takes well under a
  millisecond, so rendering, not logic, is the cost.
- A page in the web interface grew to several screens of empty space. Screen-reader-only
  labels inside a scrolling list were positioned against the page; giving the list
  `position: relative` fixed it.

## 8. Debugging approach

1. Reproduce with the same scenario and seed. Runs are deterministic.
2. Pause, then use **Step forward** to advance one decision at a time.
3. Read the event feed filtered by Collisions or Errors.
4. Open the Raw JSON observation at the step where the behaviour goes wrong.
5. Turn on Collision shapes and the grid to compare the picture with the rules.

## 9. Validation steps

```powershell
cd backend
python -m pytest tests/test_panda_scene.py -k "Engine"
```

Then open the **Performance** tab in the live workspace during a run.

## 10. Expected result

About 30 FPS, sub-millisecond steps, zero physical overlaps, and a server that keeps
answering after a bad command.
