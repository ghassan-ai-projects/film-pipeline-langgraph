"""Intake submission / analysis / approval tools."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _active_project_id, _coerce_runtime_arg, _error, _ok, _services


async def submit_idea(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project. Create one first with create_film_project.")
    idea = str(args.get("idea", args.get("text", "")))
    if not idea:
        return _error("idea is required")
    # Inject the idea and run the graph through intake_node
    active["idea"] = idea
    user_runtime = _coerce_runtime_arg(args)
    if user_runtime > 0:
        active["target_runtime_seconds"] = user_runtime
    user_scene_count = args.get("target_scene_count")
    if isinstance(user_scene_count, int) and user_scene_count > 0:
        active["target_scene_count"] = user_scene_count
    state = rt.run_graph(active)
    # Update stored state
    rt.projects[active["project_id"]] = state
    return _ok(
        project_id=state["project_id"],
        current_phase=state.get("current_phase"),
        human_approval_required=state.get("human_approval_required"),
    )


async def get_intake_analysis(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    state = rt.get_project(project_id)
    if state is None:
        return _error("No active project.")
    from film_pipeline.schemas._base import FilmPhase

    try:
        data = _services(rt).artifact_store.load(
            project_id, FilmPhase("intake"), "intake_analysis", 1
        )
        return _ok(analysis=data)
    except (FileNotFoundError, ValueError):
        # Fall back to project state idea field
        idea = state.get("idea", "")
        if idea:
            return _ok(analysis={"raw_idea": idea, "note": "Intake not yet fully analyzed."})
        return _error("No intake analysis found. Submit an idea first.")


async def approve_intake(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    current_phase = str(active.get("current_phase", ""))
    if current_phase not in ("intake", ""):
        return _error(f"Current phase is '{current_phase}', not intake.")
    try:
        state = rt.approve_phase()
        return _ok(project_id=state["project_id"], current_phase=state.get("current_phase"))
    except ValueError as e:
        return _error(str(e))
