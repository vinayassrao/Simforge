import { Download, FileBarChart2, History, ListTree, Radio } from "lucide-react";
import { useId, useMemo, useState } from "react";

import { AgentBadge, StatusBadge } from "@/components/StatusBadge";
import { buttonClasses, ButtonLink, Card, EmptyState, ErrorNote, PageHeader, Spinner } from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";
import { AGENT_LABELS, formatDateTime, formatScore, STATUS_LABELS } from "@/services/format";
import type { AgentMode, Episode, EpisodeStatus } from "@/types/api";

const FIELD_CLASS = "h-9 w-full rounded-lg border border-line bg-raised px-2.5 text-sm text-ink";

export interface HistoryFilters {
  scenario: string;
  agent: string;
  status: string;
  date: string;
  minScore: string;
}

export function filterHistory(episodes: Episode[], filters: HistoryFilters): Episode[] {
  const minimum = filters.minScore === "" ? null : Number(filters.minScore);
  return episodes.filter(
    (episode) =>
      (!filters.scenario || episode.scenario_id === filters.scenario) &&
      (!filters.agent || episode.agent_mode === filters.agent) &&
      (!filters.status || episode.status === filters.status) &&
      (!filters.date || (episode.created_at ?? "").slice(0, 10) === filters.date) &&
      (minimum === null || (episode.score !== null && episode.score >= minimum)),
  );
}

function Field({ label, children, id }: { label: string; id: string; children: React.ReactNode }) {
  return (
    <div className="min-w-36 flex-1">
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-faint">
        {label}
      </label>
      {children}
    </div>
  );
}

export function RunHistory() {
  const episodes = useApi(() => api.episodes(), [], 8000);
  const scenarios = useApi(api.scenarios);
  const [filters, setFilters] = useState<HistoryFilters>({ scenario: "", agent: "", status: "", date: "", minScore: "" });
  const ids = { scenario: useId(), agent: useId(), status: useId(), date: useId(), score: useId() };
  const set = (key: keyof HistoryFilters) => (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setFilters((current) => ({ ...current, [key]: event.target.value }));
  const visible = useMemo(() => filterHistory(episodes.data ?? [], filters), [episodes.data, filters]);

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        title="Run History"
        subtitle="Every simulation run is stored with its events and results. Filter the list, reopen a report, or export the data."
      />

      <form className="mb-5 flex flex-wrap items-end gap-3" onSubmit={(event) => event.preventDefault()} aria-label="Filter runs">
        <Field label="Scenario" id={ids.scenario}>
          <select id={ids.scenario} value={filters.scenario} onChange={set("scenario")} className={FIELD_CLASS}>
            <option value="">All scenarios</option>
            {scenarios.data?.map((scenario) => (
              <option key={scenario.id} value={scenario.id}>
                {scenario.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Agent type" id={ids.agent}>
          <select id={ids.agent} value={filters.agent} onChange={set("agent")} className={FIELD_CLASS}>
            <option value="">All agents</option>
            {(Object.keys(AGENT_LABELS) as AgentMode[]).map((mode) => (
              <option key={mode} value={mode}>
                {AGENT_LABELS[mode]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Status" id={ids.status}>
          <select id={ids.status} value={filters.status} onChange={set("status")} className={FIELD_CLASS}>
            <option value="">Any status</option>
            {(Object.keys(STATUS_LABELS) as EpisodeStatus[]).map((status) => (
              <option key={status} value={status}>
                {STATUS_LABELS[status]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Date" id={ids.date}>
          <input id={ids.date} type="date" value={filters.date} onChange={set("date")} className={FIELD_CLASS} />
        </Field>
        <Field label="Minimum score" id={ids.score}>
          <input
            id={ids.score}
            type="number"
            min={0}
            max={100}
            placeholder="0 to 100"
            value={filters.minScore}
            onChange={set("minScore")}
            className={FIELD_CLASS}
          />
        </Field>
      </form>

      {episodes.loading && !episodes.data && <Spinner label="Loading runs" />}
      {episodes.error && <ErrorNote message={episodes.error} onRetry={episodes.reload} />}

      {episodes.data && (
        <Card>
          {visible.length === 0 ? (
            <EmptyState
              icon={History}
              title={episodes.data.length === 0 ? "No runs yet" : "No run matches these filters"}
              text={
                episodes.data.length === 0
                  ? "Launch a simulation and it will be recorded here."
                  : "Clear a filter to see more runs."
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[56rem] border-collapse text-left text-sm">
                <caption className="sr-only">Simulation runs with their results and available actions</caption>
                <thead>
                  <tr className="border-b border-line text-xs uppercase tracking-wide text-faint">
                    <th scope="col" className="px-3 py-2.5 font-medium">Run</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Scenario</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Agent</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Status</th>
                    <th scope="col" className="px-3 py-2.5 text-right font-medium">Steps</th>
                    <th scope="col" className="px-3 py-2.5 text-right font-medium">Score</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Date</th>
                    <th scope="col" className="px-3 py-2.5 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.map((episode) => (
                    <tr key={episode.id} className="border-b border-line/60 last:border-0 hover:bg-raised/60">
                      <td className="px-3 py-2 font-mono text-xs text-ink">
                        {episode.id}
                        <span className="block text-faint">seed {episode.seed}</span>
                      </td>
                      <td className="px-3 py-2 text-ink">{episode.scenario_name}</td>
                      <td className="px-3 py-2"><AgentBadge mode={episode.agent_mode} /></td>
                      <td className="px-3 py-2"><StatusBadge status={episode.status} /></td>
                      <td className="px-3 py-2 text-right font-mono text-soft">{episode.steps}</td>
                      <td className="px-3 py-2 text-right font-mono font-semibold text-ink">{formatScore(episode.score)}</td>
                      <td className="px-3 py-2 text-xs text-faint">{formatDateTime(episode.created_at)}</td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-1.5">
                          {episode.score !== null ? (
                            <ButtonLink to={`/evaluations/${episode.id}`} size="sm" icon={FileBarChart2}>
                              View report
                            </ButtonLink>
                          ) : (
                            <ButtonLink to={`/simulation/${episode.id}`} size="sm" icon={Radio}>
                              Open live view
                            </ButtonLink>
                          )}
                          {episode.score !== null && (
                            <ButtonLink to={`/evaluations/${episode.id}`} size="sm" variant="ghost" icon={ListTree}>
                              Events and replay
                            </ButtonLink>
                          )}
                          <a className={buttonClasses("ghost", "sm")} href={api.exportUrl(episode.id, "json")} download>
                            <Download className="size-4" aria-hidden="true" />
                            JSON
                          </a>
                          <a className={buttonClasses("ghost", "sm")} href={api.exportUrl(episode.id, "csv")} download>
                            <Download className="size-4" aria-hidden="true" />
                            CSV
                          </a>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
