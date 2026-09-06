"""Shared helpers used across MCP tool modules.

Contains the basic response builders, runtime/service accessors, and
profile/config resolution helpers used by ``create_film_project`` and
other tools that need to load and merge profile stacks.
"""

from __future__ import annotations

import contextlib
from typing import Any

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.config.profile_resolver import load_profile_flex


def _stub(handler_name: str, **extra: object) -> dict[str, object]:
    """Build a stub response that callers can detect before full wiring."""
    return {
        "stub": True,
        "handler": handler_name,
        "message": "Not yet wired to orchestrator.",
        **extra,
    }


def _ok(**extra: object) -> dict[str, object]:
    """Build a success response."""
    return {"ok": True, **extra}


def _error(message: str, **extra: object) -> dict[str, object]:
    """Build an error response."""
    return {"ok": False, "error": message, **extra}


def _active_project_id(args: dict[str, object], rt: Any) -> str | None:
    """Return the project id for the current request.

    Prefers the project resolved from ``project_ref`` in the request envelope,
    then falls back to the runtime's active project. Returns ``None`` when no
    project can be determined.
    """
    envelope = args.get("_envelope")
    resolved = getattr(envelope, "resolved_project_id", None) if envelope is not None else None
    if resolved:
        return str(resolved)
    active = rt.get_active()
    if active is not None:
        return str(active["project_id"])
    return None


def _active_project_with_state(
    args: dict[str, object], rt: Any
) -> tuple[str, dict[str, Any]] | None:
    """Return the resolved project id and its state, or ``None`` when absent."""
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return None
    state = rt.get_project(project_id)
    if state is None:
        return None
    return project_id, state


def _active_project_state(args: dict[str, object]) -> dict[str, Any] | None:
    """Return the active project's state, or ``None`` when none resolves.

    ``get_runtime`` must keep being resolved through the package attribute at
    call time (never via a ``from`` import): tests monkeypatch
    ``film_pipeline.mcp.tools.get_runtime`` by attribute, and only lazy
    binding sees the patch.
    """
    rt = tools_pkg.get_runtime()
    resolved = _active_project_with_state(args, rt)
    return None if resolved is None else resolved[1]


def _store_project_state(rt: Any, project_id: str, state: dict[str, Any]) -> None:
    """Store the exact state object in the runtime and persist it."""
    rt.projects[project_id] = state
    rt._persist_project_state(project_id)


def _services(rt: object) -> Any:
    """Assert services are initialized and return them."""
    assert hasattr(rt, "services") and rt.services is not None
    return rt.services


def _register_active_artifact_ref(
    rt: Any, active: dict[str, Any], project_id: str, state_key: str, ref: object
) -> None:
    """Record an artifact reference on the active project and persist state."""
    active[state_key] = ref
    active.setdefault("artifact_refs", []).append(ref)
    _store_project_state(rt, project_id, active)


def _coerce_runtime_arg(args: dict[str, object]) -> int:
    """Read the user-supplied expected length from tool args.

    Accepts ``target_runtime_seconds`` (preferred) or ``target_runtime_minutes``.
    Returns 0 when unspecified (intake will then estimate from the idea).
    """
    raw_seconds = args.get("target_runtime_seconds")
    if raw_seconds is not None:
        try:
            seconds = int(float(str(raw_seconds)))
            if seconds > 0:
                return seconds
        except (TypeError, ValueError):
            pass
    raw_minutes = args.get("target_runtime_minutes")
    if raw_minutes is not None:
        try:
            minutes = float(str(raw_minutes))
            if minutes > 0:
                return int(minutes * 60)
        except (TypeError, ValueError):
            pass
    return 0


def _profile_source(
    args: dict[str, object],
    key: str,
    prefixes: tuple[str, ...],
) -> Any | None:
    """Load the profile named by ``args[key]``, or ``None`` when absent/unloadable."""
    val = args.get(key)
    if not val or not isinstance(val, str):
        return None
    try:
        _loader, src = load_profile_flex(str(val), prefixes)
    except FileNotFoundError:
        return None
    return src


def _dict_entry_ids(entries: Any, field: str) -> list[str]:
    """Collect non-empty ``field`` strings from the dict entries in ``entries``."""
    ids: list[str] = []
    for entry in entries:
        if isinstance(entry, dict):
            value = str(entry.get(field, ""))
            if value:
                ids.append(value)
    return ids


def _order_provider_ids(order_entries: Any) -> list[str]:
    """Collect non-empty provider ids from a profile's ``order`` list."""
    ids: list[str] = []
    for provider_id in order_entries:
        pid = str(provider_id)
        if pid:
            ids.append(pid)
    return ids


def _provider_ids_from_raw(raw: Any) -> list[str]:
    """Collect provider ids from a resolved provider profile's raw mapping."""
    providers = raw.get("providers", {})
    pids: list[str] = []
    for section in ("video", "image"):
        pids.extend(_dict_entry_ids(providers.get(section, []), "provider_id"))
    pids.extend(_order_provider_ids(providers.get("order", [])))
    return pids


def _model_ids_from_raw(raw: Any) -> list[str]:
    """Collect model ids from a resolved quality profile's raw mapping."""
    models = raw.get("models", {})
    return _dict_entry_ids(models.get("available", []), "model_id")


def _collect_profile_providers(args: dict[str, object]) -> list[str]:
    """Extract provider ids from profile args for real-mode rejection."""
    pids: list[str] = []
    for key in ("provider_profile",):
        src = _profile_source(args, key, ("provider",))
        if src is not None:
            pids.extend(_provider_ids_from_raw(src.raw))
    return pids


def _collect_profile_models(args: dict[str, object]) -> list[str]:
    """Extract model ids from profile args for real-mode rejection."""
    mids: list[str] = []
    for key in ("quality_profile",):
        src = _profile_source(args, key, ("quality",))
        if src is not None:
            mids.extend(_model_ids_from_raw(src.raw))
    return mids


def _load_artifact(
    store: Any, project_id: str, fp: Any, artifact_id: str, version: int
) -> dict[str, Any] | None:
    """Try to load an artifact from the artifact store."""
    try:
        return store.load(project_id, fp, artifact_id, version)  # type: ignore[no-any-return]
    except (FileNotFoundError, AttributeError):
        return None


def _latest_artifact_version(store: Any, project_id: str, fp: Any, artifact_id: str) -> int:
    artifacts = store.list_artifacts(project_id, fp)
    versions = [artifact.version for artifact in artifacts if artifact.artifact_id == artifact_id]
    return max(versions) if versions else 0


def _load_latest_reference_index(
    rt: Any,
    project_id: str,
    state: dict[str, object] | None = None,
) -> dict[str, object] | None:
    from film_pipeline.schemas._base import FilmPhase

    store = _services(rt).artifact_store
    version = 0
    if state is not None:
        visual_ref = str(state.get("visual_refs", ""))
        if visual_ref.startswith("artifact:reference_index:v"):
            with contextlib.suppress(ValueError):
                version = int(visual_ref.rsplit(":v", 1)[1])
    if version <= 0:
        version = _latest_artifact_version(
            store, project_id, FilmPhase("visual_dev"), "reference_index"
        )
    if version <= 0:
        return None
    return _load_artifact(store, project_id, FilmPhase("visual_dev"), "reference_index", version)


def _report_summary(report: Any) -> dict[str, Any]:
    """Convert a ValidationReport into a concise summary dict."""
    return {
        "validator_id": report.validator_id,
        "score": report.score,
        "status": str(report.status.value),
        "blocking_count": len(report.blocking_issues),
        "warning_count": len(report.warnings),
        "recommended_actions": report.recommended_actions,
    }
