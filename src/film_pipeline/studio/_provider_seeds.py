"""Default provider adapters and health rows for each runtime mode."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from film_pipeline.studio.runtime import StudioRuntime


def seed_default_provider_health(rt: StudioRuntime) -> None:
    """Seed provider health rows and adapters for the configured runtime mode.

    Mock mode advertises the zero-cost mock providers as healthy. Real mode
    advertises the live generation providers, marking each healthy only when
    its API credentials are configured so the operator can see at a glance
    what is wired up. Existing health entries are never overwritten, but
    missing adapters are always registered so generation can dispatch.
    """
    seed_default_provider_adapters(rt)
    if rt.provider_health:
        return
    if rt.server_mode == "real":
        from film_pipeline.providers import is_configured

        for provider_id in ("zai", "seedance-openrouter", "veo-fast", "gemini-imagen-4"):
            if is_configured(provider_id):
                rt.set_provider_health(provider_id, "healthy")
            else:
                rt.set_provider_health(
                    provider_id,
                    "unconfigured",
                    "API credentials not set",
                )
        return
    for provider_id in ("mock-image-provider", "mock-video-provider"):
        rt.set_provider_health(provider_id, "healthy", "mock runtime")


def seed_default_provider_adapters(rt: StudioRuntime) -> None:
    """Register default provider adapters for the runtime mode.

    Project profiles can replace these via ``register_provider``; seeding
    only fills providers that are not registered yet.
    """
    from film_pipeline.studio._provider_factory import build_provider_adapter

    specs: tuple[tuple[str, str], ...]
    if rt.server_mode == "real":
        specs = (
            ("seedance-openrouter", "video"),
            ("veo-fast", "video"),
            ("gemini-imagen-4", "image"),
        )
    else:
        specs = (
            ("mock-video-provider", "video"),
            ("mock-image-provider", "image"),
        )
    for provider_id, provider_type in specs:
        if provider_id not in rt.provider_adapters:
            rt.register_provider(
                provider_id,
                build_provider_adapter(provider_id, provider_type=provider_type),
            )


def default_video_provider(rt: StudioRuntime) -> tuple[str, str]:
    """Return the (provider_id, model) pair generation should default to."""
    if rt.server_mode == "real":
        from film_pipeline.providers import is_configured

        for provider_id, model in (
            ("seedance-openrouter", "bytedance/seedance-2.0"),
            ("veo-fast", "veo-3.1-fast"),
        ):
            if is_configured(provider_id):
                return provider_id, model
        return "seedance-openrouter", "bytedance/seedance-2.0"
    return "mock-video-provider", "mock-fast"
