import type {
  League,
  Match,
  MatchListResponse,
  DashboardStats,
  Prediction,
  FormResponse,
  StandingsRow,
  Team,
} from "./types";

const API_BASE = "/api/v1";

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export async function getLeagues(): Promise<League[]> {
  return fetchJSON<League[]>("/leagues/");
}

export async function getLeague(code: string): Promise<League> {
  return fetchJSON<League>(`/leagues/${code}`);
}

export async function getMatches(params: {
  league_code?: string;
  status?: string;
  season?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}): Promise<MatchListResponse> {
  const sp = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  });
  return fetchJSON<MatchListResponse>(`/matches/?${sp.toString()}`);
}

export async function getUpcomingMatches(days = 7): Promise<Match[]> {
  return fetchJSON<Match[]>(`/matches/upcoming?days=${days}`);
}

export async function getMatch(id: number): Promise<Match> {
  return fetchJSON<Match>(`/matches/${id}`);
}

export async function getMatchH2H(id: number): Promise<Match[]> {
  return fetchJSON<Match[]>(`/matches/${id}/h2h`);
}

export async function getMatchForm(id: number): Promise<FormResponse> {
  return fetchJSON<FormResponse>(`/matches/${id}/form`);
}

export async function getPrediction(matchId: number): Promise<Prediction> {
  return fetchJSON<Prediction>(`/predictions/${matchId}`);
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return fetchJSON<DashboardStats>("/predictions/stats");
}

export async function getStandings(leagueCode: string, season?: string): Promise<StandingsRow[]> {
  const params = season ? `?season=${season}` : "";
  return fetchJSON<StandingsRow[]>(`/standings/${leagueCode}${params}`);
}

export async function getTeam(teamId: number): Promise<Team> {
  return fetchJSON<Team>(`/teams/${teamId}`);
}

export async function getTeamMatches(teamId: number, limit = 20, status?: string): Promise<Match[]> {
  const sp = new URLSearchParams({ limit: String(limit) });
  if (status) sp.set("status", status);
  return fetchJSON<Match[]>(`/teams/${teamId}/matches?${sp.toString()}`);
}
