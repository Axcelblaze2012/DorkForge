"""Integration tests for all v1 API routes."""

from __future__ import annotations

import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_health_and_version(client):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "degraded")

    r = await client.get("/api/v1/version")
    assert r.status_code == 200
    data = r.json()
    assert "Dork Atlas" in data["name"]
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_system_status(client):
    r = await client.get("/api/v1/system/status")
    assert r.status_code == 200
    data = r.json()
    assert data["presets"] >= 52
    assert "capabilities" in data


@pytest.mark.asyncio
async def test_presets_list(client):
    r = await client.get("/api/v1/presets")
    assert r.status_code == 200
    data = r.json()
    presets = data["presets"]
    assert len(presets) >= 52

    # Check that builtins have categories and placeholders
    categories = {p["category"] for p in presets}
    assert "Site Discovery" in categories
    assert "Public Documents" in categories
    assert "Technology" in categories
    assert "Security & Policy" in categories

    first = presets[0]
    assert "id" in first
    assert "title" in first
    assert "query" in first


@pytest.mark.asyncio
async def test_preset_create_and_delete(client):
    create_payload = {
        "title": "Custom Test Preset",
        "description": "Testing custom preset creation",
        "query": "site:{domain} filetype:env",
        "category": "Technology",
    }
    r = await client.post("/api/v1/presets", json=create_payload)
    assert r.status_code == 201
    created = r.json()
    assert created["title"] == "Custom Test Preset"
    preset_id = created["id"]

    # Retrieve it
    r = await client.get(f"/api/v1/presets/{preset_id}")
    assert r.status_code == 200
    assert r.json()["id"] == preset_id

    # Delete it
    r = await client.delete(f"/api/v1/presets/{preset_id}")
    assert r.status_code == 204

    # Confirm it's gone
    r = await client.get(f"/api/v1/presets/{preset_id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_preset_favorite_toggle(client):
    r = await client.get("/api/v1/presets")
    preset_id = r.json()["presets"][0]["id"]

    # Favorite
    r = await client.post(f"/api/v1/presets/{preset_id}/favorite?value=true")
    assert r.status_code == 200
    assert r.json()["favorite"] is True

    # Unfavorite
    r = await client.post(f"/api/v1/presets/{preset_id}/favorite?value=false")
    assert r.status_code == 200
    assert r.json()["favorite"] is False


@pytest.mark.asyncio
async def test_history_lifecycle(client):
    # Add history entry
    payload = {
        "query": "site:example.com filetype:pdf",
        "mode": "universal",
        "result_count": 5,
        "status": "ok",
    }
    r = await client.post("/api/v1/search/history", json=payload)
    assert r.status_code == 201
    entry_id = r.json()["id"]

    # List history
    r = await client.get("/api/v1/search/history")
    assert r.status_code == 200
    history = r.json()["items"]
    assert any(h["id"] == entry_id for h in history)

    # Delete single history item
    r = await client.delete(f"/api/v1/search/history/{entry_id}")
    assert r.status_code == 204

    # Confirm deleted
    r = await client.get("/api/v1/search/history")
    assert not any(h["id"] == entry_id for h in r.json()["items"])


@pytest.mark.asyncio
async def test_query_endpoints(client):
    # Parse query
    r = await client.post("/api/v1/query/parse", json={"query": 'site:example.com "annual report"'})
    assert r.status_code == 200
    data = r.json()
    assert "operators" in data
    assert "site" in data["operators"]

    # Explain query
    r = await client.post("/api/v1/query/explain", json={"query": "site:example.com filetype:pdf"})
    assert r.status_code == 200
    data = r.json()
    assert data["rendered_query"] == "site:example.com filetype:pdf"
    assert "complexity" in data

    # Validate query
    r = await client.post("/api/v1/query/validate", json={"query": "site:example.com"})
    assert r.status_code == 200
    assert r.json()["valid"] is True


@pytest.mark.asyncio
async def test_providers_endpoints(client):
    r = await client.get("/api/v1/providers")
    assert r.status_code == 200
    providers = r.json()
    assert len(providers) >= 2
    searxng = next((p for p in providers if p["kind"] == "searxng"), None)
    assert searxng is not None

    # Patch provider
    r = await client.patch(
        f"/api/v1/providers/{searxng['id']}",
        json={"priority": 2},
    )
    assert r.status_code == 200
    assert r.json()["priority"] == 2


@pytest.mark.asyncio
async def test_legacy_migration(client):
    payload = {
        "favorites": ["b0", "b1"],
        "custom": [
            {
                "title": "Migrated Custom Dork",
                "query": "site:{domain} inurl:admin",
                "category": "Technology",
            }
        ],
        "recent": [
            {
                "query": "site:test.com",
                "label": "Google search",
                "when": "2026-11-08",
            }
        ],
    }

    # First import
    r = await client.post("/api/v1/migration/legacy", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["favorites_imported"] == 2
    assert data["custom_imported"] == 1
    assert data["recent_imported"] == 1
    assert data["already_imported"] is False

    # Second import should be idempotent
    r = await client.post("/api/v1/migration/legacy", json=payload)
    assert r.status_code == 200
    data2 = r.json()
    assert data2["already_imported"] is True
    assert data2["custom_imported"] == 0


@pytest.mark.asyncio
async def test_search_orchestration_with_adapter(client, monkeypatch):
    """Test full search flow through orchestrator with fake adapter."""
    from app.search.providers.base import ProviderConfigData, ProviderResult

    fake_results = [
        {
            "title": "Annual Report 2024",
            "url": "https://example.com/report2024.pdf",
            "snippet": "Public annual financial statement",
            "engine": "google",
        },
        {
            "title": "Quarterly Update",
            "url": "https://example.com/q3.pdf",
            "snippet": "Third quarter investor review",
            "engine": "bing",
        },
    ]

    async def fake_search(*args, **kwargs):
        return ProviderResult(
            provider="searxng-local",
            kind="searxng",
            status="ok",
            results=fake_results,
            latency_ms=12,
        )

    # Monkeypatch SearXNGAdapter search method
    from app.search.providers.searxng import SearXNGAdapter

    monkeypatch.setattr(SearXNGAdapter, "search", fake_search)

    r = await client.post(
        "/api/v1/search",
        json={
            "query": "site:example.com filetype:pdf",
            "mode": "universal",
            "page": 1,
            "per_page": 10,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert len(data["results"]) == 2
    assert data["results"][0]["title"] == "Annual Report 2024"
    assert data["results"][0]["url"] == "https://example.com/report2024.pdf"
    assert data["operators"] == ["filetype", "site"]
    assert "history_id" in data
