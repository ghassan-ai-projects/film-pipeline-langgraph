"""Snapshot loading and table/panel rendering mixin for the cockpit app."""

from __future__ import annotations

from textual.widgets import Input, Static, TabbedContent

from film_pipeline.app.services.errors import ServiceError
from film_pipeline.app.services.models import DashboardSummary, ProjectListItem
from film_pipeline.tui.app_base import AppCockpitBase
from film_pipeline.tui.formatting import pretty
from film_pipeline.tui.view_models import (
    GRAPH_PHASES,
    CockpitSnapshot,
    MatrixImpact,
    PhaseDetail,
    PhaseReading,
    ReaderView,
    build_asset_action_rows,
    build_command_help_rows,
    build_command_options,
    build_command_suggestions,
    build_command_validation,
    build_comment_thread_rows,
    build_dashboard_action_rows,
    build_dashboard_kpi_rows,
    build_graph_rows,
    build_matrix_pivot_rows,
    build_matrix_rows,
    build_phase_reading,
    build_reader_index_rows,
    build_reader_link_rows,
    build_review_checklist_rows,
    build_review_issue_rows,
    build_scene_rows,
    build_validation_fix_suggestions,
    build_validation_groups,
    filter_command_suggestions,
    filter_matrix_rows,
    summarize_attention,
    validation_issue_rows,
)


class AppRenderMixin(AppCockpitBase):
    """Rendering and snapshot-loading behavior for the cockpit app."""

    def _load_snapshot(self) -> CockpitSnapshot:
        projects = self.gateway.list_projects()
        visible_projects = self._visible_projects(projects)
        dashboard = self._load_dashboard(visible_projects)
        project_id = dashboard.project_id if dashboard else None
        review = self.gateway.get_review_workspace(project_id) if project_id else None
        validation = self.gateway.get_validation_workspace(project_id) if project_id else None
        artifacts = self.gateway.list_artifacts(project_id) if project_id else []
        artifacts = self._enrich_artifact_rows(artifacts, project_id) if project_id else artifacts
        assets = self.gateway.list_assets(project_id) if project_id else []
        generation = None
        if project_id:
            try:
                generation = self.gateway.get_generation_workspace(project_id)
            except (ServiceError, ValueError, FileNotFoundError, NotImplementedError):
                generation = None
        prompts = self._load_prompt_previews(dashboard, project_id)
        reading = self._load_phase_reading(dashboard, artifacts, prompts, project_id)
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
            assets=assets,
            generation=generation,
            reading=reading,
            prompts=prompts,
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
                projects=visible_projects,
                dashboard=dashboard,
                validation=validation,
                artifacts=artifacts,
                providers=providers,
            ),
        )

    def _load_prompt_previews(
        self,
        dashboard: DashboardSummary | None,
        project_id: str | None,
    ) -> list[dict[str, object]]:
        """Load per-shot prompt previews once the shot matrix exists."""
        if dashboard is None or not project_id:
            return []
        phases_with_prompts = {"shot_bible", "gen_planning", "generation", "qc"}
        if dashboard.current_phase not in phases_with_prompts:
            return []
        try:
            return self.gateway.preview_generation_prompts(project_id)
        except (ServiceError, ValueError, FileNotFoundError, NotImplementedError):
            return []

    def _load_phase_reading(
        self,
        dashboard: DashboardSummary | None,
        artifacts: list[dict[str, object]],
        prompts: list[dict[str, object]],
        project_id: str | None,
    ) -> PhaseReading | None:
        """Load the current phase's artifact bodies and build the reading."""
        if dashboard is None or not project_id or not dashboard.current_phase:
            return None
        phase = dashboard.current_phase
        bodies: dict[str, dict[str, object]] = {}
        for row in artifacts:
            if str(row.get("phase", "")) != phase:
                continue
            artifact_id = str(row.get("artifact_id", ""))
            if not artifact_id or artifact_id == "graph_state":
                continue
            version_value = row.get("version", 1)
            try:
                version = (
                    version_value if isinstance(version_value, int) else int(str(version_value))
                )
                detail = self.gateway.inspect_artifact(artifact_id, phase, version, project_id)
            except (ServiceError, ValueError, FileNotFoundError):
                continue
            bodies[artifact_id] = detail.body
        include_prompts = phase in {"gen_planning", "generation"}
        return build_phase_reading(
            phase,
            bodies,
            prompts=[dict(prompt) for prompt in prompts] if include_prompts else None,
        )

    def _enrich_artifact_rows(
        self,
        artifacts: list[dict[str, object]],
        project_id: str,
    ) -> list[dict[str, object]]:
        enriched: list[dict[str, object]] = []
        for artifact in artifacts:
            row = dict(artifact)
            artifact_id = str(row.get("artifact_id", ""))
            phase = str(row.get("phase", ""))
            version_value = row.get("version", 1)
            try:
                version = (
                    version_value if isinstance(version_value, int) else int(str(version_value))
                )
                detail = self.gateway.inspect_artifact(artifact_id, phase, version, project_id)
            except (ServiceError, ValueError, FileNotFoundError):
                enriched.append(row)
                continue
            scene_ids = [
                str(index_row.get("target_id", ""))
                for index_row in build_reader_index_rows(detail)
                if str(index_row.get("target_type", "")) == "scene"
                and str(index_row.get("target_id", ""))
            ]
            if scene_ids:
                row["scene_ids"] = sorted(set(scene_ids))
                row["scene_count"] = len(set(scene_ids))
            enriched.append(row)
        return enriched

    def _load_dashboard(self, projects: list[ProjectListItem]) -> DashboardSummary | None:
        if self.active_project_id:
            return self.gateway.get_dashboard(self.active_project_id)
        try:
            dashboard = self.gateway.get_dashboard(None)
            self.active_project_id = dashboard.project_id
            return dashboard
        except ServiceError:
            # Only auto-activate live, runtime-loaded projects. Folders merely
            # discovered on disk (status "discovered") require explicit opening
            # so the cockpit never boots into stale leftover state. Prefer the
            # project the operator touched most recently.
            live = [project for project in projects if project.status != "discovered"]
            if not live:
                return None
            most_recent = max(live, key=lambda project: project.last_updated_at)
            dashboard = self.gateway.set_active_project(most_recent.project_id)
            self.active_project_id = dashboard.project_id
            return dashboard

    def _render_snapshot(self, snapshot: CockpitSnapshot) -> None:
        dashboard = snapshot.dashboard
        self._render_projects(snapshot.projects)
        self._render_status(dashboard, snapshot.providers)
        self._render_dashboard(snapshot)
        self._render_graph(snapshot)
        self._render_generation(snapshot)
        self._render_matrix(snapshot)
        self._render_review(snapshot)
        self._render_scenes(snapshot)
        self._render_assets(snapshot)
        self._render_guide(snapshot)
        self._render_validation(snapshot)
        self._render_checkpoints(snapshot)
        self._render_providers(snapshot)
        self._render_audit(snapshot)
        self._render_command_options(snapshot)
        self._update_command_palette_intelligence(self.query_one("#command_palette", Input).value)
        self._context_for_tab(self.query_one("#tabs", TabbedContent).active or "dashboard")

    def _render_projects(self, projects: list[ProjectListItem]) -> None:
        visible_projects = self._visible_projects(projects)
        summary = (
            f"Lane: {self.project_filter} | all: {len(projects)} | visible: {len(visible_projects)}"
        )
        self.query_one("#project_filter", Static).update(
            f"{summary}\nCommands: projects production, projects test, projects all, project <id>"
        )
        rows = [
            {
                "project": project.project_id,
                "kind": project.project_kind,
                "phase": project.current_phase,
                "status": project.status,
                "review": "yes" if project.awaiting_review else "",
            }
            for project in visible_projects
        ]
        self._set_table("#project_table", ["project", "kind", "phase", "status", "review"], rows)

    def _render_status(
        self,
        dashboard: DashboardSummary | None,
        providers: list[dict[str, object]],
    ) -> None:
        busy = f"  ⏳ {self.busy_label}" if getattr(self, "busy_label", "") else ""
        if dashboard is None:
            text = f"No active project — press n to create one, or pick from Projects.{busy}"
        else:
            healthy = sum(
                1 for provider in providers if str(provider.get("status", "")) == "healthy"
            )
            phases = list(GRAPH_PHASES)
            phase = dashboard.current_phase
            position = f"{phases.index(phase) + 1}/{len(phases)}" if phase in phases else "—"
            next_hint = (
                "film complete 🎬"
                if dashboard.status == "complete"
                else self._humanize_action(dashboard.next_action)
            )
            text = (
                f"{dashboard.title}  |  phase {position}: {phase or 'not started'} "
                f"({dashboard.status or 'new'})  |  "
                f"{dashboard.runtime_mode or 'mock'} mode  |  "
                f"providers {healthy}/{len(providers)}  |  "
                f"next: {next_hint}{busy}"
            )
        self.query_one("#status_bar", Static).update(text)

    @staticmethod
    def _humanize_action(action: str) -> str:
        if not action:
            return "none"
        readable = {
            "wait_for_human": "review & approve (a)",
            "present_review_package": "review & approve (a)",
            "handle_blockers": "resolve blockers (open validation)",
        }
        return readable.get(action, action.replace("_", " "))

    def _render_dashboard(self, snapshot: CockpitSnapshot) -> None:
        dashboard = snapshot.dashboard
        if dashboard is None:
            self.query_one("#dashboard_summary", Static).update(
                "No active project.\n\n"
                "Press n to create a new film from an idea,\n"
                "or select an existing project on the left."
            )
            self.query_one("#attention_panel", Static).update("Create or select a project.")
            self._set_table("#dashboard_kpi_table", ["metric", "value", "state", "command"], [])
            self._set_table(
                "#dashboard_action_table",
                ["priority", "action", "status", "reason", "command"],
                [],
            )
            return
        summary = "\n".join(
            [
                f"Current phase: {dashboard.current_phase or 'none'}",
                f"Next action: {self._humanize_action(dashboard.next_action)}",
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

    def _render_graph(self, snapshot: CockpitSnapshot) -> None:
        dashboard = snapshot.dashboard
        if dashboard is None:
            self.query_one("#graph_phase_detail", Static).update("")
        else:
            self._show_phase_detail(dashboard.current_phase, open_tab=False)
        self._set_table(
            "#graph_table",
            ["step", "phase", "status", "next_action"],
            snapshot.graph_rows,
        )

    def _render_generation(self, snapshot: CockpitSnapshot) -> None:
        generation = snapshot.generation
        dashboard = snapshot.dashboard
        columns = ["shot_id", "status", "provider", "model", "polls", "cost_usd", "output", "error"]
        if generation is None or dashboard is None:
            self.query_one("#generation_summary", Static).update(
                "Generation turns approved shots into video clips.\n"
                "Approve the pipeline through gen_planning first, then plan a batch here."
            )
            self._set_table("#generation_table", columns, [])
            self.query_one("#generation_detail", Static).update("")
            return
        step_help = {
            "plan": "Press Run Generation (or G) to plan every shot in the matrix.",
            "approve_spend": "Batch is planned. Approve spend to authorize submission.",
            "start": "Spend approved. Start the batch to submit shots to the provider.",
            "poll": "Shots are generating. Poll to fetch finished clips.",
            "review_failures": "Some shots failed. Inspect errors below, then re-plan or revise.",
            "approve_phase": "All clips delivered. Approve the generation phase (a) to continue.",
        }
        summary = (
            f"Batch: {len(generation.rows)} shot(s) | provider {generation.provider} "
            f"({generation.model}) | est. cost ${generation.estimated_cost_usd:.2f}\n"
            f"planned {generation.planned} · approved {generation.submitted} · "
            f"running {generation.running} · done {generation.completed} · "
            f"failed {generation.failed}\n"
            f"Next: {step_help.get(generation.next_step, generation.next_step)}"
        )
        self.query_one("#generation_summary", Static).update(summary)
        self._set_table("#generation_table", columns, generation.rows)
        failures = [row for row in generation.rows if str(row.get("error", ""))]
        detail = ""
        if failures:
            detail = "Failures:\n" + "\n".join(
                f"- {row.get('shot_id', '')}: {row.get('error', '')}" for row in failures[:6]
            )
        elif generation.completed:
            detail = (
                f"{generation.completed} clip(s) delivered to the project asset tree.\n"
                "Open Assets (5) to inspect them."
            )
        elif snapshot.prompts:
            detail = "Select a shot row to read the exact prompt it will send."
        self.query_one("#generation_detail", Static).update(detail)

    def _show_generation_prompt(self, shot_id: str) -> None:
        """Show the full resolved prompt for a selected generation row."""
        snapshot = self.snapshot
        if snapshot is None or not shot_id:
            return
        match = next(
            (prompt for prompt in snapshot.prompts if str(prompt.get("shot_id", "")) == shot_id),
            None,
        )
        if match is None:
            self.query_one("#generation_detail", Static).update(
                f"No prompt preview available for {shot_id}."
            )
            return
        text = (
            f"[{shot_id}] {match.get('provider', '')} / {match.get('model', '')} · "
            f"{match.get('duration_seconds', '?')}s\n\n{match.get('prompt', '')}"
        )
        self.query_one("#generation_detail", Static).update(text)
        self._update_context(f"Generation Prompt\n\n{text}")

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
            self.query_one("#review_reading_body", Static).update(
                "Create a project and submit an idea; the phase output will be "
                "readable here before you approve it."
            )
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
                f"Review package: {review.phase or 'none'} | "
                f"Actions: {', '.join(review.available_actions) or 'none'} | "
                f"Open issues: {len(review.open_issues)}",
                f"Recommendation: {review.recommendation}",
            ]
        )
        self.query_one("#review_summary", Static).update(summary)
        self._render_reading_pane(snapshot.reading)
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
            "#comment_thread_table",
            ["target_id", "target_type", "open", "latest", "updated", "command"],
            thread_rows,
        )

    def _render_reading_pane(self, reading: PhaseReading | None) -> None:
        body = self.query_one("#review_reading_body", Static)
        if reading is None or not reading.sections:
            body.update(
                "Nothing to read yet for this phase.\n\n"
                "Artifacts appear here as soon as the phase produces them."
            )
            return
        body.update(reading.as_text())

    def _render_scenes(self, snapshot: CockpitSnapshot) -> None:
        self.query_one("#scene_summary", Static).update(
            "Scene workspace derives scene targets from artifacts, matrix rows, and validation.\n"
            "Select a row to read script, camera, references, assets, and linked issues."
        )
        self._set_table(
            "#scene_table",
            ["scene", "phase", "status", "validation", "action"],
            self._scene_rows(snapshot),
        )

    def _render_assets(self, snapshot: CockpitSnapshot) -> None:
        if snapshot.assets:
            self._set_table(
                "#asset_table",
                ["asset_id", "kind", "scene_id", "shot_id", "take", "active", "path"],
                snapshot.assets,
            )
        else:
            self._set_table(
                "#asset_table",
                ["artifact_id", "artifact_type", "phase", "version", "status"],
                snapshot.artifacts,
            )
        self._set_table(
            "#asset_action_table",
            ["artifact_id", "action", "phase", "purpose", "command"],
            build_asset_action_rows(snapshot.artifacts),
        )

    def _render_guide(self, snapshot: CockpitSnapshot) -> None:
        dashboard = snapshot.dashboard
        active = dashboard.project_id if dashboard else "none"
        rows = self._guide_rows(snapshot)
        done = len([row for row in rows if row.get("status") == "done"])
        blocked = len([row for row in rows if row.get("status") == "blocked"])
        current = len([row for row in rows if row.get("status") == "current"])
        self.query_one("#guide_summary", Static).update(
            "Validated mock-first path for a 1 minute film with a few clips.\n"
            f"Active project: {active}\n"
            f"Progress: {done}/6 done | current: {current} | blocked: {blocked}\n"
            "Use the command column to drive the cockpit. Approvals remain explicit."
        )
        self._set_table(
            "#guide_table",
            ["step", "status", "goal", "command", "evidence"],
            rows,
        )
        if rows:
            self._show_guide_step(rows[0], open_tab=False)

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
        if tab_id == "dashboard":
            self._update_context(
                "Dashboard\n\n"
                "Dense operating summary: phase, route, blockers, latest artifacts, "
                "and next action."
            )
        elif tab_id == "generate":
            generation = snapshot.generation
            if generation is None:
                self._update_context(
                    "Generate\n\nPlan, approve, and run the video generation batch here "
                    "once the pipeline reaches the generation phase."
                )
            else:
                self._update_context(
                    "Generate\n\n"
                    f"Next step: {generation.next_step}\n"
                    f"Rows: {len(generation.rows)} | running: {generation.running} | "
                    f"done: {generation.completed} | failed: {generation.failed}\n\n"
                    "Run Generation drives plan → spend → start → poll automatically."
                )
        elif tab_id == "ops":
            self._update_context(
                "Ops\n\nProvider health, checkpoint timeline, and the audit trail."
            )
        elif tab_id == "review" and snapshot.review is not None:
            self._update_context(
                "Review Context\n\n"
                f"{snapshot.review.recommendation}\n\n"
                "Read the phase output in the left pane, then approve (a, y) "
                "or write a note and revise (r).\n\n"
                "Deep links: scene <id>, artifact <id>, review issue <id>, "
                "thread <target>, draft <target> | <note>."
            )
        elif tab_id == "matrix":
            self._update_context(
                "Smart Matrix\n\n"
                "Rows merge artifacts and validation issues. Targets with blocking "
                "validation should be fixed before approval."
            )
        elif tab_id == "validation" and snapshot.validation is not None:
            self._update_context(pretty(snapshot.validation))
        elif tab_id == "guide":
            self._update_context(
                "Guide\n\n"
                "A-Z path: create a mock project, approve each review gate, inspect assets, "
                "validate blockers, then generate and review the resulting images."
            )
        else:
            self._update_context("Context updates with the active page and selected object.")

    def _scene_rows(self, snapshot: CockpitSnapshot) -> list[dict[str, object]]:
        rows = build_scene_rows(snapshot.matrix_rows, artifacts=snapshot.artifacts)
        seen = {str(row.get("scene", "")) for row in rows}
        if snapshot.dashboard is None:
            return rows
        for artifact_row in snapshot.artifacts:
            artifact_id = str(artifact_row.get("artifact_id", ""))
            phase = str(artifact_row.get("phase", ""))
            version_value = artifact_row.get("version", 1)
            try:
                version = (
                    version_value if isinstance(version_value, int) else int(str(version_value))
                )
                detail = self.gateway.inspect_artifact(
                    artifact_id,
                    phase,
                    version,
                    snapshot.dashboard.project_id,
                )
            except (ServiceError, ValueError, FileNotFoundError):
                continue
            for index_row in build_reader_index_rows(detail):
                scene_id = str(index_row.get("target_id", ""))
                if (
                    str(index_row.get("target_type", "")) != "scene"
                    or not scene_id
                    or scene_id in seen
                ):
                    continue
                seen.add(scene_id)
                rows.append(
                    {
                        "scene": scene_id,
                        "phase": phase,
                        "status": str(artifact_row.get("status", "")),
                        "validation": "passing/unknown",
                        "action": "open scene",
                    }
                )
        return rows

    def _guide_rows(self, snapshot: CockpitSnapshot) -> list[dict[str, object]]:
        base_rows = [
            {
                "step": 1,
                "goal": "Create a short mock project",
                "command": (
                    "create 1min-field | 1 Minute Field | "
                    "A courier crosses three locations to deliver one warning."
                ),
                "validation": "Dashboard phase becomes intake and review is available.",
            },
            {
                "step": 2,
                "goal": "Approve intake through script gates",
                "command": "next -> approve -> approve",
                "validation": "Repeat until current phase reaches visual_dev or blockers appear.",
            },
            {
                "step": 3,
                "goal": "Inspect the production backbone",
                "command": "open assets; artifact <id>; reader next",
                "validation": "Reader shows scene, shot matrix, character, or reference details.",
            },
            {
                "step": 4,
                "goal": "Fix targeted issues before generation",
                "command": "show blocked; fix <target>; revise <note>",
                "validation": "Blocking validation count returns to zero before approval.",
            },
            {
                "step": 5,
                "goal": "Generate the clips",
                "command": "approve until phase generation, then gen run",
                "validation": "Generated clips appear under Assets and the Generate tab.",
            },
            {
                "step": 6,
                "goal": "Review generated clips and finish delivery",
                "command": "open assets; open validation; approve through delivery",
                "validation": (
                    "Clips, sidecars, validation, checkpoints, and audit are inspectable."
                ),
            },
        ]
        return [self._guide_status(row, snapshot) for row in base_rows]

    @staticmethod
    def _guide_status(row: dict[str, object], snapshot: CockpitSnapshot) -> dict[str, object]:
        dashboard = snapshot.dashboard
        validation = snapshot.validation
        artifacts = snapshot.artifacts
        phase = dashboard.current_phase if dashboard else ""
        phase_order = (
            "intake",
            "constitution",
            "development",
            "script",
            "visual_dev",
            "shot_bible",
            "gen_planning",
            "generation",
            "qc",
            "post",
            "delivery",
        )

        def phase_at_or_after(target: str) -> bool:
            if phase not in phase_order or target not in phase_order:
                return False
            return phase_order.index(phase) >= phase_order.index(target)

        blocking_count = len(validation.blocking_issues) if validation else 0
        artifact_phases = {str(artifact.get("phase", "")) for artifact in artifacts}
        artifact_count = len(artifacts)
        step = int(str(row["step"]))
        status = "pending"
        evidence = str(row["validation"])
        if step == 1:
            status = "done" if dashboard and phase else "current"
            evidence = (
                f"Active project {dashboard.project_id} is at {phase}."
                if dashboard and phase
                else "No active project yet."
            )
        elif step == 2:
            if phase_at_or_after("visual_dev"):
                status = "done"
                evidence = f"Project reached {phase}."
            elif dashboard and phase:
                status = "current"
                evidence = f"Continue approvals from {phase}."
        elif step == 3:
            status = "done" if artifact_count else "pending"
            evidence = f"{artifact_count} artifact(s) are available to inspect."
        elif step == 4:
            if blocking_count:
                status = "blocked"
                evidence = f"{blocking_count} blocking validation issue(s) need fixes."
            elif validation:
                status = "done"
                evidence = "No blocking validation issues are present."
        elif step == 5:
            if phase_at_or_after("generation") or "generation" in artifact_phases:
                status = "done"
                evidence = "Generation phase or artifacts are present."
            elif phase_at_or_after("gen_planning"):
                status = "current"
                evidence = f"Project is at {phase}; approve generation planning when ready."
        elif step == 6:
            has_generation_assets = "generation" in artifact_phases
            if has_generation_assets and validation:
                status = "done"
                evidence = "Generated assets and validation workspace are available."
            elif has_generation_assets:
                status = "current"
                evidence = "Generated assets exist; open validation next."
        return {**row, "status": status, "evidence": evidence}

    def _show_guide_step(self, row: dict[str, object], *, open_tab: bool = True) -> None:
        if open_tab:
            self.action_open_tab("guide")
        detail = (
            f"Step {row.get('step')}: {row.get('goal')}\n\n"
            f"Status: {row.get('status', 'pending')}\n\n"
            f"Command: {row.get('command')}\n\n"
            f"Validation: {row.get('validation')}\n\n"
            f"Evidence: {row.get('evidence', 'Not checked yet.')}"
        )
        self.query_one("#guide_detail", Static).update(detail)
        self._update_context(detail)

    def _matrix_pivot_field(self) -> str:
        return getattr(self, "_matrix_pivot", "status")

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
