"""
Scrape historical data from all sources and save as CSVs.
Usage:
    python -m scripts.scrape_data                   # all seasons (2020-2026)
    python -m scripts.scrape_data --current-season   # current season only
    python -m scripts.scrape_data --force            # re-scrape existing files
"""

import sys
import os
import asyncio
import argparse
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(_BACKEND_ROOT / ".env")
except ImportError:
    pass

from loguru import logger
from app.scraping.config import LEAGUES, get_current_season, get_seasons
from app.scraping.sources.football_data import FootballDataScraper
from app.scraping.sources.understat import UnderstatScraper
from app.scraping.sources.clubelo import ClubEloScraper
from app.scraping.sources.fbref import FBrefScraper
from app.scraping.sources.odds_api import OddsAPIScraper
from app.scraping.sources.transfermarkt import TransfermarktScraper

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


async def scrape_football_data(seasons: list[str], force: bool = False):
    out = DATA_DIR / "football_data"
    out.mkdir(parents=True, exist_ok=True)

    async with FootballDataScraper() as scraper:
        for code, mapping in LEAGUES.items():
            if not mapping.fd_division:
                continue
            for season in seasons:
                csv_path = out / f"{code}_{season}.csv"
                if csv_path.exists() and not force:
                    logger.info(f"[FD] Skip existing: {csv_path.name}")
                    continue
                try:
                    df = await scraper.scrape(code, season)
                    if not df.empty:
                        df.to_csv(csv_path, index=False)
                        logger.info(f"[FD] Saved {csv_path.name}: {len(df)} rows")
                except Exception as e:
                    logger.error(f"[FD] {code} {season}: {e}")


async def scrape_understat(seasons: list[str], force: bool = False):
    out_m = DATA_DIR / "understat_matches"
    out_t = DATA_DIR / "understat_teams"
    out_p = DATA_DIR / "understat_players"
    out_m.mkdir(parents=True, exist_ok=True)
    out_t.mkdir(parents=True, exist_ok=True)
    out_p.mkdir(parents=True, exist_ok=True)

    async with UnderstatScraper() as scraper:
        for code in UnderstatScraper.SUPPORTED_LEAGUES:
            for season in seasons:
                m_path = out_m / f"{code}_{season}.csv"
                if m_path.exists() and not force:
                    logger.info(f"[US] Skip existing: {m_path.name}")
                    continue
                try:
                    data = await scraper.scrape(code, season)
                    if "matches" in data and not data["matches"].empty:
                        data["matches"].to_csv(m_path, index=False)
                        logger.info(f"[US] Matches {m_path.name}: {len(data['matches'])} rows")
                    if "teams" in data and not data["teams"].empty:
                        t_path = out_t / f"{code}_{season}.csv"
                        data["teams"].to_csv(t_path, index=False)
                    if "players" in data and not data["players"].empty:
                        p_path = out_p / f"{code}_{season}.csv"
                        data["players"].to_csv(p_path, index=False)
                        logger.info(f"[US] Players {p_path.name}: {len(data['players'])} rows")
                except Exception as e:
                    logger.error(f"[US] {code} {season}: {e}")


async def scrape_clubelo(seasons: list[str], force: bool = False):
    out = DATA_DIR / "clubelo"
    out.mkdir(parents=True, exist_ok=True)

    async with ClubEloScraper() as scraper:
        for code, mapping in LEAGUES.items():
            if not mapping.clubelo_country:
                continue
            for season in seasons:
                csv_path = out / f"{code}_{season}.csv"
                if csv_path.exists() and not force:
                    logger.info(f"[Elo] Skip existing: {csv_path.name}")
                    continue
                try:
                    df = await scraper.scrape_season_snapshots(code, season)
                    if not df.empty:
                        df.to_csv(csv_path, index=False)
                        logger.info(f"[Elo] Saved {csv_path.name}: {len(df)} rows")
                except Exception as e:
                    logger.error(f"[Elo] {code} {season}: {e}")


async def scrape_fbref(seasons: list[str], force: bool = False):
    out_m = DATA_DIR / "fbref_matches"
    out_t = DATA_DIR / "fbref_teams"
    out_p = DATA_DIR / "fbref_players"
    out_m.mkdir(parents=True, exist_ok=True)
    out_t.mkdir(parents=True, exist_ok=True)
    out_p.mkdir(parents=True, exist_ok=True)

    async with FBrefScraper() as scraper:
        for code, mapping in LEAGUES.items():
            if not mapping.fbref_id:
                continue
            for season in seasons:
                m_path = out_m / f"{code}_{season}.csv"
                if m_path.exists() and not force:
                    logger.info(f"[FBref] Skip existing: {m_path.name}")
                    continue
                try:
                    data = await scraper.scrape(code, season)
                    if "matches" in data and not data["matches"].empty:
                        data["matches"].to_csv(m_path, index=False)
                        logger.info(f"[FBref] Matches {m_path.name}: {len(data['matches'])} rows")
                    if "teams" in data and not data["teams"].empty:
                        t_path = out_t / f"{code}_{season}.csv"
                        data["teams"].to_csv(t_path, index=False)
                    if "players" in data and not data["players"].empty:
                        p_path = out_p / f"{code}_{season}.csv"
                        data["players"].to_csv(p_path, index=False)
                        logger.info(f"[FBref] Players {p_path.name}: {len(data['players'])} rows")
                except Exception as e:
                    logger.error(f"[FBref] {code} {season}: {e}")
                await asyncio.sleep(5)


async def scrape_odds_api():
    out = DATA_DIR / "odds_api"
    out.mkdir(parents=True, exist_ok=True)

    async with OddsAPIScraper() as scraper:
        df = await scraper.scrape_all_leagues()
        if not df.empty:
            csv_path = out / "upcoming_odds.csv"
            df.to_csv(csv_path, index=False)
            logger.info(f"[OddsAPI] Saved {len(df)} odds rows")
        else:
            logger.info("[OddsAPI] No odds fetched (key missing or no upcoming matches)")


async def scrape_transfermarkt(seasons: list[str], force: bool = False):
    out = DATA_DIR / "transfermarkt"
    out.mkdir(parents=True, exist_ok=True)

    async with TransfermarktScraper() as scraper:
        for code, mapping in LEAGUES.items():
            if not mapping.tm_slug:
                continue
            for season in seasons:
                csv_path = out / f"{code}_{season}.csv"
                if csv_path.exists() and not force:
                    logger.info(f"[TM] Skip existing: {csv_path.name}")
                    continue
                try:
                    df = await scraper.scrape(code, season)
                    if not df.empty:
                        df.to_csv(csv_path, index=False)
                        logger.info(f"[TM] Saved {csv_path.name}: {len(df)} rows")
                except Exception as e:
                    logger.error(f"[TM] {code} {season}: {e}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-season", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--odds-only", action="store_true", help="Only fetch Odds API data")
    parser.add_argument("--transfermarkt", action="store_true", help="Include Transfermarkt scrape")
    args = parser.parse_args()

    seasons = [get_current_season()] if args.current_season else get_seasons(start_year=2020)

    if args.odds_only:
        logger.info("Fetching Odds API data only...")
        await scrape_odds_api()
        return

    logger.info(f"Scraping seasons: {seasons}")

    await scrape_football_data(seasons, force=args.force)
    await scrape_fbref(seasons, force=args.force)
    await scrape_understat(seasons, force=args.force)
    await scrape_clubelo(seasons, force=args.force)
    await scrape_odds_api()

    if args.transfermarkt:
        await scrape_transfermarkt(seasons, force=args.force)

    logger.info("Scraping complete!")


if __name__ == "__main__":
    asyncio.run(main())
