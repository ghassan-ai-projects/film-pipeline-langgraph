"""Canonical path resolution per project, phase, and artifact type.

Every artifact path must flow through this module. No other module constructs
paths manually. All helpers require an explicit storage ``root`` — there is no
implicit default (see ``artifacts.storage`` for root resolution).
"""

from __future__ import annotations

from pathlib import Path

#: Phase name → directory name. Single source of truth, derived from the
#: pipeline phase vocabulary and shared with legacy-layout detection.
PHASE_DIR_MAP: dict[str, str] = {
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


def project_dir(project_slug: str, root: Path) -> Path:
    return root / project_slug


def phase_dir(project_slug: str, phase: str, root: Path) -> Path:
    return project_dir(project_slug, root) / PHASE_DIR_MAP.get(phase, phase)


def artifact_dir(project_slug: str, phase: str, artifact_id: str, root: Path) -> Path:
    safe_id = artifact_id.replace(":", "_").replace("/", "_")
    return phase_dir(project_slug, phase, root) / safe_id


def artifact_path(
    project_slug: str, phase: str, artifact_id: str, version: int, root: Path
) -> Path:
    return artifact_dir(project_slug, phase, artifact_id, root) / "versions" / f"v{version:03}.json"


def current_artifact_path(project_slug: str, phase: str, artifact_id: str, root: Path) -> Path:
    return artifact_dir(project_slug, phase, artifact_id, root) / "current.json"


def generated_asset_dir(project_slug: str, scene_id: str, shot_id: str, root: Path) -> Path:
    return phase_dir(project_slug, "generation", root) / "scenes" / scene_id / shot_id


def reference_dir(project_slug: str, ref_type: str, root: Path) -> Path:
    return project_dir(project_slug, root) / "references" / ref_type


def version_dir(project_slug: str, root: Path) -> Path:
    return project_dir(project_slug, root) / "versions"


def checkpoint_dir(project_slug: str, root: Path) -> Path:
    return version_dir(project_slug, root) / "checkpoints"


def state_dir(project_slug: str, root: Path) -> Path:
    return project_dir(project_slug, root) / "state"
