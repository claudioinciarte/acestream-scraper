"""Tests for the AceStream engine catalogue source (``acestream-search://``).

The scraper turns the engine's ``/search`` payload into channels; these tests
drive it with a fake engine so no network or database is touched.
"""
import asyncio
from types import SimpleNamespace

import pytest

from app.models.url_types import AceStreamURL, create_url_object
from app.scrapers import create_scraper_for_url
from app.scrapers import acestream as acestream_module
from app.scrapers.acestream import AceStreamSearchScraper

ID_1 = "c1959a27edb0b94c5005a2dea93b7a70d4312f1c"
ID_2 = "4fe8fd8a4b98499f784bbb9a7b7b894109924067"
ID_3 = "8a25653a2f774f4ae1062d38a30dcd714d304a3a"


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        assert self.status_code < 400, self.status_code

    def json(self):
        return self._payload


class _FakeEngine:
    def __init__(self, pages=None, auth_level=645):
        self.pages = pages or {}
        self.auth_level = auth_level
        self.get_calls = []
        self.post_calls = []

    def get(self, url, params=None, timeout=None):
        params = dict(params or {})
        self.get_calls.append((url, params))
        if url.endswith("/server/api"):
            method = params.get("method")
            if method == "get_api_access_token":
                return _FakeResponse({"result": {"token": "tok"}})
            if method == "check_auth":
                return _FakeResponse({"result": {"auth_level": self.auth_level}})
            raise AssertionError(f"unexpected api method {method}")
        if url.endswith("/search"):
            page = int(params.get("page", 0))
            payload = self.pages.get(page, {"result": {"total": 0, "results": []}})
            return _FakeResponse(payload)
        raise AssertionError(url)

    def post(self, url, data=None, timeout=None):
        self.post_calls.append(dict(data or {}))
        self.auth_level = 645
        return _FakeResponse({"result": "ok"})


def _settings(email="", password="", engine="http://engine.test:6878"):
    return SimpleNamespace(ACE_ENGINE_URL=engine, ACESTREAM_EMAIL=email, ACESTREAM_PASSWORD=password)


def _run(scraper):
    captured = {}

    async def noop_update(url, status, error=None):
        captured["status"] = status
        captured["url"] = url

    scraper.update_url_status = noop_update
    channels, status = asyncio.run(scraper.scrape())
    return channels, status, captured


def _search_payload(page0_results, total):
    return {"result": {"total": total, "results": page0_results}}


class TestAceStreamURLType:
    def test_auto_detects_scheme(self):
        url_obj = create_url_object("acestream-search://catalog")
        assert isinstance(url_obj, AceStreamURL)

    @pytest.mark.parametrize("url_type", ["auto", "acestream"])
    def test_factory_builds_search_scraper(self, url_type):
        scraper = create_scraper_for_url("acestream-search://catalog", url_type)
        assert isinstance(scraper, AceStreamSearchScraper)


class TestAceStreamSearchScraper:
    def test_flattens_and_paginates(self, monkeypatch):
        pages = {
            0: _search_payload([
                {"name": "M. LaLiga", "items": [
                    {"name": "M. LaLiga", "infohash": ID_1, "bitrate": 800000,
                     "categories": ["sport"], "countries": ["es"], "languages": ["spa"]},
                ]},
                {"name": "Canal Málaga", "items": [
                    {"name": "Canal Málaga", "infohash": ID_2, "categories": ["regional", "tv"]},
                ]},
            ], 3),
            1: _search_payload([
                {"name": "DAZN LaLiga", "items": [
                    {"name": "DAZN LaLiga", "infohash": ID_3, "categories": ["sport"]},
                    {"name": "DAZN LaLiga", "infohash": ID_1, "categories": ["sport"]},  # duplicate
                ]},
            ], 3),
        }
        engine = _FakeEngine(pages=pages)
        monkeypatch.setattr(acestream_module, "requests", engine)
        monkeypatch.setattr(acestream_module, "get_settings", lambda: _settings())
        monkeypatch.setattr(acestream_module, "PAGE_SIZE", 2)

        scraper = create_scraper_for_url("acestream-search://catalog", "acestream")
        channels, status, captured = _run(scraper)

        ids = [c[0] for c in channels]
        assert ids == [ID_1, ID_2, ID_3]  # duplicate ID_1 dropped
        assert status == "OK"
        assert captured["url"] == "acestream-search://catalog"

        by_id = {c[0]: c for c in channels}
        assert by_id[ID_1][1] == "M. LaLiga"
        assert by_id[ID_1][2]["group"] == "sport"
        assert by_id[ID_1][2]["country"] == "es"
        assert by_id[ID_2][2]["group"] == "regional"

        search_pages = [p["page"] for url, p in engine.get_calls if url.endswith("/search")]
        assert search_pages == [0, 1]

    def test_query_and_category_filters_forwarded(self, monkeypatch):
        engine = _FakeEngine(pages={0: _search_payload([], 0)})
        monkeypatch.setattr(acestream_module, "requests", engine)
        monkeypatch.setattr(acestream_module, "get_settings", lambda: _settings())

        scraper = create_scraper_for_url(
            "acestream-search://catalog?category=sport&query=laliga", "acestream"
        )
        assert scraper.filters == {"query": "laliga", "category": "sport"}
        _run(scraper)

        _, params = next((url, p) for url, p in engine.get_calls if url.endswith("/search"))
        assert params["query"] == "laliga"
        assert params["category"] == "sport"

    def test_signs_in_when_session_expired(self, monkeypatch):
        engine = _FakeEngine(pages={0: _search_payload([], 0)}, auth_level=0)
        monkeypatch.setattr(acestream_module, "requests", engine)
        monkeypatch.setattr(
            acestream_module, "get_settings",
            lambda: _settings(email="user@example.com", password="p@ss w/ord"),
        )

        scraper = create_scraper_for_url("acestream-search://catalog", "acestream")
        channels, status, _ = _run(scraper)

        assert status == "OK"
        assert channels == []
        assert engine.post_calls and engine.post_calls[0]["method"] == "sign_in"
        assert engine.post_calls[0]["email"] == "user@example.com"

    def test_error_without_session_or_credentials(self, monkeypatch):
        engine = _FakeEngine(pages={0: _search_payload([], 0)}, auth_level=0)
        monkeypatch.setattr(acestream_module, "requests", engine)
        monkeypatch.setattr(acestream_module, "get_settings", lambda: _settings())

        scraper = create_scraper_for_url("acestream-search://catalog", "acestream")
        channels, status, _ = _run(scraper)

        assert channels == []
        assert status.startswith("Error:")
        assert not engine.post_calls
