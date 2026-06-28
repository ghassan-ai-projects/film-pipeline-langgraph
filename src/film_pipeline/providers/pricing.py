"""Single source of truth for provider pricing.

Both the cost-estimating side (provider adapters / cost profiles) and the
generation-planning prompt read from here, so the cost the planner predicts
matches the cost the adapter actually charges. Previously these diverged — the
planner prompt advertised Veo at $0.50/s while the adapter billed $0.10/s, and
Seedance's $0.18/s was duplicated in three places.
"""

from __future__ import annotations

# unit is "second" for video, "image" for stills. "veo-3.1-fast"/"veo-fast" and
# "gemini-imagen-4"/"imagen-4" are alias ids for the same real provider, so they
# intentionally share one label — pricing_prompt_block() dedupes by label so the
# planner prompt shows one price line per real provider, not one per alias.
PROVIDER_PRICING: dict[str, dict[str, object]] = {
    "seedance-openrouter": {"unit": "second", "rate_usd": 0.18, "label": "Seedance 2.0"},
    "veo-3.1-fast": {"unit": "second", "rate_usd": 0.10, "label": "Veo Fast (rate TBD)"},
    "veo-fast": {"unit": "second", "rate_usd": 0.10, "label": "Veo Fast (rate TBD)"},
    "gemini-imagen-4": {"unit": "image", "rate_usd": 0.02, "label": "Imagen 4 (fast)"},
    "imagen-4": {"unit": "image", "rate_usd": 0.02, "label": "Imagen 4 (fast)"},
}

_DEFAULT_VIDEO_RATE = 0.0


def rate_for(provider_id: str) -> float:
    """Return the per-unit USD rate for a provider (0.0 if unknown)."""
    entry = PROVIDER_PRICING.get(provider_id)
    if entry is None:
        return _DEFAULT_VIDEO_RATE
    return float(entry["rate_usd"])  # type: ignore[arg-type]


def unit_for(provider_id: str) -> str:
    """Return the billing unit ('second' or 'image') for a provider."""
    entry = PROVIDER_PRICING.get(provider_id)
    return str(entry["unit"]) if entry else "second"


def pricing_prompt_block() -> str:
    """Render the canonical price list for injection into planning prompts.

    Keeping this generated (not hand-written in the prompt) guarantees the
    planner reasons over the same numbers the adapters bill.
    """
    lines = ["Provider pricing (authoritative — use these exact rates):"]
    seen: set[str] = set()
    for entry in PROVIDER_PRICING.values():
        label = str(entry["label"])
        if label in seen:
            continue
        seen.add(label)
        unit = str(entry["unit"])
        rate = float(entry["rate_usd"])  # type: ignore[arg-type]
        per = "per second" if unit == "second" else "per image"
        lines.append(f"- {label}: ${rate:.2f} {per}")
    lines.append("Cost per shot = duration_seconds x provider per-second rate.")
    return "\n".join(lines)
