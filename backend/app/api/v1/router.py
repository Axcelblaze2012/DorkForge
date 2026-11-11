"""Aggregated v1 API router."""

from __future__ import annotations

from fastapi import APIRouter

from . import history, migration, presets, providers, query, search, settings, system

api_router = APIRouter()

api_router.include_router(system.router)
api_router.include_router(search.router)
api_router.include_router(history.router)
api_router.include_router(query.router)
api_router.include_router(presets.router)
api_router.include_router(providers.router)
api_router.include_router(settings.router)
api_router.include_router(migration.router)
