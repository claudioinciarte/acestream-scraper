"""Scraper for the AceStream engine's built-in content catalogue.

Unlike the HTTP/ZeroNet/IPFS strategies this source has no web page to fetch:
it asks the configured AceStream engine (``ace_engine_url``, the same setting
the Search page and playback use) for its catalogue through ``/search`` and
turns every available stream into a channel. The source is addressed with a
pseudo-URL so several sources (whole catalogue, one category, one query) can
coexist:

    acestream-search://catalog
    acestream-search://catalog?category=sport
    acestream-search://catalog?query=laliga

The engine must hold an authenticated session (AceStream "Smart" package). When
the session has expired and ``ACESTREAM_EMAIL`` / ``ACESTREAM_PASSWORD`` are
configured, the scraper signs in again before searching.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

import requests

from app.config.settings import get_settings
from app.models.url_types import AceStreamURL
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

PAGE_SIZE = 500
MAX_PAGES = 100
REQUEST_TIMEOUT = 20


class AceStreamSearchScraper(BaseScraper):
    """Import the engine's catalogue (``/search``) as a scrapeable source."""

    def __init__(self, url_obj: AceStreamURL, timeout: int = REQUEST_TIMEOUT, retries: int = 3,
                 db=None, epg_service=None, tv_channel_service=None):
        super().__init__(url_obj, timeout, retries, db, epg_service, tv_channel_service)
        self.filters = self._parse_source_url(url_obj.get_normalized_url())

    @staticmethod
    def _parse_source_url(url: str) -> Dict[str, str]:
        parsed = urlparse(url)
        query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
        return {
            "query": (query.get("query") or "").strip(),
            "category": (query.get("category") or "").strip(),
        }

    def _engine_url(self) -> str:
        """Resolve the engine the same way the Search page and playback do."""
        if self.db is not None:
            try:
                from app.repositories.settings_repository import SettingsRepository
                from app.services.engine_client import engine_url_from_settings
                return engine_url_from_settings(SettingsRepository(self.db))
            except Exception as exc:  # noqa: BLE001 - fall back to the env default
                logger.debug("Engine URL setting unavailable, using environment: %s", exc)
        url = (get_settings().ACE_ENGINE_URL or "").strip()
        if not url:
            url = "http://127.0.0.1:6878"
        if not url.startswith(("http://", "https://")):
            url = f"http://{url}"
        return url.rstrip("/")

    async def fetch_content(self, url: str) -> str:
        raise NotImplementedError("AceStream search sources do not fetch a web page")

    def _api_call(self, engine_url: str, method: str, token: Optional[str] = None) -> Dict:
        params = {"api_version": "3", "method": method}
        if token:
            params["token"] = token
        response = requests.get(f"{engine_url}/server/api", params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json().get("result", {}) or {}

    def _ensure_session(self, engine_url: str) -> str:
        """Return an API token, signing in first when the session has lapsed."""
        token = (self._api_call(engine_url, "get_api_access_token") or {}).get("token")
        if not token:
            raise RuntimeError("AceStream engine did not return an API token")
        auth = self._api_call(engine_url, "check_auth", token)
        if int(auth.get("auth_level") or 0) > 0:
            return token

        settings = get_settings()
        email = (settings.ACESTREAM_EMAIL or "").strip()
        password = settings.ACESTREAM_PASSWORD or ""
        if not (email and password):
            raise RuntimeError(
                "AceStream engine is not signed in and no ACESTREAM_EMAIL/ACESTREAM_PASSWORD are configured"
            )
        # requests URL-encodes the form body, so account characters stay intact.
        sign_in = requests.post(
            f"{engine_url}/server/api",
            data={"api_version": "3", "method": "sign_in", "token": token, "email": email, "password": password},
            timeout=self.timeout,
        )
        sign_in.raise_for_status()
        auth = self._api_call(engine_url, "check_auth", token)
        if int(auth.get("auth_level") or 0) <= 0:
            raise RuntimeError("AceStream sign_in did not establish a session")
        logger.info("AceStream session renewed for %s", email)
        return token

    def _fetch_catalog(self, engine_url: str) -> List[Tuple[str, str, Dict[str, object]]]:
        channels: List[Tuple[str, str, Dict[str, object]]] = []
        seen: set[str] = set()
        page = 0
        while page < MAX_PAGES:
            params: Dict[str, object] = {"page": page, "page_size": PAGE_SIZE}
            if self.filters["query"]:
                params["query"] = self.filters["query"]
            if self.filters["category"]:
                params["category"] = self.filters["category"]
            response = requests.get(f"{engine_url}/search", params=params, timeout=self.timeout)
            response.raise_for_status()
            payload = response.json().get("result", {}) or {}
            results = payload.get("results", []) or []
            total = int(payload.get("total") or 0)

            for group in results:
                group_name = self.clean_channel_name(group.get("name") or "")
                for item in group.get("items") or []:
                    infohash = (item.get("infohash") or "").strip().lower()
                    if len(infohash) != 40 or infohash in seen:
                        continue
                    seen.add(infohash)
                    categories = item.get("categories") or []
                    metadata = {
                        "group": categories[0] if categories else "",
                        "categories": ",".join(categories),
                        "bitrate": str(item.get("bitrate") or ""),
                        "country": ",".join(item.get("countries") or []),
                        "language": ",".join(item.get("languages") or []),
                    }
                    name = self.clean_channel_name(item.get("name") or group_name or infohash)
                    channels.append((infohash, name, metadata))

            page += 1
            if not results or page * PAGE_SIZE >= total:
                break
        return channels

    async def scrape(self, url: str = None) -> Tuple[List[Tuple[str, str, Dict[str, object]]], str]:
        engine_url = self._engine_url()
        source_url = self.url_obj.get_normalized_url()
        try:
            await asyncio.to_thread(self._ensure_session, engine_url)
            channels = await asyncio.to_thread(self._fetch_catalog, engine_url)
            status = "OK"
            logger.info("AceStream catalogue: %s channels from %s", len(channels), engine_url)
        except Exception as exc:  # noqa: BLE001 - surface the reason as the source status
            logger.error("AceStream catalogue scrape failed: %s", exc)
            channels = []
            status = f"Error: {exc}"
        await self.update_url_status(source_url, status)
        return channels, status
