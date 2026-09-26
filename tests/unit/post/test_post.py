"""Tests for post-production agents."""

from __future__ import annotations

from pathlib import Path

from film_pipeline.post.assembly_agent import AssemblyAgent
from film_pipeline.post.audio_design_agent import AudioDesignAgent
from film_pipeline.post.delivery_packaging_agent import DeliveryPackagingAgent
from film_pipeline.post.subtitle_agent import SubtitleAgent
from film_pipeline.post.transition_agent import TransitionAgent
from film_pipeline.post.validators import PostValidator
from film_pipeline.storage.store import ArtifactStore


class TestAssembly:
    def test_build_plan(self) -> None:
        agent = AssemblyAgent()
        plan = agent.build_plan(
            project_id="test",
            shot_ids=["S001-01", "S001-02", "S001-03"],
            clip_paths=["clips/S001-01.mp4", "clips/S001-02.mp4"],
        )
        assert plan.project_id == "test"
        assert plan.clip_count == 2  # Only 2 of 3 shots have clips
        assert len(plan.missing_assets) == 1

    def test_build_plan_duplicate_skipped(self) -> None:
        agent = AssemblyAgent()
        plan = agent.build_plan(
            project_id="test",
            shot_ids=["S001", "S001"],
            clip_paths=["clips/S001.mp4"],
        )
        assert plan.clip_count == 1
        assert any("Duplicate" in n for n in plan.notes)

    def test_build_plan_transitions(self) -> None:
        agent = AssemblyAgent()
        plan = agent.build_plan(
            project_id="test",
            shot_ids=["S001", "S002", "S003"],
            clip_paths=["clips/S001.mp4", "clips/S002.mp4", "clips/S003.mp4"],
        )
        assert len(plan.transition_points) == 2  # 3 clips → 2 transitions

    def test_validate_plan_valid(self) -> None:
        agent = AssemblyAgent()
        plan = agent.build_plan(
            project_id="test",
            shot_ids=["S001"],
            clip_paths=["clips/S001.mp4"],
        )
        issues = agent.validate_plan(plan)
        assert len(issues) == 0

    def test_validate_plan_empty(self) -> None:
        agent = AssemblyAgent()
        plan = agent.build_plan(
            project_id="test",
            shot_ids=["S001"],
            clip_paths=[],
        )
        issues = agent.validate_plan(plan)
        assert len(issues) > 0


class TestTransitions:
    def test_plan_transitions(self) -> None:
        agent = TransitionAgent()
        plan = agent.plan_transitions(
            project_id="test",
            clip_paths=["c1.mp4", "c2.mp4", "c3.mp4"],
        )
        assert plan.total_count == 2

    def test_plan_transitions_with_types(self) -> None:
        agent = TransitionAgent()
        plan = agent.plan_transitions(
            project_id="test",
            clip_paths=["c1.mp4", "c2.mp4"],
            scene_types={"c1.mp4": "action", "c2.mp4": "mood"},
        )
        assert plan.transitions[0]["type"] == "dissolve"

    def test_transition_types_matches_canonical_home(self) -> None:
        """post re-exports exactly the canonical vocabulary from schemas/base."""
        from film_pipeline.post.transition_agent import TRANSITION_TYPES
        from film_pipeline.schemas.base import TRANSITION_TYPES as CANONICAL_TRANSITION_TYPES

        assert TRANSITION_TYPES == CANONICAL_TRANSITION_TYPES


class TestAudioDesign:
    def test_plan_audio(self) -> None:
        agent = AudioDesignAgent()
        plan = agent.plan_audio(
            project_id="test",
            scene_count=3,
            total_duration=90.0,
        )
        # 3 dialogue + 1 music + 3 sfx = 7 tracks
        assert plan.total_tracks == 7

    def test_plan_audio_no_dialogue(self) -> None:
        agent = AudioDesignAgent()
        plan = agent.plan_audio(
            project_id="test",
            scene_count=2,
            total_duration=60.0,
            has_dialogue={"S001": False, "S002": False},
        )
        # 0 dialogue + 1 music + 2 sfx = 3
        assert plan.total_tracks == 3


class TestDelivery:
    def test_build_package_complete(self) -> None:
        agent = DeliveryPackagingAgent()
        package = agent.build_package(
            project_id="test",
            video_path="final.mp4",
            subtitle_path="subs.srt",
            audio_stems_dir="stems/",
            validation_report_path="report.json",
            cost_report_path="cost.json",
            credits_path="credits.json",
        )
        assert package.is_complete is True
        assert len(package.missing_items) == 0

    def test_build_package_incomplete(self) -> None:
        agent = DeliveryPackagingAgent()
        package = agent.build_package(
            project_id="test",
            video_path="final.mp4",
        )
        assert package.is_complete is False
        assert len(package.missing_items) > 0

    def test_build_package_empty(self) -> None:
        agent = DeliveryPackagingAgent()
        package = agent.build_package(project_id="test")
        assert package.is_complete is False
        assert len(package.files) == 0


class TestSubtitles:
    def test_generate_subtitles(self) -> None:
        agent = SubtitleAgent()
        plan = agent.generate_subtitles(
            project_id="test",
            dialogue_lines=["Hello world", "Goodbye"],
        )
        assert plan.cue_count == 2
        assert plan.language == "en"

    def test_to_srt(self) -> None:
        agent = SubtitleAgent()
        plan = agent.generate_subtitles(
            project_id="test",
            dialogue_lines=["First line"],
        )
        srt = plan.to_srt()
        assert "1\n" in srt
        assert "First line" in srt
        assert "-->" in srt


class TestValidators:
    def test_validate_assembly(self) -> None:
        validator = PostValidator()
        agent = AssemblyAgent()
        plan = agent.build_plan(
            project_id="test",
            shot_ids=["S001"],
            clip_paths=["clips/S001.mp4"],  # Must contain shot_id
        )
        issues = validator.validate_assembly(plan)
        assert len(issues) == 0

    def test_validate_transitions(self) -> None:
        validator = PostValidator()
        agent = TransitionAgent()
        plan = agent.plan_transitions(
            project_id="test",
            clip_paths=["c1.mp4", "c2.mp4"],
        )
        issues = validator.validate_transitions(plan, clip_count=2)
        assert len(issues) == 0

    def test_validate_transitions_bad_type(self) -> None:
        validator = PostValidator()

        class _BadPlan:
            total_count = 1

            def __init__(self) -> None:
                self.transitions = [{"type": "explosion"}]

        issues = validator.validate_transitions(_BadPlan(), clip_count=2)  # type: ignore[arg-type]
        assert len(issues) > 0

    def test_validate_delivery(self) -> None:
        validator = PostValidator()
        agent = DeliveryPackagingAgent()
        package = agent.build_package(
            project_id="test",
            video_path="f.mp4",
            subtitle_path="s.srt",
            audio_stems_dir="a/",
            validation_report_path="r.json",
            cost_report_path="c.json",
            credits_path="cr.json",
        )
        issues = validator.validate_delivery(package)
        assert len(issues) == 0

    def test_validate_subtitles(self) -> None:
        validator = PostValidator()
        issues = validator.validate_subtitles(cue_count=3, dialogue_count=3)
        assert len(issues) == 0

    def test_validate_subtitles_mismatch(self) -> None:
        validator = PostValidator()
        issues = validator.validate_subtitles(cue_count=2, dialogue_count=5)
        assert len(issues) > 0

    def test_validate_assembly_no_clips(self) -> None:
        """Branch: plan.clips is empty."""
        validator = PostValidator()
        from film_pipeline.post.assembly_agent import AssemblyPlan

        plan = AssemblyPlan(plan_id="id", project_id="p", clips=[], clip_count=0)
        issues = validator.validate_assembly(plan)
        assert any("No clips" in i for i in issues)

    def test_validate_assembly_missing_assets(self) -> None:
        """Branch: plan has missing_assets."""
        validator = PostValidator()
        from film_pipeline.post.assembly_agent import AssemblyPlan

        plan = AssemblyPlan(
            plan_id="id",
            project_id="p",
            clips=["clip1.mp4"],
            missing_assets=["S002"],
            clip_count=1,
        )
        issues = validator.validate_assembly(plan)
        assert any("Missing assets" in i for i in issues)

    def test_validate_transitions_count_mismatch(self) -> None:
        """Branch: expected != plan.total_count."""
        validator = PostValidator()
        from film_pipeline.post.transition_agent import TransitionPlan

        plan = TransitionPlan(plan_id="id", project_id="p", total_count=0)
        issues = validator.validate_transitions(plan, clip_count=5)
        assert any("Expected 4" in i for i in issues)

    def test_validate_delivery_no_files(self) -> None:
        """Branch: package.files is empty."""
        validator = PostValidator()
        from film_pipeline.post.delivery_packaging_agent import DeliveryPackage

        package = DeliveryPackage(
            package_id="id",
            project_id="p",
            subtitles_included=True,
            audio_stems_included=True,
            validation_report_included=True,
            cost_report_included=True,
            credits_included=True,
        )
        issues = validator.validate_delivery(package)
        assert any("No files" in i for i in issues)

    def test_validate_subtitles_zero_cues(self) -> None:
        """Branch: cue_count == 0."""
        validator = PostValidator()
        issues = validator.validate_subtitles(cue_count=0, dialogue_count=5)
        assert any("No subtitle cues" in i for i in issues)


# ── Artifact persistence tests ──────────────────────────────────────────────


class TestAssemblyPersist:
    def test_persist_plan_to_artifact_store(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        agent = AssemblyAgent()
        plan = agent.build_plan(
            project_id="test-persist",
            shot_ids=["S001", "S002"],
            clip_paths=["clips/S001.mp4", "clips/S002.mp4"],
        )
        ref = agent.persist(plan, store)
        assert ref.startswith("artifact:")
        # Verify artifact is loadable
        from film_pipeline.schemas.base import FilmPhase

        data = store.load("test-persist", FilmPhase("post"), "assembly_manifest", 1)
        assert data["clip_count"] == 2
        assert len(data["clip_order"]) == 2


class TestSubtitlePersist:
    def test_persist_subtitles_to_artifact_store(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        agent = SubtitleAgent()
        plan = agent.generate_subtitles(
            project_id="test-persist",
            dialogue_lines=["Hello", "World"],
        )
        ref = agent.persist(plan, store)
        assert ref.startswith("artifact:")
        from film_pipeline.schemas.base import FilmPhase

        data = store.load("test-persist", FilmPhase("post"), "subtitles", 1)
        assert data["cue_count"] == 2
        assert "Hello" in data["srt_content"]
        assert "-->" in data["srt_content"]


class TestDeliveryPersist:
    def test_persist_delivery_package(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        agent = DeliveryPackagingAgent()
        package = agent.build_package(
            project_id="test-persist",
            video_path="final.mp4",
            subtitle_path="subs.srt",
            audio_stems_dir="stems/",
            validation_report_path="report.json",
            cost_report_path="cost.json",
            credits_path="credits.json",
        )
        ref = agent.persist(package, store)
        assert ref.startswith("artifact:")
        from film_pipeline.schemas.base import FilmPhase

        data = store.load("test-persist", FilmPhase("delivery"), "delivery_package", 1)
        assert data["is_complete"] is True
        assert data["subtitles_included"] is True

    def test_validate_delivery_package(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        agent = DeliveryPackagingAgent()
        package = agent.build_package(
            project_id="test-validate",
            video_path="final_video.mp4",
            subtitle_path="subtitles.srt",
            audio_stems_dir="stems/",
            validation_report_path="validation_report.json",
            cost_report_path="cost_report.json",
            credits_path="credits.txt",
        )
        # Also add review_cut for completeness
        package.files.append({"path": "review_cut.mp4", "type": "video"})
        package.files.append({"path": "still_01.png", "type": "still"})
        result = agent.validate(package, store)
        assert result["is_complete"] is True
        assert result["score"] == 100.0
        assert result["status"] == "pass"

    def test_validate_incomplete_package(self, tmp_path: Path) -> None:
        store = ArtifactStore(root=tmp_path / "artifacts")
        agent = DeliveryPackagingAgent()
        package = agent.build_package(
            project_id="test-incomplete",
            video_path="final.mp4",
        )
        result = agent.validate(package, store)
        assert result["is_complete"] is False
        assert len(result["missing_items"]) > 0
        assert result["score"] < 100.0
