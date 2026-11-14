# 01. Environment creation

## 1. Objective

Describe a warehouse task as data: the floor plan, the zones, the packages, the moving
obstacles and the limits. One scenario definition must be enough to build both the rule
world and the 3D scene, and the same definition and seed must always give the same world.

## 2. Technical requirements

- Python 3.12 or newer (developed on 3.14). No Panda3D import is needed for this layer.
- Frozen dataclasses, so a scenario cannot be changed by accident while an episode runs.
- A grid of cells addressed as `(x, y)`, with `y` growing to the north.

## 3. Implementation steps

1. Draw the floor plan as ASCII rows in `scenarios/warehouse.py`. The first row is the north
   wall. `#` is a shelf, `X` a pallet stack, `R` restricted floor and `.` open floor.
2. `parse_layout` turns the rows into cell sets (`shelves`, `static_obstacles`, `restricted`).
3. Declare zones with `rectangle(x0, y0, x1, y1)`: loading dock, collection bay, delivery zones.
4. Declare each package with a list of `candidate_cells`. The seed picks one of them.
5. Declare each forklift as a `PatrolSpec` with a start cell, an end cell and a period.
6. Register the scenario in `scenarios/__init__.py` so the API and the engine can find it.
7. `World(scenario, seed)` creates the mutable state: robot, packages and forklifts.

## 4. Relevant files

- `backend/simulation/scenarios/base.py` - `ScenarioDefinition`, `ZoneSpec`, `PackageSpec`, `PatrolSpec`, `parse_layout`
- `backend/simulation/scenarios/warehouse.py` - the three built-in scenarios
- `backend/simulation/world.py` - `World`, `Robot`, `Package`, `MovingObstacle`
- `backend/simulation/types.py` - `Orientation`, `Pose`, enums

## 5. Important code sections

```python
BASE_LAYOUT = (
    "................",
    ".##.##.##.##....",   # shelves in pairs, aisles at x = 0, 3, 6, 9, 12
    ...
    "...X....RR......",   # a pallet and the restricted area
)

class World:
    def __init__(self, scenario, seed):
        rng = random.Random(seed)            # the only source of randomness
        self.packages = self._spawn_packages(rng)
        self.obstacles = [self._spawn_obstacle(patrol, rng) for patrol in scenario.patrols]
```

## 6. Design decisions

- **ASCII floor plans.** A reviewer can see the map in the source file, and a new scenario is a
  few lines of text.
- **One seeded `random.Random` per world.** Nothing reads the global random state, so two
  worlds never influence each other and a reset is exactly reproducible.
- **Scenario and world are separate.** The definition is immutable; only `World` changes.
  Resetting an episode is just building a new `World`.
- **Zones are passable.** Only shelves, pallets, packages and forklifts block movement.
  Entering the restricted zone is allowed but counted as a safety violation.

## 7. Problems encountered

- The first checkpoint list placed a marker on a pallet cell, and one forklift route crossed a
  pallet. Both came from editing the map without rechecking coordinates.
- The top aisle of scenario 2 made the task trivial, because the robot could drive straight
  along the north wall. A pallet at `(6, 11)` now closes it.

## 8. Debugging approach

A test walks every scenario and asserts that the start cell, every zone cell and every patrol
route cell is free of static obstacles. That turned both mistakes above into failing tests
instead of visual surprises.

## 9. Validation steps

```powershell
cd backend
python -m pytest tests/test_world_and_actions.py -k "Creation or Determinism"
```

## 10. Expected result

Three registered scenarios. Building a world twice with the same seed gives identical
package and forklift positions; changing the seed changes them.
