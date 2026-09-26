"""The active-project precondition is checked once, at dispatch.

It used to be checked inside 46 handlers, each re-deriving it with its own
wording and emptiness test. It is now declared on the contract
(`ToolContract.requires_active_project`) and enforced by `MCPServer.call`,
beside the confirmation gate.

Handlers therefore *assume* the project exists and use `require_project_id` /
`require_project_state`, which raise if the assumption is violated. These tests
pin the guarantee at the level that provides it.
"""

from __future__ import annotations

import asyncio

import pytest

from film_pipeline.mcp.contract import make_registry
from film_pipeline.mcp.errors import MCPErrorCode
from film_pipeline.mcp.server import MCPServer


class TestContractDeclaration:
    def test_every_tool_declares_the_flag(self) -> None:
        """The attribute exists on every contract, defaulting to False."""
        registry = make_registry()
        for name in registry.all_names():
            contract = registry.get(name).contract
            assert isinstance(contract.requires_active_project, bool)

    def test_some_tools_require_a_project(self) -> None:
        registry = make_registry()
        flagged = [
            n for n in registry.all_names() if registry.get(n).contract.requires_active_project
        ]
        assert len(flagged) > 30, "expected most operator tools to require a project"

    def test_project_creation_does_not_require_one(self) -> None:
        """`create_film_project` is how you get a project; it cannot need one."""
        registry = make_registry()
        assert registry.get("create_film_project").contract.requires_active_project is False


class TestDispatchEnforcement:
    @pytest.mark.parametrize(
        "tool",
        ["get_film_state", "get_current_phase", "run_validation", "get_validation_report"],
    )
    def test_call_refuses_without_an_active_project(self, tool: str) -> None:
        server = MCPServer()
        response = asyncio.run(server.call(tool, {}))
        assert response.success is False
        assert response.error is not None
        assert response.error.code is MCPErrorCode.NO_ACTIVE_PROJECT

    def test_error_names_the_tool(self) -> None:
        server = MCPServer()
        response = asyncio.run(server.call("get_film_state", {}))
        assert response.error is not None
        assert response.error.details == {"tool": "get_film_state"}

    def test_unflagged_tool_is_not_blocked(self) -> None:
        """A tool that does not require a project must not be refused for one."""
        server = MCPServer()
        response = asyncio.run(server.call("list_profiles", {}))
        assert response.success is True

    def test_guard_precedes_the_handler(self) -> None:
        """The handler must not run: no project means no side effects."""
        server = MCPServer()
        response = asyncio.run(server.call("run_validation", {}))
        assert response.success is False


class TestHandlerAssumption:
    def test_require_project_id_raises_without_a_project(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Direct callers get a loud failure, not a silent wrong answer."""
        from film_pipeline.mcp.tools.helpers import require_project_id
        from film_pipeline.operations.errors import ProjectNotFoundError
        from film_pipeline.studio.runtime import get_runtime

        runtime = get_runtime()
        runtime.active_project_id = ""
        monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: runtime)
        with pytest.raises(ProjectNotFoundError):
            require_project_id({})

    def test_require_project_state_raises_without_a_project(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from film_pipeline.mcp.tools.helpers import require_project_state
        from film_pipeline.operations.errors import ProjectNotFoundError
        from film_pipeline.studio.runtime import get_runtime

        runtime = get_runtime()
        runtime.active_project_id = ""
        monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: runtime)
        with pytest.raises(ProjectNotFoundError):
            require_project_state({})
