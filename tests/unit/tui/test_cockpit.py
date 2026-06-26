"""Tests for the Textual film cockpit."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Input, Static, TabbedContent

from film_pipeline.app.services.errors import ProjectNotFoundError
from film_pipeline.app.services.models import (
    ArtifactDetail,
    AuditEvent,
    DashboardSummary,
    MutationResult,
    OperatorComment,
    OperatorCommentRequest,
    ProjectCreateRequest,
    ProjectListItem,
    ReviewWorkspace,
    ValidationWorkspace,
)
from film_pipeline.tui.app import FilmCockpitApp
from film_pipeline.tui.view_models import (
    build_artifact_reader,
    build_asset_action_rows,
    build_command_help_rows,
    build_command_options,
    build_command_suggestions,
    build_command_validation,
    build_comment_thread_rows,
    build_dashboard_action_rows,
    build_dashboard_kpi_rows,
    build_graph_rows,
    build_matrix_impact,
    build_matrix_pivot_rows,
    build_matrix_rows,
    build_phase_detail,
    build_reader_index_rows,
    build_reader_link_rows,
    build_review_checklist_rows,
    build_review_issue_rows,
    build_scene_rows,
    build_validation_fix_suggestions,
    build_validation_groups,
    complete_command_prefix,
    filter_command_suggestions,
    filter_matrix_rows,
    format_fix_draft,
    format_selection_detail,
    format_targeted_revision_note,
    selection_from_row,
    summarize_attention,
    validation_issue_rows,
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

    def submit_idea(self, project_id: str, idea: str) -> MutationResult:
        self.active_project_id = project_id
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
            },
            {
                "artifact_id": "scene_matrix",
                "artifact_type": "matrix",
                "phase": "script",
                "version": 2,
                "status": "candidate",
            },
        ]
        return [row for row in rows if phase in {None, row["phase"]}]

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


def test_graph_rows_mark_current_phase() -> None:
    dashboard = RecordingGateway().get_dashboard("field-message")

    rows = build_graph_rows(dashboard)

    current = [row for row in rows if row["status"] == "current"]
    assert current == [
        {
            "step": 4,
            "phase": "script",
            "status": "current",
            "next_action": "present_review_package",
        }
    ]


def test_phase_detail_summarizes_current_graph_position() -> None:
    gateway = RecordingGateway()
    dashboard = gateway.get_dashboard("field-message")
    validation = gateway.get_validation_workspace("field-message")

    detail = build_phase_detail(
        "script",
        dashboard=dashboard,
        artifacts=gateway.list_artifacts("field-message"),
        validation=validation,
    )

    assert detail.phase == "script"
    assert detail.status == "current"
    assert len(detail.artifacts) == 2
    assert "Dialogue voice drift in scene 4." in detail.blockers
    assert "approve" in detail.suggested_commands
    assert "artifact script" in detail.suggested_commands


def test_command_suggestions_include_live_navigation_and_fix_commands() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    artifacts = gateway.list_artifacts("field-message")
    matrix_rows = build_matrix_rows(artifacts, validation)

    suggestions = build_command_suggestions(
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        matrix_rows=matrix_rows,
    )

    commands = [str(row["command"]) for row in suggestions]
    assert "open guide" in commands
    assert "phase script" in commands
    assert "project field-message" in commands
    assert "projects production" in commands
    assert "projects test" in commands
    assert "approve" in commands
    assert "confirm approve" in commands
    assert "fix SC_004" in commands
    assert "artifact script" in commands
    assert "scene SC_007" in commands


def test_dashboard_kpis_and_actions_surface_operator_priorities() -> None:
    gateway = RecordingGateway()
    dashboard = gateway.get_dashboard("field-message")
    validation = gateway.get_validation_workspace("field-message")
    comment = gateway.add_operator_comment(
        OperatorCommentRequest(
            target_type="scene",
            target_id="SC_004",
            phase="script",
            body="Keep the scene quiet.",
        ),
        "field-message",
    )

    kpis = build_dashboard_kpi_rows(
        dashboard,
        validation,
        gateway.list_provider_status(),
        [comment],
    )
    actions = build_dashboard_action_rows(
        dashboard,
        gateway.get_review_workspace("field-message"),
        validation,
    )

    assert kpis[0]["metric"] == "phase"
    assert kpis[1]["state"] == "blocked"
    assert kpis[3]["state"] == "degraded"
    assert kpis[4]["value"] == 1
    assert actions[0]["command"] == "next"
    assert any(row["command"] == "fix SC_004" for row in actions)
    assert any(row["command"] == "approve" for row in actions)


def test_dashboard_rows_surface_stalled_phase() -> None:
    dashboard = DashboardSummary(
        project_id="field-message",
        title="The Field Message",
        slug="field-message",
        current_phase="shot_bible",
        runtime_mode="mock",
        workflow_mode="hybrid",
        status="stalled",
        next_action="wait_for_human",
        route_reason="repair stalled",
        stalled_phase="shot_bible",
        has_blockers=True,
        issue_count=1,
    )

    actions = build_dashboard_action_rows(dashboard, None, None)
    suggestions = build_command_suggestions(
        dashboard=dashboard,
        validation=None,
        artifacts=[],
        matrix_rows=[],
    )
    graph = build_graph_rows(dashboard)
    attention = summarize_attention(dashboard, None, [])

    assert any(row["action"] == "escalate stalled phase" for row in actions)
    assert any(row["scope"] == "escalation" for row in suggestions)
    assert any(row["phase"] == "shot_bible" and row["status"] == "stalled" for row in graph)
    assert any("STALLED: shot_bible" in line for line in attention)


def test_matrix_rows_merge_artifacts_and_validation_issues() -> None:
    gateway = RecordingGateway()
    artifacts = gateway.list_artifacts("field-message")
    validation = gateway.get_validation_workspace("field-message")

    rows = build_matrix_rows(artifacts, validation)

    script = next(row for row in rows if row["target"] == "script")
    scene_issue = next(row for row in rows if row["target"] == "SC_007")
    assert script["validation"] == "blocking: Dialogue voice drift in scene 4."
    assert script["action"] == "review issues"
    assert scene_issue["kind"] == "validation_issue"
    assert scene_issue["action"] == "request fix"


def test_matrix_pivot_rows_group_by_status_phase_and_validation() -> None:
    gateway = RecordingGateway()
    rows = build_matrix_rows(
        gateway.list_artifacts("field-message"),
        gateway.get_validation_workspace("field-message"),
    )

    by_status = build_matrix_pivot_rows(rows, "status")
    by_phase = build_matrix_pivot_rows(rows, "phase")
    by_validation = build_matrix_pivot_rows(rows, "validation")

    assert any(row["value"] == "candidate" and row["rows"] == 2 for row in by_status)
    assert by_phase[0]["value"] == "script"
    assert any(row["value"] == "blocking" for row in by_validation)
    assert any(row["command"] == "matrix status:candidate" for row in by_status)


def test_matrix_filter_supports_operator_queries() -> None:
    gateway = RecordingGateway()
    rows = build_matrix_rows(
        gateway.list_artifacts("field-message"),
        gateway.get_validation_workspace("field-message"),
    )

    blocking = filter_matrix_rows(rows, "blocking")
    warning_scene = filter_matrix_rows(rows, "scene:SC_007 warning")

    assert [row["target"] for row in blocking] == ["script"]
    assert [row["target"] for row in warning_scene] == ["SC_007"]


def test_matrix_impact_links_comments_and_validation() -> None:
    gateway = RecordingGateway()
    comment = gateway.add_operator_comment(
        OperatorCommentRequest(
            target_type="scene",
            target_id="SC_007",
            phase="script",
            body="Payoff needs to be more visual.",
        ),
        "field-message",
    )
    rows = build_matrix_rows(
        gateway.list_artifacts("field-message"),
        gateway.get_validation_workspace("field-message"),
    )
    row = next(row for row in rows if row["target"] == "SC_007")

    impact = build_matrix_impact(
        row,
        comments=[comment],
        validation=gateway.get_validation_workspace("field-message"),
    )

    assert impact.target_id == "SC_007"
    assert impact.linked_comments == [comment]
    assert impact.linked_validation[0]["message"] == "Payoff is unclear."
    assert "request targeted revision" in impact.suggested_actions


def test_scene_rows_extract_scene_targets_from_matrix() -> None:
    gateway = RecordingGateway()
    rows = build_matrix_rows(
        gateway.list_artifacts("field-message"),
        gateway.get_validation_workspace("field-message"),
    )

    scenes = build_scene_rows(rows)

    assert scenes == [
        {
            "scene": "SC_007",
            "phase": "script",
            "status": "warning",
            "validation": "Payoff is unclear.",
            "action": "request fix",
        }
    ]


def test_selection_and_targeted_revision_note_preserve_context() -> None:
    selection = selection_from_row(
        "scene_table",
        {
            "scene": "SC_007",
            "phase": "script",
            "status": "warning",
            "validation": "Payoff is unclear.",
        },
    )

    note = format_targeted_revision_note(selection, "Make the payoff emotionally clearer.")

    assert selection.target_type == "scene"
    assert selection.target_id == "SC_007"
    assert note == (
        "[target_type=scene target_id=SC_007 phase=script] Make the payoff emotionally clearer."
    )


def test_artifact_reader_builds_outline_body_and_links() -> None:
    gateway = RecordingGateway()
    comment = gateway.add_operator_comment(
        OperatorCommentRequest(
            target_type="scene",
            target_id="SC_004",
            phase="script",
            body="Make the station feel colder.",
        ),
        "field-message",
    )
    artifact = gateway.inspect_artifact("script", "script", 4, "field-message")

    reader = build_artifact_reader(
        artifact,
        comments=[comment],
        validation=gateway.get_validation_workspace("field-message"),
        scene_id="SC_004",
    )

    assert reader.title == "INT. STATION - DAWN"
    assert reader.metadata["scene_id"] == "SC_004"
    assert "Mara waits beside the locked platform." in reader.body
    assert "MARA" in reader.body
    assert reader.linked_comments == [comment]
    assert reader.linked_validation[0]["message"] == "Dialogue voice drift in scene 4."


def test_reader_index_and_link_rows_make_artifact_navigable() -> None:
    gateway = RecordingGateway()
    comment = gateway.add_operator_comment(
        OperatorCommentRequest(
            target_type="scene",
            target_id="SC_004",
            phase="script",
            body="Make the station feel colder.",
        ),
        "field-message",
    )
    artifact = gateway.inspect_artifact("script", "script", 4, "field-message")
    reader = build_artifact_reader(
        artifact,
        comments=[comment],
        validation=gateway.get_validation_workspace("field-message"),
        scene_id="SC_004",
    )

    index_rows = build_reader_index_rows(artifact)
    link_rows = build_reader_link_rows(reader)

    assert index_rows == [
        {
            "order": 1,
            "target_id": "SC_004",
            "target_type": "scene",
            "heading": "INT. STATION - DAWN",
            "command": "scene SC_004",
        }
    ]
    assert link_rows[0]["kind"] == "validation"
    assert link_rows[0]["command"] == "fix SC_004"
    assert link_rows[1]["kind"] == "comment"
    assert link_rows[1]["command"] == "thread SC_004"


def test_asset_action_rows_make_artifacts_actionable() -> None:
    rows = build_asset_action_rows(RecordingGateway().list_artifacts("field-message"))

    script_actions = [row for row in rows if row["artifact_id"] == "script"]
    assert [row["action"] for row in script_actions] == ["review", "change", "extend"]
    assert script_actions[0]["command"] == "asset review script"
    assert script_actions[1]["command"] == "asset change script | <note>"
    assert script_actions[2]["command"] == "asset extend script | <note>"


def test_artifact_reader_renders_text_treatment_scene_list_and_compact_bodies() -> None:
    text_artifact = ArtifactDetail(
        artifact_id="logline",
        artifact_type="text",
        phase="intake",
        version=1,
        status="candidate",
        body={"text": "A courier hears tomorrow's warning today.", "created_by": "agent"},
    )
    treatment_artifact = ArtifactDetail(
        artifact_id="treatment",
        artifact_type="treatment",
        phase="development",
        version=2,
        status="candidate",
        body={
            "treatment": {"text": "Act one opens at the abandoned platform."},
            "validation_refs": ["validation:1"],
        },
    )
    scene_list_artifact = ArtifactDetail(
        artifact_id="scene_list",
        artifact_type="scene_list",
        phase="script",
        version=1,
        status="candidate",
        body={
            "scene_list": {
                "scenes": [
                    {"scene_id": "SC_001", "dramatic_function": "Arrival"},
                    {"dramatic_function": "Missing id fallback"},
                ]
            },
            "approval_ref": "approval:1",
        },
    )
    compact_artifact = ArtifactDetail(
        artifact_id="metadata",
        artifact_type="metadata",
        phase="delivery",
        version=1,
        status="candidate",
        body={
            "title": "Field Message",
            "shots": [1, 2],
            "owner": {"agent": "delivery"},
            "empty": None,
        },
    )

    text_reader = build_artifact_reader(text_artifact, comments=[], validation=None)
    treatment_reader = build_artifact_reader(treatment_artifact, comments=[], validation=None)
    scene_reader = build_artifact_reader(scene_list_artifact, comments=[], validation=None)
    compact_reader = build_artifact_reader(compact_artifact, comments=[], validation=None)

    assert text_reader.body == "A courier hears tomorrow's warning today."
    assert text_reader.metadata["created_by"] == "agent"
    assert treatment_reader.body == "Act one opens at the abandoned platform."
    assert treatment_reader.metadata["validation_refs"] == ["validation:1"]
    assert scene_reader.outline == ["SC_001: Arrival", "?: Missing id fallback"]
    assert build_reader_index_rows(scene_list_artifact)[0]["command"] == "scene SC_001"
    assert compact_reader.body.splitlines() == [
        "title: Field Message",
        "shots: 2 item(s)",
        "owner: 1 field(s)",
        "empty: None",
    ]


def test_command_options_collect_selectable_ids() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")

    options = build_command_options(
        projects=gateway.list_projects(),
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=gateway.list_artifacts("field-message"),
        providers=gateway.list_provider_status(),
    )

    assert options.project_ids == ["field-message"]
    assert options.project_kinds == ["production", "test", "all"]
    assert "script" in options.phases
    assert options.artifact_ids == ["scene_matrix", "script"]
    assert options.scene_ids == ["SC_004", "SC_007"]
    assert options.validator_ids == ["dialogue-voice", "payoff", "script-structure"]
    assert options.provider_ids == ["imagen", "seedance"]


def test_command_help_rows_include_live_argument_values() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    options = build_command_options(
        projects=gateway.list_projects(),
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=gateway.list_artifacts("field-message"),
        providers=gateway.list_provider_status(),
    )

    help_rows = build_command_help_rows(options)

    by_command = {str(row["command"]): row for row in help_rows}
    assert "field-message" in str(by_command["project <project_id>"]["values"])
    assert "production" in str(by_command["projects <production|test|all>"]["values"])
    assert "script" in str(by_command["artifact <artifact_id>"]["values"])
    assert "script" in str(by_command["asset review <artifact_id>"]["values"])
    assert "script" in str(by_command["asset change <artifact_id> | <note>"]["values"])
    assert "SC_004" in str(by_command["scene <scene_id>"]["values"])
    assert "dialogue-voice" in str(by_command["validator <validator_id>"]["values"])
    assert by_command["create <project_id> | <title> | <idea>"]["purpose"]


def test_command_validation_accepts_known_values_and_rejects_unknown_values() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    artifacts = gateway.list_artifacts("field-message")
    matrix_rows = build_matrix_rows(artifacts, validation)
    suggestions = build_command_suggestions(
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        matrix_rows=matrix_rows,
    )
    options = build_command_options(
        projects=gateway.list_projects(),
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        providers=gateway.list_provider_status(),
    )

    assert build_command_validation("artifact script", options, suggestions).status == "ready"
    assert build_command_validation("asset review script", options, suggestions).status == "ready"
    assert (
        build_command_validation(
            "asset change script | Sharpen the visual beat.", options, suggestions
        ).status
        == "ready"
    )
    assert (
        build_command_validation(
            "asset extend script | Add one image beat.", options, suggestions
        ).status
        == "ready"
    )
    assert build_command_validation("project field-message", options, suggestions).status == "ready"
    assert build_command_validation("projects test", options, suggestions).status == "ready"
    assert build_command_validation("scene SC_004", options, suggestions).status == "ready"
    assert (
        build_command_validation("create film | Film | Idea", options, suggestions).status
        == "ready"
    )
    unknown = build_command_validation("artifact missing", options, suggestions)
    unknown_asset = build_command_validation("asset review missing", options, suggestions)
    unknown_project = build_command_validation("project missing", options, suggestions)
    bad_pivot = build_command_validation("matrix pivot mood", options, suggestions)
    partial = build_command_validation("artifact sc", options, suggestions)

    assert unknown.status == "unknown"
    assert "Unknown artifact" in unknown.message
    assert unknown_asset.status == "unknown"
    assert "Unknown asset review" in unknown_asset.message
    assert unknown_project.status == "unknown"
    assert "Unknown project" in unknown_project.message
    assert bad_pivot.status == "unknown"
    assert "Unknown matrix pivot" in bad_pivot.message
    assert partial.status == "incomplete"
    assert partial.completion == "artifact scene_matrix"


def test_command_validation_guides_incomplete_and_pipe_commands() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    artifacts = gateway.list_artifacts("field-message")
    matrix_rows = build_matrix_rows(artifacts, validation)
    suggestions = build_command_suggestions(
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        matrix_rows=matrix_rows,
    )
    options = build_command_options(
        projects=gateway.list_projects(),
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        providers=gateway.list_provider_status(),
    )

    assert build_command_validation("", options, suggestions).completion == "open graph"
    assert build_command_validation("create", options, suggestions).status == "incomplete"
    assert build_command_validation("asset", options, suggestions).status == "incomplete"
    assert (
        build_command_validation("asset change script | <note>", options, suggestions).status
        == "incomplete"
    )
    assert (
        build_command_validation("create <project_id> | Film | Idea", options, suggestions).status
        == "incomplete"
    )
    assert build_command_validation("phase", options, suggestions).completion == "phase script"
    assert build_command_validation("validator", options, suggestions).completion.startswith(
        "validator "
    )
    assert build_command_validation("matrix", options, suggestions).status == "ready"
    assert build_command_validation("matr", options, suggestions).completion == "matrix"
    assert (
        build_command_validation("matrix pivot", options, suggestions).completion
        == "matrix pivot status"
    )
    assert build_command_validation("matrix blocking", options, suggestions).status == "ready"
    assert build_command_validation("comment", options, suggestions).status == "incomplete"
    assert (
        build_command_validation("comment SC_004 | keep this quiet", options, suggestions).status
        == "ready"
    )
    assert (
        build_command_validation("draft SC_004 | <note>", options, suggestions).status
        == "incomplete"
    )
    assert build_command_validation("review issue", options, suggestions).status == "incomplete"
    assert build_command_validation("review issue SC_004", options, suggestions).status == "ready"
    assert build_command_validation("appr", options, suggestions).completion == "approve"
    assert build_command_validation("nonsense", options, suggestions).status == "unknown"


def test_command_suggestions_filter_and_complete_prefixes() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    artifacts = gateway.list_artifacts("field-message")
    suggestions = build_command_suggestions(
        dashboard=gateway.get_dashboard("field-message"),
        validation=validation,
        artifacts=artifacts,
        matrix_rows=build_matrix_rows(artifacts, validation),
    )

    filtered = filter_command_suggestions(suggestions, "fix")

    assert [row["command"] for row in filtered] == ["fix SC_004", "fix SC_007"]
    assert complete_command_prefix("art", suggestions) == "artifact script"


def test_selection_from_row_covers_tui_table_sources() -> None:
    rows: dict[str, dict[str, object]] = {
        "asset_table": {"artifact_id": "script", "phase": "script"},
        "asset_action_table": {"artifact_id": "script", "action": "review", "phase": "script"},
        "dashboard_kpi_table": {"metric": "blockers"},
        "dashboard_action_table": {"action": "approve"},
        "project_table": {"project": "field-message", "kind": "production"},
        "guide_table": {"step": 3, "goal": "Inspect assets"},
        "review_checklist_table": {"check": "read script"},
        "review_issue_table": {"target_type": "scene", "target_id": "SC_004"},
        "comment_thread_table": {"target_type": "scene", "target_id": "SC_004"},
        "validation_table": {"target": "SC_004", "phase": "script"},
        "validation_group_table": {"validator_id": "dialogue-voice"},
        "validation_fix_table": {"target_type": "scene", "target_id": "SC_004"},
        "matrix_table": {"kind": "artifact", "target": "script", "phase": "script"},
        "matrix_pivot_table": {"value": "blocking"},
        "graph_table": {"phase": "script"},
        "graph_artifact_table": {"artifact_id": "script", "phase": "script"},
        "command_suggestion_table": {"command": "fix SC_004"},
        "reader_index_table": {"target_type": "scene", "target_id": "SC_004"},
        "reader_link_table": {"kind": "validation", "target_id": "SC_004"},
        "provider_table": {"provider_id": "imagen"},
        "checkpoint_table": {"checkpoint_id": "checkpoint:1", "phase": "script"},
        "unknown_table": {"first": "fallback"},
    }

    selections = {source: selection_from_row(source, row) for source, row in rows.items()}

    assert selections["asset_table"].target_type == "artifact"
    assert selections["asset_action_table"].target_type == "asset_action"
    assert selections["dashboard_kpi_table"].target_id == "blockers"
    assert selections["dashboard_action_table"].target_type == "dashboard_action"
    assert selections["project_table"].target_type == "project"
    assert selections["guide_table"].target_type == "guide_step"
    assert selections["review_checklist_table"].target_id == "read script"
    assert selections["review_issue_table"].target_type == "scene"
    assert selections["comment_thread_table"].target_id == "SC_004"
    assert selections["validation_table"].target_type == "validation_issue"
    assert selections["validation_group_table"].target_type == "validator"
    assert selections["validation_fix_table"].target_type == "scene"
    assert selections["matrix_table"].target_type == "artifact"
    assert selections["matrix_pivot_table"].target_type == "matrix_pivot"
    assert selections["graph_table"].target_type == "graph_phase"
    assert selections["graph_artifact_table"].target_id == "script"
    assert selections["command_suggestion_table"].target_type == "command"
    assert selections["reader_index_table"].target_type == "scene"
    assert selections["reader_link_table"].target_type == "validation"
    assert selections["provider_table"].target_id == "imagen"
    assert selections["checkpoint_table"].phase == "script"
    assert selections["unknown_table"].target_id == "fallback"
    assert "comment script | <what you want changed>" in format_selection_detail(
        selections["asset_table"]
    )
    assert format_targeted_revision_note(None, "  no selection  ") == "no selection"


def test_attention_summary_surfaces_review_validation_and_provider_risk() -> None:
    gateway = RecordingGateway()

    lines = summarize_attention(
        gateway.get_dashboard("field-message"),
        gateway.get_validation_workspace("field-message"),
        gateway.list_provider_status(),
    )

    assert any(line.startswith("BLOCKED") for line in lines)
    assert any(line.startswith("REVIEW") for line in lines)
    assert any(line.startswith("VALIDATION") for line in lines)
    assert any(line.startswith("PROVIDERS") for line in lines)


def test_validation_groups_and_fixes_turn_issues_into_actions() -> None:
    validation = RecordingGateway().get_validation_workspace("field-message")

    groups = build_validation_groups(validation)
    suggestions = build_validation_fix_suggestions(validation)
    blocking_rows = validation_issue_rows(validation, severity="blocking")
    dialogue_rows = validation_issue_rows(validation, validator_id="dialogue-voice")

    assert groups[0].validator_id == "dialogue-voice"
    assert groups[0].severity == "blocking"
    assert groups[0].count == 1
    assert groups[0].suggested_action == "fix SC_004"
    assert suggestions[0].target_id == "SC_004"
    assert suggestions[0].target_type == "scene"
    assert suggestions[0].command == "fix SC_004"
    assert format_fix_draft(suggestions[0]) == ("dialogue-voice: Dialogue voice drift in scene 4.")
    assert blocking_rows == dialogue_rows
    assert blocking_rows[0]["scene"] == "SC_004"


def test_review_models_build_checklist_issues_and_threads() -> None:
    gateway = RecordingGateway()
    validation = gateway.get_validation_workspace("field-message")
    review = gateway.get_review_workspace("field-message")
    comment = gateway.add_operator_comment(
        OperatorCommentRequest(
            target_type="scene",
            target_id="SC_004",
            phase="script",
            body="Make the voice more consistent.",
        ),
        "field-message",
    )

    checklist = build_review_checklist_rows(review, validation, [comment])
    issues = build_review_issue_rows(review, validation)
    threads = build_comment_thread_rows([comment])

    assert checklist[0]["check"] == "candidate_artifacts"
    assert checklist[1]["status"] == "blocked"
    assert issues[0]["target_id"] == "SC_004"
    assert issues[0]["command"] == "scene SC_004"
    assert any(row["severity"] == "warning" and row["target_id"] == "SC_007" for row in issues)
    assert threads == [
        {
            "target_id": "SC_004",
            "target_type": "scene",
            "open": 1,
            "latest": "Make the voice more consistent.",
            "updated": "2026-06-24T10:02:00",
            "command": "thread SC_004",
        }
    ]


def test_textual_cockpit_loads_gateway_snapshot() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            assert app.snapshot is not None
            assert app.snapshot.dashboard is not None
            assert app.snapshot.dashboard.current_phase == "script"
            status = app.query_one("#status_bar", Static).renderable
            project_table = app.query_one("#project_table", DataTable)
            dashboard_kpi_table = app.query_one("#dashboard_kpi_table", DataTable)
            dashboard_action_table = app.query_one("#dashboard_action_table", DataTable)
            graph_artifact_table = app.query_one("#graph_artifact_table", DataTable)
            asset_action_table = app.query_one("#asset_action_table", DataTable)
            matrix_table = app.query_one("#matrix_table", DataTable)
            matrix_pivot_table = app.query_one("#matrix_pivot_table", DataTable)
            review_checklist_table = app.query_one("#review_checklist_table", DataTable)
            review_issue_table = app.query_one("#review_issue_table", DataTable)
            command_suggestion_table = app.query_one("#command_suggestion_table", DataTable)
            command_help_table = app.query_one("#command_help_table", DataTable)
            command_validation = app.query_one("#command_validation", Static)
            validation_group_table = app.query_one("#validation_group_table", DataTable)
            validation_fix_table = app.query_one("#validation_fix_table", DataTable)
            assert "The Field Message" in str(status)
            assert project_table.row_count == 1
            assert dashboard_kpi_table.row_count == 5
            assert dashboard_action_table.row_count >= 3
            assert graph_artifact_table.row_count == 2
            assert asset_action_table.row_count == 6
            assert matrix_table.row_count >= 3
            assert matrix_pivot_table.row_count >= 2
            assert review_checklist_table.row_count == 5
            assert review_issue_table.row_count == 3
            assert command_suggestion_table.row_count >= 8
            assert command_help_table.row_count >= 8
            assert "Command:" in str(command_validation.renderable)
            assert validation_group_table.row_count == 2
            assert validation_fix_table.row_count == 2

    asyncio.run(run())


def test_textual_cockpit_uses_dense_dashboard_and_asset_layouts() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            assert app.query_one("#dashboard_top", Horizontal)
            assert app.query_one("#dashboard_ops", Horizontal)
            assert app.query_one("#asset_ops", Horizontal)
            assert app.query_one("#reader_ops", Horizontal)
            assert app.query_one("#reader_body_stack", Vertical)

    asyncio.run(run())


def test_textual_cockpit_dashboard_metric_command_routes_to_blockers() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("dashboard blockers")
            await pilot.pause()

            table = app.query_one("#validation_table", DataTable)
            context = app.query_one("#context_panel", Static).renderable
            assert table.row_count == 1
            assert "Validation filter: blocking" in str(context)

    asyncio.run(run())


def test_textual_cockpit_revision_action_uses_comment_note() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.query_one("#comment_input", Input).value = "Fix SC_004 voice but keep the ending."
            app.action_request_revision()
            await pilot.pause()

            assert gateway.revision_notes == ["Fix SC_004 voice but keep the ending."]

    asyncio.run(run())


def test_textual_cockpit_targeted_comment_command_stores_annotation() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("comment SC_007 | Make the payoff clearer.")
            await pilot.pause()

            assert gateway.comments is not None
            assert gateway.comments[0].target_type == "validation_issue"
            assert gateway.comments[0].target_id == "SC_007"
            assert gateway.comments[0].phase == "script"
            assert gateway.comments[0].body == "Make the payoff clearer."

    asyncio.run(run())


def test_textual_cockpit_add_comment_action_uses_selected_target() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app.selected_target = selection_from_row(
                "scene_table",
                {"scene": "SC_007", "phase": "script"},
            )
            app.query_one("#comment_input", Input).value = "This scene needs a sharper turn."
            app.action_add_comment()
            await pilot.pause()

            assert gateway.comments is not None
            assert gateway.comments[0].target_type == "scene"
            assert gateway.comments[0].target_id == "SC_007"
            assert gateway.comments[0].body == "This scene needs a sharper turn."

    asyncio.run(run())


def test_textual_cockpit_review_issue_command_prefills_and_opens_target() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("review issue review:1")
            await pilot.pause()

            assert app.selected_target is not None
            assert app.selected_target.target_type == "scene"
            assert app.selected_target.target_id == "SC_004"
            assert app.query_one("#comment_input", Input).value == "Dialogue voice drift in SC_004"
            context = app.query_one("#context_panel", Static).renderable
            assert "Review Issue" in str(context)

    asyncio.run(run())


def test_textual_cockpit_draft_command_prefills_targeted_review_note() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("draft SC_007 | Make the payoff more visual.")
            await pilot.pause()

            assert app.selected_target is not None
            assert app.selected_target.target_id == "SC_007"
            assert app.query_one("#comment_input", Input).value == "Make the payoff more visual."
            context = app.query_one("#context_panel", Static).renderable
            assert "Draft Ready" in str(context)

    asyncio.run(run())


def test_textual_cockpit_thread_command_shows_grouped_comments() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        gateway.add_operator_comment(
            OperatorCommentRequest(
                target_type="scene",
                target_id="SC_004",
                phase="script",
                body="Voice is too polished.",
            ),
            "field-message",
        )
        gateway.add_operator_comment(
            OperatorCommentRequest(
                target_type="scene",
                target_id="SC_004",
                phase="script",
                body="Keep the station silence.",
            ),
            "field-message",
        )
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            thread_table = app.query_one("#comment_thread_table", DataTable)
            assert thread_table.row_count == 1

            app._run_command("thread SC_004")
            await pilot.pause()

            assert app.selected_target is not None
            assert app.selected_target.target_id == "SC_004"
            context = app.query_one("#context_panel", Static).renderable
            assert "Comment Thread" in str(context)
            assert "Voice is too polished." in str(context)
            assert "Keep the station silence." in str(context)

    asyncio.run(run())


def test_textual_cockpit_artifact_command_loads_reader_context() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("artifact script")
            await pilot.pause()

            assert app.selected_artifact is not None
            assert app.selected_artifact.artifact_id == "script"
            assert app.reader is not None
            assert app.selected_target is not None
            assert app.selected_target.target_type == "artifact"
            context = app.query_one("#context_panel", Static).renderable
            body = app.query_one("#reader_body", Static).renderable
            index_table = app.query_one("#reader_index_table", DataTable)
            assert "Reader" in str(context)
            assert "INT. STATION - DAWN" in str(body)
            assert "SC_004" in str(context)
            assert index_table.row_count == 1

    asyncio.run(run())


def test_textual_cockpit_asset_review_command_stores_review_comment() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("asset review script")
            await pilot.pause()

            assert gateway.comments is not None
            assert gateway.comments[0].target_type == "artifact"
            assert gateway.comments[0].target_id == "script"
            assert gateway.comments[0].phase == "script"
            assert "[asset_action=review]" in gateway.comments[0].body

    asyncio.run(run())


def test_textual_cockpit_asset_change_and_extend_submit_targeted_revisions() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("asset change script | Make scene four less verbal.")
            await pilot.pause()
            app._run_command("asset extend scene_matrix | Add one visual bridge shot.")
            await pilot.pause()

            assert gateway.revision_notes is not None
            assert "[asset_action=change] Make scene four less verbal." in gateway.revision_notes[0]
            assert "target_type=artifact target_id=script phase=script" in gateway.revision_notes[0]
            assert "[asset_action=extend] Add one visual bridge shot." in gateway.revision_notes[1]
            assert (
                "target_type=artifact target_id=scene_matrix phase=script"
                in gateway.revision_notes[1]
            )

    asyncio.run(run())


def test_textual_cockpit_asset_action_row_prefills_command() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            rows = app._table_rows["asset_action_table"]
            row_index = next(
                index
                for index, row in enumerate(rows)
                if row["artifact_id"] == "script" and row["action"] == "change"
            )
            table = app.query_one("#asset_action_table", DataTable)
            table.move_cursor(row=row_index)
            table.action_select_cursor()
            await pilot.pause()

            palette = app.query_one("#command_palette", Input)
            assert palette.value == "asset change script | <note>"
            assert "open" in palette.classes

    asyncio.run(run())


def test_textual_cockpit_reader_next_opens_index_target() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("artifact script")
            await pilot.pause()
            app._run_command("reader next")
            await pilot.pause()

            assert app.reader is not None
            assert app.reader.metadata["scene_id"] == "SC_004"
            assert app.selected_target is not None
            assert app.selected_target.target_type == "scene"

    asyncio.run(run())


def test_textual_cockpit_reader_link_table_runs_link_command() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        gateway.add_operator_comment(
            OperatorCommentRequest(
                target_type="scene",
                target_id="SC_004",
                phase="script",
                body="Keep the platform empty.",
            ),
            "field-message",
        )
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("scene SC_004")
            await pilot.pause()

            link_table = app.query_one("#reader_link_table", DataTable)
            assert link_table.row_count == 2
            rows = app._table_rows["reader_link_table"]
            row_index = next(index for index, row in enumerate(rows) if row["kind"] == "comment")
            link_table.move_cursor(row=row_index)
            link_table.action_select_cursor()
            await pilot.pause()

            context = app.query_one("#context_panel", Static).renderable
            assert "Comment Thread" in str(context)
            assert "Keep the platform empty." in str(context)

    asyncio.run(run())


def test_textual_cockpit_scene_command_loads_scene_reader() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("scene SC_004")
            await pilot.pause()

            assert app.reader is not None
            assert app.reader.metadata["scene_id"] == "SC_004"
            assert app.selected_target is not None
            assert app.selected_target.target_type == "scene"
            body = app.query_one("#reader_body", Static).renderable
            scene_reader = app.query_one("#scene_reader", Static).renderable
            assert "The message arrived before the train." in str(body)
            assert "Linked validation" in str(scene_reader)

    asyncio.run(run())


def test_textual_cockpit_phase_command_drills_into_graph() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("phase script")
            await pilot.pause()

            assert app.selected_target is not None
            assert app.selected_target.target_type == "graph_phase"
            assert app.selected_target.target_id == "script"
            detail = app.query_one("#graph_phase_detail", Static).renderable
            table = app.query_one("#graph_artifact_table", DataTable)
            context = app.query_one("#context_panel", Static).renderable
            assert "Phase: script" in str(detail)
            assert table.row_count == 2
            assert "Suggested commands" in str(context)

    asyncio.run(run())


def test_textual_cockpit_next_command_opens_review_workspace() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("next")
            await pilot.pause()

            context = app.query_one("#context_panel", Static).renderable
            assert "Review Context" in str(context)

    asyncio.run(run())


def test_textual_cockpit_approve_requires_confirmation() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("approve")
            await pilot.pause()

            context = app.query_one("#context_panel", Static).renderable
            assert gateway.approved_count == 0
            assert app.pending_confirmation == "approve"
            assert "Confirm Approval" in str(context)
            assert "confirm approve" in str(context)

    asyncio.run(run())


def test_textual_cockpit_confirm_approve_calls_gateway() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("approve")
            await pilot.pause()
            app._run_command("confirm approve")
            await pilot.pause()

            assert gateway.approved_count == 1
            assert app.pending_confirmation == ""

    asyncio.run(run())


def test_textual_cockpit_revise_alias_submits_note() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("revise Keep the ending but sharpen SC_004 voice.")
            await pilot.pause()

            assert gateway.revision_notes == ["Keep the ending but sharpen SC_004 voice."]

    asyncio.run(run())


def test_textual_cockpit_command_suggestion_selection_prefills_palette() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            rows = app._table_rows["command_suggestion_table"]
            row_index = next(
                index for index, row in enumerate(rows) if row["command"] == "fix SC_004"
            )
            table = app.query_one("#command_suggestion_table", DataTable)
            table.move_cursor(row=row_index)
            table.action_select_cursor()
            await pilot.pause()

            palette = app.query_one("#command_palette", Input)
            context = app.query_one("#context_panel", Static).renderable
            assert palette.value == "fix SC_004"
            assert "open" in palette.classes
            assert "Command ready" in str(context)

    asyncio.run(run())


def test_textual_cockpit_command_palette_filters_and_validates_input() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            palette = app.query_one("#command_palette", Input)
            palette.value = "artifact missing"
            await pilot.pause()

            validation = app.query_one("#command_validation", Static).renderable
            rows = app._table_rows["command_suggestion_table"]
            assert "Unknown artifact" in str(validation)
            assert all("artifact" in str(row["command"]) for row in rows)

    asyncio.run(run())


def test_textual_cockpit_commands_command_shows_help_surface() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("commands")
            await pilot.pause()

            context = app.query_one("#context_panel", Static).renderable
            help_rows = app._table_rows["command_help_table"]
            assert "Command Help" in str(context)
            assert any(row["command"] == "scene <scene_id>" for row in help_rows)

    asyncio.run(run())


def test_textual_cockpit_create_command_prefills_required_fields() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("create")
            await pilot.pause()

            palette = app.query_one("#command_palette", Input)
            validation = app.query_one("#command_validation", Static).renderable
            context = app.query_one("#context_panel", Static).renderable
            assert palette.value == "create <project_id> | <title> | <idea>"
            assert "incomplete" in str(validation)
            assert "Command template" in str(context)

    asyncio.run(run())


def test_textual_cockpit_project_lane_filter_and_switch_command() -> None:
    async def run() -> None:
        gateway = RecordingGateway(
            extra_projects=[
                ProjectListItem(
                    project_id="fixture-short-test",
                    title="Fixture Short",
                    slug="fixture-short-test",
                    current_phase="intake",
                    status="discovered",
                    has_blockers=False,
                    awaiting_review=False,
                    project_kind="test",
                    project_root="/tmp/projects/fixture-short-test",
                )
            ]
        )
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            assert app.query_one("#project_table", DataTable).row_count == 1

            app._run_command("projects test")
            await pilot.pause()
            rows = app._table_rows["project_table"]
            context = app.query_one("#context_panel", Static).renderable
            assert app.project_filter == "test"
            assert rows[0]["project"] == "fixture-short-test"
            assert "Project lane: test" in str(context)

            app._run_command("projects all")
            await pilot.pause()
            app._run_command("project field-message")
            await pilot.pause()

            assert gateway.active_project_id == "field-message"
            assert app.active_project_id == "field-message"

    asyncio.run(run())


def test_textual_cockpit_guide_tab_exposes_validated_1min_path() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("open guide")
            await pilot.pause()

            guide_table = app.query_one("#guide_table", DataTable)
            guide_detail = app.query_one("#guide_detail", Static).renderable
            guide_summary = app.query_one("#guide_summary", Static).renderable
            context = app.query_one("#context_panel", Static).renderable
            rows = app._table_rows["guide_table"]
            assert guide_table.row_count == 6
            assert rows[0]["status"] == "done"
            assert rows[1]["status"] == "current"
            assert rows[2]["status"] == "done"
            assert rows[3]["status"] == "blocked"
            assert "2/6 done" in str(guide_summary)
            assert "create 1min-field" in str(guide_detail)
            assert "Status: done" in str(guide_detail)
            assert "Active project field-message is at script." in str(guide_detail)
            assert "A-Z path" in str(context)

    asyncio.run(run())


def test_guide_status_rows_cover_later_generation_states() -> None:
    gateway = RecordingGateway()
    dashboard = gateway.get_dashboard("field-message")
    generation_dashboard = DashboardSummary(
        project_id=dashboard.project_id,
        title=dashboard.title,
        slug=dashboard.slug,
        current_phase="generation",
        runtime_mode=dashboard.runtime_mode,
        workflow_mode=dashboard.workflow_mode,
        status="in_progress",
        next_action="run_generation",
        route_reason="generation approved",
    )
    snapshot = app_snapshot = None
    app = FilmCockpitApp(gateway=gateway)
    snapshot = app_snapshot or app._load_snapshot()
    generation_snapshot = type(snapshot)(
        projects=snapshot.projects,
        dashboard=generation_dashboard,
        review=snapshot.review,
        validation=snapshot.validation,
        artifacts=[
            *snapshot.artifacts,
            {
                "artifact_id": "clip_SC_004",
                "artifact_type": "clip",
                "phase": "generation",
                "version": 1,
                "status": "candidate",
            },
        ],
        checkpoints=snapshot.checkpoints,
        providers=snapshot.providers,
        audit_events=snapshot.audit_events,
        comments=snapshot.comments,
        matrix_rows=snapshot.matrix_rows,
        graph_rows=snapshot.graph_rows,
        command_suggestions=snapshot.command_suggestions,
        command_options=snapshot.command_options,
    )

    rows = app._guide_rows(generation_snapshot)

    assert rows[1]["status"] == "done"
    assert rows[4]["status"] == "done"
    assert rows[5]["status"] == "done"


def test_textual_cockpit_guidance_branches_for_invalid_commands() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=RecordingGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            app._asset_command("")
            assert "Asset commands" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("asset review missing")
            await pilot.pause()
            assert "Artifact 'missing'" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("asset change script")
            await pilot.pause()
            assert "Use: asset change" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("projects sandbox")
            await pilot.pause()
            assert "projects production" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("project ")
            await pilot.pause()
            assert "Unknown command" in str(app.query_one("#context_panel", Static).renderable)

            app._switch_project("")
            assert "Use: project" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("confirm approve")
            await pilot.pause()
            assert "No pending approval" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("create missing-parts")
            await pilot.pause()
            assert "Use: create" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("thread missing-target")
            await pilot.pause()
            assert "No comment thread" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("draft missing-target")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "review"

            app._show_phase_detail("")
            assert "Use: phase" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("dashboard providers")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "providers"

            app._run_command("dashboard comments")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "review"

            app._run_command("dashboard unknown")
            await pilot.pause()
            assert "Dashboard commands" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("replace <template>")
            await pilot.pause()
            assert "Replace template fields" in str(
                app.query_one("#context_panel", Static).renderable
            )

    asyncio.run(run())


def test_textual_cockpit_create_and_missing_target_branches() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            app._run_command(
                "create new-short | New Short | A one minute chase across three rooms."
            )
            await pilot.pause()
            assert gateway.created_request is not None
            assert gateway.created_request.project_id == "new-short"
            assert gateway.created_request.project_kind == "production"
            assert app.active_project_id == "new-short"

            app._open_artifact("missing-artifact")
            assert "missing-artifact" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("review issue missing-issue")
            await pilot.pause()
            assert app.query_one("#tabs", TabbedContent).active == "review"

            app._run_command("asset extend missing-artifact | Add more coverage.")
            await pilot.pause()
            assert "missing-artifact" in str(app.query_one("#context_panel", Static).renderable)

            app._run_command("open unknown-target")
            await pilot.pause()
            assert "unknown-target" in str(app.query_one("#context_panel", Static).renderable)

    asyncio.run(run())


def test_textual_cockpit_no_snapshot_and_ineligible_approval_guards() -> None:
    async def run() -> None:
        app = FilmCockpitApp(gateway=NoApprovalGateway())
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()

            app._run_command("approve")
            await pilot.pause()
            assert "Approval is not eligible" in str(
                app.query_one("#context_panel", Static).renderable
            )

            app.snapshot = None
            app._show_phase_detail("script")
            assert "No snapshot loaded" in str(app.query_one("#context_panel", Static).renderable)

            app._start_fix("SC_004")
            assert "No snapshot loaded" in str(app.query_one("#context_panel", Static).renderable)

            app._show_thread("SC_004")
            assert "No snapshot loaded" in str(app.query_one("#context_panel", Static).renderable)

            app._request_asset_review("script")
            assert "No active project" in str(app.query_one("#context_panel", Static).renderable)

    asyncio.run(run())


def test_textual_cockpit_matrix_filter_command_filters_rows() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("matrix warning")
            await pilot.pause()

            table = app.query_one("#matrix_table", DataTable)
            summary = app.query_one("#matrix_summary", Static).renderable
            context = app.query_one("#context_panel", Static).renderable
            assert app.matrix_filter == "warning"
            assert table.row_count == 1
            assert "Rows: 1/" in str(summary)
            assert "Matrix filter: warning" in str(context)

    asyncio.run(run())


def test_textual_cockpit_matrix_pivot_command_groups_rows() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("matrix pivot validation")
            await pilot.pause()

            pivot_table = app.query_one("#matrix_pivot_table", DataTable)
            context = app.query_one("#context_panel", Static).renderable
            rows = app._table_rows["matrix_pivot_table"]
            assert pivot_table.row_count >= 2
            assert app._matrix_pivot == "validation"
            assert any(row["value"] == "blocking" for row in rows)
            assert "Matrix Pivot" in str(context)

    asyncio.run(run())


def test_textual_cockpit_matrix_pivot_selection_applies_filter() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("matrix pivot status")
            await pilot.pause()
            rows = app._table_rows["matrix_pivot_table"]
            row_index = next(index for index, row in enumerate(rows) if row["value"] == "candidate")
            table = app.query_one("#matrix_pivot_table", DataTable)
            table.move_cursor(row=row_index)
            table.action_select_cursor()
            await pilot.pause()

            assert app.matrix_filter == "status:candidate"
            assert app.query_one("#matrix_table", DataTable).row_count == 2

    asyncio.run(run())


def test_textual_cockpit_validator_command_filters_validation_rows() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("validator dialogue-voice")
            await pilot.pause()

            table = app.query_one("#validation_table", DataTable)
            context = app.query_one("#context_panel", Static).renderable
            assert table.row_count == 1
            assert "Validation filter: dialogue-voice" in str(context)
            assert "Visible issues: 1" in str(context)

    asyncio.run(run())


def test_textual_cockpit_show_blocked_filters_validation_rows() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("show blocked")
            await pilot.pause()

            table = app.query_one("#validation_table", DataTable)
            context = app.query_one("#context_panel", Static).renderable
            assert table.row_count == 1
            assert "Validation filter: blocking" in str(context)

    asyncio.run(run())


def test_textual_cockpit_fix_command_prefills_targeted_note() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("fix SC_004")
            await pilot.pause()

            assert app.reader is not None
            assert app.selected_target is not None
            assert app.selected_target.target_id == "SC_004"
            comment = app.query_one("#comment_input", Input).value
            context = app.query_one("#context_panel", Static).renderable
            assert comment == "dialogue-voice: Dialogue voice drift in scene 4."
            assert "Fix Draft" in str(context)

    asyncio.run(run())


def test_textual_cockpit_open_target_command_opens_artifact_reader() -> None:
    async def run() -> None:
        gateway = RecordingGateway()
        app = FilmCockpitApp(gateway=gateway)
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            app._run_command("open script")
            await pilot.pause()

            assert app.selected_artifact is not None
            assert app.selected_artifact.artifact_id == "script"
            assert app.reader is not None
            assert app.reader.title == "script:v4"

    asyncio.run(run())


def test_gateway_protocol_shape_accepts_recording_gateway() -> None:
    gateway = RecordingGateway()
    rows: list[dict[str, Any]] = gateway.list_artifacts()

    assert rows[0]["artifact_id"] == "script"
