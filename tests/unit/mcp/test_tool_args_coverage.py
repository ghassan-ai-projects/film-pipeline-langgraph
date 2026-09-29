"""A tool's args model must declare every key its handler reads.

This is the completion criterion for doc 04's slice 1, expressed as a check rather
than a work list. `extra="forbid"` makes an undeclared key a runtime refusal, so a
model that omits an argument a handler reads is not a cosmetic gap — the call fails.

It found exactly that during the migration. `plan_generation_batch` read
`args.get("mode", "test")` and the first model omitted `mode`, which the smoke suite
caught; the same sweep then confirmed it was the only one of 31 specs with an
undeclared key. A later slip — `ToolArgs.confirmed` silently not being defined —
was invisible to this check and to every gate, and only the smoke suite saw it,
which is why the protocol field is asserted separately below.
"""

from __future__ import annotations

import ast
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[3] / "src" / "film_pipeline" / "mcp" / "tools"

#: Keys dispatch injects or consumes itself, which no handler declares.
PROTOCOL_KEYS = {"confirmed", "project_ref", "_envelope"}


def _reads_key(node: ast.AST, name: str) -> set[str]:
    """Every string literal ``<name>.get("<key>", ...)`` reads."""
    out: set[str] = set()
    for x in ast.walk(node):
        if (
            isinstance(x, ast.Call)
            and isinstance(x.func, ast.Attribute)
            and x.func.attr == "get"
            and isinstance(x.func.value, ast.Name)
            and x.func.value.id == name
            and x.args
            and isinstance(x.args[0], ast.Constant)
            and isinstance(x.args[0].value, str)
        ):
            out.add(x.args[0].value)
    return out


def _handler_keys(fn: ast.AST) -> set[str]:
    """Keys read off ``args``, including through a local alias like ``a = args``."""
    names = {"args"}
    for x in ast.walk(fn):
        if isinstance(x, ast.Assign) and isinstance(x.value, ast.Name) and x.value.id in names:
            for target in x.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    out: set[str] = set()
    for name in names:
        out |= _reads_key(fn, name)
    return out


def _parse_tree(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text())
    except SyntaxError:
        return None


def _collect() -> tuple[dict[str, tuple[str, Path]], dict[str, set[str]]]:
    """Return ``{tool: (args_model, module)}`` and ``{model: field names}``."""
    specs: dict[str, tuple[str, Path]] = {}
    models: dict[str, set[str]] = {}
    for path in TOOLS.rglob("*.py"):
        tree = _parse_tree(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ToolSpec"
            ):
                name: str | None = None
                model: str | None = None
                for kw in node.keywords:
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant):
                        value = kw.value.value
                        if isinstance(value, str):
                            name = value
                    if kw.arg == "args" and isinstance(kw.value, ast.Name):
                        model = kw.value.id
                if name and model:
                    specs[name] = (model, path)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                models[node.name] = {
                    st.target.id
                    for st in node.body
                    if isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name)
                }
    return specs, models


def test_every_key_a_handler_reads_is_declared_on_its_args_model() -> None:
    specs, models = _collect()
    assert len(specs) >= 30, f"only {len(specs)} specs found; the sweep would be vacuous"

    problems: dict[str, list[str]] = {}
    for name, (model, path) in sorted(specs.items()):
        if model not in models:
            continue
        declared = models[model] | PROTOCOL_KEYS
        handlers = {
            n.name: n
            for n in ast.walk(_parse_tree(path) or ast.Module(body=[], type_ignores=[]))
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        handler_name = None
        for node in ast.walk(_parse_tree(path) or ast.Module(body=[], type_ignores=[])):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ToolSpec"
            ):
                spec_name = next(
                    (
                        kw.value.value
                        for kw in node.keywords
                        if kw.arg == "name" and isinstance(kw.value, ast.Constant)
                    ),
                    None,
                )
                if spec_name == name:
                    handler_name = next(
                        (
                            kw.value.id
                            for kw in node.keywords
                            if kw.arg == "handler" and isinstance(kw.value, ast.Name)
                        ),
                        None,
                    )
        if not handler_name or handler_name not in handlers:
            continue

        # Follow module-level helpers the handler calls, since they read ``args`` too.
        seen: set[str] = set()
        queue = [handler_name]
        while queue:
            current = queue.pop()
            if current in seen or current not in handlers:
                continue
            seen.add(current)
            for x in ast.walk(handlers[current]):
                if not (isinstance(x, ast.Call) and isinstance(x.func, ast.Name)):
                    continue
                if x.func.id in handlers:
                    queue.append(x.func.id)

        used: set[str] = set()
        for current in seen:
            used |= _handler_keys(handlers[current])
        missing = sorted(used - declared)
        if missing:
            problems[name] = missing

    assert not problems, (
        f"these tools read arguments their args model does not declare: {problems}. "
        'With extra="forbid" the call is refused, so the model is the work list.'
    )


def test_the_protocol_fields_are_really_declared() -> None:
    """`ToolArgs` must declare the fields dispatch consumes itself.

    - `confirmed` — `MCPServer._check_confirmation` reads it for every
      `confirm=True` tool.
    - `project_ref` — `MCPServer.call` lifts it into the request envelope, so a
      per-call project selection never reaches the handler either.

    If the base model does not declare one, `extra="forbid"` rejects the very field
    the protocol sends — and nothing else notices, because no handler looks at it
    and the field is absent rather than wrong.

    Both are regression guards with real incidents behind them: an edit meant to add
    `confirmed` silently did not apply (every gate stayed green; only the smoke
    suite's `promote_test_to_production` failed), and `project_ref` was discovered
    the same way, by `list_artifacts` rejecting a per-call project selection.
    """
    from film_pipeline.mcp.tools.spec import ToolArgs

    assert {"confirmed", "project_ref"} <= set(ToolArgs.model_fields)
    parsed = ToolArgs.model_validate({"confirmed": True, "project_ref": "proj-x"})
    assert parsed.confirmed is True
    assert parsed.project_ref == "proj-x"
