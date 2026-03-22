import type { Match } from "@/lib/types";
import { getMatchResult, resultColor } from "@/lib/helpers";

interface TeamFormProps {
  teamName: string;
  teamId: number;
  matches: Match[];
}

export default function TeamForm({ teamName, teamId, matches }: TeamFormProps) {
  if (matches.length === 0) {
    return (
      <div className="text-center text-gray-600 text-xs py-4">
        No recent form data
      </div>
    );
  }

  return (
    <div>
      <h4 className="text-xs font-semibold text-gray-300 mb-3">{teamName}</h4>

      {/* Form badges */}
      <div className="flex gap-1 mb-3">
        {matches.slice(0, 5).map((m) => {
          const result = getMatchResult(m, teamId);
          return (
            <span
              key={m.id}
              className={`w-6 h-6 rounded flex items-center justify-center text-[10px] font-bold ${resultColor(result)}`}
            >
              {result || "?"}
            </span>
          );
        })}
      </div>

      {/* Match list */}
      <div className="space-y-0">
        {matches.map((m) => {
          const result = getMatchResult(m, teamId);
          const isHome = m.home_team.id === teamId;
          return (
            <div
              key={m.id}
              className="flex items-center gap-2 py-1.5 border-b border-surface-3 last:border-0"
            >
              <span
                className={`w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold flex-shrink-0 ${resultColor(result)}`}
              >
                {result || "?"}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[11px] text-gray-300 truncate">
                  {isHome ? (
                    <>
                      <span className="font-semibold">{m.home_team.name}</span>
                      <span className="text-gray-600"> vs </span>
                      <span>{m.away_team.name}</span>
                    </>
                  ) : (
                    <>
                      <span>{m.home_team.name}</span>
                      <span className="text-gray-600"> vs </span>
                      <span className="font-semibold">{m.away_team.name}</span>
                    </>
                  )}
                </div>
              </div>
              <span className="text-[11px] font-mono font-bold text-gray-400 flex-shrink-0">
                {m.home_goals ?? "?"} - {m.away_goals ?? "?"}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
