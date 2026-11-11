"""Explainable, deterministic ranking for normalized search results.

Score components (all documented and unit-tested):
  - term coverage in title / url / snippet (0..1 each, weighted)
  - exact phrase bonus when every phrase appears in title or snippet
  - domain/site match bonus when a site: constraint matches the result host
  - freshness bonus for results with a published date
  - small provider-order weight so the primary provider leads ties
Scores are floats >= 0; identical inputs always produce identical scores.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

WEIGHTS = {
    "title": 0.40,
    "snippet": 0.25,
    "url": 0.10,
    "phrase": 0.15,
    "domain": 0.10,
    "freshness": 0.05,
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def _terms(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


@dataclass
class RankContext:
    keywords: list[str]
    phrases: list[str]
    site_domains: list[str]
    excluded_domains: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.excluded_domains is None:
            self.excluded_domains = []


def build_context(ast_nodes: list[Any]) -> RankContext:
    from ..parser.nodes import Exclude, Keyword, Operator, Phrase

    keywords: list[str] = []
    phrases: list[str] = []
    domains: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, Keyword):
            keywords.extend(_terms(node.text))
        elif isinstance(node, Phrase):
            phrases.append(node.text.lower())
        elif isinstance(node, Operator):
            if node.op == "site":
                domains.append(node.value.lower().lstrip("*."))
            elif node.op == "intitle":
                keywords.extend(_terms(node.value))
            elif node.op in ("inurl", "intext"):
                keywords.extend(_terms(node.value))
        elif isinstance(node, Exclude):
            visit(node.child)
        elif hasattr(node, "children"):
            for c in node.children:
                visit(c)
        elif hasattr(node, "alternatives"):
            for c in node.alternatives:
                visit(c)
        elif hasattr(node, "left"):
            visit(node.left)
            visit(node.right)

    for n in ast_nodes:
        visit(n)
    return RankContext(keywords=keywords, phrases=phrases, site_domains=domains)


def _coverage(haystack_terms: list[str], needles: list[str]) -> float:
    if not needles:
        return 0.0
    present = sum(1 for n in needles if n in haystack_terms)
    return present / len(needles)


def _phrase_hit(phrases: list[str], title: str, snippet: str) -> bool:
    if not phrases:
        return False
    combined = f"{title} \n {snippet}".lower()
    return all(p in combined for p in phrases)


def _domain_match(site_domains: list[str], host: str) -> bool:
    if not site_domains:
        return False
    host = host.lower()
    for dom in site_domains:
        dom = dom.lower().lstrip("*.").lstrip(".")
        if not dom:
            continue
        if host == dom or host.endswith("." + dom):
            return True
    return False


def _freshness_bonus(published: str | None) -> float:
    if not published:
        return 0.0
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", published):
            dt = date.fromisoformat(published[:10])
        else:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00")).date()
        days = (date.today() - dt).days
    except (ValueError, TypeError):
        return 0.0
    if days < 0:
        return 0.0
    if days <= 30:
        return 1.0
    if days <= 180:
        return 0.6
    if days <= 730:
        return 0.3
    return 0.0


def score_result(result: dict[str, Any], ctx: RankContext, provider_weight: float) -> float:
    title = result.get("title") or ""
    snippet = result.get("snippet") or ""
    url = result.get("url") or ""
    host = (result.get("domain") or "").lower()

    title_t = _terms(title)
    snippet_t = _terms(snippet)
    url_t = _terms(url)

    s_title = _coverage(title_t, ctx.keywords)
    s_snippet = _coverage(snippet_t, ctx.keywords)
    s_url = _coverage(url_t, ctx.keywords)
    s_phrase = 1.0 if _phrase_hit(ctx.phrases, title, snippet) else 0.0
    s_domain = 1.0 if _domain_match(ctx.site_domains, host) else 0.0
    s_fresh = _freshness_bonus(result.get("published_date"))

    score = (
        WEIGHTS["title"] * s_title
        + WEIGHTS["snippet"] * s_snippet
        + WEIGHTS["url"] * s_url
        + WEIGHTS["phrase"] * s_phrase
        + WEIGHTS["domain"] * s_domain
        + WEIGHTS["freshness"] * s_fresh
    )
    # Provider weight: tiny, deterministic tiebreaker (0..0.05).
    score += 0.05 * math.exp(-4 * max(0.0, provider_weight))
    return round(score, 6)


def explain(result: dict[str, Any], ctx: RankContext, provider_weight: float) -> dict[str, Any]:
    title_t = _terms(result.get("title") or "")
    snippet_t = _terms(result.get("snippet") or "")
    url_t = _terms(result.get("url") or "")
    host = (result.get("domain") or "").lower()
    return {
        "title_coverage": round(_coverage(title_t, ctx.keywords), 3),
        "snippet_coverage": round(_coverage(snippet_t, ctx.keywords), 3),
        "url_coverage": round(_coverage(url_t, ctx.keywords), 3),
        "phrase_match": _phrase_hit(ctx.phrases, result.get("title") or "", result.get("snippet") or ""),
        "domain_match": _domain_match(ctx.site_domains, host),
        "freshness": round(_freshness_bonus(result.get("published_date")), 3),
        "provider_weight": round(0.05 * math.exp(-4 * max(0.0, provider_weight)), 6),
    }
