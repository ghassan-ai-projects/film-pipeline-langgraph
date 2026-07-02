from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from film_pipeline.app.services.errors import ProjectNotFoundError
from film_pipeline.app.services.models import (
    ArtifactDetail,
    AuditEvent,
    DashboardSummary,
    GenerationWorkspace,
    MutationResult,
    OperatorComment,
    OperatorCommentRequest,
    ProjectCreateRequest,
    ProjectListItem,
    ReviewWorkspace,
    ValidationWorkspace,
)


@dataclass
class RecordingGateway:
    """Gateway fake with enough state to exercise the cockpit."""

    created_request: ProjectCreateRequest | None = None
    approved_count: int = 0
    revision_notes: list[str] | None = None
    comments: list[OperatorComment] | None = None
    active_project_id: str = "field-message"
    extra_projects: list[ProjectListItem] = field(default_factory=list)
    validation_runs: int = 0
    runtime_mode: str = "mock"
    submitted_ideas: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.revision_notes is None:
            self.revision_notes = []
        if self.comments is None:
            self.comments = []

    def list_projects(self) -> list[ProjectListItem]:
        return [
            ProjectListItem(
                project_id="field-message",
                title="The Field Message",
                slug="field-message",
                current_phase="script",
                status="awaiting_review",
                has_blockers=True,
                awaiting_review=True,
            ),
            *self.extra_projects,
        ]

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        self.created_request = request
        self.active_project_id = request.project_id
        return MutationResult(
            ok=True,
            project_id=request.project_id,
            current_phase="intake" if request.idea else "",
            message="Project created.",
        )

    def set_active_project(self, project_id: str) -> DashboardSummary:
        self.active_project_id = project_id
        return self.get_dashboard(project_id)

    def set_runtime_mode(self, mode: str) -> str:
        self.runtime_mode = mode
        return mode

    def submit_idea(self, project_id: str, idea: str) -> MutationResult:
        self.active_project_id = project_id
        self.submitted_ideas.append(idea)
        return MutationResult(ok=True, project_id=project_id, current_phase="intake")

    def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
        if project_id is None and not self.active_project_id:
            raise ProjectNotFoundError("No active project.")
        return DashboardSummary(
            project_id=project_id or self.active_project_id,
            title="The Field Message",
            slug="field-message",
            current_phase="script",
            runtime_mode="mock",
            workflow_mode="hybrid",
            status="awaiting_review",
            next_action="present_review_package",
            route_reason="script requires operator review",
            eligible_actions=["approve_phase", "request_revision"],
            blocked_actions=[{"action": "generation", "reason": "approval required"}],
            issue_count=1,
            artifact_count=2,
            checkpoint_count=1,
            has_blockers=True,
        )

    def get_review_workspace(self, project_id: str | None = None) -> ReviewWorkspace:
        return ReviewWorkspace(
            project_id=project_id or self.active_project_id,
            phase="script",
            recommendation="Review the script outputs.",
            candidate_artifacts=self.list_artifacts(project_id, phase="script"),
            open_issues=["Dialogue voice drift in SC_004"],
            available_actions=["approve_phase", "request_revision"],
        )

    def get_validation_workspace(self, project_id: str | None = None) -> ValidationWorkspace:
        return ValidationWorkspace(
            project_id=project_id or self.active_project_id,
            phase="script",
            source="stored_state",
            reports=[{"validator_id": "script-structure", "score": 74}],
            blocking_issues=[
                {
                    "severity": "blocking",
                    "validator_id": "dialogue-voice",
                    "scene_id": "SC_004",
                    "target": "script",
                    "message": "Dialogue voice drift in scene 4.",
                }
            ],
            non_blocking_issues=[
                {
                    "severity": "warning",
                    "validator_id": "payoff",
                    "scene_id": "SC_007",
                    "message": "Payoff is unclear.",
                }
            ],
        )

    def run_validation(self, project_id: str | None = None) -> ValidationWorkspace:
        self.validation_runs += 1
        return self.get_validation_workspace(project_id)

    def get_generation_workspace(self, project_id: str | None = None) -> GenerationWorkspace:
        return GenerationWorkspace(
            project_id=project_id or self.active_project_id,
            phase="generation",
            provider="mock-video-provider",
            model="mock-fast",
            estimated_cost_usd=0.0,
            rows=[
                {
                    "request_id": "req-1",
                    "shot_id": "shot_SC_004_001",
                    "scene_id": "SC_004",
                    "status": "planned",
                    "provider": "mock-video-provider",
                    "model": "mock-fast",
                    "estimated_cost_usd": 0.0,
                }
            ],
            planned=1,
            next_step="approve_spend",
        )

    def plan_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        workspace = self.get_generation_workspace(project_id)
        return GenerationWorkspace(
            project_id=workspace.project_id,
            phase=workspace.phase,
            provider=workspace.provider,
            model=workspace.model,
            estimated_cost_usd=workspace.estimated_cost_usd,
            rows=workspace.rows,
            planned=1,
            next_step="approve_spend",
        )

    def approve_generation_spend(
        self, project_id: str | None = None, max_cost_usd: float = -1.0
    ) -> GenerationWorkspace:
        workspace = self.get_generation_workspace(project_id)
        return GenerationWorkspace(
            project_id=workspace.project_id,
            phase=workspace.phase,
            provider=workspace.provider,
            model=workspace.model,
            estimated_cost_usd=workspace.estimated_cost_usd,
            rows=[{**row, "status": "approved"} for row in workspace.rows],
            planned=1,
            next_step="start",
        )

    def start_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        workspace = self.get_generation_workspace(project_id)
        return GenerationWorkspace(
            project_id=workspace.project_id,
            phase=workspace.phase,
            provider=workspace.provider,
            model=workspace.model,
            estimated_cost_usd=workspace.estimated_cost_usd,
            rows=[{**row, "status": "submitted"} for row in workspace.rows],
            planned=1,
            submitted=1,
            next_step="poll",
        )

    def poll_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        workspace = self.get_generation_workspace(project_id)
        return GenerationWorkspace(
            project_id=workspace.project_id,
            phase=workspace.phase,
            provider=workspace.provider,
            model=workspace.model,
            estimated_cost_usd=workspace.estimated_cost_usd,
            rows=[{**row, "status": "delivered"} for row in workspace.rows],
            planned=1,
            completed=1,
            next_step="approve_phase",
        )

    def approve_phase(self, project_id: str | None = None) -> MutationResult:
        self.approved_count += 1
        return MutationResult(
            ok=True,
            project_id=project_id or self.active_project_id,
            current_phase="visual_dev",
            message="Phase approved.",
        )

    def request_revision(self, note: str, project_id: str | None = None) -> MutationResult:
        assert self.revision_notes is not None
        self.revision_notes.append(note)
        return MutationResult(
            ok=True,
            project_id=project_id or self.active_project_id,
            current_phase="script",
            message="Revision requested.",
        )

    def add_operator_comment(
        self,
        request: OperatorCommentRequest,
        project_id: str | None = None,
    ) -> OperatorComment:
        assert self.comments is not None
        comment = OperatorComment(
            comment_id=f"comment:{len(self.comments) + 1}",
            project_id=project_id or self.active_project_id,
            target_type=request.target_type,
            target_id=request.target_id,
            body=request.body,
            phase=request.phase,
            source=request.source,
            created_at="2026-06-24T10:02:00",
        )
        self.comments.append(comment)
        return comment

    def list_operator_comments(
        self,
        project_id: str | None = None,
        *,
        include_resolved: bool = False,
    ) -> list[OperatorComment]:
        assert self.comments is not None
        return list(self.comments)

    def list_artifacts(
        self, project_id: str | None = None, phase: str | None = None
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = [
            {
                "artifact_id": "script",
                "artifact_type": "script",
                "phase": "script",
                "version": 4,
                "status": "candidate",
                "scene_ids": ["SC_004"],
                "scene_count": 1,
            },
            {
                "artifact_id": "scene_matrix",
                "artifact_type": "matrix",
                "phase": "script",
                "version": 2,
                "status": "candidate",
                "scene_ids": ["SC_004"],
                "scene_count": 1,
            },
        ]
        return [row for row in rows if phase in {None, row["phase"]}]

    def list_assets(self, project_id: str | None = None) -> list[dict[str, object]]:
        return [
            {
                "asset_id": "clip_SC_004_shot_001_take_001",
                "kind": "generated_clip",
                "scene_id": "SC_004",
                "shot_id": "shot_SC_004_001",
                "take": 1,
                "active": True,
                "path": "07-generated-assets/scenes/SC_004/shot_SC_004_001/take_001.mp4",
            },
            {
                "asset_id": "ref_station_platform",
                "kind": "reference_sheet",
                "scene_id": "SC_004",
                "shot_id": "",
                "take": 1,
                "active": True,
                "path": "references/environments/station/ref_station_platform.png",
            },
        ]

    def inspect_artifact(
        self,
        artifact_id: str,
        phase: str,
        version: int = 1,
        project_id: str | None = None,
    ) -> ArtifactDetail:
        body: dict[str, Any]
        if artifact_id == "script":
            body = {
                "artifact_id": "script",
                "artifact_type": "script",
                "scenes": [
                    {
                        "scene_id": "SC_004",
                        "scene_heading": "INT. STATION - DAWN",
                        "action_lines": ["Mara waits beside the locked platform."],
                        "dialogue": [
                            {
                                "character_id": "MARA",
                                "direction": "quietly",
                                "line": "The message arrived before the train.",
                            }
                        ],
                    }
                ],
            }
        elif artifact_id == "scene_matrix":
            body = {
                "artifact_id": "scene_matrix",
                "artifact_type": "matrix",
                "rows": [
                    {
                        "shot_id": "shot_SC_004_001",
                        "scene_id": "SC_004",
                        "story_function": "Mara receives the impossible warning.",
                        "environment": "abandoned station platform",
                        "camera_profile": "slow push-in",
                        "camera_movement": "dolly forward from wide to close",
                        "asset_refs": ["ref_station_platform", "prop_warning_note"],
                        "reference_refs": ["style_noir_dawn"],
                    }
                ],
            }
        else:
            body = {"artifact_id": artifact_id, "scenes": [{"scene_id": "SC_004"}]}
        return ArtifactDetail(
            artifact_id=artifact_id,
            artifact_type=artifact_id,
            phase=phase,
            version=version,
            status="candidate",
            body=body,
        )

    def list_checkpoints(self, project_id: str | None = None) -> list[dict[str, str]]:
        return [
            {
                "checkpoint_id": "script-approved-v3",
                "project_id": project_id or self.active_project_id,
                "phase": "script",
                "reason": "approved baseline",
                "created_at": "2026-06-24T10:00:00",
            }
        ]

    def list_provider_status(self) -> list[dict[str, object]]:
        return [
            {"provider_id": "seedance", "status": "healthy", "reason": ""},
            {"provider_id": "imagen", "status": "degraded", "reason": "quota"},
        ]

    def get_audit_feed(self, project_id: str | None = None, limit: int = 20) -> list[AuditEvent]:
        return [
            AuditEvent(
                timestamp="2026-06-24T10:01:00",
                actor="orchestrator",
                action="route",
                target="script",
                summary="routed to review",
            )
        ]


class NoApprovalGateway(RecordingGateway):
    """Gateway state where approval is not currently eligible."""

    def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
        dashboard = super().get_dashboard(project_id)
        return DashboardSummary(
            project_id=dashboard.project_id,
            title=dashboard.title,
            slug=dashboard.slug,
            current_phase=dashboard.current_phase,
            runtime_mode=dashboard.runtime_mode,
            workflow_mode=dashboard.workflow_mode,
            status="in_progress",
            next_action="continue_work",
            route_reason="approval not ready",
            eligible_actions=[],
            blocked_actions=[],
            issue_count=dashboard.issue_count,
            artifact_count=dashboard.artifact_count,
            checkpoint_count=dashboard.checkpoint_count,
            has_blockers=False,
        )


class BrokenArtifactGateway(RecordingGateway):
    """Gateway fake where one artifact cannot be inspected."""

    def list_artifacts(
        self, project_id: str | None = None, phase: str | None = None
    ) -> list[dict[str, object]]:
        rows = super().list_artifacts(project_id, phase)
        for row in rows:
            row.pop("scene_ids", None)
            row.pop("scene_count", None)
        return rows

    def inspect_artifact(
        self,
        artifact_id: str,
        phase: str,
        version: int = 1,
        project_id: str | None = None,
    ) -> ArtifactDetail:
        if artifact_id == "scene_matrix":
            raise ProjectNotFoundError("artifact missing")
        return super().inspect_artifact(artifact_id, phase, version, project_id)


class NoAssetGateway(RecordingGateway):
    """Gateway fake without an asset manifest."""

    def list_assets(self, project_id: str | None = None) -> list[dict[str, object]]:
        return []


class FailingGateway(RecordingGateway):
    """Gateway whose mutations raise to exercise error branches."""

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        raise ProjectNotFoundError("create boom")

    def run_validation(self, project_id: str | None = None) -> ValidationWorkspace:
        raise ProjectNotFoundError("validation boom")

    def submit_idea(self, project_id: str, idea: str) -> MutationResult:
        raise ProjectNotFoundError("idea boom")
