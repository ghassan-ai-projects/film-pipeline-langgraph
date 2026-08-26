"""Generation dispatch lifecycle: start, resume polling, cancel."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.mcp.tools.generation._text_only import (
    _is_text_only_policy,
)

from ..helpers import _error, _ok, _services

if TYPE_CHECKING:
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.providers.base import BaseProviderAdapter, ProviderJob
    from film_pipeline.schemas._base import GenerationStatus
    from film_pipeline.schemas.generation import GenerationLedgerRow


def _submit_failure(
    mgr: GenerationLedgerManager,
    project_id: str,
    row: GenerationLedgerRow,
    error_code: str,
    reason: str,
) -> dict[str, str]:
    """Mark a ledger row FAILED and build its failure record."""
    from film_pipeline.schemas._base import GenerationStatus

    mgr.update_row(
        project_id,
        row.generation_id,
        status=GenerationStatus.FAILED,
        error_code=error_code,
        blocking_reason=reason,
    )
    return {
        "generation_id": row.generation_id,
        "shot_id": row.shot_id,
        "error": reason,
    }


def _submit_one_row(
    rt: Any,
    mgr: GenerationLedgerManager,
    project_id: str,
    row: GenerationLedgerRow,
    duration_seconds: float,
) -> tuple[bool, dict[str, str]]:
    """Submit one SUBMITTED ledger row to its provider.

    Returns ``(succeeded, entry)`` where *entry* is the per-row success or
    failure record for the response envelope.
    """
    # Skip rows that already have a provider_job_id (duplicate-prevention)
    if row.provider_job_id:
        return (
            True,
            {
                "generation_id": row.generation_id,
                "shot_id": row.shot_id,
                "provider_job_id": row.provider_job_id,
                "note": "already-submitted",
            },
        )

    adapter = rt.get_provider(row.provider)
    if adapter is None:
        reason = f"Provider '{row.provider}' not registered."
        return False, _submit_failure(mgr, project_id, row, "unknown_provider", reason)

    # Build payload and submit
    try:
        payload = adapter.build_payload(
            prompt=row.prompt_ref,
            references=row.reference_refs or None,
            duration=duration_seconds,
        )
        job = adapter.submit(payload, row.shot_id)
    except Exception as exc:
        return (
            False,
            _submit_failure(mgr, project_id, row, "submit_failed", str(exc)[:200]),
        )

    return True, _mark_row_running(mgr, project_id, row, job.job_id)


def _mark_row_running(
    mgr: GenerationLedgerManager,
    project_id: str,
    row: GenerationLedgerRow,
    provider_job_id: str,
) -> dict[str, str]:
    """Persist the provider_job_id on the row and build its success record."""
    from film_pipeline.schemas._base import GenerationStatus

    mgr.update_row(
        project_id,
        row.generation_id,
        provider_job_id=provider_job_id,
        status=GenerationStatus.RUNNING,
        next_action="poll",
    )
    return {
        "generation_id": row.generation_id,
        "shot_id": row.shot_id,
        "provider_job_id": provider_job_id,
    }


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

    from film_pipeline.generation.executor import GenerationExecutor
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationStatus

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    submitted_rows = mgr.list_rows(project_id, status=GenerationStatus.SUBMITTED)
    if not submitted_rows:
        return _ok(submitted=0, message="No SUBMITTED rows to start. Approve spend first.")

    successes: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    shot_rows = {
        str(shot.get("shot_id", "")): shot
        for shot in GenerationExecutor(
            _services(rt).artifact_store, rt.provider_adapters
        ).load_shot_rows(project_id)
    }
    for row in submitted_rows:
        duration = float(shot_rows.get(row.shot_id, {}).get("duration_seconds", 5) or 5)
        succeeded, entry = _submit_one_row(rt, mgr, project_id, row, duration)
        (successes if succeeded else failures).append(entry)

    return _ok(
        submitted=len(successes),
        failed=len(failures),
        successes=successes,
        failures=failures,
    )


def _poll_row_status(
    mgr: GenerationLedgerManager,
    project_id: str,
    generation_id: str,
    adapter: BaseProviderAdapter,
    job: ProviderJob,
) -> tuple[str, int] | str:
    """Poll the provider job, recording poll failures on the ledger row.

    Returns ``(provider_status, polls)`` or the error message on failure.
    """
    try:
        result = adapter.poll(job)
    except Exception as exc:
        mgr.update_row(
            project_id,
            generation_id,
            error_code="poll_failed",
            blocking_reason=str(exc)[:200],
        )
        return f"Poll failed: {exc}"
    return result.status, result.polls


def _generation_status(provider_status: str) -> GenerationStatus:
    """Map a provider job status to its ledger generation status."""
    from film_pipeline.providers.base import ProviderJobStatus
    from film_pipeline.schemas._base import GenerationStatus

    try:
        job_status = ProviderJobStatus(provider_status)
    except ValueError:
        return GenerationStatus.RUNNING
    return {
        ProviderJobStatus.COMPLETED: GenerationStatus.COMPLETED,
        ProviderJobStatus.FAILED: GenerationStatus.FAILED,
        ProviderJobStatus.SUBMITTED: GenerationStatus.SUBMITTED,
        ProviderJobStatus.PROCESSING: GenerationStatus.RUNNING,
    }.get(job_status, GenerationStatus.RUNNING)


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
    from film_pipeline.providers.base import ProviderJob, ProviderJobStatus

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    row = mgr.get_row(project_id, generation_id)
    if row is None:
        return _error(f"Generation '{generation_id}' not found.")
    if not row.provider_job_id:
        return _error(f"Generation '{generation_id}' has no provider_job_id — not yet submitted.")

    adapter = rt.get_provider(row.provider)
    if adapter is None:
        return _error(f"Provider '{row.provider}' not registered.")

    job = ProviderJob(
        job_id=row.provider_job_id,
        shot_id=row.shot_id,
        provider_id=row.provider,
        model=row.model,
        status=ProviderJobStatus.SUBMITTED,
        polls=row.poll_count,
    )
    polled = _poll_row_status(mgr, project_id, generation_id, adapter, job)
    if isinstance(polled, str):
        return _error(polled)
    provider_status, polls = polled

    new_status = _generation_status(provider_status)
    mgr.update_row(
        project_id,
        generation_id,
        status=new_status,
        poll_count=polls,
        last_polled_at=datetime.now(UTC),
    )
    return _ok(
        generation_id=generation_id,
        shot_id=row.shot_id,
        status=str(new_status.value),
        poll_count=polls,
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

    from film_pipeline.providers.base import ProviderJob, ProviderJobStatus

    job = ProviderJob(
        job_id=row.provider_job_id,
        shot_id=row.shot_id,
        provider_id=row.provider,
        model=row.model,
        status=ProviderJobStatus.SUBMITTED,
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
