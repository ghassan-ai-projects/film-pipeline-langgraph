"""Generation dispatch lifecycle: start, resume polling, cancel."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.mcp.tools.generation._text_only import (
    _is_text_only_policy,
)

from ..helpers import _error, _ok, _services


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
    if _is_text_only_policy(active):
        return _ok(text_only=True, submitted=0)
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
