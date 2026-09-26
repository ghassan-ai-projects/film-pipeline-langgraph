"""Generation batch planning, prompt preview, and spend approval tools."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.mcp.tools.generation._text_only import (
    _complete_text_only_generation,
    _is_text_only_policy,
)

from ..helpers import (
    _active_project_id,
    _error,
    _no_active_project,
    _ok,
    _services,
)

if TYPE_CHECKING:
    from film_pipeline.schemas.base import GenerationMode
    from film_pipeline.schemas.generation import GenerationLedgerRow


def _resolve_generation_mode(args: dict[str, object]) -> GenerationMode:
    """Map the optional ``mode`` argument to a GenerationMode (default TEST)."""
    from film_pipeline.schemas.base import GenerationMode

    mode_str = str(args.get("mode", "test"))
    mode = GenerationMode.TEST
    with contextlib.suppress(ValueError):
        mode = GenerationMode(mode_str)
    return mode


def _collect_shot_ids(args: dict[str, object], rt: Any, project_id: str) -> list[str]:
    """Collect shot IDs from args, falling back to the shot matrix artifact."""
    raw_shot_ids = args.get("shot_ids", [])
    shot_ids: list[str] = []
    if isinstance(raw_shot_ids, list):
        shot_ids = [str(s) for s in raw_shot_ids if str(s).strip()]
    if not shot_ids:
        from film_pipeline.generation.executor import GenerationExecutor

        executor = GenerationExecutor(_services(rt).artifact_store, rt.provider_adapters)
        shot_ids = executor.shot_ids(project_id)
    return shot_ids


def _parse_max_cost_usd(args: dict[str, object]) -> float:
    """Read the optional ``max_cost_usd`` spend cap; -1.0 means no cap."""
    max_cost_raw = args.get("max_cost_usd", -1)
    if max_cost_raw in (-1, None):
        return -1.0
    return float(str(max_cost_raw))


async def plan_generation_batch(args: dict[str, object]) -> dict[str, object]:
    """Plan a generation batch: add rows to the ledger for each shot.

    Reads shot IDs from the shot bible artifact if none are provided.
    In text-only policy mode, no media is generated; completed requests are
    created directly so the graph can advance to delivery.
    """
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _no_active_project()
    project_id = str(active["project_id"])

    if _is_text_only_policy(active):
        return _complete_text_only_generation(rt, active, project_id)

    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.providers.pricing import estimate_cost_for_duration

    mgr = GenerationLedgerManager(_services(rt).artifact_store)

    provider = str(args.get("provider", "mock-video-provider"))
    model = str(args.get("model", "mock-fast"))
    prompt_ref = str(args.get("prompt_ref", ""))
    mode = _resolve_generation_mode(args)
    shot_ids = _collect_shot_ids(args, rt, project_id)
    if not shot_ids:
        return _error(
            "No shot IDs to plan. Provide shot_ids or approve shot_bible so the shot matrix exists."
        )

    from film_pipeline.generation.executor import GenerationExecutor

    shot_rows = {
        str(row.get("shot_id", "")): row
        for row in GenerationExecutor(
            _services(rt).artifact_store, rt.provider_adapters
        ).load_shot_rows(project_id)
    }
    estimated_costs = {
        shot_id: estimate_cost_for_duration(
            provider,
            model,
            float(shot_rows.get(shot_id, {}).get("duration_seconds", 5) or 5),
        )
        for shot_id in shot_ids
    }
    ledger = mgr.plan_batch(
        project_id=project_id,
        shot_ids=shot_ids,
        provider=provider,
        model=model,
        prompt_ref=prompt_ref,
        mode=mode,
        estimated_costs=estimated_costs,
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
        return _no_active_project()
    from film_pipeline.operations.errors import ServiceError
    from film_pipeline.studio._operator_runtime import operator_service

    try:
        previews = operator_service(rt).preview_generation_prompts(project_id)
    except ServiceError as exc:
        return _error(str(exc))
    return _ok(previews=previews)


async def approve_generation_spend(args: dict[str, object]) -> dict[str, object]:
    """Approve spend: mark PREPARED rows as SUBMITTED with optional budget gate."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _no_active_project()
    project_id = str(active["project_id"])
    if _is_text_only_policy(active):
        return _ok(text_only=True, approved=0)
    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(_services(rt).artifact_store)

    # Budget gate: the manager rejects the batch when estimated cost exceeds it.
    max_cost = _parse_max_cost_usd(args)

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


def _sync_generation_requests_from_ledger(
    active: dict[str, Any], rows: list[GenerationLedgerRow]
) -> None:
    """Publish dispatchable generation requests from ledger rows into graph state."""
    requests: list[dict[str, object]] = []
    for row in rows:
        if not row.shot_id:
            continue
        requests.append(
            {
                "generation_request_id": row.generation_request_id,
                "generation_id": row.generation_id,
                "project_id": row.project_id,
                "shot_id": row.shot_id,
                "mode": row.mode.value,
                "provider": row.provider,
                "model": row.model,
                "prompt_ref": row.prompt_ref,
                "prompt_payload": {
                    "prompt_ref": row.prompt_ref,
                    "shot_id": row.shot_id,
                },
                "reference_refs": list(row.reference_refs),
                "status": row.status.value,
            }
        )
    active["generation_requests"] = requests
