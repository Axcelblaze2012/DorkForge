"""Recursive-descent parser turning token streams into a QueryAST.

Grammar (top to bottom):
    query       := or_expr
    or_expr     := seq (OR seq)*            -> OrGroup when >1
    seq         := around_seq*              -> list of nodes
    around_seq  := atom (AROUND(n) atom)?   -> AroundClause
    atom        := exclude | operator | phrase | word | group
    exclude     := '-' atom
    group       := '(' or_expr ')'
"""

from __future__ import annotations

from .lexer import Token, tokenize
from .nodes import (
    AroundClause,
    Diagnostic,
    Exclude,
    Group,
    Keyword,
    Node,
    Operator,
    OrGroup,
    Phrase,
    QueryAST,
    validate_ast,
)

# Operators that alias to a canonical name.
ALIASES = {"ext": "filetype"}

DATE_OPS = {"before", "after"}


def parse_query(query: str) -> QueryAST:
    """Parse a raw query string into a validated QueryAST."""
    tokens = tokenize(query or "")
    parser = _Parser(tokens)
    ast = parser.parse()
    ast.diagnostics.extend(validate_ast(ast))
    return ast


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0
        self.diagnostics: list[Diagnostic] = []

    # -- helpers ------------------------------------------------------------
    def peek(self) -> Token | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def next(self) -> Token | None:
        tok = self.peek()
        if tok is not None:
            self.pos += 1
        return tok

    # -- entry ----------------------------------------------------------------
    def parse(self) -> QueryAST:
        nodes: list[Node] = []
        if not self.tokens:
            return QueryAST(nodes=[], diagnostics=[])

        or_expr = self.parse_or()
        if or_expr is not None:
            if isinstance(or_expr, list):
                nodes.extend(or_expr)
            else:
                nodes.append(or_expr)

        # Anything unconsumed indicates malformed input (stray ')').
        while self.peek() is not None:
            tok = self.next()
            assert tok is not None
            if tok.type == "RPAREN":
                self.diagnostics.append(
                    Diagnostic("warning", "stray_paren", "Unmatched ')' was ignored.")
                )
            elif tok.type == "OR":
                self.diagnostics.append(
                    Diagnostic(
                        "warning",
                        "dangling_or",
                        "OR without a left-hand term was ignored.",
                    )
                )
            else:
                node = self.atom_from_token(tok)
                if node is not None:
                    nodes.append(node)

        return QueryAST(nodes=nodes, diagnostics=self.diagnostics)

    # -- rules ----------------------------------------------------------------
    def parse_or(self) -> Node | list[Node] | None:
        """or_expr := seq (OR seq)*"""
        alternatives: list[Node | list[Node]] = []
        first = self.parse_sequence()
        if first is None:
            return None
        alternatives.append(first)
        while self.peek() is not None and self.peek().type == "OR":  # type: ignore[union-attr]
            self.next()  # consume OR
            rhs = self.parse_sequence()
            if rhs is None or rhs == []:
                self.diagnostics.append(
                    Diagnostic(
                        "warning", "dangling_or", "OR without a right-hand term was ignored."
                    )
                )
                break
            alternatives.append(rhs)
        if len(alternatives) == 1:
            return alternatives[0]
        flat: list[Node] = []
        for alt in alternatives:
            if isinstance(alt, list):
                flat.extend(alt)
            else:
                flat.append(alt)
        return OrGroup(alternatives=flat)

    def parse_sequence(self) -> list[Node] | None:
        """seq := around_seq* — stops at OR / RPAREN."""
        nodes: list[Node] = []
        while True:
            tok = self.peek()
            if tok is None or tok.type in ("OR", "RPAREN"):
                break
            atom = self.parse_around()
            if atom is None:
                break
            nodes.append(atom)
        return nodes if nodes else None

    def parse_around(self) -> Node | None:
        """atom (AROUND(n) atom)? -> AroundClause when the operator appears."""
        left = self.parse_atom()
        if left is None:
            return None
        tok = self.peek()
        if tok is not None and tok.type == "AROUND":
            self.next()
            right = self.parse_atom()
            if right is None:
                self.diagnostics.append(
                    Diagnostic(
                        "warning",
                        "dangling_around",
                        f"AROUND({tok.value}) is missing its right-hand term; "
                        "kept both terms without proximity.",
                    )
                )
                return left
            return AroundClause(left=left, right=right, distance=int(tok.value))
        return left

    def parse_atom(self) -> Node | None:
        tok = self.next()
        if tok is None:
            return None
        if tok.type == "LPAREN":
            inner = self.parse_or()
            closing = self.peek()
            if closing is not None and closing.type == "RPAREN":
                self.next()
            else:
                self.diagnostics.append(
                    Diagnostic("warning", "unclosed_group", "Unclosed '(' group.")
                )
            if inner is None:
                return None
            if isinstance(inner, OrGroup):
                return Group(children=inner.alternatives)
            if isinstance(inner, list):
                if not inner:
                    return None
                return Group(children=inner)
            return Group(children=[inner])
        if tok.type == "RPAREN":
            # Should not normally reach here; recover by ignoring.
            return None
        return self.atom_from_token(tok)

    def atom_from_token(self, tok: Token) -> Node | None:
        node: Node
        if tok.type == "PHRASE":
            if not tok.value.strip():
                return None
            node = Phrase(text=tok.value)
        elif tok.type == "AROUND":
            self.diagnostics.append(
                Diagnostic("warning", "dangling_around", "AROUND() without operands was ignored.")
            )
            return None
        else:  # WORD
            if tok.op is not None:
                canonical = ALIASES.get(tok.op, tok.op)
                arg = (tok.op_arg or "").strip()
                if not arg:
                    self.diagnostics.append(
                        Diagnostic(
                            "error",
                            "empty_operator",
                            f"Operator {tok.op}: is missing its value.",
                        )
                    )
                    return None
                if canonical in DATE_OPS:
                    arg = arg.rstrip(":.,").lower()
                node = Operator(op=canonical, value=arg)  # type: ignore[arg-type]
            else:
                cleaned = tok.value.strip()
                if not cleaned:
                    return None
                node = Keyword(text=cleaned)
        if tok.exclude:
            return Exclude(child=node)
        return node
