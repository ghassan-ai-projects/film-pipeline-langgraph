"""Composition-root helpers for the surviving operator use cases.

This module used to bind the concrete runtime to an `OperatorService` — supplying
`StudioRuntimeProvider` and a `ProviderComposition` so the service could resolve
the process singleton lazily and rebuild it on a mode switch. `OperatorService` is
gone (`docs/modularity-improvements/03-one-use-case-layer.md`), and with it those
two protocols, so what remains is the one use case that genuinely needs the
composition root: registering the provider adapters a profile stack selects.

That use case *is* composition policy — it calls `build_provider_adapter`, which
needs the concrete provider classes — so it stays here rather than moving to
`config` beside the credential lookup, which is pure.

This is also `mcp`'s last cross-package private reach-in
(`mcp -> studio._operator_runtime`), recorded in `test_boundary_law` as
irreducible — it builds concrete provider adapters, which only the composition
root can do. It stays irreducible for a smaller reason now: one function, not a
wired service.
"""

from __future__ import annotations

from film_pipeline.config.profile_resolver import provider_specs
from film_pipeline.operations.ports import RuntimePort
from film_pipeline.studio.runtime import StudioRuntime


def register_profile_providers(
    runtime: RuntimePort,
    profile_stack: dict[str, str],
    resolved_config: dict[str, object],
) -> None:
    """Replace runtime providers with the adapters selected by a profile stack.

    `mcp/tools/projects.py` and `mcp/tools/_profile_change.py` call this directly;
    it used to be reached through `OperatorService.register_profile_providers`.
    """
    specs = provider_specs(profile_stack, resolved_config)
    if not specs:
        return

    # lazy: no cycle here — `_provider_factory` imports only `providers` and
    # `schemas`, never this module. It stays function-level because tests patch
    # `studio._provider_factory.build_provider_adapter` on the module object; a
    # module-level `from ... import build_provider_adapter` here would bind the
    # real function before the patch and silently bypass it.
    from film_pipeline.studio._provider_factory import build_provider_adapter

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


__all__ = ["StudioRuntime", "register_profile_providers"]
