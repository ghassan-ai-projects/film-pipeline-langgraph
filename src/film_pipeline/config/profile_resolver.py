"""Neutral profile stack resolution used by MCP tools and OperatorService."""

from __future__ import annotations

from typing import Any, cast


def load_profile_flex(
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


def canonicalize_profile_stack(args: dict[str, object]) -> dict[str, str]:
    """Turn raw profile inputs into a validated stack of profile stems."""
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
            _loader, src = load_profile_flex(raw, prefixes)
            stack[key] = src.path.stem
        else:
            stack[key] = ""
    return stack


def resolve_project_config(profile_stack: dict[str, str]) -> dict[str, object]:
    """Merge the profile stack into a single resolved configuration."""
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


def provider_specs_from_raw(providers: object) -> list[dict[str, object]]:
    """Normalize a raw ``providers`` config block into provider specs."""
    if not isinstance(providers, dict):
        return []
    specs = _specs_from_typed_sections(providers) + _specs_from_order_list(providers)
    return _dedupe_by_provider_identity(specs)


def _specs_from_typed_sections(providers: dict[str, Any]) -> list[dict[str, object]]:
    """Collect specs declared under the typed ``video`` and ``image`` sections."""
    specs: list[dict[str, object]] = []
    for section, provider_type in (("video", "video"), ("image", "image")):
        for entry in _list_at(providers, section):
            spec = _spec_from_section_entry(entry, provider_type)
            if spec is not None:
                specs.append(spec)
    return specs


def _spec_from_section_entry(entry: object, provider_type: str) -> dict[str, object] | None:
    """Turn one raw section entry into a spec, or None when it names no provider."""
    if not isinstance(entry, dict):
        return None
    provider_id = str(entry.get("provider_id", "")).strip()
    if not provider_id:
        return None
    models = entry.get("models", [])
    return {
        "provider_id": provider_id,
        "provider_type": provider_type,
        "models": models if isinstance(models, list) else [],
    }


def _specs_from_order_list(providers: dict[str, Any]) -> list[dict[str, object]]:
    """Add default video specs for bare provider ids listed under ``order``."""
    specs: list[dict[str, object]] = []
    for item in _list_at(providers, "order"):
        provider_id = str(item).strip()
        if not provider_id:
            continue
        specs.append({"provider_id": provider_id, "provider_type": "video", "models": []})
    return specs


def _dedupe_by_provider_identity(
    specs: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Keep the first spec for every distinct ``(provider_id, provider_type)``."""
    deduped: list[dict[str, object]] = []
    seen: set[tuple[str, str]] = set()
    for spec in specs:
        identity = (str(spec["provider_id"]), str(spec["provider_type"]))
        if identity in seen:
            continue
        seen.add(identity)
        deduped.append(spec)
    return deduped


def _list_at(mapping: dict[str, Any], key: str) -> list[Any]:
    """Return the list stored at *key*, or an empty list when missing or not a list."""
    entries = mapping.get(key, [])
    return entries if isinstance(entries, list) else []


def provider_specs(
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> list[dict[str, object]]:
    """Return the ordered provider specs for a project."""
    provider_profile = profile_stack.get("provider_profile", "")
    if provider_profile:
        try:
            _loader, src = load_profile_flex(provider_profile, ("provider",))
            providers = src.raw.get("providers", {})
            specs = provider_specs_from_raw(providers)
            if specs:
                return specs
        except FileNotFoundError:
            pass

    providers = resolved_config.get("providers", {})
    if isinstance(providers, dict):
        specs = provider_specs_from_raw(providers)
        if specs:
            return specs
    return []


def register_project_providers(
    rt: Any,
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> None:
    """Clear existing providers and register the project's provider stack."""
    from film_pipeline.providers.factory import build_provider_adapter

    provider_ids = provider_specs(profile_stack, resolved_config)
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


def missing_provider_credentials(
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> list[dict[str, str]]:
    """Return providers required by the stack that lack API credentials."""
    from film_pipeline.providers.credentials import _env_var_for, is_configured

    missing: list[dict[str, str]] = []
    seen: set[str] = set()
    for spec in provider_specs(profile_stack, resolved_config):
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
