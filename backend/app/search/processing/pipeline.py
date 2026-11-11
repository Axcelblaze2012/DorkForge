"""Central result pipeline: normalize -> filter -> dedupe -> rank -> paginate.

Stage order (Section 15 of the product spec):
  1. receive provider results   (orchestrator)
  2. normalise URLs / strip tracking params
  3. apply user + operator-derived local filters (labeled)
  4. deduplicate on canonical URL, merging attribution
  5. score + rank deterministically
  6. paginate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .normalize import dedupe_key, domain_of, merge_results, normalize_url, strip_tracking
from .ranking import RankContext, build_context, explain, score_result


@dataclass
class LocalFilterSet:
    """Filters applied after retrieval, clearly labeled in responses."""

    domains: list[str] = field(default_factory=list)
    excluded_domains: list[str] = field(default_factory=list)
    filetypes: list[str] = field(default_factory=list)
    url_terms: list[str] = field(default_factory=list)
    title_terms: list[str] = field(default_factory=list)
    language: str | None = None

    def is_empty(self) -> bool:
        return not any(
            [self.domains, self.excluded_domains, self.filetypes, self.url_terms, self.title_terms]
        )


def _extension_matches(url: str, filetypes: list[str]) -> bool:
    """Check the URL path extension against allowed filetypes."""
    from urllib.parse import urlparse

    path = (urlparse(url).path or "").lower()
    return any(path.endswith("." + ft.lower()) for ft in filetypes)


def apply_local_filters(items: list[dict[str, Any]], filters: LocalFilterSet) -> list[dict[str, Any]]:
    if filters.is_empty():
        return items
    out: list[dict[str, Any]] = []
    for item in items:
        host = domain_of(item.get("url", ""))
        if filters.domains:
            if not any(host == d.lower().lstrip("*.") or host.endswith("." + d.lower().lstrip("*.")) for d in filters.domains):
                continue
        if filters.excluded_domains and any(
            host == d.lower() or host.endswith("." + d.lower()) for d in filters.excluded_domains
        ):
            continue
        if filters.filetypes and not _extension_matches(item.get("url", ""), filters.filetypes):
            continue
        if filters.url_terms and not any(
            t.lower() in item.get("url", "").lower() for t in filters.url_terms
        ):
            continue
        if filters.title_terms and not any(
            t.lower() in (item.get("title") or "").lower() for t in filters.title_terms
        ):
            continue
        out.append(item)
    return out


def process(
    provider_results: list[dict[str, Any]],
    ast,
    *,
    local_filters: LocalFilterSet | None = None,
    page: int = 1,
    per_page: int = 20,
    provider_order: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Run the full pipeline. Returns final page plus processing metadata."""
    provider_order = provider_order or {}
    local_filters = local_filters or LocalFilterSet()

    # 1-2. Normalise URLs + strip tracking params, attach domains.
    normalized: list[dict[str, Any]] = []
    for item in provider_results:
        url = strip_tracking(item.get("url", ""))
        if not url:
            continue
        entry = dict(item)
        entry["url"] = url
        entry["url_normalized"] = normalize_url(url)
        entry["domain"] = domain_of(url)
        normalized.append(entry)

    # 3. Local filters (always labeled in the response).
    filtered = apply_local_filters(normalized, local_filters)
    filters_applied = not local_filters.is_empty()

    # 4. Dedupe, merging provider attribution.
    deduped = merge_results(filtered)

    # 5. Rank deterministically.
    ctx: RankContext = build_context(ast.nodes if ast is not None else [])
    for item in deduped:
        provider_idx = provider_order.get(item.get("provider", ""), 99)
        item["score"] = score_result(item, ctx, provider_idx)
        item["score_explain"] = explain(item, ctx, provider_idx)
    deduped.sort(key=lambda x: (-x["score"], x["url_normalized"]))

    # 6. Paginate.
    total = len(deduped)
    start = (max(1, page) - 1) * per_page
    page_items = deduped[start : start + per_page]

    return {
        "results": page_items,
        "total": total,
        "page": max(1, page),
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if per_page else 0,
        "filters_applied_locally": filters_applied,
        "dedup_removed": len(normalized) - len(deduped),
        "rank_context": {
            "keywords": ctx.keywords,
            "phrases": ctx.phrases,
            "site_domains": ctx.site_domains,
        },
    }
