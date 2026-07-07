"""Generation batch planning, prompt preview, and spend approval tools."""

from __future__ import annotations

import contextlib
from typing import Any

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.mcp.tools.generation._text_only import (
    _complete_text_only_generation,
    _is_text_only_policy,
)

from ..helpers import _active_project_id, _error, _ok, _services


async def plan_generation_batch(args: dict[str, object]) -> dict[str, object]:
    """Plan a generation batch: add rows to the ledger for each shot.

    Reads shot IDs from the shot bible artifact if none are provided.
    In text-only policy mode, no media is generated; completed requests are
    created directly so the graph can advance to delivery.
    """
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])

    if _is_text_only_policy(active):
        return _complete_text_only_generation(rt, active, project_id)

    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(_services(rt).artifact_store)

    provider = str(args.get("provider", "mock-video-provider"))
    model = str(args.get("model", "mock-fast"))
    prompt_ref = str(args.get("prompt_ref", ""))
    mode_str = str(args.get("mode", "test"))
    from film_pipeline.schemas._base import GenerationMode

    mode = GenerationMode.TEST
    with contextlib.suppress(ValueError):
        mode = GenerationMode(mode_str)

    # Collect shot IDs — from args, or from the latest shot matrix artifact
    raw_shot_ids = args.get("shot_ids", [])
    shot_ids: list[str] = []
    if isinstance(raw_shot_ids, list):
        shot_ids = [str(s) for s in raw_shot_ids if str(s).strip()]
    if not shot_ids:
        from film_pipeline.generation.executor import GenerationExecutor

        executor = GenerationExecutor(_services(rt).artifact_store, rt.provider_adapters)
        shot_ids = executor.shot_ids(project_id)

    if not shot_ids:
        return _error(
            "No shot IDs to plan. Provide shot_ids or approve shot_bible so the shot matrix exists."
        )

    ledger = mgr.plan_batch(
        project_id=project_id,
        shot_ids=shot_ids,
        provider=provider,
        model=model,
        prompt_ref=prompt_ref,
        mode=mode,
    )
    _sync_generation_requests_from_ledger(active, ledger.rows)
    return _ok(
        planned=len(shot_ids),
        total_rows=len(ledger.rows),
        rows=[
            {
                "generation_id": r.generation_id,
                "shot_id": r.shot_id,
                "status": str(r.status.value),
            }
            for r in ledger.rows
            if r.shot_id in shot_ids
        ],
    )


async def preview_generation_prompts(args: dict[str, object]) -> dict[str, object]:
    """Resolve the exact prompt each shot will send to its provider.

    Available as soon as the shot matrix exists so the operator can read and
    validate prompts during gen_planning review — before any spend.
    """
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    from film_pipeline.app.services.errors import ServiceError
    from film_pipeline.app.services.operator import OperatorService

    try:
        previews = OperatorService(rt).preview_generation_prompts(project_id)
    except ServiceError as exc:
        return _error(str(exc))
    return _ok(previews=previews)


async def approve_generation_spend(args: dict[str, object]) -> dict[str, object]:
    """Approve spend: mark PREPARED rows as SUBMITTED with optional budget gate."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    if _is_text_only_policy(active):
        return _ok(text_only=True, approved=0)
    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(_services(rt).artifact_store)

    # Budget gate: reject if max_cost_usd set and cost exceeds it
    max_cost_raw = args.get("max_cost_usd", -1)
    max_cost = float(str(max_cost_raw)) if max_cost_raw not in (-1, None) else -1.0

    try:
        ledger = mgr.approve_spend(project_id, max_cost_usd=max_cost)
    except ValueError as e:
        return _error(str(e))

    submitted = [r for r in ledger.rows if r.status.value == "submitted"]
    _sync_generation_requests_from_ledger(active, submitted)
    estimated_total = mgr.estimate_total_cost(project_id)
    return _ok(
        approved=len(submitted),
        total_rows=len(ledger.rows),
        estimated_total_cost_usd=estimated_total,
    )


def _sync_generation_requests_from_ledger(active: dict[str, Any], rows: list[Any]) -> None:
    """Publish dispatchable generation requests from ledger rows into graph state."""
    requests: list[dict[str, object]] = []
    for row in rows:
        shot_id = str(getattr(row, "shot_id", ""))
        if not shot_id:
            continue
        prompt_ref = str(getattr(row, "prompt_ref", ""))
        requests.append(
            {
                "generation_request_id": str(getattr(row, "generation_request_id", "")),
                "generation_id": str(getattr(row, "generation_id", "")),
                "project_id": str(getattr(row, "project_id", active.get("project_id", ""))),
                "shot_id": shot_id,
                "mode": str(getattr(getattr(row, "mode", ""), "value", getattr(row, "mode", ""))),
                "provider": str(getattr(row, "provider", "")),
                "model": str(getattr(row, "model", "")),
                "prompt_ref": prompt_ref,
                "prompt_payload": {
                    "prompt_ref": prompt_ref,
                    "shot_id": shot_id,
                },
                "reference_refs": list(getattr(row, "reference_refs", [])),
                "status": str(
                    getattr(getattr(row, "status", ""), "value", getattr(row, "status", ""))
                ),
            }
        )
    active["generation_requests"] = requests
