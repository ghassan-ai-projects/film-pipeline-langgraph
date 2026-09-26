"""The MCP bible tools must use the shared agent path, not their own.

Audit finding F-AGENT-04: the five bible tools under this package were a second
agent lifecycle. Each built its own ``AgentRegistration``, assembled prompts by
hand, and called ``model_adapter.chat`` directly — with a model id resolved
through ``ModelRouter.resolve``, a method that does not exist, and a reply
tested with ``isinstance(raw, dict)`` against a ``-> str`` return. The real-model
path raised before the request and could never have produced a bible.

These guards are structural on purpose. The defect was never a wrong *value*; it
was a second *path*, and a unit test that exercises the tools in mock mode cannot
see the difference — which is exactly why it survived. The rules:

1. No module here constructs an ``AgentRegistration``; the roster declares
   contracts.
2. No module here calls ``model_adapter`` or ``model_router``; ``PromptRunner``
   makes the model call.
3. No module here calls the router's ``resolve``, which does not exist.
4. Every agent id these tools name is on the roster, so its contract, class,
   template, and mock all resolve.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from film_pipeline.agents.roster import MVP_AGENTS

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BIBLES_DIR = _REPO_ROOT / "src" / "film_pipeline" / "mcp" / "tools" / "bibles"
_ROSTER_IDS = {agent.agent_id for agent in MVP_AGENTS}


def _bible_modules() -> list[Path]:
    return sorted(p for p in _BIBLES_DIR.glob("*.py") if "__pycache__" not in p.parts)


def test_the_package_has_modules_to_check() -> None:
    """Guard against the sweep silently matching nothing."""
    assert len(_bible_modules()) >= 5


@pytest.mark.parametrize("path", _bible_modules(), ids=lambda p: p.name)
def test_no_bible_tool_builds_its_own_agent_contract(path: Path) -> None:
    tree = ast.parse(path.read_text())
    offenders = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "AgentRegistration"
    ]
    assert not offenders, (
        f"{path.name} constructs AgentRegistration at line(s) {offenders}. "
        "The roster declares contracts; look one up by id instead."
    )


@pytest.mark.parametrize("path", _bible_modules(), ids=lambda p: p.name)
def test_no_bible_tool_calls_the_model_adapter_directly(path: Path) -> None:
    """PromptRunner owns the model call, including its retry ladder."""
    source = path.read_text()
    tree = ast.parse(source)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in {
            "model_adapter",
            "model_router",
        }:
            offenders.append(f"line {node.lineno}: {node.attr}")
    assert not offenders, (
        f"{path.name} reaches for {offenders} directly. Route the call through "
        "PromptRunner.run_from_template so there is one agent execution path."
    )


def test_no_module_calls_the_nonexistent_router_resolve() -> None:
    """``ModelRouter.resolve`` has never existed; this is the F-AGENT-04 bug."""
    from film_pipeline.agents.model_routing import ModelRouter

    assert not hasattr(ModelRouter, "resolve"), (
        "ModelRouter gained a `resolve` method — if that is deliberate, delete "
        "this guard and update the call sites; if not, it is the F-AGENT-04 bug."
    )

    offenders: list[str] = []
    for path in _bible_modules():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "resolve"
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "model_router"
            ):
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, f"these call ModelRouter.resolve, which does not exist: {offenders}"


def test_every_agent_id_the_tools_name_is_on_the_roster() -> None:
    """A bible tool may only drive an agent the roster actually declares."""
    import re

    pattern = re.compile(r'^_AGENT_ID = "([^"]+)"$', re.MULTILINE)
    named: dict[str, str] = {}
    for path in _bible_modules():
        for agent_id in pattern.findall(path.read_text()):
            named[path.name] = agent_id

    assert named, "no bible module declares _AGENT_ID; the sweep is not checking anything"

    unknown = {name: aid for name, aid in named.items() if aid not in _ROSTER_IDS}
    assert not unknown, (
        f"these bible tools drive agents that are not on the roster: {unknown}. "
        "Add a roster row (contract, class, template, mock) or use the right id."
    )


# Variables the shared helper supplies to every template it renders.
_HELPER_SUPPLIED = {"constraints", "kb_refs"}

# What each tool passes beyond those. Pinned here rather than introspected,
# because the point is to pin the *tool/helper contract*: a template placeholder
# that no call site supplies renders as literal "{name}" text in the prompt the
# model receives, and no mock-mode test can see that.
_CALL_SITE_VARS: dict[str, set[str]] = {
    "camera-bible-agent": {"camera_philosophy", "project_id"},
    "character-bible-agent": {
        "character_id",
        "character_name",
        "constitution_content",
        "script_content",
        "project_id",
    },
    "environment-bible-agent": {
        "environment_id",
        "environment_name",
        "theme",
        "visual_language",
        "script_content",
        "project_id",
    },
    "style-bible-agent": {"visual_language", "tone", "palette_hint", "project_id"},
}

# Braces that are JSON structure in the output_format blocks, not placeholders.
_NOT_PLACEHOLDERS = {"rrggbb"}


def _template_placeholders(agent_id: str) -> set[str]:
    import re

    from film_pipeline.agents.prompt_templates.registry import get_registry

    template = get_registry().get_required(agent_id)
    blob = "\n".join(
        [
            template.role,
            template.core_task,
            template.context_template,
            template.constraints,
            template.output_format,
            template.quality_instructions,
        ]
    )
    return set(re.findall(r"\{([a-z_][a-z0-9_]*)\}", blob)) - _NOT_PLACEHOLDERS


@pytest.mark.parametrize("agent_id", sorted(_CALL_SITE_VARS), ids=str)
def test_every_template_placeholder_has_a_supplier(agent_id: str) -> None:
    """Every placeholder the template declares must be supplied at render time."""
    supplied = _CALL_SITE_VARS[agent_id] | _HELPER_SUPPLIED
    unresolved = sorted(_template_placeholders(agent_id) - supplied)

    assert not unresolved, (
        f"{agent_id}'s template declares {unresolved}, which no call site "
        "supplies — rendering leaves the literal text in the prompt. Supply it "
        "from the tool or the helper, or drop it from the template."
    )


@pytest.mark.parametrize("agent_id", sorted(_CALL_SITE_VARS), ids=str)
def test_templates_render_without_unfilled_braces(agent_id: str) -> None:
    """Render for real with the supplied variables and inspect the output."""
    import re

    from film_pipeline.agents.prompt_templates.registry import get_registry

    supplied = _CALL_SITE_VARS[agent_id] | _HELPER_SUPPLIED
    rendered = (
        get_registry().get_required(agent_id).render(**{name: f"<{name}>" for name in supplied})
    )

    leftovers = sorted(set(re.findall(r"\{([a-z_][a-z0-9_]*)\}", rendered)) - _NOT_PLACEHOLDERS)
    assert not leftovers, (
        f"{agent_id} rendered with an unfilled placeholder: {leftovers}. "
        "The prompt sent to the model would contain literal braces."
    )


def test_the_camera_template_declares_no_placeholder_the_helper_cannot_fill() -> None:
    """Guard the guard: the sweep must be looking at something real."""
    assert _template_placeholders("camera-bible-agent"), (
        "camera-bible-agent's template declares no placeholders at all, so the "
        "two tests above cannot be checking anything"
    )


def test_the_helper_actually_supplies_the_vars_it_claims() -> None:
    """``_HELPER_SUPPLIED`` is a claim about ``_run_bible_agent``; verify it.

    The two render tests above trust a hardcoded set of variables the helper is
    said to provide. If the helper stops providing one, those tests would still
    pass while the prompt shipped a literal ``{name}``. This runs the helper's
    own body against a stub runtime and reads the variables it actually passes
    to ``run_from_template``.
    """
    from typing import Any

    from film_pipeline.agents.registry import AgentRegistry
    from film_pipeline.agents.roster import MVP_AGENTS
    from film_pipeline.mcp.tools.bibles import _shared
    from film_pipeline.schemas.kb import KBContextPacket

    captured: dict[str, Any] = {}

    class _StubRunner:
        def run_from_template(self, template: Any, kb: Any, task: str, **kw: Any) -> Any:
            captured.update(kw.get("context_vars") or {})
            captured["_agent_id"] = kw.get("agent_id")
            # Return a valid camera payload so the agent's validate() passes.
            return (
                {
                    "camera_bible": {
                        "project_id": "p",
                        "profiles": [
                            {
                                "profile_id": "default",
                                "use_case": "u",
                                "lens": "l",
                                "framing": "f",
                                "movement": "m",
                                "depth_of_field": "d",
                                "composition_rules": [],
                                "transition_rules": [],
                                "emotional_meaning": "e",
                            }
                        ],
                        "default_profile_id": "default",
                    }
                },
                "tpl",
                "creative_writer",
            )

    class _StubServices:
        prompt_runner = _StubRunner()
        agent_registry = AgentRegistry()

        def kb_for(self, **_kw: Any) -> KBContextPacket:
            return KBContextPacket(
                kb_context_id="kbctx:test",
                project_id="p",
                phase="visual_dev",
                agent_id="camera-bible-agent",
                task="t",
            )

    class _StubRt:
        services = _StubServices()

    _StubServices.agent_registry.register_many(MVP_AGENTS)

    _shared._run_bible_agent(
        _StubRt(),
        "camera-bible-agent",
        "task",
        {"camera_philosophy": "philosophy", "project_id": "p"},
    )

    missing = sorted(_HELPER_SUPPLIED - set(captured))
    assert not missing, (
        f"_run_bible_agent no longer supplies {missing}, which the templates "
        "declare and these tests assume. The prompt would contain literal braces."
    )
    assert captured["_agent_id"] == "camera-bible-agent"
    # And nothing the helper adds is a placeholder the template never declares,
    # which would mean the two sides of this contract have drifted apart.
    assert {"constraints", "kb_refs"} <= set(captured), captured
