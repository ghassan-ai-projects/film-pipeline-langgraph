"""List/inspect artifacts, shots, scenes, references, and assets."""

from __future__ import annotations

from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.storage.manifest import read_manifest

from .helpers import (
    _error,
    _load_latest_reference_index,
    _ok,
    _services,
    require_project_id,
    require_project_state,
)


async def list_artifacts(args: dict[str, object]) -> dict[str, object]:
    """List all artifacts for the active project, optionally filtered by phase."""
    rt = tools_pkg.get_runtime()
    project_id = require_project_id(args)
    phase_str = args.get("phase")
    from film_pipeline.schemas.base import FilmPhase

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
    state = require_project_state(args)
    project_id = str(state["project_id"])
    artifact_id = str(args.get("artifact_id", ""))
    if not artifact_id:
        return _error("artifact_id is required.")
    phase_str = str(args.get("phase", state.get("current_phase", "")))
    version_raw = args.get("version")
    from film_pipeline.schemas.base import FilmPhase

    try:
        fp = FilmPhase(phase_str)
    except ValueError:
        return _error(f"Unknown phase: {phase_str}")
    store = _services(rt).artifact_store
    if version_raw is None:
        # No explicit version: load the artifact's latest version.
        version = max(1, store.latest_version(project_id, fp.value, artifact_id))
    else:
        version = int(str(version_raw)) if not isinstance(version_raw, int) else version_raw
    try:
        content = store.load(project_id, fp, artifact_id, version)
        return _ok(content=content)
    except FileNotFoundError:
        return _error(f"Artifact '{artifact_id}' not found in phase '{phase_str}'.")


def _load_shot_bible_rows(rt: Any, project_id: str) -> list[Any] | None:
    """Return the shot matrix rows from the project's shot bible, or None when absent."""
    from film_pipeline.schemas.base import FilmPhase

    store = _services(rt).artifact_store
    version = max(1, store.latest_version(project_id, "shot_bible", "shot_matrix"))
    try:
        data = store.load(project_id, FilmPhase("shot_bible"), "shot_matrix", version)
    except (FileNotFoundError, ValueError):
        return None
    return cast(list[Any], data.get("rows", []))


async def list_shots(args: dict[str, object]) -> dict[str, object]:
    """List shots from the shot bible artifact, if available."""
    rt = tools_pkg.get_runtime()
    project_id = require_project_id(args)
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
    project_id = require_project_id(args)
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
    project_id = require_project_id(args)
    from film_pipeline.schemas.base import FilmPhase

    store = _services(rt).artifact_store
    try:
        version = max(1, store.latest_version(project_id, "script", "script"))
        data = store.load(project_id, FilmPhase("script"), "script", version)
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
    state = require_project_state(args)
    project_id = str(state["project_id"])
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
    project_id = require_project_id(args)
    store = _services(rt).artifact_store
    manifest = read_manifest(project_id, root=store.root)
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
