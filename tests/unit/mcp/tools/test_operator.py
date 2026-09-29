"""Unit tests for film_pipeline.mcp.tools.operator."""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any, cast

import pytest

from film_pipeline.mcp.tools import add_operator_comment, list_operator_comments
from film_pipeline.studio.runtime import reset_runtime

CallTool = Callable[..., Any]


@pytest.fixture(autouse=True)
def _reset_to_mock_mode() -> Generator[None, None, None]:
    reset_runtime("mock")
    yield
    reset_runtime("mock")


def test_add_operator_comment_validates_fields(call_tool: CallTool) -> None:
    """Field validation, not the project precondition.

    This previously ran with no project at all, so it passed because the
    missing-project guard fired before the field checks — it never exercised
    what its name claims. The precondition is now enforced at dispatch, so the
    test sets up a project and asserts the field error.
    """
    from film_pipeline.mcp.tools import create_film_project, set_active_project

    call_tool(create_film_project, {"project_id": "op-validate", "title": "T"})
    call_tool(set_active_project, {"project_ref": "op-validate"})

    result = call_tool(add_operator_comment, {"target_type": "scene"})
    assert result["ok"] is False
    assert "target_id" in str(result.get("error", ""))


def test_add_and_list_operator_comments(call_tool: CallTool) -> None:
    from film_pipeline.mcp.tools import create_film_project, set_active_project

    call_tool(create_film_project, {"project_id": "op-comment", "title": "T"})
    call_tool(set_active_project, {"project_ref": "op-comment"})

    result = call_tool(
        add_operator_comment,
        {
            "target_type": "scene",
            "target_id": "s1",
            "body": "Fix lighting.",
            "phase": "script",
            "source": "mcp",
        },
    )
    assert result["ok"] is True
    assert result["body"] == "Fix lighting."
    assert result["phase"] == "script"
    assert result["source"] == "mcp"

    listed = call_tool(list_operator_comments, {})
    assert listed["ok"] is True
    comments = cast(list[dict[str, object]], listed["comments"])
    assert len(comments) == 1
    assert comments[0]["body"] == "Fix lighting."
