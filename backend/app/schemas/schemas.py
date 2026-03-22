from datetime import date, datetime
from pydantic import BaseModel


class LeagueOut(BaseModel):
    id: int
    name: str
    country: str
    code: str
    is_active: bool = True

    class Config:
        from_attributes = True


class TeamOut(BaseModel):
    id: int
    name: str
    short_name: str | None = None
    elo_rating: float | None = None
    logo_url: str | None = None

    class Config:
        from_attributes = True


class PredictionOut(BaseModel):
    prob_home: float
    prob_draw: float
    prob_away: float
    expected_total_goals: float | None = None

    prob_over_05: float | None = None
    prob_under_05: float | None = None
    prob_over_15: float | None = None
    prob_under_15: float | None = None
    prob_over_25: float | None = None
    prob_under_25: float | None = None
    prob_over_35: float | None = None
    prob_under_35: float | None = None

    home_prob_over_05: float | None = None
    home_prob_under_05: float | None = None
    home_prob_over_15: float | None = None
    home_prob_under_15: float | None = None
    home_prob_over_25: float | None = None
    home_prob_under_25: float | None = None

    away_prob_over_05: float | None = None
    away_prob_under_05: float | None = None
    away_prob_over_15: float | None = None
    away_prob_under_15: float | None = None
    away_prob_over_25: float | None = None
    away_prob_under_25: float | None = None

    home_lambda: float | None = None
    away_lambda: float | None = None

    prob_btts_yes: float | None = None
    prob_btts_no: float | None = None
    prob_dc_1x: float | None = None
    prob_dc_x2: float | None = None
    prob_dc_12: float | None = None
    correct_score_top5: str | None = None

    odds_implied_home: float | None = None
    odds_implied_draw: float | None = None
    odds_implied_away: float | None = None
    value_edge_home: float | None = None
    value_edge_draw: float | None = None
    value_edge_away: float | None = None

    confidence: float | None = None
    model_version: str = "v1"

    class Config:
        from_attributes = True


class MatchOut(BaseModel):
    id: int
    league: LeagueOut
    home_team: TeamOut
    away_team: TeamOut
    season: str
    matchday: int | None = None
    match_date: date
    kickoff_utc: datetime | None = None
    status: str
    venue: str | None = None
    referee: str | None = None
    home_goals: int | None = None
    away_goals: int | None = None
    ht_home_goals: int | None = None
    ht_away_goals: int | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    home_elo: float | None = None
    away_elo: float | None = None
    home_shots: int | None = None
    away_shots: int | None = None
    home_shots_on_target: int | None = None
    away_shots_on_target: int | None = None
    home_possession: float | None = None
    away_possession: float | None = None
    home_corners: int | None = None
    away_corners: int | None = None
    home_fouls: int | None = None
    away_fouls: int | None = None
    home_yellow_cards: int | None = None
    away_yellow_cards: int | None = None
    home_red_cards: int | None = None
    away_red_cards: int | None = None
    prediction: PredictionOut | None = None

    class Config:
        from_attributes = True


class MatchListOut(BaseModel):
    total: int
    matches: list[MatchOut]


class DashboardStats(BaseModel):
    total_matches_today: int
    upcoming_matches: int
    leagues_active: int
    predictions_generated: int
