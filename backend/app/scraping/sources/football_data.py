"""
Football-Data.co.uk scraper — historical results with bookmaker odds.

This is the single best FREE source for historical odds data. Provides:
- Match results (FT & HT scores)
- Match stats (shots, corners, fouls, cards)
- Odds from 10+ bookmakers: Bet365, Pinnacle, Betfair, William Hill, etc.
- Both 1X2 and Over/Under markets

Coverage: all 10 European domestic leagues (CSV downloads back to ~2000).
NOT available: UCL, UEL, Botola Pro, international tournaments.

Data format: clean CSV files, one per league per season.
Website: https://www.football-data.co.uk/data.php
"""

import re
from io import StringIO
from typing import Any

import pandas as pd
from loguru import logger

from app.scraping.base import BaseScraper
from app.scraping.config import FOOTBALL_DATA_BASE_URL, LEAGUES, LeagueMapping


# Football-Data uses 2-digit year codes: 2024-2025 -> "2425"
def _season_to_fd_code(season: str) -> str:
    parts = season.split("-")
    return parts[0][-2:] + parts[1][-2:]


class FootballDataScraper(BaseScraper):
    """Downloads and parses CSV match data from Football-Data.co.uk."""

    source_name = "football_data"

    @staticmethod
    def _league(code: str) -> LeagueMapping:
        m = LEAGUES.get(code)
        if not m or not m.fd_division:
            raise ValueError(f"League {code} has no Football-Data mapping")
        return m

    def _csv_url(self, league: LeagueMapping, season: str) -> str:
        code = _season_to_fd_code(season)
        # URL pattern: mmz4281/{season_code}/{division}.csv
        return f"{FOOTBALL_DATA_BASE_URL}/mmz4281/{code}/{league.fd_division}.csv"

    async def scrape(self, league_code: str, season: str, **kwargs) -> pd.DataFrame:
        """Download and parse a single season CSV."""
        league = self._league(league_code)
        url = self._csv_url(league, season)
        logger.info(f"[Football-Data] Downloading: {league.name} {season} → {url}")

        resp = await self._get(url)
        df = pd.read_csv(StringIO(resp.text), on_bad_lines="skip")

        if df.empty:
            logger.warning(f"[Football-Data] Empty CSV for {league.name} {season}")
            return df

        return self._clean(df, league_code, season)

    async def scrape_all_seasons(
        self, league_code: str, start_year: int = 2018, end_year: int = 2026
    ) -> pd.DataFrame:
        """Download multiple seasons and concatenate."""
        frames = []
        for year in range(start_year, end_year):
            season = f"{year}-{year + 1}"
            try:
                df = await self.scrape(league_code, season)
                frames.append(df)
            except Exception as e:
                logger.warning(f"[Football-Data] Failed {league_code} {season}: {e}")
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    # ------------------------------------------------------------------
    # Column standardization
    # ------------------------------------------------------------------

    @staticmethod
    def _clean(df: pd.DataFrame, league_code: str, season: str) -> pd.DataFrame:
        rename_map = {
            "Div": "division",
            "Date": "date",
            "HomeTeam": "home_team",
            "AwayTeam": "away_team",
            "FTHG": "home_goals",
            "FTAG": "away_goals",
            "FTR": "result",           # H / D / A
            "HTHG": "ht_home_goals",
            "HTAG": "ht_away_goals",
            "HTR": "ht_result",
            # Match stats
            "HS": "home_shots",
            "AS": "away_shots",
            "HST": "home_shots_on_target",
            "AST": "away_shots_on_target",
            "HC": "home_corners",
            "AC": "away_corners",
            "HF": "home_fouls",
            "AF": "away_fouls",
            "HY": "home_yellow_cards",
            "AY": "away_yellow_cards",
            "HR": "home_red_cards",
            "AR": "away_red_cards",
            # Key bookmaker odds — 1X2
            "B365H": "b365_home",
            "B365D": "b365_draw",
            "B365A": "b365_away",
            "PSH": "pinnacle_home",
            "PSD": "pinnacle_draw",
            "PSA": "pinnacle_away",
            "BWH": "bwin_home",
            "BWD": "bwin_draw",
            "BWA": "bwin_away",
            "WHH": "william_hill_home",
            "WHD": "william_hill_draw",
            "WHA": "william_hill_away",
            "BFH": "betfair_home",    # Betfair exchange
            "BFD": "betfair_draw",
            "BFA": "betfair_away",
            # Max / Avg odds
            "MaxH": "max_home",
            "MaxD": "max_draw",
            "MaxA": "max_away",
            "AvgH": "avg_home",
            "AvgD": "avg_draw",
            "AvgA": "avg_away",
            # Over/Under 2.5
            "BbMx>2.5": "max_over_25",
            "BbAv>2.5": "avg_over_25",
            "BbMx<2.5": "max_under_25",
            "BbAv<2.5": "avg_under_25",
            "Max>2.5": "max_over_25",
            "Avg>2.5": "avg_over_25",
            "Max<2.5": "max_under_25",
            "Avg<2.5": "avg_under_25",
            "B365>2.5": "b365_over_25",
            "B365<2.5": "b365_under_25",
            "P>2.5": "pinnacle_over_25",
            "P<2.5": "pinnacle_under_25",
        }

        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

        # Map any extra goal-line columns, e.g. B365>1.5 → b365_over_1_5 (rare in FD files)
        df = FootballDataScraper._rename_dynamic_ou_columns(df)

        df = df.copy()
        df["league_code"] = league_code
        df["season"] = season

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")

        return df

    @staticmethod
    def _rename_dynamic_ou_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Rename columns like ``B365>1.5`` / ``P<0.5`` to snake_case if not already mapped.
        Football-Data standard free files are still mostly 2.5-only; this future-proofs
        divisions that add more goal lines.
        """
        new_cols = {}
        pat = re.compile(r"^([A-Za-z][A-Za-z0-9]*)([><])(\d+(?:\.\d+)?)$")
        for c in df.columns:
            if not isinstance(c, str):
                continue
            m = pat.match(c.strip())
            if not m:
                continue
            prefix, op, line = m.group(1), m.group(2), m.group(3)
            direction = "over" if op == ">" else "under"
            line_part = line.replace(".", "_")
            new_name = f"{prefix.lower()}_{direction}_{line_part}"
            if new_name in df.columns:
                continue
            if new_name in new_cols.values():
                continue
            new_cols[c] = new_name
        if new_cols:
            df = df.rename(columns=new_cols)
        return df
