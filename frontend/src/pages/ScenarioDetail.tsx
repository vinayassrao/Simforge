import { ArrowLeft, CheckCircle2, MonitorPlay, XCircle } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";

import { LaunchPanel } from "@/components/LaunchPanel";
import { ScenarioThumbnail } from "@/components/ScenarioCard";
import { DifficultyBadge } from "@/components/StatusBadge";
import { Badge, Button, ButtonLink, Card, ErrorNote, MiniStat, SectionCard, Spinner } from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";

export function ScenarioDetail() {
  const { scenarioId = "" } = useParams();
  const { data: scenario, error, loading, reload } = useApi(() => api.scenario(scenarioId), [scenarioId]);
  const [viewerMessage, setViewerMessage] = useState<string | null>(null);

  const openNativeViewer = async () => {
    try {
      await api.launchNativeViewer(scenarioId, "astar");
      setViewerMessage("A Panda3D window is opening on the computer that runs the server.");
    } catch (reason) {
      setViewerMessage(reason instanceof Error ? reason.message : "Could not open the native viewer.");
    }
  };

  if (loading) return <Spinner label="Loading scenario" />;
  if (error || !scenario) return <ErrorNote message={error ?? "Scenario not found."} onRetry={reload} />;

  return (
    <div className="mx-auto max-w-7xl">
      <ButtonLink to="/scenarios" variant="ghost" size="sm" icon={ArrowLeft} className="mb-3">
        All scenarios
      </ButtonLink>

      <div className="grid gap-5 xl:grid-cols-3">
        <div className="flex flex-col gap-5 xl:col-span-2">
          <Card className="overflow-hidden">
            <ScenarioThumbnail scenario={scenario} className="aspect-video w-full" />
            <div className="p-5">
              <div className="flex flex-wrap items-center gap-2">
                <DifficultyBadge difficulty={scenario.difficulty} />
                <Badge>{scenario.task_type}</Badge>
                <Badge>Complexity: {scenario.complexity}</Badge>
              </div>
              <h1 className="mt-3 text-2xl font-semibold tracking-tight text-ink">{scenario.name}</h1>
              <p className="mt-2 text-sm text-soft">{scenario.description}</p>
              <div className="mt-4 rounded-lg border border-accent/30 bg-accent/10 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-accent">The task given to the agent</p>
                <p className="mt-1 text-base text-ink">{scenario.instructions}</p>
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
                <MiniStat label="Warehouse size" value={`${scenario.grid.width} x ${scenario.grid.height} cells`} />
                <MiniStat label="Packages" value={scenario.objectives} />
                <MiniStat label="Moving obstacles" value={scenario.moving_obstacles} />
                <MiniStat label="Step limit" value={scenario.max_steps} />
              </dl>
            </div>
          </Card>

          <div className="grid gap-5 md:grid-cols-2">
            <SectionCard title="How the run ends" hint="When the task counts as done, and when it fails.">
              <ul className="flex flex-col gap-2 text-sm">
                {scenario.completion_conditions.map((condition) => (
                  <li key={condition} className="flex gap-2 text-soft">
                    <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-good" aria-hidden="true" />
                    {condition}
                  </li>
                ))}
                {scenario.failure_conditions.map((condition) => (
                  <li key={condition} className="flex gap-2 text-soft">
                    <XCircle className="mt-0.5 size-4 shrink-0 text-bad" aria-hidden="true" />
                    {condition}
                  </li>
                ))}
                <li className="flex gap-2 text-faint">
                  <XCircle className="mt-0.5 size-4 shrink-0 text-bad" aria-hidden="true" />
                  Safety limit: {scenario.max_collisions} collisions or restricted-area entries.
                </li>
              </ul>
            </SectionCard>

            <SectionCard title="How success is measured" hint="A transparent 100-point score.">
              <ul className="flex flex-col gap-2.5">
                {scenario.evaluation_criteria.map((criterion) => (
                  <li key={criterion.label} className="flex items-start justify-between gap-3 text-sm">
                    <span>
                      <span className="block font-medium text-ink">{criterion.label}</span>
                      <span className="block text-xs text-faint">{criterion.description}</span>
                    </span>
                    <span className="shrink-0 font-mono text-accent">{criterion.points} pts</span>
                  </li>
                ))}
              </ul>
            </SectionCard>
          </div>

          <SectionCard title="What is in the warehouse" hint="Everything the robot can meet in this scenario.">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-faint">Packages</h3>
                <ul className="flex flex-col gap-2">
                  {scenario.packages.map((item) => (
                    <li key={item.id} className="rounded-lg border border-line bg-raised p-2.5 text-sm">
                      <span className="font-medium text-ink">{item.name}</span>
                      <span className="block text-xs text-soft">
                        {item.category}, {item.weight_kg} kg, deliver to the {item.destination_zone_name.toLowerCase()}
                      </span>
                      <span className="block font-mono text-[0.7rem] text-faint">{item.id}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-faint">Zones</h3>
                <ul className="flex flex-col gap-1.5 text-sm text-soft">
                  {scenario.layout.zones.map((zone) => (
                    <li key={zone.id} className="flex items-center gap-2">
                      <svg viewBox="0 0 12 12" className="size-3 shrink-0" aria-hidden="true">
                        <rect width="12" height="12" rx="3" fill={zone.color} />
                      </svg>
                      {zone.name}
                      <span className="text-xs text-faint">({zone.kind})</span>
                    </li>
                  ))}
                </ul>
                <h3 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-faint">Obstacles</h3>
                <p className="text-sm text-soft">
                  {scenario.layout.shelves.length} shelf cells, {scenario.static_obstacles} pallet stacks
                  {scenario.layout.patrols.length > 0
                    ? `, and ${scenario.layout.patrols.map((patrol) => patrol.name).join(", ")} on patrol.`
                    : ". Nothing moves in this scenario."}
                </p>
              </div>
            </div>
          </SectionCard>
        </div>

        <div className="flex flex-col gap-5">
          <SectionCard title="Launch this scenario" hint="You can change the agent for every run." className="xl:sticky xl:top-20">
            <LaunchPanel scenario={scenario} />
          </SectionCard>
          <SectionCard
            title="Native Panda3D viewer"
            hint="Open the same engine in a desktop window."
            help="The browser shows frames streamed from an off-screen Panda3D buffer. This button starts a normal Panda3D window on the machine running the server, with keyboard controls."
          >
            <Button icon={MonitorPlay} onClick={openNativeViewer} className="w-full">
              Open native viewer
            </Button>
            {viewerMessage && (
              <p className="mt-2 text-xs text-soft" role="status">
                {viewerMessage}
              </p>
            )}
          </SectionCard>
        </div>
      </div>
    </div>
  );
}
