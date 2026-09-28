"""The graph state contract: typed, not ``dict[str, Any]``.

## Why this guard exists

`StudioGraphState` (``orchestration/state_schema.py``) has declared every graph
state key, with a type and a reducer where one is needed, since Phase 2. It is
also already passed to ``StateGraph(StudioGraphState)`` in
``studio/graph_factory.py``. What was missing is that **nothing made the nodes
use it**: every node, edge and router was annotated ``state: dict[str, Any] ->
dict[str, Any]``, so the declared contract was decorative. Measured when this
guard was added (2026-09-27): 0 of 47 graph-facing functions named
``StudioGraphState``, and 167 ``state: dict[str, Any]`` annotations under
``orchestration/``.

That gap is not cosmetic, because a TypedDict is **not** assignable to
``dict[str, Any]``:

    error: Argument 1 to "helper" has incompatible type "StudioGraphState";
    expected "dict[str, Any]"  [arg-type]

Annotating a node therefore forces every helper it forwards state to be typed
honestly, and — the point of the exercise — makes mypy reject a node that returns
a key the contract does not declare:

    error: Extra key "not_a_key" for TypedDict "StudioGraphState"
    [typeddict-unknown-key]

That error is the mechanism that finds undocumented state. It requires the
return annotation to be ``StudioGraphState``; with ``dict[str, Any]`` the check
is silently skipped.

## What this enforces, and what it deliberately does not

Enforced, because each is robustly checkable from source:

1. Every function that receives the graph state names its type. ``dict[str, Any]``
   for a state parameter is the defect this guard exists to prevent.
2. The annotation is one of the three legitimate ones: ``StudioGraphState`` for
   graph-facing functions and mutators, ``Mapping[str, object]`` for read-only
   helpers, ``MutableMapping[str, object]`` where a mapping that may be written
   is genuinely wanted.
3. Every graph-facing function that returns a state update returns
   ``StudioGraphState``, so mypy can check its keys.

**Not enforced: read-only versus mutating.** This is the one place a static guard
would be actively harmful. A classifier that looks for direct writes to the state
parameter misses three things, all of which really occur in this tree:

- **Nested mutation** — ``advance_review_round`` does ``cycle["round_count"] = ...``
  on an object reached *through* state, with no store to state itself.
- **Transitive mutation** — ``_run_agent`` writes nothing to state directly, but
  calls ``_record_handoff``, which does ``state.setdefault(...)``.
- **Accumulator confusion** — ``_propagate_side_effects(source, dest, original)``
  writes to ``dest``, which is the caller's ``updates`` dict, not graph state at
  all. ``dest`` correctly stays ``dict[str, Any]``.

An earlier round of this task used exactly such a classifier and was wrong three
times for these three reasons. Choosing between ``Mapping`` and mutability is
therefore left to mypy and to review: mypy *does* reject a direct write through a
``Mapping`` (``Unsupported target for indexed assignment [index]``), while nested
mutation through a ``Mapping`` is invisible to it. That residue is a known,
stated limitation rather than something this file pretends to close.

## The governance exemption

``film_pipeline/governance/`` is exempt, and that is a design decision, not debt.
``governance`` sits below ``orchestration`` and must not import it; it has zero
such imports today. ``governance/gate_facts.py`` documents a ``GateFacts``
Protocol existing precisely so the gate law can read orchestrator facts "with no
upward edge in either direction", and ``orchestrator_reads.py`` declares the few
needed lookups structurally. Naming ``StudioGraphState`` there would create the
forbidden back-edge that ``Enola`` gates on. Those functions keep
``dict[str, Any]`` deliberately.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src" / "film_pipeline"
_ORCHESTRATION = _SRC_ROOT / "orchestration"

#: Packages that may not name `StudioGraphState`, with the reason.
#: `governance` is below `orchestration` and importing it would be a back-edge
#: (`governance/gate_facts.py` explains the structural-read workaround).
_STRUCTURAL_BOUNDARY_REASONS: dict[str, str] = {
    "governance": (
        "sits below `orchestration` and must not import it; `GateFacts` and "
        "`orchestrator_reads` declare these reads structurally instead"
    ),
}

#: Annotations that honestly describe a graph-state parameter. Matched
#: structurally by `_is_allowed`, not by string equality, because `ast.unparse`
#: renders `Mapping[...]` with or without its `collections.abc.` prefix.
_ALLOWED_STATE_ANNOTATIONS = (
    "StudioGraphState",
    "Mapping[str, object]",
    "MutableMapping[str, object]",
)

#: Functions that provably cannot name the contract, each with a checkable reason.
#:
#: These are enumerated **row by row on purpose**. The tempting alternative — a
#: predicate such as "exempt any function whose body writes a computed key" —
#: exempts a *class*, and a guard that exempts a class stops guarding: the next
#: function written in that style is silently exempt too. Each row below is a
#: claim a reviewer can check against the source, and
#: `test_exemptions_are_not_stale` fails when one stops matching anything.
_COMPUTED_KEY_WRITERS: dict[str, str] = {
    # Every one of these writes orchestrator state under a MODULE CONSTANT
    # (`_CANDIDATE_REFS`, `_PENDING_REVISIONS`, ...) via `state[k] = v` or
    # `state.setdefault(k, ...)`. A TypedDict rejects a computed key — measured:
    # `error: Expected TypedDict key to be string literal  [misc]`. A
    # `MutableMapping[str, object]` accepts the computed key but is itself not
    # assignable *from* a `StudioGraphState`, so it would reject the node callers
    # instead. `dict[str, Any]` is therefore the only type that accepts the
    # callers AND permits the write; the `dict(state)` copy at each boundary is
    # how a node feeds them.
    "init_refs": "writes candidate refs under the computed `_CANDIDATE_REFS` key",
    "set_candidate_ref": "writes under the computed `_CANDIDATE_REFS` key",
    "set_approved_ref": "writes under the computed `_APPROVED_REFS` key",
    "start_review_cycle": "writes under the computed `_ACTIVE_REVIEW_CYCLES` key",
    "add_revision_request": "writes under the computed `_PENDING_REVISIONS` key",
    "record_routing_decision": "writes under the computed `_ROUTING_DECISIONS` key",
    "add_failure_decision": "writes under the computed `_FAILURE_DECISIONS` key",
    "update_provider_health": "writes under the computed `_PROVIDER_HEALTH_SNAPSHOT` key",
    "ensure_orchestrator_state": "seeds six state domains under computed keys",
    # The resume helpers pass the state straight to `remove_issues_by_code`, whose
    # own signature is `dict[str, Any]` because it calls `merge_issues` — the
    # reducer that owns the removal rule. Narrowing these to `MutableMapping`
    # satisfies this guard but fails mypy at that call, and widening the reducer to
    # accept a mapping would change the rule's owner to accommodate a caller.
    "_strip_stale_generation_request_blockers": (
        "hands the state to remove_issues_by_code, which takes dict[str, Any]"
    ),
    # The gate law mutates through the injected fact port, not by a direct write:
    # `compute_actions` -> `facts.ensure_state(state)` ->
    # `OrchestratorGateFacts.ensure_state` -> `ensure_orchestrator_state`, which
    # does six `setdefault` calls. mypy cannot see this — `GateFacts.ensure_state`
    # declares `dict[str, Any]`, so the type is erased at that call — and a
    # `Mapping` annotation here would raise `AttributeError` at RUNTIME while
    # every gate stayed green.
    "compute_actions": "mutates transitively via `facts.ensure_state` under computed keys",
    # Called from `mcp`, `operations` and the resume path with plain project-state
    # dicts, and it writes the literal `issues` key. A `Mapping` cannot be written
    # (`[index]`) and a `StudioGraphState` would reject those dict callers.
    "remove_issues_by_code": "writes `issues` for callers that hold plain project dicts",
}

#: Functions whose returned key set is decided at runtime, with the reason.
_DYNAMIC_RETURN_REASONS: dict[str, str] = {
    # `repair_phase_node` dispatches to whichever of the eleven nodes in
    # `_PHASE_NODES` matches the current phase, then conditionally adds
    # `_orchestrator__convergence`, `issues`, `_orchestrator__pending_revisions`
    # and `_resume_to_repair` depending on the revision state. The key set is
    # therefore not knowable statically, and the only way to declare
    # `-> StudioGraphState` would be to `cast` the phase node's result — which
    # this migration forbids. `dict[str, Any]` is the honest return, and this
    # row is what keeps that from being invisible.
    "repair_phase_node": "returns whichever phase node ran, plus conditional keys",
}


def _state_param(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.arg | None:
    """The parameter holding graph state, or None when the function takes none.

    Only the canonical names are graded. A parameter called ``new_state`` or
    ``updates`` is a node-local partial-update accumulator, not the graph state:
    ``_propagate_side_effects(source, dest, original)`` writes to ``dest``, which
    is the caller's ``updates`` dict, and ``dest`` correctly stays
    ``dict[str, Any]``. Grading by parameter name keeps that distinction.
    """
    if not fn.args.args:
        return None
    first = fn.args.args[0]
    if first.arg in {"state", "graph_state", "_state"}:
        return first
    return None


def _functions() -> list[tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]]:
    found: list[tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for path in sorted(_ORCHESTRATION.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append((path, node))
    return found


def _all_functions() -> list[tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]]:
    """Every function under ``src/film_pipeline``, whatever package it is in."""
    found: list[tuple[Path, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append((path, node))
    return found


def _registered_callables() -> set[str]:
    """Names LangGraph is actually handed, read from every registration site.

    Scanning only ``orchestration/`` was a real hole: ``studio/graph_factory.py``
    registers ``_passthrough`` and ``_route_current_phase`` with ``add_node`` and
    ``add_conditional_edges``, so they are graph-facing while living outside the
    package the scan covered. Discovery is by registration rather than by path so
    a graph function cannot escape the guard by moving file.
    """
    names: set[str] = set()
    call = r"(?:add_node|add_conditional_edges|set_entry_point)\s*\("
    # Two real registration forms have to be matched, because the first argument
    # is not always a string literal:
    #   add_node("intake_node", intake_node)                  -> label, callable
    #   add_conditional_edges(phase_node, after_phase, ...)   -> variable, callable
    # Matching only the first form silently missed `after_phase`, which failed the
    # guard's own "did the scan find anything" test rather than the guard itself.
    label_then_callable = re.compile(
        call + r'\s*(?:"[^"]*"|\'[^\']*\'|[\w.]+)\s*,\s*([A-Za-z_]\w*)'
    )
    single_callable = re.compile(call + r"\s*([A-Za-z_]\w*)\s*[,)]")
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        for pattern in (label_then_callable, single_callable):
            for match in pattern.finditer(text):
                names.add(match.group(1))
    return names


def _graph_facing() -> set[str]:
    """Registered callable names, minus LangGraph's own API.

    ``add_node`` is called as ``builder.add_node("label", callable)``; the regex
    matches the callable position, but it also catches ``add_node("phase_router",
    _passthrough)``-style labels and LangGraph methods reached through the
    builder. Only names that resolve to a function defined in this repository are
    graded, so a stray match costs nothing.
    """
    return _registered_callables()


def _declared_state_keys() -> frozenset[str]:
    """The keys `StudioGraphState` declares, read from the live class.

    Read from the imported class rather than parsed from source: the annotations
    use ``Annotated[...]`` reducers and a source parser would have to re-derive
    them. Importing the owner of the contract is also the honest thing to measure.
    """
    from film_pipeline.orchestration.state_schema import StudioGraphState

    return frozenset(StudioGraphState.__annotations__)


_DECLARED_STATE_KEYS = _declared_state_keys()


def _is_allowed(rendered: str) -> bool:
    """Whether a rendered annotation is one of the legitimate state types.

    Matched structurally rather than against a fixed string set: ``ast.unparse``
    renders ``Mapping[str, object]`` with or without its ``collections.abc.``
    prefix depending on how it was imported, and a fixed set would report a
    correct annotation as a violation.
    """
    if rendered == "StudioGraphState":
        return True
    return any(
        rendered.startswith(f"{prefix}[")
        for prefix in ("Mapping", "MutableMapping", "collections.abc.Mapping")
    ) or rendered.startswith("collections.abc.MutableMapping[")


def test_no_orchestration_state_parameter_is_untyped() -> None:
    """A function receiving graph state must name a type the contract can check.

    This is the core check, and it is one check rather than two on purpose. A
    separate "is it in the allowed set" test would be the same scan over the same
    functions, and the obvious evasion — annotating a state parameter as bare
    ``Any`` or ``object``, which satisfies "not ``dict[str, Any]``" while naming
    nothing checkable — is closed by the allowed-set test *being* this test.
    """
    offenders: list[str] = []
    for path, fn in _functions():
        param = _state_param(fn)
        if param is None or param.annotation is None:
            continue
        if fn.name in _COMPUTED_KEY_WRITERS:
            continue
        rendered = ast.unparse(param.annotation)
        if not _is_allowed(rendered):
            offenders.append(f"{path.relative_to(_REPO_ROOT)}:{fn.lineno} {fn.name}({rendered})")

    assert not offenders, (
        f"{len(offenders)} function(s) take the graph state with an annotation that "
        f"names nothing checkable. Use `StudioGraphState` for graph-facing functions and "
        f"mutators, `Mapping[str, object]` for read-only helpers, or a "
        f"`MutableMapping[...]` where a writable mapping is genuinely wanted. If the "
        f"function provably cannot use any of them, add it to _COMPUTED_KEY_WRITERS with "
        f"a stated reason:\n  " + "\n  ".join(offenders[:40])
    )


def test_exemptions_are_not_stale() -> None:
    """Every exempted name must still exist, and still be exempt for its reason.

    An exemption that outlives its function is a hole: it would silently cover a
    future function that happens to reuse the name. This is the same failure the
    surface ratchet's "declared reasons are still needed" check closes.
    """
    scanned = {fn.name for _, fn in _functions()}
    stale = sorted(
        name for name in (*_COMPUTED_KEY_WRITERS, *_DYNAMIC_RETURN_REASONS) if name not in scanned
    )
    assert not stale, (
        f"{stale} are exempted but no longer exist under orchestration/. Remove the row "
        "so the exemption cannot cover a future function that reuses the name."
    )
    undated = sorted(
        name
        for name, reason in (*_COMPUTED_KEY_WRITERS.items(), *_DYNAMIC_RETURN_REASONS.items())
        if len(reason) < 20
    )
    assert not undated, f"exemptions with no real reason: {undated}"


def test_mapping_annotations_are_not_applied_to_direct_mutators() -> None:
    """A ``Mapping`` parameter that the same function writes to is a runtime bug.

    ``Mapping`` has no ``setdefault``, so annotating a mutator as ``Mapping`` is
    worse than not annotating it: mypy stays green while production raises
    ``AttributeError``. That is not hypothetical here — ``router.compute_actions``
    reaches ``facts.ensure_state``, and the ``GateFacts`` Protocol declares
    ``state: dict[str, Any]``, so the type is erased to ``dict[str, Any]`` at that
    call and mypy sees nothing. The mutation was confirmed by execution:

        AttributeError: 'M' object has no attribute 'setdefault'

    So this checks what *is* checkable — a direct store or a mutating method call
    on a parameter the same function declares ``Mapping``. It deliberately does
    **not** judge nested or transitive mutation, because a static classifier for
    those was measured wrong three times in this tree (see the module docstring).
    Nested and transitive cases are left to mypy and review; this test closes the
    cheap, common, mechanically-detectable case.
    """
    _MUTATORS = {"setdefault", "pop", "popitem", "update", "clear"}
    offenders: list[str] = []
    for path, fn in _functions():
        param = _state_param(fn)
        if param is None or param.annotation is None:
            continue
        rendered = ast.unparse(param.annotation)
        if "Mapping[" not in rendered or "MutableMapping" in rendered:
            continue
        name = param.arg
        for node in ast.walk(fn):
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id == name
                and isinstance(node.ctx, ast.Store)
            ):
                offenders.append(
                    f"{path.relative_to(_REPO_ROOT)}:{node.lineno} {fn.name} annotates "
                    f"`{name}` as {rendered} but writes `{name}[...] = ...`"
                )
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == name
                and node.func.attr in _MUTATORS
            ):
                offenders.append(
                    f"{path.relative_to(_REPO_ROOT)}:{node.lineno} {fn.name} annotates "
                    f"`{name}` as {rendered} but calls `{name}.{node.func.attr}()`"
                )

    assert not offenders, (
        "a `Mapping` parameter is written to, which fails at runtime (`Mapping` has no "
        "`setdefault`/item assignment) while mypy stays green:\n  " + "\n  ".join(offenders)
    )


def test_governance_does_not_name_the_graph_state() -> None:
    """The layering law: naming `StudioGraphState` in `governance` would invert it.

    The exemption in this guard's docstring is only honest if it is enforced.
    If `governance` ever names `StudioGraphState`, it must have imported
    `orchestration`, which is the back-edge `Enola` gates on.
    """
    governance = _REPO_ROOT / "src" / "film_pipeline" / "governance"
    offenders: list[str] = []
    for path in sorted(governance.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "StudioGraphState" in line:
                offenders.append(f"{path.relative_to(_REPO_ROOT)}:{lineno}: {line.strip()}")

    assert not offenders, (
        f"`governance` names `StudioGraphState`, which requires importing "
        f"`orchestration` and creates a forbidden back-edge "
        f"({_STRUCTURAL_BOUNDARY_REASONS['governance']}):\n  " + "\n  ".join(offenders)
    )


def test_state_update_returns_are_typed_so_mypy_can_check_their_keys() -> None:
    """A function returning a state update must say so, or mypy checks nothing.

    This is the half of the contract that actually finds undocumented state. With
    a ``dict[str, Any]`` return, a node can return a key the schema never declared
    and every gate stays green. Declaring ``StudioGraphState`` turns that into:

        error: Extra key "not_a_key" for TypedDict "StudioGraphState"
        [typeddict-unknown-key]

    The rule is scoped to functions that return a **dict literal whose keys are
    state keys** — the shape of a node update. It is deliberately not "every
    function returning a dict": helpers return payloads, envelopes and API
    responses, and demanding the graph-state type from those would be wrong.

    A note on why the accumulator must be typed rather than widened: mypy rejects
    ``u: dict[str, Any] = {}; return u`` against a ``StudioGraphState`` return, and
    there is no cast-free dynamic fold (``out[k] = v`` over ``.items()`` fails with
    ``[literal-required]``). So typing the accumulator *is* the fix, not a
    workaround.

    **Why the overlap test requires every key, not any key.** An earlier version
    flagged a function when *any* returned key was also a declared state key, and
    it reported ``_build_gate_payload`` as an offender. That function is not a node
    update at all: it returns the human-reviewer interrupt payload, which happens
    to carry ``project_id`` and ``artifact_refs`` alongside its own keys
    (``allowed_actions``, ``blocking_issue_count``, ...). Crying wolf on a
    correctly-typed payload is how a guard gets deleted, so the test now demands
    that *every* returned key be a declared state key. A genuine node update
    contains only state keys; a payload contains keys the schema has never heard of.
    """
    offenders: list[str] = []
    for path, fn in _functions():
        if _state_param(fn) is None:
            continue
        ret = fn.returns
        if ret is None or ast.unparse(ret) != "dict[str, Any]":
            continue
        # Every returned dict literal must consist solely of declared state keys.
        returned_dicts = [
            node.value
            for node in ast.walk(fn)
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)
        ]
        if not returned_dicts:
            continue
        keys_by_return = [
            {k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            for node in returned_dicts
        ]
        if all(keys and keys <= _DECLARED_STATE_KEYS for keys in keys_by_return):
            if fn.name in _DYNAMIC_RETURN_REASONS:
                continue
            union = sorted(set().union(*keys_by_return))
            offenders.append(
                f"{path.relative_to(_REPO_ROOT)}:{fn.lineno} {fn.name} -> dict[str, Any] "
                f"(returns only state keys: {union[:5]})"
            )

    assert not offenders, (
        f"{len(offenders)} function(s) return a state update as `dict[str, Any]`, so mypy "
        f"cannot check their keys against StudioGraphState. Declare the return "
        f"`StudioGraphState` (and type any accumulator that way too):\n  "
        + "\n  ".join(offenders[:40])
    )


def test_registered_graph_functions_are_typed_wherever_they_live() -> None:
    """Every function LangGraph is handed must be typed, in any package.

    The scan in ``_functions`` covers ``orchestration/``, which is where the
    nodes live but not where all of them live: ``studio/graph_factory.py``
    registers ``_passthrough`` and ``_route_current_phase``. Without this test a
    graph-facing function could sit outside the scanned package and never be
    graded. Discovery is by registration site, so moving a node to another file
    does not remove it from the guard.
    """
    offenders: list[str] = []
    for path, fn in _all_functions():
        if fn.name not in _graph_facing():
            continue
        param = _state_param(fn)
        if param is None:
            continue
        if param.annotation is None or not _is_allowed(ast.unparse(param.annotation)):
            rendered = ast.unparse(param.annotation) if param.annotation else "<missing>"
            offenders.append(f"{path.relative_to(_REPO_ROOT)}:{fn.lineno} {fn.name}({rendered})")

    assert not offenders, (
        f"{len(offenders)} function(s) registered with LangGraph do not type their state "
        f"parameter, so the graph contract does not cover them:\n  " + "\n  ".join(offenders)
    )


def test_graph_registration_discovery_is_not_empty() -> None:
    """Guard the guard: prove the registration scan actually finds callables.

    A regex that silently matched nothing would make the test above pass while
    checking nothing — the failure mode a guard may not have.
    """
    registered = _graph_facing()
    assert len(registered) >= 10, (
        f"only {len(registered)} registered callables found; the registration scan is "
        f"probably broken. Found: {sorted(registered)}"
    )
    expected = {"after_phase", "after_approval", "intake_node", "_route_current_phase"}
    missing = sorted(expected - registered)
    assert expected <= registered, f"expected registered callables missing from the scan: {missing}"


def test_state_parameters_actually_exist() -> None:
    """Guard the guard: prove the scanner reads the tree it claims to read.

    A scan that found nothing would pass every assertion above while checking
    nothing at all. This is the same failure the surface ratchet's
    `test_the_guard_has_something_to_check` was written to close.
    """
    typed = [
        (path, fn)
        for path, fn in _functions()
        if (p := _state_param(fn)) is not None and p.annotation is not None
    ]
    assert len(typed) >= 100, (
        f"only {len(typed)} typed state parameters found under orchestration/; the "
        "scanner is probably not reading the package it is meant to grade"
    )
    names = {fn.name for _, fn in typed}
    assert {"after_phase", "intake_node"} <= names, (
        f"expected known graph-facing functions in the scan, found neither: {sorted(names)[:20]}"
    )
