"""Generation dispatch lifecycle: start, resume polling, cancel."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import Field

from film_pipeline.filmspec import is_text_only_policy
from film_pipeline.generation.executor import (
    GenerationExecutor,
    GenerationRowError,
)
from film_pipeline.generation.ledger import GenerationLedgerManager
from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec
from film_pipeline.providers.base import ProviderJob, ProviderJobStatus
from film_pipeline.schemas.base import GenerationStatus

from ..helpers import (
    _error,
    _ok,
    _services,
)

if TYPE_CHECKING:
    from film_pipeline.schemas.generation import GenerationLedgerRow


def _submit_failure(
    mgr: GenerationLedgerManager,
    project_id: str,
    row: GenerationLedgerRow,
    error_code: str,
    reason: str,
) -> dict[str, str]:
    """Mark a ledger row FAILED and build its failure record.

    ``next_action`` is set to ``wait_human`` to match
    ``GenerationExecutor._fail_row``: a failed row needs a human decision, and
    leaving the pre-existing ``poll`` in place told the operator to keep polling
    a row that can never advance.
    """

    mgr.update_row(
        project_id,
        row.generation_id,
        status=GenerationStatus.FAILED,
        error_code=error_code,
        blocking_reason=reason,
        next_action="wait_human",
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
    shot_row: dict[str, Any],
    executor: Any,
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

    # Build payload and submit. The prompt is RESOLVED, not the raw
    # ``prompt_ref``: that field is an artifact reference string, so passing it
    # straight to ``build_payload`` submitted a literal like
    # "artifact:gen_planning:prompt_package:v1" — or an empty string — as the
    # prompt text for every MCP-driven generation. GenerationExecutor resolves
    # it through this same method; the two surfaces now agree.
    prompt = executor.resolve_prompt(project_id, row.shot_id, shot_row, row.prompt_ref)
    try:
        payload = adapter.build_payload(
            prompt=prompt,
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


async def start_generation_batch(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Submit all SUBMITTED generation rows to their providers.

    Each row is submitted to its provider. The provider_job_id is persisted
    in the ledger row. Partial failures are recorded per-row.
    """
    rt = ctx.runtime
    active = ctx.project_state()
    project_id = str(active["project_id"])
    if is_text_only_policy(active):
        return _ok(text_only=True, submitted=0)

    mgr = GenerationLedgerManager(_services(rt).artifact_store)
    submitted_rows = mgr.list_rows(project_id, status=GenerationStatus.SUBMITTED)
    if not submitted_rows:
        return _ok(submitted=0, message="No SUBMITTED rows to start. Approve spend first.")

    successes: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    executor = GenerationExecutor(_services(rt).artifact_store, rt.provider_adapters)
    shot_rows = {str(shot.get("shot_id", "")): shot for shot in executor.load_shot_rows(project_id)}
    for row in submitted_rows:
        shot_row = shot_rows.get(row.shot_id, {})
        duration = float(shot_row.get("duration_seconds", 5) or 5)
        succeeded, entry = _submit_one_row(rt, mgr, project_id, row, duration, shot_row, executor)
        (successes if succeeded else failures).append(entry)

    return _ok(
        submitted=len(successes),
        failed=len(failures),
        successes=successes,
        failures=failures,
    )


async def resume_generation_polling(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Poll the provider for a generation's status through the owning lifecycle.

    ``generation.GenerationExecutor`` owns the transition: this handler resolves
    the active project, asks it to poll one row, and projects the typed outcome.
    It maps no provider status, downloads nothing, and writes no ledger row of
    its own — that duplication is what let an MCP-driven completion reach
    ``COMPLETED`` without the delivered output the executor requires.
    """
    generation_id = str(args.get("generation_id", ""))
    if not generation_id:
        return _error("generation_id is required.")
    rt = ctx.runtime
    active = ctx.project_state()
    project_id = str(active["project_id"])

    store = _services(rt).artifact_store
    executor = GenerationExecutor(store, rt.provider_adapters)
    try:
        result = executor.poll_row(project_id, generation_id)
    except GenerationRowError as exc:
        return _error(str(exc))

    row = GenerationLedgerManager(store).get_row(project_id, generation_id)
    if row is None:  # pragma: no cover - poll_row proved the row exists
        return _error(f"Generation '{generation_id}' not found.")
    for outcome in result.outcomes:
        if outcome.operator_error:
            return _error(f"Poll failed: {outcome.detail}")
    return _ok(
        generation_id=generation_id,
        shot_id=row.shot_id,
        status=str(row.status.value),
        poll_count=row.poll_count,
    )


async def cancel_generation_request(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Cancel a generation and update the ledger."""
    generation_id = str(args.get("generation_id", ""))
    if not generation_id:
        return _error("generation_id is required.")
    rt = ctx.runtime
    active = ctx.project_state()
    project_id = str(active["project_id"])

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


class StartGenerationBatchArgs(ToolArgs):
    """Arguments for `start_generation_batch` (none)."""


class ResumeGenerationPollingArgs(ToolArgs):
    """Arguments for `resume_generation_polling`."""

    generation_id: str = Field(description="Generation request to resume polling.")


class CancelGenerationRequestArgs(ToolArgs):
    """Arguments for `cancel_generation_request`."""

    generation_id: str = Field(description="Generation request to cancel.")


GENERATION_DISPATCH_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="start_generation_batch",
        group=ToolGroup.GENERATION,
        description="Submit the prepared generation rows to their providers.",
        args=StartGenerationBatchArgs,
        handler=start_generation_batch,
        mutates=True,
        active_project=True,
    ),
    ToolSpec(
        name="resume_generation_polling",
        group=ToolGroup.GENERATION,
        description="Resume polling a generation request whose provider job is still running.",
        args=ResumeGenerationPollingArgs,
        handler=resume_generation_polling,
        mutates=True,
        active_project=True,
    ),
    ToolSpec(
        name="cancel_generation_request",
        group=ToolGroup.GENERATION,
        description="Cancel a generation request and stop polling its provider job.",
        args=CancelGenerationRequestArgs,
        handler=cancel_generation_request,
        mutates=True,
        active_project=True,
    ),
)
