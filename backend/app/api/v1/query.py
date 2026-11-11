"""Query engine endpoints: parse, validate, explain, compatibility."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_api_key
from app.search.compatibility import full_matrix, matrix_for
from app.search.parser.builder import ComposerFields, build_query
from app.search.parser.parser import parse_query
from app.schemas import ComposerQueryRequest, QueryExplainResponse, QueryParseRequest

router = APIRouter(prefix="/query", tags=["query"])


def _complexity(ast) -> dict:
    node_count = len(ast.walk())
    op_count = len(ast.operators())
    phrases = sum(1 for n in ast.walk() if type(n).__name__ == "Phrase")
    ors = sum(1 for n in ast.walk() if type(n).__name__ == "OrGroup")
    score = node_count + 2 * op_count + 3 * ors
    if score == 0:
        band = "empty"
    elif score <= 5:
        band = "simple"
    elif score <= 12:
        band = "moderate"
    else:
        band = "complex"
    return {
        "nodes": node_count,
        "operators": op_count,
        "phrases": phrases,
        "or_groups": ors,
        "score": score,
        "band": band,
    }


def _explain_response(ast, raw: str) -> QueryExplainResponse:
    compatibility = {
        kind: {
            "supported": [
                op for op, s in matrix.items() if s["support"] in ("native", "translated", "local")
            ],
            "partial": [op for op, s in matrix.items() if s["support"] == "translated"],
            "unsupported": [op for op, s in matrix.items() if s["support"] == "dropped"],
        }
        for kind, matrix in full_matrix().items()
    }
    return QueryExplainResponse(
        query=raw,
        rendered_query=ast.to_query(),
        ast=ast.to_dict(),
        operators=ast.operator_names(),
        diagnostics=[d.to_dict() for d in ast.diagnostics],
        complexity=_complexity(ast),
        compatibility=compatibility,
    )


@router.post("/parse")
async def parse_endpoint(
    body: QueryParseRequest, _: None = Depends(require_api_key)
) -> dict:
    ast = parse_query(body.query)
    return {"query": body.query, **ast.to_dict(), "operators": ast.operator_names()}


@router.post("/validate")
async def validate_endpoint(
    body: QueryParseRequest, _: None = Depends(require_api_key)
) -> dict:
    ast = parse_query(body.query)
    return {
        "valid": not any(d.level == "error" for d in ast.diagnostics),
        "errors": [d.to_dict() for d in ast.diagnostics if d.level == "error"],
        "warnings": [d.to_dict() for d in ast.diagnostics if d.level == "warning"],
        "rendered_query": ast.to_query(),
    }


@router.post("/explain", response_model=QueryExplainResponse)
async def explain_endpoint(
    body: QueryParseRequest, _: None = Depends(require_api_key)
) -> QueryExplainResponse:
    ast = parse_query(body.query)
    return _explain_response(ast, body.query)


@router.post("/composer/preview")
async def composer_preview(
    body: ComposerQueryRequest, _: None = Depends(require_api_key)
) -> dict:
    """Render the canonical query string from composer fields (live preview)."""
    ast = build_query(
        ComposerFields(
            terms=body.terms,
            domain=body.domain,
            filetype=body.filetype,
            title_term=body.title_term,
            url_term=body.url_term,
            exact_phrase=body.exact_phrase,
            exclude_terms=body.exclude_terms,
            time_range=body.time_range,
            region=body.region,
        )
    )
    return {
        "query": ast.to_query(),
        "operators": ast.operator_names(),
        "diagnostics": [d.to_dict() for d in ast.diagnostics],
        "compatibility": {kind: matrix_for(kind) for kind in ("searxng", "brave")},
    }
