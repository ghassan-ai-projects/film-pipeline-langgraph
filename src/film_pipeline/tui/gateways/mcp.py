"""MCP stdio JSON-RPC gateway for the TUI.

Speaks to ``film_pipeline.mcp.server`` over stdin/stdout, translating
TUI view-model calls into MCP tool invocations so the TUI exercises the
same tool surface as OpenClaw.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, cast

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


class MCPStudioGateway(StudioGateway):
    """Gateway that calls MCP tools through a stdio JSON-RPC subprocess."""

    def __init__(self, command: list[str] | None = None) -> None:
        self._command = command or self._default_command()
        self._proc: subprocess.Popen[str] | None = None
        self._lock = threading.Lock()
        self._request_id = 0
        self._ensure_started()

    @staticmethod
    def _default_command() -> list[str]:
        return [
            "uv",
            "run",
            "--python",
            "3.12",
            "--group",
            "dev",
            "python",
            "-m",
            "film_pipeline.mcp.server",
        ]

    def _ensure_started(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        self._proc = subprocess.Popen(
            self._command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(Path.cwd()),
        )

    def _call(self, method: str, params: dict[str, object] | None = None) -> dict[str, Any]:
        with self._lock:
            self._ensure_started()
            if (
                self._proc is None or self._proc.stdin is None or self._proc.stdout is None
            ):  # pragma: no cover
                raise RuntimeError("MCP server subprocess is not available.")
            self._request_id += 1
            request: dict[str, object] = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
            }
            if params:
                request["params"] = params
            body = json.dumps(request)
            self._proc.stdin.write(f"Content-Length: {len(body)}\r\n\r\n{body}")
            self._proc.stdin.flush()
            return self._read_response(self._request_id)

    def _read_response(self, expected_id: int) -> dict[str, Any]:
        if self._proc is None or self._proc.stdout is None:  # pragma: no cover
            raise RuntimeError("MCP server subprocess is not available.")
        content_length: int | None = None
        while True:
            line = self._proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server closed stdout before response")
            if line in {"\r\n", "\n"}:
                break
            header = line.strip()
            if header.lower().startswith("content-length:"):
                content_length = int(header.split(":", 1)[1].strip())
        if content_length is None:  # pragma: no cover
            raise RuntimeError("Missing Content-Length header in MCP response")
        raw = self._proc.stdout.read(content_length)
        response = json.loads(raw)
        if response.get("id") != expected_id:  # pragma: no cover
            raise RuntimeError(f"MCP response id mismatch: {response.get('id')} != {expected_id}")
        if "error" in response:
            raise RuntimeError(response["error"].get("message", "Unknown MCP error"))
        result = response.get("result", {})
        if not isinstance(result, dict):  # pragma: no cover
            raise RuntimeError("MCP result is not an object")
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        return result

    def _tool(self, tool_name: str, arguments: dict[str, object]) -> dict[str, Any]:
        return self._call("tools/call", {"name": tool_name, "arguments": arguments})

    def _set_active(self, project_id: str | None) -> None:
        if project_id:
            self._tool("set_active_project", {"project_ref": project_id})

    # --- Gateway contract ---

    def list_projects(self) -> list[ProjectListItem]:
        r = self._tool("list_projects", {})
        projects = r.get("projects", [])
        if not isinstance(projects, list):  # pragma: no cover
            return []
        items: list[ProjectListItem] = []
        for pid in projects:
            summary = self._tool("get_project_summary", {})
            items.append(
                ProjectListItem(
                    project_id=str(pid),
                    title=str(summary.get("title", pid)),
                    slug=str(summary.get("slug", pid)),
                    current_phase=str(summary.get("current_phase", "")),
                    status="in_progress" if summary.get("current_phase") else "created",
                    has_blockers=bool(summary.get("has_blockers")),
                    awaiting_review=False,
                )
            )
        return items

    def create_project(self, request: ProjectCreateRequest) -> MutationResult:
        args: dict[str, object] = {
            "project_id": request.project_id,
            "title": request.title,
        }
        if request.slug:
            args["slug"] = request.slug
        if request.idea:
            args["idea"] = request.idea
        if request.runtime_mode:
            args["runtime_mode"] = request.runtime_mode
        if request.target_runtime_seconds:
            args["target_runtime_seconds"] = request.target_runtime_seconds
        r = self._tool("create_film_project", args)
        return MutationResult(
            ok=bool(r.get("ok")),
            project_id=str(r.get("project_id", request.project_id)),
            current_phase=str(r.get("current_phase", "")),
            message="Project created." if r.get("ok") else str(r.get("error", "")),
        )

    def set_active_project(self, project_id: str) -> DashboardSummary:
        r = self._tool("set_active_project", {"project_ref": project_id})
        if not r.get("ok"):
            raise RuntimeError(str(r.get("error", "set_active_project failed")))
        return self.get_dashboard(project_id)

    def set_runtime_mode(self, mode: str) -> str:
        return mode

    def submit_idea(self, project_id: str, idea: str) -> MutationResult:
        self._set_active(project_id)
        r = self._tool("submit_idea", {"idea": idea})
        return MutationResult(
            ok=bool(r.get("ok")),
            project_id=str(r.get("project_id", project_id)),
            current_phase=str(r.get("current_phase", "")),
            message="Idea submitted." if r.get("ok") else str(r.get("error", "")),
        )

    def get_dashboard(self, project_id: str | None = None) -> DashboardSummary:
        self._set_active(project_id)
        r = self._tool("get_project_summary", {})
        return DashboardSummary(
            project_id=str(r.get("project_id", "")),
            title=str(r.get("title", "")),
            slug=str(r.get("slug", "")),
            current_phase=str(r.get("current_phase", "")),
            runtime_mode=str(r.get("runtime_mode", "mock")),
            workflow_mode="manual",
            status=str(r.get("status", "")),
            next_action="",
            route_reason="",
            issue_count=int(r.get("issue_count", 0)),
            artifact_count=int(r.get("artifact_count", 0)),
            checkpoint_count=int(r.get("checkpoint_count", 0)),
            has_blockers=bool(r.get("has_blockers")),
        )

    def get_review_workspace(self, project_id: str | None = None) -> ReviewWorkspace:
        self._set_active(project_id)
        r = self._tool("review_phase_artifacts", {})
        return ReviewWorkspace(
            project_id=str(r.get("project_id", "")),
            phase=str(r.get("phase", "")),
            recommendation="Review the phase outputs and approve or request revision.",
            candidate_artifacts=list(r.get("artifacts", []))
            if isinstance(r.get("artifacts"), list)
            else [],
        )

    def get_validation_workspace(self, project_id: str | None = None) -> ValidationWorkspace:
        self._set_active(project_id)
        r = self._tool("get_validation_report", {})
        return ValidationWorkspace(
            project_id=str(r.get("project_id", "")),
            phase=str(r.get("phase", "")),
            source=str(r.get("source", "")),
            reports=list(r.get("reports", [])) if isinstance(r.get("reports"), list) else [],
        )

    def run_validation(self, project_id: str | None = None) -> ValidationWorkspace:
        self._set_active(project_id)
        self._tool("run_validation", {})
        return self.get_validation_workspace(project_id)

    def get_generation_workspace(self, project_id: str | None = None) -> GenerationWorkspace:
        self._set_active(project_id)
        r = self._tool("list_active_generations", {})
        rows_raw = r.get("rows", [])
        rows = [dict(row) for row in rows_raw] if isinstance(rows_raw, list) else []
        running = sum(1 for row in rows if row.get("status") == "running")
        return GenerationWorkspace(
            project_id=project_id or "",
            phase="generation",
            provider="",
            model="",
            estimated_cost_usd=0.0,
            rows=rows,
            running=running,
            next_step="poll" if running else "plan",
        )

    def plan_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        self._set_active(project_id)
        result = self._tool("plan_generation_batch", {})
        if not result.get("ok"):
            raise RuntimeError(str(result.get("error", "plan_generation_batch failed")))
        return self.get_generation_workspace(project_id)

    def approve_generation_spend(
        self, project_id: str | None = None, max_cost_usd: float = -1.0
    ) -> GenerationWorkspace:
        self._set_active(project_id)
        result = self._tool("approve_generation_spend", {"max_cost_usd": max_cost_usd})
        if not result.get("ok"):
            raise RuntimeError(str(result.get("error", "approve_generation_spend failed")))
        return self.get_generation_workspace(project_id)

    def start_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        self._set_active(project_id)
        result = self._tool("start_generation_batch", {})
        if not result.get("ok"):
            raise RuntimeError(str(result.get("error", "start_generation_batch failed")))
        return self.get_generation_workspace(project_id)

    def poll_generation(self, project_id: str | None = None) -> GenerationWorkspace:
        self._set_active(project_id)
        active = self._tool("list_active_generations", {})
        rows = active.get("rows", [])
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and row.get("provider_job_id"):
                    self._tool(
                        "resume_generation_polling",
                        {"generation_id": str(row.get("generation_id", ""))},
                    )
        return self.get_generation_workspace(project_id)

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
        return MutationResult(
            ok=bool(r.get("ok")),
            project_id=str(r.get("project_id", "")),
            current_phase=str(r.get("current_phase", "")),
            message="Phase approved." if r.get("ok") else str(r.get("error", "")),
        )

    def request_revision(self, note: str, project_id: str | None = None) -> MutationResult:
        self._set_active(project_id)
        r = self._tool("request_revision", {"note": note, "confirmed": True})
        return MutationResult(  # pragma: no cover
            ok=bool(r.get("ok")),
            project_id=str(r.get("project_id", "")),
            current_phase=str(r.get("current_phase", "")),
            message="Revision requested." if r.get("ok") else str(r.get("error", "")),
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
            OperatorComment(
                comment_id=str(c.get("comment_id", "")),
                project_id=str(c.get("project_id", project_id or "")),
                target_type=str(c.get("target_type", "")),
                target_id=str(c.get("target_id", "")),
                body=str(c.get("body", "")),
                phase=str(c.get("phase", "")),
                source=str(c.get("source", "")),
                created_at=str(c.get("created_at", "")),
            )
            for c in comments
            if isinstance(c, dict)
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
        return []

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
        return ArtifactDetail(
            artifact_id=artifact_id,
            artifact_type=str(r.get("artifact_type", artifact_id)),
            phase=phase,
            version=version,
            status=str(r.get("status", "candidate")),
            body=dict(r.get("content", {})) if isinstance(r.get("content"), dict) else {},
        )

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
                    details = event.get("details", {})
                    if not isinstance(details, dict):  # pragma: no cover
                        details = {}
                    feed.append(
                        AuditEvent(
                            timestamp=str(event.get("timestamp", "")),
                            actor=str(event.get("actor", "")),
                            action=str(event.get("action", "")),
                            target=str(details.get("project_id", "")),
                            summary=(
                                f"{event.get('action', '')} {details.get('project_id', '')}"
                            ).strip(),
                        )
                    )
        return feed

    def close(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover
                self._proc.kill()

    def __del__(self) -> None:  # pragma: no cover
        self.close()


def default_gateway() -> StudioGateway:
    """Return the gateway selected by ``FILM_PIPELINE_TUI_GATEWAY``.

    Defaults to the in-process gateway: it is the complete, low-latency
    surface over the shared application service layer (routing, assets,
    generation, provider health). Set ``FILM_PIPELINE_TUI_GATEWAY=mcp`` to
    drive the cockpit through the MCP stdio tool surface instead (parity
    testing with OpenClaw; reduced feature set).
    """
    from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway

    mode = os.getenv("FILM_PIPELINE_TUI_GATEWAY", "inprocess").lower()
    if mode == "mcp":
        return MCPStudioGateway()
    return InProcessStudioGateway()
