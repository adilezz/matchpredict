"""
The Odds API scraper — pre-match bookmaker odds.

Free tier: 500 requests/month. We only fetch odds for upcoming matches
to conserve quota. Historical odds come from Football-Data.co.uk CSVs.

API: https://api.the-odds-api.com/v4
Markets: h2h (1X2), totals (O/U 2.5)
"""

from datetime import datetime, timezone
from typing import Any

import pandas as pd
from loguru import logger

from app.scraping.base import BaseScraper
from app.scraping.config import ODDS_API_BASE_URL, LEAGUES, LeagueMapping
from app.core.config import get_settings


class OddsAPIScraper(BaseScraper):
    """Fetches pre-match odds from The Odds API."""

    source_name = "odds_api"

    def __init__(self):
        super().__init__()
        self._api_key = get_settings().odds_api_key

    @staticmethod
    def _league(code: str) -> LeagueMapping:
        m = LEAGUES.get(code)
        if not m or not m.odds_api_key:
            raise ValueError(f"League {code} has no Odds API mapping")
        return m

    async def scrape(self, league_code: str, season: str = "", **kwargs) -> pd.DataFrame:
        """Fetch current odds for a league's upcoming matches."""
        if not self._api_key:
            logger.warning("[OddsAPI] No API key configured, skipping")
            return pd.DataFrame()

        league = self._league(league_code)
        sport_key = league.odds_api_key

        url = (
            f"{ODDS_API_BASE_URL}/sports/{sport_key}/odds/"
            f"?apiKey={self._api_key}"
            f"&regions=eu,uk"
            f"&markets=h2h,totals"
            f"&oddsFormat=decimal"
        )
        logger.info(f"[OddsAPI] Fetching odds: {league.name}")

        resp = await self._get(url)
        try:
            data = resp.json()
        except Exception as e:
            logger.error(f"[OddsAPI] Invalid JSON: {e}")
            return pd.DataFrame()

        if not isinstance(data, list):
            logger.warning(f"[OddsAPI] Unexpected response format for {league.name}")
            return pd.DataFrame()

        rows = []
        for event in data:
            home = event.get("home_team", "")
            away = event.get("away_team", "")
            commence = event.get("commence_time", "")

            for bookmaker in event.get("bookmakers", []):
                bk_name = bookmaker.get("key", "unknown")
                row = {
                    "home_team": home,
                    "away_team": away,
                    "commence_time": commence,
                    "bookmaker": bk_name,
                    "league_code": league_code,
                }

                for market in bookmaker.get("markets", []):
                    key = market.get("key")
                    outcomes = {o["name"]: o["price"] for o in market.get("outcomes", [])}

                    if key == "h2h":
                        row["home_odds"] = outcomes.get("Home", outcomes.get(home))
                        row["draw_odds"] = outcomes.get("Draw")
                        row["away_odds"] = outcomes.get("Away", outcomes.get(away))
                    elif key == "totals":
                        row["over_25_odds"] = outcomes.get("Over")
                        row["under_25_odds"] = outcomes.get("Under")

                rows.append(row)

        df = pd.DataFrame(rows)
        if not df.empty and "commence_time" in df.columns:
            df["commence_time"] = pd.to_datetime(df["commence_time"], errors="coerce")

        return df

    async def scrape_all_leagues(self) -> pd.DataFrame:
        """Fetch odds for all configured leagues."""
        frames = []
        for code, mapping in LEAGUES.items():
            if not mapping.odds_api_key:
                continue
            try:
                df = await self.scrape(code)
                if not df.empty:
                    frames.append(df)
            except Exception as e:
                logger.warning(f"[OddsAPI] Failed {code}: {e}")
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
