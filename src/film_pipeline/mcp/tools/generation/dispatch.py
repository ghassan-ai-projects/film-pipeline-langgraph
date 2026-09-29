"""Generation dispatch lifecycle: start, resume polling, cancel.

Transport only: each handler resolves the active project, drives the owning
lifecycle in ``film_pipeline.generation.executor``, and projects its typed
per-row outcomes into a response envelope. No status mapping, delivery, or
ledger write lives here.
"""

from __future__ import annotations

from pydantic import Field

from film_pipeline.filmspec import is_text_only_policy
from film_pipeline.generation.executor import (
    GenerationExecutor,
    GenerationRowError,
    GenerationRowOutcome,
    RowOutcomeKind,
)
from film_pipeline.generation.ledger import GenerationLedgerManager
from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec
from film_pipeline.schemas.base import GenerationStatus

from ..helpers import (
    _error,
    _ok,
    _services,
)


def _submission_entry(outcome: GenerationRowOutcome) -> dict[str, str]:
    """Project one successful submit outcome into its per-row response record."""
    entry = {
        "generation_id": outcome.generation_id,
        "shot_id": outcome.shot_id,
        "provider_job_id": outcome.provider_job_id,
    }
    if outcome.kind is RowOutcomeKind.ALREADY_SUBMITTED:
        entry["note"] = "already-submitted"
    return entry


def _submission_failure(outcome: GenerationRowOutcome) -> dict[str, str]:
    """Project one failed submit outcome into its per-row response record."""
    return {
        "generation_id": outcome.generation_id,
        "shot_id": outcome.shot_id,
        "error": outcome.detail,
    }


async def start_generation_batch(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Submit all SUBMITTED generation rows to their providers.

    Submission belongs to ``generation.GenerationExecutor``: this handler
    resolves the active project and projects the executor's typed per-row
    outcomes into the response envelope. Partial failures stay per-row.
    """
    rt = ctx.runtime
    active = ctx.project_state()
    project_id = str(active["project_id"])
    if is_text_only_policy(active):
        return _ok(text_only=True, submitted=0)

    store = _services(rt).artifact_store
    mgr = GenerationLedgerManager(store)
    if not mgr.list_rows(project_id, status=GenerationStatus.SUBMITTED):
        return _ok(submitted=0, message="No SUBMITTED rows to start. Approve spend first.")

    result = GenerationExecutor(store, rt.provider_adapters).start(project_id)
    successes = [
        _submission_entry(outcome) for outcome in result.outcomes if not outcome.operator_error
    ]
    failures = [
        _submission_failure(outcome) for outcome in result.outcomes if outcome.operator_error
    ]
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
    """Cancel a generation through the owning lifecycle.

    ``generation.GenerationExecutor`` owns the cancel transition, including the
    local case (no provider job) and a provider that refuses. This handler
    resolves the active project and reports which of those happened.
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
        result = executor.cancel_row(project_id, generation_id)
    except GenerationRowError as exc:
        return _error(str(exc))

    row = GenerationLedgerManager(store).get_row(project_id, generation_id)
    if row is None:  # pragma: no cover - cancel_row proved the row exists
        return _error(f"Generation '{generation_id}' not found.")
    refused = result.first(RowOutcomeKind.CANCEL_REFUSED) is not None
    return _ok(
        generation_id=generation_id,
        cancelled=not refused,
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
