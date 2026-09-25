"""Tests for PromptTemplateRegistry.get / get_required."""

from __future__ import annotations

import pytest

import film_pipeline.agents.prompt_templates.registry as registry_module
from film_pipeline.agents._prompt_template import PromptTemplate as SharedPromptTemplate
from film_pipeline.agents.prompt_templates import PromptTemplate as PublicPromptTemplate
from film_pipeline.agents.prompt_templates.registry import (
    PromptTemplate,
    PromptTemplateRegistry,
)


def _template(agent_id: str = "test-agent") -> PromptTemplate:
    return PromptTemplate(
        template_id="t1",
        agent_id=agent_id,
        version=1,
        role="R",
        core_task="T",
        context_template="C",
        constraints="X",
        output_format="O",
        output_schema_ref="ref",
    )


def test_prompt_template_public_imports_share_one_class() -> None:
    assert PromptTemplate is PublicPromptTemplate is SharedPromptTemplate


def test_get_registry_loads_validator_templates_and_reuses_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(registry_module, "_registry", None)

    registry = registry_module.get_registry()
    first_validator = registry.get_required("scene-writing-validator")

    assert registry_module.get_registry() is registry
    assert registry.get_required("scene-writing-validator") is first_validator
    assert {
        "scene-writing-validator",
        "dialogue-voice-validator",
        "prompt-readiness-validator",
        "reference-usability-validator",
        "scene-continuity-validator",
        "assembly-validator",
        "delivery-completeness-validator",
    } <= registry.templates.keys()


class TestGet:
    def test_returns_registered_template(self) -> None:
        reg = PromptTemplateRegistry()
        tpl = _template()
        reg.register(tpl)
        assert reg.get("test-agent") is tpl

    def test_returns_none_when_unregistered(self) -> None:
        reg = PromptTemplateRegistry()
        assert reg.get("missing-agent") is None


class TestGetRequired:
    def test_returns_registered_template(self) -> None:
        reg = PromptTemplateRegistry()
        tpl = _template()
        reg.register(tpl)
        assert reg.get_required("test-agent") is tpl

    def test_raises_keyerror_when_unregistered(self) -> None:
        reg = PromptTemplateRegistry()
        with pytest.raises(KeyError, match="No dedicated prompt template registered"):
            reg.get_required("missing-agent")
