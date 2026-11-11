"""SearXNG provider adapter.

Talks to a self-hosted SearXNG instance's JSON API
(`GET /search?q=...&format=json`). The instance must be configured with the
`json` format enabled — see infrastructure/searxng/settings.yml in this repo
and the bundled docker-compose profile.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from .base import ProviderAdapter, ProviderConfigData, ProviderResult

TRACKING_PREFIXES = ("utm_",)


def _published_date(raw: Any) -> str | None:
    """SearXNG returns publishedDate as an Apache-style date string."""
    if not raw or not isinstance(raw, str):
        return None
    from email.utils import parsedate_to_datetime

    try:
        return parsedate_to_datetime(raw).date().isoformat()
    except (TypeError, ValueError):
        return raw[:10] if len(raw) >= 10 else None


class SearXNGAdapter(ProviderAdapter):
    kind = "searxng"

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
        if not cfg.endpoint:
            return ProviderResult(cfg.id, self.kind, "skipped", error="No endpoint configured")

        request_params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "pageno": max(1, page),
            "safesearch": int(cfg.extra.get("safesearch", 1)),
        }
        if params:
            if params.get("language") and params["language"] not in ("any", ""):
                request_params["language"] = params["language"]
            if params.get("time_range"):
                request_params["time_range"] = params["time_range"]
        if cfg.extra.get("engines"):
            request_params["engines"] = cfg.extra["engines"]

        try:
            resp = await client.get(
                cfg.endpoint.rstrip("/") + "/search",
                params=request_params,
                timeout=cfg.timeout_seconds,
            )
            latency = self.measure(start)
            resp.raise_for_status()
            payload = resp.json()
        except httpx.TimeoutException:
            return ProviderResult(cfg.id, self.kind, "timeout", latency_ms=self.measure(start))
        except httpx.HTTPStatusError as exc:
            detail = f"HTTP {exc.response.status_code}"
            if exc.response.status_code == 403:
                detail += " — SearXNG rejected the JSON API request. Enable 'json' in the instance's formats setting."
            return ProviderResult(
                cfg.id, self.kind, "error", error=detail, latency_ms=self.measure(start)
            )
        except (httpx.HTTPError, ValueError) as exc:
            return ProviderResult(
                cfg.id, self.kind, "error", error=str(exc), latency_ms=self.measure(start)
            )

        raw_results = payload.get("results") or []
        normalized: list[dict[str, Any]] = []
        for item in raw_results:
            url = item.get("url")
            title = item.get("title")
            if not url or not title:
                continue
            normalized.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": item.get("content") or "",
                    "engine": item.get("engine"),
                    "published_date": _published_date(item.get("publishedDate")),
                    "score_raw": item.get("score"),
                }
            )
        total = payload.get("number_of_results")
        if not isinstance(total, int) or total < 0:
            total = None
        return ProviderResult(
            cfg.id,
            self.kind,
            "ok",
            results=normalized,
            latency_ms=latency,
            total_estimated=total,
        )

    async def health_check(self, client: httpx.AsyncClient) -> tuple[bool, str, int]:
        start = time.perf_counter()
        if not self.config.endpoint:
            return False, "No endpoint configured", 0
        try:
            resp = await client.get(
                self.config.endpoint.rstrip("/") + "/config", timeout=5.0
            )
            latency = int((time.perf_counter() - start) * 1000)
            if resp.status_code == 200:
                return True, "Instance reachable", latency
            return False, f"HTTP {resp.status_code}", latency
        except httpx.HTTPError as exc:
            return False, str(exc), int((time.perf_counter() - start) * 1000)
