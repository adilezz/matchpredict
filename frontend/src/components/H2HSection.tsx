import type { Match } from "@/lib/types";

interface H2HSectionProps {
  matches: Match[];
  homeTeamId: number;
  awayTeamId: number;
}

export default function H2HSection({
  matches,
  homeTeamId,
  awayTeamId,
}: H2HSectionProps) {
  if (matches.length === 0) {
    return (
      <div className="text-center text-gray-600 text-xs py-6">
        No head-to-head history available
      </div>
    );
  }

  let homeWins = 0;
  let draws = 0;
  let awayWins = 0;
  let homeGoals = 0;
  let awayGoals = 0;

  matches.forEach((m) => {
    if (m.home_goals == null || m.away_goals == null) return;
    const isHomeTeamAtHome = m.home_team.id === homeTeamId;
    const hg = isHomeTeamAtHome ? m.home_goals : m.away_goals;
    const ag = isHomeTeamAtHome ? m.away_goals : m.home_goals;
    homeGoals += hg;
    awayGoals += ag;
    if (hg > ag) homeWins++;
    else if (hg < ag) awayWins++;
    else draws++;
  });

  const total = homeWins + draws + awayWins || 1;

  return (
    <div>
      {/* Summary bar */}
      <div className="flex items-center gap-3 mb-4">
        <div className="text-center">
          <div className="text-lg font-bold text-blue-400 font-mono">{homeWins}</div>
          <div className="text-[10px] text-gray-600">Wins</div>
        </div>
        <div className="flex-1">
          <div className="flex h-2 rounded-full overflow-hidden bg-surface-4">
            <div
              className="bg-blue-500"
              style={{ width: `${(homeWins / total) * 100}%` }}
            />
            <div
              className="bg-gray-500"
              style={{ width: `${(draws / total) * 100}%` }}
            />
            <div
              className="bg-red-500"
              style={{ width: `${(awayWins / total) * 100}%` }}
            />
          </div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-gray-400 font-mono">{draws}</div>
          <div className="text-[10px] text-gray-600">Draws</div>
        </div>
        <div className="text-center">
          <div className="text-lg font-bold text-red-400 font-mono">{awayWins}</div>
          <div className="text-[10px] text-gray-600">Wins</div>
        </div>
      </div>

      {/* Goals summary */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="text-center py-2 bg-surface-3 rounded">
          <div className="text-[10px] text-gray-600">Goals scored</div>
          <div className="text-sm font-bold text-blue-400 font-mono">{homeGoals}</div>
        </div>
        <div className="text-center py-2 bg-surface-3 rounded">
          <div className="text-[10px] text-gray-600">Matches</div>
          <div className="text-sm font-bold text-white font-mono">{matches.length}</div>
        </div>
        <div className="text-center py-2 bg-surface-3 rounded">
          <div className="text-[10px] text-gray-600">Goals scored</div>
          <div className="text-sm font-bold text-red-400 font-mono">{awayGoals}</div>
        </div>
      </div>

      {/* Match list */}
      <div className="space-y-0">
        {matches.map((m) => {
          const isHomeTeamAtHome = m.home_team.id === homeTeamId;
          return (
            <div
              key={m.id}
              className="flex items-center gap-2 py-2 border-b border-surface-3 last:border-0"
            >
              <span className="text-[10px] text-gray-600 w-20 flex-shrink-0">
                {new Date(m.match_date).toLocaleDateString("en-GB", {
                  day: "2-digit",
                  month: "short",
                  year: "2-digit",
                })}
              </span>
              <div className="flex-1 flex items-center justify-center gap-2 min-w-0">
                <span
                  className={`text-[11px] truncate text-right flex-1 ${
                    isHomeTeamAtHome ? "text-blue-400 font-semibold" : "text-gray-300"
                  }`}
                >
                  {m.home_team.name}
                </span>
                <span className="text-xs font-mono font-bold text-white px-2 py-0.5 bg-surface-4 rounded min-w-[40px] text-center">
                  {m.home_goals ?? "?"} - {m.away_goals ?? "?"}
                </span>
                <span
                  className={`text-[11px] truncate flex-1 ${
                    !isHomeTeamAtHome ? "text-red-400 font-semibold" : "text-gray-300"
                  }`}
                >
                  {m.away_team.name}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
