"""
FBref scraper — StatsBomb-quality data for ALL leagues.

IMPORTANT: FBref uses Cloudflare Turnstile. Use a scraping API with JS rendering:

  1. Scrape.do (recommended for this project): set SCRAPE_DO_TOKEN in .env
     Optional: SCRAPE_DO_SUPER=true (residential/mobile — better for Cloudflare, higher credit use)
  2. ScrapingBee: SCRAPING_API_KEY + SCRAPING_PROVIDER=scrapingbee (default URL)
  3. StatsBomb open data (free, limited seasons)

Without a token, FBref is skipped; Football-Data + Understat + ClubElo still work.

Data provided:
- Match results with xG, possession, kickoff times
- Team-level stats: shooting, passing, pressing, progressive actions
- Player-level stats with position
"""

import asyncio
import os
import random
import re
import time
from io import StringIO
from typing import Any, Literal

import httpx
import pandas as pd
from loguru import logger

from app.scraping.config import FBREF_BASE_URL, LEAGUES, LeagueMapping, RATE_LIMITS

SCRAPE_DO_TOKEN = os.getenv("SCRAPE_DO_TOKEN", "")
# Default false: datacenter + render is often enough for FBref; set true if you get 403/empty pages.
SCRAPE_DO_SUPER = os.getenv("SCRAPE_DO_SUPER", "false").lower() in ("1", "true", "yes")
SCRAPE_DO_API = os.getenv("SCRAPE_DO_API", "https://api.scrape.do/")

SCRAPING_API_KEY = os.getenv("SCRAPING_API_KEY", "")
SCRAPING_API_URL = os.getenv("SCRAPING_API_URL", "https://app.scrapingbee.com/api/v1/")
SCRAPING_PROVIDER = os.getenv("SCRAPING_PROVIDER", "").lower()  # scrapingbee | (empty = infer)


class FBrefScraper:
    """Scrapes match and stats data from FBref HTML tables.

    Uses Scrape.do (SCRAPE_DO_TOKEN) or ScrapingBee (SCRAPING_API_KEY) when configured.
    Direct httpx hits Cloudflare Turnstile (403).
    """

    source_name = "fbref"

    def __init__(self):
        self._rate_limit = RATE_LIMITS.get("fbref", 6.0)
        self._last_request_time: float = 0.0
        self._provider: Literal["scrapedo", "scrapingbee", "none"] = "none"
        if SCRAPE_DO_TOKEN:
            self._provider = "scrapedo"
        elif SCRAPING_API_KEY:
            self._provider = "scrapingbee"
        self._use_proxy = self._provider != "none"
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=30.0),
            follow_redirects=True,
        )
        if self._provider == "scrapedo":
            logger.info("[FBref] Using Scrape.do API (render + optional super proxy)")
        elif self._provider == "scrapingbee":
            logger.info("[FBref] Using ScrapingBee API")
        else:
            logger.warning(
                "[FBref] No SCRAPE_DO_TOKEN or SCRAPING_API_KEY. FBref is blocked by Cloudflare. "
                "Add Scrape.do token to .env or use Football-Data + Understat."
            )
        return self

    async def __aexit__(self, *exc):
        if self._client:
            await self._client.aclose()

    async def _respect_rate_limit(self):
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._rate_limit:
            jitter = random.uniform(0, self._rate_limit * 0.3)
            await asyncio.sleep(self._rate_limit - elapsed + jitter)
        self._last_request_time = time.monotonic()

    async def _get(self, url: str, max_retries: int = 3) -> str:
        """Fetch URL, using scraping proxy if configured."""
        assert self._client is not None

        for attempt in range(1, max_retries + 1):
            await self._respect_rate_limit()
            try:
                logger.debug(f"[fbref] GET {url} (attempt {attempt})")

                if self._provider == "scrapedo":
                    # No waitSelector: FBref schedule table often has no id=#sched_all in rendered DOM;
                    # waiting for it can return early. networkidle2 + customWait loads the full schedule.
                    params: dict[str, str] = {
                        "token": SCRAPE_DO_TOKEN,
                        "url": url,
                        "render": "true",
                        "waitUntil": "networkidle2",
                        "customWait": "8000",
                        "timeout": "110000",
                    }
                    if SCRAPE_DO_SUPER:
                        params["super"] = "true"
                    api_base = SCRAPE_DO_API.rstrip("/")
                    resp = await self._client.get(f"{api_base}/", params=params)
                elif self._provider == "scrapingbee":
                    resp = await self._client.get(
                        SCRAPING_API_URL,
                        params={
                            "api_key": SCRAPING_API_KEY,
                            "url": url,
                            "render_js": "true",
                            "premium_proxy": "true",
                        },
                    )
                else:
                    resp = await self._client.get(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Accept": "text/html",
                        },
                    )

                if resp.status_code == 200 and "<table" in resp.text:
                    return resp.text

                if resp.status_code == 403:
                    if not self._use_proxy:
                        logger.error(
                            "[FBref] 403 Forbidden — Cloudflare Turnstile active. "
                            "Set SCRAPE_DO_TOKEN or SCRAPING_API_KEY."
                        )
                        raise RuntimeError("FBref blocked by Cloudflare Turnstile")
                    wait = 10 * attempt
                    logger.warning(f"[FBref] 403 via proxy, retrying in {wait}s...")
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code != 200:
                    logger.warning(f"[FBref] HTTP {resp.status_code} from proxy, body[:200]={resp.text[:200]!r}")
                resp.raise_for_status()
                return resp.text

            except httpx.HTTPStatusError as e:
                if attempt == max_retries:
                    raise
                await asyncio.sleep(10 * attempt)
            except Exception as e:
                if attempt == max_retries:
                    raise
                await asyncio.sleep(10 * attempt)

        raise RuntimeError(f"[FBref] Failed after {max_retries} attempts: {url}")

    @staticmethod
    def _uncomment_tables(html: str) -> str:
        """FBref hides tables inside HTML comments; uncomment them for parsing."""
        return re.sub(r'<!--\s*(<div[^>]*>.*?</div>)\s*-->', r'\1', html, flags=re.DOTALL)

    @staticmethod
    def _pick_schedule_dataframe(tables: list) -> pd.DataFrame | None:
        """Choose the main fixtures table (Home + Away/Score, most rows)."""
        best: pd.DataFrame | None = None
        best_n = 0
        for t in tables:
            if t.empty:
                continue
            flat_cols = []
            for c in t.columns:
                if isinstance(c, tuple):
                    flat_cols.append(str(c[-1]).lower().strip())
                else:
                    flat_cols.append(str(c).lower().strip())
            has_home = any("home" in c for c in flat_cols)
            has_away = any("away" in c or "visitor" in c for c in flat_cols)
            has_score = any("score" in c for c in flat_cols)
            if has_home and (has_away or has_score) and len(t) > best_n:
                best, best_n = t, len(t)
        return best

    @staticmethod
    def _league(code: str) -> LeagueMapping:
        m = LEAGUES.get(code)
        if not m or not m.fbref_id:
            raise ValueError(f"League {code} has no FBref mapping")
        return m

    def _schedule_url(self, league: LeagueMapping, season: str) -> str:
        return (
            f"{FBREF_BASE_URL}/comps/{league.fbref_id}/"
            f"{season}/schedule/"
            f"{season}-{league.fbref_slug}-Scores-and-Fixtures"
        )

    def _stats_url(self, league: LeagueMapping, season: str, stat_type: str = "") -> str:
        suffix = f"{stat_type}/" if stat_type else ""
        return (
            f"{FBREF_BASE_URL}/comps/{league.fbref_id}/"
            f"{season}/{suffix}"
            f"{season}-{league.fbref_slug}-Stats"
        )

    async def scrape_matches(self, league_code: str, season: str) -> pd.DataFrame:
        league = self._league(league_code)
        url = self._schedule_url(league, season)
        logger.info(f"[FBref] Fetching matches: {league.name} {season}")

        html = await self._get(url)
        html = self._uncomment_tables(html)
        tables: list = []
        try:
            tables = pd.read_html(StringIO(html), attrs={"id": "sched_all"})
        except ValueError:
            pass
        if not tables:
            try:
                tables = pd.read_html(StringIO(html))
            except ValueError:
                tables = []

        df = self._pick_schedule_dataframe(tables) if tables else None
        if df is None or df.empty:
            logger.warning(f"[FBref] No schedule table found for {league.name} {season}")
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(-1)

        if "Home" in df.columns:
            df = df.dropna(subset=["Home"])
        elif len(df.columns) > 3:
            df = df.dropna(subset=[df.columns[3]])
        else:
            df = df.dropna(how="all")

        col_map = {}
        for col in df.columns:
            cl = str(col).lower().strip()
            if cl == "date":           col_map[col] = "date"
            elif cl == "time":         col_map[col] = "time"
            elif cl == "home":         col_map[col] = "home_team"
            elif cl in ("away", "visitor"): col_map[col] = "away_team"
            elif cl == "score":        col_map[col] = "score"
            elif "xg" in cl and "home_xg" not in col_map.values():
                col_map[col] = "home_xg"
            elif "xg" in cl and "away_xg" not in col_map.values():
                col_map[col] = "away_xg"
            elif cl == "venue":        col_map[col] = "venue"
            elif cl == "referee":      col_map[col] = "referee"
            elif cl in ("attendance", "attend"): col_map[col] = "attendance"
            elif cl in ("matchweek", "wk"):      col_map[col] = "matchday"

        df = df.rename(columns=col_map)

        if "score" in df.columns:
            scores = df["score"].astype(str).str.extract(r"(\d+)\s*[–\-:]\s*(\d+)")
            df["home_goals"] = pd.to_numeric(scores[0], errors="coerce")
            df["away_goals"] = pd.to_numeric(scores[1], errors="coerce")
        else:
            df["home_goals"] = None
            df["away_goals"] = None

        if "date" in df.columns and "time" in df.columns:
            df["datetime"] = pd.to_datetime(
                df["date"].astype(str) + " " + df["time"].astype(str).fillna("00:00"),
                errors="coerce",
            )
        elif "date" in df.columns:
            df["datetime"] = pd.to_datetime(df["date"], errors="coerce")

        for col in ("home_xg", "away_xg"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "matchday" in df.columns:
            df["matchday"] = pd.to_numeric(df["matchday"], errors="coerce")

        df["league_code"] = league_code
        df["season"] = season
        df["is_result"] = df["home_goals"].notna()

        keep_cols = [
            c for c in [
                "date", "time", "datetime", "home_team", "away_team",
                "home_goals", "away_goals", "home_xg", "away_xg",
                "venue", "referee", "matchday", "attendance",
                "league_code", "season", "is_result",
            ] if c in df.columns
        ]
        return df[keep_cols].copy()

    async def scrape_team_stats(self, league_code: str, season: str) -> pd.DataFrame:
        league = self._league(league_code)
        url = self._stats_url(league, season)
        logger.info(f"[FBref] Fetching team stats: {league.name} {season}")

        html = await self._get(url)
        html = self._uncomment_tables(html)
        try:
            tables = pd.read_html(StringIO(html))
        except ValueError:
            return pd.DataFrame()

        if not tables:
            return pd.DataFrame()

        df = tables[0]
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["_".join(str(c) for c in col).strip("_ ") for col in df.columns]

        df["league_code"] = league_code
        df["season"] = season
        return df

    async def scrape_player_stats(self, league_code: str, season: str) -> pd.DataFrame:
        league = self._league(league_code)
        url = (
            f"{FBREF_BASE_URL}/comps/{league.fbref_id}/"
            f"{season}/stats/{season}-{league.fbref_slug}-Stats"
        )
        logger.info(f"[FBref] Fetching player stats: {league.name} {season}")

        html = await self._get(url)
        html = self._uncomment_tables(html)
        try:
            tables = pd.read_html(StringIO(html), attrs={"id": "stats_standard"})
        except ValueError:
            tables = pd.read_html(StringIO(html))

        if not tables:
            return pd.DataFrame()

        df = tables[0]
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ["_".join(str(c) for c in col).strip("_ ") for col in df.columns]

        df["league_code"] = league_code
        df["season"] = season
        return df

    async def scrape(self, league_code: str, season: str, **kwargs) -> dict[str, Any]:
        """Scrape all FBref data for a league-season."""
        if not self._use_proxy:
            logger.warning(
                f"[FBref] Skipping {league_code} {season} — set SCRAPE_DO_TOKEN or SCRAPING_API_KEY."
            )
            return {}

        result = {}
        try:
            matches = await self.scrape_matches(league_code, season)
            if not matches.empty:
                result["matches"] = matches
        except Exception as e:
            logger.warning(f"[FBref] Matches failed for {league_code} {season}: {e}")

        await asyncio.sleep(8 + random.uniform(0, 4))

        try:
            team_stats = await self.scrape_team_stats(league_code, season)
            if not team_stats.empty:
                result["teams"] = team_stats
        except Exception as e:
            logger.warning(f"[FBref] Team stats failed for {league_code} {season}: {e}")

        await asyncio.sleep(8 + random.uniform(0, 4))

        try:
            player_stats = await self.scrape_player_stats(league_code, season)
            if not player_stats.empty:
                result["players"] = player_stats
        except Exception as e:
            logger.warning(f"[FBref] Player stats failed for {league_code} {season}: {e}")

        return result
