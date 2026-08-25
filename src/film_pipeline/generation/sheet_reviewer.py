"""Composite sheet validation — Gemini review of assembled reference sheets.

Distinct from per-frame validation (Phase 3) — evaluates the complete composite
against domain-specific rubrics. Returns structured scores, pass/fail,
actionable feedback, failing tiles, and bad-reference tags.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from film_pipeline.generation.gemini_client import call_gemini

# ── Data types ────────────────────────────────────────────────────────────


@dataclass
class SheetReviewResult:
    """Outcome of a Gemini composite sheet review."""

    sheet_id: str
    sheet_type: str
    passed: bool
    total: float = 0.0
    max_score: float = 0.0
    scores: dict[str, dict[str, object]] = field(default_factory=dict)
    status: str = "pending"
    actionable_feedback: str = ""
    failing_tiles: list[str] = field(default_factory=list)
    bad_reference_tags: list[str] = field(default_factory=list)
    error: str | None = None


# ── Rubrics ───────────────────────────────────────────────────────────────

_RUBRICS: dict[str, tuple[dict[str, tuple[int, str]], int]] = {
    "character_identity_sheet": (
        {
            "identity_accuracy": (15, "Same person across all tiles? Age/features consistent?"),
            "expression_fidelity": (10, "Each expression matches its label?"),
            "composition_quality": (10, "Visual hierarchy clear? Labels in margins?"),
            "technical_quality": (10, "No artifacts? Consistent lighting? Clean edges?"),
            "usability": (5, "Would this stabilize generation across 60+ shots?"),
        },
        40,
    ),
    "environment_board": (
        {
            "spatial_consistency": (15, "Same geometry across angles? No new walls/furniture?"),
            "lighting_accuracy": (10, "Lighting matches target? Consistent direction?"),
            "mood_encoding": (10, "Mood matches scene description? Palette consistent?"),
            "technical_quality": (10, "No artifacts? Clean composites?"),
            "usability": (5, "Would this stabilize environment across shots?"),
        },
        40,
    ),
    "scale_sheet": (
        {
            "relative_proportion": (10, "Characters correctly scaled relative to each other?"),
            "context_clarity": (5, "Scale reference bar clear and usable?"),
            "technical_quality": (5, "Consistent perspective?"),
        },
        16,
    ),
}


def _pass_threshold(max_score: int) -> float:
    return max_score * 0.8


# ── Public API ────────────────────────────────────────────────────────────


def review_composite_sheet(
    sheet_path: Path,
    sheet_type: str,
    subject_id: str,
    prompt_text: str = "",
    *,
    http_opener: object = None,
    api_key: str | None = None,
    model: str,
) -> SheetReviewResult:
    """Run Gemini review on a composite reference sheet.

    Args:
        sheet_path: Path to the composite PNG.
        sheet_type: One of ``"character_identity_sheet"``, ``"environment_board"``,
                    ``"scale_sheet"``.
        subject_id: The subject this sheet covers.
        prompt_text: The prompt used to generate the constituent frames.
        http_opener: Optional mock HTTP opener for testing.
        api_key: Optional API key override.
        model: Gemini model to use.
    """
    rubric_data = _RUBRICS.get(sheet_type)
    if rubric_data is None:
        return _failed_result(subject_id, sheet_type, f"Unknown sheet type: {sheet_type}")

    domains, max_score = rubric_data

    try:
        image_b64 = _encode_sheet_image(sheet_path)
    except Exception as exc:
        return _failed_result(subject_id, sheet_type, f"Cannot read sheet: {exc}")

    prompt = _build_sheet_review_prompt(sheet_type, subject_id, prompt_text, domains, max_score)

    try:
        response = call_gemini(prompt, image_b64, model, http_opener, api_key)
    except Exception as exc:
        return _failed_result(subject_id, sheet_type, f"Gemini API error: {exc}")

    return _parse_sheet_response(response, subject_id, sheet_type, max_score)


# ── Helpers ───────────────────────────────────────────────────────────────


def _failed_result(subject_id: str, sheet_type: str, error: str) -> SheetReviewResult:
    return SheetReviewResult(
        sheet_id=subject_id,
        sheet_type=sheet_type,
        passed=False,
        error=error,
    )


def _encode_sheet_image(sheet_path: Path) -> str:
    return base64.b64encode(sheet_path.read_bytes()).decode("ascii")


def _format_rubric_lines(domains: dict[str, tuple[int, str]]) -> str:
    rubric_lines = []
    for domain, (pts, description) in domains.items():
        rubric_lines.append(f"- {domain.upper()} ({pts} pts): {description}")
    return "\n".join(rubric_lines)


def _build_sheet_review_prompt(
    sheet_type: str,
    subject_id: str,
    prompt_text: str,
    domains: dict[str, tuple[int, str]],
    max_score: int,
) -> str:
    rubric_text = _format_rubric_lines(domains)

    threshold = _pass_threshold(max_score)

    return (
        f"You are validating an AI-generated reference sheet for film production.\n"
        f"Sheet type: {sheet_type.replace('_', ' ')}.\n"
        f"Subject: {subject_id}.\n"
        f"Prompt used: {prompt_text or 'N/A'}\n\n"
        f"Score against this rubric ({max_score} pts):\n"
        f"{rubric_text}\n\n"
        f"Threshold: {threshold:.0f}/{max_score} (80%).\n\n"
        f"Return ONLY valid JSON (no markdown, no backticks):\n"
        f'{{"sheet_id":"","sheet_type":"","scores":{{'
        + ",".join(f'"{d}":{{"score":0,"max":{m},"notes":""}}' for d, (m, _) in domains.items())
        + '},"total":0,"passed":false,"actionable_feedback":"",'
        + '"failing_tiles":[],"bad_reference_tags":[]}'
    )


def _candidate_text(candidates: list[Any]) -> str:
    text = str(candidates[0].get("content", {}).get("parts", [{}])[0].get("text", ""))
    return text.strip()


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text
    stripped = text.split("\n", 1)[-1]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()


def _normalized_scores(data: dict[str, Any]) -> tuple[dict[str, dict[str, object]], float]:
    scores: dict[str, dict[str, object]] = {}
    total = 0.0
    for domain in data.get("scores", {}):
        d = data["scores"][domain]
        scores[domain] = {
            "score": float(d.get("score", 0)),
            "max": float(d.get("max", 0)),
            "notes": str(d.get("notes", "")),
        }
        total += float(cast(float, scores[domain]["score"]))
    return scores, total


def _review_status(passed: bool, data: dict[str, Any]) -> str:
    return (
        "approved"
        if passed
        else "needs_delta_fix"
        if data.get("failing_tiles")
        else "needs_regeneration"
    )


def _parse_sheet_response(
    response: dict[str, Any],
    subject_id: str,
    sheet_type: str,
    max_score: int,
) -> SheetReviewResult:
    try:
        candidates = response.get("candidates", [])
        if not candidates:
            return _failed_result(subject_id, sheet_type, "No candidates")
        text = _strip_code_fence(_candidate_text(candidates))
        data = json.loads(text)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        return SheetReviewResult(
            sheet_id=subject_id, sheet_type=sheet_type, passed=False, error=f"Parse error: {exc}"
        )

    scores, total = _normalized_scores(data)

    threshold = _pass_threshold(max_score)
    passed = total >= threshold

    status = _review_status(passed, data)

    return SheetReviewResult(
        sheet_id=str(data.get("sheet_id", subject_id)),
        sheet_type=sheet_type,
        passed=passed,
        total=total,
        max_score=float(max_score),
        scores=scores,
        status=status,
        actionable_feedback=str(data.get("actionable_feedback", "")),
        failing_tiles=list(data.get("failing_tiles", [])),
        bad_reference_tags=list(data.get("bad_reference_tags", [])),
    )
