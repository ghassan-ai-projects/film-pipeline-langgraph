"""Post-generation stamping: quality metadata, identity drift, registration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from film_pipeline.mcp.tools.reference_generation.context import (
    _EntryContext,
    _GenerationBatch,
)
from film_pipeline.mcp.tools.reference_generation.entries import (
    _group_key,
)
from film_pipeline.mcp.tools.reference_generation.retry_loop import (
    _RetryOutcome,
)


def _stamp_retry_stats(raw: dict[str, object], outcome: _RetryOutcome) -> None:
    """Record attempts spent and the best reviewed score on the entry."""
    raw["retry_count"] = outcome.best_attempt  # 0 if all attempts failed
    raw["best_score"] = outcome.best_score


def _apply_identity_drift_policy(
    identity_states: dict[str, dict[str, object]],
    raw: dict[str, object],
    frame_review_result: Any | None,
    is_anchor: bool,
) -> None:
    """Escalate to image-to-image strength when Gemini reports subject drift."""
    if frame_review_result is None or frame_review_result.passed:
        return
    subject_score = float(
        cast(float, frame_review_result.scores.get("subject", {}).get("score", 10))
    )
    if subject_score < 7 and not is_anchor:
        ist = identity_states.setdefault(_group_key(raw), {})
        if not ist.get("i2i_active"):
            ist["i2i_active"] = True
            ist["i2i_strength"] = 0.5
        elif float(cast(float, ist.get("i2i_strength", 0.5))) > 0.3:
            ist["i2i_strength"] = 0.3


def _update_identity_group(
    identity_states: dict[str, dict[str, object]],
    raw: dict[str, object],
    outcome: _RetryOutcome,
) -> None:
    """Track the anchor frame and enforce drift policy for the entry's group."""
    ist = identity_states.setdefault(_group_key(raw), {})
    is_anchor = str(raw.get("frame_role", "")).strip().lower() in (
        "front-face",
        "wide-establishing",
    )
    if is_anchor and "anchor_seed" in ist and outcome.target_path is not None:
        ist["anchor_frame_path"] = outcome.target_path
    _apply_identity_drift_policy(identity_states, raw, outcome.frame_review_result, is_anchor)


def _apply_validated_metadata(raw: dict[str, object], frame_review_result: Any) -> None:
    """Stamp approved-review quality fields onto a generated entry."""
    raw["generation_status"] = "validated"
    raw["quality_score"] = frame_review_result.total / 40.0 * 100.0
    raw["locked"] = True
    raw["validation"] = {
        "status": "approved",
        "score": frame_review_result.total,
        "reports": [json.dumps(frame_review_result.scores, default=str)],
    }
    raw["ai_usability"] = {
        "score": frame_review_result.total / 40.0 * 100.0,
        "risks": [],
        "notes": "Gemini per-frame review passed.",
    }
    raw["issues"] = []


def _apply_regeneration_metadata(raw: dict[str, object], frame_review_result: Any) -> None:
    """Stamp needs-regeneration quality fields onto a generated entry."""
    raw["generation_status"] = "needs_regeneration"
    raw["quality_score"] = frame_review_result.total / 40.0 * 100.0
    raw["locked"] = False
    raw["validation"] = {
        "status": "needs_regeneration",
        "score": frame_review_result.total,
        "reports": [json.dumps(frame_review_result.scores, default=str)],
    }
    raw["ai_usability"] = {
        "score": frame_review_result.total / 40.0 * 100.0,
        "risks": [],
        "notes": frame_review_result.actionable_feedback or "Gemini review failed.",
    }
    raw["issues"] = [
        {
            "code": "gemini_review_failed",
            "message": frame_review_result.actionable_feedback or "Gemini review below threshold.",
            "severity": "warning",
        }
    ]


def _apply_unreviewed_metadata(raw: dict[str, object]) -> None:
    """Stamp default quality fields when Gemini review did not run."""
    raw["generation_status"] = "generated"
    raw["quality_score"] = 80.0
    raw["locked"] = False
    raw["validation"] = {
        "status": "pending",
        "score": 0.0,
        "reports": [],
    }
    raw["ai_usability"] = {
        "score": 0.0,
        "risks": [],
        "notes": "Gemini review skipped (selective validation or API unavailable).",
    }
    raw["issues"] = []


def _write_frame_sidecar_safely(
    target_path: Path, raw: dict[str, object], asset_posix: str, ctx: _EntryContext
) -> None:
    """Write the frame metadata sidecar alongside the PNG; non-blocking."""
    try:
        from film_pipeline.generation.frame_sidecar import write_frame_sidecar
        from film_pipeline.schemas.reference import ReferenceFrame

        frame = ReferenceFrame(
            frame_path=asset_posix,
            reference_id=ctx.reference_id,
            subject_type=str(raw.get("subject_type", "")),
            subject_id=str(raw.get("subject_id", "")),
            provider_id=str(raw.get("provider", "")),
            model_id="",
            tier=ctx.tier,
            seed=cast(int | None, ctx.provider_kwargs.get("seed")),
            prompt_text=ctx.prompt_text,
            frame_role=str(raw.get("frame_role", "")),
            expression=str(raw.get("expression", "")) or None,
            lighting=str(raw.get("lighting", "")) or None,
            aspect_ratio=ctx.aspect_ratio,
            generation_status=str(raw.get("generation_status", "generated")),
            quality_score=float(cast(float, raw.get("quality_score", 0))),
            retry_count=int(cast(int, raw.get("retry_count", 0))),
            best_score=float(cast(float, raw.get("best_score", 0))),
            heuristic_checks_passed=True,
            mime_type=str(raw.get("normalized_mime_type", "image/png")),
            created_at="",
        )
        write_frame_sidecar(target_path, frame)
    except Exception:
        pass  # sidecar failure is non-blocking


def _stamp_asset_fields(
    batch: _GenerationBatch,
    raw: dict[str, object],
    ctx: _EntryContext,
    outcome: _RetryOutcome,
) -> None:
    """Stamp asset location, provider, and prompt provenance onto the entry."""
    rel_path = cast(Path, outcome.target_path).resolve().relative_to(batch.project_root.resolve())
    provider_entry = getattr(batch.provider, "entry", None)
    provider_id = str(getattr(provider_entry, "provider_id", ""))
    raw["asset_path"] = rel_path.as_posix()
    raw["provider"] = provider_id
    raw["tier"] = ctx.tier
    raw["prompt_text"] = ctx.prompt_text
    raw["source_frames"] = [rel_path.as_posix()]
    raw["original_mime_type"] = str(outcome.metadata.get("mime_type", "image/png"))
    raw["normalized_mime_type"] = str(outcome.metadata.get("mime_type", "image/png"))


def _append_generated_result(
    batch: _GenerationBatch,
    ctx: _EntryContext,
    asset_posix: str,
    provider_id: str,
) -> None:
    """Record the generated result row for the batch summary."""
    batch.results.append(
        {
            "reference_id": ctx.reference_id,
            "status": "generated",
            "asset_path": asset_posix,
            "provider": provider_id,
        }
    )


def _register_generated_entry(
    batch: _GenerationBatch,
    raw: dict[str, object],
    ctx: _EntryContext,
    outcome: _RetryOutcome,
) -> str:
    """Apply success metadata, write the sidecar, and record the result row."""
    _stamp_asset_fields(batch, raw, ctx, outcome)
    asset_posix = str(raw["asset_path"])

    frame_review_result = outcome.frame_review_result
    if frame_review_result is not None and frame_review_result.passed:
        _apply_validated_metadata(raw, frame_review_result)
    elif frame_review_result is not None:
        _apply_regeneration_metadata(raw, frame_review_result)
    # else: review was skipped (selective validation) or failed — keep defaults
    else:
        _apply_unreviewed_metadata(raw)

    # Phase 03 — Write frame metadata sidecar alongside the PNG
    _write_frame_sidecar_safely(cast(Path, outcome.target_path), raw, asset_posix, ctx)

    _append_generated_result(batch, ctx, asset_posix, str(raw["provider"]))
    return "generated"
