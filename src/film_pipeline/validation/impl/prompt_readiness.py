"""PromptReadinessValidator — validates RCTCO prompt packages before execution."""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator

MAX_PROMPT_LENGTH = 8000  # characters


class PromptReadinessValidator(BaseValidator):
    """Validates RCTCO prompts for completeness and readiness.

    Matches the ``prompt-readiness-validator`` contract.
    """

    def __init__(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="prompt-readiness-validator",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
            input_schema="prompt_package",
            model_profile="text_validator",
            thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
            blocking_conditions=["malformed_rctco", "missing_refs", "prompt_too_long"],
            warning_conditions=["ambiguous_constraints", "missing_examples"],
        )
        super().__init__(entry)

    def _validate_rules(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect prompt entries for readiness issues."""
        _ = context
        entries: list[dict[str, Any]] = artifact.get("entries", [])
        if not entries:
            return {
                "total_entries": 0,
                "malformed_count": 0,
                "missing_refs_count": 0,
                "too_long_count": 0,
                "ambiguous_count": 0,
                "missing_examples_count": 0,
                "issues": [],
            }

        issues: list[dict[str, str]] = []
        malformed = 0
        missing_refs = 0
        too_long = 0
        ambiguous = 0
        missing_examples = 0

        for entry in entries:
            prompt_id = str(entry.get("prompt_id", "?"))
            rctco: dict[str, Any] = entry.get("rctco", {})

            # Blocking: malformed RCTCO (missing required fields)
            role = str(rctco.get("r", ""))
            core_task = str(rctco.get("c1", ""))
            if not role or not core_task:
                malformed += 1
                issues.append(
                    {
                        "code": "malformed_rctco",
                        "severity": "blocking",
                        "message": (
                            f"Prompt '{prompt_id}' is missing required RCTCO fields "
                            f"(r={'present' if role else 'missing'}, "
                            f"c1={'present' if core_task else 'missing'})."
                        ),
                    }
                )

            # Blocking: missing artifact refs
            artifact_refs: list[str] = entry.get("artifact_refs", [])
            if not artifact_refs:
                missing_refs += 1
                issues.append(
                    {
                        "code": "missing_refs",
                        "severity": "blocking",
                        "message": f"Prompt '{prompt_id}' has no artifact_refs.",
                    }
                )

            # Blocking: prompt too long
            rendered: str = str(entry.get("rendered_prompt", ""))
            if len(rendered) > MAX_PROMPT_LENGTH:
                too_long += 1
                issues.append(
                    {
                        "code": "prompt_too_long",
                        "severity": "blocking",
                        "message": (
                            f"Prompt '{prompt_id}' is {len(rendered)} chars "
                            f"(> {MAX_PROMPT_LENGTH} limit)."
                        ),
                    }
                )

            # Warning: ambiguous constraints
            constraints: list[str] = rctco.get("c2", [])
            ambiguous_phrases = {"maybe", "if possible", "optional", "preferably", "sort of"}
            if any(phrase in str(c).lower() for c in constraints for phrase in ambiguous_phrases):
                ambiguous += 1
                issues.append(
                    {
                        "code": "ambiguous_constraints",
                        "severity": "warning",
                        "message": (
                            f"Prompt '{prompt_id}' has constraints with ambiguous language."
                        ),
                    }
                )

            # Warning: missing examples in context
            context_in: dict[str, str] = rctco.get("t", {})
            if not any(k for k in context_in if "example" in k.lower()):
                missing_examples += 1
                issues.append(
                    {
                        "code": "missing_examples",
                        "severity": "warning",
                        "message": f"Prompt '{prompt_id}' has no example references in context.",
                    }
                )

            # Blocking: missing output schema
            o_schema = str(rctco.get("o_schema_ref", ""))
            if not o_schema:
                issues.append(
                    {
                        "code": "malformed_rctco",
                        "severity": "blocking",
                        "message": f"Prompt '{prompt_id}' has no output schema reference.",
                    }
                )
                malformed += 1

        return {
            "total_entries": len(entries),
            "malformed_count": malformed,
            "missing_refs_count": missing_refs,
            "too_long_count": too_long,
            "ambiguous_count": ambiguous,
            "missing_examples_count": missing_examples,
            "issues": issues,
        }

    def extract_score(self, raw: dict[str, Any]) -> float:
        total: int = raw.get("total_entries", 0)
        if total == 0:
            return 100.0

        malformed: int = raw.get("malformed_count", 0)
        missing_r: int = raw.get("missing_refs_count", 0)
        too_long: int = raw.get("too_long_count", 0)
        ambiguous: int = raw.get("ambiguous_count", 0)
        missing_ex: int = raw.get("missing_examples_count", 0)

        score = 100.0
        score -= (malformed / total) * 40.0
        score -= (missing_r / total) * 30.0
        score -= (too_long / total) * 25.0
        score -= (ambiguous / total) * 10.0
        score -= (missing_ex / total) * 5.0
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
