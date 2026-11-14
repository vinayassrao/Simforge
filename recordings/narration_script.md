# Narration script for simforge_demo.mp4

The recording is 3 minutes 17 seconds, 1600 x 900, without audio. It was captured from the
running application by `scripts/record_demo.py`; the caption bar at the bottom is added by that
script. Read this narration alongside the video, or record it as a voice-over. Times are
approximate.

## 0:00 Introduction

"This is SIMFORGE, an AI simulation and training lab I built with Panda3D, FastAPI and React.
It lets you put an agent into a 3D warehouse, give it a delivery task, watch every action it
takes, and get an objective score at the end. Everything you will see is the real application
running locally."

"The dashboard is calculated from stored runs: how many scenarios exist, how many runs have
been executed, how many succeeded, and the average evaluation score."

## 0:12 The simulation objective

"The scenario library has three warehouse tasks. The preview images are rendered by the
Panda3D engine itself when the server starts."

"I'll open Obstacle Navigation. The task is stated in plain English: collect the assigned
package and deliver it while avoiding moving warehouse obstacles. The page also explains when
the run ends and how success is measured: a 100-point score with fifty points for completing
the task, twenty for correct pickup and delivery, fifteen for collision safety, ten for path
efficiency and five for valid actions."

## 0:36 Choosing the agent

"There are three ways to control the robot: the built-in A-star agent, manual control, or an
external Python program. I'll use the A-star agent. The seed makes the run reproducible: the
same scenario and seed always produce the same world."

## 0:45 How the environment is structured

"This is the live workspace. The image is streamed from an off-screen Panda3D buffer, so what
you see is the engine's own render. The warehouse is a sixteen by twelve grid. Orange racks
and pallet stacks are static obstacles. The blue area is the collection bay, the orange area
is the delivery zone, and the red striped area is restricted: entering it costs safety points.
The three yellow forklifts patrol fixed routes."

"On the right is the objective with a four-step checklist, and below it the agent panel with
its state, position and the actions that would succeed right now."

## 0:57 Starting the simulation

"I press Start. The agent reads its observation, plans a route with A-star search, and issues
one action per step: move forward, turn, pick up, drop or wait. The cyan line is its current
plan. It is not teleporting: every move goes through the same rules as manual control."

## 1:15 An important agent decision

"I'll pause and step forward one decision at a time. The planner searches over position and
heading together, so a turn costs a step just like a move. For each forklift it treats both
the current cell and the next cell as blocked. When a forklift enters the planned route, the
agent logs 'obstacle detected' and 'route recalculated' and takes a detour. That is why this
run needs more steps than the baseline route."

"These overlays are for debugging: the navigation grid, and the Panda3D collision solids
around the robot, the racks and the forklifts."

## 1:35 Collection and delivery

"Resuming at double speed. The robot stops next to the package, faces it and picks it up: the
forks rise and the package rides on them. Pick-up has preconditions. It fails if nothing is in
front, if the robot is already carrying something, or if the package is not the current
target. Then it crosses the warehouse and drops the package while facing a cell inside the
delivery zone. The task is complete."

## 2:00 The event feed and the observation

"Live activity lists every event with its step and timestamp. I can filter by agent actions,
collisions, errors or task milestones."

"The observation tab shows what the agent currently sees: first as readable cards, then as raw
JSON. This is exactly what an external agent receives from the API."

"The performance tab shows the engine's frame rate, the duration of a simulation step, the
action latency and the collision and invalid-action counters."

## 2:25 The evaluation report

"Here is the evaluation report. Success is a yes-or-no result, and it is kept separate from
the score. This run scored 97.6. It earned full points for completion, pickup, delivery,
safety and valid actions. Path efficiency is 7.6 out of 10: the agent used 66 steps, and the
baseline route for this exact world is 50, so the ratio is 76 percent."

"The route replay is drawn from the stored trajectory. Below it are the recommendations and
the complete event log. The run can be exported as JSON or CSV."

## 2:50 Comparing runs

"The evaluations page aggregates every stored run: success rate, average score, steps and
collisions per episode, and performance over time. Runs can be ticked and compared side by
side."

## 2:57 Connecting an external Python agent

"Agent Studio explains the loop every agent follows: observation, decision, action,
environment update, new observation. It documents the seven actions with their preconditions
and the agent's state machine."

"An external agent needs four HTTP calls: create an episode, start it, read the observation,
and post an action. No API key is required. The project includes a baseline client and a
template to start from."

## 3:08 Documentation

"The API page is generated from the server's OpenAPI schema, and the workflows section has
twelve guides that explain how each part was implemented, debugged and validated. Thank you
for watching."
