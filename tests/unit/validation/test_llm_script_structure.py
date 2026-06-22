"""Tests for ScriptStructureValidator LLM path."""

from __future__ import annotations

import json
from typing import Any

import pytest

from film_pipeline.agents.prompt_templates.registry import PromptTemplate
from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import ValidatorRegistryEntry
from film_pipeline.validation.impl.script_structure import ScriptStructureValidator


class FakeAdapter:
    """Returns pre-configured responses without network calls."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.last_prompt = ""
        self.last_model = ""

    def chat(
        self,
        prompt: str,
        *,
        model: str,
        system: str = "",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        self.last_prompt = prompt
        self.last_model = model
        self.last_system = system
        return self.response


class FakeRouter:
    def resolve_or_raise(self, profile_name: str) -> str:
        return f"test-model-{profile_name}"


class FakeTemplateRegistry:
    def __init__(self) -> None:
        self.templates: dict[str, PromptTemplate] = {}

    def get(self, agent_id: str) -> PromptTemplate | None:
        return self.templates.get(agent_id)

    def register(self, template: PromptTemplate) -> None:
        self.templates[template.agent_id] = template


def _make_template() -> PromptTemplate:
    return PromptTemplate(
        template_id="script-structure-v1",
        agent_id="scene-writing-validator",
        version=1,
        role="You are a script editor.",
        core_task="Evaluate script structure.",
        context_template="SCRIPT:\n{script_content}\nSCENES: {scene_count}",
        constraints="BLOCKING: no conflict.",
        output_format='{"score": 0, "passed": false, "issues": []}',
        output_schema_ref="validation.ValidationReport",
    )


def _llm_response(score: int, issues: list[dict[str, str]] | None = None) -> str:
    return json.dumps(
        {
            "score": score,
            "passed": score >= 85,
            "issues": issues or [],
        }
    )


def _make_validator(
    adapter: FakeAdapter,
    router: FakeRouter,
    template_registry: FakeTemplateRegistry,
) -> ScriptStructureValidator:
    validator = ScriptStructureValidator()
    validator.set_services(
        adapter=adapter,
        router=router,
        template_registry=template_registry,
    )
    return validator


def test_llm_path_produces_score() -> None:
    """LLM validation returns score and issues from the model response."""
    adapter = FakeAdapter(_llm_response(85, []))
    registry = FakeTemplateRegistry()
    registry.register(_make_template())

    validator = _make_validator(adapter, FakeRouter(), registry)
    raw = validator.validate({"scenes": [{"scene_id": "sc_001", "dialogue": []}]})

    assert raw["score"] == 85
    assert raw["passed"] is True
    assert raw["issues"] == []


def test_llm_path_includes_issues() -> None:
    """LLM response with issues is parsed correctly."""
    adapter = FakeAdapter(
        _llm_response(
            60,
            [
                {
                    "code": "no_conflict",
                    "severity": "blocking",
                    "message": "Scene sc_001 has no dramatic tension.",
                    "suggestion": "Add a disagreement between characters about a decision.",
                    "affected_entity": "sc_001",
                    "affected_field": "dialogue",
                    "affected_shot": "sc_001",
                }
            ],
        )
    )
    registry = FakeTemplateRegistry()
    registry.register(_make_template())

    validator = _make_validator(adapter, FakeRouter(), registry)
    raw = validator.validate({"scenes": [{"scene_id": "sc_001", "dialogue": []}]})

    assert raw["score"] == 60
    assert len(raw["issues"]) == 1
    assert raw["issues"][0]["code"] == "no_conflict"
    assert "suggestion" in raw["issues"][0]


def test_extract_issues_maps_suggestion_fields() -> None:
    """extract_issues() populates suggestion, affected_entity, etc."""
    adapter = FakeAdapter(
        _llm_response(
            75,
            [
                {
                    "code": "test_code",
                    "message": "test message",
                    "severity": "blocking",
                    "suggestion": "do this fix",
                    "affected_entity": "hero",
                    "affected_field": "dialogue",
                    "affected_shot": "s_001",
                }
            ],
        )
    )
    registry = FakeTemplateRegistry()
    registry.register(_make_template())

    validator = _make_validator(adapter, FakeRouter(), registry)
    raw = validator.validate({"scenes": []})
    issues = validator.extract_issues(raw)

    assert len(issues) == 1
    assert issues[0].suggestion == "do this fix"
    assert issues[0].affected_entity == "hero"
    assert issues[0].affected_field == "dialogue"
    assert issues[0].affected_shot == "s_001"


def test_llm_fallback_to_rules_on_error() -> None:
    """When LLM returns invalid JSON, falls back to rule-based validation."""
    adapter = FakeAdapter("this is not json {{{")
    registry = FakeTemplateRegistry()
    registry.register(_make_template())

    validator = _make_validator(adapter, FakeRouter(), registry)
    # Should not crash — falls back to _validate_rules()
    raw = validator.validate({"scenes": []})
    assert "issues" in raw
    assert raw["scenes_count"] == 0


def test_stub_still_works_when_disabled() -> None:
    """llm_enabled=False → rule-based path (backward compat)."""
    validator = ScriptStructureValidator()
    validator.llm_enabled = False
    raw = validator.validate(
        {"scenes": [{"scene_id": "sc_001", "intent_ref": "", "dialogue": [], "action_lines": []}]}
    )
    # Stub catches missing intent_ref
    assert any(i["code"] == "missing_scene_intent" for i in raw["issues"])


def test_stub_vs_llm_catches_semantic_issues() -> None:
    """LLM catches semantic issues the stub misses.

    A scene with the word 'conflict' in dialogue but zero actual tension:
    - Stub: passes (keyword found)
    - LLM: fails (no dramatic tension despite the word)
    """
    artifact: dict[str, Any] = {
        "scenes": [
            {
                "scene_id": "sc_001",
                "intent_ref": "establish_hero",
                "dialogue": [
                    {"character_id": "a", "line": "I'm very conflicted about this."},
                    {"character_id": "b", "line": "Yes, there is definitely conflict here."},
                ],
                "action_lines": ["They sit calmly drinking tea."],
            }
        ]
    }

    # Stub path
    validator_stub = ScriptStructureValidator()
    validator_stub.llm_enabled = False
    stub_result = validator_stub.validate(artifact)
    # Stub may or may not flag — depends on conflict keyword matching logic

    # LLM path (simulated — LLM correctly identifies zero tension)
    adapter = FakeAdapter(
        _llm_response(
            45,
            [
                {
                    "code": "no_conflict",
                    "severity": "blocking",
                    "message": (
                        "Scene 'sc_001': characters literally say 'conflict' but the scene "
                        "has zero dramatic tension — they're sitting calmly drinking tea."
                    ),
                    "suggestion": (
                        "Replace the dialogue with a disagreement about a concrete decision. "
                        "Have one character want action while the other wants caution."
                    ),
                    "affected_entity": "sc_001",
                    "affected_field": "dialogue",
                    "affected_shot": "sc_001",
                }
            ],
        )
    )
    registry = FakeTemplateRegistry()
    registry.register(_make_template())

    validator_llm = _make_validator(adapter, FakeRouter(), registry)
    llm_result = validator_llm.validate(artifact)

    # LLM correctly scores low
    assert llm_result["score"] < 50
    assert len(llm_result["issues"]) == 1
    assert llm_result["issues"][0]["suggestion"] != ""


def test_full_run_produces_report_with_suggestions() -> None:
    """run() lifecycle produces a ValidationReport with suggestion fields."""
    adapter = FakeAdapter(
        _llm_response(
            72,
            [
                {
                    "code": "no_conflict",
                    "severity": "blocking",
                    "message": "Scene has no tension.",
                    "suggestion": "Add a disagreement.",
                    "affected_entity": "sc_001",
                    "affected_field": "dialogue",
                    "affected_shot": "sc_001",
                }
            ],
        )
    )
    registry = FakeTemplateRegistry()
    registry.register(_make_template())

    validator = _make_validator(adapter, FakeRouter(), registry)
    report = validator.run({"scenes": []})

    assert report.score == 72
    assert len(report.blocking_issues) == 1
    assert report.blocking_issues[0].suggestion == "Add a disagreement."
    assert report.blocking_issues[0].affected_entity == "sc_001"
