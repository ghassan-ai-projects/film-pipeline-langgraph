"""Operator comment tools."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec

from .helpers import (
    _error,
    _ok,
)


async def add_operator_comment(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Add an operator comment to a project target."""
    rt = ctx.runtime
    project_id = ctx.project_id

    target_type = str(args.get("target_type", "")).strip()
    target_id = str(args.get("target_id", "")).strip()
    body = str(args.get("body", "")).strip()
    phase = str(args.get("phase", "")).strip()
    source = str(args.get("source", "mcp")).strip() or "mcp"

    if not target_type:
        return _error("target_type is required.")
    if not target_id:
        return _error("target_id is required.")
    if not body:
        return _error("body is required.")

    try:
        comment = rt.add_operator_comment(
            project_id,
            target_type=target_type,
            target_id=target_id,
            body=body,
            phase=phase,
            source=source,
        )
        return _ok(
            comment_id=comment["comment_id"],
            project_id=comment["project_id"],
            target_type=comment["target_type"],
            target_id=comment["target_id"],
            body=comment["body"],
            phase=comment["phase"],
            source=comment["source"],
            created_at=comment["created_at"],
        )
    except Exception as e:
        return _error(str(e))


async def list_operator_comments(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """List operator comments for the active project."""
    rt = ctx.runtime
    project_id = ctx.project_id

    include_resolved = bool(args.get("include_resolved"))
    try:
        comments = rt.list_operator_comments(project_id, include_resolved=include_resolved)
        return _ok(comments=comments)
    except Exception as e:
        return _error(str(e))


# ── Tool declarations ────────────────────────────────────────────────────────
# Declared next to the handlers they describe (doc 04 slice 1).


class AddOperatorCommentArgs(ToolArgs):
    """Arguments for `add_operator_comment`."""

    body: str = Field(description="Comment text.")
    target_type: str = Field(default="", description="What the comment is about.")
    target_id: str = Field(default="", description="Id of the thing commented on.")
    phase: str = Field(default="", description="Phase the comment belongs to.")
    source: str = Field(default="", description="Where the comment came from.")


class ListOperatorCommentsArgs(ToolArgs):
    """Arguments for `list_operator_comments`."""

    include_resolved: bool = Field(
        default=False, description="Include comments already marked resolved."
    )


OPERATOR_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="add_operator_comment",
        group=ToolGroup.OPERATOR,
        description="Record an operator comment against a project, phase or artifact.",
        args=AddOperatorCommentArgs,
        handler=add_operator_comment,
        mutates=True,
        active_project=True,
    ),
    ToolSpec(
        name="list_operator_comments",
        group=ToolGroup.OPERATOR,
        description="List the operator comments recorded for the active project.",
        args=ListOperatorCommentsArgs,
        handler=list_operator_comments,
        active_project=True,
    ),
)
