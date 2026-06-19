"""Tests for BaseValidator abstract class."""

from __future__ import annotations

from typing import Any

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import ValidatorRegistryEntry
from film_pipeline.schemas.validation import ValidationIssue
from film_pipeline.validation.base import BaseValidator


class _ConcreteValidator(BaseValidator):
    def validate(
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
    def validate(
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
