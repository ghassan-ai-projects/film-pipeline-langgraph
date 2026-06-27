"""Canonical path resolution per project, phase, and artifact type.

Every artifact path must flow through this module. No other module constructs
paths manually.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path("projects")


def project_dir(project_slug: str) -> Path:
    return ROOT / project_slug


def phase_dir(project_slug: str, phase: str) -> Path:
    mapping: dict[str, str] = {
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
    return project_dir(project_slug) / mapping.get(phase, phase)


def artifact_path(project_slug: str, phase: str, artifact_id: str, version: int) -> Path:
    safe_id = artifact_id.replace(":", "_").replace("/", "_")
    return phase_dir(project_slug, phase) / safe_id / "versions" / f"v{version:03}.json"


def generated_asset_dir(project_slug: str, scene_id: str, shot_id: str) -> Path:
    return phase_dir(project_slug, "generation") / "scenes" / scene_id / shot_id


def reference_dir(project_slug: str, ref_type: str) -> Path:
    return project_dir(project_slug) / "references" / ref_type


def version_dir(project_slug: str) -> Path:
    return project_dir(project_slug) / "versions"


def checkpoint_dir(project_slug: str) -> Path:
    return version_dir(project_slug) / "checkpoints"


def state_dir(project_slug: str) -> Path:
    return project_dir(project_slug) / "state"
