"""Tests for the neutral profile resolver used by MCP tools and OperatorService."""

from __future__ import annotations

from typing import Any, cast

import pytest

from film_pipeline.config.profile_resolver import (
    canonicalize_profile_stack,
    missing_provider_credentials,
    provider_specs,
    provider_specs_from_raw,
    resolve_project_config,
)


def test_canonicalize_profile_stack_resolves_existing_profiles() -> None:
    stack = canonicalize_profile_stack(
        {
            "film_type_profile": "narrative",
            "quality_profile": "draft",
            "provider_profile": "mock-demo",
        }
    )
    assert stack["film_type_profile"] == "film-type.narrative"
    assert stack["quality_profile"] == "quality.draft"
    assert stack["provider_profile"] == "mock-demo"
    assert stack["review_profile"] == ""
    assert stack["auto_approve_profile"] == ""


def test_canonicalize_profile_stack_ignores_missing_keys() -> None:
    stack = canonicalize_profile_stack({})
    assert all(value == "" for value in stack.values())


def test_resolve_project_config_includes_base_and_profiles() -> None:
    stack = {
        "film_type_profile": "film-type.narrative",
        "quality_profile": "quality.draft",
        "provider_profile": "mock-demo",
        "review_profile": "",
        "auto_approve_profile": "",
    }
    resolved = resolve_project_config(stack)
    raw = cast(dict[str, object], resolved["raw"])
    assert isinstance(raw, dict)
    sources = cast(list[str], resolved["sources"])
    assert "base.studio" in sources
    assert "film-type.narrative" in sources
    assert "quality.draft" in sources
    assert isinstance(resolved["conflicts"], list)


def test_provider_specs_from_raw_extracts_video_and_image_providers() -> None:
    providers: dict[str, Any] = {
        "video": [{"provider_id": "seedance-openrouter", "models": ["seedance-2"]}],
        "image": [{"provider_id": "gemini-imagen-4", "models": ["imagen-4"]}],
        "order": ["seedance-openrouter"],
    }
    specs = provider_specs_from_raw(providers)
    ids = {spec["provider_id"] for spec in specs}
    assert ids == {"seedance-openrouter", "gemini-imagen-4"}


def test_provider_specs_from_raw_deduplicates_providers() -> None:
    providers: dict[str, Any] = {
        "video": [{"provider_id": "seedance-openrouter", "models": []}],
        "order": ["seedance-openrouter"],
    }
    specs = provider_specs_from_raw(providers)
    assert len(specs) == 1


def test_provider_specs_returns_empty_when_no_providers() -> None:
    assert provider_specs({}, {}) == []


def test_provider_specs_uses_resolved_config_when_no_provider_profile() -> None:
    resolved_config: dict[str, Any] = {
        "providers": {
            "video": [{"provider_id": "seedance-openrouter", "models": []}],
        }
    }
    specs = provider_specs({}, resolved_config)
    assert specs[0]["provider_id"] == "seedance-openrouter"


def test_missing_provider_credentials_reports_unconfigured_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("film_pipeline.providers.credentials.is_configured", lambda _: False)
    stack = {"provider_profile": "mock-demo"}
    resolved = resolve_project_config(stack)
    missing = missing_provider_credentials(stack, cast(dict[str, object], resolved["raw"]))
    # mock-demo uses mock providers which do not require credentials, so the list
    # should be empty.
    assert missing == []


def test_missing_provider_credentials_reports_real_provider_without_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("film_pipeline.providers.credentials.is_configured", lambda _: False)
    resolved_config: dict[str, Any] = {
        "providers": {
            "video": [{"provider_id": "seedance-openrouter", "models": []}],
        }
    }
    missing = missing_provider_credentials({}, resolved_config)
    assert len(missing) == 1
    assert missing[0]["provider_id"] == "seedance-openrouter"
    assert missing[0]["env_var"] == "OPENROUTER_API_KEY"
