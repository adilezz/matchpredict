import Link from "next/link";
import type { Match } from "@/lib/types";
import { toPercent } from "@/lib/helpers";

interface MatchRowProps {
  match: Match;
}

export default function MatchRow({ match }: MatchRowProps) {
  const isFinished = match.status === "finished";
  const p = match.prediction;

  const kickoff = new Date(match.match_date);
  const timeStr = kickoff.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
  });

  const bestProb = p
    ? Math.max(p.prob_home, p.prob_draw, p.prob_away)
    : 0;
  const bestLabel = p
    ? p.prob_home === bestProb
      ? "1"
      : p.prob_away === bestProb
        ? "2"
        : "X"
    : "";

  return (
    <Link href={`/match/${match.id}`} className="match-row group">
      {/* Time / Status */}
      <div className="w-12 flex-shrink-0 text-center">
        {isFinished ? (
          <span className="text-[11px] font-medium text-gray-500">FT</span>
        ) : (
          <span className="text-[11px] font-medium text-gray-400">{timeStr}</span>
        )}
      </div>

      {/* Teams & Score */}
      <div className="flex-1 min-w-0 px-2">
        <div className="flex items-center justify-between gap-2">
          <span
            className={`text-xs truncate ${
              isFinished && match.home_goals != null && match.away_goals != null && match.home_goals > match.away_goals
                ? "text-white font-semibold"
                : "text-gray-300"
            }`}
          >
            {match.home_team.name}
          </span>
          {isFinished ? (
            <span className="text-xs font-mono font-bold text-white min-w-[16px] text-right">
              {match.home_goals}
            </span>
          ) : null}
        </div>
        <div className="flex items-center justify-between gap-2 mt-0.5">
          <span
            className={`text-xs truncate ${
              isFinished && match.home_goals != null && match.away_goals != null && match.away_goals > match.home_goals
                ? "text-white font-semibold"
                : "text-gray-300"
            }`}
          >
            {match.away_team.name}
          </span>
          {isFinished ? (
            <span className="text-xs font-mono font-bold text-white min-w-[16px] text-right">
              {match.away_goals}
            </span>
          ) : null}
        </div>
      </div>

      {/* 1X2 Probabilities */}
      {p && (
        <div className="hidden sm:flex items-center gap-1 flex-shrink-0">
          <ProbCell label="1" value={p.prob_home} highlight={bestLabel === "1"} />
          <ProbCell label="X" value={p.prob_draw} highlight={bestLabel === "X"} />
          <ProbCell label="2" value={p.prob_away} highlight={bestLabel === "2"} />
        </div>
      )}

      {/* Best prediction mobile */}
      {p && (
        <div className="sm:hidden flex-shrink-0 text-right">
          <div className="text-[10px] text-gray-500">{bestLabel}</div>
          <div className="text-xs font-mono font-bold text-accent">
            {toPercent(bestProb)}
          </div>
        </div>
      )}

      {/* Arrow */}
      <div className="w-5 flex-shrink-0 text-right text-gray-600 group-hover:text-gray-400 transition-colors">
        <svg
          className="w-3.5 h-3.5 inline"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
        </svg>
      </div>
    </Link>
  );
}

function ProbCell({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number;
  highlight: boolean;
}) {
  return (
    <div
      className={`w-12 text-center py-1 rounded text-[11px] font-mono ${
        highlight
          ? "bg-accent/15 text-accent font-bold"
          : "bg-surface-3 text-gray-400"
      }`}
    >
      <div className="text-[9px] text-gray-600 leading-none mb-0.5">{label}</div>
      <div>{(value * 100).toFixed(0)}%</div>
    </div>
  );
}
