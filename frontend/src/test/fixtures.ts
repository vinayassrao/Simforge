import type { Episode, EvaluatedEpisode, LiveState, Scenario, SimEvent } from "@/types/api";

export function makeEvent(seq: number, overrides: Partial<SimEvent> = {}): SimEvent {
  return {
    seq,
    episode_id: "ep-test",
    step: seq,
    type: "MOVE_COMPLETED",
    category: "action",
    description: `Event ${seq}`,
    entity_id: null,
    data: {},
    timestamp: "2026-01-15T10:00:00+00:00",
    ...overrides,
  };
}

export function makeScenario(overrides: Partial<Scenario> = {}): Scenario {
  return {
    id: "basic-delivery",
    name: "Basic Delivery",
    summary: "Collect one package and deliver it.",
    description: "A quiet warehouse with nothing moving.",
    instructions: "Deliver the blue package.",
    difficulty: "Beginner",
    task_type: "Single delivery",
    complexity: "Low",
    estimated_minutes: 1,
    objectives: 1,
    moving_obstacles: 0,
    static_obstacles: 2,
    grid: { width: 16, height: 12 },
    max_steps: 150,
    default_seed: 7,
    available_agents: ["manual", "astar", "external"],
    thumbnail_url: "/api/v1/scenarios/basic-delivery/thumbnail/",
    ...overrides,
  };
}

export function makeEpisode(overrides: Partial<Episode> = {}): Episode {
  return {
    id: "ep-00000001",
    scenario_id: "basic-delivery",
    scenario_name: "Basic Delivery",
    agent_mode: "astar",
    seed: 7,
    status: "completed",
    created_at: "2026-01-15T10:00:00+00:00",
    started_at: "2026-01-15T10:00:01+00:00",
    finished_at: "2026-01-15T10:00:20+00:00",
    steps: 34,
    progress: 100,
    collisions: 0,
    invalid_actions: 0,
    elapsed_seconds: 11.3,
    score: 100,
    success: true,
    failure_reason: null,
    ...overrides,
  };
}

export function makeEvaluated(overrides: Partial<EvaluatedEpisode> = {}): EvaluatedEpisode {
  return {
    ...makeEpisode(),
    breakdown: [],
    metrics: {
      task_completed: true,
      packages_total: 1,
      packages_collected: 1,
      packages_delivered: 1,
      collisions: 0,
      restricted_entries: 0,
      invalid_actions: 0,
      total_actions: 34,
      steps: 34,
      max_steps: 150,
      elapsed_seconds: 11.3,
      baseline_steps: 34,
      path_efficiency: 1,
      valid_action_rate: 1,
      progress: 100,
    },
    ...overrides,
  };
}

export function makeState(steps: number, status: LiveState["status"] = "running"): LiveState {
  return {
    episode_id: "ep-test",
    scenario_id: "basic-delivery",
    seed: 7,
    mode: "manual",
    status,
    speed: 1,
    planned_path: [],
    incidents: [],
    metrics: {
      steps,
      max_steps: 150,
      actions: steps,
      collisions: 0,
      restricted_entries: 0,
      invalid_actions: 0,
      progress: 0,
      elapsed_seconds: 1,
      step_duration_ms: 0.1,
      action_latency_ms: 0.2,
    },
    observation: {} as LiveState["observation"],
  };
}
