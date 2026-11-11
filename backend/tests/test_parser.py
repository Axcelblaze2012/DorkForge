"""Parser, lexer and AST validation tests."""

from __future__ import annotations

from app.search.parser.nodes import Exclude, Group, Keyword, Operator, OrGroup, Phrase
from app.search.parser.parser import parse_query


def test_simple_keywords():
    ast = parse_query("open data portal")
    assert [type(n) for n in ast.nodes] == [Keyword, Keyword, Keyword]
    assert ast.to_query() == "open data portal"
    assert not ast.diagnostics


def test_operator_parsing():
    ast = parse_query("site:example.com filetype:pdf")
    ops = ast.operators()
    assert [(o.op, o.value) for o in ops] == [("site", "example.com"), ("filetype", "pdf")]


def test_quoted_phrase_preserves_spaces():
    ast = parse_query('"annual report" 2024')
    assert isinstance(ast.nodes[0], Phrase)
    assert ast.nodes[0].text == "annual report"
    assert ast.nodes[1].text == "2024"
    assert ast.to_query() == '"annual report" 2024'


def test_intitle_with_quoted_phrase():
    ast = parse_query('intitle:"annual report"')
    op = ast.nodes[0]
    assert isinstance(op, Operator)
    assert op.op == "intitle"
    assert op.value == "annual report"


def test_exclude_keyword_and_phrase():
    ast = parse_query('security -blog -"login page"')
    assert isinstance(ast.nodes[0], Keyword)
    assert isinstance(ast.nodes[1], Exclude)
    assert isinstance(ast.nodes[1].child, Keyword)
    assert ast.nodes[2].child.text == "login page"
    assert "-blog" in ast.to_query()
    assert '-"login page"' in ast.to_query()


def test_or_group():
    ast = parse_query("filetype:pdf OR filetype:doc")
    assert isinstance(ast.nodes[0], OrGroup)
    rendered = ast.to_query()
    assert "OR" in rendered


def test_parenthesised_group():
    ast = parse_query("(filetype:pdf OR filetype:doc) site:example.com")
    group = ast.nodes[0]
    assert isinstance(group, Group)
    assert len(group.children) == 2


def test_ext_alias_maps_to_filetype():
    ast = parse_query("ext:pdf")
    assert ast.operators()[0].op == "filetype"


def test_around_clause():
    ast = parse_query("security AROUND(5) training")
    node = ast.nodes[0]
    assert type(node).__name__ == "AroundClause"
    assert node.distance == 5
    assert ast.to_query() == "security AROUND(5) training"


def test_dangling_or_produces_warning_not_error():
    ast = parse_query("security OR")
    assert not ast.has_errors()
    assert any(d.code == "dangling_or" for d in ast.diagnostics)


def test_stray_paren_ignored_with_warning():
    ast = parse_query("security )")
    assert not ast.has_errors()
    assert any(d.code == "stray_paren" for d in ast.diagnostics)


def test_unclosed_group_warning():
    ast = parse_query("(filetype:pdf security")
    assert any(d.code == "unclosed_group" for d in ast.diagnostics)


def test_empty_operator_is_error():
    ast = parse_query("site:")
    assert ast.has_errors()
    assert any(d.code == "empty_operator" for d in ast.diagnostics)


def test_invalid_date_is_error():
    ast = parse_query("after:2024/01/01")
    assert ast.has_errors()


def test_valid_date_ok():
    ast = parse_query("after:2024-01-01 before:2025-01-01")
    assert not ast.has_errors()


def test_suspicious_domain_is_warning():
    ast = parse_query("site:not a domain")
    assert not ast.has_errors()
    assert any(d.code == "suspicious_domain" for d in ast.diagnostics)


def test_exclude_operator_site():
    ast = parse_query("security -site:example.com")
    node = ast.nodes[1]
    assert isinstance(node, Exclude)
    assert isinstance(node.child, Operator)
    assert node.child.op == "site"


def test_operator_names_sorted_unique():
    ast = parse_query("site:a.com inurl:admin intitle:login site:b.com")
    assert ast.operator_names() == ["intitle", "inurl", "site"]
