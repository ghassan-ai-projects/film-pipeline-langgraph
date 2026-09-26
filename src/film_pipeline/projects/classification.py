"""Project classification: kind, title, and folder-name policy.

These rules decide what a project *is* — whether it is a production project or
test scaffolding, and how a folder name becomes a human-readable title. They are
pure functions over names and state, with no runtime, storage, or operator
dependency, so both the operator service and any future surface can share one
definition.

`projects` sits at L4 and may import only `filmspec`, `schemas`, and `storage`,
so this module raises the built-in :class:`ValueError` for a bad kind. The
operator surface translates that into its own `BackendOperationError` at the
boundary where a caller-facing message is built.
"""

from __future__ import annotations

from collections.abc import Mapping

#: Folder-name markers that identify throwaway or fixture projects. A project
#: whose name contains any of these is classified as test scaffolding.
_TEST_NAME_MARKERS: tuple[str, ...] = ("test", "fixture", "sample", "tmp", "demo")

VALID_PROJECT_KINDS: frozenset[str] = frozenset({"production", "test"})


class InvalidProjectKindError(ValueError):
    """Raised when a project kind falls outside the closed set.

    A `ValueError` subclass, so existing callers that catch `ValueError` keep
    working while the operator boundary can catch this precisely.
    """


def project_kind_for_name(name: str) -> str:
    """Classify a project folder name as ``production`` or ``test``."""
    lowered = name.lower()
    return "test" if any(marker in lowered for marker in _TEST_NAME_MARKERS) else "production"


def normalize_project_kind(project_kind: str) -> str:
    """Validate and canonicalize an explicit project kind.

    Raises :class:`InvalidProjectKindError` for a kind outside the closed set,
    so callers surface an actionable message rather than storing a bad value.
    """
    kind = project_kind.strip().lower()
    if kind not in VALID_PROJECT_KINDS:
        raise InvalidProjectKindError(
            f"project_kind must be 'production' or 'test', got '{project_kind}'."
        )
    return kind


def project_kind_for_state(state: Mapping[str, object], project_id: str) -> str:
    """Return the project's declared kind, falling back to its folder name."""
    explicit = str(state.get("project_kind", "")).strip().lower()
    if explicit:
        return normalize_project_kind(explicit)
    return project_kind_for_name(project_id)


def project_title_from_id(project_id: str) -> str:
    """Derive a human-readable title from a project folder name."""
    return project_id.replace("-", " ").replace("_", " ").title()
