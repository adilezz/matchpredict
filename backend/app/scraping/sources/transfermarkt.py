"""
Transfermarkt scraper — squad market values.

Squad market value is one of the strongest long-term predictors of match
outcomes. This scraper fetches team-level market values per season.

Website: https://www.transfermarkt.com
Rate limit: 3 seconds between requests.
"""

import re
from typing import Any

import pandas as pd
from loguru import logger

from app.scraping.base import BaseScraper
from app.scraping.config import TRANSFERMARKT_BASE_URL, LEAGUES, LeagueMapping


class TransfermarktScraper(BaseScraper):
    """Scrapes squad market values from Transfermarkt."""

    source_name = "transfermarkt"

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    @staticmethod
    def _league(code: str) -> LeagueMapping:
        m = LEAGUES.get(code)
        if not m or not m.tm_slug:
            raise ValueError(f"League {code} has no Transfermarkt mapping")
        return m

    def _season_id(self, season: str) -> str:
        """Convert '2024-2025' to '2024' (TM uses start year)."""
        return season.split("-")[0]

    async def scrape(self, league_code: str, season: str, **kwargs) -> pd.DataFrame:
        """Scrape squad market values for a league season."""
        league = self._league(league_code)
        season_id = self._season_id(season)

        url = (
            f"{TRANSFERMARKT_BASE_URL}/{league.tm_slug}/"
            f"startseite/wettbewerb/{league.tm_id}/plus/?saison_id={season_id}"
        )
        logger.info(f"[TM] Fetching: {league.name} {season}")

        resp = await self._get(url, headers=self.HEADERS)
        html = resp.text

        rows = self._parse_squad_values(html, league_code, season)
        return pd.DataFrame(rows)

    def _parse_squad_values(self, html: str, league_code: str, season: str) -> list[dict]:
        """Extract team names and squad market values from the HTML table."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")

        rows = []
        table = soup.find("table", class_="items")
        if not table:
            logger.warning(f"[TM] No data table found for {league_code} {season}")
            return rows

        tbody = table.find("tbody")
        if not tbody:
            return rows

        for tr in tbody.find_all("tr", recursive=False):
            cells = tr.find_all("td")
            if len(cells) < 4:
                continue

            team_link = cells[1].find("a") if len(cells) > 1 else None
            team_name = team_link.get_text(strip=True) if team_link else None

            value_cell = cells[-1] if cells else None
            value_text = value_cell.get_text(strip=True) if value_cell else ""
            market_value = self._parse_value(value_text)

            squad_size_cell = cells[3] if len(cells) > 3 else None
            squad_size = None
            if squad_size_cell:
                try:
                    squad_size = int(squad_size_cell.get_text(strip=True))
                except (ValueError, TypeError):
                    pass

            if team_name:
                rows.append({
                    "team": team_name,
                    "market_value_eur": market_value,
                    "squad_size": squad_size,
                    "league_code": league_code,
                    "season": season,
                })

        return rows

    @staticmethod
    def _parse_value(text: str) -> float | None:
        """Parse '€1.23bn' or '€234.50m' to numeric EUR."""
        if not text:
            return None
        text = text.replace("€", "").replace(",", ".").strip()
        multiplier = 1
        if text.endswith("bn"):
            multiplier = 1_000_000_000
            text = text[:-2]
        elif text.endswith("m"):
            multiplier = 1_000_000
            text = text[:-1]
        elif text.endswith("k") or text.endswith("Th."):
            multiplier = 1_000
            text = text.replace("Th.", "").replace("k", "")
        try:
            return float(text) * multiplier
        except (ValueError, TypeError):
            return None
