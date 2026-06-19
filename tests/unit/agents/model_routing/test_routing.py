"""Tests for model routing profiles."""

from __future__ import annotations

from film_pipeline.agents.model_routing import MODEL_PROFILES, ModelRouter


class TestModelRouter:
    def test_select_creative_writer(self) -> None:
        router = ModelRouter()
        model = router.select("creative_writer")
        assert model == "gpt-5-mini"

    def test_select_strict_validator(self) -> None:
        router = ModelRouter()
        model = router.select("strict_validator")
        assert model == "gemini-flash"

    def test_select_prefer_cheap(self) -> None:
        router = ModelRouter()
        model = router.select("creative_writer", prefer_cheap=True)
        assert model == "gemini-flash"  # fallback

    def test_fallback(self) -> None:
        router = ModelRouter()
        model = router.fallback("creative_writer")
        assert model in ("gemini-flash", "gpt-5-mini")

    def test_cost_ranked(self) -> None:
        router = ModelRouter()
        ranked = router.cost_ranked("creative_writer")
        assert len(ranked) == 2
        assert ranked[0] == "gemini-flash"  # cheaper first

    def test_cost_ranked_single(self) -> None:
        router = ModelRouter()
        ranked = router.cost_ranked("cheap_draft")
        assert len(ranked) == 1

    def test_list_profiles(self) -> None:
        router = ModelRouter()
        profiles = router.list_profiles()
        assert "creative_writer" in profiles
        assert "strict_validator" in profiles
        assert len(profiles) == 6

    def test_unknown_profile(self) -> None:
        router = ModelRouter()
        model = router.select("nonexistent")
        assert model == "gemini-flash"  # operations_triage fallback

    def test_all_profiles_in_registry(self) -> None:
        for name in MODEL_PROFILES:
            assert "primary" in MODEL_PROFILES[name]
            assert "fallback" in MODEL_PROFILES[name]
