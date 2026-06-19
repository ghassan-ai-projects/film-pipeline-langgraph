"""Seedance 2.0 provider adapter via OpenRouter.

Implements the full BaseProviderAdapter contract. Requires API key.
See docs/implementation-plan/13-real-provider-adapter.md

Pre-flight checklist before first real generation:
- E2E mock baseline passes (Phase 12)
- OPENROUTER_API_KEY set
- No-duplicate generation test passes
- Budget approval works
- Generation ledger is stable
"""

from __future__ import annotations
