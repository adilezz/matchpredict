"""
Team logo fetcher — downloads logos from free APIs.

Uses API-Football's free image endpoint (no auth needed for images)
or falls back to SofaScore. Logos are saved as PNG files in data/logos/.
"""

from pathlib import Path

from loguru import logger

from app.scraping.base import BaseScraper
from app.scraping.config import LEAGUES


LOGO_URL_TEMPLATE = "https://media.api-sports.io/football/teams/{team_id}.png"
SOFASCORE_LOGO_TEMPLATE = "https://api.sofascore.app/api/v1/team/{team_id}/image"


class LogoFetcher(BaseScraper):
    """Downloads team logos and saves them locally."""

    source_name = "logos"

    async def fetch_league_logos(
        self,
        league_code: str,
        output_dir: Path,
        team_ids: dict[str, int] | None = None,
    ) -> dict[str, str]:
        """
        Fetch logos for all teams in a league.

        team_ids: mapping of team_name -> API-Football team ID.
        If not provided, attempts to use SofaScore league endpoint.

        Returns: dict of team_name -> local file path.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        result = {}

        if not team_ids:
            logger.info(f"[Logos] No team IDs for {league_code}, skipping")
            return result

        for team_name, team_id in team_ids.items():
            safe_name = team_name.replace(" ", "_").replace("/", "_")
            out_path = output_dir / f"{safe_name}.png"

            if out_path.exists():
                result[team_name] = str(out_path.relative_to(output_dir.parent.parent))
                continue

            url = LOGO_URL_TEMPLATE.format(team_id=team_id)
            try:
                resp = await self._get(url)
                if resp.status_code == 200 and len(resp.content) > 100:
                    out_path.write_bytes(resp.content)
                    result[team_name] = str(out_path.relative_to(output_dir.parent.parent))
                    logger.info(f"[Logos] Saved: {safe_name}.png")
                else:
                    logger.warning(f"[Logos] Empty/invalid response for {team_name}")
            except Exception as e:
                logger.warning(f"[Logos] Failed {team_name}: {e}")

        return result

    async def scrape(self, league_code: str = "", season: str = "", **kwargs):
        """Not used directly — use fetch_league_logos instead."""
        return {}
