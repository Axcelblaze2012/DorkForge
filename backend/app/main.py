"""Dork Atlas Ultimate — FastAPI application entrypoint.

Phase 1 scope: real in-app search, provider orchestration, presets,
favorites, history, settings, legacy migration, and system diagnostics.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import search_cache
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.middleware import (
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.database.session import dispose_engine, get_engine
from app.models import Base

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database.session import get_session_factory
    from app.services.seeder import ensure_seeded

    # Create tables and seed the built-in preset library (idempotent).
    engine = get_engine()
    if settings.database_url.startswith("sqlite"):
        # For local SQLite, ensure the data directory exists.
        import pathlib

        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        if db_path:
            pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = get_session_factory()
    async with factory() as session:
        from app.services.providers import seed_defaults

        added = await ensure_seeded(session)
        await seed_defaults(session)
        await session.commit()
        if added:
            import logging

            logging.getLogger(__name__).info("Seeded %d built-in presets", added)
    yield
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description=(
            "Advanced search and OSINT research platform backend. "
            "Phase 1: real in-app search via configured providers (SearXNG, "
            "Brave), structured dork query engine, preset library, favorites, "
            "search history, and legacy data migration."
        ),
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
