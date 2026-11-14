import clsx from "clsx";
import { CheckCircle2, Circle, CircleDot } from "lucide-react";

import { ProgressBar, SectionCard } from "@/components/ui/primitives";
import type { Observation } from "@/types/api";

export function TaskPanel({ task }: { task: Observation["task"] }) {
  return (
    <SectionCard title="Your objective" hint="The task, in plain English, and how far along it is.">
      <p className="text-sm text-ink">{task.instructions}</p>
      <div className="mt-3">
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="text-faint">Task progress</span>
          <span className="font-mono font-semibold text-accent">{task.progress}%</span>
        </div>
        <ProgressBar value={task.progress} label={`Task progress: ${task.progress}%`} />
      </div>
      <ol className="mt-4 flex flex-col gap-2">
        {task.checklist.map((item) => {
          const Icon = item.done ? CheckCircle2 : item.current ? CircleDot : Circle;
          return (
            <li
              key={item.id}
              aria-current={item.current ? "step" : undefined}
              className={clsx(
                "flex items-center gap-2 rounded-lg border px-2.5 py-1.5 text-sm",
                item.current ? "border-accent/40 bg-accent/10 text-ink" : "border-transparent",
                item.done && "text-soft",
                !item.done && !item.current && "text-faint",
              )}
            >
              <Icon
                className={clsx("size-4 shrink-0", item.done ? "text-good" : item.current ? "text-accent" : "text-faint")}
                aria-hidden="true"
              />
              <span className={clsx(item.done && "line-through decoration-faint")}>{item.label}</span>
              <span className="sr-only">{item.done ? "(done)" : item.current ? "(current step)" : "(to do)"}</span>
            </li>
          );
        })}
      </ol>
    </SectionCard>
  );
}
