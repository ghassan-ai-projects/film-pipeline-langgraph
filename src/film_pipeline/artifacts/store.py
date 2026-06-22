"""Artifact store — save, load, list, version, supersede.

The canonical registry for all typed artifacts. Every phase writes artifacts
through this store so the project directory stays consistent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel

from film_pipeline.artifacts.metadata import read_metadata, write_metadata
from film_pipeline.schemas._base import FilmPhase
from film_pipeline.schemas.artifact import ArtifactMetadata


class ArtifactStore:
    """Persist and retrieve typed artifacts with metadata and versioning."""

    def __init__(self, root: Path = Path("projects")) -> None:
        self._root = root

    def _artifact_path(self, project_id: str, phase: str, artifact_id: str, version: int) -> Path:
        safe_id = artifact_id.replace(":", "_").replace("/", "_")
        phase_dir_map = {
            "intake": "intake",
            "constitution": "01-vision",
            "development": "02-development",
            "script": "03-script",
            "visual_dev": "04-visual-dev",
            "shot_bible": "05-shot-bible",
            "gen_planning": "06-generation-plan",
            "generation": "07-generated-assets",
            "qc": "08-validation",
            "post": "09-post",
            "delivery": "10-delivery",
        }
        pdir = phase_dir_map.get(phase, phase)
        return self._root / project_id / pdir / f"{safe_id}.v{version}.json"

    def save(self, artifact: BaseModel, meta: ArtifactMetadata) -> Path:
        """Save an artifact's content and metadata to disk."""
        content_path = self._artifact_path(
            meta.project_id, meta.phase.value, meta.artifact_id, meta.version
        )
        meta_path = _meta_sidecar(content_path)
        content_path.parent.mkdir(parents=True, exist_ok=True)
        content_path.write_text(artifact.model_dump_json(indent=2))
        write_metadata(meta_path, meta)
        return content_path

    def save_dict(self, artifact: dict[str, Any], meta: ArtifactMetadata) -> Path:
        """Save a plain dict artifact (without Pydantic model wrapping)."""
        import json

        content_path = self._artifact_path(
            meta.project_id, meta.phase.value, meta.artifact_id, meta.version
        )
        meta_path = _meta_sidecar(content_path)
        content_path.parent.mkdir(parents=True, exist_ok=True)
        content_path.write_text(json.dumps(artifact, indent=2))
        write_metadata(meta_path, meta)
        return content_path

    def load(
        self, project_id: str, phase: FilmPhase, artifact_id: str, version: int
    ) -> dict[str, Any]:
        """Load an artifact's content as a raw dict."""
        p = self._artifact_path(project_id, phase.value, artifact_id, version)
        from json import loads

        data: dict[str, Any] = loads(p.read_text())
        return data

    def list_artifacts(
        self, project_id: str, phase: FilmPhase | None = None
    ) -> list[ArtifactMetadata]:
        """List all artifact metadata in a project, optionally filtered by phase."""
        base = self._root / project_id
        if phase is not None:
            phase_dir_map = {
                "intake": "intake",
                "constitution": "01-vision",
                "development": "02-development",
                "script": "03-script",
                "visual_dev": "04-visual-dev",
                "shot_bible": "05-shot-bible",
                "gen_planning": "06-generation-plan",
                "generation": "07-generated-assets",
                "qc": "08-validation",
                "post": "09-post",
                "delivery": "10-delivery",
            }
            base = base / phase_dir_map.get(phase.value, phase.value)
        results: list[ArtifactMetadata] = []
        for meta_path in base.rglob("*.meta.json"):
            results.append(read_metadata(meta_path))
        return results

    def next_version(self, project_id: str, phase: str, artifact_id: str) -> int:
        """Determine the next version number for an artifact.

        Scans existing artifact files in the phase directory and returns
        max(version) + 1, or 1 if no prior versions exist.
        """
        # Use version 1 as placeholder to get the parent directory
        phase_dir = self._artifact_path(project_id, phase, artifact_id, 1).parent
        if not phase_dir.exists():
            return 1

        safe_id = artifact_id.replace(":", "_").replace("/", "_")
        existing = list(phase_dir.glob(f"{safe_id}.v*.json"))
        if not existing:
            return 1

        versions: list[int] = []
        for p in existing:
            stem = p.stem  # e.g. "shot_matrix.v3"
            if ".v" in stem:
                try:
                    v = int(stem.split(".v")[-1])
                    versions.append(v)
                except ValueError:
                    continue

        return max(versions) + 1 if versions else 1

    def load_metadata(
        self, project_id: str, phase: str, artifact_id: str, version: int
    ) -> ArtifactMetadata:
        """Load only the metadata sidecar, not the full artifact body."""
        content_path = self._artifact_path(project_id, phase, artifact_id, version)
        meta_path = _meta_sidecar(content_path)
        return read_metadata(meta_path)


def _meta_sidecar(content_path: Path) -> Path:
    return content_path.with_suffix(content_path.suffix + ".meta.json")
