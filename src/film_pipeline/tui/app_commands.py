"""Command palette dispatch, navigation, filtering, comments, and asset ops mixin."""

from __future__ import annotations

from textual.widgets import Input, Static

from film_pipeline.app.services.errors import ServiceError
from film_pipeline.app.services.models import (
    ArtifactDetail,
    OperatorCommentRequest,
    ProjectCreateRequest,
    ProjectListItem,
)
from film_pipeline.tui.app_base import AppCockpitBase
from film_pipeline.tui.view_models import (
    ReaderView,
    TargetSelection,
    build_artifact_reader,
    build_phase_detail,
    build_validation_fix_suggestions,
    format_fix_draft,
    format_selection_detail,
    format_targeted_revision_note,
    selection_from_row,
    validation_issue_rows,
)


def _asset_line(asset: dict[str, object]) -> str:
    return (
        f"- {asset.get('asset_id', '')} | "
        f"{asset.get('kind', '')} | "
        f"shot={asset.get('shot_id', '') or 'none'} | "
        f"take={asset.get('take', '')} | "
        f"active={asset.get('active', '')} | "
        f"{asset.get('path', '')}"
    )


class AppCommandsMixin(AppCockpitBase):
    """Command palette parsing/dispatch and navigation behavior for the cockpit app."""

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
        if normalized in {"create", "new", "new project"}:
            self.action_new_project()
            return
        if normalized in {"validate", "run validation", "validation run"}:
            self.action_run_validation()
            return
        if normalized in {"idea", "revise idea", "edit idea"}:
            self.action_revise_idea()
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
            "guide": "guide",
            "open guide": "guide",
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
        if normalized.startswith("project "):
            self._switch_project(command.split(maxsplit=1)[1].strip())
            return
        if normalized.startswith("projects "):
            self._filter_projects(command.split(maxsplit=1)[1].strip())
            return
        if normalized.startswith("create "):
            self._create_project_from_command(command.removeprefix("create ").strip())
            return
        if normalized.startswith("artifact "):
            self._open_artifact(command.split(maxsplit=1)[1].strip())
            return
        if normalized.startswith("asset "):
            self._asset_command(command.removeprefix("asset ").strip())
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
            "draft <target> | <note>, asset change <id> | <note>, project <id>, "
            "projects test, validator <id>, fix <target>."
        )

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
                project_kind="production",
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
        scene_readers: list[tuple[ArtifactDetail, ReaderView]] = []
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
                scene_readers.append((detail, reader))
        if scene_readers:
            first_detail = scene_readers[0][0]
            combined = self._combine_scene_readers(
                scene_id,
                scene_readers,
                assets=snapshot.assets,
            )
            self.selected_artifact = first_detail
            self.reader = combined
            self.selected_target = TargetSelection(
                target_type="scene",
                target_id=scene_id,
                phase=first_detail.phase,
                source="scene_command",
                detail=dict(combined.metadata),
            )
            self.action_open_tab("scenes")
            self._render_reader(combined)
            self.query_one("#scene_reader", Static).update(self._reader_context(combined))
            self._update_context(self._reader_context(combined))
            return
        self._update_context(f"Scene '{scene_id}' was not found in current artifacts.")

    @staticmethod
    def _combine_scene_readers(
        scene_id: str,
        readers: list[tuple[ArtifactDetail, ReaderView]],
        *,
        assets: list[dict[str, object]],
    ) -> ReaderView:
        first_reader = readers[0][1]
        artifact_ids = [detail.artifact_id for detail, _reader in readers]
        outline: list[str] = []
        body_sections: list[str] = []
        comments_by_id = {}
        validation_by_key: dict[tuple[str, str, str], dict[str, object]] = {}
        for detail, reader in readers:
            label = f"{detail.artifact_id}:v{detail.version}"
            outline.append(label)
            outline.extend(f"  {line}" for line in reader.outline)
            body_sections.append(f"## {label}\n{reader.body}")
            for comment in reader.linked_comments:
                comments_by_id[comment.comment_id] = comment
            for issue in reader.linked_validation:
                key = (
                    str(issue.get("severity", "")),
                    str(issue.get("validator_id", "")),
                    str(issue.get("message", "")),
                )
                validation_by_key[key] = issue
        scene_assets = [asset for asset in assets if str(asset.get("scene_id", "")) == scene_id]
        if scene_assets:
            outline.append("assets")
            body_sections.append(
                "## Manifest Assets\n" + "\n".join(_asset_line(asset) for asset in scene_assets)
            )
        metadata = {
            "scene_id": scene_id,
            "artifact_ids": artifact_ids,
            "artifact_count": len(artifact_ids),
            "asset_count": len(scene_assets),
            "phase": first_reader.metadata.get("phase", ""),
            "status": first_reader.metadata.get("status", ""),
        }
        return ReaderView(
            title=first_reader.title,
            subtitle=f"scene {scene_id} across {len(artifact_ids)} artifact(s)",
            outline=outline,
            body="\n\n".join(body_sections),
            metadata=metadata,
            linked_comments=list(comments_by_id.values()),
            linked_validation=list(validation_by_key.values()),
        )

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

    def _switch_project(self, project_id: str) -> None:
        if not project_id:
            self._update_context("Use: project <project_id>")
            return
        try:
            dashboard = self.gateway.set_active_project(project_id)
        except (ServiceError, ValueError, FileNotFoundError) as exc:
            self._update_context(
                f"Project '{project_id}' is listed but cannot be opened yet.\n\n{exc}\n\n"
                "Discovered projects need runtime recovery support before they can be active."
            )
            return
        self.active_project_id = dashboard.project_id
        self._update_context(
            f"Opened project: {dashboard.project_id}\n"
            f"phase: {dashboard.current_phase or 'none'}\n"
            f"status: {dashboard.status}"
        )
        self.action_refresh()

    def _filter_projects(self, value: str) -> None:
        normalized = value.strip().lower()
        if normalized not in {"production", "test", "all"}:
            self._update_context("Use: projects production, projects test, or projects all")
            return
        self.project_filter = normalized
        if self.snapshot is not None:
            self._render_projects(self.snapshot.projects)
        self._update_context(
            f"Project lane: {self.project_filter}\n\n"
            "Select a row or run project <id> to open a loaded project."
        )

    def _asset_command(self, payload: str) -> None:
        normalized = payload.strip().lower()
        if normalized.startswith("review "):
            self._request_asset_review(payload.removeprefix("review ").strip())
            return
        if normalized.startswith("change "):
            self._request_asset_revision("change", payload.removeprefix("change ").strip())
            return
        if normalized.startswith("extend "):
            self._request_asset_revision("extend", payload.removeprefix("extend ").strip())
            return
        self._update_context(
            "Asset commands\n\n"
            "asset review <artifact_id>\n"
            "asset change <artifact_id> | <note>\n"
            "asset extend <artifact_id> | <note>"
        )

    def _request_asset_review(self, artifact_id: str) -> None:
        snapshot = self.snapshot
        if snapshot is None or snapshot.dashboard is None:
            self._update_context("No active project.")
            return
        artifact = self._artifact_row(artifact_id)
        if artifact is None:
            self._update_context(f"Artifact '{artifact_id}' is not in the current snapshot.")
            return
        comment = self.gateway.add_operator_comment(
            OperatorCommentRequest(
                target_type="artifact",
                target_id=artifact_id,
                phase=str(artifact.get("phase", "")),
                source="tui_asset_action",
                body="[asset_action=review] Please review this artifact for production use.",
            ),
            snapshot.dashboard.project_id,
        )
        self.selected_target = TargetSelection(
            target_type="artifact",
            target_id=artifact_id,
            phase=str(artifact.get("phase", "")),
            source="asset_review",
            detail=artifact,
        )
        self._update_context(
            "Asset Review Requested\n\n"
            f"artifact: {artifact_id}\n"
            f"comment: {comment.comment_id}\n\n"
            "The request is stored as an operator comment and appears in Review threads."
        )
        self.action_refresh()

    def _request_asset_revision(self, action: str, payload: str) -> None:
        parts = [part.strip() for part in payload.split("|", maxsplit=1)]
        if len(parts) != 2 or not all(parts):
            self._update_context(f"Use: asset {action} <artifact_id> | <note>")
            return
        artifact_id, note = parts
        artifact = self._artifact_row(artifact_id)
        if artifact is None:
            self._update_context(f"Artifact '{artifact_id}' is not in the current snapshot.")
            return
        self.selected_target = TargetSelection(
            target_type="artifact",
            target_id=artifact_id,
            phase=str(artifact.get("phase", "")),
            source=f"asset_{action}",
            detail=artifact,
        )
        self.query_one("#comment_input", Input).value = note
        if not self.active_project_id:
            self._update_context("No active project.")
            return
        result = self.gateway.request_revision(
            format_targeted_revision_note(
                self.selected_target,
                f"[asset_action={action}] {note}",
            ),
            self.active_project_id,
        )
        self._update_context(
            f"Asset {action.title()} Requested\n\n"
            f"artifact: {artifact_id}\n"
            f"phase: {artifact.get('phase', '')}\n"
            f"current phase: {result.current_phase}\n\n"
            "The request was submitted through the revision path."
        )
        self.action_refresh()

    def _artifact_row(self, artifact_id: str) -> dict[str, object] | None:
        snapshot = self.snapshot
        if snapshot is None:
            return None
        return next(
            (row for row in snapshot.artifacts if str(row.get("artifact_id", "")) == artifact_id),
            None,
        )

    def _visible_projects(self, projects: list[ProjectListItem]) -> list[ProjectListItem]:
        if self.project_filter == "all":
            return projects
        visible = [project for project in projects if project.project_kind == self.project_filter]
        return visible or projects

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
