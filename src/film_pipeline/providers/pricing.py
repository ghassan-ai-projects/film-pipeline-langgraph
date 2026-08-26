"""Single source of truth for provider pricing.

Both the cost-estimating side (provider adapters / cost profiles) and the
generation-planning prompt read from here, so the cost the planner predicts
matches the cost the adapter actually charges. Previously these diverged — the
planner prompt advertised Veo at $0.50/s while the adapter billed $0.10/s, and
Seedance's $0.18/s was duplicated in three places.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class _PricingEntry(TypedDict):
    """Billing facts for one provider id; alias ids share one label.

    ``tiers`` optionally maps model-name fragments to per-unit rates that
    override the standard ``rate_usd`` (e.g. Imagen Ultra bills more than the
    standard tier). Matching is substring containment on the lowercase model
    id, mirroring how adapters dispatch models.
    """

    unit: str
    rate_usd: float
    label: str
    tiers: NotRequired[dict[str, float]]


# unit is "second" for video, "image" for stills. Mock entries are explicit
# zero-cost catalog facts so planning never treats an unknown provider as free.
# "veo-3.1-fast"/"veo-fast" and
# "gemini-imagen-4"/"imagen-4" are alias ids for the same real provider, so they
# intentionally share one label — pricing_prompt_block() dedupes by label so the
# planner prompt shows one price group per real provider, not one per alias.
PROVIDER_PRICING: dict[str, _PricingEntry] = {
    "mock-video-provider": {"unit": "second", "rate_usd": 0.0, "label": "Mock video"},
    "mock-image-provider": {"unit": "image", "rate_usd": 0.0, "label": "Mock image"},
    "seedance-openrouter": {"unit": "second", "rate_usd": 0.18, "label": "Seedance 2.0"},
    "veo-3.1-fast": {"unit": "second", "rate_usd": 0.10, "label": "Veo Fast (rate TBD)"},
    "veo-fast": {"unit": "second", "rate_usd": 0.10, "label": "Veo Fast (rate TBD)"},
    "gemini-imagen-4": {
        "unit": "image",
        # Standard/default tier — unknown or un-named models bill this.
        "rate_usd": 0.05,
        "label": "Imagen 4",
        "tiers": {"ultra": 0.10, "fast": 0.02},
    },
    "imagen-4": {
        "unit": "image",
        "rate_usd": 0.05,
        "label": "Imagen 4",
        "tiers": {"ultra": 0.10, "fast": 0.02},
    },
}

_UNKNOWN_PROVIDER_RATE = 0.0


def _tier_rate(entry: _PricingEntry, model: str | None) -> float | None:
    """Return the tier override for a model id, or None when standard applies."""
    if not model:
        return None
    lowered = model.strip().lower()
    matches = [(tier, rate) for tier, rate in entry.get("tiers", {}).items() if tier in lowered]
    if not matches:
        return None
    # Prefer the most specific matching fragment; dict order breaks ties
    # deterministically for a catalog with equal-length tier names.
    return max(matches, key=lambda item: len(item[0]))[1]


def rate_for(provider_id: str, model: str | None = None) -> float:
    """Return the per-unit USD rate for a provider/model (0.0 if unknown).

    When the provider declares tiers and the model name contains a tier key,
    the tier rate wins; otherwise the standard rate applies.
    """
    entry = PROVIDER_PRICING.get(provider_id)
    if entry is None:
        return _UNKNOWN_PROVIDER_RATE
    tier_rate = _tier_rate(entry, model)
    return tier_rate if tier_rate is not None else entry["rate_usd"]


def unit_for(provider_id: str) -> str:
    """Return the billing unit ('second' or 'image') for a provider."""
    entry = PROVIDER_PRICING.get(provider_id)
    return entry["unit"] if entry else "second"


def estimate_cost_for_duration(
    provider_id: str,
    model: str | None,
    duration_seconds: float,
) -> float:
    """Estimate one shot using the catalog's billing unit and model tier."""
    rate = rate_for(provider_id, model)
    if unit_for(provider_id) == "image":
        return rate
    return duration_seconds * rate


def tier_for(provider_id: str, model: str | None) -> str:
    """Return the catalog tier selected by a model, or ``standard``."""
    entry = PROVIDER_PRICING.get(provider_id)
    if entry is None:
        return "standard"
    if not model:
        return "standard"
    lowered = model.strip().lower()
    matches = [tier for tier in entry.get("tiers", {}) if tier in lowered]
    return max(matches, key=len) if matches else "standard"


def pricing_prompt_block() -> str:
    """Render the canonical price list for injection into planning prompts.

    Keeping this generated (not hand-written in the prompt) guarantees the
    planner reasons over the same numbers the adapters bill. Providers with
    tiers render one line per tier plus the standard rate, because planners
    do cost arithmetic against these exact numbers.
    """
    lines = ["Provider pricing (authoritative — use these exact rates):"]
    seen: set[str] = set()
    for entry in PROVIDER_PRICING.values():
        label = entry["label"]
        if label in seen:
            continue
        seen.add(label)
        per = "per second" if entry["unit"] == "second" else "per image"
        tiers = entry.get("tiers", {})
        for tier, rate in sorted(tiers.items(), key=lambda item: -item[1]):
            lines.append(f"- {label} {tier.capitalize()}: ${rate:.2f} {per}")
        suffix = " (standard)" if tiers else ""
        lines.append(f"- {label}{suffix}: ${entry['rate_usd']:.2f} {per}")
    lines.append("Video cost per shot = duration_seconds x per-second rate.")
    lines.append("Image cost per shot = one image x per-image rate; duration does not change it.")
    return "\n".join(lines)
