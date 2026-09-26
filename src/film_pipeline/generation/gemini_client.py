"""Compatibility alias for the Gemini review client, now owned by ``providers``.

The client talks to a concrete provider API and resolves that provider's
credentials, so it belongs to the provider layer rather than `generation`.
"""

from film_pipeline.providers.gemini_review_client import (
    GEMINI_API_BASE as GEMINI_API_BASE,
)
from film_pipeline.providers.gemini_review_client import call_gemini as call_gemini

__all__ = ["GEMINI_API_BASE", "call_gemini"]
