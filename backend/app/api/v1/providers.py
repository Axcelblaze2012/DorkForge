"""Search provider management endpoints."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings, require_api_key
from app.core.config import Settings
from app.models import ProviderConfig
from app.schemas import ProviderHealthOut, ProviderOut, ProviderUpdate
from app.search.compatibility import matrix_for
from app.search.providers.base import ProviderConfigData
from app.search.providers.registry import build_adapter, known_kinds

router = APIRouter(prefix="/providers", tags=["providers"])

DEFAULT_PROVIDERS = [
    {
        "id": "searxng-local",
        "kind": "searxng",
        "name": "SearXNG (local)",
        "enabled": True,
        "endpoint": "http://localhost:8080",
        "priority": 1,
        "extra": {"safesearch": 1},
    },
    {
        "id": "brave",
        "kind": "brave",
        "name": "Brave Search API",
        "enabled": False,
        "endpoint": "",
        "priority": 5,
        "extra": {"safesearch": "moderate"},
    },
    {
        "id": "local-index",
        "kind": "local_index",
        "name": "Dork Atlas Index",
        "enabled": False,
        "endpoint": "",
        "priority": 50,
        "extra": {},
    },
]


async def ensure_provider_rows(session: AsyncSession) -> list[ProviderConfig]:
    rows = (await session.execute(select(ProviderConfig))).scalars().all()
    if rows:
        return list(rows)
    for spec in DEFAULT_PROVIDERS:
        session.add(ProviderConfig(**spec))
    await session.flush()
    return list((await session.execute(select(ProviderConfig))).scalars().all())


def _to_out(row: ProviderConfig) -> ProviderOut:
    return ProviderOut(
        id=row.id,
        kind=row.kind,
        name=row.name,
        enabled=row.enabled,
        endpoint=row.endpoint,
        has_api_key=bool(row.api_key),
        timeout_seconds=row.timeout_seconds,
        priority=row.priority,
        safesearch=row.extra.get("safesearch") if row.extra else None,
        last_status=row.last_status,
        last_latency_ms=row.last_latency_ms,
        last_checked_at=row.last_checked_at.isoformat() if row.last_checked_at else None,
        last_success_at=row.last_success_at.isoformat() if row.last_success_at else None,
        last_error=row.last_error,
        error_count=row.error_count,
        compatibility=matrix_for(row.kind),
    )


@router.get("", response_model=list[ProviderOut])
async def list_providers(
    session: AsyncSession = Depends(get_db),
) -> list[ProviderOut]:
    rows = await ensure_provider_rows(session)
    rows.sort(key=lambda r: r.priority)
    return [_to_out(r) for r in rows]


@router.patch("/{provider_id}", response_model=ProviderOut)
async def update_provider(
    provider_id: str,
    body: ProviderUpdate,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> ProviderOut:
    rows = await ensure_provider_rows(session)
    row = next((r for r in rows if r.id == provider_id), None)
    if row is None:
        raise HTTPException(404, "Provider not found")
    data = body.model_dump(exclude_unset=True)
    if "safesearch" in data:
        extra = dict(row.extra or {})
        extra["safesearch"] = data.pop("safesearch")
        row.extra = extra
    if "api_key" in data and data["api_key"] is not None:
        row.api_key = data.pop("api_key")
    for key, value in data.items():
        setattr(row, key, value)
    await session.flush()
    return _to_out(row)


@router.get("/kinds")
async def provider_kinds() -> dict:
    return {"kinds": known_kinds()}


@router.post("/{provider_id}/test", response_model=ProviderHealthOut)
async def test_provider(
    provider_id: str,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> ProviderHealthOut:
    rows = await ensure_provider_rows(session)
    row = next((r for r in rows if r.id == provider_id), None)
    if row is None:
        raise HTTPException(404, "Provider not found")
    cfg = ProviderConfigData(
        id=row.id,
        kind=row.kind,
        name=row.name,
        enabled=True,
        endpoint=row.endpoint,
        api_key=row.api_key,
        timeout_seconds=min(row.timeout_seconds, 8.0),
        extra=row.extra or {},
    )
    adapter = build_adapter(cfg)
    async with httpx.AsyncClient(follow_redirects=True) as client:
        healthy, message, latency = await adapter.health_check(client)
    # Persist health state (never the API key).
    row.last_status = "ok" if healthy else "error"
    row.last_latency_ms = latency
    row.last_checked_at = row.updated_at
    row.last_error = None if healthy else message
    row.error_count = 0 if healthy else row.error_count + 1
    if healthy:
        from app.models.base import utcnow

        row.last_success_at = utcnow()
    await session.flush()
    return ProviderHealthOut(provider=row.id, healthy=healthy, message=message, latency_ms=latency)
