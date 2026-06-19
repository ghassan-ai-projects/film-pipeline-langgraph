"""DialogueVoiceValidator — validates dialogue voice consistency."""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator


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
            models=["gpt-5-mini"],
            thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
            blocking_conditions=["voice_inconsistency", "character_truth_broken"],
            warning_conditions=["generic_dialogue", "exposition_heavy"],
        )
        super().__init__(entry)

    def validate(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect dialogue across all scenes for voice issues."""
        _ = context
        scenes: list[dict[str, Any]] = artifact.get("scenes", [])
        issues: list[dict[str, str]] = []

        # Collect all dialogue per character
        char_lines: dict[str, list[str]] = {}
        char_scene_counts: dict[str, int] = {}
        total_dialogue = 0
        exposition_lines = 0
        generic_indicators = 0

        exposition_phrases = [
            "as you know",
            "let me explain",
            "remember when",
            "i should tell you",
            "you see,",
            "the thing is,",
        ]
        generic_phrases = [
            "i'm fine",
            "let's go",
            "what do you mean",
            "i don't know",
            "really?",
            "ok",
            "i see",
        ]

        for s in scenes:
            for d in s.get("dialogue", []):
                cid = str(d.get("character_id", "unknown"))
                line = str(d.get("line", ""))
                char_lines.setdefault(cid, []).append(line)
                char_scene_counts[cid] = char_scene_counts.get(cid, 0) + 1
                total_dialogue += 1

                line_lower = line.lower()
                if any(ep in line_lower for ep in exposition_phrases):
                    exposition_lines += 1
                if any(gp in line_lower for gp in generic_phrases):
                    generic_indicators += 1

        if total_dialogue == 0:
            return {"total_lines": 0, "issues": []}

        # Blocking: all characters sound the same (very short lines, same vocab)
        if len(char_lines) >= 2:
            avg_lengths = {
                cid: sum(len(line) for line in lines) / max(len(lines), 1)
                for cid, lines in char_lines.items()
            }
            if avg_lengths:
                max_avg = max(avg_lengths.values())
                min_avg = min(avg_lengths.values())
                if max_avg > 0 and (max_avg - min_avg) / max_avg < 0.1:
                    issues.append(
                        {
                            "code": "voice_inconsistency",
                            "severity": "blocking",
                            "message": (
                                "All characters have near-identical average line lengths "
                                f"({min_avg:.0f}-{max_avg:.0f} chars). "
                                "Character voices are not differentiated."
                            ),
                        }
                    )

        # Blocking: character truth broken (placeholder detection)
        # Real implementation would compare against the FilmConstitution.
        # For now, detect if any character has zero lines of dialogue.
        if char_lines and any(len(lines) == 0 for lines in char_lines.values()):  # pragma: no cover
            issues.append(
                {
                    "code": "character_truth_broken",
                    "severity": "blocking",
                    "message": "One or more characters have no dialogue lines.",
                }
            )

        # Warning: heavy exposition
        exposition_ratio = exposition_lines / total_dialogue
        if exposition_ratio > 0.2:
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

        # Warning: generic dialogue
        generic_ratio = generic_indicators / total_dialogue
        if generic_ratio > 0.3:
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

        return {
            "total_lines": total_dialogue,
            "characters": len(char_lines),
            "char_lines": {c: len(line) for c, line in char_lines.items()},
            "exposition_ratio": exposition_ratio,
            "generic_ratio": generic_ratio,
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
            )
            for i in raw.get("issues", [])
        ]
