"""Runtime version and build metadata."""

from __future__ import annotations

__version__ = "0.3.0"
BUILD_LABEL = "dev"

_VERSION_INFO = {
    "version": __version__,
    "build_label": BUILD_LABEL,
    "python": ">=3.12",
    "langgraph": ">=0.2,<0.3",
}
