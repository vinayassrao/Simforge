import type {
  ActionName,
  ActionResult,
  AgentCatalog,
  AgentMode,
  DocumentContent,
  DocumentSummary,
  EpisodeDetail,
  Episode,
  EvaluationReport,
  EvaluationsResponse,
  Health,
  LiveState,
  Overview,
  Scenario,
  ScenarioDetail,
  SimEvent,
  ViewSettings,
} from "@/types/api";

export const API_BASE = "/api/v1";
export const STREAM_URL = `${API_BASE}/simulation/stream/`;
export const SWAGGER_URL = "/api/docs";
export const OPENAPI_URL = "/api/openapi.json";

/** An error returned by the API in its standard `{error: {code, message}}` shape. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path.startsWith("/") ? path : `${API_BASE}/${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "network_error", "Cannot reach the SIMFORGE server. Is it running?");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      body?.error?.code ?? "http_error",
      body?.error?.message ?? `Request failed with status ${response.status}.`,
    );
  }
  return (await response.json()) as T;
}

const get = <T>(path: string) => request<T>(path);
const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });

function query(params: Record<string, string | number | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export interface EpisodeFilters {
  scenario_id?: string;
  agent_mode?: string;
  status?: string;
  min_score?: number;
}

export type ControlCommand = "start" | "pause" | "resume" | "reset";

export const api = {
  health: () => get<Health>("health/"),
  overview: () => get<Overview>("overview/"),
  scenarios: () => get<Scenario[]>("scenarios/"),
  scenario: (id: string) => get<ScenarioDetail>(`scenarios/${id}/`),
  createEpisode: (scenario_id: string, agent_mode: AgentMode, seed?: number) =>
    post<EpisodeDetail>("episodes/", { scenario_id, agent_mode, seed }),
  episodes: (filters: EpisodeFilters = {}) => get<Episode[]>(`episodes/${query({ ...filters })}`),
  episode: (id: string) => get<EpisodeDetail>(`episodes/${id}/`),
  control: (id: string, command: ControlCommand) => post<LiveState>(`episodes/${id}/${command}/`),
  step: (id: string) => post<ActionResult>(`episodes/${id}/step/`),
  setSpeed: (id: string, speed: number) => post<{ speed: number }>(`episodes/${id}/speed/`, { speed }),
  act: (id: string, action: ActionName) => post<ActionResult>(`episodes/${id}/actions/`, { action }),
  events: (id: string) => get<SimEvent[]>(`episodes/${id}/events/`),
  evaluation: (id: string) => get<EvaluationReport>(`episodes/${id}/evaluation/`),
  evaluations: () => get<EvaluationsResponse>("evaluations/"),
  setView: (settings: Partial<ViewSettings>) => post<ViewSettings>("simulation/view/", settings),
  camera: (action: "reset" | "zoom_in" | "zoom_out" | "preset", preset?: ViewSettings["camera"]) =>
    post<ViewSettings>("simulation/camera/", { action, preset }),
  launchNativeViewer: (scenario_id: string, agent_mode: "manual" | "astar") =>
    post<{ launched: boolean; pid: number }>("simulation/native-viewer/", { scenario_id, agent_mode }),
  agents: () => get<AgentCatalog>("agents/"),
  documents: () => get<DocumentSummary[]>("documents/"),
  document: (slug: string) => get<DocumentContent>(`documents/${slug}/`),
  openapi: () => get<OpenApiDocument>(OPENAPI_URL),
  exportUrl: (id: string, format: "json" | "csv") => `${API_BASE}/episodes/${id}/export/?format=${format}`,
};

export interface OpenApiOperation {
  summary?: string;
  description?: string;
  tags?: string[];
}

export interface OpenApiDocument {
  info: { title: string; version: string; description?: string };
  paths: Record<string, Record<string, OpenApiOperation>>;
}

export function socketUrl(episodeId: string): string {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  return `${protocol}://${window.location.host}/ws/episodes/${episodeId}/`;
}
