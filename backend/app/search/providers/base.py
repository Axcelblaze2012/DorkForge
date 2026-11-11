"""Provider adapter interface and shared data types."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class ProviderResult:
    """Raw outcome of one provider search attempt."""

    provider: str  # provider id, e.g. "searxng-local"
    kind: str  # searxng | brave | local_index
    status: str  # ok | error | timeout | skipped | disabled
    results: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    latency_ms: int = 0
    total_estimated: int | None = None  # provider-claimed total, may be None


@dataclass
class ProviderConfigData:
    """Runtime provider configuration (never includes secrets in responses)."""

    id: str
    kind: str
    name: str
    enabled: bool
    endpoint: str = ""
    api_key: str = ""  # server-side only
    timeout_seconds: float = 12.0
    priority: int = 10
    extra: dict[str, Any] = field(default_factory=dict)


class ProviderAdapter(ABC):
    """Interface every search provider adapter implements."""

    kind: str = "base"

    def __init__(self, config: ProviderConfigData) -> None:
        self.config = config

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        page: int,
        per_page: int,
        params: dict[str, Any] | None = None,
        client: httpx.AsyncClient,
    ) -> ProviderResult:
        """Execute one search. Must never raise: returns a ProviderResult
        with status error/timeout on failure."""

    async def health_check(self, client: httpx.AsyncClient) -> tuple[bool, str, int]:
        """Return (healthy, message, latency_ms). Default: unreachable."""
        return False, "Health check not implemented for this adapter.", 0

    def measure(self, start: float) -> int:
        return int((time.perf_counter() - start) * 1000)
