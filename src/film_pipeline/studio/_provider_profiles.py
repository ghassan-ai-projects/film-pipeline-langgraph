"""Compose project profile provider specs with runtime adapters and credentials."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from film_pipeline.config.profile_resolver import provider_specs
from film_pipeline.providers.credentials import (
    MissingProviderCredential,
    missing_provider_credentials,
)

if TYPE_CHECKING:
    from film_pipeline.studio.runtime import StudioRuntime


def register_profile_providers(
    runtime: StudioRuntime,
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> None:
    """Replace runtime providers with the adapters selected by a profile stack."""
    specs = provider_specs(profile_stack, resolved_config)
    if not specs:
        return

    from film_pipeline.studio._provider_factory import build_provider_adapter

    runtime.clear_providers()
    for spec in specs:
        provider_id = str(spec["provider_id"])
        provider_type = str(spec.get("provider_type", "video"))
        models = [str(model) for model in cast(list[Any], spec.get("models", [])) if str(model)]
        adapter = build_provider_adapter(
            provider_id,
            provider_type=provider_type,
            models=models,
        )
        runtime.register_provider(provider_id, adapter)
        runtime.set_provider_health(provider_id, "healthy")


def missing_profile_credentials(
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> list[MissingProviderCredential]:
    """Return missing credentials for providers required by the resolved profile."""
    provider_ids = [
        str(spec["provider_id"]) for spec in provider_specs(profile_stack, resolved_config)
    ]
    return missing_provider_credentials(provider_ids)
