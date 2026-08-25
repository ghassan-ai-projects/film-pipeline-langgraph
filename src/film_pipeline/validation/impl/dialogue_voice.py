"""DialogueVoiceValidator — validates dialogue voice consistency."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator

_EXPOSITION_PHRASES = [
    "as you know",
    "let me explain",
    "remember when",
    "i should tell you",
    "you see,",
    "the thing is,",
]
_GENERIC_PHRASES = [
    "i'm fine",
    "let's go",
    "what do you mean",
    "i don't know",
    "really?",
    "ok",
    "i see",
]


@dataclass(frozen=True)
class _DialogueStats:
    """Dialogue aggregates collected across every scene."""

    char_lines: dict[str, list[str]]
    exposition_lines: int
    generic_indicators: int
    total_dialogue: int


def _collect_dialogue_stats(scenes: list[dict[str, Any]]) -> _DialogueStats:
    """Gather each character's dialogue lines plus phrase-category counts."""
    char_lines: dict[str, list[str]] = {}
    total_dialogue = 0
    exposition_lines = 0
    generic_indicators = 0

    for s in scenes:
        for d in s.get("dialogue", []):
            cid = str(d.get("character_id", "unknown"))
            line = str(d.get("line", ""))
            char_lines.setdefault(cid, []).append(line)
            total_dialogue += 1

            line_lower = line.lower()
            if any(ep in line_lower for ep in _EXPOSITION_PHRASES):
                exposition_lines += 1
            if any(gp in line_lower for gp in _GENERIC_PHRASES):
                generic_indicators += 1

    return _DialogueStats(
        char_lines=char_lines,
        exposition_lines=exposition_lines,
        generic_indicators=generic_indicators,
        total_dialogue=total_dialogue,
    )


def _voices_are_uniform(avg_lengths: dict[str, float]) -> bool:
    """True when all characters' average line lengths differ by under 10%."""
    max_avg = max(avg_lengths.values())
    min_avg = min(avg_lengths.values())
    return max_avg > 0 and (max_avg - min_avg) / max_avg < 0.1


def _flag_voice_inconsistency(
    char_lines: dict[str, list[str]],
    issues: list[dict[str, str]],
) -> None:
    """Blocking: all characters sound the same (very short lines, same vocab)."""
    if len(char_lines) < 2:
        return
    avg_lengths = {
        cid: sum(len(line) for line in lines) / max(len(lines), 1)
        for cid, lines in char_lines.items()
    }
    if not avg_lengths or not _voices_are_uniform(avg_lengths):
        return
    issues.append(
        {
            "code": "voice_inconsistency",
            "severity": "blocking",
            "message": (
                "All characters have near-identical average line lengths "
                f"({min(avg_lengths.values()):.0f}-{max(avg_lengths.values()):.0f} chars). "
                "Character voices are not differentiated."
            ),
        }
    )


def _flag_silent_characters(
    char_lines: dict[str, list[str]],
    issues: list[dict[str, str]],
) -> None:
    """Blocking: placeholder detection for characters without dialogue lines.

    Real implementation would compare against the FilmConstitution; for now,
    detect if any character has zero lines of dialogue.
    """
    if char_lines and any(len(lines) == 0 for lines in char_lines.values()):  # pragma: no cover
        issues.append(
            {
                "code": "character_truth_broken",
                "severity": "blocking",
                "message": "One or more characters have no dialogue lines.",
            }
        )


def _flag_exposition_load(
    exposition_lines: int,
    total_dialogue: int,
    issues: list[dict[str, str]],
) -> None:
    """Warning: more than a fifth of the lines contain exposition phrases."""
    exposition_ratio = exposition_lines / total_dialogue
    if exposition_ratio <= 0.2:
        return
    issues.append(
        {
            "code": "exposition_heavy",
            "severity": "warning",
            "message": (
                f"{exposition_lines}/{total_dialogue} lines contain exposition phrases "
                f"({exposition_ratio:.0%}). Consider showing rather than telling."
            ),
        }
    )


def _flag_generic_dialogue(
    generic_indicators: int,
    total_dialogue: int,
    issues: list[dict[str, str]],
) -> None:
    """Warning: over 30% of the lines rely on generic filler phrases."""
    generic_ratio = generic_indicators / total_dialogue
    if generic_ratio <= 0.3:
        return
    issues.append(
        {
            "code": "generic_dialogue",
            "severity": "warning",
            "message": (
                f"{generic_indicators}/{total_dialogue} lines contain generic phrases "
                f"({generic_ratio:.0%}). Dialogue may lack specificity."
            ),
        }
    )


class DialogueVoiceValidator(BaseValidator):
    """Validates dialogue voice consistency, character differentiation, and
    exposition load.

    Matches the ``dialogue-voice-validator`` contract.
    """

    def __init__(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="dialogue-voice-validator",
            scope=ValidationScope.SCENE,
            modalities=[ValidationModality.TEXT],
            input_schema="scene_script",
            model_profile="text_validator",
            thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
            blocking_conditions=["voice_inconsistency", "character_truth_broken"],
            warning_conditions=["generic_dialogue", "exposition_heavy"],
        )
        super().__init__(entry)

    def _validate_rules(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect dialogue across all scenes for voice issues."""
        _ = context
        scenes: list[dict[str, Any]] = artifact.get("scenes", [])
        stats = _collect_dialogue_stats(scenes)

        if stats.total_dialogue == 0:
            return {"total_lines": 0, "issues": []}

        issues: list[dict[str, str]] = []
        _flag_voice_inconsistency(stats.char_lines, issues)
        _flag_silent_characters(stats.char_lines, issues)
        _flag_exposition_load(stats.exposition_lines, stats.total_dialogue, issues)
        _flag_generic_dialogue(stats.generic_indicators, stats.total_dialogue, issues)

        return {
            "total_lines": stats.total_dialogue,
            "characters": len(stats.char_lines),
            "char_lines": {c: len(line) for c, line in stats.char_lines.items()},
            "exposition_ratio": stats.exposition_lines / stats.total_dialogue,
            "generic_ratio": stats.generic_indicators / stats.total_dialogue,
            "issues": issues,
        }

    def extract_score(self, raw: dict[str, Any]) -> float:
        issues: list[dict[str, str]] = raw.get("issues", [])
        total_lines: int = raw.get("total_lines", 0)
        if total_lines == 0:
            return 100.0

        blocking_count = sum(1 for i in issues if i.get("severity") == "blocking")
        warning_count = sum(1 for i in issues if i.get("severity") == "warning")

        score = 100.0
        score -= blocking_count * 30.0
        score -= warning_count * 15.0

        # Bonus: penalize very high exposition or generic ratios
        exposition_ratio: float = raw.get("exposition_ratio", 0.0)
        generic_ratio: float = raw.get("generic_ratio", 0.0)
        if exposition_ratio > 0.3:
            score -= 10.0
        if generic_ratio > 0.4:
            score -= 10.0

        return max(0.0, min(100.0, score))

    def extract_issues(self, raw: dict[str, Any]) -> list[ValidationIssue]:
        return [
            ValidationIssue(
                code=str(i.get("code", "unknown")),
                message=str(i.get("message", "")),
                severity=str(i.get("severity", "info")),
                suggestion=str(i.get("suggestion", "")),
                affected_entity=str(i.get("affected_entity", "")),
                affected_field=str(i.get("affected_field", "")),
                affected_shot=str(i.get("affected_shot", "")),
            )
            for i in raw.get("issues", [])
        ]
