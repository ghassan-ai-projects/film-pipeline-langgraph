"""Bounded per-entry generation retry loop with review-driven control flow."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, cast

from film_pipeline.mcp.tools.reference_generation.context import (
    _EntryContext,
    _GenerationBatch,
)
from film_pipeline.mcp.tools.reference_generation.entries import (
    _reference_job_id,
)

from ..helpers import _services


class _AttemptVerdict(Enum):
    """Loop-control outcome of a single generation attempt."""

    RETRY = "retry"
    FAILED = "failed"
    STOP = "stop"


@dataclass
class _LoopState:
    """Mutable state threaded through the bounded retry attempts."""

    best_score: float = 0.0
    best_attempt: int = 0
    frame_review_result: Any | None = None
    retry_prompt: str = ""
    target_path: Path | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class _RetryOutcome:
    """Result of the bounded per-entry generation retry loop."""

    best_score: float
    best_attempt: int
    frame_review_result: Any | None
    target_path: Path | None
    metadata: dict[str, object]
    failed: bool


def _record_failed_entry(
    raw: dict[str, object],
    reference_id: str,
    results: list[dict[str, object]],
    *,
    code: str,
    issue_message: str,
    result_error: str,
) -> None:
    """Record a terminal generation failure on the entry and in results."""
    raw["generation_status"] = "failed"
    raw["issues"] = [{"code": code, "message": issue_message, "severity": "blocking"}]
    raw["validation"] = {"status": "needs_regeneration", "score": 0.0, "reports": []}
    results.append({"reference_id": reference_id, "status": "failed", "error": result_error})


def _feedback_retry_prompt(prompt_text: str, frame_review_result: Any | None) -> str | None:
    """Compose the retry prompt with actionable feedback, when present."""
    feedback = frame_review_result.actionable_feedback if frame_review_result else ""
    if feedback:
        return f"{prompt_text} Fix the following: {feedback}"
    return None


def _execute_provider_attempt(
    provider: Any,
    retry_prompt: str,
    ctx: _EntryContext,
) -> tuple[Path, dict[str, object], Exception | None]:
    """Submit one provider job and rename its download into place.

    Returns the renamed target path plus metadata on success, or the raised
    exception. Rename errors intentionally propagate to the caller's caller.
    """
    try:
        payload = provider.build_payload(retry_prompt, **ctx.provider_kwargs)
        job = provider.submit(payload, ctx.shot_id)
        job = provider.poll(job)
        downloaded_path = provider.download(job, ctx.output_dir)
        metadata = provider.extract_metadata(downloaded_path)
    except Exception as exc:  # retried/recorded by the loop
        return Path(), {}, exc

    ext = Path(downloaded_path).suffix or ".png"
    target_name = f"{_reference_job_id(ctx.reference_id)}{ext}"
    target_path = Path(ctx.output_dir) / target_name
    Path(downloaded_path).rename(target_path)
    return target_path, metadata, None


def _collect_frame_review(
    batch: _GenerationBatch,
    raw: dict[str, object],
    ctx: _EntryContext,
    state: _LoopState,
) -> Any | None:
    """Run selective Gemini review for the frame; None when skipped/unavailable."""
    from film_pipeline.generation.frame_reviewer import review_frame, should_review_frame

    if not should_review_frame(raw):
        return None
    with contextlib.suppress(Exception):
        return review_frame(
            cast(Path, state.target_path),
            state.retry_prompt,
            model=_services(batch.rt).prompt_runner.model_router.resolve_or_raise(
                "visual_reasoner"
            ),
            subject_type=str(raw.get("subject_type", "character")),
            frame_id=ctx.reference_id,
        )
    return None


def _grade_generated_frame(
    batch: _GenerationBatch,
    raw: dict[str, object],
    ctx: _EntryContext,
    state: _LoopState,
    attempt: int,
) -> _AttemptVerdict:
    """Run heuristics and Gemini review for a freshly generated frame."""
    from film_pipeline.generation.frame_heuristics import run_heuristic_checks

    heuristic_result = run_heuristic_checks(
        cast(Path, state.target_path), subject_type=str(raw.get("subject_type", "character"))
    )
    if not heuristic_result.passed:
        if attempt < 2:
            return _AttemptVerdict.RETRY
        _record_failed_entry(
            raw,
            ctx.reference_id,
            batch.results,
            code="heuristic_check_failed",
            issue_message=f"Heuristics failed: {', '.join(heuristic_result.failures)}",
            result_error=f"Heuristics: {', '.join(heuristic_result.failures)}",
        )
        return _AttemptVerdict.FAILED

    state.frame_review_result = _collect_frame_review(batch, raw, ctx, state)

    review_result = state.frame_review_result
    if review_result is not None and review_result.passed:
        state.best_score = review_result.total
        state.best_attempt = attempt + 1
        return _AttemptVerdict.STOP
    if review_result is not None:
        if review_result.total > state.best_score:
            state.best_score = review_result.total
            state.best_attempt = attempt + 1
        if attempt < 2:
            return _AttemptVerdict.RETRY
    # Review skipped or unavailable — accept on first attempt
    if review_result is None:
        state.best_attempt = attempt + 1
    return _AttemptVerdict.STOP


def _attempt_reference_once(
    batch: _GenerationBatch,
    raw: dict[str, object],
    ctx: _EntryContext,
    state: _LoopState,
    attempt: int,
) -> _AttemptVerdict:
    """Execute one generation attempt; classify the loop-control outcome."""
    if attempt > 0:
        # Inject actionable feedback into prompt for retry
        updated = _feedback_retry_prompt(ctx.prompt_text, state.frame_review_result)
        if updated is not None:
            state.retry_prompt = updated

    target_path, metadata, exc = _execute_provider_attempt(batch.provider, state.retry_prompt, ctx)
    if exc is None:
        state.target_path = target_path
        state.metadata = metadata
        return _grade_generated_frame(batch, raw, ctx, state, attempt)

    if attempt < 2:
        return _AttemptVerdict.RETRY
    _record_failed_entry(
        raw,
        ctx.reference_id,
        batch.results,
        code="generation_failed",
        issue_message=str(exc)[:300],
        result_error=str(exc)[:200],
    )
    return _AttemptVerdict.FAILED


def _run_retry_attempts(
    batch: _GenerationBatch,
    raw: dict[str, object],
    ctx: _EntryContext,
) -> _RetryOutcome:
    """Run up to three generation attempts, keeping the best reviewed frame."""
    state = _LoopState(retry_prompt=ctx.prompt_text)
    verdict = _AttemptVerdict.RETRY
    for attempt in range(3):
        verdict = _attempt_reference_once(batch, raw, ctx, state, attempt)
        if verdict is _AttemptVerdict.RETRY:
            continue
        break
    return _RetryOutcome(
        best_score=state.best_score,
        best_attempt=state.best_attempt,
        frame_review_result=state.frame_review_result,
        target_path=state.target_path,
        metadata=state.metadata,
        failed=verdict is _AttemptVerdict.FAILED,
    )
