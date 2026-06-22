"""Materialize the current matrix from base artifact + layered patches."""

from __future__ import annotations

from typing import Any


def materialize_matrix(
    store: Any,
    project_id: str,
    base_ref: str,
    patch_refs: list[str],
) -> dict[str, Any]:
    """Build the current matrix by applying patches to the base.

    Args:
        store: ArtifactStore instance.
        project_id: Project identifier.
        base_ref: Base matrix artifact ref (e.g. "artifact:shot_matrix:v1").
        patch_refs: Ordered list of patch refs to apply.

    Returns:
        Matrix dict with all patches applied.
    """
    matrix = _load_base_matrix(store, project_id, base_ref)
    rows_raw = matrix.get("rows", [])
    rows: list[dict[str, object]] = rows_raw if isinstance(rows_raw, list) else []

    for patch_ref in patch_refs:
        patch = _load_patch(store, project_id, patch_ref)
        rows = patch.apply_to(rows)

    matrix["rows"] = rows
    return matrix


def _load_base_matrix(store: Any, project_id: str, matrix_ref: str) -> dict[str, Any]:
    """Load the base matrix artifact."""
    parts = matrix_ref.split(":")
    artifact_id = parts[1] if len(parts) > 1 else matrix_ref
    version_str = parts[2] if len(parts) > 2 else "1"
    version = int(version_str.lstrip("v"))

    from film_pipeline.schemas._base import FilmPhase

    result: dict[str, Any] = store.load(project_id, FilmPhase.SHOT_BIBLE, artifact_id, version)
    return result


def _load_patch(store: Any, project_id: str, patch_ref: str) -> Any:
    """Load a matrix patch artifact."""
    from film_pipeline.schemas.matrix_patch import MatrixPatch

    parts = patch_ref.split(":")
    artifact_id = parts[1] if len(parts) > 1 else patch_ref
    version_str = parts[2] if len(parts) > 2 else "1"
    version = int(version_str.lstrip("v"))

    from film_pipeline.schemas._base import FilmPhase

    for phase in (
        FilmPhase.GEN_PLANNING,
        FilmPhase.GENERATION,
        FilmPhase.QC,
        FilmPhase.POST,
    ):
        try:
            data: dict[str, Any] = store.load(project_id, phase, artifact_id, version)
            return MatrixPatch(**data)
        except (FileNotFoundError, ValueError, TypeError):
            continue

    raise FileNotFoundError(f"Patch {patch_ref} not found in any phase")
