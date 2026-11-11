"""Structured representation (AST) of a dork query.

The parser turns raw query strings into these nodes. The builder turns
composer form state into these nodes. Providers translate these nodes into
their own query syntax. Nothing relies on naive string concatenation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Literal, Union

OperatorName = Literal[
    "site",
    "filetype",
    "intitle",
    "inurl",
    "intext",
    "before",
    "after",
    "related",
    "around",
]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)([a-z0-9-]{1,63}\.)+[a-z]{2,63}$", re.IGNORECASE
)
FILETYPE_RE = re.compile(r"^[a-z0-9]{1,10}$", re.IGNORECASE)


@dataclass
class Diagnostic:
    """A non-fatal problem or notice produced while parsing or validating."""

    level: Literal["info", "warning", "error"]
    code: str
    message: str

    def to_dict(self) -> dict:
        return {"level": self.level, "code": self.code, "message": self.message}


@dataclass
class Node:
    """Base AST node."""

    def to_dict(self) -> dict:
        raise NotImplementedError

    def to_query(self) -> str:
        """Render back to a provider-agnostic query string."""
        raise NotImplementedError


@dataclass
class Keyword(Node):
    text: str

    def to_dict(self) -> dict:
        return {"type": "keyword", "text": self.text}

    def to_query(self) -> str:
        return self.text


@dataclass
class Phrase(Node):
    """A quoted phrase, e.g. \"annual report\"."""

    text: str

    def to_dict(self) -> dict:
        return {"type": "phrase", "text": self.text}

    def to_query(self) -> str:
        escaped = self.text.replace('"', "")
        return f'"{escaped}"'


@dataclass
class Group(Node):
    """Parenthesised group of alternatives, e.g. (filetype:pdf OR filetype:doc)."""

    children: list[Node] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"type": "group", "children": [c.to_dict() for c in self.children]}

    def to_query(self) -> str:
        return "(" + " OR ".join(c.to_query() for c in self.children) + ")"


@dataclass
class OrGroup(Node):
    """Top-level OR between alternatives."""

    alternatives: list[Node] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"type": "or", "alternatives": [a.to_dict() for a in self.alternatives]}

    def to_query(self) -> str:
        return " OR ".join(a.to_query() for a in self.alternatives)


@dataclass
class Exclude(Node):
    """Exclusion, e.g. -inurl:blog or -\"login page\"."""

    child: Node

    def to_dict(self) -> dict:
        return {"type": "exclude", "child": self.child.to_dict()}

    def to_query(self) -> str:
        rendered = self.child.to_query()
        if isinstance(self.child, Phrase) or isinstance(self.child, Group):
            return f"-{rendered}"
        return f"-{rendered.replace(' ', '')}"


@dataclass
class Operator(Node):
    """A typed search operator such as site:example.com."""

    op: OperatorName
    value: str

    def to_dict(self) -> dict:
        return {"type": "operator", "op": self.op, "value": self.value}

    def to_query(self) -> str:
        if self.op == "around":
            return f"AROUND({self.value})"
        if self.op in ("before", "after"):
            return f"{self.op}:{self.value}"
        if " " in self.value or '"' in self.value:
            escaped = self.value.replace('"', "")
            return f'{self.op}:"{escaped}"'
        return f"{self.op}:{self.value}"


@dataclass
class AroundClause(Node):
    """Proximity operator: term AROUND(n) term."""

    left: Node
    right: Node
    distance: int

    def to_dict(self) -> dict:
        return {
            "type": "around",
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "distance": self.distance,
        }

    def to_query(self) -> str:
        return f"{self.left.to_query()} AROUND({self.distance}) {self.right.to_query()}"


@dataclass
class QueryAST:
    """Root container with diagnostics."""

    nodes: list[Node] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }

    def to_query(self) -> str:
        return " ".join(n.to_query() for n in self.nodes)

    def operators(self) -> list[Operator]:
        return [n for n in self.walk() if isinstance(n, Operator)]

    def operator_names(self) -> list[str]:
        return sorted({op.op for op in self.operators()})

    def walk(self) -> list[Node]:
        out: list[Node] = []

        def visit(node: Node) -> None:
            out.append(node)
            if isinstance(node, Exclude):
                visit(node.child)
            elif isinstance(node, AroundClause):
                visit(node.left)
                visit(node.right)
            elif isinstance(node, (Group, OrGroup)):
                kids = node.children if isinstance(node, Group) else node.alternatives
                for child in kids:
                    visit(child)

        for n in self.nodes:
            visit(n)
        return out

    def has_errors(self) -> bool:
        return any(d.level == "error" for d in self.diagnostics)


def ast_to_json(ast: QueryAST) -> str:
    return json.dumps(ast.to_dict(), ensure_ascii=False)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_ast(ast: QueryAST) -> list[Diagnostic]:
    """Validate operator values; append diagnostics for problems."""
    diagnostics: list[Diagnostic] = []
    for node in ast.walk():
        if not isinstance(node, Operator):
            continue
        value = node.value.strip()
        if node.op in ("before", "after"):
            if not DATE_RE.match(value):
                diagnostics.append(
                    Diagnostic(
                        "error",
                        "invalid_date",
                        f"{node.op}:{value} must use YYYY-MM-DD format.",
                    )
                )
        elif node.op in ("site", "related"):
            host = value.lstrip("*.") if node.op == "site" else value
            if not HOSTNAME_RE.match(host):
                diagnostics.append(
                    Diagnostic(
                        "warning",
                        "suspicious_domain",
                        f"{node.op}:{value} does not look like a valid domain name.",
                    )
                )
        elif node.op == "filetype":
            if not FILETYPE_RE.match(value):
                diagnostics.append(
                    Diagnostic(
                        "warning",
                        "suspicious_filetype",
                        f"filetype:{value} is not a typical file extension.",
                    )
                )
        elif node.op == "around" and node.value and not value.isdigit():
            diagnostics.append(
                Diagnostic(
                    "warning",
                    "invalid_around",
                    f"AROUND({value}) expects a small integer distance.",
                )
            )
        elif node.op in ("intitle", "inurl", "intext") and not value:
            diagnostics.append(
                Diagnostic(
                    "error",
                    "empty_operator",
                    f"Operator {node.op}: is missing its value.",
                )
            )
    # Extremely long queries are usually a mistake or abuse.
    rendered = ast.to_query()
    if len(rendered) > 900:
        diagnostics.append(
            Diagnostic(
                "warning",
                "query_too_long",
                "Query exceeds 900 characters; providers may truncate or reject it.",
            )
        )
    return diagnostics


NodeT = Union[
    Keyword, Phrase, Group, OrGroup, Exclude, Operator, AroundClause
]
