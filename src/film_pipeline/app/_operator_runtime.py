"""Bind the concrete studio runtime to the operator surface's port.

`operations` declares what it needs as `RuntimePort` and `RuntimeProvider`
protocols; this module supplies the concrete implementations from the
composition root. That direction is the allowed one: `studio`/`app` may import
`operations`, never the reverse.

The accessor adapter exists because the operator service resolves the process
singleton lazily (`get_runtime`) and rebuilds it on a mode switch
(`reset_runtime`). That is composition-root policy, so it lives here rather than
inside the service.
"""

from __future__ import annotations

from film_pipeline.app.runtime import StudioRuntime, get_runtime, reset_runtime
from film_pipeline.config.profile_resolver import provider_specs
from film_pipeline.operations.ports import RuntimePort
from film_pipeline.providers.credentials import (
    MissingProviderCredential,
    missing_provider_credentials,
)


class StudioRuntimeProvider:
    """Resolve and switch the process-wide studio runtime.

    Satisfies :class:`~film_pipeline.operations.ports.RuntimeProvider` so the
    operator service can be handed this object instead of importing
    `film_pipeline.app.runtime` itself.
    """

    def current(self) -> RuntimePort:
        """Return the runtime currently in effect."""
        return get_runtime()

    def switch(self, mode: str) -> RuntimePort:
        """Rebuild the runtime in ``mode`` and return it."""
        return reset_runtime(mode)


def register_profile_providers(
    runtime: RuntimePort,
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> None:
    """Replace runtime providers with the adapters selected by a profile stack."""
    specs = provider_specs(profile_stack, resolved_config)
    if not specs:
        return

    from film_pipeline.app._provider_factory import build_provider_adapter

    runtime.clear_providers()
    for spec in specs:
        provider_id = str(spec["provider_id"])
        provider_type = str(spec.get("provider_type", "video"))
        raw_models = spec.get("models", [])
        models = (
            [str(model) for model in raw_models if str(model)]
            if isinstance(raw_models, list)
            else []
        )
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


def runtime_for(service_runtime: RuntimePort | None) -> RuntimePort:
    """Resolve an explicitly supplied runtime or fall back to the singleton."""
    if service_runtime is not None:
        return service_runtime
    return get_runtime()


class _ProfileProviderComposition:
    """The concrete :class:`ProviderComposition` bound to this package."""

    def register_profile_providers(
        self,
        runtime: RuntimePort,
        profile_stack: dict[str, str],
        resolved_config: dict[str, object],
    ) -> None:
        register_profile_providers(runtime, profile_stack, resolved_config)

    def missing_profile_credentials(
        self,
        profile_stack: dict[str, str],
        resolved_config: dict[str, object],
    ) -> list[MissingProviderCredential]:
        return missing_profile_credentials(profile_stack, resolved_config)


def profile_provider_composition() -> _ProfileProviderComposition:
    """Return the composition-root provider collaborator for the operator."""
    return _ProfileProviderComposition()


__all__ = [
    "StudioRuntime",
    "StudioRuntimeProvider",
    "get_runtime",
    "missing_profile_credentials",
    "profile_provider_composition",
    "register_profile_providers",
    "reset_runtime",
    "runtime_for",
]
