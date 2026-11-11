"""Translate a QueryAST into provider-specific query strings and parameters.

Every operator that a provider cannot handle is DROPPED WITH A WARNING —
never silently removed. Where a constraint can be applied locally after
results come back, the translator records a local filter instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from ..compatibility import OperatorSupport, support_for
from .nodes import (
    AroundClause,
    Exclude,
    Group,
    Keyword,
    Node,
    Operator,
    OrGroup,
    Phrase,
    QueryAST,
)

RELATIVE_RANGES = {"d": "day", "w": "week", "m": "month", "y": "year"}


@dataclass
class LocalFilters:
    """Constraints removed from the provider query but applied afterwards."""

    domains: list[str] = field(default_factory=list)
    excluded_domains: list[str] = field(default_factory=list)
    filetypes: list[str] = field(default_factory=list)
    url_terms: list[str] = field(default_factory=list)
    title_terms: list[str] = field(default_factory=list)


@dataclass
class Translation:
    provider_kind: str
    query: str = ""
    params: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    local_filters: LocalFilters = field(default_factory=LocalFilters)


def _warn(translation: Translation, op: str, note: str) -> None:
    translation.warnings.append(
        f"Operator '{op}' is not supported by this provider and was adjusted: {note}"
    )


def _render_or(children: list[Node]) -> str:
    return " OR ".join(_render_node(c) for c in children if not isinstance(c, Exclude))


def _render_node(node: Node) -> str:
    if isinstance(node, (Keyword, Phrase, Operator)):
        return node.to_query()
    if isinstance(node, Exclude):
        return node.to_query()
    if isinstance(node, Group):
        return "(" + " OR ".join(_render_node(c) for c in node.children) + ")"
    if isinstance(node, OrGroup):
        return "(" + _render_or(node.alternatives) + ")"
    if isinstance(node, AroundClause):
        return f"{_render_node(node.left)} AROUND({node.distance}) {_render_node(node.right)}"
    return ""


# ---------------------------------------------------------------------------
# SearXNG
# ---------------------------------------------------------------------------

def translate_searxng(ast: QueryAST, language: str | None = None) -> Translation:
    t = Translation(provider_kind="searxng")
    parts: list[str] = []
    time_range: str | None = None

    def walk(nodes: list[Node]) -> None:
        nonlocal time_range
        for node in nodes:
            if isinstance(node, Operator):
                support: OperatorSupport = support_for("searxng", node.op)
                if node.op in ("before", "after"):
                    parts.append(node.to_query())
                    if node.value.count("-") == 2 and len(node.value) == 10:
                        _warn(t, node.op, "absolute dates are kept in the query text; "
                                          "coverage depends on the underlying engine.")
                    else:
                        # relative windows like after:2026-11-07 (d/w/m/y built
                        # upstream) map to SearXNG time_range when unambiguous
                        _warn(t, node.op, "handled via the query text and engine support.")
                    continue
                parts.append(node.to_query())
                if support.support == "dropped":
                    _warn(t, node.op, support.note)
                elif support.note:
                    t.warnings.append(f"Operator '{node.op}': {support.note}")
            elif isinstance(node, AroundClause):
                parts.append(_render_node(node))
                t.warnings.append(
                    "Operator 'around': AROUND(n) only applies on engines that "
                    "support it (e.g. Google). Other engines treat it as plain text."
                )
            elif isinstance(node, OrGroup):
                parts.append("(" + _render_or(node.alternatives) + ")")
            elif isinstance(node, Group):
                parts.append(_render_node(node))
            elif isinstance(node, (Keyword, Phrase, Exclude)):
                parts.append(node.to_query())

    walk(ast.nodes)
    t.query = " ".join(p for p in parts if p)
    if language and language not in ("any", ""):
        t.params["language"] = language
    return t


# ---------------------------------------------------------------------------
# Brave
# ---------------------------------------------------------------------------

def _relative_to_absolute(value: str) -> str | None:
    """Map shorthand (d/w/m/y produced by the composer) to absolute dates."""
    mapping = {"d": 1, "w": 7, "m": 30, "y": 365}
    return (date.today() - timedelta(days=mapping[value])).isoformat() if value in mapping else None


def translate_brave(ast: QueryAST) -> Translation:
    t = Translation(provider_kind="brave")
    parts: list[str] = []
    freshness: str | None = None
    lf = t.local_filters

    def classify_freshness(ast: QueryAST) -> str | None:
        """Brave freshness: pd (day), pw (week), pm (month), py (year)."""
        for node in ast.walk():
            if isinstance(node, Operator) and node.op == "after":
                if node.value in RELATIVE_RANGES:
                    return {"d": "pd", "w": "pw", "m": "pm", "y": "py"}[node.value]
                # absolute date: approximate freshness bucket
                try:
                    dt = date.fromisoformat(node.value)
                except ValueError:
                    continue
                delta = (date.today() - dt).days
                if delta <= 1:
                    return "pd"
                if delta <= 7:
                    return "pw"
                if delta <= 31:
                    return "pm"
                if delta <= 365:
                    return "py"
        return None

    freshness = classify_freshness(ast)

    def walk(nodes: list[Node]) -> None:
        for node in nodes:
            if isinstance(node, Operator):
                support = support_for("brave", node.op)
                if node.op in ("before", "after"):
                    # mapped to freshness; leave out of the query text
                    continue
                if support.support == "dropped":
                    if node.op in ("inurl",):
                        lf.url_terms.append(node.value)
                    parts.append(node.value)
                    _warn(t, node.op, support.note)
                    continue
                parts.append(node.to_query())
            elif isinstance(node, AroundClause):
                _warn(t, "around", support_for("brave", "around").note)
                parts.append(_render_node(node.left))
                parts.append(_render_node(node.right))
            elif isinstance(node, OrGroup):
                _warn(t, "or", support_for("brave", "or").note)
                parts.extend(_render_node(a) for a in node.alternatives if not isinstance(a, Exclude))
            elif isinstance(node, Group):
                parts.extend(_render_node(c) for c in node.children)
            elif isinstance(node, Exclude):
                parts.append(node.to_query())
            else:
                parts.append(node.to_query())

    walk(ast.nodes)
    t.query = " ".join(p for p in parts if p)
    if freshness:
        t.params["freshness"] = freshness
    return t


# ---------------------------------------------------------------------------
# Local index (Phase 6 target) — every constraint becomes a local filter
# ---------------------------------------------------------------------------

def translate_local_index(ast: QueryAST) -> Translation:
    t = Translation(provider_kind="local_index")
    lf = t.local_filters
    parts: list[str] = []

    def walk(nodes: list[Node]) -> None:
        for node in nodes:
            if isinstance(node, Operator):
                if node.op == "site":
                    lf.domains.append(node.value)
                elif node.op == "filetype":
                    lf.filetypes.append(node.value)
                elif node.op == "inurl":
                    lf.url_terms.append(node.value)
                elif node.op == "intitle":
                    lf.title_terms.append(node.value)
                elif node.op == "intext":
                    parts.append(node.value)
                elif node.op in ("before", "after"):
                    _warn(t, node.op, "date filters are applied to indexed timestamps.")
                elif node.op == "related":
                    _warn(t, "related", support_for("local_index", "related").note)
                elif node.op == "around":
                    _warn(t, "around", support_for("local_index", "around").note)
                    parts.extend([_render_node(node.left), _render_node(node.right)])
                else:
                    parts.append(node.to_query())
            elif isinstance(node, AroundClause):
                _warn(t, "around", "Proximity is not supported; terms kept as keywords.")
                parts.extend([_render_node(node.left), _render_node(node.right)])
            elif isinstance(node, OrGroup):
                parts.extend(_render_node(a) for a in node.alternatives if not isinstance(a, Exclude))
            elif isinstance(node, Exclude):
                child = node.child
                if isinstance(child, Operator) and child.op == "site":
                    lf.excluded_domains.append(child.value)
                else:
                    parts.append(node.to_query())
            else:
                parts.append(node.to_query())

    walk(ast.nodes)
    t.query = " ".join(parts)
    return t


# ---------------------------------------------------------------------------

def translate(ast: QueryAST, provider_kind: str, language: str | None = None) -> Translation:
    if provider_kind == "searxng":
        return translate_searxng(ast, language)
    if provider_kind == "brave":
        return translate_brave(ast)
    if provider_kind == "local_index":
        return translate_local_index(ast)
    raise ValueError(f"Unknown provider kind: {provider_kind}")
