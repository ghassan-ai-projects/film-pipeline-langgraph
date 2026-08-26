"""Project create / list / find / active / summary tools."""

from __future__ import annotations

from typing import Any, cast

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.config.profile_resolver import (
    canonicalize_profile_stack,
    missing_provider_credentials,
    register_project_providers,
    resolve_project_config,
)

from .helpers import (
    _active_project_state,
    _coerce_runtime_arg,
    _collect_profile_models,
    _collect_profile_providers,
    _error,
    _ok,
    _services,
)


def _resolve_runtime_mode(
    args: dict[str, object], server_mode: str
) -> tuple[str, dict[str, object] | None]:
    """Align the requested runtime mode with the MCP server mode.

    Returns the effective runtime mode plus an error payload when the
    request is rejected (empty error payload on success).
    """
    # --- Runtime mode alignment ---
    requested_mode = str(args.get("runtime_mode", "")).lower()
    if requested_mode not in ("", "mock", "real"):
        return "", _error(f"runtime_mode must be 'mock' or 'real', got '{requested_mode}'")

    runtime_mode = requested_mode or server_mode
    if runtime_mode != server_mode:
        return (
            "",
            _error(
                "Project runtime_mode must match the MCP server mode.",
                server_mode=server_mode,
                requested_runtime_mode=runtime_mode,
            ),
        )
    return runtime_mode, None


def _reject_mock_ids(args: dict[str, object], runtime_mode: str) -> dict[str, object] | None:
    """Reject mock provider/model ids when running in real mode."""
    if runtime_mode != "real":
        return None
    for pid in _collect_profile_providers(args):
        if pid.startswith("mock-"):
            return _error(f"Provider '{pid}' is not allowed in real mode.")
    for mid in _collect_profile_models(args):
        if mid.startswith("mock-"):
            return _error(f"Model '{mid}' is not allowed in real mode.")
    return None


def _extract_conflicts(resolved_config: dict[str, Any]) -> list[Any]:
    """Normalize the conflict list reported by the profile resolver."""
    return list(cast(list[Any], resolved_config.get("conflicts", [])))


def _validate_resolved_profile(
    profile_stack: Any,
    resolved_config: dict[str, Any],
    runtime_mode: str,
) -> dict[str, object] | None:
    """Reject blocking conflicts and missing real-mode provider credentials."""
    conflicts = _extract_conflicts(resolved_config)
    if conflicts:
        blocking = [c for c in conflicts if c.get("severity") == "blocking"]
        if blocking:
            return _error(
                "Resolved profile stack has blocking conflicts.",
                conflicts=conflicts,
            )
    if runtime_mode == "real":
        missing_credentials = missing_provider_credentials(
            profile_stack, cast(dict[str, object], resolved_config.get("raw", {}))
        )
        if missing_credentials:
            return _error(
                "Real-mode provider credentials are missing.",
                missing_credentials=missing_credentials,
            )
    return None


def _populate_project_state(
    state: dict[str, object],
    args: dict[str, object],
    *,
    profile_stack: Any,
    resolved_config: dict[str, Any],
    runtime_mode: str,
    server_mode: str,
) -> None:
    """Persist runtime mode and resolved profile stack onto the project state."""
    state["runtime_mode"] = runtime_mode
    state["profile_stack"] = profile_stack
    state["server_mode"] = server_mode
    state["resolved_config"] = cast(dict[str, object], resolved_config.get("raw", {}))
    state["resolved_config_sources"] = resolved_config["sources"]
    state["config_conflicts"] = _extract_conflicts(resolved_config)
    state["generation_policy"] = str(args.get("generation_policy", "generate"))
    user_runtime = _coerce_runtime_arg(args)
    if user_runtime > 0:
        # User-supplied expected length is authoritative for the whole pipeline.
        state["target_runtime_seconds"] = user_runtime


def _audit_project_creation(rt: Any, project_id: str, runtime_mode: str, server_mode: str) -> None:
    """Record the project creation in the runtime audit trail."""
    rt._record_audit(
        "system",
        "create_film_project",
        project_id=project_id,
        runtime_mode=runtime_mode,
        server_mode=server_mode,
    )


def _run_intake_for_idea(
    rt: Any, state: dict[str, object], args: dict[str, object], project_id: str
) -> dict[str, object]:
    """Run the intake graph when an idea accompanies the request."""
    idea = str(args.get("idea", "")).strip()
    if idea:
        rt.set_active(project_id)
        state["idea"] = idea
        state = rt.run_graph(state)
        state["generation_policy"] = str(args.get("generation_policy", "generate"))
        rt.projects[project_id] = state
    return state


async def create_film_project(args: dict[str, object]) -> dict[str, object]:
    """Create a new film project — wired to runtime.

    Accepts optional profile stack and runtime_mode. In ``real`` mode,
    mock providers and models are rejected.
    """
    rt = tools_pkg.get_runtime()
    project_id = str(args.get("project_id", ""))
    if not project_id:
        return _error("project_id is required")

    server_mode = rt.server_mode
    runtime_mode, mode_error = _resolve_runtime_mode(args, server_mode)
    if mode_error is not None:
        return mode_error

    mock_error = _reject_mock_ids(args, runtime_mode)
    if mock_error is not None:
        return mock_error

    try:
        profile_stack = canonicalize_profile_stack(args)
        resolved_config = resolve_project_config(profile_stack)
        profile_error = _validate_resolved_profile(profile_stack, resolved_config, runtime_mode)
        if profile_error is not None:
            return profile_error

        state = rt.create_project(
            project_id=project_id,
            title=str(args.get("title", "")),
            slug=str(args.get("slug", "")),
        )
        _populate_project_state(
            state,
            args,
            profile_stack=profile_stack,
            resolved_config=resolved_config,
            runtime_mode=runtime_mode,
            server_mode=server_mode,
        )
        register_project_providers(
            rt, profile_stack, cast(dict[str, object], resolved_config.get("raw", {}))
        )
        _audit_project_creation(rt, project_id, runtime_mode, server_mode)
        state = _run_intake_for_idea(rt, state, args, project_id)
        return _ok(
            project_id=project_id,
            current_phase=str(state.get("current_phase", "")),
            state=state,
        )
    except ValueError as e:
        return _error(str(e))


async def list_projects(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    return _ok(projects=list(rt.projects.keys()))


async def find_project(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    ref = str(args.get("ref", ""))
    if not ref:
        return _error("ref is required (project_id or slug)")
    # Try direct lookup by project_id
    project = rt.get_project(ref)
    if project is not None:
        return _ok(project_id=project["project_id"], slug=project.get("slug", ""))
    # Try lookup by slug
    for pid, pstate in rt.projects.items():
        if pstate.get("slug") == ref:
            return _ok(project_id=pid, slug=ref)
    return _error(f"Project '{ref}' not found.")


async def set_active_project(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    project_id = str(args.get("project_ref", args.get("project_id", "")))
    if not project_id:
        return _error("project_ref is required")
    try:
        rt.set_active(project_id)
        return _ok(active_project_id=project_id)
    except ValueError as e:
        return _error(str(e))


async def get_active_project(args: dict[str, object]) -> dict[str, object]:
    state = _active_project_state(args)
    if state is None:
        return _error("No active project set")
    return _ok(project_id=state["project_id"], current_phase=state.get("current_phase"))


def _collect_artifact_summaries(store: Any, project_id: str) -> list[dict[str, object]]:
    """Summarize every stored artifact of a project across all film phases."""
    # Imported here to match the lazy-import pattern used by tools.helpers,
    # which keeps tool-module import time independent of schema enum loading.
    from film_pipeline.schemas._base import FilmPhase

    summaries: list[dict[str, object]] = []
    for phase in FilmPhase:
        try:
            artifacts = store.list_artifacts(project_id, phase)
            for artifact in artifacts:
                summaries.append(
                    {
                        "artifact_id": artifact.artifact_id,
                        "artifact_type": str(artifact.artifact_type.value),
                        "phase": str(artifact.phase.value),
                        "version": artifact.version,
                        "status": str(artifact.status.value),
                    }
                )
        except Exception:
            continue
    return summaries


async def get_project_summary(args: dict[str, object]) -> dict[str, object]:
    """Return a summary of the active project: phase, artifacts, issues, and handoffs."""
    rt = tools_pkg.get_runtime()
    state = _active_project_state(args)
    if state is None:
        return _error("No active project.")
    project_id = str(state["project_id"])
    artifact_summary = _collect_artifact_summaries(_services(rt).artifact_store, project_id)
    routing = state.get("_routing_decisions", [])

    return _ok(
        project_id=project_id,
        title=state.get("title", state.get("idea", ""))[:200],
        slug=state.get("slug", ""),
        current_phase=state.get("current_phase", ""),
        approved=state.get("approved"),
        artifact_count=len(artifact_summary),
        artifacts=artifact_summary,
        issue_count=len(state.get("issues", [])),
        routing_decisions_count=len(routing),
        has_blockers=any(i.get("severity") == "blocking" for i in state.get("issues", [])),
        generation_policy=str(state.get("generation_policy", "generate")),
    )
