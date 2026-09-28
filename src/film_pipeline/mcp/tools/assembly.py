"""Coverage and assembly/delivery tools (mostly stubs pending full wiring)."""

from __future__ import annotations

from typing import cast

from pydantic import Field

from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec

from .helpers import (
    _ok,
    _stub,
)


async def plan_coverage_group(args: dict[str, object]) -> dict[str, object]:
    return _stub("plan_coverage_group")


async def list_coverage_groups(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_coverage_groups")


async def inspect_coverage_group(args: dict[str, object]) -> dict[str, object]:
    return _stub("inspect_coverage_group")


async def approve_coverage_generation(args: dict[str, object]) -> dict[str, object]:
    return _stub("approve_coverage_generation")


# --- Assembly tools ------------------------------------------------------


async def assemble_review_cut(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Assemble a review cut using the AssemblyAgent."""
    active = ctx.project_state()
    from film_pipeline.post.assembly_agent import AssemblyAgent

    agent = AssemblyAgent()
    plan = agent.build_plan(
        project_id=active["project_id"],
        shot_ids=cast(list[str], args.get("shot_ids", [])),
        clip_paths=cast(list[str], args.get("clip_paths", [])),
    )
    issues = agent.validate_plan(plan)
    return _ok(plan_id=plan.plan_id, clip_count=plan.clip_count, issues=issues)


async def assemble_final_cut(args: dict[str, object]) -> dict[str, object]:
    return _stub("assemble_final_cut")


async def export_delivery_package(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Export a delivery package using the DeliveryPackagingAgent."""
    active = ctx.project_state()
    from film_pipeline.post.delivery_packaging_agent import DeliveryPackagingAgent

    agent = DeliveryPackagingAgent()
    package = agent.build_package(
        project_id=active["project_id"],
        video_path=str(args.get("video_path", "")),
        subtitle_path=str(args.get("subtitle_path", "")),
        audio_stems_dir=str(args.get("audio_stems_dir", "")),
        stills_dir=str(args.get("stills_dir", "")),
        validation_report_path=str(args.get("validation_report_path", "")),
        credits_path=str(args.get("credits_path", "")),
    )
    return _ok(
        package_id=package.package_id,
        is_complete=package.is_complete,
        missing=package.missing_items,
    )


# ── Tool declarations ────────────────────────────────────────────────────────
# Declared next to the handlers they describe (doc 04 slice 1).


class PlanCoverageGroupArgs(ToolArgs):
    """Arguments for `plan_coverage_group` (none)."""


class ListCoverageGroupsArgs(ToolArgs):
    """Arguments for `list_coverage_groups` (none)."""


class InspectCoverageGroupArgs(ToolArgs):
    """Arguments for `inspect_coverage_group` (none)."""


class ApproveCoverageGenerationArgs(ToolArgs):
    """Arguments for `approve_coverage_generation` (none)."""


class AssembleReviewCutArgs(ToolArgs):
    """Arguments for `assemble_review_cut`."""

    shot_ids: object = Field(default=None, description="Shots to include; empty uses them all.")
    clip_paths: object = Field(default=None, description="Explicit clip paths to concatenate.")


class AssembleFinalCutArgs(ToolArgs):
    """Arguments for `assemble_final_cut` (none)."""


class ExportDeliveryPackageArgs(ToolArgs):
    """Arguments for `export_delivery_package`.

    Every path is optional; the handler falls back to the project's own artifacts.
    """

    video_path: str = Field(default="", description="Finished video to deliver.")
    audio_stems_dir: str = Field(default="", description="Directory of audio stems.")
    subtitle_path: str = Field(default="", description="Subtitle file to include.")
    stills_dir: str = Field(default="", description="Directory of still images.")
    credits_path: str = Field(default="", description="Credits file to include.")
    validation_report_path: str = Field(default="", description="Validation report to bundle.")


COVERAGE_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="plan_coverage_group",
        group=ToolGroup.COVERAGE,
        description="Plan the coverage group a shot needs before generating it.",
        args=PlanCoverageGroupArgs,
        handler=plan_coverage_group,
        mutates=True,
    ),
    ToolSpec(
        name="list_coverage_groups",
        group=ToolGroup.COVERAGE,
        description="List the planned coverage groups and their approval state.",
        args=ListCoverageGroupsArgs,
        handler=list_coverage_groups,
    ),
    ToolSpec(
        name="inspect_coverage_group",
        group=ToolGroup.COVERAGE,
        description="Inspect one coverage group's shots, variants and readiness.",
        args=InspectCoverageGroupArgs,
        handler=inspect_coverage_group,
    ),
    ToolSpec(
        name="approve_coverage_generation",
        group=ToolGroup.COVERAGE,
        description="Approve a planned coverage group so its variants may be generated.",
        args=ApproveCoverageGenerationArgs,
        handler=approve_coverage_generation,
        mutates=True,
        confirm=True,
    ),
)

ASSEMBLY_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="assemble_review_cut",
        group=ToolGroup.ASSEMBLY,
        description="Assemble a review cut from the approved shots' clips.",
        args=AssembleReviewCutArgs,
        handler=assemble_review_cut,
        mutates=True,
        active_project=True,
    ),
    ToolSpec(
        name="assemble_final_cut",
        group=ToolGroup.ASSEMBLY,
        description="Assemble the final cut from the approved review cut.",
        args=AssembleFinalCutArgs,
        handler=assemble_final_cut,
        mutates=True,
    ),
    ToolSpec(
        name="export_delivery_package",
        group=ToolGroup.ASSEMBLY,
        description="Bundle the finished film and its delivery assets into one package.",
        args=ExportDeliveryPackageArgs,
        handler=export_delivery_package,
        mutates=True,
        confirm=True,
        active_project=True,
    ),
)
