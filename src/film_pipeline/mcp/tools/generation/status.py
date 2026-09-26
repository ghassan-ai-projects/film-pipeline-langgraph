"""Generation status and active-generation listing tools."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg

from ..helpers import (
    _error,
    _ok,
    _services,
    require_project_id,
)


async def get_generation_status(args: dict[str, object]) -> dict[str, object]:
    """Get status of a generation by id."""
    generation_id = str(args.get("generation_id", ""))
    if not generation_id:
        return _error("generation_id is required.")
    rt = tools_pkg.get_runtime()
    project_id = require_project_id(args)
    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    row = mgr.get_row(project_id, generation_id)
    if row is None:
        return _error(f"Generation '{generation_id}' not found.")
    return _ok(
        generation_id=row.generation_id,
        shot_id=row.shot_id,
        status=str(row.status.value),
        provider_job_id=row.provider_job_id,
        submitted_at=str(row.submitted_at) if row.submitted_at else None,
        poll_count=row.poll_count,
        estimated_cost_usd=row.estimated_cost_usd,
        next_action=row.next_action,
    )


async def list_active_generations(args: dict[str, object]) -> dict[str, object]:
    """List active (non-terminal) generation rows."""
    rt = tools_pkg.get_runtime()
    project_id = require_project_id(args)
    from film_pipeline.generation.ledger import GenerationLedgerManager, is_terminal
    from film_pipeline.schemas.base import FilmPhase

    # Guard against the read creating an artifact: the ledger manager's load()
    # persists a new empty ledger when none exists, so without this a status
    # refresh on an unplanned project writes one. GenerationExecutor.has_ledger
    # carries the same guard, expressed as these two store primitives.
    store = _services(rt).artifact_store
    has_ledger = (
        store.mutable_exists(project_id, FilmPhase.GENERATION, "generation_ledger")
        or store.next_version(project_id, FilmPhase.GENERATION.value, "generation_ledger") > 1
    )
    if not has_ledger:
        return _ok(count=0, rows=[])

    # Terminality is owned by the ledger's state machine. This handler used to
    # hand-roll the same four-member set from a ten-member enum.
    mgr = GenerationLedgerManager(store)
    active_rows = [r for r in mgr.list_rows(project_id) if not is_terminal(r.status)]
    return _ok(
        count=len(active_rows),
        rows=[
            {
                "generation_id": r.generation_id,
                "shot_id": r.shot_id,
                "status": str(r.status.value),
                "provider_job_id": r.provider_job_id,
                "next_action": r.next_action,
            }
            for r in active_rows
        ],
    )
