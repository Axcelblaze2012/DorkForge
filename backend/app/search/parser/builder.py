"""Build a QueryAST (and query string) from structured composer fields.

This mirrors the original Dork Atlas composer fields:
search terms, domain, filetype, title term, URL term, exact phrase,
excluded terms, and date range. It lives on the backend so the frontend
and the API share one canonical builder, and so tests cover the exact
query output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from .nodes import (
    AroundClause,
    Diagnostic,
    Exclude,
    Keyword,
    Node,
    Operator,
    OrGroup,
    Phrase,
    QueryAST,
    validate_ast,
)

_DOMAIN_CLEAN_RE = re.compile(r"\s+")
_SCHEMA_RE = re.compile(r"^https?://", re.IGNORECASE)
_WWW_RE = re.compile(r"^www\.", re.IGNORECASE)

RELATIVE_RANGES = {"d", "w", "m", "y"}


@dataclass
class ComposerFields:
    """Composer form state (subset of the original HTML app)."""

    terms: str = ""
    domain: str = ""
    filetype: str = ""
    title_term: str = ""
    url_term: str = ""
    exact_phrase: str = ""
    exclude_terms: str = ""
    time_range: str = ""  # "", d, w, m, y
    region: str = ""  # gl country code; not part of the query string

    def any_value(self) -> bool:
        return any(
            [
                self.terms.strip(),
                self.domain.strip(),
                self.filetype.strip(),
                self.title_term.strip(),
                self.url_term.strip(),
                self.exact_phrase.strip(),
                self.exclude_terms.strip(),
            ]
        )


def clean_domain(value: str) -> str:
    """Normalise a user-provided domain (strip scheme, www, paths, spaces)."""
    v = value.strip()
    v = _SCHEMA_RE.sub("", v)
    v = _WWW_RE.sub("", v)
    v = v.split("/")[0]
    v = _DOMAIN_CLEAN_RE.sub("", v)
    return v


def resolve_template(query: str, domain: str = "example.com", topic: str = "research topic") -> str:
    """Replace {domain} and {topic} placeholders used by presets."""
    return query.replace("{domain}", domain).replace("{topic}", topic)


def _relative_date(range_code: str) -> str:
    days = {"d": 1, "w": 7, "m": 30, "y": 365}.get(range_code, 0)
    return (date.today() - timedelta(days=days)).isoformat()


def build_nodes(fields: ComposerFields, resolve_placeholders: bool = True) -> tuple[list[Node], list[Diagnostic]]:
    nodes: list[Node] = []
    diagnostics: list[Diagnostic] = []

    terms = fields.terms.strip()
    if terms:
        parsed = parse_query(terms)
        nodes.extend(parsed.nodes)
        for d in parsed.diagnostics:
            if d.code not in ("query_too_long",):
                diagnostics.append(d)

    domain = clean_domain(fields.domain)
    if domain:
        nodes.append(Operator(op="site", value=domain))

    filetype = fields.filetype.strip().lstrip(".").lower()
    if filetype:
        nodes.append(Operator(op="filetype", value=filetype))

    title = fields.title_term.strip()
    if title:
        if " " in title:
            nodes.append(Operator(op="intitle", value=title.replace('"', "")))
        else:
            nodes.append(Operator(op="intitle", value=title))

    url = fields.url_term.strip()
    if url:
        nodes.append(Operator(op="inurl", value=url.replace('"', "")))

    exact = fields.exact_phrase.strip()
    if exact:
        nodes.append(Phrase(text=exact.replace('"', "")))

    # Exclusions: split on whitespace, tolerate comma separation.
    exclusions = [t for t in re.split(r"[\s,]+", fields.exclude_terms.strip()) if t]
    for term in exclusions:
        cleaned = term.lstrip("-").replace('"', "")
        if cleaned:
            nodes.append(Exclude(child=Keyword(text=cleaned)))

    time_range = fields.time_range.strip().lower()
    if time_range in RELATIVE_RANGES:
        # Relative windows are expressed with an `after:` date constraint so
        # every provider path can translate or carry it explicitly.
        nodes.append(Operator(op="after", value=_relative_date(time_range)))

    return nodes, diagnostics


def build_query(fields: ComposerFields, resolve_placeholders: bool = True) -> QueryAST:
    nodes, diagnostics = build_nodes(fields)
    ast = QueryAST(nodes=nodes, diagnostics=diagnostics)
    ast.diagnostics.extend(validate_ast(ast))
    return ast


def build_query_string(fields: ComposerFields) -> str:
    ast = build_query(fields)
    return ast.to_query()


# Re-exports for convenient imports elsewhere.
__all__ = [
    "ComposerFields",
    "build_nodes",
    "build_query",
    "build_query_string",
    "clean_domain",
    "resolve_template",
    "AroundClause",
    "Diagnostic",
    "Exclude",
    "Keyword",
    "Node",
    "Operator",
    "OrGroup",
    "Phrase",
    "QueryAST",
]
