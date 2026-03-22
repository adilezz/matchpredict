"""
ClubElo API client — free Elo ratings for football clubs.

Provides:
- Daily Elo ratings for 500+ clubs since 1939
- Full rating history per club
- Rankings on any given date

Coverage: all major European leagues + many others.
API: http://api.clubelo.com — returns CSV, no auth required.

WHY THIS MATTERS for ML:
Elo rating is one of the single strongest predictive features for match
outcome. It encapsulates team strength, recent form, and quality of
opposition faced — all in one number.
"""

from datetime import date, timedelta
from io import StringIO
from typing import Optional

import pandas as pd
from loguru import logger

from app.scraping.base import BaseScraper
from app.scraping.config import CLUBELO_API_URL, LEAGUES


class ClubEloScraper(BaseScraper):
    """Fetches Elo ratings from the ClubElo API."""

    source_name = "clubelo"

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------

    async def scrape(self, league_code: str = "", season: str = "", **kwargs) -> pd.DataFrame:
        """Get current Elo ratings for all clubs (or filter by league)."""
        return await self.scrape_by_date(date.today(), league_code)

    async def scrape_by_date(
        self, target_date: date, league_code: str = ""
    ) -> pd.DataFrame:
        """Get the full Elo ranking for a specific date."""
        url = f"{CLUBELO_API_URL}/{target_date.isoformat()}"
        logger.info(f"[ClubElo] Fetching ratings for {target_date}")

        resp = await self._get(url)
        df = pd.read_csv(StringIO(resp.text))

        if df.empty:
            return df

        df.columns = ["rank", "club", "country", "level", "elo", "from_date", "to_date"]
        df["snapshot_date"] = target_date

        if league_code:
            mapping = LEAGUES.get(league_code)
            if mapping and mapping.clubelo_country:
                df = df[df["country"] == mapping.clubelo_country]

        return df

    async def scrape_team_history(self, club_name: str) -> pd.DataFrame:
        """
        Get the full Elo history for a single club.
        Club name must match ClubElo's format (e.g. "Liverpool", "Barcelona").
        """
        url = f"{CLUBELO_API_URL}/{club_name}"
        logger.info(f"[ClubElo] Fetching history for {club_name}")

        resp = await self._get(url)
        df = pd.read_csv(StringIO(resp.text))

        if df.empty:
            return df

        df.columns = ["rank", "club", "country", "level", "elo", "from_date", "to_date"]
        df["from_date"] = pd.to_datetime(df["from_date"], errors="coerce")
        df["to_date"] = pd.to_datetime(df["to_date"], errors="coerce")
        return df

    async def scrape_season_snapshots(
        self, league_code: str, season: str, interval_days: int = 14
    ) -> pd.DataFrame:
        """
        Get Elo snapshots throughout a season at regular intervals.
        Useful for building time-series Elo features for each match.
        """
        start_year = int(season.split("-")[0])
        start = date(start_year, 8, 1)
        end = date(start_year + 1, 6, 30)
        current = start

        frames = []
        while current <= end:
            try:
                df = await self.scrape_by_date(current, league_code)
                frames.append(df)
            except Exception as e:
                logger.warning(f"[ClubElo] Failed for {current}: {e}")
            current += timedelta(days=interval_days)

        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
