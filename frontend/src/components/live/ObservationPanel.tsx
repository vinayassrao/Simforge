import { useState } from "react";

import { CodeBlock } from "@/components/ui/CodeBlock";
import { Badge, MiniStat, Tabs } from "@/components/ui/primitives";
import { formatCell, humanize } from "@/services/format";
import type { Observation } from "@/types/api";

type ObservationView = "readable" | "json";

function ReadableObservation({ observation }: { observation: Observation }) {
  const { agent, target, obstacles, objects } = observation;
  return (
    <div className="flex flex-col gap-4">
      <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <MiniStat label="Step" value={`${observation.step} / ${observation.max_steps}`} />
        <MiniStat label="Robot at" value={formatCell(agent.position)} />
        <MiniStat label="Facing" value={humanize(agent.orientation)} />
        <MiniStat label="Task state" value={humanize(agent.state)} tone="accent" />
      </dl>

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-line bg-raised p-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-faint">Current target</h3>
          {target ? (
            <ul className="mt-2 flex flex-col gap-1 text-sm text-soft">
              <li>
                <span className="font-medium text-ink">{target.name}</span>{" "}
                <span className="font-mono text-xs text-faint">{target.object_id}</span>
              </li>
              <li>{target.position ? `Waiting at ${formatCell(target.position)}` : "Currently on the robot"}</li>
              <li>
                Deliver to the {target.delivery_zone_name.toLowerCase()}: cells{" "}
                <span className="font-mono text-xs">{target.delivery_cells.map(formatCell).join(" ")}</span>
              </li>
            </ul>
          ) : (
            <p className="mt-2 text-sm text-soft">No target left. Every package has been delivered.</p>
          )}
        </div>

        <div className="rounded-lg border border-line bg-raised p-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-faint">Surroundings</h3>
          <ul className="mt-2 flex flex-col gap-1 text-sm text-soft">
            <li>
              Warehouse of {observation.grid.width} x {observation.grid.height} cells, {obstacles.static.length} blocked by
              shelves and pallets
            </li>
            <li>
              {obstacles.moving.length === 0
                ? "No moving obstacles"
                : obstacles.moving
                    .map((item) => `${item.name} at ${formatCell(item.position)}, heading to ${formatCell(item.next_position)}`)
                    .join("; ")}
            </li>
            <li>
              Packages:{" "}
              {objects.map((item) => `${item.name} (${item.state}${item.position ? ` at ${formatCell(item.position)}` : ""})`).join(", ")}
            </li>
          </ul>
        </div>
      </div>

      <div>
        <h3 className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-faint">Legal actions</h3>
        <ul className="flex flex-wrap gap-1.5">
          {observation.available_actions.length === 0 && <li className="text-sm text-faint">None while the episode is not running.</li>}
          {observation.available_actions.map((action) => (
            <li key={action}>
              <Badge tone="accent" className="font-mono">
                {action}
              </Badge>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/** "What the agent currently sees": a readable summary and the exact JSON an agent receives. */
export function ObservationPanel({ observation }: { observation: Observation }) {
  const [view, setView] = useState<ObservationView>("readable");
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-faint">
          This is the full information an agent gets each step. It is read straight from the Panda3D simulation.
        </p>
        <Tabs
          label="Observation format"
          active={view}
          onChange={setView}
          tabs={[
            { id: "readable", label: "Readable" },
            { id: "json", label: "Raw JSON" },
          ]}
        />
      </div>
      {view === "readable" ? (
        <ReadableObservation observation={observation} />
      ) : (
        <CodeBlock
          code={JSON.stringify(observation, null, 2)}
          language="json"
          title={`GET /api/v1/episodes/${observation.episode_id}/observation/`}
          maxHeightClass="max-h-80"
        />
      )}
    </div>
  );
}
