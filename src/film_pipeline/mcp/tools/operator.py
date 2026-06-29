"""Operator comment tools."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _active_project_id, _error, _ok


async def add_operator_comment(args: dict[str, object]) -> dict[str, object]:
    """Add an operator comment to a project target."""
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")

    target_type = str(args.get("target_type", "")).strip()
    target_id = str(args.get("target_id", "")).strip()
    body = str(args.get("body", "")).strip()
    phase = str(args.get("phase", "")).strip()
    source = str(args.get("source", "tui")).strip() or "tui"

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


async def list_operator_comments(args: dict[str, object]) -> dict[str, object]:
    """List operator comments for the active project."""
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")

    include_resolved = bool(args.get("include_resolved"))
    try:
        comments = rt.list_operator_comments(project_id, include_resolved=include_resolved)
        return _ok(comments=comments)
    except Exception as e:
        return _error(str(e))
