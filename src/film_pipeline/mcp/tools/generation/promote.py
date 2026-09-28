"""Promote a test-kind project to production."""

from __future__ import annotations

from pydantic import Field

from film_pipeline.generation.ledger import GenerationLedgerManager
from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec

from ..helpers import (
    _ok,
    _services,
)


async def promote_test_to_production(
    ctx: ToolContext, args: dict[str, object]
) -> dict[str, object]:
    """Promote completed TEST generation rows to PRODUCTION mode.

    Only rows with mode=TEST and status=COMPLETED are eligible.
    Provide ``shot_ids`` to promote specific shots, or omit to promote all eligible.
    """
    rt = ctx.runtime
    active = ctx.project_state()
    project_id = str(active["project_id"])

    mgr = GenerationLedgerManager(_services(rt).artifact_store)

    raw_shot_ids = args.get("shot_ids")
    shot_ids: list[str] | None = None
    if raw_shot_ids and isinstance(raw_shot_ids, list):
        shot_ids = [str(s) for s in raw_shot_ids if s]

    count, promoted_ids = mgr.promote_to_production(project_id, shot_ids=shot_ids)
    return _ok(
        promoted=count,
        generation_ids=promoted_ids,
        message=f"{count} generation(s) promoted to PRODUCTION mode.",
    )


# ── Tool declarations ────────────────────────────────────────────────────────
# Declared next to the handlers they describe (doc 04 slice 1).


class PromoteTestToProductionArgs(ToolArgs):
    """Arguments for `promote_test_to_production`."""

    shot_ids: object = Field(
        default=None, description="Shot ids to promote; empty promotes every completed test row."
    )


GENERATION_PROMOTE_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="promote_test_to_production",
        group=ToolGroup.GENERATION,
        description="Promote completed TEST-mode generations to PRODUCTION.",
        args=PromoteTestToProductionArgs,
        handler=promote_test_to_production,
        mutates=True,
        confirm=True,
        active_project=True,
    ),
)
