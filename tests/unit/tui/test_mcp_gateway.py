"""Tests for the MCP-client TUI gateway."""

from __future__ import annotations

import pytest

from film_pipeline.app.runtime import reset_runtime
from film_pipeline.app.services.models import (
    OperatorCommentRequest,
    ProjectCreateRequest,
)
from film_pipeline.tui.gateways._transport import MCPProcessTransport
from film_pipeline.tui.gateways.mcp import MCPStudioGateway


def test_mcp_gateway_default_command_uses_running_interpreter() -> None:
    """The default launch runs the in-package server with the current interpreter.

    Shelling out to ``uv run`` required an external ``uv`` binary and a writable
    uv cache merely to start a module that ships with this package.
    """
    import sys

    assert MCPProcessTransport._default_command() == [
        sys.executable,
        "-m",
        "film_pipeline.mcp.server",
    ]


def test_mcp_gateway_full_lifecycle() -> None:
    """Exercise every gateway method against the real MCP server subprocess."""
    reset_runtime("mock")
    gateway = MCPStudioGateway()
    try:
        projects = gateway.list_projects()
        assert isinstance(projects, list)

        request = ProjectCreateRequest(project_id="mcp-gw", title="MCP Gateway Test")
        result = gateway.create_project(request)
        assert result.ok is True
        assert result.project_id == "mcp-gw"

        projects = gateway.list_projects()
        assert any(p.project_id == "mcp-gw" for p in projects)

        dashboard = gateway.set_active_project("mcp-gw")
        assert dashboard.project_id == "mcp-gw"

        dashboard = gateway.get_dashboard("mcp-gw")
        assert dashboard.project_id == "mcp-gw"

        idea_result = gateway.submit_idea("mcp-gw", "A film about testing.")
        assert idea_result.ok is True
        assert idea_result.current_phase == "intake"

        dashboard = gateway.get_dashboard("mcp-gw")
        assert dashboard.current_phase == "intake"

        review = gateway.get_review_workspace("mcp-gw")
        assert isinstance(review.project_id, str)

        validation = gateway.get_validation_workspace("mcp-gw")
        assert isinstance(validation.project_id, str)

        refreshed = gateway.run_validation("mcp-gw")
        assert isinstance(refreshed.project_id, str)

        comment = gateway.add_operator_comment(
            OperatorCommentRequest(target_type="scene", target_id="s1", body="Fix lighting."),
            "mcp-gw",
        )
        assert comment.body == "Fix lighting."

        comments = gateway.list_operator_comments("mcp-gw")
        assert len(comments) == 1

        artifacts = gateway.list_artifacts("mcp-gw")
        assert isinstance(artifacts, list)

        assets = gateway.list_assets("mcp-gw")
        assert isinstance(assets, list)

        checkpoints = gateway.list_checkpoints("mcp-gw")
        assert isinstance(checkpoints, list)

        providers = gateway.list_provider_status()
        assert isinstance(providers, list)

        audit = gateway.get_audit_feed("mcp-gw", limit=5)
        assert isinstance(audit, list)
    finally:
        gateway.close()


def test_mcp_gateway_approve_and_revision() -> None:
    reset_runtime("mock")
    gateway = MCPStudioGateway()
    try:
        request = ProjectCreateRequest(project_id="mcp-gw-approve", title="T")
        gateway.create_project(request)
        gateway.set_active_project("mcp-gw-approve")
        idea = gateway.submit_idea("mcp-gw-approve", "A short film about a second chance.")
        assert idea.ok is True
        result = gateway.approve_phase("mcp-gw-approve")
        assert isinstance(result.ok, bool)

        # An active project can enter the revision path; the gateway must
        # surface the successful mutation.
        revision = gateway.request_revision("Refine tone.", "mcp-gw-approve")
        assert revision.ok is True
        assert revision.project_id == "mcp-gw-approve"
    finally:
        gateway.close()


def test_mcp_gateway_inspect_artifact() -> None:
    reset_runtime("mock")
    gateway = MCPStudioGateway()
    try:
        request = ProjectCreateRequest(project_id="mcp-gw-inspect", title="T")
        gateway.create_project(request)
        detail = gateway.inspect_artifact("nonexistent", "intake", 1, "mcp-gw-inspect")
        assert detail.artifact_id == "nonexistent"
    finally:
        gateway.close()


def test_mcp_gateway_create_project_with_optional_fields() -> None:
    reset_runtime("mock")
    gateway = MCPStudioGateway()
    try:
        request = ProjectCreateRequest(
            project_id="mcp-gw-full",
            title="Full",
            slug="full",
            idea="An idea.",
            runtime_mode="mock",
            target_runtime_seconds=120,
        )
        result = gateway.create_project(request)
        assert result.ok is True
        assert result.project_id == "mcp-gw-full"
    finally:
        gateway.close()


def test_mcp_gateway_default_gateway_selection() -> None:
    import os

    from film_pipeline.tui.gateways import default_gateway
    from film_pipeline.tui.gateways.inprocess import InProcessStudioGateway

    prev = os.environ.get("FILM_PIPELINE_TUI_GATEWAY")
    try:
        os.environ["FILM_PIPELINE_TUI_GATEWAY"] = "inprocess"
        assert isinstance(default_gateway(), InProcessStudioGateway)
        del os.environ["FILM_PIPELINE_TUI_GATEWAY"]
        assert isinstance(default_gateway(), InProcessStudioGateway)
    finally:
        if prev is None:
            os.environ.pop("FILM_PIPELINE_TUI_GATEWAY", None)
        else:
            os.environ["FILM_PIPELINE_TUI_GATEWAY"] = prev


def test_mcp_gateway_handles_bad_subprocess() -> None:
    """A subprocess that emits invalid JSON-RPC surfaces a RuntimeError."""
    import sys

    gateway = MCPStudioGateway(command=[sys.executable, "-c", "print('garbage')"])
    try:
        with pytest.raises(RuntimeError):
            gateway.list_projects()
    finally:
        gateway.close()


def test_mcp_gateway_handles_early_exit() -> None:
    """A subprocess that exits immediately surfaces a RuntimeError."""
    gateway = MCPStudioGateway(command=["true"])
    try:
        with pytest.raises(RuntimeError):
            gateway.list_projects()
    finally:
        gateway.close()


def test_mcp_gateway_set_active_project_failure() -> None:
    reset_runtime("mock")
    gateway = MCPStudioGateway()
    try:
        with pytest.raises(RuntimeError):
            gateway.set_active_project("does-not-exist")
    finally:
        gateway.close()


def test_mcp_gateway_set_runtime_mode() -> None:
    gateway = MCPStudioGateway()
    try:
        assert gateway.set_runtime_mode("mock") == "mock"
    finally:
        gateway.close()


def test_mcp_gateway_list_assets_with_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gateway delegates asset listing to the list_assets MCP tool."""
    gateway = MCPStudioGateway()
    try:
        monkeypatch.setattr(
            gateway,
            "_tool",
            lambda _method, _args: {
                "ok": True,
                "assets": [
                    {
                        "asset_id": "clip-001",
                        "kind": "generated_clip",
                        "shot_id": "shot_0001",
                        "scene_id": "scene_01",
                        "path": "projects/mcp-gw-assets/07-generated-assets/clip-001.mp4",
                    }
                ],
            },
        )
        assets = gateway.list_assets("mcp-gw-assets")
        assert len(assets) == 1
        assert assets[0]["asset_id"] == "clip-001"
        assert assets[0]["kind"] == "generated_clip"
    finally:
        gateway.close()


def test_mcp_gateway_text_only_workspace_tracks_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Text-only generation is incomplete until the manifest asset is recorded."""
    gateway = MCPStudioGateway()
    assets: list[dict[str, object]] = []

    def fake_tool(method: str, _args: dict[str, object]) -> dict[str, object]:
        if method == "get_project_summary":
            return {"ok": True, "generation_policy": "text_only"}
        if method == "list_assets":
            return {"ok": True, "assets": assets}
        if method == "plan_generation_batch":
            assets.append({"asset_id": "text-only-delivery", "kind": "text_only_delivery"})
            return {"ok": True}
        return {"ok": True}

    try:
        monkeypatch.setattr(gateway, "_tool", fake_tool)

        before = gateway.get_generation_workspace("mcp-gw-text-only")
        assert before.completed == 0
        assert before.next_step == "plan"

        after = gateway.plan_generation("mcp-gw-text-only")
        assert after.completed == 1
        assert after.next_step == "approve_phase"
    finally:
        gateway.close()


def test_mcp_gateway_preview_generation_prompts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gateway delegates prompt previews to the MCP tool surface."""
    gateway = MCPStudioGateway()
    try:
        monkeypatch.setattr(
            gateway,
            "_tool",
            lambda _method, _args: {
                "ok": True,
                "previews": [
                    {
                        "shot_id": "shot_0001",
                        "scene_id": "sc_001",
                        "provider": "mock-video-provider",
                        "model": "mock-fast",
                        "duration_seconds": 8,
                        "prompt": "Wide establishing shot of the field at dawn.",
                    }
                ],
            },
        )
        previews = gateway.preview_generation_prompts("any-project")
        assert len(previews) == 1
        assert previews[0]["shot_id"] == "shot_0001"
        assert "prompt" in previews[0]
    finally:
        gateway.close()


def test_mcp_gateway_preview_generation_prompts_returns_empty_on_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gateway surfaces a failed tool call as an empty list."""
    gateway = MCPStudioGateway()
    try:
        monkeypatch.setattr(
            gateway,
            "_tool",
            lambda _method, _args: {"ok": False, "error": "No shot matrix"},
        )
        previews = gateway.preview_generation_prompts("any-project")
        assert previews == []
    finally:
        gateway.close()


def test_mcp_gateway_reads_plain_result_dict() -> None:
    """Responses without structuredContent fall back to the raw result dict."""
    import sys

    script = r"""
import sys, json

def read_message():
    length = None
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line == b"\r\n" or line == b"\n":
            break
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
    if length is None:
        return None
    return json.loads(sys.stdin.buffer.read(length))

read_message()
resp = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"ok": True}})
sys.stdout.write(f"Content-Length: {len(resp)}\r\n\r\n{resp}")
sys.stdout.flush()
"""
    gateway = MCPStudioGateway(command=[sys.executable, "-c", script])
    try:
        result = gateway._call("tools/call")
        assert result["ok"] is True
    finally:
        gateway.close()
