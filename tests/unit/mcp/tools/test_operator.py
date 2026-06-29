"""Unit tests for film_pipeline.mcp.tools.operator."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import cast

import pytest

from film_pipeline.app.runtime import reset_runtime
from film_pipeline.mcp.tools import add_operator_comment, list_operator_comments


@pytest.fixture(autouse=True)
def _reset_to_mock_mode() -> Generator[None, None, None]:
    reset_runtime("mock")
    yield
    reset_runtime("mock")


def test_add_operator_comment_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(
        add_operator_comment({"target_type": "scene", "target_id": "s1", "body": "Fix lighting."})
    )
    assert result["ok"] is False
    assert "active project" in cast(str, result["error"]).lower()


def test_add_operator_comment_validates_fields() -> None:
    result = asyncio.run(add_operator_comment({"target_type": "scene"}))
    assert result["ok"] is False


def test_add_and_list_operator_comments() -> None:
    from film_pipeline.mcp.tools import create_film_project, set_active_project

    asyncio.run(create_film_project({"project_id": "op-comment", "title": "T"}))
    asyncio.run(set_active_project({"project_ref": "op-comment"}))

    result = asyncio.run(
        add_operator_comment(
            {
                "target_type": "scene",
                "target_id": "s1",
                "body": "Fix lighting.",
                "phase": "script",
                "source": "mcp",
            }
        )
    )
    assert result["ok"] is True
    assert result["body"] == "Fix lighting."
    assert result["phase"] == "script"
    assert result["source"] == "mcp"

    listed = asyncio.run(list_operator_comments({}))
    assert listed["ok"] is True
    comments = cast(list[dict[str, object]], listed["comments"])
    assert len(comments) == 1
    assert comments[0]["body"] == "Fix lighting."
