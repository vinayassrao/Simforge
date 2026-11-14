import clsx from "clsx";
import { Pause, Play, RotateCcw, StepForward, Wifi, WifiOff } from "lucide-react";
import { useId } from "react";

import { AgentBadge, StatusBadge } from "@/components/StatusBadge";
import { Button, Card, InfoTip } from "@/components/ui/primitives";
import type { ConnectionStatus } from "@/hooks/useEpisodeSocket";
import type { ControlCommand } from "@/services/api";
import type { AgentMode, EpisodeStatus } from "@/types/api";

export const SPEEDS = [0.25, 0.5, 1, 2, 4];

interface ToolbarProps {
  scenarioName: string;
  episodeId: string;
  mode: AgentMode;
  status: EpisodeStatus;
  connection: ConnectionStatus;
  speed: number;
  isLive: boolean;
  busy: boolean;
  onControl: (command: ControlCommand) => void;
  onStep: () => void;
  onSpeed: (speed: number) => void;
}

const CONNECTION_LABEL: Record<ConnectionStatus, string> = {
  connecting: "Connecting",
  open: "Live connection",
  closed: "Disconnected",
};

export function SimulationToolbar(props: ToolbarProps) {
  const { scenarioName, episodeId, mode, status, connection, speed, isLive, busy, onControl, onStep, onSpeed } = props;
  const speedId = useId();
  const finished = status === "completed" || status === "failed" || status === "aborted";
  const disabled = busy || !isLive;
  const ConnectionIcon = connection === "open" ? Wifi : WifiOff;

  return (
    <Card className="flex flex-wrap items-center gap-x-4 gap-y-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-lg font-semibold text-ink">{scenarioName}</h1>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
          <span className="font-mono text-faint">Episode {episodeId}</span>
          <StatusBadge status={status} />
          <AgentBadge mode={mode} />
          <span className={clsx("inline-flex items-center gap-1", connection === "open" ? "text-good" : "text-warn")}>
            <ConnectionIcon className="size-3.5" aria-hidden="true" />
            {CONNECTION_LABEL[connection]}
          </span>
        </div>
      </div>

      <div role="group" aria-label="Simulation controls" className="flex flex-wrap items-center gap-2">
        {status === "created" && (
          <Button variant="primary" icon={Play} disabled={disabled} onClick={() => onControl("start")}>
            Start
          </Button>
        )}
        {status === "running" && (
          <Button icon={Pause} disabled={disabled} onClick={() => onControl("pause")}>
            Pause
          </Button>
        )}
        {status === "paused" && (
          <Button variant="primary" icon={Play} disabled={disabled} onClick={() => onControl("resume")}>
            Resume
          </Button>
        )}
        <Button
          icon={StepForward}
          disabled={disabled || finished || status === "created"}
          onClick={onStep}
          title={mode === "astar" ? "Let the agent make one decision" : "Let one step pass (the robot waits)"}
        >
          Step forward
        </Button>
        <Button icon={RotateCcw} disabled={disabled} onClick={() => onControl("reset")}>
          Reset
        </Button>

        <div className="flex items-center gap-1.5">
          <label htmlFor={speedId} className="flex items-center gap-1 text-xs text-faint">
            Speed
            <InfoTip text="How fast the built-in agent acts. 1x is three actions per second. Manual and external agents act whenever they send an action." />
          </label>
          <select
            id={speedId}
            value={speed}
            disabled={disabled}
            onChange={(event) => onSpeed(Number(event.target.value))}
            className="h-9 rounded-lg border border-line bg-raised px-2 text-sm text-ink disabled:opacity-45"
          >
            {SPEEDS.map((value) => (
              <option key={value} value={value}>
                {value}x
              </option>
            ))}
          </select>
        </div>
      </div>
    </Card>
  );
}
