"""Search orchestration: parse → translate → fan out → normalise → rank.

The engine never hides provider failures: every provider attempt produces a
status that is surfaced to the caller, and dropped operators produce
warnings. When no provider succeeds, the response says so instead of
returning fabricated or stale data.
"""

from __future__ import annotations

import asyncio
import fnmatch
import time
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import httpx

from ..parser.nodes import Diagnostic, QueryAST
from ..parser.parser import parse_query
from ..parser.translator import Translation, translate
from ..processing.normalize import domain_of, merge_results, strip_tracking
from ..processing.ranking import build_context, explain, score_result
from ..providers.base import ProviderAdapter, ProviderConfigData, ProviderResult

MAX_PAGES = 10


@dataclass
class SearchRequest:
    """Everything one search execution needs."""

    query: str
    providers: list[str]
    page: int = 1
    per_page: int = 20
    language: str = "any"
    region: str = "any"

    def clamped(self, max_per_page: int) -> "SearchRequest":
        return SearchRequest(
            query=self.query,
            providers=list(self.providers),
            page=max(1, min(self.page, MAX_PAGES)),
            per_page=max(1, min(self.per_page, max_per_page)),
            language=self.language or "any",
            region=self.region or "any",
        )


@dataclass
class ProviderReport:
    """Outcome of one provider attempt, safe to serialise."""

    id: str
    kind: str
    status: str
    count: int = 0
    latency_ms: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "count": self.count,
            "latency_ms": self.latency_ms,
            "error": self.error,
        }


@dataclass
class SearchOutcome:
    """Complete, explainable result of one search."""

    query_raw: str
    query_canonical: str
    ast: QueryAST
    results: list[dict[str, Any]] = field(default_factory=list)
    providers: list[ProviderReport] = field(default_factory=list)
    translations: dict[str, Translation] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    total: int = 0
    deduped_from: int = 0
    duration_ms: int = 0
    cache: str = "miss"  # hit | miss

    @property
    def has_errors(self) -> bool:
        return self.ast.has_errors()

    def provider_dicts(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self.providers]


def _host_matches(host: str, domain: str) -> bool:
    host, domain = host.lower(), domain.lower().lstrip("*.")
    if not host or not domain:
        return False
    return host == domain or host.endswith("." + domain)


def _parse_published(value: str | None) -> date | None:
    if not value:
        return None
    try:
        if len(value) >= 10 and value[4] == "-" and value[7] == "-":
            return date.fromisoformat(value[:10])
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


class SearchOrchestrator:
    """Executes a parsed query against a registry of provider adapters."""

    def __init__(self, adapters: list[ProviderAdapter], max_concurrency: int = 4) -> None:
        self.adapters = {a.config.id: a for a in adapters}
        self.semaphore = asyncio.Semaphore(max(1, max_concurrency))

    # -- public API ---------------------------------------------------------

    async def run(
        self, request: SearchRequest, client: httpx.AsyncClient
    ) -> SearchOutcome:
        started = time.perf_counter()
        ast = parse_query(request.query)
        outcome = SearchOutcome(
            query_raw=request.query,
            query_canonical=ast.to_query(),
            ast=ast,
            diagnostics=list(ast.diagnostics),
        )

        if ast.has_errors():
            outcome.duration_ms = self._ms(started)
            outcome.warnings.append(
                "Query has errors; fix them before searching. No providers were contacted."
            )
            return outcome

        # Resolve requested providers against the registry.
        requested = request.providers or list(self.adapters)
        known: list[ProviderAdapter] = []
        for pid in requested:
            adapter = self.adapters.get(pid)
            if adapter is None:
                outcome.diagnostics.append(
                    Diagnostic("warning", "unknown_provider", f"Unknown provider '{pid}' was skipped.")
                )
            else:
                known.append(adapter)
        if not known:
            outcome.duration_ms = self._ms(started)
            outcome.warnings.append("No known providers were requested.")
            return outcome

        # Translate once per provider kind; share identical translations.
        translations: dict[str, Translation] = {}
        jobs: list[tuple[ProviderAdapter, Translation]] = []
        for adapter in known:
            kind = adapter.kind
            if kind not in translations:
                translations[kind] = translate(
                    ast, kind, language=request.language
                )
            jobs.append((adapter, translations[kind]))
        outcome.translations = {kind: tr for kind, tr in translations.items()}

        # Fan out with bounded concurrency.
        responses = await asyncio.gather(
            *(self._run_one(adapter, tr, request, client) for adapter, tr in jobs)
        )

        raw_results: list[dict[str, Any]] = []
        for adapter, translation, result in responses:
            report = ProviderReport(
                id=adapter.config.id,
                kind=adapter.kind,
                status=result.status,
                count=len(result.results),
                latency_ms=result.latency_ms,
                error=result.error,
            )
            outcome.providers.append(report)
            if result.status == "ok":
                for item in result.results:
                    item["provider"] = adapter.config.id
                raw_results.extend(result.results)
            elif result.status in ("error", "timeout"):
                outcome.warnings.append(
                    f"Provider '{adapter.config.id}' failed: {result.error or result.status}"
                )

        outcome.warnings.extend(self._collect_warnings(translations))

        # Normalise: tracking stripped, domain extracted, dedup with merge.
        for item in raw_results:
            item["url"] = strip_tracking(item.get("url") or item["url"])
            item.setdefault("domain", domain_of(item["url"]))
        merged = merge_results(raw_results)
        outcome.deduped_from = len(raw_results)

        # Local post-filters + ranking. Provider weight follows the order the
        # caller requested (primary provider first).
        provider_order = {a.config.id: i for i, a in enumerate(known)}
        ctx = build_context(ast.nodes)
        kept: list[dict[str, Any]] = []
        for item in merged:
            translation = translations.get(
                next((a.kind for a in known if a.config.id == item.get("provider")), ""), None
            )
            local = translation.local_filters if translation else None
            if local is not None and not self._passes_local_filters(item, local):
                continue
            if not self._passes_dates(item, ast):
                continue
            weight = provider_order.get(item.get("provider", ""), len(provider_order))
            item["score"] = score_result(item, ctx, weight)
            item["explain"] = explain(item, ctx, weight)
            kept.append(item)

        kept.sort(key=lambda r: r["score"], reverse=True)
        outcome.results = kept
        outcome.total = len(kept)
        outcome.duration_ms = self._ms(started)
        return outcome

    async def health_all(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Health-check every registered adapter concurrently."""

        async def one(adapter: ProviderAdapter) -> dict[str, Any]:
            ok, message, latency = await adapter.health_check(client)
            return {"id": adapter.config.id, "kind": adapter.kind, "healthy": ok, "message": message, "latency_ms": latency}

        return list(await asyncio.gather(*(one(a) for a in self.adapters.values())))

    # -- internals ------------------------------------------------------------

    async def _run_one(
        self,
        adapter: ProviderAdapter,
        translation: Translation,
        request: SearchRequest,
        client: httpx.AsyncClient,
    ) -> tuple[ProviderAdapter, Translation, ProviderResult]:
        async with self.semaphore:
            params = dict(translation.params)
            if request.region and request.region != "any":
                params.setdefault("country", request.region)
            result = await adapter.search(
                translation.query,
                page=request.page,
                per_page=request.per_page,
                params=params,
                client=client,
            )
        return adapter, translation, result

    def _collect_warnings(self, translations: dict[str, Translation]) -> list[str]:
        warnings: list[str] = []
        for kind, tr in translations.items():
            for w in tr.warnings:
                line = f"[{kind}] {w}"
                if line not in warnings:
                    warnings.append(line)
        return warnings

    def _passes_local_filters(self, item: dict[str, Any], local: Any) -> bool:
        """Apply constraints the provider could not honour itself."""
        host = (item.get("domain") or "").lower()
        url = (item.get("url") or "").lower()
        title = (item.get("title") or "").lower()

        if local.domains and not any(_host_matches(host, d) for d in local.domains):
            return False
        if local.excluded_domains and any(_host_matches(host, d) for d in local.excluded_domains):
            return False
        if local.filetypes:
            path = url.split("?", 1)[0]
            if not any(path.endswith("." + ft.lower().lstrip(".")) for ft in local.filetypes):
                return False
        if local.url_terms and not any(t.lower() in url for t in local.url_terms):
            return False
        if local.title_terms and not any(t.lower() in title for t in local.title_terms):
            return False
        return True

    def _passes_dates(self, item: dict[str, Any], ast: QueryAST) -> bool:
        """Locally enforce before:/after: when the result carries a date.

        Results without a verifiable date are KEPT (we cannot confirm either
        way); this limitation is stated in the response instead of silently
        dropping or fabricating data.
        """
        after: date | None = None
        before: date | None = None
        for node in ast.walk():
            from ..parser.nodes import Operator

            if isinstance(node, Operator) and node.op == "after":
                after = _parse_published(node.value) or after
            elif isinstance(node, Operator) and node.op == "before":
                before = _parse_published(node.value) or before
        if after is None and before is None:
            return True
        published = _parse_published(item.get("published_date"))
        if published is None:
            return True
        if after and published < after:
            return False
        if before and published >= before:
            return False
        return True

    @staticmethod
    def _ms(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)
