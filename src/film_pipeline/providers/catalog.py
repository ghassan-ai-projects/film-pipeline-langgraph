"""The provider identity catalogue — which provider ids exist.

This answers one question: *is this provider id real?* It holds no cost data.

Kept in `providers` rather than `studio` because provider identity is this
package's concern: `studio` only decides which of these a given server mode uses.
"""

from __future__ import annotations

#: Every provider id the system knows how to build an adapter for.
KNOWN_PROVIDER_IDS: frozenset[str] = frozenset(
    {
        "seedance-openrouter",
        "veo-fast",
        "veo-3.1-fast",
        "gemini-imagen-4",
        "imagen-4",
        "mock-video-provider",
        "mock-image-provider",
    }
)

#: Provider ids each server mode seeds adapters for.
PROVIDER_IDS_BY_MODE: dict[str, tuple[str, ...]] = {
    "real": ("seedance-openrouter", "veo-fast", "gemini-imagen-4"),
    "mock": ("mock-video-provider", "mock-image-provider"),
}

__all__ = ["KNOWN_PROVIDER_IDS", "PROVIDER_IDS_BY_MODE"]


def is_known_provider(provider_id: str) -> bool:
    """True when ``provider_id`` is a real provider id, not a typo."""
    return provider_id in KNOWN_PROVIDER_IDS


def supported_provider_ids(server_mode: str) -> tuple[str, ...]:
    """Provider ids the given server mode seeds adapters for."""
    return PROVIDER_IDS_BY_MODE.get(server_mode, PROVIDER_IDS_BY_MODE["mock"])
