import { describe, expect, it } from "vitest";

import { filterEvents } from "@/components/EventFeed";
import { feedReducer, mergeEvents, type EpisodeFeed } from "@/hooks/useEpisodeSocket";
import { groupEndpoints } from "@/pages/ApiDocs";
import { chartRows } from "@/pages/Evaluations";
import { filterHistory } from "@/pages/RunHistory";
import { filterScenarios } from "@/pages/ScenarioLibrary";
import { groupDocuments } from "@/pages/Workflows";
import { formatCell, formatDuration, formatPercent, formatScore, humanize } from "@/services/format";
import { makeEpisode, makeEvaluated, makeEvent, makeScenario, makeState } from "@/test/fixtures";

const EMPTY_FEED: EpisodeFeed = {
  connection: "open",
  episode: null,
  state: null,
  status: null,
  events: [],
  evaluation: null,
  performance: {},
};

describe("formatting", () => {
  it("turns enum names into readable labels", () => {
    expect(humanize("NAVIGATING_TO_OBJECT")).toBe("Navigating to object");
    expect(humanize("EAST")).toBe("East");
  });

  it("shows a dash for values that do not exist yet", () => {
    expect(formatScore(null)).toBe("-");
    expect(formatPercent(null)).toBe("-");
    expect(formatDuration(undefined)).toBe("-");
    expect(formatCell(null)).toBe("-");
  });

  it("formats scores, ratios, durations and cells", () => {
    expect(formatScore(97.55)).toBe("97.5");
    expect(formatPercent(0.756)).toBe("76%");
    expect(formatPercent(0.5, 1)).toBe("50.0%");
    expect(formatDuration(8.14)).toBe("8.1s");
    expect(formatDuration(125)).toBe("2m 5s");
    expect(formatCell([3, 9])).toBe("(3, 9)");
  });
});

describe("live event merging", () => {
  it("appends only events that are newer than the last one", () => {
    const merged = mergeEvents([makeEvent(1), makeEvent(2)], [makeEvent(2), makeEvent(3)]);

    expect(merged.map((event) => event.seq)).toEqual([1, 2, 3]);
  });

  it("starts over when the sequence restarts after a reset", () => {
    const merged = mergeEvents([makeEvent(1), makeEvent(2), makeEvent(3)], [makeEvent(1), makeEvent(2)]);

    expect(merged.map((event) => event.seq)).toEqual([1, 2]);
  });

  it("keeps the list bounded", () => {
    const many = Array.from({ length: 700 }, (_, index) => makeEvent(index + 1));

    const merged = mergeEvents([], many);

    expect(merged).toHaveLength(600);
    expect(merged[merged.length - 1].seq).toBe(700);
  });

  it("puts stored history before events that already arrived live", () => {
    const live = { ...EMPTY_FEED, events: [makeEvent(4), makeEvent(5)] };

    const next = feedReducer(live, { kind: "history", events: [makeEvent(1), makeEvent(2), makeEvent(3), makeEvent(4)] });

    expect(next.events.map((event) => event.seq)).toEqual([1, 2, 3, 4, 5]);
  });
});

describe("live feed reducer", () => {
  it("follows the status from state messages", () => {
    const next = feedReducer(EMPTY_FEED, { kind: "message", message: { type: "state", state: makeState(3, "paused") } });

    expect(next.status).toBe("paused");
    expect(next.state?.metrics.steps).toBe(3);
  });

  it("drops the old evaluation when the episode is reset", () => {
    const finished: EpisodeFeed = {
      ...EMPTY_FEED,
      state: makeState(34, "completed"),
      evaluation: { score: 100 } as EpisodeFeed["evaluation"],
    };

    const next = feedReducer(finished, { kind: "message", message: { type: "state", state: makeState(0, "created") } });

    expect(next.evaluation).toBeNull();
    expect(next.status).toBe("created");
  });

  it("stores the evaluation and performance messages", () => {
    const evaluation = { score: 88.5, success: true } as EpisodeFeed["evaluation"];
    let feed = feedReducer(EMPTY_FEED, { kind: "message", message: { type: "finished", evaluation: evaluation! } });
    feed = feedReducer(feed, { kind: "message", message: { type: "perf", perf: { fps: 29.7 } } });

    expect(feed.evaluation?.score).toBe(88.5);
    expect(feed.performance.fps).toBe(29.7);
  });
});

describe("filters", () => {
  const events = [
    makeEvent(1),
    makeEvent(2, { category: "collision", type: "COLLISION" }),
    makeEvent(3, { category: "error", type: "PICKUP_FAILED" }),
    makeEvent(4, { category: "milestone", type: "PICKUP_SUCCESS" }),
  ];

  it("filters events by category", () => {
    expect(filterEvents(events, "all")).toHaveLength(4);
    expect(filterEvents(events, "collision").map((event) => event.seq)).toEqual([2]);
    expect(filterEvents(events, "milestone").map((event) => event.type)).toEqual(["PICKUP_SUCCESS"]);
  });

  const scenarios = [
    makeScenario(),
    makeScenario({ id: "obstacle-navigation", name: "Obstacle Navigation", summary: "Forklifts patrol the aisles.", difficulty: "Intermediate", task_type: "Dynamic navigation", estimated_minutes: 2 }),
    makeScenario({ id: "multi-step-delivery", name: "Multi-Step Delivery", difficulty: "Advanced", task_type: "Sequenced delivery", estimated_minutes: 3 }),
  ];

  it("searches and filters scenarios", () => {
    expect(filterScenarios(scenarios, "forklift", "", "", "name").map((item) => item.id)).toEqual(["obstacle-navigation"]);
    expect(filterScenarios(scenarios, "", "Advanced", "", "name").map((item) => item.id)).toEqual(["multi-step-delivery"]);
    expect(filterScenarios(scenarios, "", "", "Single delivery", "name")).toHaveLength(1);
    expect(filterScenarios(scenarios, "nothing matches", "", "", "name")).toEqual([]);
  });

  it("sorts scenarios by difficulty, name and duration", () => {
    const shuffled = [scenarios[2], scenarios[0], scenarios[1]];

    expect(filterScenarios(shuffled, "", "", "", "difficulty").map((item) => item.difficulty)).toEqual(["Beginner", "Intermediate", "Advanced"]);
    expect(filterScenarios(shuffled, "", "", "", "name")[0].name).toBe("Basic Delivery");
    expect(filterScenarios(shuffled, "", "", "", "duration").map((item) => item.estimated_minutes)).toEqual([1, 2, 3]);
  });

  it("filters the run history by every field", () => {
    const runs = [
      makeEpisode({ id: "a" }),
      makeEpisode({ id: "b", agent_mode: "manual", status: "failed", score: 42, success: false, created_at: "2026-02-01T08:00:00+00:00" }),
      makeEpisode({ id: "c", scenario_id: "obstacle-navigation", status: "aborted", score: null, success: null }),
    ];
    const none = { scenario: "", agent: "", status: "", date: "", minScore: "" };
    const ids = (filters: Partial<typeof none>) => filterHistory(runs, { ...none, ...filters }).map((run) => run.id);

    expect(ids({})).toEqual(["a", "b", "c"]);
    expect(ids({ scenario: "obstacle-navigation" })).toEqual(["c"]);
    expect(ids({ agent: "manual" })).toEqual(["b"]);
    expect(ids({ status: "completed" })).toEqual(["a"]);
    expect(ids({ date: "2026-02-01" })).toEqual(["b"]);
    expect(ids({ minScore: "50" })).toEqual(["a"]);
  });
});

describe("page data shaping", () => {
  it("groups API endpoints by their first tag", () => {
    const groups = groupEndpoints({
      info: { title: "SIMFORGE API", version: "1.0.0" },
      paths: {
        "/api/v1/scenarios/": { get: { tags: ["Scenarios"], summary: "List" } },
        "/api/v1/episodes/": { get: { tags: ["Episodes"], summary: "List" }, post: { tags: ["Episodes"], summary: "Create" } },
        "/untagged": { get: {} },
      },
    });

    expect(groups.map((group) => [group.tag, group.endpoints.length])).toEqual([["Scenarios", 1], ["Episodes", 2], ["Other", 1]]);
    expect(groups[1].endpoints[1]).toEqual({ method: "post", path: "/api/v1/episodes/", summary: "Create" });
  });

  it("builds chart rows from evaluated runs without inventing values", () => {
    const rows = chartRows([makeEvaluated(), makeEvaluated({ id: "ep-2", score: 30, success: false, steps: 150, collisions: 4 })]);

    expect(rows.map((row) => row.run)).toEqual(["#1", "#2"]);
    expect(rows[1]).toMatchObject({ id: "ep-2", score: 30, steps: 150, collisions: 4, success: false });
  });

  it("groups documents while keeping their order", () => {
    const groups = groupDocuments([
      { slug: "workflows-01", title: "01", group: "Workflows" },
      { slug: "tasks-01", title: "Task 01", group: "Task specifications" },
      { slug: "workflows-02", title: "02", group: "Workflows" },
    ]);

    expect(groups.map(([name, documents]) => [name, documents.map((document) => document.slug)])).toEqual([
      ["Workflows", ["workflows-01", "workflows-02"]],
      ["Task specifications", ["tasks-01"]],
    ]);
  });
});
