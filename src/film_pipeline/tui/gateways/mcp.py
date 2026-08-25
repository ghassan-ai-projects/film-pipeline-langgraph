"""MCP stdio JSON-RPC gateway for the TUI.

Speaks to ``film_pipeline.mcp.server`` over stdin/stdout, translating
TUI view-model calls into MCP tool invocations so the TUI exercises the
same tool surface as OpenClaw. Payload-to-view-model translation lives in
``_translations``; this module owns orchestration and error surfacing.
"""

from __future__ import annotations

import os
from typing import cast

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
from film_pipeline.tui.gateway import StudioGateway
from film_pipeline.tui.gateways._translations import (
    artifact_detail_from_response,
    audit_event_from_entry,
    dashboard_summary_from_response,
    generation_workspace_from_rows,
    mutation_result_from_response,
    operator_comment_from_entry,
    project_create_arguments,
    project_list_item_from_summary,
    review_workspace_from_response,
    text_only_generation_workspace,
    validation_workspace_from_response,
)
from film_pipeline.tui.gateways._transport import MCPProcessTransport


class MCPStudioGateway(MCPProcessTransport, StudioGateway):
    """Gateway that calls MCP tools through a stdio JSON-RPC subprocess."""

    # --- Gateway contract ---

    def list_projects(self) -> list[ProjectListItem]:
        r = self._tool("list_projects", {})
        projects = r.get("projects", [])
        if not isinstance(projects, list):  # pragma: no cover
            return []
        items: list[ProjectListItem] = []
        for pid in projects:
            if not isinstance(pid, str):
                continue
            summary = self._tool("get_project_summary", {"project_ref": pid})
            items.append(project_list_item_from_summary(pid, summary))
        return items

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        r = self._tool("create_film_project", project_create_arguments(request))
        return mutation_result_from_response(
            r,
            fallback_project_id=request.project_id,
            success_message="Project created.",
        )

    def set_active_project(self, project_id: str) -> DashboardSummary:
        self._invoke_tool_or_raise("set_active_project", {"project_ref": project_id})
        return self.get_dashboard(project_id)

    def set_runtime_mode(self, mode: str) -> str:
        return mode

    def submit_idea(self, project_id: str, idea: str) -> MutationResult:
        self._set_active(project_id)
        r = self._tool("submit_idea", {"idea": idea})
        return mutation_result_from_response(
            r,
            fallback_project_id=project_id,
            success_message="Idea submitted.",
        )

    def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
        self._set_active(project_id)
        r = self._tool("get_project_summary", {})
        return dashboard_summary_from_response(r)

    def get_review_workspace(self, project_id: str | None = None) -> ReviewWorkspace:
        self._set_active(project_id)
        r = self._tool("review_phase_artifacts", {})
        return review_workspace_from_response(r)

    def get_validation_workspace(self, project_id: str | None = None) -> ValidationWorkspace:
        self._set_active(project_id)
        r = self._tool("get_validation_report", {})
        return validation_workspace_from_response(r)

    def run_validation(self, project_id: str | None = None) -> ValidationWorkspace:
        self._set_active(project_id)
        self._tool("run_validation", {})
        return self.get_validation_workspace(project_id)

    def _is_text_only(self, project_id: str | None) -> bool:
        self._set_active(project_id)
        r = self._tool("get_project_summary", {})
        return str(r.get("generation_policy", "")).lower() == "text_only"

    def _text_only_workspace(self, project_id: str | None) -> GenerationWorkspace:
        return text_only_generation_workspace(project_id, self.list_assets(project_id))

    def get_generation_workspace(self, project_id: str | None = None) -> GenerationWorkspace:
        self._set_active(project_id)
        if self._is_text_only(project_id):
            return self._text_only_workspace(project_id)
        r = self._tool("list_active_generations", {})
        return generation_workspace_from_rows(project_id, r.get("rows", []))

    def _current_generation_workspace(self, project_id: str | None) -> GenerationWorkspace:
        """Return the workspace view matching the project's generation policy."""
        if self._is_text_only(project_id):
            return self._text_only_workspace(project_id)
        return self.get_generation_workspace(project_id)

    def plan_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        self._set_active(project_id)
        self._invoke_tool_or_raise("plan_generation_batch", {})
        return self._current_generation_workspace(project_id)

    def approve_generation_spend(
        self, project_id: str | None = None, max_cost_usd: float = -1.0
    ) -> GenerationWorkspace:
        self._set_active(project_id)
        self._invoke_tool_or_raise("approve_generation_spend", {"max_cost_usd": max_cost_usd})
        return self._current_generation_workspace(project_id)

    def start_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        self._set_active(project_id)
        self._invoke_tool_or_raise("start_generation_batch", {})
        return self._current_generation_workspace(project_id)

    def poll_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        self._set_active(project_id)
        if self._is_text_only(project_id):
            return self._text_only_workspace(project_id)
        self._resume_inflight_generations()
        return self.get_generation_workspace(project_id)

    def _resume_inflight_generations(self) -> None:
        """Resume server-side polling for every row with a provider job."""
        active = self._tool("list_active_generations", {})
        rows = active.get("rows", [])
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and row.get("provider_job_id"):
                    self._tool(
                        "resume_generation_polling",
                        {"generation_id": str(row.get("generation_id", ""))},
                    )

    def _invoke_tool_or_raise(self, tool_name: str, arguments: dict[str, object]) -> None:
        """Invoke ``tool_name`` and raise RuntimeError when it reports failure."""
        result = self._tool(tool_name, arguments)
        if not result.get("ok"):
            raise RuntimeError(str(result.get("error", f"{tool_name} failed")))

    def preview_generation_prompts(self, project_id: str | None = None) -> list[dict[str, object]]:
        """Resolve the exact prompt each shot will send to its provider."""
        self._set_active(project_id)
        r = self._tool("preview_generation_prompts", {})
        if not r.get("ok"):
            return []
        return cast(list[dict[str, object]], r.get("previews", []))

    def approve_phase(self, project_id: str | None = None) -> MutationResult:
        self._set_active(project_id)
        r = self._tool("approve_phase", {"confirmed": True})
        return mutation_result_from_response(
            r,
            fallback_project_id="",
            success_message="Phase approved.",
        )

    def request_revision(self, note: str, project_id: str | None = None) -> MutationResult:
        self._set_active(project_id)
        r = self._tool("request_revision", {"note": note, "confirmed": True})
        return mutation_result_from_response(
            r,
            fallback_project_id="",
            success_message="Revision requested.",
        )

    def add_operator_comment(
        self,
        request: OperatorCommentRequest,
        project_id: str | None = None,
    ) -> OperatorComment:
        self._set_active(project_id)
        r = self._tool(
            "add_operator_comment",
            {
                "target_type": request.target_type,
                "target_id": request.target_id,
                "body": request.body,
                "phase": request.phase,
                "source": request.source,
            },
        )
        return OperatorComment(
            comment_id=str(r.get("comment_id", "comment:mcp:synthetic")),
            project_id=project_id or "",
            target_type=request.target_type,
            target_id=request.target_id,
            body=request.body,
            phase=request.phase,
            source=request.source,
            created_at=str(r.get("created_at", "")),
        )

    def list_operator_comments(
        self,
        project_id: str | None = None,
        *,
        include_resolved: bool = False,
    ) -> list[OperatorComment]:
        self._set_active(project_id)
        r = self._tool("list_operator_comments", {"include_resolved": include_resolved})
        comments = r.get("comments", [])
        if not isinstance(comments, list):  # pragma: no cover
            return []
        return [
            operator_comment_from_entry(comment, project_id)
            for comment in comments
            if isinstance(comment, dict)
        ]

    def list_artifacts(
        self, project_id: str | None = None, phase: str | None = None
    ) -> list[dict[str, object]]:
        self._set_active(project_id)
        arguments: dict[str, object] = {"phase": phase} if phase else {}
        r = self._tool("list_artifacts", arguments)
        artifacts = r.get("artifacts", [])
        return list(artifacts) if isinstance(artifacts, list) else []

    def list_assets(self, project_id: str | None = None) -> list[dict[str, object]]:
        self._set_active(project_id)
        r = self._tool("list_assets", {})
        assets = r.get("assets", [])
        return list(assets) if isinstance(assets, list) else []

    def inspect_artifact(
        self,
        artifact_id: str,
        phase: str,
        version: int = 1,
        project_id: str | None = None,
    ) -> ArtifactDetail:
        self._set_active(project_id)
        r = self._tool(
            "inspect_artifact",
            {"artifact_id": artifact_id, "phase": phase, "version": version},
        )
        return artifact_detail_from_response(artifact_id, phase, version, r)

    def list_checkpoints(self, project_id: str | None = None) -> list[dict[str, str]]:
        self._set_active(project_id)
        r = self._tool("list_checkpoints", {})
        checkpoints = r.get("checkpoints", [])
        return [dict(c) for c in checkpoints] if isinstance(checkpoints, list) else []

    def list_provider_status(self) -> list[dict[str, object]]:
        r = self._tool("list_providers", {})
        providers = r.get("providers", [])
        return (
            [{"provider_id": p, "status": "unknown"} for p in providers]
            if isinstance(providers, list)
            else []
        )

    def get_audit_feed(self, project_id: str | None = None, limit: int = 20) -> list[AuditEvent]:
        self._set_active(project_id)
        r = self._tool("get_audit_log", {"limit": limit})
        events = r.get("events", [])
        feed: list[AuditEvent] = []
        if isinstance(events, list):
            for event in events[:limit]:
                if isinstance(event, dict):
                    feed.append(audit_event_from_entry(event))
        return feed


def default_gateway() -> StudioGateway:
    """Return the gateway selected by ``FILM_PIPELINE_TUI_GATEWAY``.

    Defaults to the in-process gateway: it is the complete, low-latency
    surface over the shared application service layer (routing, assets,
    generation, provider health). Set ``FILM_PIPELINE_TUI_GATEWAY=mcp`` to
    drive the studio through the MCP stdio tool surface instead (parity
    testing with OpenClaw).
    """
    from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway

    mode = os.getenv("FILM_PIPELINE_TUI_GATEWAY", "inprocess").lower()
    if mode == "mcp":
        return MCPStudioGateway()
    return InProcessStudioGateway()
