import clsx from "clsx";

import { ProgressBar } from "@/components/ui/primitives";
import { formatScore } from "@/services/format";
import type { BreakdownItem } from "@/types/api";

export function ScoreRing({ score, success }: { score: number; success: boolean }) {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const filled = (Math.max(0, Math.min(100, score)) / 100) * circumference;
  return (
    <div className="relative size-36 shrink-0">
      <svg viewBox="0 0 120 120" className="size-full -rotate-90" role="img" aria-label={`Score ${formatScore(score)} out of 100`}>
        <circle cx="60" cy="60" r={radius} fill="none" strokeWidth="10" className="stroke-raised" />
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
          className={success ? "stroke-good" : "stroke-warn"}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-semibold tracking-tight text-ink">{formatScore(score)}</span>
        <span className="text-xs text-faint">out of 100</span>
      </div>
    </div>
  );
}

export function ScoreBreakdown({ breakdown }: { breakdown: BreakdownItem[] }) {
  return (
    <ul className="flex flex-col gap-3.5">
      {breakdown.map((item) => {
        const full = item.points >= item.max_points;
        return (
          <li key={item.key}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-sm font-medium text-ink">{item.label}</span>
              <span className={clsx("font-mono text-sm", full ? "text-good" : item.points === 0 ? "text-bad" : "text-warn")}>
                {item.points.toFixed(1)} / {item.max_points}
              </span>
            </div>
            <ProgressBar
              value={item.points}
              max={item.max_points}
              label={`${item.label}: ${item.points} of ${item.max_points} points`}
              tone={full ? "good" : item.points === 0 ? "bad" : "warn"}
            />
            <p className="mt-1 text-xs text-soft">{item.explanation}</p>
            <p className="text-xs text-faint">Rule: {item.rule}</p>
          </li>
        );
      })}
    </ul>
  );
}
