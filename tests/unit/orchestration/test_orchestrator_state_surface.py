"""Public-surface contract for ``orchestration.orchestrator_state``.

The module carries 39 public symbols across eight state slices, which made it
one of the widest surfaces in the repository (``07`` §3, §6.4: "97% public").
Adding a declared surface is the fix — the diagnosis was a *surface* problem,
not a size one, so the module is deliberately not split.

Three guards:

1. **Declared surface** — ``__all__`` names every public accessor, and no public
   callable or class is missing from it.
2. **No private leakage** — consumers outside the module never import a
   ``_``-prefixed name from it. ``require_human_approval`` is the one internal
   helper the node layer legitimately needs, and it is reached through the
   module's own gate API rather than by name.
3. **No key rebuilding** — no module outside ``orchestrator_state`` constructs an
   ``_orchestrator__`` key by hand. That was the defect class behind the
   duplicated `issues` writers: the accessors exist so callers never re-derive
   the key grammar.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from film_pipeline.orchestration import orchestrator_state

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src" / "film_pipeline"
_MODULE_PATH = _SRC / "orchestration" / "orchestrator_state.py"
_MODULE_STEM = "orchestrator_state"


def _public_module_symbols() -> set[str]:
    """Public callables and classes defined in the module, excluding re-exports."""
    found: set[str] = set()
    for name, obj in vars(orchestrator_state).items():
        if name.startswith("_"):
            continue
        if not (inspect.isfunction(obj) or inspect.isclass(obj)):
            continue
        if getattr(obj, "__module__", None) != orchestrator_state.__name__:
            continue  # imported, not defined here
        found.add(name)
    # Module-level constants the module defines itself.
    for name in ("ORCH_CHANNELS",):
        if hasattr(orchestrator_state, name):
            found.add(name)
    return found


def test_declared_surface_covers_every_public_definition() -> None:
    declared = set(orchestrator_state.__all__)
    defined = _public_module_symbols()

    missing = sorted(defined - declared)
    assert not missing, (
        "orchestrator_state defines public symbols that __all__ does not declare: "
        f"{missing}. Either declare them or make them private."
    )


def test_declared_surface_names_only_existing_symbols() -> None:
    stale = sorted(
        name for name in orchestrator_state.__all__ if not hasattr(orchestrator_state, name)
    )
    assert not stale, f"orchestrator_state.__all__ names symbols that do not exist: {stale}"


def test_declared_surface_is_a_subset_of_the_real_public_names() -> None:
    """``__all__`` must not be wider than what the module actually exposes."""
    real = {n for n in vars(orchestrator_state) if not n.startswith("_")}
    extra = sorted(set(orchestrator_state.__all__) - real)
    assert not extra, f"orchestrator_state.__all__ exports unknown names: {extra}"


def _iter_source_modules() -> list[Path]:
    return [p for p in _SRC.rglob("*.py") if "__pycache__" not in p.parts and p != _MODULE_PATH]


def test_no_module_outside_rebuilds_an_orchestrator_key_to_read() -> None:
    """The ``_orchestrator__`` key grammar has exactly one author.

    Scope: *reads*. A module that indexes the state dict with a hand-written
    ``_orchestrator__`` key is re-deriving the key grammar the accessors exist
    to own — the same defect class as the duplicated ``issues`` writers.

    Out of scope, deliberately: the boundary-propagation writes in
    ``orchestration/nodes/_agent_handoff.py`` and ``_repair_loop.py``. Those
    keys are carried *out* of a node by the channel mechanism, which reads its
    own ``ORCH_CHANNELS`` registry; writing them is the mechanism's job, and a
    guard that forbade it would fail on correct code.
    """
    offenders: list[str] = []
    for path in _iter_source_modules():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            # A subscript read (``state.get("<key>")``) with a literal key.
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value.startswith("_orchestrator__")
            ):
                offenders.append(f"{path.relative_to(_SRC)}:{node.lineno} -> {node.args[0].value}")

    assert not offenders, (
        "these modules read an orchestrator state key by hand instead of going "
        f"through the accessors: {offenders}"
    )


def test_no_module_outside_imports_a_private_orchestrator_symbol() -> None:
    """Private helpers stay private; the node layer uses the gate API."""
    offenders: list[str] = []
    for path in _iter_source_modules():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if not (node.module and _MODULE_STEM in node.module):
                continue
            for alias in node.names:
                if alias.name.startswith("_"):
                    offenders.append(f"{path.relative_to(_SRC)}:{node.lineno} -> {alias.name}")

    assert not offenders, (
        "these modules import a private name from orchestrator_state: "
        f"{offenders}. Expose a public accessor instead."
    )
