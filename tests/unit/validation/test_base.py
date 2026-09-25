"""Tests for BaseValidator abstract class."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from film_pipeline.schemas.base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import ValidatorRegistryEntry
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator


class _ConcreteValidator(BaseValidator):
    def _validate_rules(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _ = context
        return {"score": artifact.get("score", 90), "issues": []}

    def extract_score(self, raw: dict[str, Any]) -> float:
        return float(raw.get("score", 0))

    def extract_issues(self, raw: dict[str, Any]) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = raw.get("issues", [])
        return issues


class _BlockingValidator(_ConcreteValidator):
    def _validate_rules(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _ = artifact
        _ = context
        return {
            "score": 50,
            "issues": [{"code": "b1", "message": "bad", "severity": "blocking"}],
        }

    def extract_issues(self, raw: dict[str, Any]) -> list[ValidationIssue]:
        return [
            ValidationIssue(
                code=i["code"],
                message=i["message"],
                severity=i["severity"],
            )
            for i in raw["issues"]
        ]


@dataclass(frozen=True)
class _Template:
    role: str = "validator"
    core_task: str = "Validate the artifact."
    context_template: str = "Project: {project_id}; Missing: {missing}"
    constraints: str = "Be strict."
    output_format: str = '{"score": 90, "issues": []}'


class _TemplateRegistry:
    def __init__(self, template: _Template | None = None, *, missing: bool = False) -> None:
        self.template = None if missing else template or _Template()

    def get(self, *, agent_id: str) -> _Template | None:
        _ = agent_id
        return self.template


class _Router:
    def resolve_or_raise(self, profile: str) -> str:
        return f"model:{profile}"


class _Adapter:
    def __init__(self, *, response: str) -> None:
        self.response = response
        self.chat_calls: list[dict[str, Any]] = []
        self.multimodal_calls: list[dict[str, Any]] = []

    def chat(self, prompt: str, **kwargs: Any) -> str:
        self.chat_calls.append({"prompt": prompt, **kwargs})
        return self.response

    def chat_multimodal(self, prompt: str, **kwargs: Any) -> str:
        self.multimodal_calls.append({"prompt": prompt, **kwargs})
        return self.response


class _PromptRunner:
    def build(self, *, template: _Template, context: dict[str, Any]) -> str:
        return f"runner:{template.role}:{context['artifact']['name']}"


class _FailingLLMValidator(_ConcreteValidator):
    llm_enabled = True

    def _validate_llm(
        self,
        artifact: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _ = artifact
        _ = context
        raise RuntimeError("provider unavailable")


class TestBaseValidator:
    def test_run_pass(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="test-v",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )
        validator = _ConcreteValidator(entry)
        report = validator.run({"score": 90}, artifact_refs=["ref:1"])
        assert report.score == 90
        assert report.validator_id == "test-v"
        assert report.artifact_refs == ["ref:1"]

    def test_run_blocking_issues(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="test-v",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )
        validator = _BlockingValidator(entry)
        report = validator.run({"score": 50})
        assert len(report.blocking_issues) == 1
        assert report.blocking_issues[0].code == "b1"
        assert report.requires_human_review is True

    def test_entry_stored(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="test-v",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )
        validator = _ConcreteValidator(entry)
        assert validator.entry.validator_id == "test-v"

    def test_run_pass_with_notes(self) -> None:
        """Score 80 → PASS_WITH_NOTES."""
        entry = ValidatorRegistryEntry(
            validator_id="test-v",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )

        class _NotesValidator(_ConcreteValidator):
            def _validate_rules(
                self,
                artifact: dict[str, Any],
                context: dict[str, Any] | None = None,
            ) -> dict[str, Any]:
                _ = artifact
                _ = context
                return {"score": 80, "issues": []}

        validator = _NotesValidator(entry)
        report = validator.run({"score": 80})
        assert report.score == 80
        assert len(report.recommended_actions) > 0

    def test_run_needs_revision_without_blocking(self) -> None:
        """NEEDS_REVISION status with no blocking → fallback recommendation."""
        entry = ValidatorRegistryEntry(
            validator_id="test-v",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )

        class _ReviseValidator(_ConcreteValidator):
            def _validate_rules(
                self,
                artifact: dict[str, Any],
                context: dict[str, Any] | None = None,
            ) -> dict[str, Any]:
                _ = artifact
                _ = context
                return {
                    "score": 70,
                    "issues": [{"code": "w1", "message": "weak", "severity": "warning"}],
                }

            def extract_issues(self, raw: dict[str, Any]) -> list[ValidationIssue]:
                return [
                    ValidationIssue(code=i["code"], message=i["message"], severity=i["severity"])
                    for i in raw["issues"]
                ]

        validator = _ReviseValidator(entry)
        report = validator.run({"score": 70})
        assert len(report.recommended_actions) > 0

    def test_validate_falls_back_when_llm_services_missing(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="test-v",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )
        validator = _ConcreteValidator(entry)
        validator.llm_enabled = True

        assert validator.validate({"score": 88}) == {"score": 88, "issues": []}

    def test_validate_falls_back_when_llm_raises(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="test-v",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )
        validator = _FailingLLMValidator(entry)
        validator.set_services(
            adapter=_Adapter(response='{"score": 99, "issues": []}'),
            router=_Router(),
            template_registry=_TemplateRegistry(),
        )

        assert validator.validate({"score": 77}) == {"score": 77, "issues": []}

    def test_validate_llm_uses_text_chat_and_prompt_runner(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="test-v",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
            model_profile="quality-medium",
        )
        adapter = _Adapter(response='{"score": 91, "issues": []}')
        validator = _ConcreteValidator(entry)
        validator.set_services(
            adapter=adapter,
            router=_Router(),
            template_registry=_TemplateRegistry(),
            prompt_runner=_PromptRunner(),
        )

        raw = validator._validate_llm({"name": "draft"}, {"project_id": "p1"})

        assert raw == {"score": 91, "issues": []}
        assert adapter.chat_calls[0]["prompt"] == "runner:validator:draft"
        assert adapter.chat_calls[0]["model"] == "model:quality-medium"
        assert adapter.chat_calls[0]["system"] == "validator"

    def test_validate_llm_uses_multimodal_chat_when_images_exist(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="image-v",
            scope=ValidationScope.CLIP,
            modalities=[ValidationModality.IMAGE],
            model_profile="vision",
        )
        adapter = _Adapter(response='{"score": 94, "issues": []}')
        validator = _ConcreteValidator(entry)
        validator.set_services(
            adapter=adapter,
            router=_Router(),
            template_registry=_TemplateRegistry(),
        )

        raw = validator._validate_llm(
            {
                "images": [
                    "raw-b64",
                    {"data": "data-b64"},
                    {"b64": "b64-value"},
                    {"image_b64": "image-b64"},
                    {"ignored": ""},
                ]
            },
            {"project_id": "p1"},
        )

        assert raw["score"] == 94
        assert adapter.chat_calls == []
        assert adapter.multimodal_calls[0]["images_b64"] == [
            "raw-b64",
            "data-b64",
            "b64-value",
            "image-b64",
        ]

    def test_validate_llm_requires_template_and_model_profile(self) -> None:
        no_template_entry = ValidatorRegistryEntry(
            validator_id="missing-template",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
            model_profile="quality-medium",
        )
        validator = _ConcreteValidator(no_template_entry)
        validator.set_services(
            adapter=_Adapter(response="{}"),
            router=_Router(),
            template_registry=_TemplateRegistry(missing=True),
        )

        with pytest.raises(RuntimeError, match="No prompt template"):
            validator._validate_llm({"name": "draft"})

        no_profile_entry = ValidatorRegistryEntry(
            validator_id="missing-profile",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )
        validator = _ConcreteValidator(no_profile_entry)
        validator.set_services(
            adapter=_Adapter(response="{}"),
            router=_Router(),
            template_registry=_TemplateRegistry(),
        )

        with pytest.raises(RuntimeError, match="no model_profile"):
            validator._validate_llm({"name": "draft"})

    def test_build_validation_prompt_preserves_missing_placeholders(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="test-v",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )
        validator = _ConcreteValidator(entry)

        prompt = validator._build_validation_prompt(_Template(), {"project_id": "p1"})

        assert "Validate the artifact." in prompt
        assert "Project: p1; Missing: {missing}" in prompt
        assert "Respond ONLY with valid JSON" in prompt

    def test_parse_validation_response_accepts_fences_and_embedded_json(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="test-v",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.TEXT],
        )
        validator = _ConcreteValidator(entry)

        assert validator._parse_validation_response('```json\n{"score": 90}\n```') == {"score": 90}
        assert validator._parse_validation_response('prefix {"score": 81} suffix') == {"score": 81}

        with pytest.raises(ValueError, match="not valid JSON"):
            validator._parse_validation_response("no json here")

    def test_extract_images_checks_known_artifact_fields(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="test-v",
            scope=ValidationScope.ARTIFACT,
            modalities=[ValidationModality.VIDEO],
        )
        validator = _ConcreteValidator(entry)

        assert validator._extract_images({"frames": [{"image_b64": "frame-b64"}]}) == ["frame-b64"]
        assert validator._extract_images({"clips": []}) == []
