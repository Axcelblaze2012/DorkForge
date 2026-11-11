"""Result processing: URL normalisation, tracking-param stripping, dedup."""

from __future__ import annotations

import hashlib
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "gclid", "fbclid", "msclkid", "dclid", "twclid", "mc_cid",
    "mc_eid", "igshid", "ref_src", "ref_url", "spm", "scm",
}

_TRACKED_RE = re.compile(r"^utm_", re.IGNORECASE)


def strip_tracking(url: str) -> str:
    """Remove common tracking query parameters."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    if not parsed.query:
        return url
    kept = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS and not _TRACKED_RE.match(k)
    ]
    query = urlencode(kept)
    return urlunparse(parsed._replace(query=query))


def normalize_url(url: str) -> str:
    """Canonical-ish form used for dedup keys: lowercase scheme+host,
    strip fragments, strip default ports, drop trailing slash on path,
    sort query params, strip tracking params."""
    url = url.strip()
    try:
        parsed = urlparse(url)
    except ValueError:
        return url
    scheme = parsed.scheme.lower() or "http"
    host = (parsed.hostname or "").lower()
    if not host:
        return url
    port = parsed.port
    default_ports = {"http": 80, "https": 443}
    netloc = host if (port is None or default_ports.get(scheme) == port) else f"{host}:{port}"
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    normalized = urlunparse((scheme, netloc, path, "", query, ""))
    return normalized


def domain_of(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""


def dedupe_key(url: str) -> str:
    return normalize_url(url)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def merge_results(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge result dicts that share a dedupe key, preserving first-seen
    order and merging provider attribution ('found_by')."""
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in raw:
        key = dedupe_key(item["url"])
        if not key:
            continue
        if key in merged:
            existing = merged[key]
            found_by = set(existing.get("found_by", []))
            found_by.add(item.get("provider", ""))
            existing["found_by"] = sorted(x for x in found_by if x)
            # Prefer the richer snippet if the first was empty.
            if not existing.get("snippet") and item.get("snippet"):
                existing["snippet"] = item["snippet"]
            if not existing.get("published_date") and item.get("published_date"):
                existing["published_date"] = item["published_date"]
        else:
            found_by = {item.get("provider", "")}
            item = dict(item)
            item["url_normalized"] = key
            item["found_by"] = sorted(x for x in found_by if x)
            merged[key] = item
            order.append(key)
    return [merged[k] for k in order]
