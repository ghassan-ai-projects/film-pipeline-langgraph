"""Base validator — standard lifecycle: prepare → validate → score → report.

Subclasses implement ``_validate_rules()`` for rule-based checks.
When ``llm_enabled=True`` and services are injected, ``validate()``
dispatches to ``_validate_llm()`` which uses the shared LLM infrastructure
(ModelRouter, PromptTemplateRegistry, ModelAdapter).
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from film_pipeline.schemas._base import IssueSeverity, ValidationModality, ValidationStatus
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
)
from film_pipeline.schemas.validation import ValidationIssue, ValidationReport
from film_pipeline.validation.thresholds import score_to_status

_logger = logging.getLogger(__name__)


class BaseValidator(ABC):
    """Standard validator lifecycle.

    Subclasses implement ``_validate_rules()`` for rule-based checks.
    When ``llm_enabled=True`` and services are injected, ``validate()``
    dispatches to ``_validate_llm()``.
    """

    entry: ValidatorRegistryEntry
    llm_enabled: bool = False

    def __init__(self, entry: ValidatorRegistryEntry) -> None:
        self.entry = entry
        self._adapter: Any = None
        self._router: Any = None
        self._template_registry: Any = None
        self._prompt_runner: Any = None

    # ── Service injection ──────────────────────────────────────────

    def set_services(
        self,
        *,
        adapter: Any = None,
        router: Any = None,
        template_registry: Any = None,
        prompt_runner: Any = None,
    ) -> None:
        """Inject runtime services for LLM validation.

        Args:
            adapter: ModelAdapter instance (required for LLM calls).
            router: ModelRouter instance (required for model resolution).
            template_registry: PromptTemplateRegistry (required for prompt loading).
            prompt_runner: PromptRunner instance (optional, for RCTCO assembly).
        """
        if adapter is not None:
            self._adapter = adapter
        if router is not None:
            self._router = router
        if template_registry is not None:
            self._template_registry = template_registry
        if prompt_runner is not None:
            self._prompt_runner = prompt_runner

    def _has_llm_services(self) -> bool:
        return (
            self._adapter is not None
            and self._router is not None
            and self._template_registry is not None
        )

    # ── Public API ──────────────────────────────────────────────────

    def validate(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run validation, dispatching to LLM or rules."""
        if self.llm_enabled and self._has_llm_services():
            try:
                return self._validate_llm(artifact, context)
            except Exception:
                _logger.warning(
                    "Validator '%s': LLM validation failed, falling back to rule-based check.",
                    self.entry.validator_id,
                )
        return self._validate_rules(artifact, context)

    @abstractmethod
    def _validate_rules(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Rule-based validation (existing logic, renamed from validate)."""
        ...

    # ── LLM validation lifecycle ────────────────────────────────────

    def _validate_llm(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Shared LLM validation: prompt → model → parse."""
        # 1. Load template
        template = self._template_registry.get(agent_id=self.entry.validator_id)
        if template is None:
            raise RuntimeError(
                f"No prompt template found for validator '{self.entry.validator_id}'"
            )

        # 2. Resolve model
        profile = self.entry.model_profile
        if not profile:
            raise RuntimeError(f"Validator '{self.entry.validator_id}' has no model_profile set.")
        model = self._router.resolve_or_raise(profile)

        # 3. Build prompt
        ctx = (context or {}) | {"artifact": artifact}
        prompt = self._build_validation_prompt(template, ctx)

        # 4. Call LLM
        is_multimodal = self._needs_multimodal()
        images = self._extract_images(artifact) if is_multimodal else None

        if is_multimodal and images:
            text = self._adapter.chat_multimodal(
                prompt,
                model=model,
                images_b64=images,
                max_tokens=4096,
                temperature=0.2,
            )
        else:
            text = self._adapter.chat(
                prompt,
                model=model,
                system=template.role,
                max_tokens=4096,
                temperature=0.2,
            )

        # 5. Parse response
        return self._parse_validation_response(text)

    def _build_validation_prompt(
        self,
        template: Any,
        context: dict[str, Any],
    ) -> str:
        """Build the full validation prompt from template + context."""
        if self._prompt_runner is not None:
            return str(self._prompt_runner.build(template=template, context=context))
        # Fallback: assemble full prompt from template parts
        parts = []
        if template.core_task:
            parts.append(template.core_task)
        if template.context_template:
            parts.append(template.context_template.format_map(_SafeDict(context)))
        if template.constraints:
            parts.append(template.constraints)
        if template.output_format:
            parts.append(f"Respond ONLY with valid JSON in this format:\n{template.output_format}")
        return "\n\n".join(parts)

    def _needs_multimodal(self) -> bool:
        """Check if this validator needs multimodal (image+text) input."""
        return (
            ValidationModality.IMAGE in self.entry.modalities
            or ValidationModality.VIDEO in self.entry.modalities
        )

    @staticmethod
    def _image_data(item: object) -> str | None:
        """Return the base64 image carried by one list item, when present."""
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            b64 = item.get("data") or item.get("b64") or item.get("image_b64")
            if b64:
                return str(b64)
        return None

    def _extract_images(self, artifact: dict[str, Any]) -> list[str]:
        """Extract base64-encoded images from the artifact.

        Override in subclasses for artifact-specific extraction.
        """
        for key in ("images", "frames", "asset_data", "clips"):
            value = artifact.get(key)
            if isinstance(value, list) and value:
                images = [image for item in value if (image := self._image_data(item)) is not None]
                if images:
                    return images
        return []

    def _parse_validation_response(self, text: str) -> dict[str, Any]:
        """Parse LLM response into the expected raw dict format."""
        text = text.strip()
        direct = _parse_json_dict_or_none(text)
        if direct is not None:
            return direct

        for fence in ("```json", "```JSON", "```"):
            if fence in text:
                idx = text.rfind(fence)
                block = text[idx + len(fence) :]
                close = block.find("```")
                if close != -1:
                    block = block[:close]
                fenced = _parse_json_dict_or_none(block.strip())
                if fenced is not None:
                    return fenced

        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            embedded = _parse_json_dict_or_none(text[brace_start : brace_end + 1])
            if embedded is not None:
                return embedded

        raise ValueError(
            f"Validator '{self.entry.validator_id}' LLM response is not valid JSON. "
            f"Preview: {text[:300]}"
        )

    # ── Abstract methods (unchanged) ────────────────────────────────

    @abstractmethod
    def extract_score(self, raw: dict[str, Any]) -> float:
        """Extract a 0-100 score from the raw validation output."""
        ...

    def extract_issues(self, raw: dict[str, Any]) -> list[ValidationIssue]:
        """Extract standard issues (blocking + warnings) from raw output.

        Validators may override this when their model output uses a different
        issue shape, but the common JSON contract is handled here.
        """
        return [
            ValidationIssue(
                code=str(issue.get("code", "unknown")),
                message=str(issue.get("message", "")),
                severity=IssueSeverity(issue.get("severity", "info")),
                suggestion=str(issue.get("suggestion", "")),
                affected_entity=str(issue.get("affected_entity", "")),
                affected_field=str(issue.get("affected_field", "")),
                affected_shot=str(issue.get("affected_shot", "")),
            )
            for issue in raw.get("issues", [])
        ]

    # ── Full lifecycle ──────────────────────────────────────────────

    def run(
        self,
        artifact: dict[str, Any],
        artifact_refs: list[str] | None = None,
        context: dict[str, Any] | None = None,
    ) -> ValidationReport:
        """Full lifecycle: validate → score → classify → report."""
        raw = self.validate(artifact, context)
        score = self.extract_score(raw)
        issues = self.extract_issues(raw)

        blocking = [i for i in issues if i.severity == "blocking"]
        warnings = [i for i in issues if i.severity != "blocking"]
        status = score_to_status(score, self.entry.thresholds)

        # Four-status contract: BLOCKED must have at least one blocking issue.
        if status == ValidationStatus.BLOCKED and not blocking:
            blocking = [
                ValidationIssue(
                    code="score_below_threshold",
                    message=f"Score {score:.1f} is below the block threshold.",
                    severity=IssueSeverity.BLOCKING,
                )
            ]

        return ValidationReport(
            validation_id=f"validation:{self.entry.validator_id}:{uuid4().hex[:8]}",
            validator_id=self.entry.validator_id,
            scope=self.entry.scope,
            modalities=list(self.entry.modalities),
            artifact_refs=artifact_refs or [],
            score=score,
            status=status,
            blocking_issues=blocking,
            warnings=warnings,
            recommended_actions=_recommended_actions(status, blocking),
            requires_human_review=status
            in (
                ValidationStatus.NEEDS_REVISION,
                ValidationStatus.BLOCKED,
            ),
        )


class _SafeDict(dict[str, str]):
    """Format-map dict that leaves unknown placeholders as ``{key}`` text."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def _parse_json_dict_or_none(text: str) -> dict[str, Any] | None:
    """Return ``text`` decoded as a JSON object, or None when it is not valid JSON."""
    try:
        return dict(json.loads(text))
    except json.JSONDecodeError:
        return None


def _recommended_actions(
    status: ValidationStatus,
    blocking: list[ValidationIssue],
) -> list[str]:
    if status == ValidationStatus.PASS:
        return []
    if status == ValidationStatus.PASS_WITH_NOTES:
        return ["Review warnings before proceeding."]
    if status == ValidationStatus.NEEDS_REVISION:
        return ["Revise the artifact and resubmit for validation."]
    if blocking:
        return [f"Resolve: {i.code} — {i.message}" for i in blocking]
    return ["Review and revise before resubmitting."]
