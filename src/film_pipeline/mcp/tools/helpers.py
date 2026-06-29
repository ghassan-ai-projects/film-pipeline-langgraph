"""Shared helpers used across MCP tool modules.

Contains the basic response builders, runtime/service accessors, and
profile/config resolution helpers used by ``create_film_project`` and
other tools that need to load and merge profile stacks.
"""

from __future__ import annotations

import contextlib
from typing import Any, cast


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


def _load_profile_flex(
    profile_id: str,
    prefixes: tuple[str, ...],
) -> tuple[Any, Any]:
    """Load a profile spec, trying prefixed variants.

    Returns ``(loader, source)`` where *source* is a ``ProfileSource``
    (with ``.raw``, ``.path``, ``.name`` attributes).
    """
    from film_pipeline.config.loader import ProfileLoader

    loader = ProfileLoader()
    candidates = [profile_id]
    if "." not in profile_id:
        candidates.extend(f"{prefix}.{profile_id}" for prefix in prefixes)
    for candidate in candidates:
        try:
            return loader, loader.load(candidate)
        except FileNotFoundError:
            continue
    raise FileNotFoundError(profile_id)


def _collect_profile_providers(args: dict[str, object]) -> list[str]:
    """Extract provider ids from profile args for real-mode rejection."""
    pids: list[str] = []
    for key in ("provider_profile",):
        val = args.get(key)
        if val and isinstance(val, str) and val:
            try:
                _loader, src = _load_profile_flex(str(val), ("provider",))
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
                _loader, src = _load_profile_flex(str(val), ("quality",))
                models = src.raw.get("models", {})
                for entry in models.get("available", []):
                    if isinstance(entry, dict):
                        mid = str(entry.get("model_id", ""))
                        if mid:
                            mids.append(mid)
            except FileNotFoundError:
                continue
    return mids


def _canonicalize_profile_stack(args: dict[str, object]) -> dict[str, str]:
    stack: dict[str, str] = {}
    mapping = {
        "film_type_profile": ("film-type",),
        "quality_profile": ("quality",),
        "provider_profile": ("provider",),
        "review_profile": ("review",),
        "auto_approve_profile": ("",),  # no prefix — matches any profile dir
    }
    for key, prefixes in mapping.items():
        raw = str(args.get(key, "")).strip()
        if raw:
            _loader, src = _load_profile_flex(raw, prefixes)
            stack[key] = src.path.stem
        else:
            stack[key] = ""
    return stack


def _resolve_project_config(profile_stack: dict[str, str]) -> dict[str, object]:
    from film_pipeline.config.resolver import ConfigResolver

    names = ["base.studio"]
    for key in (
        "film_type_profile",
        "quality_profile",
        "provider_profile",
        "review_profile",
        "auto_approve_profile",
    ):
        value = profile_stack.get(key, "")
        if value:
            names.append(value)

    resolver = ConfigResolver()
    resolved = resolver.resolve(names)
    return {
        "raw": resolved.raw,
        "sources": [source.path.stem for source in resolved.sources],
        "conflicts": [
            {
                "code": conflict.code,
                "message": conflict.message,
                "severity": conflict.severity,
            }
            for conflict in resolved.conflicts
        ],
    }


def _provider_specs_from_raw(providers: object) -> list[dict[str, object]]:
    if not isinstance(providers, dict):
        return []
    specs: list[dict[str, object]] = []
    for section, provider_type in (("video", "video"), ("image", "image")):
        entries = providers.get(section, [])
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict):
                    provider_id = str(entry.get("provider_id", "")).strip()
                    if provider_id:
                        models = entry.get("models", [])
                        specs.append(
                            {
                                "provider_id": provider_id,
                                "provider_type": provider_type,
                                "models": models if isinstance(models, list) else [],
                            }
                        )
    order = providers.get("order", [])
    if isinstance(order, list):
        for item in order:
            provider_id = str(item).strip()
            if provider_id:
                specs.append(
                    {
                        "provider_id": provider_id,
                        "provider_type": "video",
                        "models": [],
                    }
                )
    deduped: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for spec in specs:
        key = (str(spec["provider_id"]), str(spec["provider_type"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(spec)
    return deduped


def _provider_specs(
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> list[dict[str, object]]:
    provider_profile = profile_stack.get("provider_profile", "")
    if provider_profile:
        try:
            _loader, src = _load_profile_flex(provider_profile, ("provider",))
            providers = src.raw.get("providers", {})
            specs = _provider_specs_from_raw(providers)
            if specs:
                return specs
        except FileNotFoundError:
            pass

    providers = resolved_config.get("providers", {})
    if isinstance(providers, dict):
        specs = _provider_specs_from_raw(providers)
        if specs:
            return specs
    return []


def _register_project_providers(
    rt: Any,
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> None:
    from film_pipeline.providers.factory import build_provider_adapter

    provider_ids = _provider_specs(profile_stack, resolved_config)
    if not provider_ids:
        return

    rt.clear_providers()
    for spec in provider_ids:
        provider_id = str(spec["provider_id"])
        provider_type = str(spec.get("provider_type", "video"))
        models = [str(model) for model in cast(list[Any], spec.get("models", [])) if str(model)]
        adapter = build_provider_adapter(
            provider_id,
            provider_type=provider_type,
            models=models,
        )
        rt.register_provider(provider_id, adapter)
        rt.set_provider_health(provider_id, "healthy")


def _missing_provider_credentials(
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> list[dict[str, str]]:
    from film_pipeline.providers.credentials import _env_var_for, is_configured

    missing: list[dict[str, str]] = []
    seen: set[str] = set()
    for spec in _provider_specs(profile_stack, resolved_config):
        provider_id = str(spec["provider_id"])
        if provider_id in seen:
            continue
        seen.add(provider_id)
        env_var = _env_var_for(provider_id)
        if not env_var:
            continue
        if is_configured(provider_id):
            continue
        missing.append({"provider_id": provider_id, "env_var": env_var})
    return missing


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
