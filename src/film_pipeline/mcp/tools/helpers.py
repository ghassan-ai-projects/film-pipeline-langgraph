"""Shared helpers used across MCP tool modules.

Contains the basic response builders, runtime/service accessors, and
profile/config resolution helpers used by ``create_film_project`` and
other tools that need to load and merge profile stacks.
"""

from __future__ import annotations

import contextlib
from typing import Any

from film_pipeline.config.profile_resolver import load_profile_flex, provider_specs
from film_pipeline.filmspec import NO_ACTIVE_PROJECT as NO_ACTIVE_PROJECT
from film_pipeline.providers.credentials import (
    missing_provider_credentials,
)
from film_pipeline.schemas.artifact import ArtifactRef


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


def _no_active_project() -> dict[str, object]:
    """The standard "nothing to act on" error response."""
    return _error(NO_ACTIVE_PROJECT)


def _services(rt: object) -> Any:
    """Assert services are initialized and return them."""
    assert hasattr(rt, "services") and rt.services is not None
    return rt.services


def _register_active_artifact_ref(
    rt: Any, active: dict[str, Any], project_id: str, state_key: str, ref: object
) -> None:
    """Record an artifact reference on the active project and persist state.

    The one definition of this write. It was previously defined byte-identically
    in two modules and inlined a third time, so dropping the ``artifact_refs``
    append from one copy failed no test in any suite — the three copies could
    drift apart with nothing able to notice.
    """
    active[state_key] = ref
    active.setdefault("artifact_refs", []).append(ref)
    rt.projects[project_id] = active
    rt.persist_project_state(project_id)


def missing_profile_credentials(
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> list[Any]:
    """Return the provider credentials a resolved profile requires but lacks.

    Composed here from two importable owners rather than routed through the
    composition root: `config.profile_resolver.provider_specs` says which
    providers the profile selects, and `providers.credentials` says which of
    their keys are unset. Neither needs the concrete provider classes, so `mcp`
    can do this itself — and doing it here keeps `mcp`'s one remaining private
    reach-in (`studio._operator_runtime`, for the adapter factory) at one site.

    This used to be a method on the deleted `OperatorService`.
    """
    provider_ids = [
        str(spec["provider_id"]) for spec in provider_specs(profile_stack, resolved_config)
    ]
    return missing_provider_credentials(provider_ids)


def register_profile_providers(
    rt: Any,
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> None:
    """Register the provider adapters a profile stack selects.

    The single place this package reaches the composition root's provider wiring.
    Four tool modules previously obtained a whole ``OperatorService`` here to call
    one method on it; `OperatorService` is gone
    (`docs/modularity-improvements/03-one-use-case-layer.md`), so this names the
    one use case instead.

    The concrete factory still lives in the composition root, which owns that
    wiring — it calls `build_provider_adapter`, which needs the concrete provider
    classes. This is the ``mcp``-side seam for reaching it.
    """
    from film_pipeline.studio._operator_runtime import register_profile_providers as _register

    _register(rt, profile_stack, resolved_config)


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
    from film_pipeline.schemas.base import FilmPhase

    store = _services(rt).artifact_store
    version = 0
    if state is not None:
        visual_ref = str(state.get("visual_refs", ""))
        with contextlib.suppress(ValueError):
            parsed = ArtifactRef.from_string(visual_ref)
            if parsed.artifact_id == "reference_index":
                version = parsed.version
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
