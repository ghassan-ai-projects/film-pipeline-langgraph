"""Tests for PromptTemplateRegistry.get / get_required."""

from __future__ import annotations

import pytest

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
