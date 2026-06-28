"""Action keybinding handlers and Textual event handlers mixin."""

from __future__ import annotations

from textual.widgets import Button, DataTable, Input, TabbedContent

from film_pipeline.app.services.errors import ServiceError
from film_pipeline.app.services.models import OperatorCommentRequest, ProjectCreateRequest
from film_pipeline.tui.app_base import AppCockpitBase
from film_pipeline.tui.screens import NewProjectScreen, ReviseIdeaScreen
from film_pipeline.tui.view_models import (
    TargetSelection,
    build_matrix_impact,
    format_selection_detail,
    format_targeted_revision_note,
    selection_from_row,
)


class AppActionsMixin(AppCockpitBase):
    """Keybinding actions and Textual event handlers for the cockpit app."""

    def on_mount(self) -> None:
        """Initialize tables and load the first snapshot."""
        self.title = "LangGraph Film Studio Cockpit"
        self.sub_title = "operator cockpit"
        self._initialize_tables()
        self.action_refresh()
        if self.start_create:
            self.action_new_project()

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
        if self.pending_confirmation == "approve":
            self._approve_phase_now()
            return
        self._prepare_approval_confirmation()

    def action_confirm_approval(self) -> None:
        """Commit a prepared approval confirmation."""
        self._confirm_approval()

    def action_new_project(self) -> None:
        """Open the New Project modal form."""
        self.push_screen(NewProjectScreen(), self._on_new_project_result)

    def _on_new_project_result(self, request: ProjectCreateRequest | None) -> None:
        """Create the project requested by the modal form."""
        if request is None:
            return
        try:
            active_mode = self.gateway.set_runtime_mode(request.runtime_mode)
            result = self.gateway.create_project(request)
        except (ServiceError, ValueError, FileNotFoundError) as exc:
            # Refresh first (a partial create may have registered the project),
            # then set the error last so it is not overwritten by the render.
            self.action_refresh()
            self._update_context(
                "Create Project failed\n\n"
                f"{exc}\n\n"
                "For real mode, confirm API credentials are configured, then retry."
            )
            return
        self.active_project_id = result.project_id
        self._update_context(
            f"{result.message or 'Project created.'}\n"
            f"project: {result.project_id}\n"
            f"phase: {result.current_phase or 'none'}\n"
            f"runtime mode: {active_mode}"
        )
        self.action_open_tab("dashboard")
        self.action_refresh()

    def action_revise_idea(self) -> None:
        """Open the Revise Idea modal for the active project."""
        if not self.active_project_id:
            self._update_context("No active project. Create one first with n.")
            return
        current_idea = ""
        snapshot = self.snapshot
        if snapshot and snapshot.dashboard:
            current_idea = str(getattr(snapshot.dashboard, "idea", "") or "")
        self.push_screen(
            ReviseIdeaScreen(project_id=self.active_project_id, current_idea=current_idea),
            self._on_revise_idea_result,
        )

    def _on_revise_idea_result(self, idea: str | None) -> None:
        """Submit a revised idea and re-run intake."""
        if idea is None:
            return
        try:
            result = self.gateway.submit_idea(self.active_project_id, idea)
        except (ServiceError, ValueError, FileNotFoundError) as exc:
            self._update_context(f"Revise idea failed\n\n{exc}")
            return
        self._update_context(
            f"{result.message or 'Idea submitted.'}\nCurrent phase: {result.current_phase}"
        )
        self.action_refresh()

    def action_run_validation(self) -> None:
        """Run validators on demand against the active project's current phase."""
        if not self.active_project_id:
            self._update_context("No active project.")
            return
        try:
            workspace = self.gateway.run_validation(self.active_project_id)
        except (ServiceError, ValueError, FileNotFoundError) as exc:
            self._update_context(f"Run validation failed\n\n{exc}")
            return
        # Refresh first so the validation tables reflect the fresh run, then set
        # the summary last so it is not overwritten by the tab-context render.
        self.action_refresh()
        self.action_open_tab("validation")
        self._update_context(
            "Validation complete\n\n"
            f"phase: {workspace.phase or 'none'}\n"
            f"blocking: {len(workspace.blocking_issues)}\n"
            f"warnings: {len(workspace.non_blocking_issues)}\n"
            f"reports: {len(workspace.reports)}\n\n"
            "Fix blocking issues before approving, then run validation again."
        )

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
        elif button_id == "confirm_approve_button":
            self.action_confirm_approval()
        elif button_id == "revision_button":
            self.action_request_revision()
        elif button_id == "comment_button":
            self.action_add_comment()
        elif button_id == "new_project":
            self.action_new_project()
        elif button_id == "revise_idea_button":
            self.action_revise_idea()
        elif button_id == "run_validation_button":
            self.action_run_validation()

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
        if table_id == "asset_action_table":
            self._fill_command(str(row.get("command", "")))
        if table_id == "project_table":
            self._switch_project(str(row.get("project", "")))
        if table_id == "guide_table":
            self._show_guide_step(row)
        if table_id == "scene_table" and selection.target_id:
            self._open_scene(selection.target_id)
            return
        if selection.target_type == "artifact" and selection.target_id:
            self._open_artifact(selection.target_id)

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
            "Click Confirm Approval, press y, or press a again to continue."
        )

    def _confirm_approval(self) -> None:
        if self.pending_confirmation != "approve":
            self._update_context("No pending approval confirmation. Run 'approve' first.")
            return
        self._approve_phase_now()
