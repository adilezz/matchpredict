import Link from "next/link";
import type { Match } from "@/lib/types";
import { getTopPrediction, getCountryFlag, toPercent } from "@/lib/helpers";

interface TopPredictionsProps {
  matches: Match[];
}

export default function TopPredictions({ matches }: TopPredictionsProps) {
  const withPredictions = matches
    .filter((m) => m.prediction && m.status === "scheduled")
    .map((m) => ({
      match: m,
      top: getTopPrediction(m)!,
    }))
    .sort((a, b) => b.top.prob - a.top.prob)
    .slice(0, 12);

  if (withPredictions.length === 0) {
    return (
      <div className="sidebar-card p-4">
        <h3 className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-3">
          Top Predictions
        </h3>
        <p className="text-xs text-gray-600 text-center py-4">
          No predictions available
        </p>
      </div>
    );
  }

  return (
    <div className="sidebar-card overflow-hidden">
      <div className="px-3 py-2.5 border-b border-surface-4">
        <h3 className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
          Top Predictions
        </h3>
        <p className="text-[10px] text-gray-600 mt-0.5">Sorted by probability</p>
      </div>
      <div className="max-h-[calc(100vh-16rem)] overflow-y-auto">
        {withPredictions.map(({ match, top }) => (
          <Link
            key={match.id}
            href={`/match/${match.id}`}
            className="flex items-center gap-2 px-3 py-2 border-b border-surface-3 hover:bg-surface-2 transition-colors"
          >
            <span className="text-xs flex-shrink-0">
              {getCountryFlag(match.league.country)}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-[11px] text-gray-300 truncate">
                {match.home_team.short_name || match.home_team.name} vs{" "}
                {match.away_team.short_name || match.away_team.name}
              </div>
              <div className="text-[10px] text-gray-600">{match.league.name}</div>
            </div>
            <div className="flex-shrink-0 text-right">
              <div className="text-[10px] text-gray-500">{top.label}</div>
              <div className="text-xs font-mono font-bold text-accent">
                {toPercent(top.prob)}
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
