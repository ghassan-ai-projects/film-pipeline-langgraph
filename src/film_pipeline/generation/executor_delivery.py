"""Delivery of completed generation jobs into the project asset tree.

Downloads a finished provider job's outputs, records every produced file
in the project asset manifest under the next take number, and returns the
paths recorded on the ledger row.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from film_pipeline.artifacts.manifest import (
    AssetEntry,
    AssetManifest,
    read_manifest,
    write_manifest,
)
from film_pipeline.artifacts.paths import generated_asset_dir

if TYPE_CHECKING:
    from film_pipeline.providers.base import BaseProviderAdapter, ProviderJob


def deliver_completed_job(
    root: Path,
    adapter: BaseProviderAdapter,
    job: ProviderJob,
    project_id: str,
    shot_id: str,
    shot_row: dict[str, Any],
) -> list[str]:
    """Download a completed job into the project asset tree + manifest."""
    scene_id = _scene_id_of(shot_row)
    output_dir = _prepare_output_dir(root, project_id, scene_id, shot_id)
    primary = adapter.download(job, str(output_dir))
    produced = _produced_files(output_dir)
    _record_assets(
        root=root, project_id=project_id, shot_id=shot_id, produced=produced, scene_id=scene_id
    )
    return _delivered_output_paths(primary, produced)


def _scene_id_of(shot_row: dict[str, Any]) -> str:
    """Scene a shot belongs to, or the ``unassigned`` placeholder."""
    return str(shot_row.get("scene_id", "") or "unassigned")


def _prepare_output_dir(root: Path, project_id: str, scene_id: str, shot_id: str) -> Path:
    """Create and return the directory for a shot's generated assets."""
    output_dir = generated_asset_dir(project_id, scene_id, shot_id, root=root)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _produced_files(output_dir: Path) -> list[Path]:
    """Files downloaded into *output_dir*, excluding metadata sidecars."""
    return sorted(
        path
        for path in output_dir.iterdir()
        if path.is_file() and not path.name.endswith("_metadata.json")
    )


def _delivered_output_paths(primary: str, produced: list[Path]) -> list[str]:
    """Primary output first, followed by any additional produced files."""
    return [primary, *[str(path) for path in produced if str(path) != primary]]


def _record_assets(
    root: Path,
    project_id: str,
    shot_id: str,
    produced: list[Path],
    scene_id: str,
) -> None:
    """Record every produced file in the asset manifest under the next take."""
    take = _next_take(root=root, project_id=project_id, shot_id=shot_id)
    manifest = read_manifest(project_id, root=root) or AssetManifest(project_id=project_id)
    for path in produced:
        kind = _asset_kind(path)
        manifest.add(
            AssetEntry(
                asset_id=f"{shot_id}:{kind}:take{take}",
                path=str(path),
                kind=kind,
                scene_id="" if scene_id == "unassigned" else scene_id,
                shot_id=shot_id,
                take=take,
                active=True,
            )
        )
    write_manifest(manifest, root=root)


def _next_take(root: Path, project_id: str, shot_id: str) -> int:
    manifest = read_manifest(project_id, root=root)
    if manifest is None:
        return 1
    takes = [entry.take for entry in manifest.entries if entry.shot_id == shot_id]
    return max(takes, default=0) + 1


def _asset_kind(path: Path) -> str:
    name = path.name.lower()
    if name.endswith("_last.png"):
        return "last_frame"
    if name.endswith("_mid.png"):
        return "mid_frame"
    if path.suffix.lower() in {".mp4", ".mov", ".webm"}:
        return "generated_clip"
    if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        return "reference_sheet"
    if path.suffix.lower() in {".wav", ".mp3"}:
        return "audio_stem"
    return "generated_clip"
