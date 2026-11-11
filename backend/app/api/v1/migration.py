"""Legacy data migration: import the original Dork Atlas localStorage keys.

Legacy keys (from Dork_Atlas_Final.html):
  - dork-atlas-favorites-v1 : list of preset ids ('b0'..'b55' or 'c<ts>')
  - dork-atlas-custom-v1    : list of custom preset objects
  - dork-atlas-recent-v1    : list of {query, label, when}

Import is idempotent: a SHA-256 payload hash is stored so re-submitting the
same data is a no-op. Legacy favorites reference built-in ids via the
`legacy_id` column, which the seeder preserves ('b0'..'b55').
"""

from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_api_key
from app.models import AuditEvent, LegacyImport, PresetFavorite, QueryPreset, SearchHistory
from app.schemas import LegacyImportRequest, LegacyImportResponse
from app.services.seeder import CATEGORIES

router = APIRouter(prefix="/migration", tags=["migration"])


def _hash_payload(payload: LegacyImportRequest) -> str:
    canonical = f"{sorted(payload.favorites)}|{[ (c.get('title'), c.get('query')) for c in payload.custom ]}|{[ (r.get('query'), r.get('when')) for r in payload.recent ]}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@router.post("/legacy", response_model=LegacyImportResponse)
async def import_legacy(
    payload: LegacyImportRequest,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> LegacyImportResponse:
    payload_hash = _hash_payload(payload)

    existing = (
        await session.execute(
            select(LegacyImport).where(LegacyImport.payload_hash == payload_hash)
        )
    ).scalar_one_or_none()
    if existing:
        return LegacyImportResponse(
            favorites_imported=0,
            custom_imported=0,
            recent_imported=0,
            favorites_skipped=0,
            custom_skipped=0,
            already_imported=True,
            message="This legacy payload was already imported; nothing was duplicated.",
        )

    favorites_skipped = 0
    custom_skipped = 0
    favorites_imported = 0
    custom_imported = 0
    recent_imported = 0

    # --- Favorites ---------------------------------------------------------
    if payload.favorites:
        builtins = {
            r.legacy_id: r.id
            for r in (
                await session.execute(
                    select(QueryPreset).where(QueryPreset.legacy_id.isnot(None))
                )
            )
            .scalars()
            .all()
        }
        existing_favs = set(
            (await session.execute(select(PresetFavorite.preset_id))).scalars().all()
        )
        for legacy_id in payload.favorites:
            target = builtins.get(legacy_id)
            if target is None or target in existing_favs:
                favorites_skipped += 1
                continue
            session.add(PresetFavorite(preset_id=target))
            existing_favs.add(target)
            favorites_imported += 1

    # --- Custom presets ------------------------------------------------------
    existing_custom = {
        t.lower()
        for t in (
            await session.execute(
                select(QueryPreset.title).where(QueryPreset.source == "custom")
            )
        )
        .scalars()
        .all()
    }
    for item in payload.custom:
        title = str(item.get("title") or "").strip()
        query = str(item.get("query") or "").strip()
        if not title or not query:
            custom_skipped += 1
            continue
        if title.lower() in existing_custom:
            custom_skipped += 1
            continue
        category = str(item.get("category") or "Site Discovery")
        session.add(
            QueryPreset(
                slug=f"c-{hashlib.sha1(title.encode()).hexdigest()[:10]}",
                title=title[:120],
                description=str(item.get("desc") or "")[:500],
                query=query[:500],
                category=category if category in CATEGORIES else "Site Discovery",
                scope="Scoped" if "{domain}" in query else "General",
                tags=[],
                source="custom",
                legacy_id=str(item.get("id") or "")[:40] or None,
            )
        )
        existing_custom.add(title.lower())
        custom_imported += 1

    # --- Recent searches (into history, marked as imported) ------------------
    seen_recent: set[str] = set()
    for item in payload.recent:
        query = str(item.get("query") or "").strip()
        if not query or query.lower() in seen_recent:
            continue
        seen_recent.add(query.lower())
        session.add(
            SearchHistory(
                query=query[:900],
                mode="legacy",
                parsed_operators=[],
                providers_used=["google-redirect"],
                provider_statuses=[],
                result_count=0,
                status="imported",
                duration_ms=0,
            )
        )
        recent_imported += 1

    session.add(
        LegacyImport(
            payload_hash=payload_hash,
            source_keys=["dork-atlas-favorites-v1", "dork-atlas-custom-v1", "dork-atlas-recent-v1"],
            favorites_imported=favorites_imported,
            custom_imported=custom_imported,
            recent_imported=recent_imported,
            skipped_duplicates=favorites_skipped + custom_skipped,
        )
    )
    session.add(
        AuditEvent(
            action="migration.legacy_import",
            detail={
                "favorites": favorites_imported,
                "custom": custom_imported,
                "recent": recent_imported,
            },
        )
    )
    await session.flush()

    return LegacyImportResponse(
        favorites_imported=favorites_imported,
        custom_imported=custom_imported,
        recent_imported=recent_imported,
        favorites_skipped=favorites_skipped,
        custom_skipped=custom_skipped,
        already_imported=False,
        message=(
            f"Imported {favorites_imported} favorites, {custom_imported} custom presets, "
            f"{recent_imported} recent searches. Legacy browser data was not modified."
        ),
    )


@router.get("/status")
async def migration_status(session: AsyncSession = Depends(get_db)) -> dict:
    rows = (await session.execute(select(LegacyImport))).scalars().all()
    return {
        "imports": [
            {
                "id": r.id,
                "favorites_imported": r.favorites_imported,
                "custom_imported": r.custom_imported,
                "recent_imported": r.recent_imported,
                "skipped_duplicates": r.skipped_duplicates,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
        "legacy_keys_expected": [
            "dork-atlas-favorites-v1",
            "dork-atlas-custom-v1",
            "dork-atlas-recent-v1",
        ],
    }
