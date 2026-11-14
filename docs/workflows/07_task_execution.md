# 07. Task execution

## 1. Objective

Run one episode from start to completion or failure: apply actions, track milestones, move
the forklifts, enforce limits, and publish every change.

## 2. Technical requirements

- A task has an id, a name, instructions, a start pose, target packages, destinations, a step
  limit, an optional time limit, completion conditions and failure conditions.
- Progress must be observable as a percentage and as a checklist.
- Pause, resume, single step, reset and five playback speeds.

## 3. Implementation steps

1. `WarehouseEnvironment.step(action)` runs one step in a fixed order: settle transient
   states, increment the step counter, execute the action, update metrics and events, update
   the task, record the trajectory point, advance the forklifts, check end conditions.
2. `TaskManager` keeps one `Objective` per package with four milestones: reach the package,
   collect it, reach the destination, deliver it. Progress is milestones reached out of the
   total.
3. End conditions: all objectives complete gives `COMPLETED`; reaching `max_collisions`
   safety incidents or `max_steps` gives `FAILED` with a reason.
4. `SimulationController` wraps the environment with commands: `load`, `start`, `pause`,
   `resume`, `reset`, `step`, `action`, `set_speed`.
5. `controller.tick(dt)` runs on every Panda3D frame. It enforces the time limit and, in A*
   mode, converts elapsed time into agent decisions: three per second at 1x.
6. After each change the controller queues `events`, `state` and, once, `finished` messages.

## 4. Relevant files

- `backend/simulation/environment.py` - the step loop, metrics, summary
- `backend/simulation/task_manager.py` - objectives, milestones, checklist
- `backend/simulation/controller.py` - commands, clock, outputs
- `backend/app/services/episodes.py` - persistence of what the controller publishes

## 5. Important code sections

```python
def step(self, action):
    self._transition_logged(self.tasks.begin_step)
    self.world.step_count += 1
    outcome = self.executor.execute(action, target.id if target else None)
    self._account(outcome)
    self._transition_logged(lambda: self._apply_to_task(outcome))
    self.trajectory.append(self._trajectory_point())
    self.world.advance_obstacles()
    self._check_end_conditions()
```

## 6. Design decisions

- **The robot acts first, then the forklifts move.** The order is fixed, so a run is
  reproducible from its seed and its action list.
- **Steps, not seconds, drive the simulation.** Wall-clock time only decides how fast the
  built-in agent acts and whether an optional time limit has passed.
- **Reset rebuilds the world from the seed.** There is no "undo" logic to get wrong.
- **One live episode at a time.** A single Panda3D scene is authoritative. Starting a new
  episode marks an unfinished one as aborted and keeps its history.

## 7. Problems encountered

- An engine test stepped the agent twelve times and found twenty steps: the real-time tick
  was also running. The test now pauses the episode first, which is also how a user single
  steps.

## 8. Debugging approach

The controller takes an injectable clock. Tests advance a fake clock to check elapsed time
across pause and resume, and to trigger the time limit without waiting.

## 9. Validation steps

```powershell
cd backend
python -m pytest tests/test_controller.py tests/test_world_and_actions.py -k "Lifecycle or Progress or Clock"
```

## 10. Expected result

The checklist advances 25% per milestone for one package. An episode ends as `completed`, or
as `failed` with `step_limit_exceeded`, `collision_limit_exceeded` or `time_limit_exceeded`.
