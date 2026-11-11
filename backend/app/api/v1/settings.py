"""Application settings endpoints."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_api_key
from app.models import AppSetting
from app.schemas import AppSettingsOut, AppSettingsUpdate
from sqlalchemy import select

router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_KEY = "app"

DEFAULTS = AppSettingsOut()


async def read_settings(session: AsyncSession) -> AppSettingsOut:
    row = (
        await session.execute(select(AppSetting).where(AppSetting.key == SETTINGS_KEY))
    ).scalar_one_or_none()
    if row is None:
        return DEFAULTS
    data = row.value or {}
    merged = DEFAULTS.model_dump()
    merged.update({k: v for k, v in data.items() if k in merged})
    return AppSettingsOut(**merged)


async def write_settings(session: AsyncSession, out: AppSettingsOut) -> AppSettingsOut:
    row = (
        await session.execute(select(AppSetting).where(AppSetting.key == SETTINGS_KEY))
    ).scalar_one_or_none()
    value = json.loads(out.model_dump_json())
    if row is None:
        session.add(AppSetting(key=SETTINGS_KEY, value=value))
    else:
        row.value = value
    await session.flush()
    return out


@router.get("", response_model=AppSettingsOut)
async def get_settings_endpoint(
    session: AsyncSession = Depends(get_db),
) -> AppSettingsOut:
    return await read_settings(session)


@router.patch("", response_model=AppSettingsOut)
async def update_settings_endpoint(
    body: AppSettingsUpdate,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_api_key),
) -> AppSettingsOut:
    current = (await read_settings(session)).model_dump()
    updates = body.model_dump(exclude_unset=True)
    current.update(updates)
    return await write_settings(session, AppSettingsOut(**current))
