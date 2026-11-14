import { ArrowRight, Clock, Forklift, Package, Target } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { DifficultyBadge } from "@/components/StatusBadge";
import { Badge, ButtonLink, Card } from "@/components/ui/primitives";
import { AGENT_LABELS } from "@/services/format";
import type { Scenario } from "@/types/api";

/** The scenario preview is a real Panda3D render produced by the engine at startup. */
export function ScenarioThumbnail({ scenario, className }: { scenario: Scenario; className?: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div className={`viewport-frame flex items-center justify-center text-xs text-faint ${className ?? ""}`}>
        Preview appears once the Panda3D engine has rendered it
      </div>
    );
  }
  return (
    <img
      src={scenario.thumbnail_url}
      alt={`Panda3D render of the ${scenario.name} warehouse`}
      loading="lazy"
      onError={() => setFailed(true)}
      className={`object-cover ${className ?? ""}`}
    />
  );
}

export function ScenarioCard({ scenario, showAgents = false }: { scenario: Scenario; showAgents?: boolean }) {
  return (
    <Card className="group flex animate-rise flex-col overflow-hidden transition-colors hover:border-accent/40">
      <Link to={`/scenarios/${scenario.id}`} className="relative block" aria-label={`Open ${scenario.name}`}>
        <ScenarioThumbnail scenario={scenario} className="aspect-video w-full" />
        <span className="absolute left-3 top-3">
          <DifficultyBadge difficulty={scenario.difficulty} />
        </span>
      </Link>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div>
          <h3 className="text-base font-semibold text-ink">{scenario.name}</h3>
          <p className="mt-1 text-sm text-soft">{scenario.summary}</p>
        </div>
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-faint">
          <li className="flex items-center gap-1">
            <Target className="size-3.5" aria-hidden="true" />
            {scenario.task_type}
          </li>
          <li className="flex items-center gap-1">
            <Package className="size-3.5" aria-hidden="true" />
            {scenario.objectives} {scenario.objectives === 1 ? "objective" : "objectives"}
          </li>
          <li className="flex items-center gap-1">
            <Forklift className="size-3.5" aria-hidden="true" />
            {scenario.moving_obstacles} moving
          </li>
          <li className="flex items-center gap-1">
            <Clock className="size-3.5" aria-hidden="true" />
            about {scenario.estimated_minutes} min
          </li>
        </ul>
        {showAgents && (
          <div className="flex flex-wrap gap-1.5">
            <Badge>Complexity: {scenario.complexity}</Badge>
            {scenario.available_agents.map((agent) => (
              <Badge key={agent}>{AGENT_LABELS[agent]}</Badge>
            ))}
          </div>
        )}
        <div className="mt-auto pt-1">
          <ButtonLink to={`/scenarios/${scenario.id}`} variant="secondary" icon={ArrowRight} className="w-full">
            Open scenario
          </ButtonLink>
        </div>
      </div>
    </Card>
  );
}
