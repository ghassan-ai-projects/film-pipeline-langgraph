"""Integration test: core artifact-producing spine.

Proves that the full intake → constitution → development → script pipeline
produces real, persisted, schema-valid artifacts that downstream phases consume.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from film_pipeline.schemas.artifact import ArtifactRef
from film_pipeline.schemas.base import FilmPhase
from film_pipeline.schemas.script import Script
from film_pipeline.schemas.story_bible import StoryBible
from film_pipeline.studio.runtime import StudioRuntime


class TestArtifactSpine:
    """Prove the core spine produces and consumes persisted artifacts."""

    def test_intake_produces_profile(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("spine-test", "Spine Test")
        rt.set_active("spine-test")

        result = rt._run_phase_node(rt.get_active() or {}, "intake")

        assert result.get("profile_ref"), f"Expected profile_ref in {list(result.keys())}"
        assert "artifact_refs" in result
        assert len(result["artifact_refs"]) >= 1

    def test_constitution_produces_valid_artifact(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("spine-test", "Spine Test")
        rt.set_active("spine-test")
        assert rt.services is not None

        state = rt._run_phase_node(rt.get_active() or {}, "intake")
        result = rt._run_phase_node(state, "constitution")

        artifact_refs = result.get("artifact_refs", [])
        assert len(artifact_refs) >= 2

        constitution_ref = result.get("constitution_ref", "")
        assert constitution_ref

        constitution_ref_parsed = ArtifactRef.from_string(constitution_ref)
        raw = rt.services.artifact_store.load(
            "spine-test",
            phase=FilmPhase("constitution"),
            artifact_id=constitution_ref_parsed.artifact_id,
            version=constitution_ref_parsed.version,
        )
        assert raw["theme"]
        assert raw["tone"]
        assert len(raw["character_truths"]) >= 1
        assert len(raw["taboo_mistakes"]) >= 1

    def test_development_consumes_constitution(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("spine-test", "Spine Test")
        rt.set_active("spine-test")
        assert rt.services is not None

        state = rt._run_phase_node(rt.get_active() or {}, "intake")
        state = rt._run_phase_node(state, "constitution")
        result = rt._run_phase_node(state, "development")

        assert result.get("constitution_ref")
        treatment_ref = result.get("treatment_ref", "")
        assert treatment_ref

        treatment_ref_parsed = ArtifactRef.from_string(treatment_ref)
        raw = rt.services.artifact_store.load(
            "spine-test",
            phase=FilmPhase("development"),
            artifact_id=treatment_ref_parsed.artifact_id,
            version=treatment_ref_parsed.version,
        )
        assert raw["text"]
        assert len(raw["themes"]) >= 1
        assert raw.get("act_map") is not None

    def test_script_consumes_development(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("spine-test", "Spine Test")
        rt.set_active("spine-test")
        assert rt.services is not None

        state = rt._run_phase_node(rt.get_active() or {}, "intake")
        state = rt._run_phase_node(state, "constitution")
        state = rt._run_phase_node(state, "development")
        result = rt._run_phase_node(state, "script")

        assert result.get("constitution_ref")
        assert result.get("treatment_ref")
        script_ref = result.get("script_ref", "")
        assert script_ref

        script_ref_parsed = ArtifactRef.from_string(script_ref)
        raw = rt.services.artifact_store.load(
            "spine-test",
            phase=FilmPhase("script"),
            artifact_id=script_ref_parsed.artifact_id,
            version=script_ref_parsed.version,
        )
        assert raw["title"]
        assert len(raw["scenes"]) >= 1

    def test_full_spine_produces_all_artifacts(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("spine-test", "Spine Test")
        rt.set_active("spine-test")

        phases = ["intake", "constitution", "development", "script"]
        state: dict[str, Any] = rt.get_active() or {}

        for phase in phases:
            state = rt._run_phase_node(state, phase)
            assert state.get("artifact_refs"), f"Phase {phase} should produce artifacts"
            assert state["current_phase"] == phase

        refs = state.get("artifact_refs", [])
        assert len(refs) >= 5

        assert state.get("constitution_ref")
        assert state.get("treatment_ref")
        assert state.get("scene_list_ref")
        assert state.get("script_ref")
        assert state.get("story_bible_ref")

    def test_script_output_is_schema_valid(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("spine-test", "Spine Test")
        rt.set_active("spine-test")
        assert rt.services is not None

        state = rt._run_phase_node(rt.get_active() or {}, "intake")
        state = rt._run_phase_node(state, "constitution")
        state = rt._run_phase_node(state, "development")
        result = rt._run_phase_node(state, "script")

        # Load story bible and construct typed object
        bible_ref = result.get("story_bible_ref", "")
        assert bible_ref
        bible_parsed = ArtifactRef.from_string(bible_ref)
        bible_id = bible_parsed.artifact_id
        bible_raw = rt.services.artifact_store.load(
            "spine-test",
            phase=FilmPhase("script"),
            artifact_id=bible_id,
            version=1,
        )
        bible = StoryBible(**bible_raw)
        assert bible.logline.text
        assert bible.premise.dramatic_question

        # Load script and construct typed object
        script_ref = result.get("script_ref", "")
        assert script_ref
        script_parsed = ArtifactRef.from_string(script_ref)
        script_id = script_parsed.artifact_id
        script_raw = rt.services.artifact_store.load(
            "spine-test",
            phase=FilmPhase("script"),
            artifact_id=script_id,
            version=1,
        )
        script = Script(**script_raw)
        assert script.title == "After the Fall"
        assert script.total_scenes >= 2
        for scene in script.scenes:
            assert scene.scene_heading
            assert len(scene.scene_id) > 0

    def test_approval_advances_through_spine(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("spine-test", "Spine Test")
        rt.set_active("spine-test")

        state = rt._run_phase_node(rt.get_active() or {}, "intake")
        rt.projects["spine-test"] = state
        assert state["current_phase"] == "intake"
        assert state["human_approval_required"] is True

        result = rt.approve_phase()
        assert result["current_phase"] == "constitution"
        assert result["human_approval_required"] is True

        result = rt.approve_phase()
        assert result["current_phase"] == "development"

        result = rt.approve_phase()
        assert result["current_phase"] == "script"

    def test_visual_dev_produces_reference_index(self, tmp_path: Path) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.create_project("spine-test", "Spine Test")
        rt.set_active("spine-test")
        assert rt.services is not None

        state = rt._run_phase_node(rt.get_active() or {}, "intake")
        state = rt._run_phase_node(state, "constitution")
        state = rt._run_phase_node(state, "development")
        state = rt._run_phase_node(state, "script")
        result = rt._run_phase_node(state, "visual_dev")

        assert result["current_phase"] == "visual_dev"
        assert result["human_approval_required"] is True

        visual_refs = result.get("visual_refs", "")
        assert ArtifactRef.from_string(visual_refs).artifact_id == "reference_index"

        # Verify artifact was persisted
        visual_parsed = ArtifactRef.from_string(visual_refs)
        artifact_id = visual_parsed.artifact_id
        version = visual_parsed.version

        from film_pipeline.schemas.base import FilmPhase

        raw = rt.services.artifact_store.load(
            "spine-test",
            FilmPhase("visual_dev"),
            artifact_id,
            version,
        )
        assert raw.get("project_id")
        entries = raw.get("entries", [])
        assert len(entries) >= 1
        assert entries[0].get("reference_id", "").startswith("ref_")
