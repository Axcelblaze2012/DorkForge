"""Async SQLAlchemy setup (SQLite via aiosqlite in this build).

The URL comes from settings so a production deployment can point at
PostgreSQL without touching application code.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from ..core.config import get_settings
from ..models.base import Base

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        if settings.database_url.startswith("sqlite"):
            db_path = settings.database_url.split("///", 1)[-1]
            if db_path:
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_async_engine(settings.database_url, echo=False, future=True)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


# Compatibility alias used across the codebase.
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return get_sessionmaker()


async def init_db() -> None:
    """Create tables (create_all is sufficient for this single-file store)."""
    from .. import models  # noqa: F401  (register all tables)

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async session with commit-on-success."""
    factory = get_sessionmaker()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None
