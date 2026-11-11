"""Lexer for dork query strings.

Splits a raw query into tokens while respecting:
- double-quoted phrases (spaces preserved inside quotes)
- parentheses groups
- OR boolean (uppercase only, matching Google semantics)
- '-' exclusions (applied to words and quoted phrases)
- operator prefixes (site:, filetype:, intitle:, ...)

A quoted segment may appear inside a word so ``intitle:"annual report"``
is captured as a single WORD token whose operator argument is
``annual report``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

TokenType = Literal["WORD", "PHRASE", "LPAREN", "RPAREN", "OR", "AROUND"]

KNOWN_OPERATORS = {
    "site",
    "filetype",
    "ext",
    "intitle",
    "inurl",
    "intext",
    "before",
    "after",
    "related",
}

AROUND_RE = re.compile(r"^AROUND\((\d+)\)", re.IGNORECASE)


@dataclass
class Token:
    type: TokenType
    value: str  # for PHRASE: unquoted text; for WORD: raw text
    raw: str  # exactly as it appeared
    op: str | None = None  # lowercase operator prefix, e.g. "site"
    op_arg: str | None = None  # value that followed the operator prefix
    exclude: bool = False  # token was prefixed with '-'


def tokenize(query: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(query)

    while i < n:
        ch = query[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "(":
            tokens.append(Token("LPAREN", "(", "("))
            i += 1
            continue
        if ch == ")":
            tokens.append(Token("RPAREN", ")", ")"))
            i += 1
            continue

        around_match = AROUND_RE.match(query[i:])
        if around_match:
            dist = around_match.group(1)
            raw = around_match.group(0)
            tokens.append(Token("AROUND", dist, raw))
            i += len(raw)
            continue

        if ch == '"':
            value, i = _read_quoted(query, i)
            tokens.append(Token("PHRASE", value, f'"{value}"'))
            continue

        exclude = ch == "-"
        if exclude:
            i += 1
            if i < n and query[i] == '"':
                value, i = _read_quoted(query, i)
                tokens.append(Token("PHRASE", value, f'-"{value}"', exclude=True))
                continue

        # Scan one word: a run of non-space characters where quoted segments
        # may contain spaces and are consumed verbatim.
        chars: list[str] = []
        while i < n:
            c = query[i]
            if c.isspace() or c in "()":
                break
            if c == '"':
                segment, i = _read_quoted(query, i)
                chars.append(f'"{segment}"')
                continue
            chars.append(c)
            i += 1
        word = "".join(chars)
        if not word:
            if exclude:
                tokens.append(Token("WORD", "-", "-"))
            continue

        raw = f"-{word}" if exclude else word

        if not exclude:
            m = AROUND_RE.match(word)
            if m:
                tokens.append(Token("AROUND", m.group(1), word))
                continue
            if word == "OR":
                tokens.append(Token("OR", word, word))
                continue

        op: str | None = None
        op_arg: str | None = None
        if ":" in word:
            prefix, _, rest = word.partition(":")
            if prefix.lower() in KNOWN_OPERATORS:
                op = prefix.lower()
                op_arg = rest[1:].rstrip('"') if rest.startswith('"') else rest

        tokens.append(Token("WORD", word, raw, op=op, op_arg=op_arg, exclude=exclude))
    return tokens


def _read_quoted(query: str, start: int) -> tuple[str, int]:
    """Read a quoted segment beginning at ``start`` (which must point at '"').

    Returns (unquoted_value, index_after_closing_quote). An unterminated
    quote consumes the rest of the string.
    """
    end = query.find('"', start + 1)
    if end == -1:
        return query[start + 1 :], len(query)
    return query[start + 1 : end], end + 1
