import { ArrowLeft, Download, Lightbulb, Repeat } from "lucide-react";
import { useId, useState } from "react";
import { useParams } from "react-router-dom";

import { EventFeed } from "@/components/EventFeed";
import { PathMap, PathMapLegend } from "@/components/PathMap";
import { ScoreBreakdown, ScoreRing } from "@/components/ScoreBreakdown";
import { AgentBadge, ResultBadge, StatusBadge } from "@/components/StatusBadge";
import { buttonClasses, ButtonLink, Card, ErrorNote, MiniStat, SectionCard, Spinner } from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";
import { FAILURE_LABELS, formatCell, formatDateTime, formatDuration, formatPercent } from "@/services/format";

export function EvaluationReport() {
  const { episodeId = "" } = useParams();
  const episode = useApi(() => api.episode(episodeId), [episodeId]);
  const report = useApi(() => api.evaluation(episodeId), [episodeId]);
  const events = useApi(() => api.events(episodeId), [episodeId]);
  const scenario = useApi(
    () => (episode.data ? api.scenario(episode.data.scenario_id) : Promise.resolve(null)),
    [episode.data?.scenario_id],
  );
  const [replayStep, setReplayStep] = useState<number | null>(null);
  const sliderId = useId();

  if (episode.loading || report.loading) return <Spinner label="Loading the evaluation report" />;
  if (episode.error || !episode.data) return <ErrorNote message={episode.error ?? "Episode not found."} onRetry={episode.reload} />;
  if (report.error || !report.data) {
    return (
      <div className="mx-auto max-w-3xl">
        <ErrorNote message={report.error ?? "This run has no evaluation."} />
        <ButtonLink to={`/simulation/${episodeId}`} className="mt-3">
          Open the live view
        </ButtonLink>
      </div>
    );
  }

  const run = episode.data;
  const evaluation = report.data;
  const metrics = evaluation.metrics;
  const lastStep = run.trajectory.length > 0 ? run.trajectory[run.trajectory.length - 1][0] : 0;
  const shownStep = replayStep ?? lastStep;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <ButtonLink to="/evaluations" variant="ghost" size="sm" icon={ArrowLeft}>
          All evaluations
        </ButtonLink>
        <div className="flex flex-wrap gap-2">
          <a className={buttonClasses("secondary", "sm")} href={api.exportUrl(run.id, "json")} download>
            <Download className="size-4" aria-hidden="true" />
            Export JSON
          </a>
          <a className={buttonClasses("secondary", "sm")} href={api.exportUrl(run.id, "csv")} download>
            <Download className="size-4" aria-hidden="true" />
            Export events CSV
          </a>
          <ButtonLink to={`/scenarios/${run.scenario_id}`} size="sm" icon={Repeat}>
            Run again
          </ButtonLink>
        </div>
      </div>

      <Card className="hero-gradient flex flex-wrap items-center gap-6 p-6">
        <ScoreRing score={evaluation.score} success={evaluation.success} />
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">Evaluation report</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">{run.scenario_name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <ResultBadge success={evaluation.success} />
            <StatusBadge status={run.status} />
            <AgentBadge mode={run.agent_mode} />
            <span className="font-mono text-faint">
              {run.id} · seed {run.seed} · {formatDateTime(run.started_at)}
            </span>
          </div>
          <p className="mt-3 max-w-3xl text-sm text-soft">{evaluation.behaviour_summary}</p>
          {evaluation.failure_reason && (
            <p className="mt-2 text-sm text-bad">
              Failure reason: {FAILURE_LABELS[evaluation.failure_reason] ?? evaluation.failure_reason}.{" "}
              {evaluation.failure_explanation}
            </p>
          )}
          <p className="mt-2 text-xs text-faint">
            Success is a yes/no result and is separate from the score: a run can earn points and still fail the task.
          </p>
        </div>
      </Card>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard title="Performance score" hint="Where the points came from, with the rule behind each line.">
          <ScoreBreakdown breakdown={evaluation.breakdown} />
        </SectionCard>

        <div className="flex flex-col gap-5">
          <SectionCard title="Measured results" hint="Raw numbers recorded during the run.">
            <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              <MiniStat label="Task completed" value={metrics.task_completed ? "Yes" : "No"} tone={metrics.task_completed ? "good" : "bad"} />
              <MiniStat label="Packages collected" value={`${metrics.packages_collected} / ${metrics.packages_total}`} />
              <MiniStat label="Packages delivered" value={`${metrics.packages_delivered} / ${metrics.packages_total}`} />
              <MiniStat label="Total steps" value={metrics.steps} />
              <MiniStat label="Baseline route" value={metrics.baseline_steps ?? "-"} />
              <MiniStat label="Path efficiency" value={formatPercent(metrics.path_efficiency)} />
              <MiniStat label="Collisions" value={metrics.collisions} tone={metrics.collisions ? "bad" : "good"} />
              <MiniStat label="Restricted entries" value={metrics.restricted_entries} tone={metrics.restricted_entries ? "bad" : "good"} />
              <MiniStat label="Invalid actions" value={metrics.invalid_actions} tone={metrics.invalid_actions ? "warn" : "good"} />
              <MiniStat label="Valid action rate" value={formatPercent(metrics.valid_action_rate)} />
              <MiniStat label="Execution time" value={formatDuration(metrics.elapsed_seconds)} />
              <MiniStat label="Milestones reached" value={`${metrics.progress}%`} />
            </dl>
          </SectionCard>

          <SectionCard title="Recommendations" hint="Generated from the measured results of this run.">
            <ul className="flex flex-col gap-2">
              {evaluation.recommendations.map((tip) => (
                <li key={tip} className="flex gap-2 text-sm text-soft">
                  <Lightbulb className="mt-0.5 size-4 shrink-0 text-warn" aria-hidden="true" />
                  {tip}
                </li>
              ))}
            </ul>
          </SectionCard>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <SectionCard
          title="Route replay"
          hint="A top-down map drawn from the stored trajectory. Drag the slider to replay the run."
          help="This is a 2D summary built from recorded positions. The 3D view on the Live Simulation page is rendered by Panda3D."
        >
          {scenario.data ? (
            <>
              <PathMap
                grid={scenario.data.grid}
                layout={scenario.data.layout}
                trajectory={run.trajectory}
                incidents={run.incidents}
                untilStep={shownStep}
              />
              <div className="mt-3">
                <label htmlFor={sliderId} className="flex justify-between text-xs text-faint">
                  <span>Replay position</span>
                  <span className="font-mono">
                    step {shownStep} of {lastStep}
                  </span>
                </label>
                <input
                  id={sliderId}
                  type="range"
                  min={0}
                  max={lastStep}
                  value={shownStep}
                  onChange={(event) => setReplayStep(Number(event.target.value))}
                  className="mt-1 w-full accent-[var(--sf-accent)]"
                />
              </div>
              <PathMapLegend />
            </>
          ) : (
            <Spinner label="Loading the map" />
          )}
          <h3 className="mb-1.5 mt-4 text-xs font-semibold uppercase tracking-wide text-faint">Collision locations</h3>
          {evaluation.incident_locations.length === 0 ? (
            <p className="text-sm text-soft">No collisions or restricted-area entries were recorded.</p>
          ) : (
            <ul className="flex flex-col gap-1 text-sm text-soft">
              {evaluation.incident_locations.map((incident, index) => (
                <li key={index}>
                  Step {incident.step}: {incident.kind === "collision" ? "collision with" : "entered"}{" "}
                  {incident.blocker.replaceAll("_", " ")} at <span className="font-mono">{formatCell(incident.cell)}</span>
                </li>
              ))}
            </ul>
          )}
        </SectionCard>

        <SectionCard title="Event log" hint="Everything that happened, in order. Use the filters to find failed actions.">
          {events.error ? <ErrorNote message={events.error} onRetry={events.reload} /> : <EventFeed events={events.data ?? []} heightClass="h-[34rem]" />}
        </SectionCard>
      </div>
    </div>
  );
}
