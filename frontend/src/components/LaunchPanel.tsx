import clsx from "clsx";
import { Bot, Code2, Gamepad2, type LucideIcon, Rocket } from "lucide-react";
import { useId, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button, ErrorNote, InfoTip } from "@/components/ui/primitives";
import { api } from "@/services/api";
import type { AgentMode, Scenario } from "@/types/api";

const AGENT_OPTIONS: { id: AgentMode; label: string; text: string; icon: LucideIcon }[] = [
  { id: "astar", label: "Built-in A* agent", text: "Watch the autonomous baseline plan a route and deliver.", icon: Bot },
  { id: "manual", label: "Manual control", text: "Drive the robot yourself with buttons or the keyboard.", icon: Gamepad2 },
  { id: "external", label: "External Python agent", text: "Your own script sends the actions through the API.", icon: Code2 },
];

/** Choose an agent and a seed, then create the episode and open the live workspace. */
export function LaunchPanel({ scenario }: { scenario: Scenario }) {
  const navigate = useNavigate();
  const groupId = useId();
  const seedId = useId();
  const [agent, setAgent] = useState<AgentMode>("astar");
  const [seed, setSeed] = useState(String(scenario.default_seed));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const launch = async () => {
    const parsedSeed = Number.parseInt(seed, 10);
    if (!Number.isInteger(parsedSeed) || parsedSeed < 0) {
      setError("The seed must be a whole number, 0 or greater.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const episode = await api.createEpisode(scenario.id, agent, parsedSeed);
      navigate(`/simulation/${episode.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not start the simulation.");
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <fieldset>
        <legend id={groupId} className="mb-2 text-sm font-semibold text-ink">
          1. Who controls the robot?
        </legend>
        <div className="grid gap-2">
          {AGENT_OPTIONS.map(({ id, label, text, icon: Icon }) => (
            <label
              key={id}
              className={clsx(
                "flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors",
                agent === id ? "border-accent/50 bg-accent/10" : "border-line bg-raised hover:border-accent/30",
              )}
            >
              <input
                type="radio"
                name={groupId}
                value={id}
                checked={agent === id}
                onChange={() => setAgent(id)}
                className="mt-1 accent-[var(--sf-accent)]"
              />
              <Icon className={clsx("mt-0.5 size-4 shrink-0", agent === id ? "text-accent" : "text-faint")} aria-hidden="true" />
              <span className="min-w-0">
                <span className="block text-sm font-medium text-ink">{label}</span>
                <span className="block text-xs text-soft">{text}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div>
        <label htmlFor={seedId} className="mb-1 flex items-center gap-1.5 text-sm font-semibold text-ink">
          2. Random seed
          <InfoTip text="The seed decides where packages start and how the forklifts are placed. The same scenario and seed always give exactly the same run." />
        </label>
        <input
          id={seedId}
          type="number"
          min={0}
          inputMode="numeric"
          value={seed}
          onChange={(event) => setSeed(event.target.value)}
          className="h-9 w-full rounded-lg border border-line bg-raised px-3 font-mono text-sm text-ink"
        />
      </div>

      {error && <ErrorNote message={error} />}
      <Button variant="primary" size="lg" icon={Rocket} busy={busy} onClick={launch}>
        Launch simulation
      </Button>
      <p className="text-xs text-faint">
        One simulation runs at a time. Launching a new one stops an unfinished run and keeps it in the history.
      </p>
    </div>
  );
}
