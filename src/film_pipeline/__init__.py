"""Film Pipeline LangGraph — a studio operating system for AI-assisted film creation.

The package exposes sub-packages for each major subsystem. Importing from the
package root is intentional only for version constants; subsystems should be
imported via their explicit sub-package (e.g. ``film_pipeline.schemas``).
"""

from __future__ import annotations

__version__ = "0.4.0"


def project_name() -> str:
    """Return the project name for this package."""
    return "film-pipeline"
