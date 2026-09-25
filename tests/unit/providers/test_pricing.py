"""Tests for the single-source provider pricing module.

Contract under test [Flx-F10]: every adapter's ``estimate_cost`` derives from
this table — never from local literals — so planner prompts advertise exactly
what adapters bill. Mock providers are explicit zero-cost pricing entries, so
they cannot be confused with an unknown provider during planning.

Known limitation (recorded deliberately): ``app._provider_factory._default_cost_profile``
reports the standard tier because it has no model in hand; per-tier honesty
lives in ``rate_for(provider_id, model)`` and the prompt block.
"""

from __future__ import annotations

import pytest

from film_pipeline.providers.adapters import (
    Imagen4GeminiProvider,
    SeedanceOpenRouterProvider,
    VeoFastProvider,
)
from film_pipeline.providers.pricing import (
    PROVIDER_PRICING,
    pricing_prompt_block,
    rate_for,
    tier_for,
    unit_for,
)
from film_pipeline.schemas.registries.provider_registry import (
    CostProfile,
    ProviderCapabilities,
    ProviderRegistryEntry,
)


class TestRateAndUnit:
    def test_standard_rates_unchanged(self) -> None:
        assert rate_for("seedance-openrouter") == 0.18
        assert rate_for("veo-3.1-fast") == 0.10
        assert unit_for("seedance-openrouter") == "second"
        assert unit_for("gemini-imagen-4") == "image"

    def test_imagen_tiers(self) -> None:
        # Default/standard is 0.05 — the old flat entry claimed 0.02 for it.
        assert rate_for("gemini-imagen-4") == 0.05
        assert rate_for("gemini-imagen-4", None) == 0.05
        assert rate_for("gemini-imagen-4", "imagen-4.0-generate-001") == 0.05
        assert rate_for("gemini-imagen-4", "imagen-4.0-ultra-generate-001") == 0.10
        assert rate_for("gemini-imagen-4", "imagen-4.0-fast-generate-001") == 0.02

    def test_imagen_alias_shares_tiers(self) -> None:
        assert rate_for("imagen-4", "ultra") == rate_for("gemini-imagen-4", "ultra")
        assert tier_for("gemini-imagen-4", "imagen-4.0-ultra-generate-001") == "ultra"
        assert tier_for("gemini-imagen-4", "imagen-4.0-generate-001") == "standard"

    def test_tier_matching_is_case_and_whitespace_insensitive(self) -> None:
        assert rate_for("gemini-imagen-4", "  IMAGEN-4-FAST  ") == 0.02

    def test_unknown_model_uses_standard_rate(self) -> None:
        assert rate_for("gemini-imagen-4", "imagen-4-future-tier") == 0.05

    def test_overlapping_tier_fragments_choose_specific_match(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(
            PROVIDER_PRICING["gemini-imagen-4"],
            "tiers",
            {"pro": 0.03, "professional": 0.08},
        )
        assert rate_for("gemini-imagen-4", "professional") == 0.08

    def test_unknown_provider(self) -> None:
        assert rate_for("nope") == 0.0
        assert rate_for("nope", "ultra") == 0.0
        assert unit_for("nope") == "second"


def _entry(provider_id: str, models: list[str], provider_type: str) -> ProviderRegistryEntry:
    return ProviderRegistryEntry(
        provider_id=provider_id,
        provider_type=provider_type,
        models=models,
        capabilities=ProviderCapabilities(
            text_to_video=True,
            image_to_video=True,
            return_last_frame=True,
            max_duration_seconds=30,
            aspect_ratios=["16:9"],
            supported_resolutions=["480p", "720p"],
        ),
        cost_profile=CostProfile(unit="second", estimated_rate_usd=0.0),
    )


_ADAPTERS = [
    pytest.param(
        SeedanceOpenRouterProvider,
        "seedance-openrouter",
        ["seedance-2.0"],
        "video",
        id="seedance",
    ),
    pytest.param(
        VeoFastProvider,
        "veo-3.1-fast",
        ["veo-3.1-fast"],
        "video",
        id="veo-fast",
    ),
    pytest.param(
        Imagen4GeminiProvider,
        "gemini-imagen-4",
        ["imagen-4.0-generate-001"],
        "image",
        id="imagen4-gemini",
    ),
]


class TestAdapterPricingParity:
    """Every real adapter bills exactly what the pricing table advertises."""

    @pytest.mark.parametrize(
        ("adapter_cls", "provider_id", "models", "provider_type"),
        _ADAPTERS,
    )
    def test_estimate_matches_table(
        self,
        adapter_cls: type,
        provider_id: str,
        models: list[str],
        provider_type: str,
    ) -> None:
        entry = _entry(provider_id, models, provider_type)
        adapter = adapter_cls(entry)

        probe_models = [None, *models, "totally-unknown-model"]
        if "tiers" in PROVIDER_PRICING[provider_id]:
            probe_models += list(PROVIDER_PRICING[provider_id]["tiers"])
        for model in probe_models:
            billed = adapter.estimate_cost(duration=10.0, model=model)
            expected_rate = rate_for(provider_id, model)
            unit = unit_for(provider_id)
            expected = expected_rate if unit == "image" else round(10.0 * expected_rate, 6)
            assert billed == pytest.approx(expected), f"model={model!r}"


class TestPromptBlock:
    def test_block_is_consistent_with_rates(self) -> None:
        block = pricing_prompt_block()
        # The divergent $0.50 Veo figure that used to live in the prompt is gone.
        assert "0.50" not in block
        assert "Seedance 2.0: $0.18 per second" in block
        assert "per image" in block
        assert "Video cost per shot = duration_seconds x per-second rate." in block
        assert (
            "Image cost per shot = one image x per-image rate; duration does not change it."
            in block
        )
        assert "Cost per shot = duration_seconds x provider per-second rate." not in block

    def test_tiered_provider_renders_every_tier(self) -> None:
        """Planner-visible imagen rates equal billed rates for all tiers."""
        block = pricing_prompt_block()
        assert "- Imagen 4 Ultra: $0.10 per image" in block
        assert "- Imagen 4 Fast: $0.02 per image" in block
        assert "- Imagen 4 (standard): $0.05 per image" in block
        # The old misleading flat line must not survive.
        assert "Imagen 4 (fast)" not in block

    def test_alias_providers_dedupe_to_one_group(self) -> None:
        # veo-3.1-fast/veo-fast and gemini-imagen-4/imagen-4 are alias ids for the
        # same real provider and intentionally share a label; the block must show
        # each real provider's price group exactly once, not once per alias id.
        block = pricing_prompt_block()
        assert block.count("Veo Fast (rate TBD)") == 1
        assert block.count("- Imagen 4 Ultra:") == 1
        assert block.count("- Imagen 4 Fast:") == 1
        assert block.count("- Imagen 4 (standard):") == 1
