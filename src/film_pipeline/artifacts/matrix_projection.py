"""Materialize the current matrix from base artifact + layered patches."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from film_pipeline.schemas.artifact import ArtifactRef

if TYPE_CHECKING:
    from film_pipeline.schemas.base import FilmPhase
    from film_pipeline.schemas.matrix_patch import MatrixPatch


class _MatrixStore(Protocol):
    """The one store capability matrix projection needs: load an artifact body."""

    def load(
        self, project_id: str, phase: FilmPhase, artifact_id: str, version: int
    ) -> dict[str, Any]: ...


def materialize_matrix(
    store: _MatrixStore,
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


def _parse_artifact_ref(artifact_ref: str) -> ArtifactRef:
    """Parse an ``artifact:...:v<N>`` ref into its id, version, and phase."""
    return ArtifactRef.from_string(artifact_ref)


def _load_base_matrix(store: _MatrixStore, project_id: str, matrix_ref: str) -> dict[str, Any]:
    """Load the base matrix artifact."""
    from film_pipeline.schemas.base import FilmPhase

    parsed = _parse_artifact_ref(matrix_ref)
    phase = FilmPhase(parsed.phase)
    result: dict[str, Any] = store.load(project_id, phase, parsed.artifact_id, parsed.version)
    return result


def _load_patch(store: _MatrixStore, project_id: str, patch_ref: str) -> MatrixPatch:
    """Load a matrix patch artifact from its ref's phase, or the patch phases."""
    from film_pipeline.schemas.base import FilmPhase
    from film_pipeline.schemas.matrix_patch import MatrixPatch

    parsed = _parse_artifact_ref(patch_ref)
    data: dict[str, Any] = store.load(
        project_id, FilmPhase(parsed.phase), parsed.artifact_id, parsed.version
    )
    return MatrixPatch(**data)
