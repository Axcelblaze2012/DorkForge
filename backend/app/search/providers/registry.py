"""Provider adapter registry."""

from __future__ import annotations

from .base import ProviderAdapter, ProviderConfigData
from .brave import BraveAdapter
from .local_index import LocalIndexAdapter
from .searxng import SearXNGAdapter

_REGISTRY: dict[str, type[ProviderAdapter]] = {
    "searxng": SearXNGAdapter,
    "brave": BraveAdapter,
    "local_index": LocalIndexAdapter,
}


def build_adapter(config: ProviderConfigData) -> ProviderAdapter:
    cls = _REGISTRY.get(config.kind)
    if cls is None:
        raise ValueError(f"No adapter registered for provider kind '{config.kind}'")
    return cls(config)


def known_kinds() -> list[str]:
    return sorted(_REGISTRY)
