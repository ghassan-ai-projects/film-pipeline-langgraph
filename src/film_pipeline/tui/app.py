"""Textual operator cockpit for the film pipeline.

Run with:

```
python -m film_pipeline.tui.app
```
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Mapping
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, DataTable, Footer, Header, Input, Static, TabbedContent, TabPane

from film_pipeline.app.services.errors import ServiceError
from film_pipeline.app.services.models import (
    ArtifactDetail,
    DashboardSummary,
    OperatorCommentRequest,
    ProjectCreateRequest,
    ProjectListItem,
)
from film_pipeline.tui.formatting import pretty
from film_pipeline.tui.gateway import StudioGateway
from film_pipeline.tui.gateways import InProcessStudioGateway
from film_pipeline.tui.view_models import (
    CockpitSnapshot,
    MatrixImpact,
    PhaseDetail,
    ReaderView,
    TargetSelection,
    build_artifact_reader,
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
    filter_command_suggestions,
    filter_matrix_rows,
    format_fix_draft,
    format_selection_detail,
    format_targeted_revision_note,
    selection_from_row,
    summarize_attention,
    validation_issue_rows,
)


class FilmCockpitApp(App[None]):
    """Bloomberg-style terminal cockpit for film pipeline operations."""

    CSS = """
    Screen {
        background: #06080a;
        color: #d8dee9;
    }

    #shell {
        height: 1fr;
    }

    #project_rail {
        width: 28;
        border: solid #2e3440;
        padding: 0 1;
    }

    #workspace {
        width: 1fr;
        border: solid #3b4252;
    }

    #context_drawer {
        width: 34;
        border: solid #2e3440;
        padding: 0 1;
    }

    .panel {
        border: solid #3b4252;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    .headline {
        color: #88c0d0;
        text-style: bold;
    }

    .danger {
        color: #bf616a;
    }

    .warn {
        color: #ebcb8b;
    }

    .ok {
        color: #a3be8c;
    }

    DataTable {
        height: 1fr;
    }

    #comment_input {
        height: 3;
    }

    #command_palette {
        dock: bottom;
        display: none;
    }

    #command_palette.open {
        display: block;
    }
    """

    BINDINGS: ClassVar = [
        Binding("g,d", "open_tab('dashboard')", "Dashboard"),
        Binding("g,r", "open_tab('review')", "Review"),
        Binding("g,g", "open_tab('graph')", "Graph"),
        Binding("g,m", "open_tab('matrix')", "Matrix"),
        Binding("g,s", "open_tab('scenes')", "Scenes"),
        Binding("g,a", "open_tab('assets')", "Assets"),
        Binding("g,v", "open_tab('validation')", "Validation"),
        Binding("g,p", "open_tab('providers')", "Providers"),
        Binding("g,c", "open_tab('checkpoints')", "Checkpoints"),
        Binding("g,u", "open_tab('audit')", "Audit"),
        Binding("a", "approve_phase", "Approve"),
        Binding("r", "request_revision", "Revise"),
        Binding("c", "add_comment", "Comment"),
        Binding("/", "toggle_command_palette", "Command"),
        Binding("f5", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        gateway: StudioGateway | None = None,
        *,
        start_create: bool = False,
    ) -> None:
        super().__init__()
        self.gateway = gateway or InProcessStudioGateway()
        self.start_create = start_create
        self.active_project_id = ""
        self.snapshot: CockpitSnapshot | None = None
        self.selected_artifact: ArtifactDetail | None = None
        self.reader: ReaderView | None = None
        self.selected_target: TargetSelection | None = None
        self.matrix_filter = ""
        self._matrix_pivot = "status"
        self.matrix_impact: MatrixImpact | None = None
        self.pending_confirmation = ""
        self._table_rows: dict[str, list[dict[str, object]]] = {}

    def compose(self) -> ComposeResult:
        """Compose the persistent cockpit shell."""
        yield Header(show_clock=True)
        with Horizontal(id="shell"):
            with Vertical(id="project_rail"):
                yield Static("Projects", classes="headline")
                yield DataTable(id="project_table")
                yield Button("New Project", id="new_project", variant="primary")
                yield Button("Refresh", id="refresh_button")
            with Vertical(id="workspace"):
                yield Static("", id="status_bar", classes="panel")
                with TabbedContent(initial="dashboard", id="tabs"):
                    with TabPane("Dashboard", id="dashboard"):
                        yield Static("", id="dashboard_summary", classes="panel")
                        yield Static("", id="attention_panel", classes="panel")
                        yield DataTable(id="dashboard_kpi_table")
                        yield DataTable(id="dashboard_action_table")
                        yield DataTable(id="dashboard_artifacts")
                    with TabPane("Graph", id="graph"):
                        yield Static("", id="graph_summary", classes="panel")
                        yield DataTable(id="graph_table")
                        yield Static("", id="graph_phase_detail", classes="panel")
                        yield DataTable(id="graph_artifact_table")
                    with TabPane("Matrix", id="matrix"):
                        yield Static("Smart Matrix", classes="headline")
                        yield Static("", id="matrix_summary", classes="panel")
                        yield DataTable(id="matrix_pivot_table")
                        yield DataTable(id="matrix_table")
                    with TabPane("Review", id="review"):
                        yield Static("", id="review_summary", classes="panel")
                        yield Static("", id="review_intelligence", classes="panel")
                        yield DataTable(id="review_checklist_table")
                        yield DataTable(id="review_issue_table")
                        yield DataTable(id="review_artifacts")
                        yield Static("Comment Threads", classes="headline")
                        yield DataTable(id="comment_thread_table")
                        yield Static("Operator Comments", classes="headline")
                        yield DataTable(id="comment_table")
                        yield Input(
                            placeholder="Comment on selected scene/artifact/issue, then press r",
                            id="comment_input",
                        )
                        with Horizontal():
                            yield Button("Add Comment", id="comment_button", variant="primary")
                            yield Button("Approve Phase", id="approve_button", variant="success")
                            yield Button(
                                "Request Revision",
                                id="revision_button",
                                variant="warning",
                            )
                    with TabPane("Scenes", id="scenes"):
                        yield Static("", id="scene_summary", classes="panel")
                        yield DataTable(id="scene_table")
                        yield Static("", id="scene_reader", classes="panel")
                    with TabPane("Assets", id="assets"):
                        yield Static("Assets and Artifacts", classes="headline")
                        yield DataTable(id="asset_table")
                        yield Static("Reader Index", classes="headline")
                        yield DataTable(id="reader_index_table")
                        yield Static("", id="reader_title", classes="panel")
                        yield Static("", id="reader_outline", classes="panel")
                        yield Static("", id="reader_body", classes="panel")
                        yield Static("", id="reader_metadata", classes="panel")
                        yield DataTable(id="reader_link_table")
                        yield Static("", id="reader_links", classes="panel")
                    with TabPane("Validation", id="validation"):
                        yield Static("", id="validation_summary", classes="panel")
                        yield Static("", id="validation_intelligence", classes="panel")
                        yield DataTable(id="validation_group_table")
                        yield DataTable(id="validation_fix_table")
                        yield DataTable(id="validation_table")
                    with TabPane("Checkpoints", id="checkpoints"):
                        yield Static("Checkpoint Timeline", classes="headline")
                        yield DataTable(id="checkpoint_table")
                    with TabPane("Providers", id="providers"):
                        yield Static("Provider Operations", classes="headline")
                        yield DataTable(id="provider_table")
                    with TabPane("Audit", id="audit"):
                        yield Static("Recent Audit Events", classes="headline")
                        yield DataTable(id="audit_table")
            with VerticalScroll(id="context_drawer"):
                yield Static("Context", classes="headline")
                yield Static("", id="context_panel")
                yield Static("", id="command_options", classes="panel")
                yield Static("", id="command_validation", classes="panel")
                yield Static("Command Suggestions", classes="headline")
                yield DataTable(id="command_suggestion_table")
                yield Static("Command Help", classes="headline")
                yield DataTable(id="command_help_table")
        yield Input(
            placeholder="Command palette: try 'open review', 'show blocked', 'artifact <id>'",
            id="command_palette",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize tables and load the first snapshot."""
        self.title = "LangGraph Film Studio Cockpit"
        self.sub_title = "operator cockpit"
        self._initialize_tables()
        self.action_refresh()
        if self.start_create:
            self.action_toggle_command_palette()

    def action_refresh(self) -> None:
        """Refresh all cockpit pages from the gateway."""
        try:
            self.snapshot = self._load_snapshot()
            self._render_snapshot(self.snapshot)
        except (ServiceError, ValueError, FileNotFoundError) as exc:
            self._update_context(f"Error\n\n{exc}")

    def action_open_tab(self, tab_id: str) -> None:
        """Open a workspace tab by ID."""
        self.query_one("#tabs", TabbedContent).active = tab_id
        self._context_for_tab(tab_id)

    def action_toggle_command_palette(self) -> None:
        """Show or hide the command palette."""
        palette = self.query_one("#command_palette", Input)
        if "open" in palette.classes:
            palette.remove_class("open")
            return
        palette.add_class("open")
        self._update_command_palette_intelligence(palette.value)
        palette.focus()

    def action_approve_phase(self) -> None:
        """Prepare explicit approval confirmation for the active phase."""
        self._prepare_approval_confirmation()

    def _approve_phase_now(self) -> None:
        """Approve the active phase after explicit operator confirmation."""
        if not self.active_project_id:
            self._update_context("No active project.")
            return
        result = self.gateway.approve_phase(self.active_project_id)
        self.active_project_id = result.project_id
        self.pending_confirmation = ""
        self._update_context(
            f"{result.message or 'Phase approved.'}\nCurrent phase: {result.current_phase}"
        )
        self.action_refresh()

    def action_request_revision(self) -> None:
        """Request a revision using the review comment field."""
        if not self.active_project_id:
            self._update_context("No active project.")
            return
        note = self.query_one("#comment_input", Input).value.strip()
        if not note:
            self._update_context("Write a revision note before requesting revision.")
            self.action_open_tab("review")
            return
        targeted_note = format_targeted_revision_note(self.selected_target, note)
        result = self.gateway.request_revision(targeted_note, self.active_project_id)
        self.active_project_id = result.project_id
        self._update_context(
            f"{result.message or 'Revision requested.'}\nCurrent phase: {result.current_phase}"
        )
        self.query_one("#comment_input", Input).value = ""
        self.action_refresh()

    def action_add_comment(self) -> None:
        """Store the review input as a target-scoped operator comment."""
        if not self.active_project_id:
            self._update_context("No active project.")
            return
        note = self.query_one("#comment_input", Input).value.strip()
        if not note:
            self._update_context("Write a comment before storing it.")
            self.action_open_tab("review")
            return
        phase = self.snapshot.review.phase if self.snapshot and self.snapshot.review else ""
        selection = self.selected_target or TargetSelection(
            target_type="phase",
            target_id=phase or "review",
            phase=phase,
        )
        comment = self.gateway.add_operator_comment(
            OperatorCommentRequest(
                target_type=selection.target_type,
                target_id=selection.target_id,
                phase=selection.phase,
                source="tui",
                body=note,
            ),
            self.active_project_id,
        )
        self.query_one("#comment_input", Input).value = ""
        self._update_context(
            "Comment stored\n\n"
            f"id: {comment.comment_id}\n"
            f"target: {comment.target_type} {comment.target_id}\n"
            f"body: {comment.body}"
        )
        self.action_refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle cockpit action buttons."""
        button_id = event.button.id
        if button_id == "refresh_button":
            self.action_refresh()
        elif button_id == "approve_button":
            self.action_approve_phase()
        elif button_id == "revision_button":
            self.action_request_revision()
        elif button_id == "comment_button":
            self.action_add_comment()
        elif button_id == "new_project":
            self._update_context(
                "Create Project\n\nUse the command palette with:\n"
                "create <project_id> | <title> | <idea>\n\n"
                "The service will auto-fill slug/runtime/workflow defaults."
            )
            self._fill_command("create <project_id> | <title> | <idea>")

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Show selected row detail and make it the active comment target."""
        table_id = event.data_table.id or ""
        rows = self._table_rows.get(table_id, [])
        if event.cursor_row >= len(rows):
            return
        row = rows[event.cursor_row]
        selection = selection_from_row(table_id, row)
        self.selected_target = selection
        self._update_context(format_selection_detail(selection))
        if table_id == "matrix_table" and self.snapshot is not None:
            self.matrix_impact = build_matrix_impact(
                row,
                comments=self.snapshot.comments,
                validation=self.snapshot.validation,
            )
            self._update_context(self._matrix_impact_context(self.matrix_impact))
        if table_id == "matrix_pivot_table":
            self._filter_matrix(str(row.get("command", "matrix all")).removeprefix("matrix "))
        if table_id in {"dashboard_kpi_table", "dashboard_action_table"}:
            self._fill_command(str(row.get("command", "")))
        if table_id == "graph_table":
            self._show_phase_detail(selection.target_id)
        if table_id == "review_issue_table":
            self._open_review_issue(row)
        if table_id == "comment_thread_table":
            self._show_thread(selection.target_id)
        if table_id == "validation_fix_table":
            self.query_one("#comment_input", Input).value = str(row.get("rationale", ""))
        if table_id == "command_suggestion_table":
            self._fill_command(str(row.get("command", "")))
        if table_id == "reader_index_table":
            self._open_reader_index(row)
        if table_id == "reader_link_table":
            self._run_command(str(row.get("command", "")))
        if selection.target_type == "artifact" and selection.target_id:
            self._try_load_artifact_detail(selection)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Run simple command palette commands."""
        if event.input.id != "command_palette":
            return
        self._run_command(event.value.strip())
        event.input.value = ""
        event.input.remove_class("open")
        self._update_command_palette_intelligence("")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Refresh command intelligence while the operator types."""
        if event.input.id != "command_palette":
            return
        self._update_command_palette_intelligence(event.value)

    def _load_snapshot(self) -> CockpitSnapshot:
        projects = self.gateway.list_projects()
        dashboard = self._load_dashboard(projects)
        project_id = dashboard.project_id if dashboard else None
        review = self.gateway.get_review_workspace(project_id) if project_id else None
        validation = self.gateway.get_validation_workspace(project_id) if project_id else None
        artifacts = self.gateway.list_artifacts(project_id) if project_id else []
        checkpoints = self.gateway.list_checkpoints(project_id) if project_id else []
        providers = self.gateway.list_provider_status()
        audit_events = self.gateway.get_audit_feed(project_id, limit=30) if project_id else []
        comments = self.gateway.list_operator_comments(project_id) if project_id else []
        matrix_rows = build_matrix_rows(artifacts, validation)
        graph_rows = build_graph_rows(dashboard)
        return CockpitSnapshot(
            projects=projects,
            dashboard=dashboard,
            review=review,
            validation=validation,
            artifacts=artifacts,
            checkpoints=checkpoints,
            providers=providers,
            audit_events=audit_events,
            comments=comments,
            matrix_rows=matrix_rows,
            graph_rows=graph_rows,
            command_suggestions=build_command_suggestions(
                dashboard=dashboard,
                validation=validation,
                artifacts=artifacts,
                matrix_rows=matrix_rows,
            ),
            command_options=build_command_options(
                projects=projects,
                dashboard=dashboard,
                validation=validation,
                artifacts=artifacts,
                providers=providers,
            ),
        )

    def _load_dashboard(self, projects: list[ProjectListItem]) -> DashboardSummary | None:
        if self.active_project_id:
            return self.gateway.get_dashboard(self.active_project_id)
        try:
            dashboard = self.gateway.get_dashboard(None)
            self.active_project_id = dashboard.project_id
            return dashboard
        except ServiceError:
            if not projects:
                return None
            dashboard = self.gateway.set_active_project(projects[0].project_id)
            self.active_project_id = dashboard.project_id
            return dashboard

    def _render_snapshot(self, snapshot: CockpitSnapshot) -> None:
        dashboard = snapshot.dashboard
        self._render_projects(snapshot.projects)
        self._render_status(dashboard, snapshot.providers)
        self._render_dashboard(snapshot)
        self._render_graph(snapshot)
        self._render_matrix(snapshot)
        self._render_review(snapshot)
        self._render_scenes(snapshot)
        self._render_assets(snapshot)
        self._render_validation(snapshot)
        self._render_checkpoints(snapshot)
        self._render_providers(snapshot)
        self._render_audit(snapshot)
        self._render_command_options(snapshot)
        self._update_command_palette_intelligence(self.query_one("#command_palette", Input).value)
        self._context_for_tab(self.query_one("#tabs", TabbedContent).active or "dashboard")

    def _render_projects(self, projects: list[ProjectListItem]) -> None:
        rows = [
            {
                "project": project.project_id,
                "phase": project.current_phase,
                "status": project.status,
                "review": "yes" if project.awaiting_review else "",
            }
            for project in projects
        ]
        self._set_table("#project_table", ["project", "phase", "status", "review"], rows)

    def _render_status(
        self,
        dashboard: DashboardSummary | None,
        providers: list[dict[str, object]],
    ) -> None:
        if dashboard is None:
            text = "No active project | / command palette | New Project"
        else:
            healthy = sum(
                1 for provider in providers if str(provider.get("status", "")) == "healthy"
            )
            text = (
                f"Project: {dashboard.title} | Phase: {dashboard.current_phase or 'none'} | "
                f"Status: {dashboard.status} | "
                f"Mode: {dashboard.workflow_mode}/{dashboard.runtime_mode} | "
                f"Next: {dashboard.next_action or 'none'} | "
                f"Providers: {healthy}/{len(providers)} healthy"
            )
        self.query_one("#status_bar", Static).update(text)

    def _render_dashboard(self, snapshot: CockpitSnapshot) -> None:
        dashboard = snapshot.dashboard
        if dashboard is None:
            self.query_one("#dashboard_summary", Static).update("No active project.")
            self.query_one("#attention_panel", Static).update("Create or select a project.")
            self._set_table("#dashboard_kpi_table", ["metric", "value", "state", "command"], [])
            self._set_table(
                "#dashboard_action_table",
                ["priority", "action", "status", "reason", "command"],
                [],
            )
            self._set_table("#dashboard_artifacts", ["artifact", "type", "phase", "status"], [])
            return
        summary = "\n".join(
            [
                f"Current phase: {dashboard.current_phase or 'none'}",
                f"Next action: {dashboard.next_action or 'none'}",
                f"Route reason: {dashboard.route_reason or 'none'}",
                f"Eligible: {', '.join(dashboard.eligible_actions) or 'none'}",
                f"Blocked: {len(dashboard.blocked_actions)}",
                f"Artifacts: {dashboard.artifact_count} | "
                f"Checkpoints: {dashboard.checkpoint_count} | "
                f"Issues: {dashboard.issue_count}",
            ]
        )
        self.query_one("#dashboard_summary", Static).update(summary)
        self.query_one("#attention_panel", Static).update(
            "\n".join(summarize_attention(dashboard, snapshot.validation, snapshot.providers))
        )
        self._set_table(
            "#dashboard_kpi_table",
            ["metric", "value", "state", "command"],
            build_dashboard_kpi_rows(
                dashboard,
                snapshot.validation,
                snapshot.providers,
                snapshot.comments,
            ),
        )
        self._set_table(
            "#dashboard_action_table",
            ["priority", "action", "status", "reason", "command"],
            build_dashboard_action_rows(dashboard, snapshot.review, snapshot.validation),
        )
        self._set_table(
            "#dashboard_artifacts",
            ["artifact", "type", "phase", "status"],
            [
                {
                    "artifact": row.get("artifact_id", ""),
                    "type": row.get("artifact_type", ""),
                    "phase": row.get("phase", ""),
                    "status": row.get("status", ""),
                }
                for row in snapshot.artifacts[:12]
            ],
        )

    def _render_graph(self, snapshot: CockpitSnapshot) -> None:
        dashboard = snapshot.dashboard
        if dashboard is None:
            self.query_one("#graph_summary", Static).update("No graph state yet.")
            self.query_one("#graph_phase_detail", Static).update("")
            self._set_table(
                "#graph_artifact_table",
                ["artifact_id", "artifact_type", "phase", "version", "status"],
                [],
            )
        else:
            self.query_one("#graph_summary", Static).update(
                f"You are here: {dashboard.current_phase or 'not started'}\n"
                f"Router says: {dashboard.next_action or 'none'}\n"
                f"{dashboard.route_reason or 'No route reason recorded.'}"
            )
            self._show_phase_detail(dashboard.current_phase, open_tab=False)
        self._set_table(
            "#graph_table",
            ["step", "phase", "status", "next_action"],
            snapshot.graph_rows,
        )

    def _render_matrix(self, snapshot: CockpitSnapshot) -> None:
        matrix_rows = filter_matrix_rows(snapshot.matrix_rows, self.matrix_filter)
        self.query_one("#matrix_summary", Static).update(
            f"Rows: {len(matrix_rows)}/{len(snapshot.matrix_rows)} | "
            f"Filter: {self.matrix_filter or 'all'} | "
            "Commands: matrix <query>, matrix pivot <status|phase|kind|validation>"
        )
        self._set_table(
            "#matrix_pivot_table",
            ["field", "value", "rows", "issues", "sample", "command"],
            build_matrix_pivot_rows(matrix_rows, self._matrix_pivot_field()),
        )
        self._set_table(
            "#matrix_table",
            ["target", "kind", "phase", "status", "validation", "action"],
            matrix_rows,
        )

    def _render_review(self, snapshot: CockpitSnapshot) -> None:
        review = snapshot.review
        if review is None:
            self.query_one("#review_summary", Static).update("No review workspace.")
            self.query_one("#review_intelligence", Static).update("")
            self._set_table(
                "#review_checklist_table",
                ["check", "status", "detail", "action"],
                [],
            )
            self._set_table(
                "#review_issue_table",
                ["issue_id", "severity", "target_id", "target_type", "message", "command"],
                [],
            )
            self._set_table("#review_artifacts", ["artifact", "type", "phase", "status"], [])
            self._set_table(
                "#comment_thread_table",
                ["target_id", "target_type", "open", "latest", "updated", "command"],
                [],
            )
            return
        checklist_rows = build_review_checklist_rows(
            review,
            snapshot.validation,
            snapshot.comments,
        )
        issue_rows = build_review_issue_rows(review, snapshot.validation)
        thread_rows = build_comment_thread_rows(snapshot.comments)
        summary = "\n".join(
            [
                f"Review package: {review.phase or 'none'}",
                f"Recommendation: {review.recommendation}",
                f"Actions: {', '.join(review.available_actions) or 'none'}",
                f"Blocked actions: {len(review.blocked_actions)}",
                f"Open issues: {len(review.open_issues)}",
            ]
        )
        self.query_one("#review_summary", Static).update(summary)
        self.query_one("#review_intelligence", Static).update(
            "Review Intelligence\n"
            f"Checklist: {len(checklist_rows)} | Issues: {len(issue_rows)} | "
            f"Threads: {len(thread_rows)}\n"
            "Commands: review issue <id>, thread <target>, draft <target> | <note>"
        )
        self._set_table(
            "#review_checklist_table",
            ["check", "status", "detail", "action"],
            checklist_rows,
        )
        self._set_table(
            "#review_issue_table",
            ["issue_id", "severity", "target_id", "target_type", "message", "command"],
            issue_rows,
        )
        self._set_table(
            "#review_artifacts",
            ["artifact", "type", "phase", "version", "status"],
            [
                {
                    "artifact": row.get("artifact_id", ""),
                    "type": row.get("artifact_type", ""),
                    "phase": row.get("phase", ""),
                    "version": row.get("version", ""),
                    "status": row.get("status", ""),
                }
                for row in review.candidate_artifacts
            ],
        )
        self._set_table(
            "#comment_thread_table",
            ["target_id", "target_type", "open", "latest", "updated", "command"],
            thread_rows,
        )
        self._set_table(
            "#comment_table",
            ["target", "type", "phase", "body", "created"],
            [
                {
                    "target": comment.target_id,
                    "type": comment.target_type,
                    "phase": comment.phase,
                    "body": comment.body,
                    "created": comment.created_at,
                }
                for comment in snapshot.comments
            ],
        )

    def _render_scenes(self, snapshot: CockpitSnapshot) -> None:
        self.query_one("#scene_summary", Static).update(
            "Scene workspace derives scene targets from matrix rows and validation issues.\n"
            "Use comments in Review to request targeted scene changes."
        )
        self._set_table(
            "#scene_table",
            ["scene", "phase", "status", "validation", "action"],
            build_scene_rows(snapshot.matrix_rows),
        )

    def _render_assets(self, snapshot: CockpitSnapshot) -> None:
        self._set_table(
            "#asset_table",
            ["artifact_id", "artifact_type", "phase", "version", "status"],
            snapshot.artifacts,
        )

    def _render_validation(self, snapshot: CockpitSnapshot) -> None:
        validation = snapshot.validation
        if validation is None:
            self.query_one("#validation_summary", Static).update("No validation workspace.")
            self.query_one("#validation_intelligence", Static).update("")
            self._set_table(
                "#validation_group_table",
                ["severity", "validator_id", "count", "targets", "suggested_action"],
                [],
            )
            self._set_table(
                "#validation_fix_table",
                ["severity", "target_id", "target_type", "validator_id", "command", "rationale"],
                [],
            )
            self._set_table("#validation_table", ["severity", "validator", "target", "message"], [])
            return
        groups = build_validation_groups(validation)
        suggestions = build_validation_fix_suggestions(validation)
        self.query_one("#validation_summary", Static).update(
            f"Phase: {validation.phase or 'none'} | Source: {validation.source} | "
            f"Blocking: {len(validation.blocking_issues)} | "
            f"Warnings: {len(validation.non_blocking_issues)} | Reports: {len(validation.reports)}"
        )
        self.query_one("#validation_intelligence", Static).update(
            "Validation Intelligence\n"
            f"Grouped validators: {len(groups)} | Suggested fixes: {len(suggestions)}\n"
            "Commands: validator <id>, fix <target>, show blocked, validation clear"
        )
        self._set_table(
            "#validation_group_table",
            ["severity", "validator_id", "count", "targets", "suggested_action"],
            [
                {
                    "severity": group.severity,
                    "validator_id": group.validator_id,
                    "count": group.count,
                    "targets": group.targets,
                    "message": group.message,
                    "suggested_action": group.suggested_action,
                }
                for group in groups
            ],
        )
        self._set_table(
            "#validation_fix_table",
            ["severity", "target_id", "target_type", "validator_id", "command", "rationale"],
            [
                {
                    "severity": suggestion.severity,
                    "target_id": suggestion.target_id,
                    "target_type": suggestion.target_type,
                    "validator_id": suggestion.validator_id,
                    "message": suggestion.message,
                    "command": suggestion.command,
                    "rationale": suggestion.rationale,
                }
                for suggestion in suggestions
            ],
        )
        self._set_table(
            "#validation_table",
            ["severity", "validator", "target", "scene", "message"],
            validation_issue_rows(validation),
        )

    def _render_checkpoints(self, snapshot: CockpitSnapshot) -> None:
        self._set_table(
            "#checkpoint_table",
            ["checkpoint_id", "phase", "reason", "created_at"],
            snapshot.checkpoints,
        )

    def _render_providers(self, snapshot: CockpitSnapshot) -> None:
        self._set_table(
            "#provider_table",
            ["provider_id", "status", "reason"],
            snapshot.providers,
        )

    def _render_audit(self, snapshot: CockpitSnapshot) -> None:
        self._set_table(
            "#audit_table",
            ["timestamp", "actor", "action", "target", "summary"],
            [event.__dict__ for event in snapshot.audit_events],
        )

    def _render_command_options(self, snapshot: CockpitSnapshot) -> None:
        options = snapshot.command_options
        self.query_one("#command_options", Static).update(
            "Selectable IDs\n\n"
            f"Projects: {', '.join(options.project_ids[:8]) or 'none'}\n"
            f"Phases: {', '.join(options.phases[:8]) or 'none'}\n"
            f"Artifacts: {', '.join(options.artifact_ids[:8]) or 'none'}\n"
            f"Scenes: {', '.join(options.scene_ids[:8]) or 'none'}\n"
            f"Validators: {', '.join(options.validator_ids[:8]) or 'none'}"
        )
        self._set_table(
            "#command_suggestion_table",
            ["command", "scope", "reason"],
            snapshot.command_suggestions,
        )
        self._set_table(
            "#command_help_table",
            ["command", "values", "purpose"],
            build_command_help_rows(options),
        )

    def _update_command_palette_intelligence(self, command: str) -> None:
        snapshot = self.snapshot
        if snapshot is None:
            return
        validation = build_command_validation(
            command,
            snapshot.command_options,
            snapshot.command_suggestions,
        )
        completion = f"\nComplete: {validation.completion}" if validation.completion else ""
        self.query_one("#command_validation", Static).update(
            f"Command: {validation.status}\n{validation.message}{completion}"
        )
        filtered = filter_command_suggestions(snapshot.command_suggestions, command)
        self._set_table(
            "#command_suggestion_table",
            ["command", "scope", "reason"],
            filtered or snapshot.command_suggestions,
        )

    def _show_command_help(self) -> None:
        snapshot = self.snapshot
        if snapshot is None:
            self._update_context("No command help without a loaded snapshot.")
            return
        self._set_table(
            "#command_help_table",
            ["command", "values", "purpose"],
            build_command_help_rows(snapshot.command_options),
        )
        self._update_context(
            "Command Help\n\n"
            "Use selectable IDs from the right rail. Suggestions are filtered as you type; "
            "the validation panel tells you whether a command is ready, incomplete, or unknown."
        )

    def _context_for_tab(self, tab_id: str) -> None:
        snapshot = self.snapshot
        if snapshot is None:
            self._update_context("No snapshot loaded.")
            return
        dashboard = snapshot.dashboard
        if tab_id == "dashboard":
            self._update_context(
                "Dashboard\n\n"
                "Dense operating summary: phase, route, blockers, latest artifacts, "
                "and next action."
            )
        elif tab_id == "graph" and dashboard is not None:
            self._update_context(
                "Graph Position\n\n"
                f"Current phase: {dashboard.current_phase or 'none'}\n"
                f"Next action: {dashboard.next_action or 'none'}\n"
                f"Route reason: {dashboard.route_reason or 'none'}"
            )
        elif tab_id == "review" and snapshot.review is not None:
            self._update_context(
                "Review Context\n\n"
                f"{snapshot.review.recommendation}\n\n"
                "Use review issue <id> to jump to issue context, thread <target> "
                "to inspect notes, or draft <target> | <note> to prefill revision."
            )
        elif tab_id == "matrix":
            self._update_context(
                "Smart Matrix\n\n"
                "Rows merge artifacts and validation issues. Targets with blocking "
                "validation should be fixed before approval."
            )
        elif tab_id == "validation" and snapshot.validation is not None:
            self._update_context(pretty(snapshot.validation))
        else:
            self._update_context("Context updates with the active page and selected object.")

    def _run_command(self, command: str) -> None:
        normalized = command.lower().strip()
        if not normalized:
            return
        if "<" in command and ">" in command:
            self._update_command_palette_intelligence(command)
            self._update_context("Replace template fields before running this command.")
            return
        if normalized in {"commands", "help", "help commands"}:
            self._show_command_help()
            return
        if normalized == "create":
            self._fill_command("create <project_id> | <title> | <idea>")
            return
        tab_aliases = {
            "dashboard": "dashboard",
            "open dashboard": "dashboard",
            "review": "review",
            "open review": "review",
            "graph": "graph",
            "open graph": "graph",
            "matrix": "matrix",
            "open matrix": "matrix",
            "validation": "validation",
            "providers": "providers",
            "assets": "assets",
            "artifacts": "assets",
            "scenes": "scenes",
            "checkpoints": "checkpoints",
            "audit": "audit",
        }
        if normalized in tab_aliases:
            self.action_open_tab(tab_aliases[normalized])
            return
        if normalized == "next":
            self._open_next_action()
            return
        if normalized == "approve":
            self.action_approve_phase()
            return
        if normalized == "confirm approve":
            self._confirm_approval()
            return
        if normalized.startswith("revise "):
            self.query_one("#comment_input", Input).value = command.removeprefix("revise ").strip()
            self.action_request_revision()
            return
        if normalized.startswith("review issue "):
            self._open_review_issue_by_id(command.removeprefix("review issue ").strip())
            return
        if normalized.startswith("thread "):
            self._show_thread(command.removeprefix("thread ").strip())
            return
        if normalized.startswith("draft "):
            self._draft_for_target(command.removeprefix("draft ").strip())
            return
        if normalized.startswith("dashboard "):
            self._dashboard_command(command.removeprefix("dashboard ").strip())
            return
        if normalized.startswith("reader "):
            self._reader_command(command.removeprefix("reader ").strip())
            return
        if normalized.startswith("link "):
            self._open_reader_link(command.removeprefix("link ").strip())
            return
        if normalized == "show blocked":
            self._filter_validation(severity="blocking")
            return
        if normalized.startswith("phase "):
            self._show_phase_detail(command.split(maxsplit=1)[1].strip())
            return
        if normalized.startswith("create "):
            self._create_project_from_command(command.removeprefix("create ").strip())
            return
        if normalized.startswith("artifact "):
            self._open_artifact(command.split(maxsplit=1)[1].strip())
            return
        if normalized.startswith("scene "):
            self._open_scene(command.split(maxsplit=1)[1].strip())
            return
        if normalized.startswith("matrix "):
            payload = command.removeprefix("matrix ").strip()
            if payload.lower().startswith("pivot "):
                self._pivot_matrix(payload.removeprefix("pivot ").strip())
            else:
                self._filter_matrix(payload)
            return
        if normalized.startswith("validator "):
            self._filter_validation(validator_id=command.split(maxsplit=1)[1].strip())
            return
        if normalized.startswith("validation "):
            self._validation_command(command.removeprefix("validation ").strip())
            return
        if normalized.startswith("fix "):
            self._start_fix(command.removeprefix("fix ").strip())
            return
        if normalized.startswith("open "):
            self._open_target(command.removeprefix("open ").strip())
            return
        if normalized.startswith("comment "):
            self._comment_from_command(command.removeprefix("comment ").strip())
            return
        self._update_context(
            "Unknown command.\n\n"
            "Try: next, phase <phase>, open review, open graph, show blocked, approve, "
            "confirm approve, matrix blocking, matrix pivot status, dashboard blockers, "
            "review issue <id>, thread <target>, reader next, link <target>, "
            "draft <target> | <note>, validator <id>, fix <target>."
        )

    def _prepare_approval_confirmation(self) -> None:
        snapshot = self.snapshot
        dashboard = snapshot.dashboard if snapshot else None
        if not self.active_project_id or snapshot is None or dashboard is None:
            self._update_context("No active project.")
            return
        if "approve_phase" not in dashboard.eligible_actions:
            self._update_context("Approval is not eligible for the current project state.")
            return
        blocking = len(snapshot.validation.blocking_issues) if snapshot.validation else 0
        self.pending_confirmation = "approve"
        self.action_open_tab("review")
        self._update_context(
            "Confirm Approval\n\n"
            f"project: {dashboard.project_id}\n"
            f"phase: {dashboard.current_phase or 'none'}\n"
            f"mode: {dashboard.workflow_mode}/{dashboard.runtime_mode}\n"
            f"blocking validation issues: {blocking}\n\n"
            "Approval will promote the current candidate phase and resume the pipeline. "
            "Type 'confirm approve' to continue."
        )

    def _confirm_approval(self) -> None:
        if self.pending_confirmation != "approve":
            self._update_context("No pending approval confirmation. Run 'approve' first.")
            return
        self._approve_phase_now()

    def _create_project_from_command(self, payload: str) -> None:
        parts = [part.strip() for part in payload.split("|")]
        if len(parts) != 3 or not all(parts):
            self._update_context("Use: create <project_id> | <title> | <idea>")
            return
        project_id, title, idea = parts
        result = self.gateway.create_project(
            ProjectCreateRequest(
                project_id=project_id,
                title=title,
                slug=project_id,
                idea=idea,
                runtime_mode="mock",
                workflow_mode="manual",
            )
        )
        self.active_project_id = result.project_id
        self._update_context(
            f"{result.message or 'Project created.'}\nCurrent phase: {result.current_phase}"
        )
        self.action_refresh()

    def _open_artifact(self, artifact_id: str) -> None:
        snapshot = self.snapshot
        if snapshot is None or snapshot.dashboard is None:
            self._update_context("No active project.")
            return
        match = next(
            (row for row in snapshot.artifacts if str(row.get("artifact_id", "")) == artifact_id),
            None,
        )
        if match is None:
            self._update_context(f"Artifact '{artifact_id}' is not in the current snapshot.")
            return
        version_value = match.get("version", 1)
        version = version_value if isinstance(version_value, int) else int(str(version_value))
        detail = self.gateway.inspect_artifact(
            artifact_id,
            str(match.get("phase", "")),
            version,
            snapshot.dashboard.project_id,
        )
        self.selected_artifact = detail
        self.reader = build_artifact_reader(
            detail,
            comments=snapshot.comments,
            validation=snapshot.validation,
        )
        self.selected_target = TargetSelection(
            target_type="artifact",
            target_id=detail.artifact_id,
            phase=detail.phase,
            source="artifact_command",
            detail={
                "artifact_id": detail.artifact_id,
                "artifact_type": detail.artifact_type,
                "phase": detail.phase,
                "version": detail.version,
                "status": detail.status,
            },
        )
        self.action_open_tab("assets")
        self._render_reader(self.reader)
        self._update_context(self._reader_context(self.reader))

    def _open_scene(self, scene_id: str) -> None:
        snapshot = self.snapshot
        if snapshot is None or snapshot.dashboard is None:
            self._update_context("No active project.")
            return
        for artifact_row in snapshot.artifacts:
            artifact_id = str(artifact_row.get("artifact_id", ""))
            phase = str(artifact_row.get("phase", ""))
            version_value = artifact_row.get("version", 1)
            version = version_value if isinstance(version_value, int) else int(str(version_value))
            try:
                detail = self.gateway.inspect_artifact(
                    artifact_id,
                    phase,
                    version,
                    snapshot.dashboard.project_id,
                )
            except (ServiceError, ValueError, FileNotFoundError):
                continue
            reader = build_artifact_reader(
                detail,
                comments=snapshot.comments,
                validation=snapshot.validation,
                scene_id=scene_id,
            )
            if reader.metadata.get("scene_id") == scene_id:
                self.selected_artifact = detail
                self.reader = reader
                self.selected_target = TargetSelection(
                    target_type="scene",
                    target_id=scene_id,
                    phase=detail.phase,
                    source="scene_command",
                    detail=dict(reader.metadata),
                )
                self.action_open_tab("scenes")
                self._render_reader(reader)
                self.query_one("#scene_reader", Static).update(self._reader_context(reader))
                self._update_context(self._reader_context(reader))
                return
        self._update_context(f"Scene '{scene_id}' was not found in current artifacts.")

    def _comment_from_command(self, payload: str) -> None:
        parts = [part.strip() for part in payload.split("|", maxsplit=1)]
        if len(parts) != 2 or not all(parts):
            self._update_context("Use: comment <target_id> | <what should change>")
            return
        target_id, note = parts
        selection = self._find_selection_for_target(target_id)
        self.selected_target = selection
        if not self.active_project_id:
            self._update_context("No active project.")
            return
        comment = self.gateway.add_operator_comment(
            OperatorCommentRequest(
                target_type=selection.target_type,
                target_id=selection.target_id,
                phase=selection.phase,
                source="tui_command",
                body=note,
            ),
            self.active_project_id,
        )
        self._update_context(
            "Comment stored\n\n"
            f"id: {comment.comment_id}\n"
            f"target: {comment.target_type} {comment.target_id}\n"
            f"body: {comment.body}"
        )
        self.action_refresh()

    def _filter_matrix(self, query: str) -> None:
        self.matrix_filter = "" if query.lower() in {"clear", "all", "*"} else query
        self.action_open_tab("matrix")
        if self.snapshot is not None:
            self._render_matrix(self.snapshot)
            rows = self._table_rows.get("matrix_table", [])
            self._update_context(
                f"Matrix filter: {self.matrix_filter or 'all'}\n"
                f"Visible rows: {len(rows)}\n\n"
                "Examples: matrix blocking, matrix warning, matrix phase:script, "
                "matrix scene:SC_004, matrix clear"
            )

    def _pivot_matrix(self, field: str) -> None:
        self.matrix_filter = self.matrix_filter
        self._matrix_pivot = field or "status"
        self.action_open_tab("matrix")
        if self.snapshot is not None:
            self._render_matrix(self.snapshot)
            self._update_context(
                "Matrix Pivot\n\n"
                f"field: {self._matrix_pivot_field()}\n"
                f"rows: {len(self._table_rows.get('matrix_pivot_table', []))}\n\n"
                "Select a pivot row to apply its filter command."
            )

    def _dashboard_command(self, metric: str) -> None:
        normalized = metric.strip().lower()
        if normalized in {"blocker", "blockers", "blocked"}:
            self._filter_validation(severity="blocking")
            return
        if normalized in {"warning", "warnings"}:
            self._filter_validation(severity="warning")
            return
        if normalized in {"provider", "providers"}:
            self.action_open_tab("providers")
            return
        if normalized in {"comment", "comments"}:
            self.action_open_tab("review")
            return
        if normalized in {"phase", "current"} and self.snapshot and self.snapshot.dashboard:
            self._show_phase_detail(self.snapshot.dashboard.current_phase)
            return
        self.action_open_tab("dashboard")
        self._update_context(
            "Dashboard commands\n\n"
            "dashboard blockers, dashboard warnings, dashboard providers, "
            "dashboard comments, dashboard phase"
        )

    def _matrix_pivot_field(self) -> str:
        return getattr(self, "_matrix_pivot", "status")

    def _open_review_issue_by_id(self, issue_id: str) -> None:
        row = next(
            (
                item
                for item in self._table_rows.get("review_issue_table", [])
                if str(item.get("issue_id", "")) == issue_id
            ),
            None,
        )
        if row is None:
            self._update_context(f"Review issue '{issue_id}' was not found.")
            self.action_open_tab("review")
            return
        self._open_review_issue(row)

    def _open_review_issue(self, row: dict[str, object]) -> None:
        target_id = str(row.get("target_id", ""))
        target_type = str(row.get("target_type", "review_issue"))
        self.selected_target = TargetSelection(
            target_type=target_type,
            target_id=target_id,
            phase=self.snapshot.review.phase if self.snapshot and self.snapshot.review else "",
            source="review_issue",
            detail=row,
        )
        self.query_one("#comment_input", Input).value = str(row.get("message", ""))
        if target_type in {"scene", "artifact"} and target_id:
            self._open_target(target_id)
        self._update_context(
            "Review Issue\n\n"
            f"id: {row.get('issue_id', '')}\n"
            f"severity: {row.get('severity', '')}\n"
            f"target: {target_type} {target_id}\n"
            f"message: {row.get('message', '')}\n\n"
            "The Review comment field has been prefilled for a targeted note."
        )

    def _show_thread(self, target_id: str) -> None:
        snapshot = self.snapshot
        if snapshot is None:
            self._update_context("No snapshot loaded.")
            return
        comments = [comment for comment in snapshot.comments if comment.target_id == target_id]
        self.action_open_tab("review")
        if not comments:
            self.selected_target = self._find_selection_for_target(target_id)
            self._update_context(f"No comment thread for '{target_id}'.")
            return
        latest = max(comments, key=lambda comment: comment.created_at)
        self.selected_target = TargetSelection(
            target_type=latest.target_type,
            target_id=latest.target_id,
            phase=latest.phase,
            source="comment_thread",
            detail={"comment_count": len(comments), "latest": latest.body},
        )
        self._update_context(
            "Comment Thread\n\n"
            f"target: {latest.target_type} {latest.target_id}\n"
            f"open: {len([comment for comment in comments if not comment.resolved])}\n\n"
            + "\n".join(
                f"- {comment.created_at} {comment.source}: {comment.body}"
                for comment in comments[:12]
            )
        )

    def _draft_for_target(self, payload: str) -> None:
        parts = [part.strip() for part in payload.split("|", maxsplit=1)]
        if len(parts) != 2 or not all(parts):
            self._update_context("Use: draft <target_id> | <revision note>")
            self.action_open_tab("review")
            return
        target_id, note = parts
        self.selected_target = self._find_selection_for_target(target_id)
        self.query_one("#comment_input", Input).value = note
        self.action_open_tab("review")
        self._update_context(
            "Draft Ready\n\n"
            f"target: {self.selected_target.target_type} {self.selected_target.target_id}\n"
            f"note: {note}\n\n"
            "Press r to request revision or Add Comment to store it."
        )

    def _show_phase_detail(self, phase: str, *, open_tab: bool = True) -> None:
        snapshot = self.snapshot
        if snapshot is None:
            self._update_context("No snapshot loaded.")
            return
        phase_id = phase.strip()
        if not phase_id:
            self._update_context("Use: phase <phase>")
            return
        detail = build_phase_detail(
            phase_id,
            dashboard=snapshot.dashboard,
            artifacts=snapshot.artifacts,
            validation=snapshot.validation,
        )
        if open_tab:
            self.action_open_tab("graph")
        self.query_one("#graph_phase_detail", Static).update(
            "\n".join(
                [
                    f"Phase: {detail.phase}",
                    f"Status: {detail.status or 'unknown'}",
                    detail.summary,
                    f"Blockers: {len(detail.blockers)}",
                    f"Commands: {', '.join(detail.suggested_commands) or 'none'}",
                ]
            )
        )
        self._set_table(
            "#graph_artifact_table",
            ["artifact_id", "artifact_type", "phase", "version", "status"],
            detail.artifacts,
        )
        if open_tab:
            self.selected_target = TargetSelection(
                target_type="graph_phase",
                target_id=detail.phase,
                phase=detail.phase,
                source="phase_command",
                detail={
                    "status": detail.status,
                    "artifact_count": len(detail.artifacts),
                    "blockers": detail.blockers,
                    "suggested_commands": detail.suggested_commands,
                },
            )
            self._update_context(self._phase_context(detail))

    def _open_next_action(self) -> None:
        snapshot = self.snapshot
        dashboard = snapshot.dashboard if snapshot else None
        if dashboard is None:
            self._update_context("No active project.")
            return
        next_action = dashboard.next_action
        if next_action == "present_review_package" or dashboard.status == "awaiting_review":
            self.action_open_tab("review")
            return
        if dashboard.has_blockers:
            self._filter_validation(severity="blocking")
            return
        self._show_phase_detail(dashboard.current_phase)

    def _fill_command(self, command: str) -> None:
        if not command:
            return
        palette = self.query_one("#command_palette", Input)
        palette.value = command
        if "open" not in palette.classes:
            palette.add_class("open")
        palette.focus()
        self._update_command_palette_intelligence(command)
        label = "Command template" if "<" in command and ">" in command else "Command ready"
        self._update_context(f"{label}\n\n{command}")

    def _validation_command(self, query: str) -> None:
        normalized = query.strip().lower()
        if normalized in {"clear", "all", "*"}:
            self._filter_validation()
            return
        if normalized in {"blocking", "blocked", "failed", "fail"}:
            self._filter_validation(severity="blocking")
            return
        self._filter_validation(validator_id=query.strip())

    def _filter_validation(self, *, validator_id: str = "", severity: str = "") -> None:
        self.action_open_tab("validation")
        snapshot = self.snapshot
        if snapshot is None:
            return
        rows = validation_issue_rows(
            snapshot.validation,
            validator_id=validator_id,
            severity=severity,
        )
        self._set_table(
            "#validation_table",
            ["severity", "validator", "target", "scene", "message"],
            rows,
        )
        filter_label = validator_id or severity or "all"
        self._update_context(
            f"Validation filter: {filter_label}\n"
            f"Visible issues: {len(rows)}\n\n"
            "Use fix <target> to draft a targeted note, or open <target> to inspect."
        )

    def _start_fix(self, target_id: str) -> None:
        snapshot = self.snapshot
        if snapshot is None:
            self._update_context("No snapshot loaded.")
            return
        suggestion = next(
            (
                item
                for item in build_validation_fix_suggestions(snapshot.validation)
                if item.target_id == target_id
            ),
            None,
        )
        if suggestion is None:
            self._update_context(f"No validation fix suggestion for '{target_id}'.")
            return
        self.query_one("#comment_input", Input).value = format_fix_draft(suggestion)
        self.selected_target = TargetSelection(
            target_type=suggestion.target_type,
            target_id=suggestion.target_id,
            phase=snapshot.validation.phase if snapshot.validation else "",
            source="validation_fix",
            detail={
                "severity": suggestion.severity,
                "validator": suggestion.validator_id,
                "message": suggestion.message,
                "command": suggestion.command,
            },
        )
        self._open_target(suggestion.target_id)
        self._update_context(
            "Fix Draft\n\n"
            f"target: {suggestion.target_type} {suggestion.target_id}\n"
            f"validator: {suggestion.validator_id}\n"
            f"severity: {suggestion.severity}\n"
            f"note: {suggestion.message}\n\n"
            "The Review comment field has been prefilled. Press r to request revision "
            "or Add Comment to store it."
        )

    def _open_target(self, target_id: str) -> None:
        selection = self._find_selection_for_target(target_id)
        self.selected_target = selection
        if selection.target_type == "artifact":
            self._open_artifact(selection.target_id)
            return
        scene_like = selection.target_type in {"scene", "scene_script", "scene_issue"}
        if scene_like or target_id.startswith(("SC_", "s_", "scene_")):
            self._open_scene(selection.target_id)
            return
        self._update_context(format_selection_detail(selection))

    def _reader_command(self, payload: str) -> None:
        normalized = payload.strip().lower()
        rows = self._table_rows.get("reader_index_table", [])
        if not rows:
            self._update_context("No reader index loaded.")
            return
        current_id = self.selected_target.target_id if self.selected_target else ""
        index = next(
            (idx for idx, row in enumerate(rows) if str(row.get("target_id", "")) == current_id),
            -1,
        )
        if normalized in {"next", "down"}:
            next_index = 0 if index < 0 else min(index + 1, len(rows) - 1)
            self._open_reader_index(rows[next_index])
            return
        if normalized in {"prev", "previous", "up"}:
            prev_index = len(rows) - 1 if index < 0 else max(index - 1, 0)
            self._open_reader_index(rows[prev_index])
            return
        if normalized in {"index", "outline"}:
            self.action_open_tab("assets")
            self._update_context(f"Reader index loaded: {len(rows)} row(s).")
            return
        self._update_context("Reader commands: reader next, reader prev, reader index")

    def _open_reader_index(self, row: dict[str, object]) -> None:
        target_id = str(row.get("target_id", ""))
        target_type = str(row.get("target_type", ""))
        if target_type == "scene" and target_id:
            self._open_scene(target_id)
            return
        self._open_reader_link(target_id)

    def _open_reader_link(self, target_id: str) -> None:
        rows = self._table_rows.get("reader_link_table", [])
        row = next(
            (item for item in rows if str(item.get("target_id", "")) == target_id),
            None,
        )
        if row is not None:
            command = str(row.get("command", ""))
            if command and not command.startswith("link "):
                self._run_command(command)
                return
        self.selected_target = TargetSelection(target_type="reader_link", target_id=target_id)
        self._update_context(f"Reader link\n\n{target_id or 'unknown'}")

    def _find_selection_for_target(self, target_id: str) -> TargetSelection:
        for table_id, rows in self._table_rows.items():
            for row in rows:
                selection = selection_from_row(table_id, row)
                if selection.target_id == target_id:
                    return selection
        return TargetSelection(target_type="operator_note", target_id=target_id)

    def _try_load_artifact_detail(self, selection: TargetSelection) -> None:
        snapshot = self.snapshot
        if snapshot is None or snapshot.dashboard is None:
            return
        phase = selection.phase
        if not phase:
            return
        version_value = selection.detail.get("version", 1)
        try:
            version = version_value if isinstance(version_value, int) else int(str(version_value))
            detail = self.gateway.inspect_artifact(
                selection.target_id,
                phase,
                version,
                snapshot.dashboard.project_id,
            )
        except (ServiceError, ValueError, FileNotFoundError):
            return
        self.selected_artifact = detail
        self.reader = build_artifact_reader(
            detail,
            comments=snapshot.comments,
            validation=snapshot.validation,
        )
        self._update_context(
            f"{format_selection_detail(selection)}\n\n{self._reader_context(self.reader)}"
        )
        self._render_reader(self.reader)

    @staticmethod
    def _matrix_impact_context(impact: MatrixImpact) -> str:
        lines = [
            "Matrix Impact",
            "",
            impact.summary,
            "",
            "Suggested actions",
            *[f"- {action}" for action in impact.suggested_actions],
            "",
            "Linked comments",
            *[
                f"- {comment.target_type}:{comment.target_id} {comment.body}"
                for comment in impact.linked_comments
            ],
            "",
            "Linked validation",
            *[
                f"- {issue.get('severity', '')} {issue.get('message', '')}"
                for issue in impact.linked_validation
            ],
        ]
        return "\n".join(lines)

    @staticmethod
    def _phase_context(phase_detail: PhaseDetail) -> str:
        lines = [
            "Phase Detail",
            "",
            f"phase: {phase_detail.phase}",
            f"status: {phase_detail.status or 'unknown'}",
            "",
            "Blockers",
            *[f"- {blocker}" for blocker in phase_detail.blockers],
            "",
            "Suggested commands",
            *[f"- {command}" for command in phase_detail.suggested_commands],
        ]
        return "\n".join(lines)

    def _initialize_tables(self) -> None:
        for selector in (
            "#project_table",
            "#dashboard_artifacts",
            "#dashboard_kpi_table",
            "#dashboard_action_table",
            "#graph_table",
            "#graph_artifact_table",
            "#matrix_table",
            "#matrix_pivot_table",
            "#review_artifacts",
            "#review_checklist_table",
            "#review_issue_table",
            "#scene_table",
            "#asset_table",
            "#reader_index_table",
            "#reader_link_table",
            "#validation_table",
            "#validation_group_table",
            "#validation_fix_table",
            "#checkpoint_table",
            "#provider_table",
            "#audit_table",
            "#comment_table",
            "#comment_thread_table",
            "#command_suggestion_table",
            "#command_help_table",
        ):
            table = self.query_one(selector, DataTable)
            table.cursor_type = "row"
            table.zebra_stripes = True

    def _set_table(
        self,
        selector: str,
        columns: list[str],
        rows: Iterable[Mapping[str, object]],
    ) -> None:
        table = self.query_one(selector, DataTable)
        table.clear(columns=True)
        table.add_columns(*columns)
        row_list = [dict(row) for row in rows]
        self._table_rows[selector.removeprefix("#")] = row_list
        for row in row_list:
            table.add_row(*[self._cell(row.get(column, "")) for column in columns])

    def _update_context(self, text: str) -> None:
        self.query_one("#context_panel", Static).update(text)

    def _render_reader(self, reader: ReaderView) -> None:
        self._set_table(
            "#reader_index_table",
            ["order", "target_id", "target_type", "heading", "command"],
            build_reader_index_rows(self.selected_artifact),
        )
        self._set_table(
            "#reader_link_table",
            ["kind", "target_id", "status", "detail", "command"],
            build_reader_link_rows(reader),
        )
        self.query_one("#reader_title", Static).update(f"{reader.title}\n{reader.subtitle}")
        self.query_one("#reader_outline", Static).update(
            "Outline\n" + ("\n".join(reader.outline[:30]) or "No outline.")
        )
        self.query_one("#reader_body", Static).update("Body\n" + (reader.body or "No body."))
        self.query_one("#reader_metadata", Static).update("Metadata\n" + pretty(reader.metadata))
        self.query_one("#reader_links", Static).update(
            "Linked Comments\n"
            + (
                "\n".join(
                    f"- {comment.target_type}:{comment.target_id} {comment.body}"
                    for comment in reader.linked_comments
                )
                or "None"
            )
            + "\n\nLinked Validation\n"
            + (
                "\n".join(
                    f"- {issue.get('severity', '')} {issue.get('message', '')}"
                    for issue in reader.linked_validation
                )
                or "None"
            )
        )

    @staticmethod
    def _reader_context(reader: ReaderView) -> str:
        return "\n".join(
            [
                "Reader",
                "",
                reader.title,
                reader.subtitle,
                "",
                "Outline",
                *reader.outline[:12],
                "",
                "Linked comments",
                *[
                    f"- {comment.target_type}:{comment.target_id} {comment.body}"
                    for comment in reader.linked_comments[:8]
                ],
                "",
                "Linked validation",
                *[
                    f"- {issue.get('severity', '')} {issue.get('message', '')}"
                    for issue in reader.linked_validation[:8]
                ],
            ]
        )

    @staticmethod
    def _cell(value: object) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        if isinstance(value, dict):
            return pretty(value)
        return str(value)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the Textual TUI."""
    parser = argparse.ArgumentParser(description="Run the film pipeline Textual cockpit.")
    parser.add_argument("--create", action="store_true", help="Open the create-project command.")
    args = parser.parse_args(argv)
    FilmCockpitApp(start_create=args.create).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
