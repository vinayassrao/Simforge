import { Search, SearchX } from "lucide-react";
import { useId, useMemo, useState } from "react";

import { ScenarioCard } from "@/components/ScenarioCard";
import { EmptyState, ErrorNote, PageHeader, Spinner } from "@/components/ui/primitives";
import { useApi } from "@/hooks/useApi";
import { api } from "@/services/api";
import type { Scenario } from "@/types/api";

type SortKey = "difficulty" | "name" | "duration";
const DIFFICULTY_ORDER = ["Beginner", "Intermediate", "Advanced"];
const SORTERS: Record<SortKey, (a: Scenario, b: Scenario) => number> = {
  difficulty: (a, b) => DIFFICULTY_ORDER.indexOf(a.difficulty) - DIFFICULTY_ORDER.indexOf(b.difficulty),
  name: (a, b) => a.name.localeCompare(b.name),
  duration: (a, b) => a.estimated_minutes - b.estimated_minutes,
};
const SELECT_CLASS = "h-9 rounded-lg border border-line bg-raised px-2.5 text-sm text-ink";

export function filterScenarios(scenarios: Scenario[], search: string, difficulty: string, taskType: string, sort: SortKey) {
  const needle = search.trim().toLowerCase();
  return scenarios
    .filter(
      (scenario) =>
        (!needle || `${scenario.name} ${scenario.summary} ${scenario.description}`.toLowerCase().includes(needle)) &&
        (!difficulty || scenario.difficulty === difficulty) &&
        (!taskType || scenario.task_type === taskType),
    )
    .sort(SORTERS[sort]);
}

export function ScenarioLibrary() {
  const { data, error, loading, reload } = useApi(api.scenarios);
  const [search, setSearch] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [taskType, setTaskType] = useState("");
  const [sort, setSort] = useState<SortKey>("difficulty");
  const searchId = useId();
  const difficultyId = useId();
  const typeId = useId();
  const sortId = useId();

  const taskTypes = useMemo(() => [...new Set(data?.map((scenario) => scenario.task_type) ?? [])], [data]);
  const visible = useMemo(
    () => filterScenarios(data ?? [], search, difficulty, taskType, sort),
    [data, search, difficulty, taskType, sort],
  );

  return (
    <div className="mx-auto max-w-7xl">
      <PageHeader
        title="Scenario Library"
        subtitle="Each scenario is a 3D warehouse with a delivery task. Open one to read the task, then launch it with the agent of your choice."
      />

      <form role="search" className="mb-5 flex flex-wrap items-end gap-3" onSubmit={(event) => event.preventDefault()}>
        <div className="min-w-56 flex-1">
          <label htmlFor={searchId} className="mb-1 block text-xs font-medium text-faint">
            Search
          </label>
          <div className="relative">
            <Search className="pointer-events-none absolute left-2.5 top-2.5 size-4 text-faint" aria-hidden="true" />
            <input
              id={searchId}
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search scenarios"
              className="h-9 w-full rounded-lg border border-line bg-raised pl-8 pr-3 text-sm text-ink placeholder:text-faint"
            />
          </div>
        </div>
        <div>
          <label htmlFor={difficultyId} className="mb-1 block text-xs font-medium text-faint">
            Difficulty
          </label>
          <select id={difficultyId} value={difficulty} onChange={(event) => setDifficulty(event.target.value)} className={SELECT_CLASS}>
            <option value="">All levels</option>
            {DIFFICULTY_ORDER.map((level) => (
              <option key={level}>{level}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={typeId} className="mb-1 block text-xs font-medium text-faint">
            Task type
          </label>
          <select id={typeId} value={taskType} onChange={(event) => setTaskType(event.target.value)} className={SELECT_CLASS}>
            <option value="">All types</option>
            {taskTypes.map((type) => (
              <option key={type}>{type}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor={sortId} className="mb-1 block text-xs font-medium text-faint">
            Sort by
          </label>
          <select id={sortId} value={sort} onChange={(event) => setSort(event.target.value as SortKey)} className={SELECT_CLASS}>
            <option value="difficulty">Difficulty</option>
            <option value="name">Name</option>
            <option value="duration">Estimated time</option>
          </select>
        </div>
      </form>

      {loading && <Spinner label="Loading scenarios" />}
      {error && <ErrorNote message={error} onRetry={reload} />}
      {data && visible.length === 0 && (
        <EmptyState icon={SearchX} title="No scenario matches" text="Try a different search term or clear the filters." />
      )}
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {visible.map((scenario) => (
          <ScenarioCard key={scenario.id} scenario={scenario} showAgents />
        ))}
      </div>
    </div>
  );
}
