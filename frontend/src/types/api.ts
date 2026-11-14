export type Cell = [number, number];
export type ActionName =
  | "MOVE_FORWARD"
  | "MOVE_BACKWARD"
  | "TURN_LEFT"
  | "TURN_RIGHT"
  | "PICK_UP"
  | "DROP"
  | "WAIT";
export type AgentMode = "manual" | "astar" | "external";
export type EpisodeStatus = "created" | "running" | "paused" | "completed" | "failed" | "aborted";
export type EventCategory = "action" | "collision" | "error" | "milestone" | "info";

export interface Scenario {
  id: string;
  name: string;
  summary: string;
  description: string;
  instructions: string;
  difficulty: string;
  task_type: string;
  complexity: string;
  estimated_minutes: number;
  objectives: number;
  moving_obstacles: number;
  static_obstacles: number;
  grid: { width: number; height: number };
  max_steps: number;
  default_seed: number;
  available_agents: AgentMode[];
  thumbnail_url: string;
}

export interface Zone {
  id: string;
  name: string;
  kind: "loading" | "collection" | "delivery" | "restricted";
  color: string;
  cells: Cell[];
}

export interface ScenarioLayout {
  start: Cell;
  start_orientation: string;
  shelves: Cell[];
  static_obstacles: Cell[];
  checkpoints: Cell[];
  patrols: { id: string; name: string; start: Cell; end: Cell }[];
  zones: Zone[];
}

export interface ScenarioDetail extends Scenario {
  max_collisions: number;
  time_limit_s: number | null;
  completion_conditions: string[];
  failure_conditions: string[];
  evaluation_criteria: { label: string; points: number; description: string }[];
  packages: {
    id: string;
    name: string;
    category: string;
    color: string;
    weight_kg: number;
    destination_zone_name: string;
  }[];
  layout: ScenarioLayout;
}

export interface Episode {
  id: string;
  scenario_id: string;
  scenario_name: string;
  agent_mode: AgentMode;
  seed: number;
  status: EpisodeStatus;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  steps: number;
  progress: number;
  collisions: number;
  invalid_actions: number;
  elapsed_seconds: number;
  score: number | null;
  success: boolean | null;
  failure_reason: string | null;
}

export interface Incident {
  kind: "collision" | "restricted_area";
  cell: Cell;
  step: number;
  blocker: string;
}

export interface EpisodeDetail extends Episode {
  is_active: boolean;
  trajectory: [number, number, number, string][];
  incidents: Incident[];
}

export interface SimEvent {
  seq: number;
  episode_id: string;
  step: number;
  type: string;
  category: EventCategory;
  description: string;
  entity_id: string | null;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface ChecklistItem {
  id: string;
  label: string;
  done: boolean;
  current: boolean;
}

export interface Observation {
  episode_id: string;
  scenario_id: string;
  step: number;
  max_steps: number;
  status: EpisodeStatus;
  agent: {
    position: Cell;
    orientation: string;
    state: string;
    carrying: boolean;
    carrying_object_id: string | null;
  };
  target: {
    object_id: string;
    name: string;
    position: Cell | null;
    delivery_zone_id: string;
    delivery_zone_name: string;
    delivery_cells: Cell[];
  } | null;
  objects: {
    id: string;
    name: string;
    category: string;
    color: string;
    weight_kg: number;
    position: Cell | null;
    state: string;
    destination_zone_id: string;
  }[];
  zones: Zone[];
  obstacles: {
    static: Cell[];
    moving: { id: string; name: string; position: Cell; next_position: Cell }[];
  };
  grid: { width: number; height: number };
  checkpoints: Cell[];
  available_actions: ActionName[];
  task: {
    name: string;
    instructions: string;
    progress: number;
    current_objective: string;
    objectives_total: number;
    objectives_completed: number;
    checklist: ChecklistItem[];
  };
  recent_events: SimEvent[];
}

export interface LiveMetrics {
  steps: number;
  max_steps: number;
  actions: number;
  collisions: number;
  restricted_entries: number;
  invalid_actions: number;
  progress: number;
  elapsed_seconds: number;
  step_duration_ms: number;
  action_latency_ms: number;
}

export interface LiveState {
  episode_id: string;
  scenario_id: string;
  seed: number;
  mode: AgentMode;
  status: EpisodeStatus;
  speed: number;
  observation: Observation;
  planned_path: Cell[];
  incidents: Incident[];
  metrics: LiveMetrics;
}

export interface ActionResult {
  action: ActionName;
  success: boolean;
  message: string;
  error_code: string | null;
  done: boolean;
  observation: Observation;
}

export interface BreakdownItem {
  key: string;
  label: string;
  points: number;
  max_points: number;
  rule: string;
  explanation: string;
}

export interface EvaluationMetrics {
  task_completed: boolean;
  packages_total: number;
  packages_collected: number;
  packages_delivered: number;
  collisions: number;
  restricted_entries: number;
  invalid_actions: number;
  total_actions: number;
  steps: number;
  max_steps: number | null;
  elapsed_seconds: number;
  baseline_steps: number | null;
  path_efficiency: number | null;
  valid_action_rate: number;
  progress: number;
}

export interface EvaluationReport {
  episode_id: string;
  score: number;
  max_score: number;
  success: boolean;
  failure_reason: string | null;
  failure_explanation: string | null;
  breakdown: BreakdownItem[];
  metrics: EvaluationMetrics;
  behaviour_summary: string;
  recommendations: string[];
  incident_locations: Incident[];
}

export interface EvaluatedEpisode extends Episode {
  metrics: EvaluationMetrics;
  breakdown: BreakdownItem[];
}

export interface EvaluationsResponse {
  summary: {
    total_episodes: number;
    success_rate: number | null;
    average_score: number | null;
    average_completion_steps: number | null;
    collision_rate: number | null;
  };
  items: EvaluatedEpisode[];
}

export interface Overview {
  scenarios: number;
  total_runs: number;
  successful_runs: number;
  average_score: number | null;
  recent_episodes: Episode[];
  recent_events: SimEvent[];
  active_episode_id: string | null;
}

export interface Performance {
  fps?: number;
  frame_ms?: number;
  physical_contacts?: string[];
  renderer?: string;
  resolution?: [number, number];
}

export interface Health {
  status: "ok";
  simulation: "process" | "inline";
  rendering: boolean;
  active_episode_id: string | null;
  performance: Performance;
}

export interface ViewSettings {
  grid: boolean;
  paths: boolean;
  collisions: boolean;
  labels: boolean;
  collision_shapes: boolean;
  camera: "perspective" | "isometric" | "top";
  zoom: number;
}

export interface AgentCatalog {
  agents: { id: AgentMode; name: string; kind: string; description: string; how_it_acts: string }[];
  actions: { name: ActionName; meaning: string; precondition: string; failure: string }[];
  states: { name: string; next: string[] }[];
  speeds: number[];
  scoring: { key: string; label: string; max_points: number; rule: string }[];
  observation_schema: Record<string, unknown>;
  examples: Record<string, string>;
}

export interface DocumentSummary {
  slug: string;
  title: string;
  group: string;
}

export interface DocumentContent extends DocumentSummary {
  content: string;
}

export type SocketMessage =
  | { type: "hello"; episode: EpisodeDetail; state: LiveState | null }
  | { type: "state"; state: LiveState }
  | { type: "events"; events: SimEvent[] }
  | { type: "finished"; evaluation: EvaluationReport }
  | { type: "status"; status: EpisodeStatus }
  | { type: "perf"; perf: Performance };
