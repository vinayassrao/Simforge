import { FileBarChart2, Radio, Rocket } from "lucide-react";
import { useCallback, useState } from "react";
import { Navigate, useParams } from "react-router-dom";

import { EventFeed } from "@/components/EventFeed";
import { AgentPanel } from "@/components/live/AgentPanel";
import { ObservationPanel } from "@/components/live/ObservationPanel";
import { LiveMetricsStrip, PerformancePanel } from "@/components/live/PerformancePanel";
import { SimulationToolbar } from "@/components/live/SimulationToolbar";
import { TaskPanel } from "@/components/live/TaskPanel";
import { Timeline } from "@/components/live/Timeline";
import { Viewport } from "@/components/live/Viewport";
import { ResultBadge } from "@/components/StatusBadge";
import { ButtonLink, Card, EmptyState, ErrorNote, SectionCard, Spinner, Tabs } from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { useEpisodeSocket } from "@/hooks/useEpisodeSocket";
import { api, type ControlCommand } from "@/services/api";
import { FAILURE_LABELS, formatScore } from "@/services/format";
import type { ActionName, EvaluationReport } from "@/types/api";

type DetailTab = "activity" | "observation" | "performance";

/** `/simulation` without an id: jump to the active run, or explain how to start one. */
export function LiveSimulationEntry() {
  const { data, error, loading, reload } = useApi(api.overview);
  if (loading) return <Spinner label="Looking for a live simulation" />;
  if (error) return <ErrorNote message={error} onRetry={reload} />;
  if (data?.active_episode_id) return <Navigate to={`/simulation/${data.active_episode_id}`} replace />;
  return (
    <Card className="mx-auto mt-10 max-w-xl">
      <EmptyState
        icon={Radio}
        title="No simulation is loaded"
        text="Choose a scenario, pick who controls the robot, and the live 3D view opens here."
        action={
          <ButtonLink to="/scenarios" variant="primary" icon={Rocket}>
            Choose a scenario
          </ButtonLink>
        }
      />
    </Card>
  );
}

function ResultBanner({ evaluation }: { evaluation: EvaluationReport }) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-accent/30 bg-accent/10 px-3 py-2.5">
      <ResultBadge success={evaluation.success} />
      <p className="min-w-0 flex-1 basis-40 text-sm text-ink">
        Performance score{" "}
        <span className="whitespace-nowrap font-mono font-semibold">{formatScore(evaluation.score)} / 100</span>
        {evaluation.failure_reason && (
          <span className="text-soft"> · {FAILURE_LABELS[evaluation.failure_reason] ?? evaluation.failure_reason}</span>
        )}
      </p>
      <ButtonLink to={`/evaluations/${evaluation.episode_id}`} variant="primary" size="sm" icon={FileBarChart2}>
        Open evaluation report
      </ButtonLink>
    </div>
  );
}

export function LiveSimulation() {
  const { episodeId = "" } = useParams();
  const feed = useEpisodeSocket(episodeId);
  const health = useApi(api.health, [], 10_000);
  const [tab, setTab] = useState<DetailTab>("activity");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ ok: boolean; text: string } | null>(null);

  const run = useCallback(async (operation: () => Promise<unknown>) => {
    setBusy(true);
    setError(null);
    try {
      await operation();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The command failed.");
    } finally {
      setBusy(false);
    }
  }, []);

  const onControl = useCallback(
    (command: ControlCommand) => {
      setFeedback(null);
      void run(() => api.control(episodeId, command));
    },
    [episodeId, run],
  );
  const onStep = useCallback(() => void run(() => api.step(episodeId)), [episodeId, run]);
  const onSpeed = useCallback((speed: number) => void run(() => api.setSpeed(episodeId, speed)), [episodeId, run]);
  const onAction = useCallback(
    (action: ActionName) => {
      api.act(episodeId, action).then(
        (result) => setFeedback({ ok: result.success, text: result.message }),
        (reason: unknown) => setFeedback({ ok: false, text: reason instanceof Error ? reason.message : "The action was rejected." }),
      );
    },
    [episodeId],
  );

  const { episode, state } = feed;
  if (!episode) {
    return feed.connection === "closed" ? (
      <ErrorNote message="This episode could not be loaded. It may not exist, or the server is offline." />
    ) : (
      <Spinner label="Connecting to the simulation" />
    );
  }

  const status = feed.status ?? episode.status;
  if (!state) {
    return (
      <Card className="mx-auto mt-10 max-w-xl">
        <EmptyState
          icon={Radio}
          title="This run is no longer loaded in the simulation"
          text={`Episode ${episode.id} (${episode.scenario_name}) has ended or was replaced by a newer run. Its events and results are stored.`}
          action={
            <div className="flex flex-wrap justify-center gap-2">
              {episode.score !== null && (
                <ButtonLink to={`/evaluations/${episode.id}`} variant="primary" icon={FileBarChart2}>
                  Open evaluation report
                </ButtonLink>
              )}
              <ButtonLink to={`/scenarios/${episode.scenario_id}`} icon={Rocket}>
                Run this scenario again
              </ButtonLink>
            </div>
          }
        />
      </Card>
    );
  }

  const canAct = status === "running";
  return (
    <div className="mx-auto flex max-w-[110rem] flex-col gap-4">
      <SimulationToolbar
        scenarioName={episode.scenario_name}
        episodeId={episode.id}
        mode={state.mode}
        status={status}
        connection={feed.connection}
        speed={state.speed}
        isLive
        busy={busy}
        onControl={onControl}
        onStep={onStep}
        onSpeed={onSpeed}
      />
      {error && <ErrorNote message={error} />}

      <div className="grid gap-4 xl:grid-cols-12">
        <div className="flex min-w-0 flex-col gap-4 xl:col-span-8">
          <Viewport
            isLive
            rendering={health.data?.rendering ?? true}
            banner={feed.evaluation ? <ResultBanner evaluation={feed.evaluation} /> : undefined}
          />
          <Card className="p-4">
            <LiveMetricsStrip metrics={state.metrics} />
            <div className="mt-4">
              <Timeline events={feed.events} step={state.metrics.steps} maxSteps={state.metrics.max_steps} />
            </div>
          </Card>
          <SectionCard
            title={
              tab === "activity"
                ? "Live activity"
                : tab === "observation"
                  ? "What the agent currently sees"
                  : "Performance"
            }
            hint={
              tab === "activity"
                ? "See every action your agent performs, as it happens."
                : tab === "observation"
                  ? "The observation: the agent's complete view of the world."
                  : "Live counters and engine timings."
            }
            actions={
              <Tabs
                label="Detail panel"
                active={tab}
                onChange={setTab}
                tabs={[
                  { id: "activity", label: "Live activity", count: feed.events.length },
                  { id: "observation", label: "Observation" },
                  { id: "performance", label: "Performance" },
                ]}
              />
            }
          >
            {tab === "activity" && <EventFeed events={feed.events} live heightClass="h-72" />}
            {tab === "observation" && <ObservationPanel observation={state.observation} />}
            {tab === "performance" && <PerformancePanel metrics={state.metrics} performance={feed.performance} />}
          </SectionCard>
        </div>

        <div className="flex min-w-0 flex-col gap-4 xl:col-span-4">
          <TaskPanel task={state.observation.task} />
          <AgentPanel
            mode={state.mode}
            observation={state.observation}
            canAct={canAct}
            feedback={feedback}
            onAction={onAction}
          />
        </div>
      </div>
    </div>
  );
}
