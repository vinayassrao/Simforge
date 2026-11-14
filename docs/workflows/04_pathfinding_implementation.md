# 04. Pathfinding implementation

## 1. Objective

Plan the shortest sequence of actions from the robot's pose to a goal, around static and
moving obstacles, and re-plan when the world changes.

## 2. Technical requirements

- A* search with an admissible heuristic.
- The cost must be counted in actions, because turning takes a step just like moving.
- The planner must work from observation data only.

## 3. Implementation steps

1. Search over **poses** `(cell, orientation)`, not cells. Each pose has four successors:
   forward, backward, turn left, turn right, all with cost 1.
2. The heuristic is the smallest Manhattan distance from the current cell to any goal cell.
   It ignores turns, so it never overestimates.
3. `facing_poses(targets, passable)` builds the goal set: every pose that stands next to a
   target cell and faces it. Picking up and dropping both act on the cell in front.
4. `AStarAgent.decide` rebuilds the blocked set every step: static cells, the restricted
   area, packages on the floor, and for each forklift both its current and its next cell.
5. If the new plan differs because a forklift cell lies on the old route, the agent emits
   `OBSTACLE_DETECTED` and `PATH_RECALCULATED` notes. If no route exists, it waits.
6. `baseline_route_length` runs the same planner on the starting map without forklifts. The
   evaluation uses that number for path efficiency.

## 4. Relevant files

- `backend/simulation/pathfinding.py` - `plan_actions`, `facing_poses`, `path_cells`
- `backend/agents/astar_agent.py` - the agent and its explanations
- `backend/simulation/baseline.py` - the baseline route

## 5. Important code sections

```python
for action in MOVE_ACTIONS:
    successor = apply_move(pose, action)
    if successor.cell != pose.cell and not passable(successor.cell):
        continue                                    # turning in place is always possible
    new_cost = cost + 1
    if new_cost < best_cost.get(successor, new_cost + 1):
        heapq.heappush(frontier, (new_cost + heuristic(successor.cell), next(tie), new_cost, successor))
```

## 6. Design decisions

- **Pose space.** A cell-only search would count a route with many turns as equal to a
  straight one. In pose space the plan length is exactly the number of steps.
- **Reversing is an action.** Backing out of a dead end is often shorter than two turns.
- **Re-plan every step.** The grid has 192 cells and 768 poses, so a full search takes well
  under a millisecond. That is simpler and safer than repairing an old plan.
- **Treat a forklift's next cell as blocked.** It keeps the robot out of the cell the forklift
  is about to enter.

## 7. Problems encountered

- A* tie-breaking sometimes returned a different route of equal length on the next step, and
  the agent reported a "recalculation" each time. The agent now reports one only when the
  plan length changes or a forklift cell lies on the old route.
- A test expected 14 actions around a wall. The planner found 13 by ending in a different
  orientation, and it was right.

## 8. Debugging approach

`path_cells` converts a plan back into the cells it visits. The engine draws those cells as a
line in the 3D view, so a wrong plan is visible immediately.

## 9. Validation steps

```powershell
cd backend
python -m pytest tests/test_pathfinding_and_agent.py -k "Pathfinding or AStar"
```

## 10. Expected result

On the Basic Delivery scenario the agent matches the baseline route exactly. With forklifts
it takes more steps, logs its re-plans, and still finishes without a collision on every
tested seed.
