"""
Base scraper with anti-ban measures: rotating user-agents, rate limiting,
exponential backoff retries, and optional proxy support.
"""

import asyncio
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.scraping.config import RATE_LIMITS

# ---------------------------------------------------------------------------
# User-Agent rotation pool
# ---------------------------------------------------------------------------

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
]


class BaseScraper(ABC):
    """
    Abstract base for all data-source scrapers.

    Provides:
    - Async HTTP client with rotating user-agents
    - Per-source rate limiting
    - Exponential-backoff retries on transient errors
    - Optional proxy support (set via PROXY_URL env var)
    """

    source_name: str = "base"

    def __init__(
        self,
        proxy_url: Optional[str] = None,
        rate_limit_override: Optional[float] = None,
    ):
        self._proxy_url = proxy_url
        self._rate_limit = rate_limit_override or RATE_LIMITS.get(
            self.source_name, 2.0
        )
        self._last_request_time: float = 0.0
        self._client: Optional[httpx.AsyncClient] = None

    # -- lifecycle -----------------------------------------------------------

    async def __aenter__(self):
        self._client = self._build_client()
        return self

    async def __aexit__(self, *exc):
        if self._client:
            await self._client.aclose()

    def _build_client(self) -> httpx.AsyncClient:
        transport_kwargs: dict[str, Any] = {}
        if self._proxy_url:
            transport_kwargs["proxy"] = self._proxy_url

        return httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
            **transport_kwargs,
        )

    # -- rate limiting -------------------------------------------------------

    async def _respect_rate_limit(self):
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._rate_limit:
            jitter = random.uniform(0, self._rate_limit * 0.3)
            await asyncio.sleep(self._rate_limit - elapsed + jitter)
        self._last_request_time = time.monotonic()

    # -- request helpers -----------------------------------------------------

    def _random_headers(self, extra: Optional[dict] = None) -> dict[str, str]:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        if extra:
            headers.update(extra)
        return headers

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=3, min=5, max=60),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def _get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
    ) -> httpx.Response:
        await self._respect_rate_limit()
        merged_headers = self._random_headers(headers)
        logger.debug(f"[{self.source_name}] GET {url}")

        assert self._client is not None, "Use scraper as async context manager"
        response = await self._client.get(url, params=params, headers=merged_headers)
        response.raise_for_status()
        return response

    async def _get_json(self, url: str, params: Optional[dict] = None) -> Any:
        resp = await self._get(url, params=params, headers={"Accept": "application/json"})
        return resp.json()

    # -- abstract interface --------------------------------------------------

    @abstractmethod
    async def scrape(self, league_code: str, season: str, **kwargs) -> Any:
        """Each scraper must implement its primary scrape method."""
        ...
