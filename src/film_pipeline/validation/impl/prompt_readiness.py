"""PromptReadinessValidator — validates RCTCO prompt packages before execution."""

from __future__ import annotations

from typing import Any, Final

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.validation.base import BaseValidator

MAX_PROMPT_LENGTH: Final[int] = 8000  # characters

_AMBIGUOUS_PHRASES: Final[frozenset[str]] = frozenset(
    {"maybe", "if possible", "optional", "preferably", "sort of"}
)


def _empty_prompt_readiness_result() -> dict[str, Any]:
    """Result payload for a package that declares no prompts."""
    return {
        "total_entries": 0,
        "malformed_count": 0,
        "missing_refs_count": 0,
        "too_long_count": 0,
        "ambiguous_count": 0,
        "missing_examples_count": 0,
        "issues": [],
    }


def _flag_malformed_rctco(
    prompt_id: str,
    rctco: dict[str, Any],
    issues: list[dict[str, str]],
) -> int:
    """Blocking: required RCTCO role or core-task fields are absent."""
    role = str(rctco.get("r", ""))
    core_task = str(rctco.get("c1", ""))
    if role and core_task:
        return 0
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
    return 1


def _flag_missing_artifact_refs(
    prompt_id: str,
    artifact_refs: list[str],
    issues: list[dict[str, str]],
) -> int:
    """Blocking: the prompt references no upstream artifacts."""
    if artifact_refs:
        return 0
    issues.append(
        {
            "code": "missing_refs",
            "severity": "blocking",
            "message": f"Prompt '{prompt_id}' has no artifact_refs.",
        }
    )
    return 1


def _flag_overlong_prompt(
    prompt_id: str,
    rendered: str,
    issues: list[dict[str, str]],
) -> int:
    """Blocking: the rendered prompt exceeds the character limit."""
    if len(rendered) <= MAX_PROMPT_LENGTH:
        return 0
    issues.append(
        {
            "code": "prompt_too_long",
            "severity": "blocking",
            "message": (
                f"Prompt '{prompt_id}' is {len(rendered)} chars (> {MAX_PROMPT_LENGTH} limit)."
            ),
        }
    )
    return 1


def _flag_ambiguous_constraints(
    prompt_id: str,
    constraints: list[str],
    issues: list[dict[str, str]],
) -> int:
    """Warning: constraints use hedging language."""
    if not any(phrase in str(c).lower() for c in constraints for phrase in _AMBIGUOUS_PHRASES):
        return 0
    issues.append(
        {
            "code": "ambiguous_constraints",
            "severity": "warning",
            "message": (f"Prompt '{prompt_id}' has constraints with ambiguous language."),
        }
    )
    return 1


def _flag_missing_examples(
    prompt_id: str,
    context_in: dict[str, str],
    issues: list[dict[str, str]],
) -> int:
    """Warning: no example references appear in the context block."""
    if any(k for k in context_in if "example" in k.lower()):
        return 0
    issues.append(
        {
            "code": "missing_examples",
            "severity": "warning",
            "message": f"Prompt '{prompt_id}' has no example references in context.",
        }
    )
    return 1


def _flag_missing_output_schema(
    prompt_id: str,
    rctco: dict[str, Any],
    issues: list[dict[str, str]],
) -> int:
    """Blocking: no output schema reference is given."""
    o_schema = str(rctco.get("o_schema_ref", ""))
    if o_schema:
        return 0
    issues.append(
        {
            "code": "malformed_rctco",
            "severity": "blocking",
            "message": f"Prompt '{prompt_id}' has no output schema reference.",
        }
    )
    return 1


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
            return _empty_prompt_readiness_result()

        issues: list[dict[str, str]] = []
        malformed = 0
        missing_refs = 0
        too_long = 0
        ambiguous = 0
        missing_examples = 0

        for entry in entries:
            prompt_id = str(entry.get("prompt_id", "?"))
            rctco: dict[str, Any] = entry.get("rctco", {})
            malformed += _flag_malformed_rctco(prompt_id, rctco, issues)
            artifact_refs: list[str] = entry.get("artifact_refs", [])
            missing_refs += _flag_missing_artifact_refs(prompt_id, artifact_refs, issues)
            rendered: str = str(entry.get("rendered_prompt", ""))
            too_long += _flag_overlong_prompt(prompt_id, rendered, issues)
            constraints: list[str] = rctco.get("c2", [])
            ambiguous += _flag_ambiguous_constraints(prompt_id, constraints, issues)
            context_in: dict[str, str] = rctco.get("t", {})
            missing_examples += _flag_missing_examples(prompt_id, context_in, issues)
            malformed += _flag_missing_output_schema(prompt_id, rctco, issues)

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
