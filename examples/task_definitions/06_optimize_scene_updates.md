# Task 06: Optimize scene update performance

## Task objective

Reduce the per-frame cost of the Panda3D scene so the engine keeps 30 FPS at 1600 x 900 on an
integrated GPU, by flattening static geometry and measuring the effect.

## Environment setup

- Scenario: `multi-step-delivery`, off-screen engine at 1600 x 900.
- Baseline measurement on the development laptop at 960 x 540: about 28 ms per frame
  including JPEG encoding. Measure 1600 x 900 before changing anything.

## Initial state

- Every shelf is its own node with about 13 child Geoms (posts, boards, cartons).
- The static group is rebuilt only when an episode is loaded or reset.

## Required actions

1. Write a benchmark script that loads the scenario, renders 300 frames and prints the mean
   and 95th-percentile frame time, with and without frame capture.
2. After `WarehouseScene.build` finishes the static world, call `flattenStrong()` on the
   static group so its Geoms are merged.
3. Keep collision nodes and labels out of the flattened group.
4. Re-run the benchmark and the scene tests.

## Expected final state

- The static group has far fewer Geom nodes (report the count before and after with
  `root.analyze()`).
- Rendering looks identical; thumbnails differ by no more than JPEG noise.
- Collision solids still report `shelf-x-y` names.

## Success criteria

- Mean frame time at 1600 x 900 improves by at least 15%, or the report explains with numbers
  why the bottleneck is elsewhere (for example the frame read-back).
- `tests/test_panda_scene.py` passes, including the collision cross-check.

## Failure conditions

- Flattening removes or renames the collision nodes.
- Dynamic entities (robot, packages, forklifts) are flattened and stop moving.
- A claimed speed-up without before and after measurements.

## Validation method

```powershell
cd backend
# benchmark_scene.py is created as part of this task
python ../scripts/benchmark_scene.py --width 1600 --height 900 --frames 300
python -m pytest tests/test_panda_scene.py
```

## Prompt for an AI coding agent

> Profile and optimise the Panda3D scene in `backend/simulation/scene.py`. First add a
> benchmark script that creates a `SimulationEngine` off-screen at a given resolution, loads
> `multi-step-delivery`, steps the task manager for N frames and reports mean and p95 frame
> time, separately with and without `capture_jpeg`. Record the numbers. Then restructure
> `WarehouseScene.build` so visual static geometry lives under one node that is flattened
> with `flattenStrong()` after building, while collision nodes stay under a separate
> unflattened node with their names intact. Print `analyze()` output before and after.
> Re-run the benchmark and the tests. Report all numbers honestly, including the case where
> the gain is small because reading the frame buffer back dominates.
