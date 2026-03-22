export interface League {
  id: number;
  name: string;
  country: string;
  code: string;
  is_active: boolean;
}

export interface Team {
  id: number;
  name: string;
  short_name: string | null;
  elo_rating: number | null;
  logo_url: string | null;
}

export interface Prediction {
  prob_home: number;
  prob_draw: number;
  prob_away: number;
  expected_total_goals: number | null;
  prob_over_05: number | null;
  prob_under_05: number | null;
  prob_over_15: number | null;
  prob_under_15: number | null;
  prob_over_25: number | null;
  prob_under_25: number | null;
  prob_over_35: number | null;
  prob_under_35: number | null;
  home_prob_over_05: number | null;
  home_prob_under_05: number | null;
  home_prob_over_15: number | null;
  home_prob_under_15: number | null;
  home_prob_over_25: number | null;
  home_prob_under_25: number | null;
  away_prob_over_05: number | null;
  away_prob_under_05: number | null;
  away_prob_over_15: number | null;
  away_prob_under_15: number | null;
  away_prob_over_25: number | null;
  away_prob_under_25: number | null;
  home_lambda: number | null;
  away_lambda: number | null;
  prob_btts_yes: number | null;
  prob_btts_no: number | null;
  prob_dc_1x: number | null;
  prob_dc_x2: number | null;
  prob_dc_12: number | null;
  correct_score_top5: string | null;
  odds_implied_home: number | null;
  odds_implied_draw: number | null;
  odds_implied_away: number | null;
  value_edge_home: number | null;
  value_edge_draw: number | null;
  value_edge_away: number | null;
  confidence: number | null;
  model_version: string;
}

export interface Match {
  id: number;
  league: League;
  home_team: Team;
  away_team: Team;
  season: string;
  matchday: number | null;
  match_date: string;
  kickoff_utc: string | null;
  status: string;
  venue: string | null;
  referee: string | null;
  home_goals: number | null;
  away_goals: number | null;
  ht_home_goals: number | null;
  ht_away_goals: number | null;
  home_xg: number | null;
  away_xg: number | null;
  home_elo: number | null;
  away_elo: number | null;
  home_shots: number | null;
  away_shots: number | null;
  home_shots_on_target: number | null;
  away_shots_on_target: number | null;
  home_possession: number | null;
  away_possession: number | null;
  home_corners: number | null;
  away_corners: number | null;
  home_fouls: number | null;
  away_fouls: number | null;
  home_yellow_cards: number | null;
  away_yellow_cards: number | null;
  home_red_cards: number | null;
  away_red_cards: number | null;
  prediction: Prediction | null;
}

export interface MatchListResponse {
  total: number;
  matches: Match[];
}

export interface DashboardStats {
  total_matches_today: number;
  upcoming_matches: number;
  leagues_active: number;
  predictions_generated: number;
}

export interface FormResponse {
  home_team: string;
  away_team: string;
  home_form: Match[];
  away_form: Match[];
}

export interface StandingsRow {
  position: number;
  team_id: number;
  team_name: string;
  logo_url: string | null;
  elo_rating: number | null;
  played: number;
  won: number;
  drawn: number;
  lost: number;
  gf: number;
  ga: number;
  gd: number;
  points: number;
  form: ("W" | "D" | "L")[];
}
