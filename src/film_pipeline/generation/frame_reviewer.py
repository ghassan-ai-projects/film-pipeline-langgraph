"""Per-frame Gemini review — AI-based validation of generated reference images.

Runs after auto-heuristic checks (Phase 1). Uses Gemini Flash to score each
frame against a 40-point rubric. Supports selective validation to save cost.
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
class FrameReviewResult:
    """Outcome of a Gemini per-frame review."""

    frame_id: str
    passed: bool
    total: float = 0.0
    scores: dict[str, dict[str, object]] = field(default_factory=dict)
    actionable_feedback: str = ""
    raw_response: dict[str, Any] | None = None
    error: str | None = None


# ── Rubric ────────────────────────────────────────────────────────────────

_PER_FRAME_RUBRIC = """Score against this rubric (40 pts):
1. SUBJECT (10 pts): Is the expected subject visible? Face/character clear?
2. PROMPT MATCH (10 pts): Does expression/position/lighting match prompt?
3. ARTIFACTS (10 pts): Any deformities, merges, extra anatomy, corruption?
4. TECHNICAL (10 pts): Sharp focus, proper exposure, clean quality?

Threshold: 28/40 (70%)."""

_PASS_THRESHOLD = 28.0

# ── Selective validation ──────────────────────────────────────────────────


def should_review_frame(entry: dict[str, Any], *, frame_index: int = 0) -> bool:
    """Decide whether a frame warrants a paid Gemini review.

    Returns False for frame types that are safe to skip (saves ~$0.001/frame).
    """
    subject_type = str(entry.get("subject_type", "")).strip().lower()
    frame_role = str(entry.get("frame_role", "")).strip().lower()
    asset_type = str(entry.get("asset_type", "")).strip().lower()

    # Skip: environment wide shots and lighting variants
    if subject_type == "environment":
        if frame_role in ("wide-establishing",) or frame_role.startswith("lighting-"):
            return False
        if frame_role.startswith("alt-angle-"):
            # Spot-check 30% of environment alt angles
            return (hash(frame_role + str(frame_index)) % 10) < 3
        # Detail insets: skip
        return not (frame_role.startswith("detail-") or frame_role == "color-palette")

    # Skip: detail insets for characters
    if frame_role.startswith("detail-"):
        return False

    # Character front face: always review
    if frame_role == "front-face":
        return True

    # Character alt angles: spot-check 30%
    if frame_role in ("3-4-left", "3-4-right", "profile-left", "profile-right"):
        return (hash(frame_role + str(frame_index)) % 10) < 3

    # Character expressions: first 3, then spot-check
    if frame_role and frame_role.startswith("expression-"):
        if frame_index < 3:
            return True
        return (hash(frame_role + str(frame_index)) % 10) < 5

    # Scale references and props: once
    if asset_type in ("scale_sheet", "prop_sheet"):
        return frame_index == 0

    # Default: review
    return True


# ── Public API ────────────────────────────────────────────────────────────


def review_frame(
    image_path: Path,
    prompt_text: str,
    *,
    subject_type: str = "character",
    frame_id: str = "",
    http_opener: object = None,
    api_key: str | None = None,
    model: str = "gemini-2.0-flash",
) -> FrameReviewResult:
    """Run Gemini Flash review on a single reference frame.

    Args:
        image_path: Path to the generated PNG.
        prompt_text: The structured prompt used to generate the image.
        subject_type: ``"character"`` or ``"environment"``.
        frame_id: Identifier for the frame (used in result).
        http_opener: Optional mock HTTP opener for testing.
        api_key: Optional API key override.
        model: Gemini model to use.

    Returns:
        ``FrameReviewResult`` with scores, pass/fail, and feedback.
    """
    try:
        image_b64 = _encode_image(image_path)
    except Exception as exc:
        return FrameReviewResult(
            frame_id=frame_id,
            passed=False,
            error=f"Cannot read image: {exc}",
        )

    prompt = _build_review_prompt(prompt_text, subject_type)

    try:
        response = _call_gemini(
            prompt=prompt,
            image_b64=image_b64,
            model=model,
            http_opener=http_opener,
            api_key=api_key,
        )
    except Exception as exc:
        return FrameReviewResult(
            frame_id=frame_id,
            passed=False,
            error=f"Gemini API error: {exc}",
        )

    return _parse_response(response, frame_id=frame_id)


# ── Helpers ───────────────────────────────────────────────────────────────


def _encode_image(image_path: Path) -> str:
    data = image_path.read_bytes()
    return base64.b64encode(data).decode("ascii")


def _build_review_prompt(prompt_text: str, subject_type: str) -> str:
    return (
        f"You are validating an AI-generated reference image for film production.\n"
        f"Subject type: {subject_type}.\n"
        f"The image should show: {prompt_text}\n\n"
        f"{_PER_FRAME_RUBRIC}\n\n"
        f"Return ONLY valid JSON (no markdown, no backticks):\n"
        f'{{"frame_id":"","scores":{{'
        f'"subject":{{"score":0,"max":10,"notes":""}},'
        f'"prompt_match":{{"score":0,"max":10,"notes":""}},'
        f'"artifacts":{{"score":0,"max":10,"notes":""}},'
        f'"technical":{{"score":0,"max":10,"notes":""}}'
        f'}},"total":0,"passed":false,"actionable_feedback":""}}'
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
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": image_b64,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 1024,
        },
    }

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    opener = http_opener if http_opener is not None else urllib.request.build_opener()
    with opener.open(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_response(response: dict[str, Any], *, frame_id: str = "") -> FrameReviewResult:
    try:
        candidates = response.get("candidates", [])
        if not candidates:
            return FrameReviewResult(
                frame_id=frame_id, passed=False, error="No candidates in response"
            )

        text = str(candidates[0].get("content", {}).get("parts", [{}])[0].get("text", ""))
        # Strip markdown fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        data = json.loads(text)
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        return FrameReviewResult(
            frame_id=frame_id, passed=False, error=f"Failed to parse Gemini response: {exc}"
        )

    scores: dict[str, dict[str, object]] = {}
    total = 0.0
    for domain in ("subject", "prompt_match", "artifacts", "technical"):
        domain_data = data.get("scores", {}).get(domain, {})
        if isinstance(domain_data, dict):
            scores[domain] = {
                "score": float(domain_data.get("score", 0)),
                "max": float(domain_data.get("max", 10)),
                "notes": str(domain_data.get("notes", "")),
            }
            total += scores[domain]["score"]

    return FrameReviewResult(
        frame_id=str(data.get("frame_id", frame_id)),
        passed=total >= _PASS_THRESHOLD,
        total=total,
        scores=scores,
        actionable_feedback=str(data.get("actionable_feedback", "")),
        raw_response=data,
    )
