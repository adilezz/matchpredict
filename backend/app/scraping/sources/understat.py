"""
Understat scraper — granular xG data via their JSON API.

Provides:
- Per-match xG with team breakdowns
- Player-level xG/xA/npxG per season
- Team-level xG timelines

Coverage: 6 leagues — EPL, La Liga, Bundesliga, Serie A, Ligue 1, RFPL.
Data from 2014-2015 onward.
API: GET https://understat.com/getLeagueData/{league}/{year}
"""

from typing import Any

import pandas as pd
from loguru import logger

from app.scraping.base import BaseScraper
from app.scraping.config import UNDERSTAT_BASE_URL, LEAGUES, LeagueMapping


class UnderstatScraper(BaseScraper):
    """Scrapes xG data from Understat's JSON API."""

    source_name = "understat"

    SUPPORTED_LEAGUES = {"EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"}

    # Understat uses different slugs for the API than for page URLs
    _API_SLUGS = {
        "EPL": "EPL",
        "LALIGA": "La_liga",
        "BUNDESLIGA": "Bundesliga",
        "SERIEA": "Serie_A",
        "LIGUE1": "Ligue_1",
    }

    @staticmethod
    def _league(code: str) -> LeagueMapping:
        m = LEAGUES.get(code)
        if not m or not m.understat_slug:
            raise ValueError(f"League {code} has no Understat mapping")
        return m

    def _api_url(self, league_code: str, season: str) -> str:
        slug = self._API_SLUGS.get(league_code, "")
        start_year = season.split("-")[0]
        return f"{UNDERSTAT_BASE_URL}/getLeagueData/{slug}/{start_year}"

    def _api_headers(self) -> dict:
        return {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
        }

    # ------------------------------------------------------------------
    # Primary scrape
    # ------------------------------------------------------------------

    async def scrape(self, league_code: str, season: str, **kwargs) -> dict[str, Any]:
        if league_code not in self.SUPPORTED_LEAGUES:
            logger.info(f"[Understat] {league_code} not supported, skipping")
            return {}

        league = self._league(league_code)
        url = self._api_url(league_code, season)
        logger.info(f"[Understat] Fetching: {league.name} {season}")

        # API expects browser-like headers (Referer helps avoid empty/blocked responses)
        start_year = season.split("-")[0]
        slug_page = league.understat_slug or self._API_SLUGS.get(league_code, "")
        referer = f"{UNDERSTAT_BASE_URL}/league/{slug_page}/{start_year}"
        hdrs = {**self._api_headers(), "Referer": referer}
        resp = await self._get(url, headers=hdrs)
        try:
            data = resp.json()
        except Exception as e:
            logger.error(f"[Understat] Invalid JSON for {league.name} {season}: {e}")
            return {}

        if not data:
            logger.warning(f"[Understat] No data for {league.name} {season}")
            return {}

        result = {}

        # Parse matches (dates)
        dates = data.get("dates", [])
        if dates:
            result["matches"] = self._parse_matches(dates, league_code, season)

        # Parse teams (aggregated xG history)
        teams_data = data.get("teams", {})
        if teams_data:
            result["teams"] = self._parse_teams(teams_data, league_code, season)

        # Parse players
        players_data = data.get("players", [])
        if players_data:
            result["players"] = self._parse_players(players_data, league_code, season)

        return result

    # ------------------------------------------------------------------
    # Parsers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_matches(dates: list[dict], league_code: str, season: str) -> pd.DataFrame:
        rows = []
        for match in dates:
            rows.append({
                "understat_id": match.get("id"),
                "date": match.get("datetime"),
                "home_team": match.get("h", {}).get("title"),
                "away_team": match.get("a", {}).get("title"),
                "home_goals": match.get("goals", {}).get("h"),
                "away_goals": match.get("goals", {}).get("a"),
                "home_xg": match.get("xG", {}).get("h"),
                "away_xg": match.get("xG", {}).get("a"),
                "is_result": match.get("isResult", False),
                "home_forecast_w": match.get("forecast", {}).get("w"),
                "home_forecast_d": match.get("forecast", {}).get("d"),
                "home_forecast_l": match.get("forecast", {}).get("l"),
            })

        df = pd.DataFrame(rows)
        df["league_code"] = league_code
        df["season"] = season
        for col in ("home_xg", "away_xg", "home_forecast_w", "home_forecast_d", "home_forecast_l"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df

    @staticmethod
    def _parse_teams(teams_data: dict, league_code: str, season: str) -> pd.DataFrame:
        rows = []
        for team_id, team_info in teams_data.items():
            hist = team_info.get("history", [])
            for entry in hist:
                rows.append({
                    "team": team_info.get("title"),
                    "date": entry.get("date"),
                    "xg": entry.get("xG"),
                    "xga": entry.get("xGA"),
                    "npxg": entry.get("npxG"),
                    "npxga": entry.get("npxGA"),
                    "scored": entry.get("scored"),
                    "conceded": entry.get("missed"),
                    "wins": entry.get("wins"),
                    "draws": entry.get("draws"),
                    "losses": entry.get("loses"),
                    "pts": entry.get("pts"),
                    "ppda_att": entry.get("ppda", {}).get("att"),
                    "ppda_def": entry.get("ppda", {}).get("def"),
                    "deep": entry.get("deep"),
                    "deep_allowed": entry.get("deep_allowed"),
                })

        df = pd.DataFrame(rows)
        df["league_code"] = league_code
        df["season"] = season
        return df

    @staticmethod
    def _parse_players(players_data: list[dict], league_code: str, season: str) -> pd.DataFrame:
        df = pd.DataFrame(players_data)
        numeric_cols = [
            "games", "time", "goals", "xG", "assists", "xA", "shots",
            "key_passes", "yellow_cards", "red_cards", "npg", "npxG",
            "xGChain", "xGBuildup",
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["league_code"] = league_code
        df["season"] = season
        return df

    # ------------------------------------------------------------------
    # Shot-level data (per match)
    # ------------------------------------------------------------------

    async def scrape_match_shots(self, match_id: str) -> pd.DataFrame:
        """Shot-by-shot xG for a single match."""
        url = f"{UNDERSTAT_BASE_URL}/match/{match_id}"
        logger.info(f"[Understat] Scraping shots for match {match_id}")

        resp = await self._get(url)
        html = resp.text

        # Match pages may still embed shot data inline
        import re, json
        pattern = r"var\s+shotsData\s*=\s*JSON\.parse\('(.+?)'\)"
        match_obj = re.search(pattern, html)
        if not match_obj:
            return pd.DataFrame()

        raw = match_obj.group(1)
        decoded = raw.encode("utf-8").decode("unicode_escape")
        data = json.loads(decoded)

        all_shots = []
        for side in ("h", "a"):
            for shot in data.get(side, []):
                all_shots.append({
                    "match_id": match_id,
                    "side": "home" if side == "h" else "away",
                    "player": shot.get("player"),
                    "minute": shot.get("minute"),
                    "xg": shot.get("xG"),
                    "result": shot.get("result"),
                    "situation": shot.get("situation"),
                    "body_part": shot.get("shotType"),
                    "x": shot.get("X"),
                    "y": shot.get("Y"),
                })

        return pd.DataFrame(all_shots)
