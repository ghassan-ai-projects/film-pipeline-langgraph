"""Common filesystem paths for KB assets."""

from __future__ import annotations

from pathlib import Path


def kb_manifest_path() -> Path:
    """Return the first available KB manifest path for this repo layout."""
    candidates = (
        Path("film-knowledge-base/manifest.yaml"),
        Path("film-knowledge-base/index/kb-manifest.yaml"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[1]
