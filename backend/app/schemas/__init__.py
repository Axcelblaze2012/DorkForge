"""Pydantic request/response schemas (API contract)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

SearchMode = Literal["universal", "advanced", "local_index", "research"]


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=900, description="Raw dork query")
    mode: SearchMode = "universal"
    providers: list[str] | None = Field(None, max_length=10)
    page: int = Field(1, ge=1, le=100)
    per_page: int = Field(20, ge=1, le=50)
    language: str = Field("", max_length=12, description="Any/empty = provider default")
    region: str = Field("", max_length=8, description="Country code (gl)")
    save_history: bool = True

    @field_validator("query")
    @classmethod
    def strip_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Query must not be empty")
        return v


class ResultCard(BaseModel):
    title: str
    url: str
    domain: str = ""
    snippet: str = ""
    provider: str = ""
    provider_kind: str = ""
    found_by: list[str] = []
    engine: str | None = None
    published_date: str | None = None
    score: float = 0.0
    score_explain: dict[str, Any] = {}


class ProviderStatus(BaseModel):
    provider: str
    kind: str
    status: str
    latency_ms: int = 0
    count: int = 0
    error: str | None = None
    total_estimated: int | None = None


class SearchResponse(BaseModel):
    query: str
    rendered_query: str
    mode: str
    results: list[ResultCard]
    total: int
    page: int
    per_page: int
    total_pages: int
    providers_used: list[str]
    provider_statuses: list[ProviderStatus]
    warnings: list[str]
    diagnostics: list[dict[str, Any]]
    operators: list[str]
    dedup_removed: int = 0
    filters_applied_locally: bool = False
    elapsed_ms: int = 0
    cached: bool = False
    history_id: int | None = None


# ---------------------------------------------------------------------------
# Query engine
# ---------------------------------------------------------------------------

class QueryParseRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=900)


class ComposerQueryRequest(BaseModel):
    terms: str = Field("", max_length=300)
    domain: str = Field("", max_length=120)
    filetype: str = Field("", max_length=16)
    title_term: str = Field("", max_length=120)
    url_term: str = Field("", max_length=120)
    exact_phrase: str = Field("", max_length=200)
    exclude_terms: str = Field("", max_length=200)
    time_range: str = Field("", max_length=2)
    region: str = Field("", max_length=8)
    # Execution parameters
    providers: list[str] | None = Field(None, max_length=10)
    page: int = Field(1, ge=1, le=100)
    per_page: int = Field(20, ge=1, le=50)
    language: str = Field("", max_length=12)
    save_history: bool = True


class QueryExplainResponse(BaseModel):
    query: str
    rendered_query: str
    ast: dict[str, Any]
    operators: list[str]
    diagnostics: list[dict[str, Any]]
    complexity: dict[str, Any]
    compatibility: dict[str, Any]  # per-provider operator support


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

PresetSource = Literal["builtin", "custom"]


class PresetBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    description: str = Field("", max_length=500)
    query: str = Field(..., min_length=1, max_length=500)
    category: str = Field(..., min_length=1, max_length=60)
    scope: Literal["Scoped", "General"] = "General"
    tags: list[str] = Field(default_factory=list, max_length=12)

    @field_validator("tags")
    @classmethod
    def clean_tags(cls, v: list[str]) -> list[str]:
        return [t.strip()[:40] for t in v if t.strip()][:12]


class PresetCreate(PresetBase):
    pass


class PresetUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=120)
    description: str | None = Field(None, max_length=500)
    query: str | None = Field(None, min_length=1, max_length=500)
    category: str | None = Field(None, min_length=1, max_length=60)
    scope: Literal["Scoped", "General"] | None = None
    tags: list[str] | None = None


class PresetOut(PresetBase):
    id: int
    slug: str
    source: str
    legacy_id: str | None = None
    version: int
    favorite: bool = False

    class Config:
        from_attributes = True


class PresetListResponse(BaseModel):
    presets: list[PresetOut]
    total: int
    categories: dict[str, int]


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

class HistoryCreate(BaseModel):
    query: str = Field(..., min_length=1, max_length=900)
    mode: str = "universal"
    result_count: int = 0
    status: str = "ok"
    duration_ms: int = 0
    providers_used: list[str] = []
    warnings: list[str] = []


class HistoryOut(BaseModel):
    id: int
    query: str
    mode: str
    operators: list[str]
    providers_used: list[str]
    provider_statuses: list[dict[str, Any]]
    result_count: int
    status: str
    duration_ms: int
    cached: bool
    created_at: str
    warnings: list[str] = []
    pinned: bool = False

    class Config:
        from_attributes = True


class HistoryListResponse(BaseModel):
    items: list[HistoryOut]
    total: int


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

class ProviderOut(BaseModel):
    id: str
    kind: str
    name: str
    enabled: bool
    endpoint: str
    has_api_key: bool
    timeout_seconds: float
    priority: int
    safesearch: int | str | None = None
    last_status: str | None = None
    last_latency_ms: int | None = None
    last_checked_at: str | None = None
    last_success_at: str | None = None
    last_error: str | None = None
    error_count: int = 0
    compatibility: dict[str, Any] = {}


class ProviderUpdate(BaseModel):
    enabled: bool | None = None
    endpoint: str | None = Field(None, max_length=500)
    api_key: str | None = Field(None, max_length=300)
    timeout_seconds: float | None = Field(None, gt=0, le=60)
    priority: int | None = Field(None, ge=0, le=100)
    safesearch: int | str | None = None


class ProviderHealthOut(BaseModel):
    provider: str
    healthy: bool
    message: str
    latency_ms: int


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class AppSettingsOut(BaseModel):
    default_results_per_page: int = 20
    default_region: str = ""
    default_language: str = ""
    safe_search: int = 1
    search_cache_ttl_seconds: int = 300
    history_retention_days: int = 180
    default_provider: str = "searxng"


class AppSettingsUpdate(BaseModel):
    default_results_per_page: int | None = Field(None, ge=5, le=50)
    default_region: str | None = Field(None, max_length=8)
    default_language: str | None = Field(None, max_length=12)
    safe_search: int | None = Field(None, ge=0, le=2)
    search_cache_ttl_seconds: int | None = Field(None, ge=0, le=86400)
    history_retention_days: int | None = Field(None, ge=1, le=3650)
    default_provider: str | None = Field(None, max_length=40)


# ---------------------------------------------------------------------------
# Legacy migration
# ---------------------------------------------------------------------------

class LegacyImportRequest(BaseModel):
    """Payload from the original app's localStorage keys."""

    favorites: list[str] = Field(default_factory=list, max_length=500)
    custom: list[dict[str, Any]] = Field(default_factory=list, max_length=500)
    recent: list[dict[str, Any]] = Field(default_factory=list, max_length=200)

    @field_validator("custom")
    @classmethod
    def validate_custom(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        cleaned: list[dict[str, Any]] = []
        for item in v:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("name") or "").strip()
            query = str(item.get("query") or "").strip()
            if not title or not query:
                continue
            cleaned.append(
                {
                    "id": str(item.get("id") or "")[:40],
                    "title": title[:120],
                    "desc": str(item.get("desc") or item.get("description") or "")[:500],
                    "category": str(item.get("category") or "Site Discovery")[:60],
                    "query": query[:500],
                    "scope": "Scoped" if "{domain}" in query else "General",
                }
            )
        return cleaned


class LegacyImportResponse(BaseModel):
    favorites_imported: int
    custom_imported: int
    recent_imported: int
    favorites_skipped: int
    custom_skipped: int
    already_imported: bool = False
    message: str
