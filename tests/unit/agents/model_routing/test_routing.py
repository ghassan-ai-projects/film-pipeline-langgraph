"""Tests for model routing profiles."""

from __future__ import annotations

import pytest

from film_pipeline.agents.model_routing import ModelResolutionError, ModelRouter


class TestModelRouter:
    def test_select_creative_writer(self) -> None:
        router = ModelRouter()
        model = router.select("creative_writer")
        assert model == "deepseek/deepseek-chat"

    def test_select_strict_validator(self) -> None:
        router = ModelRouter()
        model = router.select("strict_validator")
        assert model == "deepseek/deepseek-chat"

    def test_default_profiles_preserve_existing_provider_policy(self) -> None:
        """The adapter addition must not change the built-in model policy."""
        router = ModelRouter()
        expected = {
            "creative_writer": "deepseek/deepseek-chat",
            "strict_validator": "deepseek/deepseek-chat",
            "visual_reasoner": "google/gemini-3-flash-preview",
            "schema_enforcer": "deepseek/deepseek-chat",
            "cheap_draft": "google/gemini-3-flash-preview",
            "operations_triage": "google/gemini-3-flash-preview",
            "multimodal_reviewer": "google/gemini-3-flash-preview",
            "text_validator": "deepseek/deepseek-chat",
        }
        assert {name: router.select(name) for name in expected} == expected

    def test_zai_model_is_available_when_explicitly_configured(self) -> None:
        router = ModelRouter(
            profiles={
                "zai_chat": {
                    "primary": "zai/glm-5.3-flash",
                    "fallback": "deepseek/deepseek-chat",
                }
            }
        )
        assert router.select("zai_chat") == "zai/glm-5.3-flash"

    def test_select_prefer_cheap(self) -> None:
        router = ModelRouter()
        model = router.select("creative_writer", prefer_cheap=True)
        assert model == "google/gemini-3-flash-preview"  # fallback

    def test_fallback(self) -> None:
        router = ModelRouter()
        model = router.fallback("creative_writer")
        assert model in ("deepseek/deepseek-chat", "google/gemini-3-flash-preview")

    def test_fallback_unknown_profile_raises(self) -> None:
        router = ModelRouter()
        with pytest.raises(ModelResolutionError, match="not defined"):
            router.fallback("nonexistent")

    def test_cost_ranked(self) -> None:
        router = ModelRouter()
        ranked = router.cost_ranked("creative_writer")
        assert len(ranked) == 2
        assert "google/gemini-3-flash-preview" in ranked
        assert "deepseek/deepseek-chat" in ranked

    def test_cost_ranked_unknown_profile_returns_empty(self) -> None:
        router = ModelRouter()
        assert router.cost_ranked("nonexistent") == []

    def test_cost_ranked_same_primary_and_fallback(self) -> None:
        router = ModelRouter(profiles={"solo": {"primary": "x/y", "fallback": "x/y"}})
        assert router.cost_ranked("solo") == ["x/y"]

    def test_cost_ranked_single(self) -> None:
        router = ModelRouter()
        ranked = router.cost_ranked("cheap_draft")
        assert len(ranked) == 2

    def test_list_profiles(self) -> None:
        router = ModelRouter()
        profiles = router.list_profiles()
        assert "creative_writer" in profiles
        assert "strict_validator" in profiles
        assert len(profiles) == 8  # 6 agent + 2 validator profiles

    def test_unknown_profile_raises(self) -> None:
        router = ModelRouter()
        with pytest.raises(ModelResolutionError, match="not defined"):
            router.select("nonexistent")

    def test_unknown_profile_resolve_or_raise(self) -> None:
        router = ModelRouter()
        with pytest.raises(ModelResolutionError, match="not defined"):
            router.resolve_or_raise("nonexistent")

    def test_resolve_or_raise_success(self) -> None:
        router = ModelRouter()
        model = router.resolve_or_raise("creative_writer")
        assert model == "deepseek/deepseek-chat"

    def test_resolve_model_params(self) -> None:
        router = ModelRouter()
        model_id, max_tokens, temperature, top_p, freq_pen = router.resolve_model_params(
            "strict_validator"
        )
        assert model_id == "deepseek/deepseek-chat"
        assert max_tokens == 4096
        assert temperature == 0.1
        assert top_p == 0.95
        assert freq_pen == 0.0

    def test_resolve_model_params_unknown_profile_raises(self) -> None:
        router = ModelRouter()
        with pytest.raises(ModelResolutionError, match="not defined"):
            router.resolve_model_params("nonexistent")

    def test_custom_profiles(self) -> None:
        router = ModelRouter(
            profiles={
                "test_profile": {
                    "primary": "custom/model",
                    "fallback": "custom/fallback",
                    "max_tokens": 100,
                    "temperature": 0.5,
                }
            }
        )
        model = router.select("test_profile")
        assert model == "custom/model"

    def test_all_profiles_have_required_keys(self) -> None:
        router = ModelRouter()
        for name in router.list_profiles():
            model_id, max_tokens, temperature, top_p, freq_pen = router.resolve_model_params(name)
            assert isinstance(model_id, str) and model_id
            assert max_tokens > 0
            assert 0.0 <= temperature <= 1.0
            assert 0.0 <= top_p <= 1.0
            assert -2.0 <= freq_pen <= 2.0
