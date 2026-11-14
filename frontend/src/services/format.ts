import type { AgentMode, EpisodeStatus } from "@/types/api";

export const AGENT_LABELS: Record<AgentMode, string> = {
  manual: "Manual control",
  astar: "A* agent",
  external: "External agent",
};

export const STATUS_LABELS: Record<EpisodeStatus, string> = {
  created: "Ready",
  running: "Running",
  paused: "Paused",
  completed: "Completed",
  failed: "Failed",
  aborted: "Stopped",
};

export const FAILURE_LABELS: Record<string, string> = {
  step_limit_exceeded: "Step limit reached",
  collision_limit_exceeded: "Too many collisions",
  time_limit_exceeded: "Time limit reached",
  aborted: "Stopped before finishing",
};

/** "NAVIGATING_TO_OBJECT" -> "Navigating to object". */
export function humanize(value: string): string {
  const text = value.replaceAll("_", " ").toLowerCase();
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function formatScore(score: number | null | undefined): string {
  return score === null || score === undefined ? "-" : score.toFixed(1);
}

export function formatPercent(ratio: number | null | undefined, digits = 0): string {
  return ratio === null || ratio === undefined ? "-" : `${(ratio * 100).toFixed(digits)}%`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return "-";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ${Math.round(seconds - minutes * 60)}s`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour12: false });
}

export function formatCell(cell: [number, number] | null | undefined): string {
  return cell ? `(${cell[0]}, ${cell[1]})` : "-";
}
