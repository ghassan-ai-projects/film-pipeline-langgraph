"""Intake submission / analysis / approval tools."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec
from film_pipeline.schemas.base import FilmPhase

from .helpers import (
    _coerce_runtime_arg,
    _error,
    _ok,
    _services,
)


def _apply_intake_hints(active: dict[str, Any], args: dict[str, object]) -> None:
    """Copy user-supplied generation hints (runtime, scene count, constraints) onto the state."""
    user_runtime = _coerce_runtime_arg(args)
    if user_runtime > 0:
        active["target_runtime_seconds"] = user_runtime
    user_scene_count = args.get("target_scene_count")
    if isinstance(user_scene_count, int) and user_scene_count > 0:
        active["target_scene_count"] = user_scene_count
    user_constraints = args.get("constraints")
    if isinstance(user_constraints, dict):
        active["constraints_hints"] = user_constraints


async def submit_idea(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    rt = ctx.runtime
    active = ctx.project_state()
    idea = str(args.get("idea", args.get("text", "")))
    if not idea:
        return _error("idea is required")
    # Inject the idea and run the graph through intake_node
    active["idea"] = idea
    _apply_intake_hints(active, args)
    state = rt.run_graph(active)
    # Update stored state
    rt.projects[active["project_id"]] = state
    return _ok(
        project_id=state["project_id"],
        current_phase=state.get("current_phase"),
        human_approval_required=state.get("human_approval_required"),
    )


async def get_intake_analysis(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    _ = args
    rt = ctx.runtime
    state = ctx.project_state()
    project_id = str(state["project_id"])

    try:
        data = _services(rt).artifact_store.load(
            project_id, FilmPhase("intake"), "intake_analysis", 1
        )
        return _ok(analysis=data)
    except (FileNotFoundError, ValueError):
        # Fall back to project state idea field
        idea = state.get("idea", "")
        if idea:
            return _ok(analysis={"raw_idea": idea, "note": "Intake not yet fully analyzed."})
        return _error("No intake analysis found. Submit an idea first.")


async def approve_intake(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    _ = args
    rt = ctx.runtime
    active = ctx.project_state()
    current_phase = str(active.get("current_phase", ""))
    if current_phase not in ("intake", ""):
        return _error(f"Current phase is '{current_phase}', not intake.")
    try:
        state = rt.approve_phase()
        return _ok(project_id=state["project_id"], current_phase=state.get("current_phase"))
    except ValueError as e:
        return _error(str(e))


# ── Tool declarations ────────────────────────────────────────────────────────
# Declared next to the handlers they describe (doc 04 slice 1).


class SubmitIdeaArgs(ToolArgs):
    """Arguments for `submit_idea`.

    `idea` and `text` are both accepted spellings of the same input.
    """

    idea: str = Field(default="", description="The film idea to submit.")
    text: str = Field(default="", description="Alias for `idea`.")
    target_runtime_seconds: int | float | str | None = Field(
        default=None,
        description=(
            "Requested film length in seconds; takes precedence over "
            "`target_runtime_minutes`. Numeric strings are accepted."
        ),
    )
    target_runtime_minutes: int | float | str | None = Field(
        default=None,
        description="Requested film length in minutes, used only when seconds is unset.",
    )
    target_scene_count: object = Field(
        default=None, description="Requested number of scenes, if any."
    )
    constraints: object = Field(default=None, description="Constraints to apply to the idea.")


class GetIntakeAnalysisArgs(ToolArgs):
    """Arguments for `get_intake_analysis` (none)."""


class ApproveIntakeArgs(ToolArgs):
    """Arguments for `approve_intake` (none)."""


INTAKE_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="submit_idea",
        group=ToolGroup.INTAKE,
        description="Submit a film idea and run the intake analysis on it.",
        args=SubmitIdeaArgs,
        handler=submit_idea,
        mutates=True,
        active_project=True,
    ),
    ToolSpec(
        name="get_intake_analysis",
        group=ToolGroup.INTAKE,
        description="Read the intake analysis produced for the active project's idea.",
        args=GetIntakeAnalysisArgs,
        handler=get_intake_analysis,
        active_project=True,
    ),
    ToolSpec(
        name="approve_intake",
        group=ToolGroup.INTAKE,
        description="Approve the intake analysis and advance the project to constitution.",
        args=ApproveIntakeArgs,
        handler=approve_intake,
        mutates=True,
        confirm=True,
        active_project=True,
    ),
)
