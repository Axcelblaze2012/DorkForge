"""In-memory TTL cache for search responses.

Phase 1 uses a process-local cache. It is deliberately bounded (max size +
TTL) so long-running instances do not grow without limit. A Redis-backed
cache can replace this later without changing callers.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _Entry:
    value: Any
    expires_at: float


class SearchCache:
    def __init__(self, ttl_seconds: int = 300, max_entries: int = 256) -> None:
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._store: dict[str, _Entry] = {}
        self.hits = 0
        self.misses = 0

    @staticmethod
    def fingerprint(payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def make_key(
        query_canonical: str,
        providers: list[str],
        page: int,
        per_page: int,
        language: str = "any",
        region: str = "any",
    ) -> str:
        material = json.dumps(
            [query_canonical, sorted(providers), page, per_page, language, region],
            ensure_ascii=False,
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            self.misses += 1
            return None
        if entry.expires_at < time.time():
            del self._store[key]
            self.misses += 1
            return None
        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any) -> None:
        if len(self._store) >= self.max_entries:
            # Drop the oldest half to stay bounded.
            for old_key in sorted(self._store, key=lambda k: self._store[k].expires_at)[
                : self.max_entries // 2
            ]:
                self._store.pop(old_key, None)
        self._store[key] = _Entry(value=value, expires_at=time.time() + self.ttl)

    def clear(self) -> None:
        self._store.clear()
        self.hits = 0
        self.misses = 0

    def stats(self) -> dict[str, Any]:
        total = self.hits + self.misses
        return {
            "entries": len(self._store),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / total, 4) if total else 0.0,
            "ttl_seconds": self.ttl,
        }
