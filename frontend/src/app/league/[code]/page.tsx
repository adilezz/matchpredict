"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { League, StandingsRow, Match } from "@/lib/types";
import { getLeague, getStandings, getMatches } from "@/lib/api";
import { getCountryFlag, resultColor } from "@/lib/helpers";
import MatchRow from "@/components/MatchRow";

type Tab = "standings" | "fixtures" | "results";

export default function LeagueDetailPage() {
  const params = useParams();
  const code = String(params.code);

  const [league, setLeague] = useState<League | null>(null);
  const [standings, setStandings] = useState<StandingsRow[]>([]);
  const [fixtures, setFixtures] = useState<Match[]>([]);
  const [results, setResults] = useState<Match[]>([]);
  const [tab, setTab] = useState<Tab>("standings");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [leagueData, standingsData, fixturesData, resultsData] =
          await Promise.allSettled([
            getLeague(code),
            getStandings(code),
            getMatches({ league_code: code, status: "scheduled", limit: 30 }),
            getMatches({ league_code: code, status: "finished", limit: 30 }),
          ]);

        if (leagueData.status === "fulfilled") setLeague(leagueData.value);
        if (standingsData.status === "fulfilled") setStandings(standingsData.value);
        if (fixturesData.status === "fulfilled") setFixtures(fixturesData.value.matches);
        if (resultsData.status === "fulfilled") setResults(resultsData.value.matches);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [code]);

  if (loading) {
    return (
      <div className="max-w-[1440px] mx-auto px-4 py-6">
        <div className="skeleton h-8 w-48 mb-4 rounded" />
        <div className="skeleton h-96 rounded-lg" />
      </div>
    );
  }

  if (!league) {
    return (
      <div className="max-w-[1440px] mx-auto px-4 py-6">
        <div className="card p-8 text-center">
          <p className="text-red-400 text-sm">League not found</p>
          <Link
            href="/leagues"
            className="inline-block mt-3 px-4 py-1.5 bg-surface-3 hover:bg-surface-5 text-xs text-gray-300 rounded transition-colors"
          >
            Back to Leagues
          </Link>
        </div>
      </div>
    );
  }

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "standings", label: "Standings" },
    { id: "fixtures", label: "Fixtures", count: fixtures.length },
    { id: "results", label: "Results", count: results.length },
  ];

  return (
    <div className="max-w-[1440px] mx-auto px-4 py-4 fade-in">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
        <Link href="/leagues" className="hover:text-gray-300 transition-colors">
          Leagues
        </Link>
        <span>/</span>
        <span className="text-gray-300">{league.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <span className="text-3xl">{getCountryFlag(league.country)}</span>
        <div>
          <h1 className="text-lg font-bold text-white">{league.name}</h1>
          <p className="text-xs text-gray-500">{league.country}</p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-surface-4 mb-4">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2.5 text-xs font-medium transition-colors ${
              tab === t.id ? "tab-active" : "tab-inactive"
            }`}
          >
            {t.label}
            {t.count != null && (
              <span className="ml-1.5 text-[10px] text-gray-600">({t.count})</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === "standings" && <StandingsTable rows={standings} />}
      {tab === "fixtures" && (
        <MatchList matches={fixtures} emptyMsg="No upcoming fixtures" />
      )}
      {tab === "results" && (
        <MatchList matches={results} emptyMsg="No results yet" />
      )}
    </div>
  );
}

function StandingsTable({ rows }: { rows: StandingsRow[] }) {
  if (rows.length === 0) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-xs">No standings data available</p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-surface-4 text-gray-500 uppercase text-[10px] tracking-wider">
              <th className="py-2.5 px-3 text-left w-8">#</th>
              <th className="py-2.5 px-2 text-left">Team</th>
              <th className="py-2.5 px-2 text-center">P</th>
              <th className="py-2.5 px-2 text-center">W</th>
              <th className="py-2.5 px-2 text-center">D</th>
              <th className="py-2.5 px-2 text-center">L</th>
              <th className="py-2.5 px-2 text-center hidden sm:table-cell">GF</th>
              <th className="py-2.5 px-2 text-center hidden sm:table-cell">GA</th>
              <th className="py-2.5 px-2 text-center">GD</th>
              <th className="py-2.5 px-2 text-center font-bold">Pts</th>
              <th className="py-2.5 px-2 text-center hidden md:table-cell">Form</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const zoneClass =
                row.position <= 4
                  ? "border-l-2 border-l-blue-500"
                  : row.position >= rows.length - 2
                    ? "border-l-2 border-l-red-500"
                    : "border-l-2 border-l-transparent";
              return (
                <tr
                  key={row.team_id}
                  className={`border-b border-surface-3 hover:bg-surface-2 transition-colors ${zoneClass}`}
                >
                  <td className="py-2 px-3 text-gray-500 font-mono">{row.position}</td>
                  <td className="py-2 px-2">
                    <Link
                      href={`/team/${row.team_id}`}
                      className="text-gray-200 hover:text-accent font-medium transition-colors"
                    >
                      {row.team_name}
                    </Link>
                  </td>
                  <td className="py-2 px-2 text-center text-gray-400 font-mono">{row.played}</td>
                  <td className="py-2 px-2 text-center text-gray-400 font-mono">{row.won}</td>
                  <td className="py-2 px-2 text-center text-gray-400 font-mono">{row.drawn}</td>
                  <td className="py-2 px-2 text-center text-gray-400 font-mono">{row.lost}</td>
                  <td className="py-2 px-2 text-center text-gray-400 font-mono hidden sm:table-cell">
                    {row.gf}
                  </td>
                  <td className="py-2 px-2 text-center text-gray-400 font-mono hidden sm:table-cell">
                    {row.ga}
                  </td>
                  <td
                    className={`py-2 px-2 text-center font-mono font-semibold ${
                      row.gd > 0 ? "text-accent" : row.gd < 0 ? "text-red-400" : "text-gray-400"
                    }`}
                  >
                    {row.gd > 0 ? "+" : ""}
                    {row.gd}
                  </td>
                  <td className="py-2 px-2 text-center font-mono font-bold text-white">
                    {row.points}
                  </td>
                  <td className="py-2 px-2 hidden md:table-cell">
                    <div className="flex items-center justify-center gap-0.5">
                      {row.form.map((r, i) => (
                        <span
                          key={i}
                          className={`w-5 h-5 rounded-sm flex items-center justify-center text-[9px] font-bold ${resultColor(
                            r
                          )}`}
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="px-3 py-2 border-t border-surface-4 flex items-center gap-4 text-[10px] text-gray-600">
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 bg-blue-500 rounded-sm" /> Champions League
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2 h-2 bg-red-500 rounded-sm" /> Relegation
        </span>
      </div>
    </div>
  );
}

function MatchList({ matches, emptyMsg }: { matches: Match[]; emptyMsg: string }) {
  if (matches.length === 0) {
    return (
      <div className="card p-8 text-center">
        <p className="text-gray-500 text-xs">{emptyMsg}</p>
      </div>
    );
  }
  return (
    <div className="card overflow-hidden">
      {matches.map((m) => (
        <MatchRow key={m.id} match={m} />
      ))}
    </div>
  );
}
