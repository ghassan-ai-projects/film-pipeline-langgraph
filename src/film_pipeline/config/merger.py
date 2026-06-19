"""Profile merging with clear layering semantics.

Rules:
- Scalars: later values override earlier ones.
- Lists: later lists replace earlier lists (no merge).
- Dicts: recursed; later keys override earlier keys at each level.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from film_pipeline.config.loader import ProfileSource


@dataclass
class ProfileMerger:
    """Layer a stack of profile sources into one resolved dict."""

    def merge(self, sources: list[ProfileSource]) -> dict[str, Any]:
        """Merge sources in order; later overrides earlier."""
        merged: dict[str, Any] = {}
        for src in sources:
            merged = self._deep_merge(merged, src.raw)
        return merged

    @staticmethod
    def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = dict(base)
        for k, v in overlay.items():
            if k in out and isinstance(out[k], dict) and isinstance(v, dict):
                out[k] = ProfileMerger._deep_merge(out[k], v)
            else:
                out[k] = v
        return out
