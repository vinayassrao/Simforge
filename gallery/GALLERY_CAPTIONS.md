# Gallery captions

All six images are 1600 x 900 PNG files captured from the running application by
`scripts/capture_gallery.py`. Images 01, 02, 04, 05 and 06 are browser screenshots taken with
Playwright. Image 03 is written by the Panda3D engine directly from its frame buffer. Every
number shown comes from runs that were actually executed; nothing is mocked or edited.

## 01_simforge_dashboard.png

**SIMFORGE overview dashboard.** The landing page of the platform: a three-step quick start,
four figures calculated from stored runs (scenarios, runs, successful tasks, average score),
and scenario cards whose previews are rendered by the Panda3D engine.

## 02_scenario_library.png

**Scenario library.** Three warehouse scenarios of increasing difficulty, with search, filters
and sorting. Each card shows the task type, the number of objectives and moving obstacles, the
estimated time and the agents that can run it.

## 03_live_panda3d_simulation.png

**The Panda3D warehouse, rendered by the engine.** A procedurally built 3D scene with shadowed
shelving, pallet stacks, colour-coded zones, three patrolling forklifts and the robot carrying
the blue package along its planned route (cyan). No external models or textures are used.

## 04_agent_execution.png

**An autonomous agent executing a task, live.** The built-in A* agent is part-way through the
two-package scenario. The browser shows frames streamed from Panda3D, the task checklist with
the current step highlighted, live counters and the episode timeline.

## 05_evaluation_report.png

**Evaluation report for a completed run.** A 97.6 / 100 score with its breakdown: full marks
for completion, pickup, delivery and safety, and 7.6 of 10 for path efficiency because the
agent needed 66 steps against a 50-step baseline while avoiding forklifts. Each line shows the
rule that produced it.

## 06_agent_studio_and_api.png

**Agent Studio.** The three agent types, the observation-decision-action loop, the action
interface with preconditions and failure behaviour, and the agent state machine. The same page
contains the instructions and example scripts for connecting an external Python agent.
