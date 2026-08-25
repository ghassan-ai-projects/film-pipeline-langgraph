"""List/inspect artifacts, shots, scenes, references, and assets."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.artifacts.manifest import read_manifest

from .helpers import _active_project_id, _error, _load_latest_reference_index, _ok, _services


async def list_artifacts(args: dict[str, object]) -> dict[str, object]:
    """List all artifacts for the active project, optionally filtered by phase."""
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    phase_str = args.get("phase")
    from film_pipeline.schemas._base import FilmPhase

    fp = None
    if phase_str:
        try:
            fp = FilmPhase(str(phase_str))
        except ValueError:
            return _error(f"Unknown phase: {phase_str}")
    artifacts = _services(rt).artifact_store.list_artifacts(project_id, fp)
    return _ok(
        artifacts=[
            {
                "artifact_id": a.artifact_id,
                "artifact_type": a.artifact_type,
                "phase": str(a.phase.value),
                "version": a.version,
                "status": a.status,
            }
            for a in artifacts
        ]
    )


async def inspect_artifact(args: dict[str, object]) -> dict[str, object]:
    """Load and return the content of a specific artifact."""
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    state = rt.get_project(project_id)
    if state is None:
        return _error("No active project.")
    artifact_id = str(args.get("artifact_id", ""))
    if not artifact_id:
        return _error("artifact_id is required.")
    phase_str = str(args.get("phase", state.get("current_phase", "")))
    version_raw = args.get("version", 1)
    version = int(str(version_raw)) if not isinstance(version_raw, int) else version_raw
    from film_pipeline.schemas._base import FilmPhase

    try:
        fp = FilmPhase(phase_str)
    except ValueError:
        return _error(f"Unknown phase: {phase_str}")
    try:
        content = _services(rt).artifact_store.load(project_id, fp, artifact_id, version)
        return _ok(content=content)
    except FileNotFoundError:
        return _error(f"Artifact '{artifact_id}' not found in phase '{phase_str}'.")


def _load_shot_bible_rows(rt: Any, project_id: str) -> list[Any] | None:
    """Return the shot matrix rows from the project's shot bible, or None when absent."""
    from film_pipeline.schemas._base import FilmPhase

    try:
        data = _services(rt).artifact_store.load(
            project_id, FilmPhase("shot_bible"), "shot_matrix", 1
        )
    except (FileNotFoundError, ValueError):
        return None
    return cast(list[Any], data.get("rows", []))


async def list_shots(args: dict[str, object]) -> dict[str, object]:
    """List shots from the shot bible artifact, if available."""
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    shots = _load_shot_bible_rows(rt, project_id)
    if shots is None:
        return _ok(shots=[], note="Shot bible not yet generated.")
    return _ok(shots=shots)


async def inspect_shot(args: dict[str, object]) -> dict[str, object]:
    """Inspect a specific shot by ID from the shot bible."""
    shot_id = str(args.get("shot_id", ""))
    if not shot_id:
        return _error("shot_id is required.")
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    shots = _load_shot_bible_rows(rt, project_id)
    if shots is None:
        return _error("Shot bible not yet generated.")
    match = next(
        (s for s in shots if str(s.get("shot_id", s.get("scene_id", ""))) == shot_id), None
    )
    if match is None:
        return _error(f"Shot '{shot_id}' not found.")
    return _ok(shot=match)


async def inspect_scene(args: dict[str, object]) -> dict[str, object]:
    """Inspect a specific scene from the script artifact."""
    scene_id = str(args.get("scene_id", ""))
    if not scene_id:
        return _error("scene_id is required.")
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    from film_pipeline.schemas._base import FilmPhase

    try:
        data = _services(rt).artifact_store.load(project_id, FilmPhase("script"), "script", 1)
        scenes = data.get("scenes", [])
        match = next((s for s in scenes if str(s.get("scene_id", "")) == scene_id), None)
        if match is None:
            return _error(f"Scene '{scene_id}' not found.")
        return _ok(scene=match)
    except (FileNotFoundError, ValueError):
        return _error("Script artifact not yet generated.")


async def inspect_reference(args: dict[str, object]) -> dict[str, object]:
    """Inspect a reference by ID from the visual development phase."""
    reference_id = str(args.get("reference_id", ""))
    if not reference_id:
        return _error("reference_id is required.")
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    state = rt.get_project(project_id)
    if state is None:
        return _error("No active project.")
    data = _load_latest_reference_index(rt, project_id, state)
    if data is None:
        return _error("Reference index not yet generated.")
    refs = cast(list[Any], data.get("entries", data.get("references", data.get("items", []))))
    match = next(
        (r for r in refs if str(r.get("reference_id", r.get("id", ""))) == reference_id),
        None,
    )
    if match is None:
        return _error(f"Reference '{reference_id}' not found.")
    return _ok(reference=match)


async def list_assets(args: dict[str, object]) -> dict[str, object]:
    """List generated/reference assets from the project asset manifest."""
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    store = _services(rt).artifact_store
    root = getattr(store, "_root", None)
    if not isinstance(root, Path):
        root = Path("projects")
    manifest = read_manifest(project_id, root=root)
    if manifest is None:
        return _ok(assets=[])
    return _ok(
        assets=[
            {
                "asset_id": entry.asset_id,
                "kind": entry.kind,
                "scene_id": entry.scene_id,
                "shot_id": entry.shot_id,
                "take": entry.take,
                "active": entry.active,
                "path": entry.path,
            }
            for entry in manifest.entries
        ]
    )
