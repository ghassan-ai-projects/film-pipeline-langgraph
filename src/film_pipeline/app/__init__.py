"""Compatibility shims for the studio composition root.

The `app` package became `studio`. This package keeps the historical
`film_pipeline.app.*` import paths resolving while consumers migrate; every
module here re-exports its studio owner.
"""

from __future__ import annotations

import importlib
from typing import Any

#: Studio submodules that had an `app` counterpart.
_SHIMS = (
    "_graph_exec",
    "_operator_runtime",
    "_persistence",
    "_provider_factory",
    "_provider_profiles",
    "_provider_seeds",
    "_resume",
    "bootstrap",
    "graph_factory",
    "health",
    "logging_setup",
    "mock_responses",
    "runtime",
    "safety",
    "smoke",
    "version",
)


def __getattr__(name: str) -> Any:
    """Resolve a legacy submodule name against its studio owner."""
    if name in _SHIMS:
        return importlib.import_module(f"film_pipeline.studio.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_SHIMS))


__all__ = list(_SHIMS)
