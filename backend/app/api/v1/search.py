"""Search execution endpoints."""

from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_settings, require_api_key, search_cache
from app.core.config import Settings
from app.models import ProviderConfig, SearchHistory
from app.schemas import (
    ComposerQueryRequest as ComposerQueryRequestModel,
    SearchRequest,
    SearchResponse,
)
from app.search.orchestrator.engine import (
    SearchOrchestrator,
    SearchRequest as EngineRequest,
)
from app.search.parser.builder import ComposerFields, build_query
from app.search.providers.base import ProviderConfigData
from app.search.providers.registry import build_adapter

router = APIRouter(prefix="/search", tags=["search"])


async def load_provider_configs(session: AsyncSession) -> list[ProviderConfigData]:
    from app.core.config import get_settings

    app_settings = get_settings()
    rows = (await session.execute(select(ProviderConfig))).scalars().all()
    if not rows:
        # Sensible defaults for a fresh database: local SearXNG first.
        return [
            ProviderConfigData(
                id="searxng-local",
                kind="searxng",
                name="SearXNG (local)",
                enabled=True,
                endpoint=app_settings.searxng_url or "http://localhost:8080",
                priority=1,
            ),
            ProviderConfigData(
                id="local-index",
                kind="local_index",
                name="Dork Atlas Index",
                enabled=False,
                priority=50,
            ),
        ]
    result: list[ProviderConfigData] = []
    for row in rows:
        endpoint = row.endpoint
        api_key = row.api_key
        enabled = row.enabled
        if row.kind == "searxng" and not endpoint and app_settings.searxng_url:
            endpoint = app_settings.searxng_url
        if row.kind == "brave" and not api_key and app_settings.brave_api_key:
            api_key = app_settings.brave_api_key
            enabled = True
        result.append(
            ProviderConfigData(
                id=row.id,
                kind=row.kind,
                name=row.name,
                enabled=enabled,
                endpoint=endpoint,
                api_key=api_key,
                timeout_seconds=row.timeout_seconds,
                priority=row.priority,
                extra=row.extra or {},
            )
        )
    return result


def _build_orchestrator(
    configs: list[ProviderConfigData], settings: Settings, providers: list[str] | None
) -> SearchOrchestrator:
    selected = configs
    if providers:
        wanted = set(providers)
        selected = [c for c in configs if c.id in wanted or c.kind in wanted]
    adapters = [build_adapter(cfg) for cfg in selected]
    return SearchOrchestrator(adapters, max_concurrency=settings.max_concurrent_providers)


async def _execute(
    request: SearchRequest,
    session: AsyncSession,
    settings: Settings,
) -> SearchResponse:
    cache_payload = {
        "query": request.query,
        "providers": request.providers,
        "page": request.page,
        "per_page": request.per_page,
        "language": request.language,
        "region": request.region,
    }
    fingerprint = search_cache.fingerprint(cache_payload)
    if settings.search_cache_ttl_seconds > 0:
        cached_value = search_cache.get(fingerprint)
        if cached_value is not None:
            response = SearchResponse.model_validate(cached_value)
            response.cached = True
            return response

    configs = await load_provider_configs(session)

    # Mode semantics: local_index restricts to the local adapter (which
    # honestly reports "not available in this build" rather than faking).
    providers = request.providers
    if request.mode == "local_index":
        providers = ["local-index"] + [c.id for c in configs if c.kind == "local_index"]

    orchestrator = _build_orchestrator(configs, settings, providers)
    engine_request = EngineRequest(
        query=request.query,
        providers=providers or [],
        page=request.page,
        per_page=request.per_page,
        language=request.language or "any",
        region=request.region or "any",
    )
    async with httpx.AsyncClient(follow_redirects=True) as client:
        outcome = await orchestrator.run(engine_request, client)

    total = len(outcome.results)
    start = (request.page - 1) * request.per_page
    page_items = outcome.results[start : start + request.per_page]
    total_pages = (total + request.per_page - 1) // request.per_page if request.per_page else 0

    response = SearchResponse(
        query=request.query,
        rendered_query=outcome.query_canonical,
        mode=request.mode,
        results=page_items,
        total=total,
        page=request.page,
        per_page=request.per_page,
        total_pages=total_pages,
        providers_used=[p.id for p in outcome.providers],
        provider_statuses=[
            {
                "provider": p.id,
                "kind": p.kind,
                "status": p.status,
                "latency_ms": p.latency_ms,
                "count": p.count,
                "error": p.error,
                "total_estimated": None,
            }
            for p in outcome.providers
        ],
        warnings=outcome.warnings,
        diagnostics=[d.to_dict() for d in outcome.diagnostics],
        operators=outcome.ast.operator_names(),
        dedup_removed=max(0, outcome.deduped_from - total),
        filters_applied_locally=any(
            tr.local_filters is not None
            and (
                tr.local_filters.domains
                or tr.local_filters.filetypes
                or tr.local_filters.url_terms
                or tr.local_filters.title_terms
            )
            for tr in outcome.translations.values()
        ),
        elapsed_ms=outcome.duration_ms,
        cached=False,
    )

    if request.save_history:
        row = SearchHistory(
            query=request.query,
            mode=request.mode,
            parsed_operators=outcome.ast.operator_names(),
            providers_used=[p.id for p in outcome.providers],
            provider_statuses=[s.model_dump() for s in response.provider_statuses],
            result_count=total,
            status="ok" if total > 0 else ("error" if outcome.has_errors else "empty"),
            duration_ms=outcome.duration_ms,
            cached=False,
        )
        session.add(row)
        await session.flush()
        response.history_id = row.id

    if settings.search_cache_ttl_seconds > 0:
        search_cache.set(fingerprint, response.model_dump(mode="json"))
    return response


@router.post("", response_model=SearchResponse)
async def execute_search(
    request: SearchRequest,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_api_key),
) -> SearchResponse:
    return await _execute(request, session, settings)


@router.post("/composer", response_model=SearchResponse)
async def execute_composer_search(
    body: ComposerQueryRequestModel,
    session: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: None = Depends(require_api_key),
) -> SearchResponse:
    """Execute a search built from composer fields (structured form state)."""
    ast = build_query(
        ComposerFields(
            terms=body.terms,
            domain=body.domain,
            filetype=body.filetype,
            title_term=body.title_term,
            url_term=body.url_term,
            exact_phrase=body.exact_phrase,
            exclude_terms=body.exclude_terms,
            time_range=body.time_range,
            region=body.region,
        )
    )
    request = SearchRequest(
        query=ast.to_query(),
        providers=body.providers,
        page=body.page,
        per_page=body.per_page,
        language=body.language,
        region=body.region,
    )
    return await _execute(request, session, settings)
