"""Brave Search API adapter (official, requires an API key).

https://api.search.brave.com/res/v1/web/search — the key is stored
server-side and never sent to the frontend.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from .base import ProviderAdapter, ProviderResult

API_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveAdapter(ProviderAdapter):
    kind = "brave"

    async def search(
        self,
        query: str,
        *,
        page: int,
        per_page: int,
        params: dict[str, Any] | None = None,
        client: httpx.AsyncClient,
    ) -> ProviderResult:
        cfg = self.config
        start = time.perf_counter()
        if not cfg.api_key:
            return ProviderResult(
                cfg.id, self.kind, "skipped", error="No API key configured"
            )

        # Brave requires offset % 9 == 0 for pagination; clamp to valid range.
        offset = max(0, (page - 1)) * per_page
        offset -= offset % 9
        request_params: dict[str, Any] = {
            "q": query,
            "count": min(per_page, 20),
            "offset": min(offset, 198),
            "safesearch": cfg.extra.get("safesearch", "moderate"),
        }
        if params:
            if params.get("freshness"):
                request_params["freshness"] = params["freshness"]
            if params.get("country") and params["country"] not in ("any", ""):
                request_params["country"] = params["country"]
            if params.get("search_lang") and params["search_lang"] not in ("any", ""):
                request_params["search_lang"] = params["search_lang"]

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": cfg.api_key,
        }
        try:
            resp = await client.get(
                API_URL, params=request_params, headers=headers, timeout=cfg.timeout_seconds
            )
            latency = self.measure(start)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.TimeoutException:
            return ProviderResult(cfg.id, self.kind, "timeout", latency_ms=self.measure(start))
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            detail = f"HTTP {status}"
            if status == 401:
                detail += " — invalid API key"
            elif status == 429:
                detail += " — rate limit or monthly quota exceeded"
            return ProviderResult(
                cfg.id, self.kind, "error", error=detail, latency_ms=self.measure(start)
            )
        except (httpx.HTTPError, ValueError) as exc:
            return ProviderResult(
                cfg.id, self.kind, "error", error=str(exc), latency_ms=self.measure(start)
            )

        web = payload.get("web") or {}
        normalized: list[dict[str, Any]] = []
        for item in web.get("results") or []:
            url = item.get("url")
            title = item.get("title")
            if not url or not title:
                continue
            meta = item.get("meta_url") or {}
            normalized.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": item.get("description") or "",
                    "engine": "brave",
                    "published_date": item.get("age") or None,  # relative age or None
                    "favicon": meta.get("favicon") or None,
                    "score_raw": None,
                }
            )
        total = None
        if isinstance(web.get("total"), int):
            total = web["total"]
        elif isinstance(payload.get("query", {}).get("total_results"), int):
            total = payload["query"]["total_results"]
        return ProviderResult(
            cfg.id, self.kind, "ok", results=normalized, latency_ms=latency, total_estimated=total
        )

    async def health_check(self, client: httpx.AsyncClient) -> tuple[bool, str, int]:
        start = time.perf_counter()
        if not self.config.api_key:
            return False, "No API key configured", 0
        try:
            resp = await client.get(
                API_URL,
                params={"q": "atlas", "count": 1},
                headers={"Accept": "application/json", "X-Subscription-Token": self.config.api_key},
                timeout=6.0,
            )
            latency = int((time.perf_counter() - start) * 1000)
            if resp.status_code == 200:
                return True, "API reachable and key accepted", latency
            if resp.status_code == 401:
                return False, "API key rejected (401)", latency
            if resp.status_code == 429:
                return False, "Rate limit / quota exceeded (429)", latency
            return False, f"HTTP {resp.status_code}", latency
        except httpx.HTTPError as exc:
            return False, str(exc), int((time.perf_counter() - start) * 1000)
