import { Activity, Boxes, CheckCircle2, Gauge, ListChecks, PlayCircle, Rocket } from "lucide-react";

import { EpisodeTable } from "@/components/EpisodeTable";
import { EventFeed } from "@/components/EventFeed";
import { ScenarioCard } from "@/components/ScenarioCard";
import { ButtonLink, Card, EmptyState, ErrorNote, SectionCard, Spinner, Stat } from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";
import { formatPercent, formatScore } from "@/services/format";

const QUICK_START = [
  { title: "Choose an environment", text: "Pick one of the warehouse scenarios from the library." },
  { title: "Select an agent", text: "Use the built-in A* agent, drive manually, or connect your own code." },
  { title: "Run and evaluate", text: "Watch the run live, then open its score report." },
];

export function Overview() {
  const overview = useApi(api.overview, [], 6000);
  const scenarios = useApi(api.scenarios);
  const stats = overview.data;
  const successRate = stats && stats.total_runs > 0 ? stats.successful_runs / stats.total_runs : null;

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6">
      <Card className="hero-gradient animate-rise overflow-hidden p-6 sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">AI Simulation &amp; Training Lab</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Welcome to SIMFORGE</h1>
            <p className="mt-2 text-base text-soft">
              Your workspace for building, testing and evaluating intelligent agents.
            </p>
            <p className="mt-3 text-sm text-faint">
              A warehouse robot lives in a real Panda3D world. Give it a delivery task, watch every action, and get an
              objective score at the end.
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <ButtonLink to="/scenarios" variant="primary" size="lg" icon={Rocket}>
              Launch your first simulation
            </ButtonLink>
            {stats?.active_episode_id && (
              <ButtonLink to={`/simulation/${stats.active_episode_id}`} variant="secondary" icon={PlayCircle}>
                Return to the live run
              </ButtonLink>
            )}
          </div>
        </div>
        <ol className="mt-6 grid gap-3 sm:grid-cols-3">
          {QUICK_START.map((step, index) => (
            <li key={step.title} className="flex gap-3 rounded-lg border border-line bg-panel/70 p-3">
              <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-accent text-sm font-bold text-accent-ink">
                {index + 1}
              </span>
              <span>
                <span className="block text-sm font-semibold text-ink">{step.title}</span>
                <span className="block text-xs text-soft">{step.text}</span>
              </span>
            </li>
          ))}
        </ol>
      </Card>

      {overview.error && <ErrorNote message={overview.error} onRetry={overview.reload} />}

      <section aria-label="Key figures" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Available scenarios" value={stats?.scenarios ?? "-"} hint="Ready-made 3D environments" icon={Boxes} />
        <Stat label="Simulation runs" value={stats?.total_runs ?? "-"} hint="Every run is stored" icon={Activity} tone="info" />
        <Stat
          label="Successful tasks"
          value={stats?.successful_runs ?? "-"}
          hint={successRate === null ? "No runs yet" : `${formatPercent(successRate)} of all runs`}
          icon={CheckCircle2}
          tone="good"
        />
        <Stat
          label="Average evaluation score"
          value={formatScore(stats?.average_score)}
          hint="Out of 100, across evaluated runs"
          icon={Gauge}
          tone="warn"
        />
      </section>

      <section aria-labelledby="featured-title">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <h2 id="featured-title" className="text-lg font-semibold text-ink">
              Featured scenarios
            </h2>
            <p className="text-sm text-faint">Previews are rendered by the Panda3D engine.</p>
          </div>
          <ButtonLink to="/scenarios" variant="ghost" size="sm">
            View all
          </ButtonLink>
        </div>
        {scenarios.loading && <Spinner label="Loading scenarios" />}
        {scenarios.error && <ErrorNote message={scenarios.error} onRetry={scenarios.reload} />}
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {scenarios.data?.map((scenario) => <ScenarioCard key={scenario.id} scenario={scenario} />)}
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-5">
        <SectionCard
          title="Recent runs"
          hint="The latest simulations, newest first."
          className="xl:col-span-3"
          actions={
            <ButtonLink to="/history" variant="ghost" size="sm">
              Full history
            </ButtonLink>
          }
        >
          {stats && stats.recent_episodes.length > 0 ? (
            <EpisodeTable episodes={stats.recent_episodes} caption="Recent simulation runs" />
          ) : (
            <EmptyState
              icon={ListChecks}
              title="No runs yet"
              text="Launch a simulation and it will appear here with its status and score."
            />
          )}
        </SectionCard>
        <SectionCard
          title="Recent activity"
          hint="Milestones, collisions and errors from the latest runs."
          className="xl:col-span-2"
        >
          <EventFeed events={[...(stats?.recent_events ?? [])].reverse()} heightClass="h-72" />
        </SectionCard>
      </div>
    </div>
  );
}
