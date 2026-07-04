"""Shared helpers used across MCP tool modules.

Contains the basic response builders, runtime/service accessors, and
profile/config resolution helpers used by ``create_film_project`` and
other tools that need to load and merge profile stacks.
"""

from __future__ import annotations

import contextlib
from typing import Any

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


def _services(rt: object) -> Any:
    """Assert services are initialized and return them."""
    assert hasattr(rt, "services") and rt.services is not None
    return rt.services


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


def _collect_profile_providers(args: dict[str, object]) -> list[str]:
    """Extract provider ids from profile args for real-mode rejection."""
    pids: list[str] = []
    for key in ("provider_profile",):
        val = args.get(key)
        if val and isinstance(val, str) and val:
            try:
                _loader, src = load_profile_flex(str(val), ("provider",))
                providers = src.raw.get("providers", {})
                for section in ("video", "image"):
                    for entry in providers.get(section, []):
                        if isinstance(entry, dict):
                            pid = str(entry.get("provider_id", ""))
                            if pid:
                                pids.append(pid)
                for provider_id in providers.get("order", []):
                    pid = str(provider_id)
                    if pid:
                        pids.append(pid)
            except FileNotFoundError:
                continue
    return pids


def _collect_profile_models(args: dict[str, object]) -> list[str]:
    """Extract model ids from profile args for real-mode rejection."""
    mids: list[str] = []
    for key in ("quality_profile",):
        val = args.get(key)
        if val and isinstance(val, str) and val:
            try:
                _loader, src = load_profile_flex(str(val), ("quality",))
                models = src.raw.get("models", {})
                for entry in models.get("available", []):
                    if isinstance(entry, dict):
                        mid = str(entry.get("model_id", ""))
                        if mid:
                            mids.append(mid)
            except FileNotFoundError:
                continue
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
