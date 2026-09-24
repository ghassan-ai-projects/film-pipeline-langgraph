"""Artifact persistence: versioning, candidate metadata, and ref publication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from film_pipeline.graph.nodes._context import (
    _build_dependency_map,
    _infer_artifact_type,
    _parse_ref,
)
from film_pipeline.graph.nodes._shared import (
    _get_services,
)
from film_pipeline.schemas._base import ArtifactType as _ArtifactType

if TYPE_CHECKING:
    from film_pipeline.graph.services import GraphServices
    from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef


@dataclass(frozen=True)
class _ArtifactProvenance:
    """Provenance inputs captured once per artifact save."""

    phase: str
    built_from: dict[str, str]
    kb_context_ref: str | None
    change_summary: str


def _resolve_artifact_type(artifact_type: str | None, artifact: Any) -> _ArtifactType:
    """Resolve the declared artifact type; infer from the class name when omitted."""
    if artifact_type is not None:
        try:
            return _ArtifactType(artifact_type)
        except ValueError:
            return _ArtifactType.SCRIPT
    return _infer_artifact_type(artifact)


def _publish_candidate_ref(state: dict[str, Any], artifact_id: str, ref: str) -> None:
    """Record the candidate ref in orchestrator state."""
    from film_pipeline.graph.orchestrator_state import ensure_orchestrator_state, set_candidate_ref

    ensure_orchestrator_state(state)
    set_candidate_ref(state, artifact_id, ref)


def _build_artifact_metadata(
    state: dict[str, Any],
    services: GraphServices,
    artifact_id: str,
    artifact_type: _ArtifactType,
    provenance: _ArtifactProvenance,
) -> ArtifactMetadata:
    """Allocate the next version and assemble candidate metadata.

    ``next_version`` must run before metadata construction so repairs (v2, v3, …)
    never overwrite the original version.
    """
    from datetime import UTC, datetime

    from film_pipeline.schemas._base import ArtifactStatus, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata

    project_id = str(state.get("project_id", ""))
    version = services.artifact_store.next_version(project_id, provenance.phase, artifact_id)
    parents: list[ArtifactRef] = []
    for raw_ref in state.get("artifact_refs", []):
        try:
            parents.append(_parse_ref(raw_ref))
        except ValueError:
            continue  # malformed refs in state must not crash the save

    return ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        project_id=project_id,
        phase=FilmPhase(provenance.phase),
        version=version,
        status=ArtifactStatus.CANDIDATE,
        parents=parents,
        created_by="graph_node",
        kb_context_ref=provenance.kb_context_ref,
        created_at=datetime.now(UTC),
        built_from=provenance.built_from,
        change_summary=provenance.change_summary,
    )


def _resolve_provenance(
    state: dict[str, Any],
    phase: str,
    *,
    change_summary: str,
    built_from: dict[str, str] | None,
    kb_context_ref: str | None,
) -> _ArtifactProvenance:
    """Capture provenance once per save, defaulting to the current graph context."""
    return _ArtifactProvenance(
        phase=phase,
        built_from=built_from if built_from is not None else _build_dependency_map(state),
        kb_context_ref=(
            kb_context_ref if kb_context_ref is not None else state.get("_last_kb_context_ref")
        ),
        change_summary=change_summary,
    )


def _save_artifact(
    state: dict[str, Any],
    artifact: Any,
    artifact_id: str,
    phase: str,
    artifact_type: str | None = None,
    *,
    change_summary: str = "",
    built_from: dict[str, str] | None = None,
    kb_context_ref: str | None = None,
) -> str | None:
    """Persist an artifact via ArtifactStore and return its ref string.

    Auto-increments the version so repairs (v2, v3, …) never overwrite the
    original. Populates ``built_from`` with current upstream artifact refs
    for dependency tracking.

    ``artifact_type`` is an optional ArtifactType enum value. When omitted,
    inferred from the class name via mapping.
    """
    services = _get_services(state)
    if services is None:
        return None

    atype = _resolve_artifact_type(artifact_type, artifact)
    provenance = _resolve_provenance(
        state,
        phase,
        change_summary=change_summary,
        built_from=built_from,
        kb_context_ref=kb_context_ref,
    )

    meta = _build_artifact_metadata(state, services, artifact_id, atype, provenance)
    ref = services.artifact_store.save(artifact, meta).to_string()

    _publish_candidate_ref(state, artifact_id, ref)

    return ref
