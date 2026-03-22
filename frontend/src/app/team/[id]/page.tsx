"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { Team, Match } from "@/lib/types";
import { getTeam, getTeamMatches } from "@/lib/api";
import { getMatchResult, resultColor } from "@/lib/helpers";
import MatchRow from "@/components/MatchRow";

export default function TeamPage() {
  const params = useParams();
  const teamId = Number(params.id);

  const [team, setTeam] = useState<Team | null>(null);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [teamData, matchData] = await Promise.allSettled([
          getTeam(teamId),
          getTeamMatches(teamId, 30),
        ]);
        if (teamData.status === "fulfilled") setTeam(teamData.value);
        if (matchData.status === "fulfilled") setMatches(matchData.value);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [teamId]);

  if (loading) {
    return (
      <div className="max-w-[1440px] mx-auto px-4 py-6">
        <div className="skeleton h-8 w-48 mb-4 rounded" />
        <div className="skeleton h-64 rounded-lg" />
      </div>
    );
  }

  if (!team) {
    return (
      <div className="max-w-[1440px] mx-auto px-4 py-6">
        <div className="card p-8 text-center">
          <p className="text-red-400 text-sm">Team not found</p>
          <Link
            href="/"
            className="inline-block mt-3 px-4 py-1.5 bg-surface-3 hover:bg-surface-5 text-xs text-gray-300 rounded transition-colors"
          >
            Back to Fixtures
          </Link>
        </div>
      </div>
    );
  }

  const finished = matches.filter((m) => m.status === "finished");
  const upcoming = matches.filter((m) => m.status === "scheduled");

  const form = finished.slice(0, 10).map((m) => getMatchResult(m, teamId));
  const wins = form.filter((r) => r === "W").length;
  const draws = form.filter((r) => r === "D").length;
  const losses = form.filter((r) => r === "L").length;

  return (
    <div className="max-w-[1440px] mx-auto px-4 py-4 fade-in">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
        <Link href="/" className="hover:text-gray-300 transition-colors">
          Fixtures
        </Link>
        <span>/</span>
        <span className="text-gray-300">{team.name}</span>
      </div>

      {/* Team Header */}
      <div className="card p-6 mb-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-xl bg-surface-3 flex items-center justify-center text-2xl font-bold text-accent">
            {team.name.charAt(0)}
          </div>
          <div className="flex-1">
            <h1 className="text-xl font-bold text-white">{team.name}</h1>
            {team.elo_rating != null && (
              <p className="text-xs text-gray-500 mt-0.5">
                Elo Rating: <span className="font-mono text-gray-300">{team.elo_rating.toFixed(0)}</span>
              </p>
            )}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
          <QuickStat label="Last 10" value={`${wins}W ${draws}D ${losses}L`} />
          <QuickStat label="Total Matches" value={String(finished.length)} />
          <QuickStat label="Upcoming" value={String(upcoming.length)} />
          <QuickStat label="Elo" value={team.elo_rating?.toFixed(0) ?? "-"} />
        </div>

        {/* Form badges */}
        {form.length > 0 && (
          <div className="flex items-center gap-1 mt-4">
            <span className="text-[10px] text-gray-500 mr-2 uppercase font-bold tracking-wider">
              Form
            </span>
            {form.map((r, i) => (
              <span
                key={i}
                className={`w-6 h-6 rounded-sm flex items-center justify-center text-[10px] font-bold ${resultColor(
                  r
                )}`}
              >
                {r ?? "-"}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Matches */}
      <div className="space-y-4">
        {upcoming.length > 0 && (
          <div>
            <h2 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-2">
              Upcoming Matches
            </h2>
            <div className="card overflow-hidden">
              {upcoming.map((m) => (
                <MatchRow key={m.id} match={m} />
              ))}
            </div>
          </div>
        )}

        {finished.length > 0 && (
          <div>
            <h2 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-2">
              Recent Results
            </h2>
            <div className="card overflow-hidden">
              {finished.map((m) => (
                <MatchRow key={m.id} match={m} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function QuickStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface-3 rounded-lg p-3 text-center">
      <div className="text-[10px] text-gray-500 uppercase tracking-wider font-medium">
        {label}
      </div>
      <div className="text-sm font-mono font-bold text-white mt-0.5">{value}</div>
    </div>
  );
}
