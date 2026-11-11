"""System endpoints: health, status, diagnostics."""

from __future__ import annotations

import shutil
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings as get_settings_dep, search_cache
from app.core.config import Settings
from app.models import QueryPreset, SearchHistory

router = APIRouter(tags=["system"])

START_TIME = time.time()


@router.get("/health")
async def health(session: AsyncSession = Depends(get_db)) -> dict:
    """Liveness + minimal DB check."""
    db_ok = False
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/version")
async def version() -> dict:
    settings = get_settings_dep()
    return {"name": settings.app_name, "version": settings.version}


@router.get("/version")
async def version(settings: Settings = Depends(get_settings)) -> dict:
    """App identity + version."""
    return {"name": settings.app_name, "version": settings.version}


@router.get("/system/status")
async def system_status(
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    presets = (
        await session.execute(select(func.count()).select_from(QueryPreset))
    ).scalar_one()
    history = (
        await session.execute(select(func.count()).select_from(SearchHistory))
    ).scalar_one()
    return {
        "app": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "uptime_seconds": int(time.time() - START_TIME),
        "database_url_kind": settings.database_url.split("://")[0],
        "presets": presets,
        "history_entries": history,
        "cache": search_cache.stats(),
        "capabilities": {
            "search": True,
            "presets": True,
            "favorites": True,
            "history": True,
            "legacy_migration": True,
            "brave_provider": True,
            "searxng_provider": True,
            "local_index": False,  # Phase 6
            "ai": False,  # Phase 3
            "crawler": False,  # Phase 5
            "workspaces": False,  # Phase 4
        },
    }


@router.get("/system/diagnostics")
async def diagnostics(
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Detailed diagnostics safe to share for troubleshooting (no secrets)."""
    import sys

    checks: list[dict] = []

    # Database
    try:
        await session.execute(text("SELECT 1"))
        checks.append({"name": "database", "ok": True, "detail": "connection ok"})
    except Exception as exc:
        checks.append({"name": "database", "ok": False, "detail": str(exc)})

    # Data directory
    import pathlib

    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    parent = pathlib.Path(db_path).parent if db_path else pathlib.Path(".")
    writable = parent.exists() and (not db_path or _is_writable(parent))
    checks.append(
        {
            "name": "data_directory",
            "ok": writable,
            "detail": str(parent) + ("" if writable else " (not writable)"),
        }
    )

    # Disk space
    try:
        usage = shutil.disk_usage(parent)
        checks.append(
            {
                "name": "disk_space",
                "ok": usage.free > 100 * 1024 * 1024,
                "detail": f"{usage.free // (1024 * 1024)} MB free of {usage.total // (1024 * 1024)} MB",
            }
        )
    except Exception as exc:
        checks.append({"name": "disk_space", "ok": False, "detail": str(exc)})

    return {
        "python": sys.version.split(" ")[0],
        "settings": {
            "default_provider": settings.default_provider,
            "rate_limit": f"{settings.rate_limit_requests}/{settings.rate_limit_window_seconds}s",
            "cache_ttl": settings.search_cache_ttl_seconds,
            "api_key_required": bool(settings.api_key),
        },
        "checks": checks,
    }


def _is_writable(path) -> bool:
    import os

    return os.access(path, os.W_OK)
