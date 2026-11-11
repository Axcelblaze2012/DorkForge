"""Local Dork Atlas index adapter.

Placeholder for Phase 6. It must NEVER fabricate results: it reports the
honest status so the orchestrator can surface "Local index: not available
in this build" instead of pretending to search.
"""

from __future__ import annotations

from typing import Any

import httpx

from .base import ProviderAdapter, ProviderResult


class LocalIndexAdapter(ProviderAdapter):
    kind = "local_index"

    async def search(
        self,
        query: str,
        *,
        page: int,
        per_page: int,
        params: dict[str, Any] | None = None,
        client: httpx.AsyncClient,
    ) -> ProviderResult:
        return ProviderResult(
            self.config.id,
            self.kind,
            "skipped",
            error="Local index search ships in Phase 6. No local documents are indexed in this build.",
        )
