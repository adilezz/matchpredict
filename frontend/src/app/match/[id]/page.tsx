"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { Match, FormResponse, StandingsRow } from "@/lib/types";
import { getMatch, getMatchH2H, getMatchForm, getPrediction, getStandings } from "@/lib/api";
import { getCountryFlag, formatDate, resultColor, getMatchResult } from "@/lib/helpers";
import PredictionPanel from "@/components/PredictionPanel";
import TeamForm from "@/components/TeamForm";
import H2HSection from "@/components/H2HSection";
import ProbabilityBar from "@/components/ProbabilityBar";

type Tab = "preview" | "h2h" | "form" | "stats";

export default function MatchDetailPage() {
  const params = useParams();
  const matchId = Number(params.id);

  const [match, setMatch] = useState<Match | null>(null);
  const [h2h, setH2H] = useState<Match[]>([]);
  const [form, setForm] = useState<FormResponse | null>(null);
  const [standings, setStandings] = useState<StandingsRow[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("preview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [matchData, h2hData, formData] = await Promise.allSettled([
          getMatch(matchId),
          getMatchH2H(matchId),
          getMatchForm(matchId),
        ]);

        if (matchData.status === "fulfilled") {
          const m = matchData.value;
          setMatch(m);
          if (!m.prediction) {
            try {
              const pred = await getPrediction(matchId);
              setMatch((prev) => (prev ? { ...prev, prediction: pred } : prev));
            } catch {}
          }
          try {
            const st = await getStandings(m.league.code);
            setStandings(st);
          } catch {}
        } else {
          setError("Match not found");
        }

        if (h2hData.status === "fulfilled") setH2H(h2hData.value);
        if (formData.status === "fulfilled") setForm(formData.value);
      } catch {
        setError("Failed to load match data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [matchId]);

  if (loading) {
    return (
      <div className="max-w-[1440px] mx-auto px-4 py-6">
        <div className="card p-8">
          <div className="flex items-center justify-center gap-3">
            <div className="w-5 h-5 border-2 border-accent border-t-transparent rounded-full animate-spin" />
            <span className="text-sm text-gray-400">Loading match...</span>
          </div>
        </div>
      </div>
    );
  }

  if (error || !match) {
    return (
      <div className="max-w-[1440px] mx-auto px-4 py-6">
        <div className="card p-8 text-center">
          <p className="text-red-400 text-sm">{error || "Match not found"}</p>
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

  const isFinished = match.status === "finished";
  const kickoff = match.kickoff_utc ? new Date(match.kickoff_utc) : new Date(match.match_date);
  const hasKickoffTime = !!match.kickoff_utc;
  const p = match.prediction;

  const tabs: { id: Tab; label: string }[] = [
    { id: "preview", label: "Preview" },
    { id: "h2h", label: "H2H" },
    { id: "form", label: "Form" },
    { id: "stats", label: "Stats" },
  ];

  return (
    <div className="max-w-[1440px] mx-auto px-4 py-4 fade-in">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
        <Link href="/" className="hover:text-gray-300 transition-colors">
          Fixtures
        </Link>
        <span>/</span>
        <Link
          href={`/league/${match.league.code}`}
          className="hover:text-gray-300 transition-colors"
        >
          {match.league.name}
        </Link>
        <span>/</span>
        <span className="text-gray-300">
          {match.home_team.name} vs {match.away_team.name}
        </span>
      </div>

      <div className="flex flex-col lg:flex-row gap-4">
        {/* Main Content */}
        <div className="flex-1 min-w-0 space-y-4">
          {/* Match Header */}
          <div className="card overflow-hidden">
            {/* League bar */}
            <div className="flex items-center gap-2 px-4 py-2 bg-surface-0 border-b border-surface-4">
              <span className="text-sm">{getCountryFlag(match.league.country)}</span>
              <span className="text-xs text-gray-400 font-medium">
                {match.league.country}
              </span>
              <span className="text-gray-600">·</span>
              <Link
                href={`/league/${match.league.code}`}
                className="text-xs text-gray-300 font-semibold hover:text-accent transition-colors"
              >
                {match.league.name}
              </Link>
              {match.matchday && (
                <>
                  <span className="text-gray-600">·</span>
                  <span className="text-xs text-gray-500">
                    Matchday {match.matchday}
                  </span>
                </>
              )}
            </div>

            {/* Score / Time */}
            <div className="px-4 py-6">
              <div className="flex items-center justify-center gap-6">
                {/* Home Team */}
                <div className="flex-1 text-right">
                  <Link href={`/team/${match.home_team.id}`} className="hover:text-accent transition-colors">
                    <h2 className="text-lg font-bold text-white">
                      {match.home_team.name}
                    </h2>
                  </Link>
                  {match.home_team.elo_rating != null && (
                    <p className="text-[10px] font-mono text-gray-500 mt-0.5">
                      ELO {match.home_team.elo_rating.toFixed(0)}
                    </p>
                  )}
                </div>

                {/* Score / Kickoff */}
                <div className="flex-shrink-0 text-center min-w-[100px]">
                  {isFinished ? (
                    <div className="flex items-center justify-center gap-2">
                      <span className="text-3xl font-bold font-mono text-white">
                        {match.home_goals}
                      </span>
                      <span className="text-xl text-gray-600">-</span>
                      <span className="text-3xl font-bold font-mono text-white">
                        {match.away_goals}
                      </span>
                    </div>
                  ) : (
                    <div>
                      <div className="text-xl font-bold text-gray-300">
                        {hasKickoffTime
                          ? kickoff.toLocaleTimeString("en-GB", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "TBD"}
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {formatDate(match.match_date)}
                      </div>
                    </div>
                  )}
                  <div className="mt-1">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        isFinished
                          ? "bg-surface-4 text-gray-500"
                          : "bg-accent/15 text-accent"
                      }`}
                    >
                      {match.status}
                    </span>
                  </div>
                </div>

                {/* Away Team */}
                <div className="flex-1">
                  <Link href={`/team/${match.away_team.id}`} className="hover:text-accent transition-colors">
                    <h2 className="text-lg font-bold text-white">
                      {match.away_team.name}
                    </h2>
                  </Link>
                  {match.away_team.elo_rating != null && (
                    <p className="text-[10px] font-mono text-gray-500 mt-0.5">
                      ELO {match.away_team.elo_rating.toFixed(0)}
                    </p>
                  )}
                </div>
              </div>

              {/* xG row */}
              {isFinished && (match.home_xg != null || match.away_xg != null) && (
                <div className="flex items-center justify-center gap-6 mt-3">
                  <span className="text-xs font-mono text-gray-500">
                    xG: {match.home_xg?.toFixed(2) ?? "-"}
                  </span>
                  <span className="text-[10px] text-gray-600">Expected Goals</span>
                  <span className="text-xs font-mono text-gray-500">
                    xG: {match.away_xg?.toFixed(2) ?? "-"}
                  </span>
                </div>
              )}

              {/* Quick 1X2 bar */}
              {p && (
                <div className="max-w-sm mx-auto mt-4">
                  <ProbabilityBar
                    home={p.prob_home}
                    draw={p.prob_draw}
                    away={p.prob_away}
                    size="sm"
                  />
                </div>
              )}
            </div>

            {/* Venue & Referee */}
            {(match.venue || match.referee) && (
              <div className="px-4 py-2 border-t border-surface-4 flex items-center justify-center gap-4">
                {match.venue && (
                  <span className="text-[10px] text-gray-600">📍 {match.venue}</span>
                )}
                {match.referee && (
                  <span className="text-[10px] text-gray-600">🟨 {match.referee}</span>
                )}
              </div>
            )}
          </div>

          {/* Goal Distribution (Poisson) */}
          {p && p.home_lambda != null && p.away_lambda != null && !isFinished && (
            <GoalDistribution homeLambda={p.home_lambda} awayLambda={p.away_lambda} />
          )}

          {/* Tabs */}
          <div className="flex gap-0 border-b border-surface-4">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2.5 text-xs font-medium transition-colors ${
                  activeTab === tab.id ? "tab-active" : "tab-inactive"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="card p-4 fade-in">
            {activeTab === "preview" && (
              <PreviewTab match={match} h2h={h2h} form={form} />
            )}
            {activeTab === "h2h" && (
              <H2HSection
                matches={h2h}
                homeTeamId={match.home_team.id}
                awayTeamId={match.away_team.id}
              />
            )}
            {activeTab === "form" && form && (
              <FormTab match={match} form={form} />
            )}
            {activeTab === "stats" && <StatsTab match={match} />}
          </div>
        </div>

        {/* Right Sidebar */}
        <aside className="w-full lg:w-80 flex-shrink-0">
          <div className="sticky top-16 space-y-4">
            {p ? (
              <PredictionPanel
                prediction={p}
                homeTeam={match.home_team.short_name || match.home_team.name}
                awayTeam={match.away_team.short_name || match.away_team.name}
              />
            ) : (
              <div className="sidebar-card p-6 text-center">
                <p className="text-gray-500 text-xs">No prediction available</p>
              </div>
            )}

            {/* Mini Standings */}
            {standings.length > 0 && (
              <MiniStandings
                standings={standings}
                homeTeamId={match.home_team.id}
                awayTeamId={match.away_team.id}
                leagueCode={match.league.code}
              />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function GoalDistribution({ homeLambda, awayLambda }: { homeLambda: number; awayLambda: number }) {
  const maxGoals = 5;
  const poissonProb = (lambda: number, k: number) => {
    let result = Math.exp(-lambda) * Math.pow(lambda, k);
    for (let i = 2; i <= k; i++) result /= i;
    return result;
  };

  const bars = [];
  for (let g = 0; g <= maxGoals; g++) {
    bars.push({
      goals: g,
      home: poissonProb(homeLambda, g),
      away: poissonProb(awayLambda, g),
    });
  }

  const maxProb = Math.max(...bars.flatMap((b) => [b.home, b.away]));

  return (
    <div className="card p-4">
      <h3 className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-3">
        Goal Probability Distribution
      </h3>
      <div className="space-y-2">
        {bars.map((b) => (
          <div key={b.goals} className="flex items-center gap-2">
            <div className="w-16 flex justify-end">
              <div
                className="h-4 bg-blue-500/60 rounded-l transition-all duration-500"
                style={{ width: `${(b.home / maxProb) * 100}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-gray-400 w-8 text-center">
              {(b.home * 100).toFixed(0)}%
            </span>
            <span className="text-xs font-bold text-white w-6 text-center">{b.goals}</span>
            <span className="text-[10px] font-mono text-gray-400 w-8 text-center">
              {(b.away * 100).toFixed(0)}%
            </span>
            <div className="w-16">
              <div
                className="h-4 bg-red-500/60 rounded-r transition-all duration-500"
                style={{ width: `${(b.away / maxProb) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-between text-[9px] text-gray-600 mt-2 px-1">
        <span>Home</span>
        <span>Goals</span>
        <span>Away</span>
      </div>
    </div>
  );
}

function MiniStandings({
  standings,
  homeTeamId,
  awayTeamId,
  leagueCode,
}: {
  standings: StandingsRow[];
  homeTeamId: number;
  awayTeamId: number;
  leagueCode: string;
}) {
  return (
    <div className="sidebar-card overflow-hidden">
      <div className="px-3 py-2.5 border-b border-surface-4 flex items-center justify-between">
        <h3 className="text-[10px] font-bold uppercase tracking-widest text-gray-500">
          Standings
        </h3>
        <Link
          href={`/league/${leagueCode}`}
          className="text-[10px] text-accent hover:underline"
        >
          Full table
        </Link>
      </div>
      <table className="w-full text-[11px]">
        <thead>
          <tr className="text-gray-600 text-[9px] uppercase">
            <th className="py-1.5 px-2 text-left">#</th>
            <th className="py-1.5 px-2 text-left">Team</th>
            <th className="py-1.5 px-2 text-center">P</th>
            <th className="py-1.5 px-2 text-center">GD</th>
            <th className="py-1.5 px-2 text-center">Pts</th>
          </tr>
        </thead>
        <tbody>
          {standings.slice(0, 8).map((row) => {
            const isActive = row.team_id === homeTeamId || row.team_id === awayTeamId;
            return (
              <tr
                key={row.team_id}
                className={`border-t border-surface-3 ${
                  isActive ? "bg-accent/5" : ""
                }`}
              >
                <td className="py-1 px-2 text-gray-500 font-mono">{row.position}</td>
                <td className={`py-1 px-2 truncate max-w-[120px] ${isActive ? "text-accent font-semibold" : "text-gray-300"}`}>
                  {row.team_name}
                </td>
                <td className="py-1 px-2 text-center text-gray-400 font-mono">{row.played}</td>
                <td className={`py-1 px-2 text-center font-mono ${row.gd > 0 ? "text-accent" : row.gd < 0 ? "text-red-400" : "text-gray-400"}`}>
                  {row.gd > 0 ? "+" : ""}{row.gd}
                </td>
                <td className="py-1 px-2 text-center font-mono font-bold text-white">{row.points}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function PreviewTab({
  match,
  h2h,
  form,
}: {
  match: Match;
  h2h: Match[];
  form: FormResponse | null;
}) {
  return (
    <div className="space-y-6">
      {/* Team Comparison */}
      <div>
        <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">
          Team Comparison
        </h3>
        <div className="space-y-2">
          <ComparisonRow
            label="Elo Rating"
            homeVal={match.home_team.elo_rating?.toFixed(0) ?? "-"}
            awayVal={match.away_team.elo_rating?.toFixed(0) ?? "-"}
            homeHigher={(match.home_team.elo_rating ?? 0) > (match.away_team.elo_rating ?? 0)}
          />
        </div>
      </div>

      {/* Recent Form */}
      {form && (
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">
            Recent Form (Last 5)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <TeamForm
              teamName={match.home_team.name}
              teamId={match.home_team.id}
              matches={form.home_form.slice(0, 5)}
            />
            <TeamForm
              teamName={match.away_team.name}
              teamId={match.away_team.id}
              matches={form.away_form.slice(0, 5)}
            />
          </div>
        </div>
      )}

      {/* H2H Summary */}
      {h2h.length > 0 && (
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-3">
            Head to Head (Last {Math.min(h2h.length, 5)})
          </h3>
          <H2HSection
            matches={h2h.slice(0, 5)}
            homeTeamId={match.home_team.id}
            awayTeamId={match.away_team.id}
          />
        </div>
      )}
    </div>
  );
}

function FormTab({ match, form }: { match: Match; form: FormResponse }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <TeamForm
        teamName={match.home_team.name}
        teamId={match.home_team.id}
        matches={form.home_form}
      />
      <TeamForm
        teamName={match.away_team.name}
        teamId={match.away_team.id}
        matches={form.away_form}
      />
    </div>
  );
}

function StatsTab({ match }: { match: Match }) {
  const p = match.prediction;
  const hasAnyStats =
    match.home_xg != null ||
    match.home_shots != null ||
    match.home_possession != null ||
    match.home_corners != null ||
    match.home_fouls != null ||
    match.home_yellow_cards != null ||
    p?.home_lambda != null ||
    match.home_elo != null;

  return (
    <div className="space-y-4">
      <h3 className="text-xs font-bold uppercase tracking-widest text-gray-500">
        Match Statistics
      </h3>

      {match.home_xg != null && match.away_xg != null && (
        <StatBar label="Expected Goals (xG)" homeVal={match.home_xg} awayVal={match.away_xg!} />
      )}

      {match.home_possession != null && match.away_possession != null && (
        <StatBar label="Possession %" homeVal={match.home_possession} awayVal={match.away_possession!} max={100} />
      )}

      {match.home_shots != null && match.away_shots != null && (
        <StatBar label="Total Shots" homeVal={match.home_shots} awayVal={match.away_shots!} integer />
      )}

      {match.home_shots_on_target != null && match.away_shots_on_target != null && (
        <StatBar label="Shots on Target" homeVal={match.home_shots_on_target} awayVal={match.away_shots_on_target!} integer />
      )}

      {match.home_corners != null && match.away_corners != null && (
        <StatBar label="Corners" homeVal={match.home_corners} awayVal={match.away_corners!} integer />
      )}

      {match.home_fouls != null && match.away_fouls != null && (
        <StatBar label="Fouls" homeVal={match.home_fouls} awayVal={match.away_fouls!} integer />
      )}

      {match.home_yellow_cards != null && match.away_yellow_cards != null && (
        <StatBar label="Yellow Cards" homeVal={match.home_yellow_cards} awayVal={match.away_yellow_cards!} integer />
      )}

      {match.home_red_cards != null && match.away_red_cards != null && (
        <StatBar label="Red Cards" homeVal={match.home_red_cards} awayVal={match.away_red_cards!} integer />
      )}

      {p?.home_lambda != null && p?.away_lambda != null && (
        <StatBar label="Predicted Goals (λ)" homeVal={p.home_lambda} awayVal={p.away_lambda} />
      )}

      {match.home_elo != null && match.away_elo != null && (
        <StatBar label="Elo Rating" homeVal={match.home_elo} awayVal={match.away_elo!} max={2200} />
      )}

      {(match.venue || match.referee) && (
        <div className="text-center py-2 space-y-1">
          {match.venue && (
            <span className="text-[10px] text-gray-600 block">Venue: {match.venue}</span>
          )}
          {match.referee && (
            <span className="text-[10px] text-gray-600 block">Referee: {match.referee}</span>
          )}
        </div>
      )}

      {!hasAnyStats && (
        <p className="text-gray-600 text-xs text-center py-4">
          No detailed statistics available for this match
        </p>
      )}
    </div>
  );
}

function ComparisonRow({
  label,
  homeVal,
  awayVal,
  homeHigher,
}: {
  label: string;
  homeVal: string;
  awayVal: string;
  homeHigher: boolean;
}) {
  return (
    <div className="flex items-center gap-2 py-2 px-3 bg-surface-3 rounded">
      <span
        className={`flex-1 text-right text-xs font-mono ${
          homeHigher ? "text-accent font-bold" : "text-gray-400"
        }`}
      >
        {homeVal}
      </span>
      <span className="text-[10px] text-gray-600 font-medium min-w-[80px] text-center">
        {label}
      </span>
      <span
        className={`flex-1 text-xs font-mono ${
          !homeHigher ? "text-accent font-bold" : "text-gray-400"
        }`}
      >
        {awayVal}
      </span>
    </div>
  );
}

function StatBar({
  label,
  homeVal,
  awayVal,
  max,
  integer,
}: {
  label: string;
  homeVal: number;
  awayVal: number;
  max?: number;
  integer?: boolean;
}) {
  const maxVal = max || Math.max(homeVal, awayVal) * 1.2 || 1;
  const homeW = (homeVal / maxVal) * 100;
  const awayW = (awayVal / maxVal) * 100;
  const fmt = (v: number) => (integer ? v.toString() : v.toFixed(2));

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px] text-gray-600">
        <span>{fmt(homeVal)}</span>
        <span className="font-medium">{label}</span>
        <span>{fmt(awayVal)}</span>
      </div>
      <div className="flex gap-1">
        <div className="flex-1 h-2 bg-surface-4 rounded-full overflow-hidden flex justify-end">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-500"
            style={{ width: `${homeW}%` }}
          />
        </div>
        <div className="flex-1 h-2 bg-surface-4 rounded-full overflow-hidden">
          <div
            className="h-full bg-red-500 rounded-full transition-all duration-500"
            style={{ width: `${awayW}%` }}
          />
        </div>
      </div>
    </div>
  );
}
