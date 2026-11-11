"""Shared fixtures: an isolated temp database and a live app client.

The database URL is pinned BEFORE app modules import settings, so every
test run gets a fresh throwaway SQLite file.
"""

from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="dork-atlas-tests-")
os.environ["DORK_ATLAS_DATABASE_URL"] = f"sqlite+aiosqlite:///{_TMP}/test.db"
os.environ.setdefault("DORK_ATLAS_SEARXNG_URL", "")

import httpx  # noqa: E402
import pytest  # noqa: E402

from app.main import app  # noqa: E402


class FakeAdapter:
    """Scriptable adapter used to test orchestration without network."""

    def __init__(self, config_id="fake", kind="searxng", results=None, status="ok", error=None):
        from app.search.providers.base import ProviderConfigData

        self.kind = kind
        self.config = ProviderConfigData(
            id=config_id, kind=kind, name=config_id.title(), enabled=True
        )
        self.results = results or []
        self.status = status
        self.error = error
        self.calls = []

    async def search(self, query, *, page, per_page, params=None, client):
        from app.search.providers.base import ProviderResult

        self.calls.append({"query": query, "page": page, "per_page": per_page, "params": params or {}})
        return ProviderResult(
            self.config.id,
            self.kind,
            self.status,
            results=list(self.results),
            error=self.error,
            latency_ms=5,
        )

    async def health_check(self, client):
        return True, "ok", 1


@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest.fixture
def fake_adapter():
    return FakeAdapter
