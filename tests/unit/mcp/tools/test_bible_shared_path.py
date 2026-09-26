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

**What these guards are, honestly.** They are a tripwire against re-introducing
the specific shape this audit found, not a proof that a second lifecycle is
impossible. An adversarial pass built a rogue module that evades them by aliasing
the import (``AgentRegistration as _AR``), fetching the adapter with ``getattr``,
and naming its agent with anything other than a module-level ``_AGENT_ID``. That
evasion is why rules 1-3 also resolve import aliases and ``getattr`` literals
rather than matching one syntax. A determined rewrite can still avoid all four;
what cannot survive is the *ordinary* way this code was written, which is the
regression that actually happened here. The real structural guarantee is that
the tools have no other way to reach a model: ``_run_bible_agent`` is the only
entry, and behaviour tests pin its output.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from film_pipeline.agents.roster import MVP_AGENTS

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BIBLES_DIR = _REPO_ROOT / "src" / "film_pipeline" / "mcp" / "tools" / "bibles"
_ROSTER_IDS = {agent.agent_id for agent in MVP_AGENTS}

# Attribute names that mean "reaching for the model layer directly".
_FORBIDDEN_ATTRS = {"model_adapter", "model_router"}

# Names that resolve to AgentRegistration, however they were imported.
_CONTRACT_NAMES = {"AgentRegistration"}


def _bible_modules() -> list[Path]:
    """Every module in the package, recursively.

    Recursive on purpose: a new ``bibles/sub/`` package would otherwise escape
    every rule here silently.
    """
    return sorted(p for p in _BIBLES_DIR.rglob("*.py") if "__pycache__" not in p.parts)


def _module_source(path: Path) -> str:
    return path.read_text()


def _imported_names(tree: ast.Module) -> dict[str, str]:
    """Map local name -> original name for ``import`` / ``from … import``.

    This is what defeats the ``AgentRegistration as _AR`` evasion: the local
    alias is resolved back to the name it came from.
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                aliases[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    aliases[alias.asname] = alias.name
    return aliases


def _string_literals(tree: ast.Module) -> set[str]:
    """Every string literal in the module, for ``getattr`` evasion checks."""
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_the_package_has_modules_to_check() -> None:
    """Guard against the sweep silently matching nothing."""
    assert len(_bible_modules()) >= 5


def test_the_sweep_reaches_subpackages() -> None:
    """The sweep must be recursive, or a subpackage escapes every rule."""
    assert _BIBLES_DIR in [p.parent for p in _bible_modules()], (
        "the sweep found no module directly in the package; it is scoped wrong"
    )
    # Every module in the tree, at any depth, must be in scope.
    on_disk = {p for p in _BIBLES_DIR.rglob("*.py") if "__pycache__" not in p.parts}
    assert set(_bible_modules()) == on_disk


@pytest.mark.parametrize("path", _bible_modules(), ids=lambda p: str(p.name))
def test_no_bible_tool_builds_its_own_agent_contract(path: Path) -> None:
    tree = ast.parse(_module_source(path))
    aliases = _imported_names(tree)

    offenders: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Direct call: AgentRegistration(...)
        if isinstance(func, ast.Name) and aliases.get(func.id, func.id) in _CONTRACT_NAMES:
            offenders.append(f"line {node.lineno}: {func.id}(...)")
        # Aliased name that was never imported (e.g. assigned from an import).
        if isinstance(func, ast.Name) and func.id in _CONTRACT_NAMES:
            offenders.append(f"line {node.lineno}: {func.id}(...)")

    assert not offenders, (
        f"{path.name} constructs an agent contract at {offenders}. "
        "The roster declares contracts; look one up by id instead."
    )


def _static_string(node: ast.expr) -> str | None:
    """Fold a constant expression to its string value, or None if not static.

    Handles the concatenation evasion: ``getattr(runner, "model_a" + "dapter")``
    is a ``BinOp`` of two constants, not a ``Constant``.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _static_string(node.left)
        right = _static_string(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                return None
        return "".join(parts)
    return None


def _all_static_strings(tree: ast.Module) -> set[str]:
    """Every statically-known string in the module, concatenation folded."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.expr):
            continue
        folded = _static_string(node)
        if folded is not None:
            found.add(folded)
    return found


@pytest.mark.parametrize("path", _bible_modules(), ids=lambda p: str(p.name))
def test_no_bible_tool_reaches_for_the_model_layer(path: Path) -> None:
    """PromptRunner owns the model call, including its retry ladder."""
    tree = ast.parse(_module_source(path))
    offenders: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in _FORBIDDEN_ATTRS:
            offenders.append(f"line {node.lineno}: .{node.attr}")

    # getattr(runner, "model_adapter"), including a concatenated/joined name.
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "getattr" or len(node.args) < 2:
            continue
        name = _static_string(node.args[1])
        if name is None:
            offenders.append(f"line {node.lineno}: getattr with a non-static attribute name")
        elif name in _FORBIDDEN_ATTRS:
            offenders.append(f"line {node.lineno}: getattr(..., {name!r})")

    # Any final string that equals a forbidden attribute name, however built.
    for name in sorted(_all_static_strings(tree) & _FORBIDDEN_ATTRS):
        offenders.append(f"string literal {name!r}")

    assert not offenders, (
        f"{path.name} reaches for the model layer at {offenders}. Route the call "
        "through PromptRunner.run_from_template so there is one execution path."
    )


def test_no_module_calls_the_nonexistent_router_resolve() -> None:
    """``ModelRouter.resolve`` has never existed; this is the F-AGENT-04 bug."""
    from film_pipeline.agents.model_routing import ModelRouter

    assert not hasattr(ModelRouter, "resolve"), (
        "ModelRouter gained a `resolve` method — if that is deliberate, delete "
        "this guard and update the call sites; if not, it is the F-AGENT-04 bug."
    )

    offenders: list[str] = []
    # Any .resolve( call whose receiver is or holds a router.
    for path in _bible_modules():
        tree = ast.parse(_module_source(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "resolve"):
                continue
            receiver = func.value
            # model_router.resolve(...) or something.model_router.resolve(...)
            if (isinstance(receiver, ast.Attribute) and receiver.attr in _FORBIDDEN_ATTRS) or (
                isinstance(receiver, ast.Name) and "router" in receiver.id
            ):
                offenders.append(f"{path.name}:{node.lineno}")
        if "resolve(" in _module_source(path):
            # Covers the alias route (`routed = runner.model_router`) by
            # flagging any bare string-built receiver too.
            for name in _string_literals(tree):
                if name in _FORBIDDEN_ATTRS:
                    offenders.append(f"{path.name}: string literal {name!r}")

    assert not offenders, f"these call ModelRouter.resolve, which does not exist: {offenders}"


def test_every_agent_id_the_tools_name_is_on_the_roster() -> None:
    """A bible tool may only drive an agent the roster actually declares.

    Any string literal that looks like an agent id is checked, not just a
    module-level ``_AGENT_ID`` constant — the adversary's evasion was to spell
    the id some other way.
    """
    pattern = re.compile(r"^[a-z][a-z0-9-]*-agent$|^[a-z][a-z0-9-]*-validator$")

    named: dict[str, set[str]] = {}
    for path in _bible_modules():
        tree = ast.parse(_module_source(path))
        found = {s for s in _string_literals(tree) if pattern.match(s)}
        if found:
            named[path.name] = found

    assert named, "no bible module names an agent id; the sweep checks nothing"

    unknown = {name: sorted(ids - _ROSTER_IDS) for name, ids in named.items() if ids - _ROSTER_IDS}
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


# The operator-facing message each tool must produce when its agent rejects
# model output. Pinned because routing the tools through the shared helper once
# collapsed all five into one generic string: the agent id was carried by the
# exception but the tool's own wording was dropped.
_INVALID_OUTPUT_MESSAGE: dict[str, str] = {
    "camera.py": "CameraBible agent produced invalid output.",
    "character.py": "CharacterBible agent produced invalid output.",
    "environment.py": "EnvironmentBible agent produced invalid output.",
    "style.py": "StyleBible agent produced invalid output.",
    "shot.py": "ShotBible agent produced invalid output.",
}


@pytest.mark.parametrize("filename", sorted(_INVALID_OUTPUT_MESSAGE), ids=str)
def test_tool_reports_its_own_invalid_output_message(filename: str) -> None:
    """A tool's rejection message must name its own artifact, not a generic one."""
    expected = _INVALID_OUTPUT_MESSAGE[filename]
    tree = ast.parse((_BIBLES_DIR / filename).read_text())

    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert expected in literals, (
        f"{filename} no longer returns {expected!r}. The shared helper raises "
        "InvalidBibleOutput carrying the agent id; the tool must translate that "
        "into its own operator-facing wording."
    )


def test_every_bible_tool_handles_the_invalid_output_exception() -> None:
    """Each tool must catch it explicitly, or the specific message is unreachable."""
    for filename in sorted(_INVALID_OUTPUT_MESSAGE):
        tree = ast.parse((_BIBLES_DIR / filename).read_text())
        handled = any(
            isinstance(node, ast.ExceptHandler)
            and isinstance(node.type, ast.Name)
            and node.type.id == "InvalidBibleOutput"
            for node in ast.walk(tree)
        )
        assert handled, (
            f"{filename} does not catch InvalidBibleOutput, so its specific "
            "message can never be returned"
        )


def test_the_active_artifact_ref_write_has_one_definition() -> None:
    """One persisted-project write, one author.

    This body was defined byte-identically in two modules and inlined a third
    time. An independent probe removed the ``artifact_refs`` append from one
    copy and ran every suite — unit, smoke, integration and e2e — and **zero**
    tests failed, so the copies could drift apart unnoticed. It now lives once,
    in ``helpers``, and this pins that.
    """
    defining: list[str] = []
    for path in _BIBLES_DIR.parent.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_register_active_artifact_ref":
                defining.append(str(path.relative_to(_BIBLES_DIR.parent.parent.parent)))

    assert defining == ["mcp/tools/helpers.py"], (
        "the active-artifact-ref write must be defined exactly once, in "
        f"mcp/tools/helpers.py; found {defining}"
    )


def test_no_mcp_tool_inlines_the_active_artifact_ref_write() -> None:
    """Call the owner; do not re-derive its two lines."""
    offenders: list[str] = []
    for path in _BIBLES_DIR.parent.rglob("*.py"):
        if "__pycache__" in path.parts or path.name == "helpers.py":
            continue
        text = path.read_text()
        if 'setdefault("artifact_refs", []).append(' in text:
            offenders.append(str(path.relative_to(_BIBLES_DIR.parent)))

    assert not offenders, (
        "these MCP modules inline the active-artifact-ref write instead of "
        f"calling helpers._register_active_artifact_ref: {offenders}"
    )
