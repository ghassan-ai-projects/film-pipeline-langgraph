"""Artifact store — save, load, list, version, supersede.

The canonical registry for all typed artifacts. Every phase writes artifacts
through this store so the project directory stays consistent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from film_pipeline.artifacts.metadata import read_metadata, write_metadata
from film_pipeline.artifacts.paths import (
    artifact_dir,
    artifact_path,
    current_artifact_path,
    phase_dir,
)
from film_pipeline.schemas._base import ArtifactStatus, FilmPhase
from film_pipeline.schemas.artifact import ArtifactMetadata


class ArtifactStore:
    """Persist and retrieve typed artifacts with metadata and versioning."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        """The storage root this store reads and writes."""
        return self._root

    def _artifact_path(self, project_id: str, phase: str, artifact_id: str, version: int) -> Path:
        return artifact_path(project_id, phase, artifact_id, version, root=self._root)

    def _current_path(self, project_id: str, phase: str, artifact_id: str) -> Path:
        return current_artifact_path(project_id, phase, artifact_id, root=self._root)

    def save(self, artifact: BaseModel, meta: ArtifactMetadata) -> Path:
        """Save an artifact's content and metadata to disk."""
        version_path = self._artifact_path(
            meta.project_id, meta.phase.value, meta.artifact_id, meta.version
        )
        current_path = self._current_path(meta.project_id, meta.phase.value, meta.artifact_id)
        payload = artifact.model_dump(mode="json")
        content = artifact.model_dump_json(indent=2)
        _write_artifact_files(version_path, current_path, content, payload, meta)
        return current_path

    def load(
        self, project_id: str, phase: FilmPhase, artifact_id: str, version: int
    ) -> dict[str, Any]:
        """Load an artifact's content as a raw dict."""
        content_path = self._artifact_path(project_id, phase.value, artifact_id, version)
        data: dict[str, Any] = json.loads(content_path.read_text())
        return data

    def list_artifacts(
        self, project_id: str, phase: FilmPhase | None = None
    ) -> list[ArtifactMetadata]:
        """List all artifact metadata in a project, optionally filtered by phase."""
        base = self._root / project_id
        if phase is not None:
            base = phase_dir(project_id, phase.value, root=self._root)
        results: list[ArtifactMetadata] = []
        for meta_path in base.rglob("current.meta.json"):
            results.append(read_metadata(meta_path))
        return results

    def next_version(self, project_id: str, phase: str, artifact_id: str) -> int:
        """Determine the next version number for an artifact.

        Scans existing artifact files in the phase directory and returns
        max(version) + 1, or 1 if no prior versions exist.
        """
        version_dir = artifact_dir(project_id, phase, artifact_id, root=self._root) / "versions"
        if not version_dir.exists():
            return 1

        existing = list(version_dir.glob("v*.json"))
        if not existing:
            return 1

        versions: list[int] = []
        for p in existing:
            try:
                versions.append(int(p.stem.removeprefix("v")))
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

    def approve(
        self,
        project_id: str,
        phase: str,
        artifact_id: str,
        version: int,
        approval_ref: str | None = None,
    ) -> ArtifactMetadata:
        """Transition an artifact version from CANDIDATE to APPROVED."""
        return self._transition_status(
            project_id,
            phase,
            artifact_id,
            version,
            expected_status=ArtifactStatus.CANDIDATE,
            next_status=ArtifactStatus.APPROVED,
            action="approve",
            extra_updates={"approval_ref": approval_ref},
        )

    def supersede(
        self, project_id: str, phase: str, artifact_id: str, version: int
    ) -> ArtifactMetadata:
        """Transition an artifact version from APPROVED to SUPERSEDED."""
        return self._transition_status(
            project_id,
            phase,
            artifact_id,
            version,
            expected_status=ArtifactStatus.APPROVED,
            next_status=ArtifactStatus.SUPERSEDED,
            action="supersede",
        )

    def _transition_status(
        self,
        project_id: str,
        phase: str,
        artifact_id: str,
        version: int,
        expected_status: ArtifactStatus,
        next_status: ArtifactStatus,
        action: str,
        extra_updates: dict[str, Any] | None = None,
    ) -> ArtifactMetadata:
        """Require one status on a version and persist its successor."""
        meta = self.load_metadata(project_id, phase, artifact_id, version)
        if meta.status != expected_status:
            raise ValueError(
                f"Cannot {action} {artifact_id} v{version}: status is {meta.status.value}, "
                f"expected {expected_status.value}"
            )
        updated = meta.model_copy(update={"status": next_status, **(extra_updates or {})})
        self._write_metadata_for(project_id, phase, artifact_id, version, updated)
        return updated

    def _write_metadata_for(
        self,
        project_id: str,
        phase: str,
        artifact_id: str,
        version: int,
        meta: ArtifactMetadata,
    ) -> None:
        """Persist metadata to both the version sidecar and current sidecar."""
        version_path = self._artifact_path(project_id, phase, artifact_id, version)
        current_path = self._current_path(project_id, phase, artifact_id)
        write_metadata(_meta_sidecar(version_path), meta)
        write_metadata(_meta_sidecar(current_path), meta)


def _meta_sidecar(content_path: Path) -> Path:
    return content_path.with_suffix(".meta.json")


def _write_artifact_files(
    version_path: Path,
    current_path: Path,
    content: str,
    payload: dict[str, Any],
    meta: ArtifactMetadata,
) -> None:
    version_path.parent.mkdir(parents=True, exist_ok=True)
    current_path.parent.mkdir(parents=True, exist_ok=True)
    version_path.write_text(content)
    current_path.write_text(content)
    write_metadata(_meta_sidecar(version_path), meta)
    write_metadata(_meta_sidecar(current_path), meta)
    current_path.with_suffix(".md").write_text(_render_markdown(meta, payload))


def _render_markdown(meta: ArtifactMetadata, payload: dict[str, Any]) -> str:
    title = f"# {meta.artifact_id}\n\n"
    details = [
        f"- phase: {meta.phase.value}",
        f"- type: {meta.artifact_type.value}",
        f"- version: {meta.version}",
        f"- status: {meta.status.value}",
    ]
    body = _markdown_body(payload)
    detail_text = "\n".join(details)
    return f"{title}{detail_text}\n\n{body}\n"


def _markdown_body(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("text"), str):
        return str(payload["text"])
    if isinstance(payload.get("treatment"), dict) and isinstance(
        payload["treatment"].get("text"), str
    ):
        return str(payload["treatment"]["text"])
    scenes = _scene_rows(payload)
    if scenes:
        return "\n\n".join(_scene_markdown(scene) for scene in scenes)
    return "\n".join(f"- {key}: {_markdown_value(value)}" for key, value in payload.items())


def _scene_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    scene_list = payload.get("scene_list")
    nested = scene_list.get("scenes", []) if isinstance(scene_list, dict) else []
    rows: list[dict[str, Any]] = []
    for container in (payload.get("scenes"), payload.get("rows"), nested):
        if isinstance(container, list):
            rows.extend(row for row in container if isinstance(row, dict))
    return rows


def _scene_markdown(scene: dict[str, Any]) -> str:
    heading = str(scene.get("scene_heading", scene.get("scene_id", "Scene")))
    lines = [f"## {heading}"]
    for key in (
        "scene_id",
        "dramatic_function",
        "story_function",
        "conflict",
        "outcome",
        "environment",
        "viewpoint",
        "camera_profile",
        "camera_movement",
        "movement",
    ):
        if scene.get(key):
            lines.append(f"- {key}: {scene[key]}")
    for action in scene.get("action_lines", []):
        lines.append(str(action))
    for dialogue in scene.get("dialogue", []):
        if isinstance(dialogue, dict):
            character = str(dialogue.get("character_id", "")).upper()
            direction = str(dialogue.get("direction", ""))
            line = str(dialogue.get("line", ""))
            lines.append(f"{character} {f'({direction}) ' if direction else ''}{line}".strip())
    for key in ("characters", "asset_refs", "reference_refs", "validation_refs"):
        if scene.get(key):
            lines.append(f"- {key}: {_markdown_value(scene[key])}")
    return "\n".join(lines)


def _markdown_value(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return f"{len(value)} field(s)"
    return str(value)
