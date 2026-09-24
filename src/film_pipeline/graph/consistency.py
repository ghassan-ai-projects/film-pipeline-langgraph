"""Artifact consistency checks — staleness detection, dependency validation.

Phase 3: informational staleness warnings. Non-blocking until Phase 6.
"""

from __future__ import annotations

from typing import Any


def _staleness_warnings(
    artifact_id: str,
    artifact_ref: str,
    built_from: dict[str, Any],
    approved: dict[str, str],
) -> list[dict[str, Any]]:
    """Compare each dependency's built-from ref against the approved ref."""
    warnings: list[dict[str, Any]] = []
    for dep_id, dep_version_ref in built_from.items():
        current_ref = approved.get(dep_id)
        if current_ref and current_ref != dep_version_ref:
            warnings.append(
                {
                    "artifact_id": artifact_id,
                    "artifact_ref": artifact_ref,
                    "dependency_id": dep_id,
                    "built_with_version": dep_version_ref,
                    "current_version": current_ref,
                    "severity": "stale",
                    "message": (
                        f"'{artifact_id}' built from {dep_version_ref} "
                        f"but {dep_id} is now at {current_ref} — may be stale"
                    ),
                }
            )
    return warnings


def check_staleness(
    artifact_ref: str,
    state: dict[str, Any],
    store: Any,
) -> list[dict[str, Any]]:
    """Check if an artifact's upstream dependencies have newer versions.

    Returns a list of staleness warnings. Empty list = all deps are current.
    """
    from film_pipeline.schemas.artifact import ArtifactRef

    try:
        parsed = ArtifactRef.from_string(artifact_ref)
    except ValueError:
        return []

    project_id = str(state.get("project_id", ""))
    try:
        metadata = store.load_metadata(project_id, parsed.phase, parsed.artifact_id, parsed.version)
    except (FileNotFoundError, ValueError):
        return []
    if metadata is None:
        return []

    built_from = getattr(metadata, "built_from", {}) or {}

    from film_pipeline.graph.orchestrator_state import get_approved_refs

    return _staleness_warnings(
        parsed.artifact_id, artifact_ref, built_from, get_approved_refs(state)
    )


def check_phase_consistency(
    state: dict[str, Any],
    services: Any,
) -> list[dict[str, Any]]:
    """Run staleness checks on all artifacts created in the current phase."""
    artifact_refs = state.get("artifact_refs", [])
    store = services.artifact_store

    all_warnings: list[dict[str, Any]] = []
    for ref in artifact_refs:
        all_warnings.extend(check_staleness(ref, state, store))

    return all_warnings
