import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { EpisodeTable } from "@/components/EpisodeTable";
import { EventFeed } from "@/components/EventFeed";
import { ControlPad } from "@/components/live/AgentPanel";
import { TaskPanel } from "@/components/live/TaskPanel";
import { ScoreBreakdown, ScoreRing } from "@/components/ScoreBreakdown";
import { ResultBadge, StatusBadge } from "@/components/StatusBadge";
import { makeEpisode, makeEvent } from "@/test/fixtures";

describe("EventFeed", () => {
  const events = [
    makeEvent(1, { description: "Moved forward from [0, 0] to [1, 0]." }),
    makeEvent(2, { category: "collision", type: "COLLISION", description: "Collision: the robot hit a shelving unit." }),
    makeEvent(3, { category: "error", type: "PICKUP_FAILED", description: "Pick-up failed: nothing in range." }),
  ];

  it("shows every event with a count per filter", () => {
    render(<EventFeed events={events} />);

    expect(screen.getAllByRole("listitem")).toHaveLength(3);
    expect(screen.getByRole("tab", { name: /All events\s*3/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /Collisions\s*1/ })).toBeInTheDocument();
  });

  it("filters the list when a category is chosen", async () => {
    render(<EventFeed events={events} />);

    await userEvent.click(screen.getByRole("tab", { name: /Errors/ }));

    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByText("Pick-up failed: nothing in range.")).toBeInTheDocument();
    expect(screen.queryByText(/Collision: the robot hit/)).not.toBeInTheDocument();
  });

  it("explains an empty feed", () => {
    render(<EventFeed events={[]} />);

    expect(screen.getByText("Events appear here as soon as the simulation starts.")).toBeInTheDocument();
  });
});

describe("TaskPanel", () => {
  it("marks the current step and the finished ones", () => {
    render(
      <TaskPanel
        task={{
          name: "Basic Delivery",
          instructions: "Deliver the blue package.",
          progress: 50,
          current_objective: "Navigate to the green delivery zone",
          objectives_total: 1,
          objectives_completed: 0,
          checklist: [
            { id: "a", label: "Reach the blue package", done: true, current: false },
            { id: "b", label: "Collect the blue package", done: true, current: false },
            { id: "c", label: "Navigate to the green delivery zone", done: false, current: true },
            { id: "d", label: "Deliver the blue package", done: false, current: false },
          ],
        }}
      />,
    );

    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: "Task progress: 50%" })).toHaveAttribute("value", "50");
    const current = screen.getByText("Navigate to the green delivery zone").closest("li");
    expect(current).toHaveAttribute("aria-current", "step");
    expect(within(screen.getByText("Reach the blue package").closest("li")!).getByText("(done)")).toBeInTheDocument();
  });
});

describe("ControlPad", () => {
  it("sends the action for a button click and for its keyboard shortcut", async () => {
    const onAction = vi.fn();
    render(<ControlPad available={["MOVE_FORWARD", "TURN_LEFT"]} enabled onAction={onAction} />);

    await userEvent.click(screen.getByRole("button", { name: /Forward/ }));
    await userEvent.keyboard("{ArrowLeft}e");

    expect(onAction.mock.calls.map(([action]) => action)).toEqual(["MOVE_FORWARD", "TURN_LEFT", "PICK_UP"]);
  });

  it("labels every control with text and ignores keys while disabled", async () => {
    const onAction = vi.fn();
    render(<ControlPad available={[]} enabled={false} onAction={onAction} />);

    for (const label of ["Turn left", "Forward", "Turn right", "Pick up", "Backward", "Drop", "Wait one step"]) {
      expect(screen.getByRole("button", { name: new RegExp(label) })).toBeDisabled();
    }
    await userEvent.keyboard("w");
    expect(onAction).not.toHaveBeenCalled();
  });
});

describe("evaluation components", () => {
  it("renders each scoring line with its points and rule", () => {
    render(
      <ScoreBreakdown
        breakdown={[
          { key: "completion", label: "Task completion", points: 50, max_points: 50, rule: "All 50 points if delivered.", explanation: "Every package was delivered." },
          { key: "efficiency", label: "Path efficiency", points: 7.6, max_points: 10, rule: "Baseline / steps.", explanation: "Used 66 steps; the baseline route needs 50." },
        ]}
      />,
    );

    expect(screen.getByText("50.0 / 50")).toBeInTheDocument();
    expect(screen.getByText("7.6 / 10")).toBeInTheDocument();
    expect(screen.getByText("Used 66 steps; the baseline route needs 50.")).toBeInTheDocument();
    expect(screen.getByRole("progressbar", { name: /Path efficiency: 7.6 of 10 points/ })).toHaveAttribute("max", "10");
  });

  it("announces the score and keeps success separate from it", () => {
    render(
      <>
        <ScoreRing score={30} success={false} />
        <ResultBadge success={false} />
      </>,
    );

    expect(screen.getByRole("img", { name: "Score 30.0 out of 100" })).toBeInTheDocument();
    expect(screen.getByText("Task failed")).toBeInTheDocument();
  });

  it("uses plain-language status labels", () => {
    render(
      <>
        <StatusBadge status="created" />
        <StatusBadge status="aborted" />
        <ResultBadge success={null} />
      </>,
    );

    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Stopped")).toBeInTheDocument();
    expect(screen.getByText("Not evaluated")).toBeInTheDocument();
  });
});

describe("EpisodeTable", () => {
  it("links evaluated runs to their report and unfinished ones to the live view", () => {
    render(
      <MemoryRouter>
        <EpisodeTable
          caption="Runs"
          episodes={[makeEpisode({ id: "ep-done" }), makeEpisode({ id: "ep-live", status: "running", score: null, success: null })]}
        />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "ep-done" })).toHaveAttribute("href", "/evaluations/ep-done");
    expect(screen.getByRole("link", { name: "ep-live" })).toHaveAttribute("href", "/simulation/ep-live");
    expect(screen.getByRole("table", { name: "Runs" })).toBeInTheDocument();
  });

  it("reports which run is ticked for comparison", async () => {
    const onToggle = vi.fn();
    render(
      <MemoryRouter>
        <EpisodeTable caption="Runs" episodes={[makeEpisode({ id: "ep-a" })]} selectedIds={[]} onToggleSelect={onToggle} />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole("checkbox", { name: "Select run ep-a for comparison" }));

    expect(onToggle).toHaveBeenCalledWith("ep-a");
  });
});
