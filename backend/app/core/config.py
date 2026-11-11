"""Application configuration loaded from environment variables / .env file.

All secrets are provided through the environment. Nothing secret is ever
hardcoded here and nothing here is sent to the frontend.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DORK_ATLAS_",
        env_file=(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application -------------------------------------------------------
    app_name: str = "Dork Atlas Ultimate"
    version: str = "0.1.0"
    environment: str = "development"  # development | production
    log_level: str = "INFO"

    # --- Database ----------------------------------------------------------
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'dork_atlas.db'}"

    # --- Security ----------------------------------------------------------
    # Optional: when set, all mutating API routes require `X-API-Key`.
    # Leave empty for local single-user development bound to localhost.
    api_key: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    rate_limit_requests: int = 120  # per window, per IP
    rate_limit_window_seconds: int = 60
    max_request_body_bytes: int = 512 * 1024

    # --- Provider credentials (server-side only; never sent to frontend) ---
    # Env: DORK_ATLAS_SEARXNG_URL, DORK_ATLAS_BRAVE_API_KEY
    searxng_url: str = ""
    brave_api_key: str = ""

    # --- Search defaults ---------------------------------------------------
    default_provider: str = "searxng"
    default_results_per_page: int = 20
    max_results_per_page: int = 50
    provider_request_timeout_seconds: float = 12.0
    search_cache_ttl_seconds: int = 300
    max_concurrent_providers: int = 4

    # --- History -----------------------------------------------------------
    history_retention_days: int = 180
    history_max_entries: int = 5000


@lru_cache
def get_settings() -> Settings:
    return Settings()
