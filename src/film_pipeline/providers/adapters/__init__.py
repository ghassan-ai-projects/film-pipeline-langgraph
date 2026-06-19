"""Real provider adapter — Seedance 2.0 via OpenRouter.

Implements BaseProviderAdapter using the OpenRouter API.
Requires: OPENROUTER_API_KEY environment variable.
Provider chain: Seedance 2.0 → Veo 3.1 Fast → Veo 3.1 Lite.

DO NOT USE until Phase 12 E2E mock baseline passes.
See docs/implementation-plan/13-real-provider-adapter.md
"""

from __future__ import annotations
