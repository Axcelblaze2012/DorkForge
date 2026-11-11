"""Search history endpoints: list, delete, clear, export."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_api_key
from app.models import SearchHistory
from app.schemas import HistoryCreate, HistoryListResponse, HistoryOut

router = APIRouter(prefix="/search/history", tags=["history"])


def _to_out(entry: SearchHistory) -> HistoryOut:
    return HistoryOut(
        id=entry.id,
        query=entry.query,
        mode=entry.mode,
        operators=list(entry.parsed_operators or []),
        providers_used=list(entry.providers_used or []),
        provider_statuses=list(entry.provider_statuses or []),
        result_count=entry.result_count,
        status=entry.status,
        duration_ms=entry.duration_ms,
        cached=bool(entry.cached),
        created_at=entry.created_at.isoformat(),
    )


@router.get("", response_model=HistoryListResponse)
async def list_history(
    q: str = Query(default="", max_length=200),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> HistoryListResponse:
    stmt = select(SearchHistory).order_by(SearchHistory.id.desc())
    count_stmt = select(func.count()).select_from(SearchHistory)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(func.lower(SearchHistory.query).like(like))
        count_stmt = count_stmt.where(func.lower(SearchHistory.query).like(like))
    total = (await session.execute(count_stmt)).scalar_one()
    rows = (await session.execute(stmt.limit(limit).offset(offset))).scalars().all()
    return HistoryListResponse(items=[_to_out(r) for r in rows], total=total)


@router.post("", response_model=HistoryOut, status_code=201)
async def create_history_entry(
    body: HistoryCreate,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> HistoryOut:
    from app.search.parser.parser import parse_query

    ast = parse_query(body.query)
    entry = SearchHistory(
        query=body.query[:1000],
        mode=body.mode,
        parsed_operators=ast.operator_names(),
        providers_used=body.providers_used,
        provider_statuses=[],
        result_count=body.result_count,
        duration_ms=body.duration_ms,
        status=body.status,
        cached=False,
        warnings=body.warnings,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return _to_out(entry)


@router.get("/export")
async def export_history(
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Export the full history as JSON (user data portability)."""
    rows = (await session.execute(select(SearchHistory).order_by(SearchHistory.id))).scalars().all()
    import json

    payload = json.dumps(
        {
            "format": "dork-atlas-history-v1",
            "entries": [
                {
                    "query": r.query,
                    "mode": r.mode,
                    "operators": r.parsed_operators or [],
                    "providers_used": r.providers_used or [],
                    "result_count": r.result_count,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ],
        },
        ensure_ascii=False,
        indent=2,
    )
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="dork-atlas-history.json"'},
    )


@router.delete("/{history_id}", status_code=204)
async def delete_history_entry(
    history_id: int,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> None:
    row = await session.get(SearchHistory, history_id)
    if row is None:
        raise HTTPException(404, "History entry not found")
    await session.delete(row)


@router.delete("", status_code=204)
async def clear_history(
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> None:
    await session.execute(delete(SearchHistory))
