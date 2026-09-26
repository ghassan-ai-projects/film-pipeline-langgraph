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
