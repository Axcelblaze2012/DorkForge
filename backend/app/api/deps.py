"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import Settings, get_settings
from ..database.session import get_db, get_sessionmaker  # re-export
from ..services.cache import SearchCache

# Process-wide bounded TTL cache for search responses.
search_cache = SearchCache(ttl_seconds=300)

__all__ = [
    "get_db",
    "get_sessionmaker",
    "get_settings",
    "require_api_key",
    "search_cache",
    "client_ip",
    "DBSession",
    "SettingsDep",
]


async def require_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """When an API key is configured, all /api/v1 routes require it.

    Left empty (default), the backend is a localhost single-user tool.
    """
    settings = get_settings()
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid X-API-Key header.",
        )


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


DBSession = Annotated[AsyncSession, Depends(get_db)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
