"""Coverage and assembly/delivery tools (mostly stubs pending full wiring)."""

from __future__ import annotations

from typing import cast

from film_pipeline.mcp.tools.context import ToolContext

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
