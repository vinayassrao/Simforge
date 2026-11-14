import clsx from "clsx";
import { useMemo, useState } from "react";

import type { SimEvent } from "@/types/api";

const MARKER_CLASS: Record<string, string> = {
  collision: "fill-bad",
  error: "fill-warn",
  milestone: "fill-good",
};

interface TimelineProps {
  events: SimEvent[];
  step: number;
  maxSteps: number;
}

/** One marker per notable event along the step axis. Select a marker to read the event. */
export function Timeline({ events, step, maxSteps }: TimelineProps) {
  const [selected, setSelected] = useState<SimEvent | null>(null);
  const notable = useMemo(() => events.filter((event) => event.category in MARKER_CLASS), [events]);
  const span = Math.max(step, 1);
  const position = (value: number) => 2 + (value / span) * 96;

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs text-faint">
        <span>Episode timeline: milestones, collisions and errors by step</span>
        <span className="font-mono">
          step {step} (limit {maxSteps})
        </span>
      </div>
      <svg viewBox="0 0 100 9" preserveAspectRatio="none" className="h-9 w-full" role="group" aria-label="Episode timeline">
        <rect x="2" y="4" width="96" height="1" rx="0.5" className="fill-line" />
        <rect x="2" y="4" width={step > 0 ? 96 : 0} height="1" rx="0.5" className="fill-accent/60" />
        {notable.map((event) => (
          <rect
            key={event.seq}
            x={position(event.step) - 0.45}
            y={selected?.seq === event.seq ? 0.5 : 1.5}
            width="0.9"
            height={selected?.seq === event.seq ? 8 : 6}
            rx="0.3"
            className={clsx("cursor-pointer", MARKER_CLASS[event.category])}
            tabIndex={0}
            role="button"
            aria-label={`Step ${event.step}: ${event.description}`}
            onClick={() => setSelected(event)}
            onFocus={() => setSelected(event)}
            onMouseEnter={() => setSelected(event)}
          />
        ))}
      </svg>
      <p className="min-h-5 text-xs text-soft" aria-live="polite">
        {selected
          ? `Step ${selected.step}: ${selected.description}`
          : notable.length > 0
            ? "Hover or focus a marker to read what happened."
            : "Markers appear as the run progresses."}
      </p>
    </div>
  );
}
