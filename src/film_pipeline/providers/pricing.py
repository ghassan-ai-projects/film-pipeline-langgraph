"""Single source of truth for provider pricing.

Both the cost-estimating side (provider adapters / cost profiles) and the
generation-planning prompt read from here, so the cost the planner predicts
matches the cost the adapter actually charges. Previously these diverged — the
planner prompt advertised Veo at $0.50/s while the adapter billed $0.10/s, and
Seedance's $0.18/s was duplicated in three places.
"""

from __future__ import annotations

from typing import TypedDict


class _PricingEntry(TypedDict):
    """Billing facts for one provider id; alias ids share one label."""

    unit: str
    rate_usd: float
    label: str


# unit is "second" for video, "image" for stills. "veo-3.1-fast"/"veo-fast" and
# "gemini-imagen-4"/"imagen-4" are alias ids for the same real provider, so they
# intentionally share one label — pricing_prompt_block() dedupes by label so the
# planner prompt shows one price line per real provider, not one per alias.
PROVIDER_PRICING: dict[str, _PricingEntry] = {
    "seedance-openrouter": {"unit": "second", "rate_usd": 0.18, "label": "Seedance 2.0"},
    "veo-3.1-fast": {"unit": "second", "rate_usd": 0.10, "label": "Veo Fast (rate TBD)"},
    "veo-fast": {"unit": "second", "rate_usd": 0.10, "label": "Veo Fast (rate TBD)"},
    "gemini-imagen-4": {"unit": "image", "rate_usd": 0.02, "label": "Imagen 4 (fast)"},
    "imagen-4": {"unit": "image", "rate_usd": 0.02, "label": "Imagen 4 (fast)"},
}

_UNKNOWN_PROVIDER_RATE = 0.0


def rate_for(provider_id: str) -> float:
    """Return the per-unit USD rate for a provider (0.0 if unknown)."""
    entry = PROVIDER_PRICING.get(provider_id)
    if entry is None:
        return _UNKNOWN_PROVIDER_RATE
    return entry["rate_usd"]


def unit_for(provider_id: str) -> str:
    """Return the billing unit ('second' or 'image') for a provider."""
    entry = PROVIDER_PRICING.get(provider_id)
    return entry["unit"] if entry else "second"


def pricing_prompt_block() -> str:
    """Render the canonical price list for injection into planning prompts.

    Keeping this generated (not hand-written in the prompt) guarantees the
    planner reasons over the same numbers the adapters bill.
    """
    lines = ["Provider pricing (authoritative — use these exact rates):"]
    seen: set[str] = set()
    for entry in PROVIDER_PRICING.values():
        label = entry["label"]
        if label in seen:
            continue
        seen.add(label)
        per = "per second" if entry["unit"] == "second" else "per image"
        lines.append(f"- {label}: ${entry['rate_usd']:.2f} {per}")
    lines.append("Cost per shot = duration_seconds x provider per-second rate.")
    return "\n".join(lines)
