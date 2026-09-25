"""Tests for operator application services."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from film_pipeline.app.runtime import create_runtime
from film_pipeline.operations.errors import BackendOperationError, ProjectNotFoundError
from film_pipeline.operations.models import OperatorCommentRequest, ProjectCreateRequest
from film_pipeline.operations.operator import OperatorService
from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.film_constitution import FilmConstitution
from film_pipeline.schemas.story_bible import SceneList
from film_pipeline.storage.manifest import AssetEntry, AssetManifest, write_manifest
from film_pipeline.storage.store import ArtifactStore


def _service(tmp_path: Path) -> OperatorService:
    runtime = create_runtime("mock")
    runtime.runtime_root = tmp_path
    assert runtime.services is not None
    runtime.services.artifact_store = ArtifactStore(root=tmp_path / "projects")
    return OperatorService(runtime)


class TestOperatorService:
    def test_create_project_from_idea_runs_intake(self, tmp_path: Path) -> None:
        service = _service(tmp_path)

        result = service.create_project(
            ProjectCreateRequest(
                project_id="field-message",
                title="The Field Message",
                slug="the-field-message",
                idea="A walker crosses five changing fields while nature carries a message.",
            )
        )

        assert result.ok is True
        assert result.project_id == "field-message"
        assert result.current_phase == "intake"

        dashboard = service.get_dashboard("field-message")
        assert dashboard.project_id == "field-message"
        assert dashboard.title == "The Field Message"
        assert dashboard.current_phase == "intake"
        assert dashboard.workflow_mode == "manual"
        assert dashboard.artifact_count >= 1
        assert "_services" not in service.runtime.projects["field-message"]

        review = service.get_review_workspace("field-message")
        assert review.phase == "intake"
        assert review.candidate_artifacts
        assert "Review" in review.recommendation

    def test_list_projects_exposes_review_status(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(
            ProjectCreateRequest(
                project_id="quiet-city",
                title="Quiet City",
                idea="A composer hears a city become silent overnight.",
            )
        )

        projects = service.list_projects()

        assert len(projects) == 1
        assert projects[0].project_id == "quiet-city"
        assert projects[0].current_phase == "intake"
        assert projects[0].status == "awaiting_review"
        assert projects[0].awaiting_review is True
        assert projects[0].project_kind == "production"

    def test_list_projects_discovers_and_separates_artifact_folders(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        assert service.runtime.services is not None
        service.runtime.services.artifact_store = ArtifactStore(root=tmp_path / "projects")
        store = service.runtime.services.artifact_store
        store.save(
            SceneList(scenes=[]),
            ArtifactMetadata(
                artifact_id="scene_list",
                artifact_type=ArtifactType.SCENE_LIST,
                project_id="real-short",
                phase=FilmPhase.SCRIPT,
                version=1,
                status=ArtifactStatus.CANDIDATE,
                created_by="test",
                created_at=datetime.now(UTC),
            ),
        )
        store.save(
            SceneList(scenes=[]),
            ArtifactMetadata(
                artifact_id="scene_list",
                artifact_type=ArtifactType.SCENE_LIST,
                project_id="fixture-short-test",
                phase=FilmPhase.SCRIPT,
                version=1,
                status=ArtifactStatus.CANDIDATE,
                created_by="test",
                created_at=datetime.now(UTC),
            ),
        )

        projects = {project.project_id: project for project in service.list_projects()}

        assert projects["real-short"].status == "discovered"
        assert projects["real-short"].project_kind == "production"
        assert projects["real-short"].current_phase == "script"
        assert projects["fixture-short-test"].project_kind == "test"
        assert projects["fixture-short-test"].project_root.endswith("fixture-short-test")

    def test_set_active_project_hydrates_discovered_artifact_folder(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        assert service.runtime.services is not None
        service.runtime.services.artifact_store.save(
            SceneList(scenes=[]),
            ArtifactMetadata(
                artifact_id="scene_list",
                artifact_type=ArtifactType.SCENE_LIST,
                project_id="archived-short",
                phase=FilmPhase.SCRIPT,
                version=1,
                status=ArtifactStatus.CANDIDATE,
                created_by="test",
                created_at=datetime.now(UTC),
            ),
        )

        dashboard = service.set_active_project("archived-short")

        assert dashboard.project_id == "archived-short"
        assert dashboard.current_phase == "script"
        assert dashboard.status == "in_progress"
        assert service.runtime.active_project_id == "archived-short"
        assert service.list_artifacts("archived-short")[0]["artifact_id"] == "scene_list"

    def test_create_project_accepts_test_project_kind(self, tmp_path: Path) -> None:
        service = _service(tmp_path)

        service.create_project(
            ProjectCreateRequest(project_id="scratch", title="Scratch", project_kind="test")
        )

        assert service.runtime.projects["scratch"]["project_kind"] == "test"
        assert service.list_projects()[0].project_kind == "test"

    def test_create_project_rejects_unknown_project_kind(self, tmp_path: Path) -> None:
        service = _service(tmp_path)

        with pytest.raises(BackendOperationError, match="project_kind"):
            service.create_project(
                ProjectCreateRequest(
                    project_id="bad-kind",
                    title="Bad Kind",
                    project_kind="sandbox",
                )
            )

    def test_approve_phase_advances_and_creates_checkpoint(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(
            ProjectCreateRequest(
                project_id="gate-test",
                title="Gate Test",
                idea="A projectionist restores a lost frame.",
            )
        )

        result = service.approve_phase("gate-test")

        assert result.ok is True
        assert result.current_phase == "constitution"
        checkpoints = service.list_checkpoints("gate-test")
        # Intake submission now auto-checkpoints, so at least one post-approval
        # checkpoint at constitution must exist.
        assert len(checkpoints) >= 1
        assert checkpoints[-1]["phase"] == "constitution"

    def test_approve_phase_advances_through_pre_generation_phases(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(
            ProjectCreateRequest(
                project_id="multi-phase",
                title="Multi Phase",
            )
        )
        service.submit_idea(
            "multi-phase",
            "A projectionist restores a lost frame and discovers it predicts the future.",
        )

        for expected in ("constitution", "development", "script", "visual_dev", "shot_bible"):
            result = service.approve_phase("multi-phase")
            assert result.ok is True
            assert result.current_phase == expected

    def test_validation_workspace_splits_blocking_and_non_blocking_issues(
        self, tmp_path: Path
    ) -> None:
        service = _service(tmp_path)
        service.create_project(
            ProjectCreateRequest(
                project_id="validation-test",
                title="Validation Test",
                idea="A projectionist restores a lost frame.",
            )
        )
        state = service.runtime.projects["validation-test"]
        state["_validation_reports"] = [{"validator_id": "script-structure", "score": 91}]
        state["issues"] = [
            {"severity": "blocking", "message": "Missing shot prompt."},
            {"severity": "warning", "message": "Weak scene transition."},
        ]

        workspace = service.get_validation_workspace("validation-test")

        assert workspace.source == "stored_state"
        assert len(workspace.reports) == 1
        assert len(workspace.blocking_issues) == 1
        assert len(workspace.non_blocking_issues) == 1

    def test_operator_comments_are_persisted_and_audited(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="notes", title="Notes"))

        comment = service.add_operator_comment(
            OperatorCommentRequest(
                target_type="scene",
                target_id="SC_007",
                phase="script",
                body="This scene needs a sharper emotional turn.",
            ),
            "notes",
        )

        comments = service.list_operator_comments("notes")
        audit = service.get_audit_feed("notes")
        assert comment.comment_id.startswith("comment:")
        assert comments == [comment]
        assert comments[0].target_type == "scene"
        assert comments[0].target_id == "SC_007"
        assert comments[0].body == "This scene needs a sharper emotional turn."
        assert any(event.action == "add_operator_comment" for event in audit)

    def test_operator_comment_requires_target_and_body(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="bad-notes", title="Bad Notes"))

        with pytest.raises(BackendOperationError, match="comment body is required"):
            service.add_operator_comment(
                OperatorCommentRequest(target_type="scene", target_id="SC_001", body=""),
                "bad-notes",
            )

    def test_submit_idea_requires_text(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="empty", title="Empty"))

        with pytest.raises(BackendOperationError, match="idea is required"):
            service.submit_idea("empty", "")

    def test_unknown_project_raises_actionable_error(self, tmp_path: Path) -> None:
        service = _service(tmp_path)

        with pytest.raises(ProjectNotFoundError, match="not found"):
            service.get_dashboard("missing")

    def test_create_project_requires_project_id_and_title(self, tmp_path: Path) -> None:
        service = _service(tmp_path)

        with pytest.raises(BackendOperationError, match="project_id is required"):
            service.create_project(ProjectCreateRequest(project_id=" ", title="Title"))
        with pytest.raises(BackendOperationError, match="title is required"):
            service.create_project(ProjectCreateRequest(project_id="p1", title=" "))

    def test_set_active_project_returns_dashboard(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="active", title="Active"))

        dashboard = service.set_active_project("active")

        assert dashboard.project_id == "active"
        assert service.runtime.active_project_id == "active"

    def test_active_project_required_for_default_views(self, tmp_path: Path) -> None:
        service = _service(tmp_path)

        with pytest.raises(ProjectNotFoundError, match="No active project"):
            service.get_dashboard()

    def test_create_project_resolves_and_stores_profile_stack(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(
            ProjectCreateRequest(
                project_id="profiled",
                title="Profiled",
                film_type_profile="narrative",
                quality_profile="draft",
                provider_profile="mock-demo",
            )
        )

        state = service.runtime.projects["profiled"]
        assert state["profile_stack"]["film_type_profile"] == "film-type.narrative"
        assert state["profile_stack"]["quality_profile"] == "quality.draft"
        assert state["profile_stack"]["provider_profile"] == "mock-demo"
        assert "resolved_config" in state
        assert service.runtime.list_providers() == [
            "mock-video-provider",
            "mock-image-provider",
        ]
        assert service.runtime.get_provider_health("mock-video-provider") == {
            "status": "healthy",
            "reason": "",
        }
        assert service.runtime.get_provider_health("mock-image-provider") == {
            "status": "healthy",
            "reason": "",
        }

        dashboard = service.get_dashboard("profiled")
        assert dashboard.profile_stack["film_type_profile"] == "film-type.narrative"
        assert dashboard.profile_stack["quality_profile"] == "quality.draft"

    def test_review_workspace_before_phase_recommends_starting_intake(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="draft", title="Draft"))

        review = service.get_review_workspace("draft")

        assert review.phase == ""
        assert review.recommendation == "Submit an idea to start intake."
        assert review.candidate_artifacts == []

    def test_validation_workspace_without_reports_has_none_source(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="no-reports", title="No Reports"))

        workspace = service.get_validation_workspace("no-reports")

        assert workspace.source == "none"
        assert workspace.reports == []
        assert workspace.blocking_issues == []
        assert workspace.non_blocking_issues == []

    def test_request_revision_requires_note(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="revision", title="Revision"))

        with pytest.raises(BackendOperationError, match="revision note is required"):
            service.request_revision(" ", "revision")

    def test_operator_comment_requires_target_type_and_id(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="bad-target", title="Bad Target"))

        with pytest.raises(BackendOperationError, match="comment target_type is required"):
            service.add_operator_comment(
                OperatorCommentRequest(target_type="", target_id="SC_001", body="Body"),
                "bad-target",
            )
        with pytest.raises(BackendOperationError, match="comment target_id is required"):
            service.add_operator_comment(
                OperatorCommentRequest(target_type="scene", target_id="", body="Body"),
                "bad-target",
            )

    def test_comment_listing_filters_resolved_comments_by_default(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="resolved", title="Resolved"))
        comment = service.add_operator_comment(
            OperatorCommentRequest(target_type="scene", target_id="SC_001", body="Body"),
            "resolved",
        )
        service.runtime.projects["resolved"]["_operator_comments"][0]["resolved"] = True

        assert service.list_operator_comments("resolved") == []
        assert service.list_operator_comments("resolved", include_resolved=True)[0].comment_id == (
            comment.comment_id
        )

    def test_status_for_blocked_stalled_completed_and_created_projects(
        self, tmp_path: Path
    ) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="created", title="Created"))
        service.create_project(ProjectCreateRequest(project_id="complete", title="Complete"))
        service.create_project(ProjectCreateRequest(project_id="stalled", title="Stalled"))
        service.create_project(ProjectCreateRequest(project_id="blocked", title="Blocked"))
        service.runtime.projects["complete"]["completed"] = True
        service.runtime.projects["stalled"]["_stalled_phase"] = "script"
        service.runtime.projects["blocked"]["current_phase"] = "script"
        service.runtime.projects["blocked"]["issues"] = [
            {"severity": "blocking", "message": "Needs revision."}
        ]

        projects = {project.project_id: project for project in service.list_projects()}

        assert projects["created"].status == "created"
        assert projects["complete"].status == "complete"
        assert projects["stalled"].status == "stalled"
        assert projects["blocked"].has_blockers is True

    def test_provider_status_and_global_audit_feed(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="providers", title="Providers"))
        service.runtime.set_provider_health("veo", "degraded", "quota")

        providers = service.list_provider_status()
        audit = service.get_audit_feed(limit=5)

        assert providers == [{"provider_id": "veo", "status": "degraded", "reason": "quota"}]
        assert any(event.action == "create_project" for event in audit)
        assert all(event.summary for event in audit)

    def test_inspect_artifact_returns_detail_from_store(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="artifact", title="Artifact"))
        assert service.runtime.services is not None
        constitution = FilmConstitution(
            project_id="artifact",
            theme="Memory heals through action.",
            tone="precise",
            emotional_promise="clarity",
            visual_language="still frames",
            camera_philosophy="observational",
            quality_bar="specificity",
        )
        service.runtime.services.artifact_store.save(
            constitution,
            ArtifactMetadata(
                artifact_id="film_constitution",
                artifact_type=ArtifactType.FILM_CONSTITUTION,
                project_id="artifact",
                phase=FilmPhase.CONSTITUTION,
                version=1,
                status=ArtifactStatus.CANDIDATE,
                created_by="test",
                created_at=datetime.now(UTC),
            ),
        )

        artifacts = service.list_artifacts("artifact", phase="constitution")
        detail = service.inspect_artifact("film_constitution", "constitution", 1, "artifact")

        assert artifacts == [
            {
                "artifact_id": "film_constitution",
                "artifact_type": "film_constitution",
                "phase": "constitution",
                "version": 1,
                "status": "candidate",
            }
        ]
        assert detail.artifact_id == "film_constitution"
        assert detail.phase == "constitution"
        assert detail.body["theme"] == "Memory heals through action."

    def test_list_assets_returns_scene_and_shot_manifest_rows(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="assets", title="Assets"))
        assert service.runtime.services is not None
        manifest = AssetManifest(project_id="assets")
        manifest.add_take(
            AssetEntry(
                asset_id="clip_SC_001_shot_001_take_001",
                path="07-generated-assets/scenes/SC_001/shot_001/take_001.mp4",
                kind="generated_clip",
                scene_id="SC_001",
                shot_id="shot_001",
                take=1,
                active=True,
            )
        )
        write_manifest(manifest, root=service.runtime.services.artifact_store.root)

        assert service.list_assets("assets") == [
            {
                "asset_id": "clip_SC_001_shot_001_take_001",
                "kind": "generated_clip",
                "scene_id": "SC_001",
                "shot_id": "shot_001",
                "take": 1,
                "active": True,
                "path": "07-generated-assets/scenes/SC_001/shot_001/take_001.mp4",
            }
        ]

    def test_inspect_artifact_validates_inputs_and_store(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="inspect", title="Inspect"))

        with pytest.raises(BackendOperationError, match="artifact_id is required"):
            service.inspect_artifact("", "constitution", project_id="inspect")

        service.runtime.services = None
        with pytest.raises(BackendOperationError, match="artifact store is not configured"):
            service.inspect_artifact("x", "constitution", project_id="inspect")

    def test_run_validation_refreshes_workspace_and_audits(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(
            ProjectCreateRequest(
                project_id="validate-me",
                title="Validate Me",
                idea="A courier crosses three fields to deliver one warning.",
            )
        )

        workspace = service.run_validation("validate-me")

        assert workspace.project_id == "validate-me"
        assert isinstance(workspace.blocking_issues, list)
        audit = service.get_audit_feed("validate-me", limit=20)
        assert any(event.action == "run_validation" for event in audit)

    def test_run_validation_requires_a_phase(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="no-phase", title="No Phase"))

        with pytest.raises(BackendOperationError, match="Submit an idea"):
            service.run_validation("no-phase")

    def test_set_runtime_mode_guards_injected_runtime(self, tmp_path: Path) -> None:
        service = _service(tmp_path)

        assert service.set_runtime_mode("mock") == "mock"
        with pytest.raises(BackendOperationError, match="Runtime mode is fixed"):
            service.set_runtime_mode("real")

    def test_preview_generation_prompts_resolves_from_shot_matrix(self, tmp_path: Path) -> None:
        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata
        from film_pipeline.schemas.matrix import MasterFilmMatrix, MasterFilmMatrixRow

        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="prompts", title="Prompts"))
        assert service.runtime.services is not None
        matrix = MasterFilmMatrix(
            project_id="prompts",
            rows=[
                MasterFilmMatrixRow(
                    shot_id="shot_0001",
                    act_id="act1",
                    sequence_id="seq_001",
                    scene_id="sc_001",
                    scene_intent_ref="s_001",
                    duration_seconds=8,
                    story_function="inciting image",
                    characters=["mara"],
                    environment="field",
                    camera_profile="wide_establishing",
                )
            ],
        )
        service.runtime.services.artifact_store.save(
            matrix,
            ArtifactMetadata(
                artifact_id="shot_matrix",
                artifact_type=ArtifactType.MASTER_FILM_MATRIX,
                project_id="prompts",
                phase=FilmPhase.SHOT_BIBLE,
                version=1,
                status=ArtifactStatus.CANDIDATE,
                created_by="test",
                created_at=datetime.now(UTC),
            ),
        )

        previews = service.preview_generation_prompts("prompts")

        assert len(previews) == 1
        preview = previews[0]
        assert preview["shot_id"] == "shot_0001"
        assert preview["scene_id"] == "sc_001"
        assert preview["provider"] == "mock-video-provider"
        assert preview["duration_seconds"] == 8
        assert "wide_establishing" in str(preview["prompt"]).lower()

    def test_preview_generation_prompts_empty_without_matrix(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(ProjectCreateRequest(project_id="bare", title="Bare"))

        assert service.preview_generation_prompts("bare") == []


class TestProviderHealthSeeding:
    def test_seed_mock_runtime_advertises_mock_providers(self) -> None:
        runtime = create_runtime("mock")
        runtime.seed_default_provider_health()

        health = runtime.get_all_health()
        assert set(health) == {"mock-image-provider", "mock-video-provider"}
        assert all(entry["status"] == "healthy" for entry in health.values())

    def test_seed_is_idempotent_and_preserves_existing(self) -> None:
        runtime = create_runtime("mock")
        runtime.set_provider_health("veo", "degraded", "quota")
        runtime.seed_default_provider_health()

        assert runtime.get_all_health() == {"veo": {"status": "degraded", "reason": "quota"}}

    def test_seed_real_runtime_lists_live_providers(self) -> None:
        runtime = create_runtime("real")
        runtime.seed_default_provider_health()

        health = runtime.get_all_health()
        assert set(health) == {"zai", "seedance-openrouter", "veo-fast", "gemini-imagen-4"}
        assert all(entry["status"] in {"healthy", "unconfigured"} for entry in health.values())


class TestTextOnlyGeneration:
    def test_plan_generation_text_only_creates_completed_requests(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(
            ProjectCreateRequest(
                project_id="text-only",
                title="Text Only Film",
                idea="A film delivered as text only.",
                generation_policy="text_only",
            )
        )
        state = service.runtime.projects["text-only"]
        state["current_phase"] = "generation"
        service.runtime.projects["text-only"] = state

        workspace = service.plan_generation("text-only")
        assert workspace.completed == 1
        assert workspace.next_step == "approve_phase"
        assert workspace.estimated_cost_usd == 0.0

        state = service.runtime.projects["text-only"]
        assert state.get("_text_only_generation_completed") is True
        requests = state.get("generation_requests", [])
        assert len(requests) >= 1
        assert all(str(r.get("status", "")).lower() == "completed" for r in requests)

    def test_approve_and_start_text_only_are_no_ops(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        service.create_project(
            ProjectCreateRequest(
                project_id="text-only-noop",
                title="Text Only Noop",
                idea="A text-only film.",
                generation_policy="text_only",
            )
        )
        state = service.runtime.projects["text-only-noop"]
        state["current_phase"] = "generation"
        service.runtime.projects["text-only-noop"] = state
        service.plan_generation("text-only-noop")

        workspace = service.approve_generation_spend("text-only-noop")
        assert workspace.completed == 1
        workspace = service.start_generation("text-only-noop")
        assert workspace.completed == 1
        workspace = service.poll_generation("text-only-noop")
        assert workspace.completed == 1


class TestCheckpointOperations:
    def test_checkpoint_rollback_persists_bookkeeping(self, tmp_path: Path) -> None:
        service = _service(tmp_path)
        project_id = "checkpoint-service"
        service.runtime.create_project(project_id, "Checkpoint Service")
        checkpoint = service.runtime.create_checkpoint(
            project_id=project_id,
            phase="intake",
            reason="service rollback target",
        )

        result = service.rollback_to_checkpoint(checkpoint, project_id)

        assert result.rollback_target == checkpoint.checkpoint_id
        assert result.phase == "intake"
        assert result.reason == "service rollback target"
        assert result.invalidation_report_ref.startswith("artifact:")
        assert result.rollback_record_ref.startswith("artifact:")
        assert service.runtime.services is not None
        saved_types = {
            artifact.artifact_type
            for artifact in service.runtime.services.artifact_store.list_artifacts(project_id)
        }
        assert ArtifactType.INVALIDATION_REPORT in saved_types
        assert ArtifactType.ROLLBACK_RECORD in saved_types
