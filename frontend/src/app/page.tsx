"use client";

import { useState, useEffect, useCallback } from "react";
import type { League, Match, DashboardStats } from "@/lib/types";
import { getLeagues, getMatches, getUpcomingMatches, getDashboardStats } from "@/lib/api";
import { toDateString, groupMatchesByLeague, getCountryFlag } from "@/lib/helpers";
import LeagueSidebar from "@/components/LeagueSidebar";
import DateNav from "@/components/DateNav";
import MatchRow from "@/components/MatchRow";
import TopPredictions from "@/components/TopPredictions";
import StatsCard from "@/components/StatsCard";
import MatchListSkeleton from "@/components/MatchListSkeleton";

export default function FixturesPage() {
  const [leagues, setLeagues] = useState<League[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [upcomingMatches, setUpcomingMatches] = useState<Match[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [selectedLeague, setSelectedLeague] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadInitial() {
      try {
        const [leagueData, upcoming, dashStats] = await Promise.allSettled([
          getLeagues(),
          getUpcomingMatches(14),
          getDashboardStats(),
        ]);
        if (leagueData.status === "fulfilled") setLeagues(leagueData.value);
        if (upcoming.status === "fulfilled") setUpcomingMatches(upcoming.value);
        if (dashStats.status === "fulfilled") setStats(dashStats.value);
      } catch {
        // non-critical
      }
    }
    loadInitial();
  }, []);

  const loadMatches = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const dateStr = toDateString(selectedDate);
      const data = await getMatches({
        league_code: selectedLeague || undefined,
        date_from: dateStr,
        date_to: dateStr,
        limit: 100,
      });
      setMatches(data.matches);
    } catch (err) {
      setError("Could not load matches. Make sure the API is running.");
      setMatches([]);
    } finally {
      setLoading(false);
    }
  }, [selectedDate, selectedLeague]);

  useEffect(() => {
    loadMatches();
  }, [loadMatches]);

  const grouped = groupMatchesByLeague(matches);
  const leagueMap = Object.fromEntries(leagues.map((l) => [l.code, l]));

  return (
    <div className="max-w-[1440px] mx-auto px-4 py-4">
      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <StatsCard title="Today" value={stats.total_matches_today} subtitle="Matches" />
          <StatsCard title="Upcoming" value={stats.upcoming_matches} subtitle="Next 7 days" />
          <StatsCard title="Leagues" value={stats.leagues_active} subtitle="Active" />
          <StatsCard title="Predictions" value={stats.predictions_generated} subtitle="Generated" />
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-4">
        {/* Left Sidebar - Leagues */}
        <aside className="w-full lg:w-52 flex-shrink-0">
          <div className="sticky top-16">
            <LeagueSidebar
              leagues={leagues}
              selected={selectedLeague}
              onSelect={setSelectedLeague}
            />
          </div>
        </aside>

        {/* Center - Match List */}
        <div className="flex-1 min-w-0 space-y-3">
          {/* Date Navigator */}
          <DateNav selectedDate={selectedDate} onSelect={setSelectedDate} />

          {/* Loading */}
          {loading && <MatchListSkeleton />}

          {/* Error */}
          {error && (
            <div className="card p-6 text-center">
              <p className="text-red-400 text-sm">{error}</p>
              <button
                onClick={loadMatches}
                className="mt-3 px-4 py-1.5 bg-surface-3 hover:bg-surface-5 text-xs text-gray-300 rounded transition-colors"
              >
                Retry
              </button>
            </div>
          )}

          {/* Match List grouped by League */}
          {!loading && !error && Object.keys(grouped).length > 0 && (
            <div className="card overflow-hidden fade-in">
              {Object.entries(grouped).map(([leagueCode, leagueMatches]) => {
                const league = leagueMap[leagueCode] || leagueMatches[0]?.league;
                return (
                  <div key={leagueCode}>
                    <div className="league-header">
                      <span className="text-sm">
                        {league ? getCountryFlag(league.country) : "⚽"}
                      </span>
                      <span>{league?.name || leagueCode}</span>
                      {league && (
                        <span className="text-gray-600 font-normal">{league.country}</span>
                      )}
                    </div>
                    {leagueMatches.map((match) => (
                      <MatchRow key={match.id} match={match} />
                    ))}
                  </div>
                );
              })}
            </div>
          )}

          {/* Empty */}
          {!loading && !error && Object.keys(grouped).length === 0 && (
            <div className="card p-10 text-center">
              <div className="text-3xl mb-3">⚽</div>
              <p className="text-gray-400 text-sm font-medium">
                No matches found for this date
              </p>
              <p className="text-gray-600 text-xs mt-1">
                Try selecting a different date or league
              </p>
            </div>
          )}
        </div>

        {/* Right Sidebar - Top Predictions */}
        <aside className="w-full lg:w-64 flex-shrink-0">
          <div className="sticky top-16">
            <TopPredictions matches={upcomingMatches} />
          </div>
        </aside>
      </div>
    </div>
  );
}
