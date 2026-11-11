"""All ORM models; importing this package registers every table.

Phase 1 tables: presets, favorites, search history, provider configs,
application settings, legacy-import tracking, and an audit trail.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, utcnow


class QueryPreset(Base, TimestampMixin):
    """Built-in and custom dork presets."""

    __tablename__ = "query_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(60), index=True, nullable=False)
    scope: Mapped[str] = mapped_column(String(20), default="General", nullable=False)
    tags: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    source: Mapped[str] = mapped_column(String(10), default="custom", index=True)  # builtin | custom
    legacy_id: Mapped[str | None] = mapped_column(String(40), index=True, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    favorites: Mapped[list["PresetFavorite"]] = relationship(
        back_populates="preset", cascade="all, delete-orphan"
    )


class PresetFavorite(Base, TimestampMixin):
    """Favorited presets (single-user in Phase 1; user_id reserved)."""

    __tablename__ = "preset_favorites"
    __table_args__ = (UniqueConstraint("user_id", "preset_id", name="uq_user_preset_fav"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=1, index=True)
    preset_id: Mapped[int] = mapped_column(
        ForeignKey("query_presets.id", ondelete="CASCADE"), index=True
    )
    preset: Mapped[QueryPreset] = relationship(back_populates="favorites")


class SearchHistory(Base, TimestampMixin):
    """One row per executed search — an honest record of what was run."""

    __tablename__ = "search_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, default=1, index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="universal", nullable=False)
    parsed_operators: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    providers_used: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    provider_statuses: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ok", nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    workspace_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warnings: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)


class ProviderConfig(Base, TimestampMixin):
    """Search provider configuration. API keys stay server-side."""

    __tablename__ = "search_providers"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    endpoint: Mapped[str] = mapped_column(Text, default="", nullable=False)
    api_key: Mapped[str] = mapped_column(Text, default="", nullable=False)  # never serialized
    timeout_seconds: Mapped[float] = mapped_column(Float, default=12.0, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    extra: Mapped[dict[Any, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # Health tracking
    last_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class AppSetting(Base, TimestampMixin):
    """Key/value application settings."""

    __tablename__ = "application_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict[Any, Any] | list[Any] | str | int | bool | None] = mapped_column(
        JSON, nullable=False
    )


class LegacyImport(Base):
    """Tracks legacy localStorage imports to prevent duplicate imports."""

    __tablename__ = "legacy_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source_keys: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    favorites_imported: Mapped[int] = mapped_column(Integer, default=0)
    custom_imported: Mapped[int] = mapped_column(Integer, default=0)
    recent_imported: Mapped[int] = mapped_column(Integer, default=0)
    skipped_duplicates: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    """Lightweight audit trail for sensitive actions (imports, deletes)."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    detail: Mapped[dict[Any, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


__all__ = [
    "Base",
    "TimestampMixin",
    "utcnow",
    "QueryPreset",
    "PresetFavorite",
    "SearchHistory",
    "ProviderConfig",
    "AppSetting",
    "LegacyImport",
    "AuditEvent",
]
