"""Provider operator compatibility engine.

Providers understand different subsets of the query language. This module
records, per provider kind, whether each operator is:
  - native:      sent to the provider as-is
  - translated:  converted into a provider parameter or equivalent syntax
  - dropped:     not supported; removed from the provider query WITH an
                 explicit warning (never silently)
  - local:       applied locally to results (filters)

The matrix is deliberately conservative: we only claim what each adapter
actually implements in code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Support = Literal["native", "translated", "local", "dropped"]

OPERATORS = [
    "site",
    "filetype",
    "intitle",
    "inurl",
    "intext",
    "before",
    "after",
    "related",
    "around",
    "or",
    "phrase",
    "exclude",
]

PROVIDER_KINDS = ["searxng", "brave", "local_index"]


@dataclass(frozen=True)
class OperatorSupport:
    support: Support
    note: str = ""


# --- SearXNG ---------------------------------------------------------------
# SearXNG forwards the query string to its configured engines. Google-family
# operators pass through when Google-class engines are enabled; generic
# engines (ddg, wikipedia, ...) apply what they understand. We keep the
# operators in the query and label engine-dependent ones as "translated"
# with a caveat, because SearXNG also exposes native parameters (language,
# time_range) we can use instead.
SEARXNG: dict[str, OperatorSupport] = {
    "site": OperatorSupport("native"),
    "filetype": OperatorSupport("native", "Honoured by Google/Brave-class engines."),
    "intitle": OperatorSupport("native", "Engine-dependent; supported by Google engine."),
    "inurl": OperatorSupport("native", "Engine-dependent; supported by Google engine."),
    "intext": OperatorSupport("native", "Engine-dependent."),
    "before": OperatorSupport("translated", "Absolute dates kept in query text."),
    "after": OperatorSupport(
        "translated", "Relative windows map to SearXNG time_range when possible."
    ),
    "related": OperatorSupport("native", "Google engine only."),
    "around": OperatorSupport("native", "Google engine only."),
    "or": OperatorSupport("native"),
    "phrase": OperatorSupport("native"),
    "exclude": OperatorSupport("native"),
}

# --- Brave Search API -------------------------------------------------------
# Brave documents: site:, -site:, +/-term, filetype:, ext:, intitle:, lang:.
# intitle: is documented; inurl:/related:/AROUND are not; OR is not
# documented as a boolean operator. Unsupported operators are dropped with
# warnings and, where possible, applied as local post-filters instead.
BRAVE: dict[str, OperatorSupport] = {
    "site": OperatorSupport("native"),
    "filetype": OperatorSupport("native", "Brave also exposes ext: as an alias."),
    "intitle": OperatorSupport("native"),
    "inurl": OperatorSupport("dropped", "Kept as plain keywords; results locally filtered."),
    "intext": OperatorSupport("dropped", "Kept as plain keywords."),
    "before": OperatorSupport("translated", "Mapped to Brave freshness parameter."),
    "after": OperatorSupport("translated", "Mapped to Brave freshness parameter."),
    "related": OperatorSupport("dropped", "Brave has no related-sites operator."),
    "around": OperatorSupport("dropped", "Proximity is not supported."),
    "or": OperatorSupport("dropped", "Brave does not document OR grouping."),
    "phrase": OperatorSupport("native"),
    "exclude": OperatorSupport("native"),
}

# --- Local Dork Atlas index -------------------------------------------------
# The local index (Phase 6) applies every constraint as a structured filter.
LOCAL_INDEX: dict[str, OperatorSupport] = {
    "site": OperatorSupport("local"),
    "filetype": OperatorSupport("local"),
    "intitle": OperatorSupport("local"),
    "inurl": OperatorSupport("local"),
    "intext": OperatorSupport("local"),
    "before": OperatorSupport("local"),
    "after": OperatorSupport("local"),
    "related": OperatorSupport("dropped", "Not computed by the local index."),
    "around": OperatorSupport("dropped", "Proximity is not supported."),
    "or": OperatorSupport("local"),
    "phrase": OperatorSupport("local"),
    "exclude": OperatorSupport("local"),
}

MATRIX: dict[str, dict[str, OperatorSupport]] = {
    "searxng": SEARXNG,
    "brave": BRAVE,
    "local_index": LOCAL_INDEX,
}


def support_for(provider_kind: str, operator: str) -> OperatorSupport:
    table = MATRIX.get(provider_kind, {})
    return table.get(operator, OperatorSupport("dropped", "Unknown operator for this provider."))


def matrix_for(provider_kind: str) -> dict[str, dict[str, str]]:
    table = MATRIX.get(provider_kind, {})
    return {
        op: {"support": s.support, "note": s.note} for op, s in table.items()
    }


def full_matrix() -> dict[str, dict[str, dict[str, str]]]:
    return {kind: matrix_for(kind) for kind in PROVIDER_KINDS}
