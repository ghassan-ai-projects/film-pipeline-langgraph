"""E2E Scenario 11: Full 3-minute / 12-scene flow through script and shot bible.

This scenario validates that a detailed feature-film-scale idea can flow through
intake → constitution → development → script → visual_dev → shot_bible, producing
a real MasterFilmMatrix that is ready for generation planning.

- Mock mode runs in CI and uses the standard ``studio_runtime`` fixture.
- Real mode is manual, gated by ``RUN_REAL_E2E=1`` and ``OPENROUTER_API_KEY``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from film_pipeline.providers import credentials
from film_pipeline.schemas.artifact import ArtifactRef
from film_pipeline.schemas.base import FilmPhase
from film_pipeline.storage.store import ArtifactStore
from film_pipeline.studio.runtime import StudioRuntime

# A concrete 3-minute short with 12 scenes so every phase has material to work on.
THE_LAST_SIGNAL_IDEA = """
A 3-minute science-fiction drama called "The Last Signal".

After a solar flare wipes out global communications, Dr. Elena Voss, a retired
radio astronomer at a remote mountain observatory, picks up a faint, repeating
signal from deep space. Over three days she repairs storm-damaged equipment
while replaying old voicemails from her estranged daughter Maya, who begged her
to come home. With the help of a skeptical local ranger, Elena decodes the
message and must decide whether to broadcast a reply that could reveal Earth's
location to an unknown intelligence.

Twelve scenes, roughly 15 seconds each:
1. Establishing shot: silent observatory at dawn, aurora overhead.
2. Elena wakes the telescope; instruments flicker with static.
3. The signal appears as a rhythmic pulse on her screen.
4. Voicemail flashback: Maya asks Elena to stop running away.
5. Elena climbs the dish in a storm to repair a fried receiver.
6. Ranger Diego arrives, questions her sanity, stays to help.
7. They decode coordinates embedded in the signal.
8. Another voicemail: Maya says she is pregnant.
9. Elena realizes replying could expose humanity.
10. Diego argues the risk is worth knowing we are not alone.
11. Elena makes her choice and transmits a single word: "Hello."
12. Final shot: the telescope silent, a single new pulse arriving in response.

Tone: intimate, melancholic, hopeful. Visual style: cinematic realism with
soft natural light and deep blues. Target runtime: 180 seconds.
"""


def _approve_to_phase(rt: StudioRuntime, target_phase: str) -> dict[str, Any]:
    """Approve phases until the runtime reaches ``target_phase``.

    Guards against infinite loops.
    """
    from tests.e2e.conftest import invoke_tool

    for _ in range(12):
        state = rt.get_active()
        if state is not None and str(state.get("current_phase", "")) == target_phase:
            return {"ok": True, "current_phase": target_phase}
        result = invoke_tool(rt, "approve_phase", confirmed=True)
        if not result.get("ok"):
            return result
        state = rt.get_active()
        if state is not None and str(state.get("current_phase", "")) == target_phase:
            return {"ok": True, "current_phase": target_phase}
    return {"ok": False, "error": f"Did not reach {target_phase} within 12 approvals"}


@pytest.mark.e2e
class TestFull3MinuteFlowMock:
    """Mock-mode full flow — runs in CI."""

    def test_full_flow_to_shot_bible_matrix(
        self,
        studio_runtime: StudioRuntime,
    ) -> None:
        """Drive a detailed idea through all phases to shot_bible and validate the matrix."""
        rt = studio_runtime
        from tests.e2e.conftest import invoke_tool

        project_id = "e2e-3min-mock"

        result = invoke_tool(
            rt,
            "create_film_project",
            project_id=project_id,
            title="The Last Signal",
            slug="the-last-signal",
        )
        assert result["ok"] is True, f"create_film_project failed: {result}"

        result = invoke_tool(rt, "set_active_project", project_ref=project_id)
        assert result["ok"] is True, f"set_active_project failed: {result}"

        result = invoke_tool(rt, "submit_idea", idea=THE_LAST_SIGNAL_IDEA, target_scene_count=2)
        assert result["ok"] is True, f"submit_idea failed: {result}"
        assert result.get("current_phase") is not None

        advance = _approve_to_phase(rt, "shot_bible")
        assert advance["ok"] is True, f"advance to shot_bible failed: {advance}"

        state = rt.get_active()
        assert state is not None
        assert str(state.get("current_phase", "")) == "shot_bible"
        # The user-supplied scene count must propagate into the Story Scope Contract.
        assert state.get("target_scene_count") == 2
        assert state.get("min_scene_count") == 2

        assert rt.services is not None
        store: ArtifactStore = rt.services.artifact_store

        matrix_ref = state.get("shot_matrix_ref", "")
        assert matrix_ref, f"Expected shot_matrix_ref, got keys: {list(state.keys())}"
        matrix_parsed = ArtifactRef.from_string(matrix_ref)
        artifact_id = matrix_parsed.artifact_id
        version = matrix_parsed.version
        matrix_raw = store.load(project_id, FilmPhase("shot_bible"), artifact_id, version)
        assert isinstance(matrix_raw, dict), f"Expected matrix dict, got {type(matrix_raw)}"

        rows = matrix_raw.get("rows", [])
        assert len(rows) >= 1, "Matrix should contain at least one shot row"

        scene_list_ref = state.get("scene_list_ref", "")
        assert scene_list_ref, "Expected scene_list_ref"
        scene_list_parsed = ArtifactRef.from_string(scene_list_ref)
        artifact_id = scene_list_parsed.artifact_id
        version = scene_list_parsed.version
        scene_list_raw = store.load(project_id, FilmPhase("development"), artifact_id, version)
        scenes = scene_list_raw.get("scenes", []) if isinstance(scene_list_raw, dict) else []
        assert len(scenes) >= 1, "Scene list should contain scenes"

        script_ref = state.get("script_ref", "")
        assert script_ref, "Expected script_ref"

        result = invoke_tool(rt, "list_checkpoints")
        assert result["ok"] is True
        checkpoints = result.get("checkpoints", [])
        assert len(checkpoints) >= 5, f"Expected at least 5 checkpoints, got {len(checkpoints)}"

        result = invoke_tool(rt, "get_audit_log", limit=100)
        assert result["ok"] is True
        events = result.get("events", [])
        assert len(events) > 0, "Audit log should have events"


def _real_credentials_available() -> bool:
    return bool(
        os.getenv("RUN_REAL_E2E") == "1"
        and credentials.is_configured("seedance-openrouter")
        and credentials.is_configured("gemini-imagen-4")
    )


@pytest.mark.e2e
@pytest.mark.skipif(
    not _real_credentials_available(),
    reason="RUN_REAL_E2E not set or provider credentials missing",
)
class TestFull3MinuteFlowReal:
    """Real-provider full flow — manual, may incur cost."""

    def test_real_flow_to_shot_bible_matrix(self, tmp_path: Path) -> None:
        """Run the same 3-minute idea through real LLM providers."""
        import film_pipeline.studio.runtime as rt_mod

        previous_override = rt_mod._RUNTIME_MODE_OVERRIDE
        rt_mod._RUNTIME_MODE_OVERRIDE = "real"
        rt = StudioRuntime(server_mode="real", runtime_root=tmp_path / "e2e-real-runtime")
        previous_runtime = rt_mod._RUNTIME
        rt_mod._RUNTIME = rt
        # Prefer Gemini Flash for real-model calls: it is fast enough for an
        # E2E run through multiple phases while still exercising the real
        # OpenRouter adapter path.
        assert rt.services is not None
        router = rt.services.prompt_runner.model_router
        assert router is not None, "ModelRouter is required for real-mode E2E"
        for profile in router.profiles:
            router.profiles[profile]["primary"] = "google/gemini-3-flash-preview"
        try:
            from tests.e2e.conftest import invoke_tool

            project_id = "e2e-3min-real"
            result = invoke_tool(
                rt,
                "create_film_project",
                project_id=project_id,
                title="The Last Signal",
                slug="the-last-signal",
                runtime_mode="real",
                provider_profile="provider.seedance_primary",
                quality_profile="quality.studio",
                film_type_profile="film-type.narrative",
            )
            assert result["ok"] is True, f"create_film_project failed: {result}"

            result = invoke_tool(rt, "set_active_project", project_ref=project_id)
            assert result["ok"] is True

            result = invoke_tool(
                rt, "submit_idea", idea=THE_LAST_SIGNAL_IDEA, target_scene_count=12
            )
            assert result["ok"] is True, f"submit_idea failed: {result}"

            advance = _approve_to_phase(rt, "shot_bible")
            assert advance["ok"] is True, f"advance to shot_bible failed: {advance}"

            state = rt.get_active()
            assert state is not None
            assert str(state.get("current_phase", "")) == "shot_bible"
            assert rt.services is not None

            matrix_ref = state.get("shot_matrix_ref", "")
            assert matrix_ref
            matrix_parsed = ArtifactRef.from_string(matrix_ref)
            artifact_id = matrix_parsed.artifact_id
            version = matrix_parsed.version
            matrix_raw = rt.services.artifact_store.load(
                project_id, FilmPhase("shot_bible"), artifact_id, version
            )
            rows = matrix_raw.get("rows", []) if isinstance(matrix_raw, dict) else []
            assert len(rows) >= 1, "Real run should produce at least one matrix row"

            scene_ids = {str(row.get("scene_id", "")) for row in rows if row.get("scene_id")}
            assert len(scene_ids) >= 12, (
                f"Real matrix should reference all 12 scenes, got {len(scene_ids)}"
            )

            scene_list_ref = state.get("scene_list_ref", "")
            assert scene_list_ref
            scene_list_parsed = ArtifactRef.from_string(scene_list_ref)
            artifact_id = scene_list_parsed.artifact_id
            version = scene_list_parsed.version
            scene_list_raw = rt.services.artifact_store.load(
                project_id, FilmPhase("development"), artifact_id, version
            )
            scenes = scene_list_raw.get("scenes", []) if isinstance(scene_list_raw, dict) else []
            assert len(scenes) >= 12, (
                f"Real scene list should contain at least 12 scenes, got {len(scenes)}"
            )

            script_ref = state.get("script_ref", "")
            assert script_ref, "Expected script_ref"
            script_parsed = ArtifactRef.from_string(script_ref)
            artifact_id = script_parsed.artifact_id
            version = script_parsed.version
            script_raw = rt.services.artifact_store.load(
                project_id, FilmPhase("script"), artifact_id, version
            )
            script_scenes = script_raw.get("scenes", []) if isinstance(script_raw, dict) else []
            assert len(script_scenes) >= 12, (
                f"Real script should contain at least 12 scenes, got {len(script_scenes)}"
            )
        finally:
            rt_mod._RUNTIME = previous_runtime
            rt_mod._RUNTIME_MODE_OVERRIDE = previous_override
