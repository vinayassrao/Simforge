import clsx from "clsx";
import {
  ArrowDown,
  ArrowUp,
  CornerUpLeft,
  CornerUpRight,
  Hand,
  Hourglass,
  type LucideIcon,
  PackageCheck,
} from "lucide-react";
import { useEffect } from "react";

import { Badge, MiniStat, SectionCard } from "@/components/ui/primitives";
import { AGENT_LABELS, formatCell, humanize } from "@/services/format";
import type { ActionName, AgentMode, Observation } from "@/types/api";

interface ControlDefinition {
  action: ActionName;
  label: string;
  keys: string[];
  keyHint: string;
  icon: LucideIcon;
  area: string;
}

export const CONTROLS: ControlDefinition[] = [
  { action: "TURN_LEFT", label: "Turn left", keys: ["ArrowLeft", "a"], keyHint: "A / Left", icon: CornerUpLeft, area: "col-start-1 row-start-1" },
  { action: "MOVE_FORWARD", label: "Forward", keys: ["ArrowUp", "w"], keyHint: "W / Up", icon: ArrowUp, area: "col-start-2 row-start-1" },
  { action: "TURN_RIGHT", label: "Turn right", keys: ["ArrowRight", "d"], keyHint: "D / Right", icon: CornerUpRight, area: "col-start-3 row-start-1" },
  { action: "PICK_UP", label: "Pick up", keys: ["e"], keyHint: "E", icon: Hand, area: "col-start-1 row-start-2" },
  { action: "MOVE_BACKWARD", label: "Backward", keys: ["ArrowDown", "s"], keyHint: "S / Down", icon: ArrowDown, area: "col-start-2 row-start-2" },
  { action: "DROP", label: "Drop", keys: ["q"], keyHint: "Q", icon: PackageCheck, area: "col-start-3 row-start-2" },
  { action: "WAIT", label: "Wait one step", keys: ["x"], keyHint: "X", icon: Hourglass, area: "col-span-3 row-start-3" },
];

const KEY_TO_ACTION = new Map(CONTROLS.flatMap((control) => control.keys.map((key) => [key.toLowerCase(), control.action] as const)));

function isTyping(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
}

interface ControlPadProps {
  available: ActionName[];
  enabled: boolean;
  onAction: (action: ActionName) => void;
}

export function ControlPad({ available, enabled, onAction }: ControlPadProps) {
  useEffect(() => {
    if (!enabled) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.ctrlKey || event.metaKey || event.altKey || isTyping(event.target)) return;
      const action = KEY_TO_ACTION.get(event.key.toLowerCase());
      if (action) {
        event.preventDefault();
        onAction(action);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [enabled, onAction]);

  return (
    <div role="group" aria-label="Robot controls" className="grid grid-cols-3 gap-2">
      {CONTROLS.map(({ action, label, keyHint, icon: Icon, area }) => {
        const willSucceed = available.includes(action);
        return (
          <button
            key={action}
            type="button"
            disabled={!enabled}
            onClick={() => onAction(action)}
            title={willSucceed ? undefined : "This action would fail right now. You can still send it to see what happens."}
            className={clsx(
              "flex flex-col items-center gap-0.5 rounded-lg border px-2 py-2 text-xs font-medium transition-colors",
              "disabled:cursor-not-allowed disabled:opacity-40",
              area,
              willSucceed
                ? "border-accent/40 bg-accent/10 text-ink hover:bg-accent/20"
                : "border-line bg-raised text-faint hover:text-soft",
            )}
          >
            <Icon className="size-4" aria-hidden="true" />
            {label}
            <kbd className="font-mono text-[0.65rem] text-faint">{keyHint}</kbd>
          </button>
        );
      })}
    </div>
  );
}

interface AgentPanelProps {
  mode: AgentMode;
  observation: Observation;
  canAct: boolean;
  feedback: { ok: boolean; text: string } | null;
  onAction: (action: ActionName) => void;
}

const MODE_NOTES: Record<AgentMode, string> = {
  manual: "You are in control. Highlighted buttons will succeed right now; greyed ones would fail.",
  astar: "The built-in A* agent chooses every action. Use Pause and Step forward to follow its decisions.",
  external: "Waiting for actions from an external program through the API. You can also send actions from here.",
};

export function AgentPanel({ mode, observation, canAct, feedback, onAction }: AgentPanelProps) {
  const { agent, available_actions: available } = observation;
  return (
    <SectionCard title="Agent" hint="Who is driving, and what the robot is doing now.">
      <dl className="grid grid-cols-2 gap-2">
        <MiniStat label="Mode" value={AGENT_LABELS[mode]} />
        <MiniStat label="State" value={humanize(agent.state)} tone="accent" />
        <MiniStat label="Position (x, y)" value={formatCell(agent.position)} />
        <MiniStat label="Facing" value={humanize(agent.orientation)} />
        <div className="col-span-2">
          <MiniStat
            label="Carrying"
            value={agent.carrying ? (agent.carrying_object_id ?? "A package") : "Nothing"}
            tone={agent.carrying ? "good" : undefined}
          />
        </div>
      </dl>

      <div className="mt-3">
        <p className="mb-1.5 text-xs font-medium text-faint">Actions that would succeed right now</p>
        <ul className="flex flex-wrap gap-1.5">
          {available.length === 0 && <li className="text-xs text-faint">None. The episode is not running.</li>}
          {available.map((action) => (
            <li key={action}>
              <Badge tone="accent" className="font-mono">
                {action}
              </Badge>
            </li>
          ))}
        </ul>
      </div>

      <p className="mt-3 text-xs text-soft">{MODE_NOTES[mode]}</p>
      {mode !== "astar" && (
        <div className="mt-3">
          <ControlPad available={available} enabled={canAct} onAction={onAction} />
          <p
            role="status"
            aria-live="polite"
            className={clsx("mt-2 min-h-5 text-xs", feedback?.ok === false ? "text-warn" : "text-soft")}
          >
            {feedback?.text ?? (canAct ? "Use the buttons or your keyboard." : "Start the simulation to enable the controls.")}
          </p>
        </div>
      )}
    </SectionCard>
  );
}
