"""Reference index persistence and provider selection."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from film_pipeline.artifacts.project_storage import ProjectStorage

from ..helpers import _latest_artifact_version, _services

if TYPE_CHECKING:
    from film_pipeline.schemas.reference import ReferenceIndexEntry

_logger = logging.getLogger(__name__)


def _write_reference_index_files(project_root: Path, entries: list[dict[str, object]]) -> None:
    """Write human-readable reference index files (Phase 11)."""
    idx_dir = project_root / "references" / "index"
    idx_dir.mkdir(parents=True, exist_ok=True)

    # reference-index.json
    index_data = {
        "project_id": "",
        "generated_at": "",
        "entries": [
            {
                "reference_id": str(e.get("reference_id", "")),
                "asset_type": str(e.get("asset_type", "")),
                "subject_id": str(e.get("subject_id", "")),
                "asset_path": str(e.get("asset_path", "")),
                "provider": str(e.get("provider", "")),
                "validation": e.get("validation", {}),
                "locked": bool(e.get("locked", False)),
            }
            for e in entries
        ],
    }
    ProjectStorage.for_root(idx_dir).write_json_document(
        idx_dir / "reference-index.json", index_data
    )

    # reference-validation-summary.json
    scores = [
        float(cast(float, e.get("quality_score", 0))) for e in entries if e.get("quality_score")
    ]
    validated = sum(1 for e in entries if e.get("generation_status") == "validated")
    summary = {
        "project_id": "",
        "total_entries": len(entries),
        "validated": validated,
        "failed": sum(1 for e in entries if e.get("generation_status") == "failed"),
        "average_score": sum(scores) / len(scores) if scores else 0.0,
    }
    ProjectStorage.for_root(idx_dir).write_json_document(
        idx_dir / "reference-validation-summary.json", summary
    )


def _select_image_provider(rt: Any) -> Any | None:
    for provider_id in rt.list_providers():
        adapter = rt.get_provider(provider_id)
        entry = getattr(adapter, "entry", None)
        if entry is not None and getattr(entry, "provider_type", "") == "image":
            return adapter
    return None


def _save_reference_index_artifact(
    rt: Any,
    state: dict[str, object],
    artifact: dict[str, object],
) -> str | None:
    from datetime import UTC, datetime

    from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef
    from film_pipeline.schemas.base import ArtifactStatus, ArtifactType, FilmPhase

    project_id = str(state.get("project_id", ""))
    store = _services(rt).artifact_store
    version = (
        _latest_artifact_version(store, project_id, FilmPhase("visual_dev"), "reference_index") + 1
    )
    meta = ArtifactMetadata(
        artifact_id="reference_index",
        artifact_type=ArtifactType.REFERENCE_INDEX,
        project_id=project_id,
        phase=FilmPhase("visual_dev"),
        version=version,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by="mcp.generate_reference_images",
        created_at=datetime.now(UTC),
    )
    from film_pipeline.schemas.reference import ReferenceIndex

    entries = _reference_entries_from_grouped(artifact)
    reference_index = ReferenceIndex(project_id=project_id, entries=entries)
    ref: ArtifactRef = store.save(reference_index, meta)
    return ref.to_string()


def _reference_entries_from_grouped(
    artifact: dict[str, object],
) -> list[ReferenceIndexEntry]:
    """Build typed ``ReferenceIndexEntry`` objects from grouped raw entries."""
    from film_pipeline.schemas.reference import ReferenceIndexEntry

    raw_entries = cast(list[Any], artifact.get("entries", []))
    entries: list[ReferenceIndexEntry] = []
    for raw in raw_entries or []:
        if not isinstance(raw, dict):
            continue
        data = dict(raw)
        data.setdefault("asset_path", "")
        data.setdefault("asset_type", "")
        data.setdefault("subject_type", "")
        data.setdefault("subject_id", "")
        data.setdefault("quality_score", 0.0)
        entries.append(ReferenceIndexEntry.model_validate(data))
    return entries
