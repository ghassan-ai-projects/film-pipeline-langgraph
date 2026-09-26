"""Promote a test-kind project to production."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import (
    _ok,
    _services,
    require_project_state,
)


async def promote_test_to_production(args: dict[str, object]) -> dict[str, object]:
    """Promote completed TEST generation rows to PRODUCTION mode.

    Only rows with mode=TEST and status=COMPLETED are eligible.
    Provide ``shot_ids`` to promote specific shots, or omit to promote all eligible.
    """
    rt = tools_pkg.get_runtime()
    active = require_project_state(args)
    project_id = str(active["project_id"])
    from film_pipeline.generation.ledger import GenerationLedgerManager

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
