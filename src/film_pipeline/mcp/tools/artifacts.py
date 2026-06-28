"""List/inspect artifacts, shots, scenes, and references."""

from __future__ import annotations

from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _error, _load_latest_reference_index, _ok, _services


async def list_artifacts(args: dict[str, object]) -> dict[str, object]:
    """List all artifacts for the active project, optionally filtered by phase."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
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
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    artifact_id = str(args.get("artifact_id", ""))
    if not artifact_id:
        return _error("artifact_id is required.")
    phase_str = str(args.get("phase", active.get("current_phase", "")))
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


async def list_shots(args: dict[str, object]) -> dict[str, object]:
    """List shots from the shot bible artifact, if available."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.schemas._base import FilmPhase

    try:
        data = _services(rt).artifact_store.load(
            project_id, FilmPhase("shot_bible"), "shot_matrix", 1
        )
        shots = data.get("rows", [])
        return _ok(shots=shots)
    except (FileNotFoundError, ValueError):
        return _ok(shots=[], note="Shot bible not yet generated.")


async def inspect_shot(args: dict[str, object]) -> dict[str, object]:
    """Inspect a specific shot by ID from the shot bible."""
    shot_id = str(args.get("shot_id", ""))
    if not shot_id:
        return _error("shot_id is required.")
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.schemas._base import FilmPhase

    try:
        data = _services(rt).artifact_store.load(
            project_id, FilmPhase("shot_bible"), "shot_matrix", 1
        )
        shots = data.get("rows", [])
        match = next(
            (s for s in shots if str(s.get("shot_id", s.get("scene_id", ""))) == shot_id), None
        )
        if match is None:
            return _error(f"Shot '{shot_id}' not found.")
        return _ok(shot=match)
    except (FileNotFoundError, ValueError):
        return _error("Shot bible not yet generated.")


async def inspect_scene(args: dict[str, object]) -> dict[str, object]:
    """Inspect a specific scene from the script artifact."""
    scene_id = str(args.get("scene_id", ""))
    if not scene_id:
        return _error("scene_id is required.")
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
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
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    data = _load_latest_reference_index(rt, project_id, active)
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
