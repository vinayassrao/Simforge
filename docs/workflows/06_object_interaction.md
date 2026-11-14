# 06. Object interaction

## 1. Objective

Let the robot pick up a package and put it down again, with clear preconditions, visible
feedback in the 3D scene, and delivery detection.

## 2. Technical requirements

- Interaction range is exactly one cell: the cell in front of the robot.
- The robot carries at most one package.
- Each package has an id, a name, a category, a weight, a position and a state
  (`available`, `carried`, `delivered`).

## 3. Implementation steps

1. `_pickup_error` returns `None` or a `(code, message)` pair. It checks, in order: already
   carrying, nothing in front, already delivered, not the current target.
2. `_pick_up` sets the package position to `None`, its state to `carried`, and
   `robot.carrying` to its id.
3. `_drop_error` checks that the robot carries something and that the front cell is free.
4. `_drop` places the package in the front cell. If that cell belongs to the package's
   destination zone the state becomes `delivered`; otherwise it is `available` again.
5. In the scene, `sync` re-parents a carried package to the robot's `carry-slot` node, and
   `animate` raises the forks. A delivered or dropped package returns to the world.

## 4. Relevant files

- `backend/simulation/actions.py` - `_pick_up`, `_drop` and their precondition checks
- `backend/simulation/world.py` - `Package`, `package_at`, `carried_package`
- `backend/simulation/scene.py` - `_build_package`, the carry slot, the fork animation

## 5. Important code sections

```python
def _pickup_error(self, current_target_id):
    if world.robot.carrying is not None:
        return "already_carrying", "The robot is already carrying a package."
    package = world.package_at(world.robot.pose.front)
    if package is None:
        return "no_object_in_range", "There is no package directly in front of the robot."
    if package.id != current_target_id:
        return "object_unavailable", "... is not the current target and cannot be collected yet."
```

## 6. Design decisions

- **Packages block their cell.** The robot must stop next to a package and face it, which
  makes "in range" unambiguous and gives pathfinding a clear goal pose.
- **A drop outside the zone is allowed.** It is a mistake the evaluation can measure, not an
  error. The package can be collected again.
- **Order is enforced at pick-up time.** In the multi-step scenario the amber package is
  `object_unavailable` until the blue one is delivered.
- **Re-parenting instead of copying positions.** The carried package follows the robot's
  animation for free.

## 7. Problems encountered

- `DROP` is legal whenever the front cell is free, so a naive agent that drops as soon as
  `DROP` appears in `available_actions` loses the package in an aisle. The agent template
  shows the extra check: is the front cell one of the delivery cells?

## 8. Debugging approach

Every interaction writes an event with the error code in its data. Filtering the event feed
by **Errors** shows each failed pick-up and drop with its reason.

## 9. Validation steps

```powershell
cd backend
python -m pytest tests/test_world_and_actions.py -k "PickUp"
python -m pytest tests/test_panda_scene.py -k carried
```

## 10. Expected result

A valid pick-up lifts the package and raises the forks. Dropping it while facing a delivery
cell marks it delivered and, for the last package, completes the task.
