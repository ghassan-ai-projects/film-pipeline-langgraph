"""Gateway-to-snapshot assembly for the studio TUI.

Split from :mod:`film_pipeline.tui.app` so the App shell stays focused on
wiring, key bindings, and user actions while these helpers translate gateway
calls into a single coherent :class:`StudioSnapshot`.
"""

from __future__ import annotations

from film_pipeline.app.services.models import (
    DashboardSummary,
    GenerationWorkspace,
    ProjectListItem,
)
from film_pipeline.tui.app_state import AppState
from film_pipeline.tui.gateway import StudioGateway
from film_pipeline.tui.view_models.models import StudioSnapshot


class SnapshotLoaderMixin:
    """Methods that load studio state through the gateway for the app.

    The annotation-only attributes below name the ``FilmStudioApp`` members
    this mixin relies on; they carry no runtime value and are satisfied by
    the composing application class.
    """

    gateway: StudioGateway
    state: AppState
    active_project_id: str

    def _load_snapshot(self) -> StudioSnapshot:
        projects = self.gateway.list_projects()
        active = self._resolve_active_project(projects)
        self.state.active_project = active
        dashboard = self.gateway.get_dashboard(active.project_id) if active else None
        self.state.dashboard = dashboard
        project_id = dashboard.project_id if dashboard else None
        artifacts = self.gateway.list_artifacts(project_id) if project_id else []
        assets = self.gateway.list_assets(project_id) if project_id else []
        review = self.gateway.get_review_workspace(project_id) if project_id else None
        validation = self.gateway.get_validation_workspace(project_id) if project_id else None
        providers = self.gateway.list_provider_status()
        comments = self.gateway.list_operator_comments(project_id) if project_id else []
        generation = self._load_generation_workspace(project_id, dashboard)
        prompts = self._load_generation_prompts(project_id, dashboard)
        return StudioSnapshot(
            projects=projects,
            dashboard=dashboard,
            review=review,
            validation=validation,
            artifacts=artifacts,
            assets=assets,
            providers=providers,
            comments=comments,
            generation=generation,
            prompts=prompts,
        )

    def _load_generation_workspace(
        self, project_id: str | None, dashboard: DashboardSummary | None
    ) -> GenerationWorkspace | None:
        if project_id and dashboard and dashboard.current_phase == "generation":
            return self.gateway.get_generation_workspace(project_id)
        return None

    def _load_generation_prompts(
        self, project_id: str | None, dashboard: DashboardSummary | None
    ) -> list[dict[str, object]]:
        prompt_phases = {"generation", "gen_planning"}
        if project_id and dashboard and dashboard.current_phase in prompt_phases:
            return self.gateway.preview_generation_prompts(project_id)
        return []

    def _resolve_active_project(self, projects: list[ProjectListItem]) -> ProjectListItem | None:
        if self.active_project_id:
            match = next((p for p in projects if p.project_id == self.active_project_id), None)
            if match is not None:
                return match
        live = [p for p in projects if p.status != "discovered"]
        if live:
            return live[0]
        discovered = [p for p in projects if p.status == "discovered"]
        if discovered:
            return discovered[0]
        return None
