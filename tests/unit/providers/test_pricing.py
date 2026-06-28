"""Tests for the single-source provider pricing module."""

from __future__ import annotations

from film_pipeline.providers.pricing import (
    pricing_prompt_block,
    rate_for,
    unit_for,
)


class TestRateAndUnit:
    def test_known_providers(self) -> None:
        assert rate_for("seedance-openrouter") == 0.18
        assert rate_for("veo-3.1-fast") == 0.10
        assert rate_for("gemini-imagen-4") == 0.02
        assert unit_for("seedance-openrouter") == "second"
        assert unit_for("gemini-imagen-4") == "image"

    def test_unknown_provider(self) -> None:
        assert rate_for("nope") == 0.0
        assert unit_for("nope") == "second"


class TestPromptBlock:
    def test_block_is_consistent_with_rates(self) -> None:
        block = pricing_prompt_block()
        # The divergent $0.50 Veo figure that used to live in the prompt is gone.
        assert "0.50" not in block
        assert "Seedance 2.0: $0.18 per second" in block
        assert "per image" in block
        assert "Cost per shot" in block

    def test_alias_providers_dedupe_to_one_line(self) -> None:
        # veo-3.1-fast/veo-fast and gemini-imagen-4/imagen-4 are alias ids for the
        # same real provider and intentionally share a label; the block must show
        # each real provider exactly once, not once per alias id.
        block = pricing_prompt_block()
        assert block.count("Veo Fast (rate TBD)") == 1
        assert block.count("Imagen 4 (fast)") == 1
