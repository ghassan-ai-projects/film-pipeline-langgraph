"""Tests for composition of profile-selected provider adapters."""

from __future__ import annotations

import pytest

from film_pipeline.providers.credentials import MissingProviderCredential
from film_pipeline.studio import _provider_factory as provider_factory

# Retargeted from `studio._provider_profiles`, which was a byte-identical dead
# duplicate of these two functions in `studio._operator_runtime` — nothing in
# src/ imported it, only this file did. The behaviour asserted below is the
# same; the implementation now under test is the live one.
from film_pipeline.studio._operator_runtime import (
    missing_profile_credentials,
    register_profile_providers,
)
from film_pipeline.studio.runtime import StudioRuntime


def test_register_profile_providers_builds_ordered_adapters_and_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = StudioRuntime(server_mode="mock")
    runtime.register_provider("old-provider", object())
    runtime.set_provider_health("old-provider", "degraded", "old state")
    built: list[tuple[str, str, list[str]]] = []

    def build_adapter(
        provider_id: str, *, provider_type: str, models: list[str] | None = None
    ) -> object:
        built.append((provider_id, provider_type, models or []))
        return object()

    monkeypatch.setattr(provider_factory, "build_provider_adapter", build_adapter)

    register_profile_providers(
        runtime,
        {},
        {
            "providers": {
                "video": [
                    {"provider_id": "video-a", "models": ["model-a", ""]},
                    {"provider_id": "video-b", "models": ["model-b"]},
                ],
                "image": [{"provider_id": "image-a", "models": ["model-c"]}],
            }
        },
    )

    assert built == [
        ("video-a", "video", ["model-a"]),
        ("video-b", "video", ["model-b"]),
        ("image-a", "image", ["model-c"]),
    ]
    assert runtime.list_providers() == ["video-a", "video-b", "image-a"]
    for provider_id in runtime.list_providers():
        assert runtime.get_provider_health(provider_id) == {"status": "healthy", "reason": ""}


def test_register_profile_providers_keeps_existing_runtime_when_no_specs() -> None:
    runtime = StudioRuntime(server_mode="mock")
    existing = object()
    runtime.register_provider("existing", existing)
    runtime.set_provider_health("existing", "degraded", "keep")

    register_profile_providers(runtime, {}, {})

    assert runtime.get_provider("existing") is existing
    assert runtime.get_provider_health("existing") == {"status": "degraded", "reason": "keep"}


def test_missing_profile_credentials_uses_resolved_provider_specs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("film_pipeline.providers.credentials.is_configured", lambda _: False)

    missing = missing_profile_credentials(
        {},
        {
            "providers": {
                "video": [{"provider_id": "seedance-openrouter", "models": []}],
            }
        },
    )

    assert missing == [MissingProviderCredential("seedance-openrouter", "OPENROUTER_API_KEY")]
