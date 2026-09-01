"""Live z.ai (GLM) provider test — real API, no mocks or fixtures.

**NOT in CI.** Gated behind ``RUN_REAL_E2E=1`` and a configured ``ZAI_API_KEY``
(environment or ``.env`` — run from the repo root so the ``.env`` fallback
applies). Marked ``real_provider`` so ``-m "not real_provider"`` can deselect it.

Coding-plan keys ONLY work against the coding endpoint; set
``ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4`` in the environment or
``.env``. Symptom of the wrong endpoint: error 1113 "Insufficient balance or
no resource package".

Usage::

    RUN_REAL_E2E=1 pytest tests/integration/providers/test_zai_llm_live.py -v

Cost: ~$0 per run on a coding plan (2 short glm-5.3-flash calls).
"""

from __future__ import annotations

import os

import pytest

from film_pipeline.agents.model_adapter import ModelAdapter
from film_pipeline.providers import credentials

pytestmark = [
    pytest.mark.integration,
    pytest.mark.real_provider,
    pytest.mark.skipif(
        os.getenv("RUN_REAL_E2E") != "1" or not credentials.is_configured("zai"),
        reason="RUN_REAL_E2E not set or ZAI_API_KEY not configured — live test is manual-only",
    ),
]


class TestZaiLive:
    """Exercise the real z.ai endpoint through the production ModelAdapter."""

    def test_chat_returns_non_empty_content(self) -> None:
        """The substantive evidence: glm-5.3-flash replies through ModelAdapter.

        ``max_tokens`` is generous because glm-5.3-flash is a reasoning model —
        reasoning tokens count against the completion budget, and an exhausted
        budget yields empty content.
        """
        adapter = ModelAdapter()
        text = adapter.chat(
            "Reply with exactly: OK",
            model="zai/glm-5.3-flash",
            max_tokens=4096,
        )
        assert isinstance(text, str)
        assert text.strip(), "Empty content from z.ai — reasoning likely exhausted max_tokens."

    def test_chat_json_parses_structured_output(self) -> None:
        """Structured JSON calls survive glm-5.3-flash's reasoning_content."""
        adapter = ModelAdapter()
        result = adapter.chat_json(
            'Return JSON {"status": "ok", "score": 42} and nothing else.',
            model="zai/glm-5.3-flash",
            max_tokens=4096,
            temperature=0.0,
        )
        assert isinstance(result, dict)
        assert result.get("status") == "ok"
