"""E2E smoke test against the default real chat provider (z.ai).

**NOT in CI.** Gated behind ``RUN_REAL_E2E=1`` env var.
Requires ``ZAI_API_KEY`` set in the environment (and the other provider keys
needed by the selected real profile).

Usage::

    RUN_REAL_E2E=1 ZAI_API_KEY=... \\
        pytest tests/e2e/test_real_provider_smoke.py -v -s

Cost: ~$0.01-0.05 per run (1-2 short LLM calls).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.providers import credentials
from film_pipeline.schemas._base import FilmPhase

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REAL_E2E") != "1" or not credentials.is_configured("zai"),
    reason="Set RUN_REAL_E2E=1 and configure ZAI_API_KEY for manual live tests",
)


@pytest.mark.e2e
class TestRealProviderSmoke:
    """Smoke-test the graph with real LLM calls through z.ai."""

    def test_intake_with_real_llm(self, tmp_path: Path) -> None:
        """Verify intake phase produces a real project profile.

        Submits a concrete film idea and asserts the resulting profile
        contains the expected structural fields and plausible content.
        """
        rt = StudioRuntime(server_mode="real", runtime_root=tmp_path / "runtime")
        rt.create_project("real-smoke", "Real Smoke Test", slug="real-smoke")
        rt.set_active("real-smoke")

        state: dict[str, Any] = rt.get_active() or {}
        state["idea"] = (
            "A short documentary about a lighthouse keeper in Nova Scotia "
            "who discovers a message in a bottle that changes everything. "
            "Tone: melancholic but hopeful. Target: 4 minutes."
        )
        result = rt.run_graph(state)

        # Graph pauses at approval gate after intake
        assert result.get("current_phase") == "intake"
        assert result.get("human_approval_required") is True

        # Verify artifact was saved
        refs = result.get("artifact_refs", [])
        assert len(refs) >= 1, f"Expected at least 1 artifact ref, got {refs}"

        profile_ref = result.get("profile_ref", "")
        assert profile_ref, "Expected profile_ref to be set"

        # Load the artifact and verify it has real content
        parts = profile_ref.split(":")
        artifact_id = parts[1] if len(parts) > 1 else ""
        assert artifact_id, f"Could not parse artifact_id from {profile_ref}"

        assert rt.services is not None
        raw = rt.services.artifact_store.load(
            "real-smoke",
            phase=FilmPhase("intake"),
            artifact_id=artifact_id,
            version=1,
        )
        assert isinstance(raw, dict), f"Expected dict, got {type(raw)}"
        identity = raw.get("identity", {})
        title = str(identity.get("title", ""))
        assert title, f"Expected identity.title in profile, got keys: {list(raw.keys())}"
        assert raw.get("target_runtime_seconds", 0) > 0, (
            f"Expected positive runtime, got {raw.get('target_runtime_seconds')}"
        )

        # Content plausibility: real LLM should produce a plausible title
        assert len(title) > 1, f"Title too short: {title!r}"

    def test_intake_then_approve_constitution(self, tmp_path: Path) -> None:
        """Verify intake → approve → constitution with real LLM calls.

        This exercises two agents (intake + constitution) and the approval
        path to confirm the graph and services work end-to-end.
        """
        rt = StudioRuntime(server_mode="real", runtime_root=tmp_path / "runtime")
        rt.create_project("real-spine", "Real Spine Test", slug="real-spine")
        rt.set_active("real-spine")

        state: dict[str, Any] = rt.get_active() or {}
        state["idea"] = (
            "A five-minute animated short about a stray cat who befriends "
            "a lonely robot in a post-industrial city. Dialogue-free. "
            "Visual style: watercolor-inspired 2D animation."
        )
        result = rt.run_graph(state)
        assert result.get("current_phase") == "intake"
        rt.projects["real-spine"] = result

        # Approve intake → should advance to constitution
        advanced = rt.approve_phase()
        assert advanced.get("current_phase") == "constitution", (
            f"Expected constitution, got {advanced.get('current_phase')}"
        )

        # Constitution should produce an artifact
        constitution_ref = advanced.get("constitution_ref", "")
        assert constitution_ref, f"Expected constitution_ref, got keys: {list(advanced.keys())}"

        # Load and verify
        parts = constitution_ref.split(":")
        artifact_id = parts[1] if len(parts) > 1 else ""
        assert rt.services is not None
        raw = rt.services.artifact_store.load(
            "real-spine",
            phase=FilmPhase("constitution"),
            artifact_id=artifact_id,
            version=1,
        )
        assert isinstance(raw, dict)
        assert raw.get("theme"), f"Constitution missing theme: {list(raw.keys())}"
        assert raw.get("tone"), "Constitution missing tone"
        assert raw.get("visual_language"), "Constitution missing visual_language"
        assert raw.get("quality_bar"), "Constitution missing quality_bar"
