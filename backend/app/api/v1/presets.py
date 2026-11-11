"""Preset library endpoints (built-in + custom, favorites, import/export)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_api_key
from app.models import AuditEvent, PresetFavorite, QueryPreset
from app.schemas import PresetCreate, PresetListResponse, PresetOut, PresetUpdate
from app.services.seeder import CATEGORIES

router = APIRouter(prefix="/presets", tags=["presets"])


def _slugify(title: str, salt: str = "") -> str:
    import re

    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    suffix = salt or str(datetime.now(UTC).microsecond)
    return f"c-{base[:60]}-{suffix}"[:80]


async def _favorite_ids(session: AsyncSession) -> set[int]:
    rows = await session.execute(select(PresetFavorite.preset_id))
    return set(rows.scalars().all())


def _to_out(preset: QueryPreset, favorites: set[int]) -> PresetOut:
    return PresetOut(
        id=preset.id,
        slug=preset.slug,
        title=preset.title,
        description=preset.description,
        query=preset.query,
        category=preset.category,
        scope=preset.scope,
        tags=list(preset.tags or []),
        source=preset.source,
        legacy_id=preset.legacy_id,
        version=preset.version,
        favorite=preset.id in favorites,
    )


@router.get("", response_model=PresetListResponse)
async def list_presets(
    view: str = Query("all", pattern="^(all|favorites|custom|builtin)$"),
    category: str = Query("", max_length=60),
    q: str = Query("", max_length=120),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> PresetListResponse:
    stmt = select(QueryPreset)
    if view == "favorites":
        fav_ids = await _favorite_ids(session)
        stmt = stmt.where(QueryPreset.id.in_(fav_ids) if fav_ids else QueryPreset.id == -1)
    elif view == "custom":
        stmt = stmt.where(QueryPreset.source == "custom")
    elif view == "builtin":
        stmt = stmt.where(QueryPreset.source == "builtin")
    if category and category != "All":
        stmt = stmt.where(QueryPreset.category == category)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(QueryPreset.title).like(like),
                func.lower(QueryPreset.description).like(like),
                func.lower(QueryPreset.query).like(like),
                func.lower(QueryPreset.category).like(like),
            )
        )
    stmt = stmt.order_by(QueryPreset.source.desc(), QueryPreset.id)
    rows = (await session.execute(stmt.limit(limit).offset(offset))).scalars().all()
    total = (
        await session.execute(select(func.count()).select_from(QueryPreset))
    ).scalar_one()
    favorites = await _favorite_ids(session)
    counts = dict(
        (
            await session.execute(
                select(QueryPreset.category, func.count()).group_by(QueryPreset.category)
            )
        ).all()
    )
    return PresetListResponse(
        presets=[_to_out(r, favorites) for r in rows],
        total=total,
        categories={c: counts.get(c, 0) for c in CATEGORIES},
    )


@router.post("", response_model=PresetOut, status_code=201)
async def create_preset(
    body: PresetCreate,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> PresetOut:
    existing = (
        await session.execute(
            select(QueryPreset).where(
                func.lower(QueryPreset.title) == body.title.lower(),
                QueryPreset.source == "custom",
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "A custom preset with this title already exists")
    preset = QueryPreset(
        slug=_slugify(body.title),
        title=body.title,
        description=body.description,
        query=body.query,
        category=body.category if body.category in CATEGORIES else "Site Discovery",
        scope=body.scope,
        tags=body.tags,
        source="custom",
    )
    session.add(preset)
    await session.flush()
    session.add(
        AuditEvent(action="preset.create", detail={"id": preset.id, "title": preset.title})
    )
    return _to_out(preset, await _favorite_ids(session))


@router.get("/{preset_id}", response_model=PresetOut)
async def get_preset(
    preset_id: int,
    session: AsyncSession = Depends(get_db),
) -> PresetOut:
    preset = await session.get(QueryPreset, preset_id)
    if preset is None:
        raise HTTPException(404, "Preset not found")
    return _to_out(preset, await _favorite_ids(session))


@router.patch("/{preset_id}", response_model=PresetOut)
async def update_preset(
    preset_id: int,
    body: PresetUpdate,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> PresetOut:
    preset = await session.get(QueryPreset, preset_id)
    if preset is None:
        raise HTTPException(404, "Preset not found")
    if preset.source == "builtin":
        raise HTTPException(403, "Built-in presets cannot be edited; duplicate it instead")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(preset, key, value)
    preset.version += 1
    await session.flush()
    return _to_out(preset, await _favorite_ids(session))


@router.delete("/{preset_id}", status_code=204)
async def delete_preset(
    preset_id: int,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> None:
    preset = await session.get(QueryPreset, preset_id)
    if preset is None:
        raise HTTPException(404, "Preset not found")
    if preset.source == "builtin":
        raise HTTPException(403, "Built-in presets cannot be deleted")
    session.add(
        AuditEvent(action="preset.delete", detail={"id": preset_id, "title": preset.title})
    )
    await session.execute(delete(PresetFavorite).where(PresetFavorite.preset_id == preset_id))
    await session.delete(preset)


@router.post("/{preset_id}/favorite", response_model=PresetOut)
async def toggle_favorite(
    preset_id: int,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> PresetOut:
    preset = await session.get(QueryPreset, preset_id)
    if preset is None:
        raise HTTPException(404, "Preset not found")
    existing = (
        await session.execute(
            select(PresetFavorite).where(PresetFavorite.preset_id == preset_id)
        )
    ).scalar_one_or_none()
    if existing:
        await session.delete(existing)
    else:
        session.add(PresetFavorite(preset_id=preset_id))
    await session.flush()
    return _to_out(preset, await _favorite_ids(session))


@router.post("/duplicate", response_model=PresetOut, status_code=201)
async def duplicate_preset(
    preset_id: int,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> PresetOut:
    """Duplicate a preset (e.g. a built-in) into an editable custom copy."""
    source = await session.get(QueryPreset, preset_id)
    if source is None:
        raise HTTPException(404, "Preset not found")
    copy = QueryPreset(
        slug=_slugify(f"{source.title}-copy"),
        title=f"{source.title} (copy)"[:120],
        description=source.description,
        query=source.query,
        category=source.category,
        scope=source.scope,
        tags=list(source.tags or []),
        source="custom",
    )
    session.add(copy)
    await session.flush()
    return _to_out(copy, await _favorite_ids(session))


@router.get("/export")
async def export_presets(
    include_builtin: bool = False,
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Export presets as JSON (custom by default)."""
    stmt = select(QueryPreset)
    if not include_builtin:
        stmt = stmt.where(QueryPreset.source == "custom")
    rows = (await session.execute(stmt)).scalars().all()
    favorites = await _favorite_ids(session)
    payload = json.dumps(
        {
            "format": "dork-atlas-presets-v1",
            "exported_at": datetime.now(UTC).isoformat(),
            "presets": [
                {
                    "title": p.title,
                    "description": p.description,
                    "query": p.query,
                    "category": p.category,
                    "scope": p.scope,
                    "tags": list(p.tags or []),
                    "source": p.source,
                    "legacy_id": p.legacy_id,
                    "favorite": p.id in favorites,
                }
                for p in rows
            ],
        },
        ensure_ascii=False,
        indent=2,
    )
    return Response(
        content=payload,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="dork-atlas-presets.json"'},
    )


@router.post("/import", status_code=201)
async def import_presets(
    payload: dict,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> dict:
    """Import presets from a dork-atlas-presets-v1 JSON payload."""
    if payload.get("format") != "dork-atlas-presets-v1":
        raise HTTPException(422, "Unrecognised import format; expected dork-atlas-presets-v1")
    items = payload.get("presets") or []
    if not isinstance(items, list) or len(items) > 500:
        raise HTTPException(422, "Invalid presets payload")
    existing_slugs = set(
        (await session.execute(select(QueryPreset.slug))).scalars().all()
    )
    existing_titles = {
        t.lower()
        for t in (
            await session.execute(
                select(QueryPreset.title).where(QueryPreset.source == "custom")
            )
        ).scalars().all()
    }
    imported, skipped = 0, 0
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            skipped += 1
            continue
        title = str(item.get("title") or "").strip()[:120]
        query = str(item.get("query") or "").strip()[:500]
        if not title or not query:
            skipped += 1
            continue
        if title.lower() in existing_titles:
            skipped += 1
            continue
        category = str(item.get("category") or "Site Discovery")
        preset = QueryPreset(
            slug=_slugify(title, str(i)),
            title=title,
            description=str(item.get("description") or "")[:500],
            query=query,
            category=category if category in CATEGORIES else "Site Discovery",
            scope="Scoped" if item.get("scope") == "Scoped" else "General",
            tags=[str(t)[:40] for t in (item.get("tags") or [])][:12],
            source="custom",
            legacy_id=str(item.get("legacy_id") or "")[:40] or None,
        )
        session.add(preset)
        existing_slugs.add(preset.slug)
        existing_titles.add(title.lower())
        imported += 1
    await session.flush()
    session.add(AuditEvent(action="preset.import", detail={"imported": imported, "skipped": skipped}))
    return {"imported": imported, "skipped": skipped}
