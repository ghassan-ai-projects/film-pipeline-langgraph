"""Tests for PromptTemplateRegistry.get / get_required."""

from __future__ import annotations

import pytest

import film_pipeline.agents.prompt_templates.registry as registry_module
from film_pipeline.agents.prompt_templates import PromptTemplate as PublicPromptTemplate
from film_pipeline.agents.prompt_templates import get_registry as package_get_registry
from film_pipeline.agents.prompt_templates.registry import (
    PromptTemplate,
    PromptTemplateRegistry,
)
from film_pipeline.agents.prompt_templates.template import PromptTemplate as OwnerPromptTemplate


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
    """Every import path for ``PromptTemplate`` must resolve to one class.

    This pins the ownership move that removed the `agents <->
    agents/prompt_templates` cycle. The class used to live at
    `agents/_prompt_template.py`, one level *above* the subpackage whose 58 uses
    justified it, and `prompt_templates/registry.py` re-exported it. That re-export
    was the cycle: `prompt_templates` depended on the parent package while the
    parent's `registry` reached back into the subpackage.

    It now lives in `prompt_templates/template.py` — the owner — and both the
    package root and the registry import it from there. If a second definition or
    a re-export shim is ever introduced, these identities diverge.
    """
    assert PromptTemplate is PublicPromptTemplate is OwnerPromptTemplate


def test_package_get_registry_loads_the_shipped_templates() -> None:
    """The package-level entry point returns a registry with defaults loaded.

    This is the function consumers call. `registry.get_registry` deliberately
    returns an *empty* registry — see the test below — because loading `defaults`
    from the `registry` submodule is the cycle that
    `prompt_templates -> registry -> defaults` creates. Ownership of the wiring
    sits at the package root.
    """
    registry = package_get_registry()
    assert {
        "scene-writing-validator",
        "dialogue-voice-validator",
        "prompt-readiness-validator",
        "reference-usability-validator",
        "scene-continuity-validator",
        "assembly-validator",
        "delivery-completeness-validator",
    } <= registry.templates.keys()


def test_registry_submodule_returns_an_empty_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The submodule's factory must not load defaults, and must be idempotent.

    Pinning the empty-by-default behaviour is what keeps the cycle from being
    reintroduced: if `registry.get_registry` ever registers the shipped templates
    again, it has to import `defaults` and the cycle returns.
    """
    monkeypatch.setattr(registry_module, "_registry", None)

    registry = registry_module.get_registry()

    assert registry.templates == {}
    assert registry_module.get_registry() is registry


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
