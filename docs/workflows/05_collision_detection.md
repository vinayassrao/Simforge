# 05. Collision detection

## 1. Objective

Decide, deterministically, whether the robot may enter a cell, record every collision with
its location, and confirm with Panda3D's own collision system that the rendered scene agrees.

## 2. Technical requirements

- One function answers "what blocks this cell?" for every caller.
- Collisions must be reproducible, so they cannot depend on frame timing.
- The Panda3D collision solids must be viewable for debugging.

## 3. Implementation steps

1. `find_blocker(world, cell)` checks, in order: outside the grid (wall), shelf, pallet,
   package on the floor, forklift. It returns a `Blocker` or `None`.
2. `_move` asks for the blocker of the target cell. If there is one, the robot stays, the
   outcome carries the blocker, and the environment increments `collisions` and stores the
   cell in `incident_locations`.
3. Entering a restricted cell succeeds but is logged as `RESTRICTED_AREA_ENTERED` and counted
   as a safety incident.
4. Forklifts never cause a collision themselves: `advance_obstacles` skips a move when the
   robot, a package or another forklift is in the next cell.
5. In the scene, shelves, pallets and forklifts get a `CollisionBox`, and the robot a
   `CollisionSphere`. `physical_contacts()` runs a `CollisionTraverser` and returns the names
   of any solids the robot overlaps.
6. The engine publishes that list once a second as `physical_contacts`. It should be empty.

## 4. Relevant files

- `backend/simulation/collision.py` - `find_blocker`, `Blocker`, `BlockerKind`
- `backend/simulation/actions.py` - `_move`
- `backend/simulation/world.py` - `advance_obstacles`
- `backend/simulation/scene.py` - collision solids and `physical_contacts`

## 5. Important code sections

```python
def find_blocker(world, cell):
    if not world.in_bounds(cell):
        return Blocker(BlockerKind.WALL, "warehouse-wall", "the warehouse wall")
    if cell in world.scenario.shelves:
        return Blocker(BlockerKind.SHELF, f"shelf-{cell[0]}-{cell[1]}", "a shelving unit")
    ...

def physical_contacts(self):
    self._traverser.traverse(self.root)
    return sorted({entry.getIntoNode().getName() for entry in self._contacts.getEntries()})
```

## 6. Design decisions

- **Grid rules are authoritative; Panda3D collision is a cross-check.** Scoring must not
  depend on interpolation or frame rate. The traverser answers a different question: does
  the picture match the rules?
- **The robot stays put after a collision.** The state remains valid and the agent can react.
- **A safety limit ends the episode.** After `max_collisions` incidents the task fails, so a
  broken agent cannot grind against a wall for the whole step budget.

## 7. Problems encountered

- The robot's collision node and its model node were both named `robot`. A lookup by name
  returned the wrong node and a scene test failed. The solid is now `robot-collider`.

## 8. Debugging approach

Turn on **Collision shapes** in the live view (or press `C` in the native viewer) to draw
every solid. The scene test forces the robot model into a shelf cell and asserts that the
traverser reports exactly that shelf.

## 9. Validation steps

```powershell
cd backend
python -m pytest tests/test_world_and_actions.py -k "collision or forklift or restricted"
python -m pytest tests/test_panda_scene.py -k collision
```

## 10. Expected result

Driving into a wall, shelf, pallet, package or forklift leaves the robot in place and adds
one collision with its cell. During normal runs `physical_contacts` stays empty.
