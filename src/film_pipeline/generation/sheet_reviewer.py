"""Composite sheet validation — Gemini review of assembled reference sheets.

Distinct from per-frame validation (Phase 3) — evaluates the complete composite
against domain-specific rubrics. Returns structured scores, pass/fail,
actionable feedback, failing tiles, and bad-reference tags.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
    model: str = "gemini-2.0-flash",
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
        return SheetReviewResult(
            sheet_id=subject_id,
            sheet_type=sheet_type,
            passed=False,
            error=f"Unknown sheet type: {sheet_type}",
        )

    domains, max_score = rubric_data

    try:
        image_b64 = base64.b64encode(sheet_path.read_bytes()).decode("ascii")
    except Exception as exc:
        return SheetReviewResult(
            sheet_id=subject_id,
            sheet_type=sheet_type,
            passed=False,
            error=f"Cannot read sheet: {exc}",
        )

    prompt = _build_sheet_review_prompt(sheet_type, subject_id, prompt_text, domains, max_score)

    try:
        response = _call_gemini(prompt, image_b64, model, http_opener, api_key)
    except Exception as exc:
        return SheetReviewResult(
            sheet_id=subject_id,
            sheet_type=sheet_type,
            passed=False,
            error=f"Gemini API error: {exc}",
        )

    return _parse_sheet_response(response, subject_id, sheet_type, max_score)


# ── Helpers ───────────────────────────────────────────────────────────────


def _build_sheet_review_prompt(
    sheet_type: str,
    subject_id: str,
    prompt_text: str,
    domains: dict[str, tuple[int, str]],
    max_score: int,
) -> str:
    rubric_lines = []
    for domain, (pts, description) in domains.items():
        rubric_lines.append(f"- {domain.upper()} ({pts} pts): {description}")
    rubric_text = "\n".join(rubric_lines)

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


def _call_gemini(
    prompt: str,
    image_b64: str,
    model: str,
    http_opener: object = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    from film_pipeline.providers.credentials import lookup

    key = api_key or lookup("gemini-imagen-4")
    if not key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    )
    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/png", "data": image_b64}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    opener = http_opener if http_opener is not None else urllib.request.build_opener()
    with opener.open(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_sheet_response(
    response: dict[str, Any],
    subject_id: str,
    sheet_type: str,
    max_score: int,
) -> SheetReviewResult:
    try:
        candidates = response.get("candidates", [])
        if not candidates:
            return SheetReviewResult(
                sheet_id=subject_id, sheet_type=sheet_type, passed=False, error="No candidates"
            )
        text = str(candidates[0].get("content", {}).get("parts", [{}])[0].get("text", ""))
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        data = json.loads(text)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        return SheetReviewResult(
            sheet_id=subject_id, sheet_type=sheet_type, passed=False, error=f"Parse error: {exc}"
        )

    scores: dict[str, dict[str, object]] = {}
    total = 0.0
    for domain in data.get("scores", {}):
        d = data["scores"][domain]
        scores[domain] = {
            "score": float(d.get("score", 0)),
            "max": float(d.get("max", 0)),
            "notes": str(d.get("notes", "")),
        }
        total += scores[domain]["score"]

    threshold = _pass_threshold(max_score)
    passed = total >= threshold

    status = (
        "approved"
        if passed
        else "needs_delta_fix"
        if data.get("failing_tiles")
        else "needs_regeneration"
    )

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
