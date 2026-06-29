"""Generation batch planning, approval, status, and lifecycle tools."""

from __future__ import annotations

import contextlib
from typing import Any

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _active_project_id, _error, _ok, _services


async def plan_generation_batch(args: dict[str, object]) -> dict[str, object]:
    """Plan a generation batch: add rows to the ledger for each shot.

    Reads shot IDs from the shot bible artifact if none are provided.
    """
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
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

    # Collect shot IDs — from args, or from shot bible artifact
    raw_shot_ids = args.get("shot_ids", [])
    shot_ids: list[str] = []
    if isinstance(raw_shot_ids, list):
        shot_ids = [str(s) for s in raw_shot_ids]
    else:
        # Try the shot bible
        try:
            from film_pipeline.schemas._base import FilmPhase

            data = _services(rt).artifact_store.load(
                project_id, FilmPhase("shot_bible"), "shot_bible", 1
            )
            shot_ids = [
                str(s.get("shot_id", s.get("scene_id", "")))
                for s in data.get("shots", data.get("scenes", []))
            ]
        except (FileNotFoundError, ValueError):
            return _error("No shot_ids provided and no shot bible found.")

    if not shot_ids:
        return _error("No shot IDs to plan.")

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


async def approve_generation_spend(args: dict[str, object]) -> dict[str, object]:
    """Approve spend: mark PREPARED rows as SUBMITTED with optional budget gate."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
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


async def get_generation_status(args: dict[str, object]) -> dict[str, object]:
    """Get status of a generation by id."""
    generation_id = str(args.get("generation_id", ""))
    if not generation_id:
        return _error("generation_id is required.")
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
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
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationStatus

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    terminal = {
        GenerationStatus.COMPLETED,
        GenerationStatus.FAILED,
        GenerationStatus.CANCELLED,
        GenerationStatus.TIMED_OUT,
    }
    all_rows = mgr.list_rows(project_id)
    active_rows = [r for r in all_rows if r.status not in terminal]
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


async def start_generation_batch(args: dict[str, object]) -> dict[str, object]:
    """Submit all SUBMITTED generation rows to their providers.

    Each row is submitted to its provider. The provider_job_id is persisted
    in the ledger row. Partial failures are recorded per-row.
    """
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationStatus

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    submitted_rows = mgr.list_rows(project_id, status=GenerationStatus.SUBMITTED)

    if not submitted_rows:
        return _ok(submitted=0, message="No SUBMITTED rows to start. Approve spend first.")

    successes: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []

    for row in submitted_rows:
        # Skip rows that already have a provider_job_id (duplicate-prevention)
        if row.provider_job_id:
            successes.append(
                {
                    "generation_id": row.generation_id,
                    "shot_id": row.shot_id,
                    "provider_job_id": row.provider_job_id,
                    "note": "already-submitted",
                }
            )
            continue

        adapter = rt.get_provider(row.provider)
        if adapter is None:
            mgr.update_row(
                project_id,
                row.generation_id,
                status=GenerationStatus.FAILED,
                error_code="unknown_provider",
                blocking_reason=f"Provider '{row.provider}' not registered.",
            )
            failures.append(
                {
                    "generation_id": row.generation_id,
                    "shot_id": row.shot_id,
                    "error": f"Provider '{row.provider}' not registered.",
                }
            )
            continue

        # Build payload and submit
        try:
            payload = adapter.build_payload(
                prompt=row.prompt_ref,
                references=row.reference_refs or None,
                duration=5.0,
            )
            job = adapter.submit(payload, row.shot_id)
        except Exception as exc:
            mgr.update_row(
                project_id,
                row.generation_id,
                status=GenerationStatus.FAILED,
                error_code="submit_failed",
                blocking_reason=str(exc)[:200],
            )
            failures.append(
                {
                    "generation_id": row.generation_id,
                    "shot_id": row.shot_id,
                    "error": str(exc)[:200],
                }
            )
            continue

        # Persist provider_job_id
        mgr.update_row(
            project_id,
            row.generation_id,
            provider_job_id=job.job_id,
            status=GenerationStatus.RUNNING,
            next_action="poll",
        )
        successes.append(
            {
                "generation_id": row.generation_id,
                "shot_id": row.shot_id,
                "provider_job_id": job.job_id,
            }
        )

    return _ok(
        submitted=len(successes),
        failed=len(failures),
        successes=successes,
        failures=failures,
    )


async def resume_generation_polling(args: dict[str, object]) -> dict[str, object]:
    """Poll the provider for a generation's status and update the ledger."""
    generation_id = str(args.get("generation_id", ""))
    if not generation_id:
        return _error("generation_id is required.")
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from datetime import UTC, datetime

    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    row = mgr.get_row(project_id, generation_id)
    if row is None:
        return _error(f"Generation '{generation_id}' not found.")
    if not row.provider_job_id:
        return _error(f"Generation '{generation_id}' has no provider_job_id — not yet submitted.")

    adapter = rt.get_provider(row.provider)
    if adapter is None:
        return _error(f"Provider '{row.provider}' not registered.")

    from film_pipeline.providers.base import ProviderJob
    from film_pipeline.schemas._base import GenerationStatus

    job = ProviderJob(
        job_id=row.provider_job_id,
        shot_id=row.shot_id,
        provider_id=row.provider,
        model=row.model,
        status="submitted",
        polls=row.poll_count,
    )
    try:
        result = adapter.poll(job)
    except Exception as exc:
        mgr.update_row(
            project_id,
            generation_id,
            error_code="poll_failed",
            blocking_reason=str(exc)[:200],
        )
        return _error(f"Poll failed: {exc}")

    status_map: dict[str, GenerationStatus] = {
        "completed": GenerationStatus.COMPLETED,
        "failed": GenerationStatus.FAILED,
        "submitted": GenerationStatus.SUBMITTED,
        "processing": GenerationStatus.RUNNING,
    }
    new_status = status_map.get(result.status, GenerationStatus.RUNNING)

    mgr.update_row(
        project_id,
        generation_id,
        status=new_status,
        poll_count=result.polls,
        last_polled_at=datetime.now(UTC),
    )
    return _ok(
        generation_id=generation_id,
        shot_id=row.shot_id,
        status=str(new_status.value),
        poll_count=result.polls,
    )


async def cancel_generation_request(args: dict[str, object]) -> dict[str, object]:
    """Cancel a generation and update the ledger."""
    generation_id = str(args.get("generation_id", ""))
    if not generation_id:
        return _error("generation_id is required.")
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationStatus

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    row = mgr.get_row(project_id, generation_id)
    if row is None:
        return _error(f"Generation '{generation_id}' not found.")
    if not row.provider_job_id:
        mgr.update_row(
            project_id,
            generation_id,
            status=GenerationStatus.CANCELLED,
            next_action="stop",
        )
        return _ok(generation_id=generation_id, cancelled=True, provider=False)

    adapter = rt.get_provider(row.provider)
    if adapter is None:
        return _error(f"Provider '{row.provider}' not registered.")

    from film_pipeline.providers.base import ProviderJob

    job = ProviderJob(
        job_id=row.provider_job_id,
        shot_id=row.shot_id,
        provider_id=row.provider,
        model=row.model,
        status="submitted",
    )
    cancelled = adapter.cancel(job)
    if cancelled:
        mgr.update_row(
            project_id,
            generation_id,
            status=GenerationStatus.CANCELLED,
            next_action="stop",
        )
    return _ok(
        generation_id=generation_id,
        cancelled=cancelled,
        provider=bool(row.provider_job_id),
    )


async def promote_test_to_production(args: dict[str, object]) -> dict[str, object]:
    """Promote completed TEST generation rows to PRODUCTION mode.

    Only rows with mode=TEST and status=COMPLETED are eligible.
    Provide ``shot_ids`` to promote specific shots, or omit to promote all eligible.
    """
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
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
