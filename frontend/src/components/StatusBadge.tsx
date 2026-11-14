import { Badge, type Tone } from "@/components/ui/primitives";
import { AGENT_LABELS, STATUS_LABELS } from "@/services/format";
import type { AgentMode, EpisodeStatus } from "@/types/api";

const STATUS_TONES: Record<EpisodeStatus, Tone> = {
  created: "neutral",
  running: "accent",
  paused: "warn",
  completed: "good",
  failed: "bad",
  aborted: "neutral",
};

const DIFFICULTY_TONES: Record<string, Tone> = {
  Beginner: "good",
  Intermediate: "warn",
  Advanced: "bad",
};

export function StatusBadge({ status }: { status: EpisodeStatus }) {
  return (
    <Badge tone={STATUS_TONES[status]}>
      {status === "running" && <span className="size-1.5 animate-pulse-dot rounded-full bg-current" aria-hidden="true" />}
      {STATUS_LABELS[status]}
    </Badge>
  );
}

export function AgentBadge({ mode }: { mode: AgentMode }) {
  return <Badge tone={mode === "astar" ? "info" : mode === "external" ? "accent" : "neutral"}>{AGENT_LABELS[mode]}</Badge>;
}

export function DifficultyBadge({ difficulty }: { difficulty: string }) {
  return (
    <Badge tone={DIFFICULTY_TONES[difficulty] ?? "neutral"} className="bg-panel/90 backdrop-blur">
      {difficulty}
    </Badge>
  );
}

export function ResultBadge({ success }: { success: boolean | null }) {
  if (success === null) return <Badge>Not evaluated</Badge>;
  return <Badge tone={success ? "good" : "bad"}>{success ? "Task succeeded" : "Task failed"}</Badge>;
}
