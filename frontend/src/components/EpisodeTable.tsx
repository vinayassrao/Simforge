import { FileBarChart2, Radio } from "lucide-react";
import { Link } from "react-router-dom";

import { AgentBadge, StatusBadge } from "@/components/StatusBadge";
import { formatDateTime, formatScore } from "@/services/format";
import type { Episode } from "@/types/api";

interface EpisodeTableProps {
  episodes: Episode[];
  selectedIds?: string[];
  onToggleSelect?: (id: string) => void;
  caption: string;
}

export function episodeLink(episode: Episode): string {
  return episode.score !== null ? `/evaluations/${episode.id}` : `/simulation/${episode.id}`;
}

export function EpisodeTable({ episodes, selectedIds, onToggleSelect, caption }: EpisodeTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[42rem] border-collapse text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b border-line text-xs uppercase tracking-wide text-faint">
            {onToggleSelect && <th scope="col" className="w-10 px-2 py-2 font-medium">Compare</th>}
            <th scope="col" className="px-2 py-2 font-medium">Run</th>
            <th scope="col" className="px-2 py-2 font-medium">Scenario</th>
            <th scope="col" className="px-2 py-2 font-medium">Agent</th>
            <th scope="col" className="px-2 py-2 font-medium">Status</th>
            <th scope="col" className="px-2 py-2 text-right font-medium">Steps</th>
            <th scope="col" className="px-2 py-2 text-right font-medium">Collisions</th>
            <th scope="col" className="px-2 py-2 text-right font-medium">Score</th>
            <th scope="col" className="px-2 py-2 font-medium">Started</th>
          </tr>
        </thead>
        <tbody>
          {episodes.map((episode) => (
            <tr key={episode.id} className="border-b border-line/60 last:border-0 hover:bg-raised/60">
              {onToggleSelect && (
                <td className="px-2 py-2">
                  <input
                    type="checkbox"
                    className="size-4 accent-[var(--sf-accent)]"
                    checked={selectedIds?.includes(episode.id) ?? false}
                    onChange={() => onToggleSelect(episode.id)}
                    aria-label={`Select run ${episode.id} for comparison`}
                  />
                </td>
              )}
              <td className="px-2 py-2">
                <Link to={episodeLink(episode)} className="inline-flex items-center gap-1.5 font-mono text-xs text-accent hover:underline">
                  {episode.score !== null ? (
                    <FileBarChart2 className="size-3.5" aria-hidden="true" />
                  ) : (
                    <Radio className="size-3.5" aria-hidden="true" />
                  )}
                  {episode.id}
                </Link>
              </td>
              <td className="px-2 py-2 text-ink">{episode.scenario_name}</td>
              <td className="px-2 py-2">
                <AgentBadge mode={episode.agent_mode} />
              </td>
              <td className="px-2 py-2">
                <StatusBadge status={episode.status} />
              </td>
              <td className="px-2 py-2 text-right font-mono text-soft">{episode.steps}</td>
              <td className="px-2 py-2 text-right font-mono text-soft">{episode.collisions}</td>
              <td className="px-2 py-2 text-right font-mono font-semibold text-ink">{formatScore(episode.score)}</td>
              <td className="px-2 py-2 text-xs text-faint">{formatDateTime(episode.started_at ?? episode.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
