import { MiniStat, ProgressBar } from "@/components/ui/primitives";
import { formatDuration } from "@/services/format";
import type { LiveMetrics, Performance } from "@/types/api";

export function LiveMetricsStrip({ metrics }: { metrics: LiveMetrics }) {
  return (
    <dl className="grid grid-cols-2 gap-2 sm:grid-cols-5">
      <MiniStat label="Steps" value={`${metrics.steps} / ${metrics.max_steps}`} />
      <MiniStat label="Elapsed" value={formatDuration(metrics.elapsed_seconds)} />
      <MiniStat
        label="Collisions"
        value={metrics.collisions + metrics.restricted_entries}
        tone={metrics.collisions + metrics.restricted_entries > 0 ? "bad" : "good"}
      />
      <MiniStat label="Actions sent" value={metrics.actions} />
      <MiniStat label="Progress" value={`${metrics.progress}%`} tone="accent" />
    </dl>
  );
}

function milliseconds(value: number | undefined): string {
  return value === undefined ? "-" : `${value.toFixed(2)} ms`;
}

/** Live counters plus engine timings. Values that are not measured yet show a dash. */
export function PerformancePanel({ metrics, performance }: { metrics: LiveMetrics; performance: Performance }) {
  const contacts = performance.physical_contacts;
  return (
    <div className="flex flex-col gap-4">
      <LiveMetricsStrip metrics={metrics} />
      <div>
        <div className="mb-1 flex justify-between text-xs text-faint">
          <span>Step budget used</span>
          <span className="font-mono">
            {metrics.steps} of {metrics.max_steps}
          </span>
        </div>
        <ProgressBar
          value={metrics.steps}
          max={metrics.max_steps}
          label="Step budget used"
          tone={metrics.steps / metrics.max_steps > 0.8 ? "warn" : "accent"}
        />
      </div>
      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-faint">Engine and debugging</h3>
        <dl className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <MiniStat label="Render FPS" value={performance.fps === undefined ? "-" : performance.fps.toFixed(1)} />
          <MiniStat label="Frame time" value={milliseconds(performance.frame_ms)} />
          <MiniStat label="Step duration" value={milliseconds(metrics.step_duration_ms)} />
          <MiniStat label="Action latency" value={milliseconds(metrics.action_latency_ms)} />
          <MiniStat label="Invalid actions" value={metrics.invalid_actions} tone={metrics.invalid_actions > 0 ? "warn" : undefined} />
          <MiniStat label="Restricted entries" value={metrics.restricted_entries} tone={metrics.restricted_entries > 0 ? "bad" : undefined} />
          <MiniStat
            label="Physical overlaps"
            value={contacts === undefined ? "-" : contacts.length}
            tone={contacts && contacts.length > 0 ? "bad" : undefined}
          />
          <MiniStat label="Resolution" value={performance.resolution ? performance.resolution.join(" x ") : "-"} />
        </dl>
        <p className="mt-2 text-xs text-faint">
          {performance.renderer ? `Renderer: ${performance.renderer}. ` : ""}
          "Physical overlaps" is an independent check with Panda3D's collision system that the robot model never
          overlaps an obstacle. Step duration and action latency are measured inside the simulation process.
        </p>
      </div>
    </div>
  );
}
