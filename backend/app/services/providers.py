"""Provider service: seed default provider rows at startup."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProviderConfig

DEFAULT_PROVIDERS = [
    {
        "id": "searxng-local",
        "kind": "searxng",
        "name": "SearXNG (local)",
        "enabled": True,
        "endpoint": "http://localhost:8080",
        "timeout_seconds": 12.0,
        "priority": 1,
        "extra": {"safesearch": 1},
    },
    {
        "id": "brave",
        "kind": "brave",
        "name": "Brave Search API",
        "enabled": False,
        "endpoint": "https://api.search.brave.com",
        "timeout_seconds": 12.0,
        "priority": 5,
        "extra": {"safesearch": "moderate"},
    },
    {
        "id": "local-index",
        "kind": "local_index",
        "name": "Dork Atlas Index",
        "enabled": False,
        "endpoint": "",
        "timeout_seconds": 5.0,
        "priority": 50,
        "extra": {},
    },
]


async def seed_defaults(session: AsyncSession) -> int:
    """Insert default provider rows that do not exist yet. Idempotent."""
    existing_ids = set(
        (await session.execute(select(ProviderConfig.id))).scalars().all()
    )
    added = 0
    for spec in DEFAULT_PROVIDERS:
        if spec["id"] in existing_ids:
            continue
        session.add(ProviderConfig(**spec))
        added += 1
    if added:
        await session.flush()
    return added
