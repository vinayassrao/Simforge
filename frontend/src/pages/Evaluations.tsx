import { Activity, BarChart3, CheckCircle2, Footprints, Gauge, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EpisodeTable } from "@/components/EpisodeTable";
import { ButtonLink, Card, EmptyState, ErrorNote, PageHeader, SectionCard, Spinner, Stat } from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";
import { AGENT_LABELS, formatPercent, formatScore } from "@/services/format";
import type { EvaluatedEpisode } from "@/types/api";

const AXIS = { stroke: "var(--sf-faint)", fontSize: 11 };
const TOOLTIP_STYLE = {
  contentStyle: { background: "var(--sf-raised)", border: "1px solid var(--sf-line)", borderRadius: 8, fontSize: 12 },
  labelStyle: { color: "var(--sf-ink)" },
  itemStyle: { color: "var(--sf-soft)" },
};
const MAX_COMPARED = 3;

export function chartRows(items: EvaluatedEpisode[]) {
  return items.map((item, index) => ({
    run: `#${index + 1}`,
    id: item.id,
    label: `${item.scenario_name} · ${AGENT_LABELS[item.agent_mode]}`,
    score: item.score ?? 0,
    steps: item.steps,
    collisions: item.collisions,
    success: item.success === true,
  }));
}

function ChartCard({ title, hint, children }: { title: string; hint: string; children: React.ReactElement }) {
  return (
    <SectionCard title={title} hint={hint}>
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </SectionCard>
  );
}

const COMPARISON_ROWS: { label: string; value: (item: EvaluatedEpisode) => string }[] = [
  { label: "Scenario", value: (item) => item.scenario_name },
  { label: "Agent", value: (item) => AGENT_LABELS[item.agent_mode] },
  { label: "Seed", value: (item) => String(item.seed) },
  { label: "Completion", value: (item) => (item.success ? "Completed" : "Not completed") },
  { label: "Overall score", value: (item) => formatScore(item.score) },
  { label: "Steps", value: (item) => String(item.steps) },
  { label: "Baseline route steps", value: (item) => String(item.metrics.baseline_steps ?? "-") },
  { label: "Path efficiency", value: (item) => formatPercent(item.metrics.path_efficiency) },
  { label: "Collisions", value: (item) => String(item.metrics.collisions) },
  { label: "Restricted-area entries", value: (item) => String(item.metrics.restricted_entries) },
  { label: "Invalid actions", value: (item) => String(item.metrics.invalid_actions) },
  { label: "Valid action rate", value: (item) => formatPercent(item.metrics.valid_action_rate) },
];

function Comparison({ items }: { items: EvaluatedEpisode[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[32rem] border-collapse text-left text-sm">
        <caption className="sr-only">Side-by-side comparison of the selected runs</caption>
        <thead>
          <tr className="border-b border-line text-xs text-faint">
            <th scope="col" className="px-2 py-2 font-medium">Metric</th>
            {items.map((item) => (
              <th key={item.id} scope="col" className="px-2 py-2 font-mono font-medium text-accent">{item.id}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {COMPARISON_ROWS.map((row) => (
            <tr key={row.label} className="border-b border-line/60 last:border-0">
              <th scope="row" className="px-2 py-1.5 font-normal text-soft">{row.label}</th>
              {items.map((item) => (
                <td key={item.id} className="px-2 py-1.5 font-mono text-ink">{row.value(item)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Evaluations() {
  const { data, error, loading, reload } = useApi(api.evaluations, [], 8000);
  const [selected, setSelected] = useState<string[]>([]);
  const rows = useMemo(() => chartRows(data?.items ?? []), [data]);
  const newestFirst = useMemo(() => [...(data?.items ?? [])].reverse(), [data]);
  const compared = useMemo(() => (data?.items ?? []).filter((item) => selected.includes(item.id)), [data, selected]);

  const toggle = (id: string) =>
    setSelected((current) =>
      current.includes(id) ? current.filter((value) => value !== id) : [...current, id].slice(-MAX_COMPARED),
    );

  if (loading && !data) return <Spinner label="Loading evaluations" />;
  if (error && !data) return <ErrorNote message={error} onRetry={reload} />;
  const summary = data!.summary;

  if (summary.total_episodes === 0) {
    return (
      <div className="mx-auto max-w-7xl">
        <PageHeader title="Evaluations" subtitle="Scores and comparisons for every finished run." />
        <Card>
          <EmptyState
            icon={BarChart3}
            title="Nothing has been evaluated yet"
            text="A run is scored automatically when it completes or fails. Finish one and the charts appear here."
            action={<ButtonLink to="/scenarios" variant="primary">Choose a scenario</ButtonLink>}
          />
        </Card>
      </div>
    );
  }

  const successes = rows.filter((row) => row.success).length;
  const outcome = [
    { name: "Succeeded", value: successes, color: "var(--sf-good)" },
    { name: "Failed", value: rows.length - successes, color: "var(--sf-bad)" },
  ];

  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-5">
      <PageHeader
        title="Evaluations"
        subtitle="Every finished run gets a performance score out of 100. All figures on this page are calculated from stored runs."
      />

      <section aria-label="Summary" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Stat label="Total episodes" value={summary.total_episodes} hint="Evaluated runs" icon={Activity} tone="info" />
        <Stat label="Success rate" value={formatPercent(summary.success_rate)} hint="Tasks fully completed" icon={CheckCircle2} tone="good" />
        <Stat label="Average score" value={formatScore(summary.average_score)} hint="Out of 100" icon={Gauge} />
        <Stat
          label="Average completion steps"
          value={summary.average_completion_steps ?? "-"}
          hint="Successful runs only"
          icon={Footprints}
          tone="warn"
        />
        <Stat label="Collision rate" value={formatPercent(summary.collision_rate)} hint="Runs with a safety incident" icon={ShieldAlert} tone="bad" />
      </section>

      <div className="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
        <ChartCard title="Score comparison" hint="Performance score of each run, oldest first.">
          <BarChart data={rows}>
            <CartesianGrid stroke="var(--sf-line)" vertical={false} />
            <XAxis dataKey="run" {...AXIS} />
            <YAxis domain={[0, 100]} {...AXIS} />
            <Tooltip {...TOOLTIP_STYLE} cursor={{ fill: "var(--sf-raised)" }} />
            <Bar dataKey="score" name="Score" radius={[4, 4, 0, 0]}>
              {rows.map((row) => (
                <Cell key={row.id} fill={row.success ? "var(--sf-accent)" : "var(--sf-warn)"} />
              ))}
            </Bar>
          </BarChart>
        </ChartCard>

        <ChartCard title="Success and failure" hint="How many runs completed their task.">
          <PieChart>
            <Pie data={outcome} dataKey="value" nameKey="name" innerRadius={48} outerRadius={78} paddingAngle={3}>
              {outcome.map((slice) => (
                <Cell key={slice.name} fill={slice.color} stroke="var(--sf-panel)" />
              ))}
            </Pie>
            <Tooltip {...TOOLTIP_STYLE} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
          </PieChart>
        </ChartCard>

        <ChartCard title="Steps per episode" hint="Fewer steps for the same task means a better route.">
          <BarChart data={rows}>
            <CartesianGrid stroke="var(--sf-line)" vertical={false} />
            <XAxis dataKey="run" {...AXIS} />
            <YAxis allowDecimals={false} {...AXIS} />
            <Tooltip {...TOOLTIP_STYLE} cursor={{ fill: "var(--sf-raised)" }} />
            <Bar dataKey="steps" name="Steps" fill="var(--sf-info)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartCard>

        <ChartCard title="Collision count" hint="Collisions and restricted-area entries per run.">
          <BarChart data={rows}>
            <CartesianGrid stroke="var(--sf-line)" vertical={false} />
            <XAxis dataKey="run" {...AXIS} />
            <YAxis allowDecimals={false} {...AXIS} />
            <Tooltip {...TOOLTIP_STYLE} cursor={{ fill: "var(--sf-raised)" }} />
            <Bar dataKey="collisions" name="Safety incidents" fill="var(--sf-bad)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ChartCard>

        <div className="lg:col-span-2">
          <ChartCard title="Performance over time" hint="Score of each run in the order they were executed.">
            <LineChart data={rows}>
              <CartesianGrid stroke="var(--sf-line)" vertical={false} />
              <XAxis dataKey="run" {...AXIS} />
              <YAxis domain={[0, 100]} {...AXIS} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Line type="monotone" dataKey="score" name="Score" stroke="var(--sf-accent)" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ChartCard>
        </div>
      </div>

      <SectionCard
        title="Compare runs"
        hint={`Tick up to ${MAX_COMPARED} runs in the table below to see them side by side.`}
      >
        {compared.length >= 2 ? (
          <Comparison items={compared} />
        ) : (
          <p className="text-sm text-faint">
            {compared.length === 1 ? "Select one more run to compare." : "No runs selected yet."}
          </p>
        )}
      </SectionCard>

      <SectionCard title="Evaluated episodes" hint="Open a run to read its full evaluation report.">
        <EpisodeTable episodes={newestFirst} selectedIds={selected} onToggleSelect={toggle} caption="Evaluated episodes" />
      </SectionCard>
    </div>
  );
}
