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

    def test_select_prefer_cheap(self) -> None:
        router = ModelRouter()
        model = router.select("creative_writer", prefer_cheap=True)
        assert model == "google/gemini-3-flash-preview"  # fallback

    def test_fallback(self) -> None:
        router = ModelRouter()
        model = router.fallback("creative_writer")
        assert model in ("deepseek/deepseek-chat", "google/gemini-3-flash-preview")

    def test_cost_ranked(self) -> None:
        router = ModelRouter()
        ranked = router.cost_ranked("creative_writer")
        assert len(ranked) == 2
        assert "google/gemini-3-flash-preview" in ranked
        assert "deepseek/deepseek-chat" in ranked

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
        model_id, max_tokens, temperature = router.resolve_model_params("strict_validator")
        assert model_id == "deepseek/deepseek-chat"
        assert max_tokens == 4096
        assert temperature == 0.1

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
            model_id, max_tokens, temperature = router.resolve_model_params(name)
            assert isinstance(model_id, str) and model_id
            assert max_tokens > 0
            assert 0.0 <= temperature <= 1.0
