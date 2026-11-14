# 10. Evaluation engine

## 1. Objective

Turn the raw results of an episode into an objective, explainable 100-point report, and keep
task success as a separate yes/no result.

## 2. Technical requirements

- Scoring must be a pure function of the episode summary: same run, same score.
- Every point must be traceable to a rule and a measured number.
- No value in a report or chart may be hardcoded.

## 3. Implementation steps

1. When an episode ends, `WarehouseEnvironment.summary()` returns the measured facts:
   packages collected and delivered, collisions, restricted-area entries, invalid actions,
   total actions, steps, the baseline route length, the trajectory and incident locations.
2. The controller adds elapsed time and the agent mode and emits one `finished` message.
3. `evaluate_episode(summary)` computes six components and their explanations.
4. `EpisodeService._store_result` saves the report and copies the headline numbers to the
   episode row, so lists and charts need no extra work.
5. `GET /api/v1/evaluations/` returns every evaluated run plus aggregates: success rate,
   average score, average steps of successful runs, and the share of runs with an incident.

## 4. Relevant files

- `backend/app/evaluation/engine.py` - `SCORING_RULES`, `evaluate_episode`
- `backend/simulation/environment.py` - `summary`
- `backend/simulation/baseline.py` - the baseline route
- `frontend/src/pages/EvaluationReport.tsx`, `frontend/src/pages/Evaluations.tsx`

## 5. Important code sections

The scoring model:

| Criterion | Points | Formula |
|---|---:|---|
| Task completion | 50 | 50 if every package is delivered, else 0 |
| Correct pickup | 10 | 10 x collected / assigned |
| Correct delivery | 10 | 10 x delivered / assigned |
| Collision safety | 15 | max(0, 15 - 3 x (collisions + restricted entries)) |
| Path efficiency | 10 | 10 x min(1, baseline steps / steps used), completed runs only |
| Valid actions | 5 | 5 x valid actions / total actions |

```python
efficiency = min(1.0, _ratio(baseline, steps)) if completed and baseline else None
points = {
    "completion": COMPLETION_POINTS if completed else 0.0,
    "safety": max(0.0, SAFETY_POINTS - SAFETY_PENALTY_PER_INCIDENT * incidents),
    ...
}
```

## 6. Design decisions

- **Success is a Boolean, the score is a number.** A run that collects the package but hits
  the step limit can score 30 and is still a failure. The report states both.
- **Efficiency is relative to a baseline computed for this exact world**, so scores are
  comparable across seeds.
- **Efficiency is zero for incomplete runs.** A short run that gave up is not efficient.
- **Recommendations are rules over the metrics**, so each one can be traced to a number.

## 7. Problems encountered

- An episode that is stopped early has no failure reason from the simulation. The evaluator
  reports it as `aborted` instead of leaving the field empty.

## 8. Debugging approach

A test asserts that the total always equals the sum of the breakdown and that each component
stays between zero and its maximum, over clean, messy, failed and aborted summaries.

## 9. Validation steps

```powershell
cd backend
python -m pytest tests/test_evaluation.py
```

## 10. Expected result

The A* agent scores 100.0 on Basic Delivery. A manual run with one wall collision and two
failed interactions loses 3 safety points and part of the valid-action points, and the report
lists the collision cell.
