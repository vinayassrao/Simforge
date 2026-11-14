import clsx from "clsx";
import { AlertTriangle, CheckCircle2, Flag, Info, type LucideIcon, Play, XCircle } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Tabs } from "@/components/ui/primitives";
import { formatTime } from "@/services/format";
import type { EventCategory, SimEvent } from "@/types/api";

export type EventFilter = "all" | "action" | "collision" | "error" | "milestone";

const FILTERS: { id: EventFilter; label: string }[] = [
  { id: "all", label: "All events" },
  { id: "action", label: "Agent actions" },
  { id: "collision", label: "Collisions" },
  { id: "error", label: "Errors" },
  { id: "milestone", label: "Task milestones" },
];

const CATEGORY_STYLE: Record<EventCategory, { icon: LucideIcon; className: string; label: string }> = {
  action: { icon: Play, className: "text-accent", label: "Action" },
  collision: { icon: AlertTriangle, className: "text-bad", label: "Collision" },
  error: { icon: XCircle, className: "text-warn", label: "Error" },
  milestone: { icon: Flag, className: "text-good", label: "Milestone" },
  info: { icon: Info, className: "text-faint", label: "Info" },
};

export function filterEvents(events: SimEvent[], filter: EventFilter): SimEvent[] {
  return filter === "all" ? events : events.filter((event) => event.category === filter);
}

function EventRow({ event }: { event: SimEvent }) {
  const style = event.type === "TASK_COMPLETED" ? { ...CATEGORY_STYLE.milestone, icon: CheckCircle2 } : CATEGORY_STYLE[event.category];
  const Icon = style.icon;
  return (
    <li className="flex gap-2.5 border-b border-line/60 px-1 py-2 last:border-0">
      <Icon className={clsx("mt-0.5 size-4 shrink-0", style.className)} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="break-words text-[0.82rem] leading-snug text-ink">
          <span className="sr-only">{style.label}: </span>
          {event.description}
        </p>
        <p className="mt-0.5 font-mono text-[0.68rem] text-faint">
          step {event.step} · {formatTime(event.timestamp)} · {event.type}
        </p>
      </div>
    </li>
  );
}

interface EventFeedProps {
  events: SimEvent[];
  /** Follow new events as they arrive. Turn off for finished episodes. */
  live?: boolean;
  heightClass?: string;
}

export function EventFeed({ events, live = false, heightClass = "h-80" }: EventFeedProps) {
  const [filter, setFilter] = useState<EventFilter>("all");
  const listRef = useRef<HTMLDivElement>(null);
  const visible = useMemo(() => filterEvents(events, filter), [events, filter]);
  const counts = useMemo(
    () => FILTERS.map((item) => ({ ...item, count: filterEvents(events, item.id).length })),
    [events],
  );

  useEffect(() => {
    const list = listRef.current;
    if (live && list) list.scrollTop = list.scrollHeight;
  }, [visible.length, live]);

  return (
    <div className="flex min-h-0 flex-col gap-3">
      <Tabs tabs={counts} active={filter} onChange={setFilter} label="Filter events" />
      <div ref={listRef} className={clsx("relative overflow-y-auto pr-1", heightClass)} tabIndex={0} aria-label="Event list">
        {visible.length === 0 ? (
          <p className="px-1 py-6 text-center text-sm text-faint">
            {events.length === 0 ? "Events appear here as soon as the simulation starts." : "No events of this kind yet."}
          </p>
        ) : (
          <ol aria-live={live ? "polite" : undefined}>
            {visible.map((event) => (
              <EventRow key={event.seq} event={event} />
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}
