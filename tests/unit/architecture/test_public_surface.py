"""Cross-package consumers must use a package's declared public surface.

## What this guards, and what it deliberately does not

`06-independent-review-and-decision.md` section 4 asks for "a single owner for a
concrete rule" and proof "at the consumer boundary". This is the interface half of
that: a package declares its surface in ``__all__``, and a consumer in another
package must not reach through the package root for a name the owner never
declared.

It does **not** enforce `03-target-architecture.md`'s "Allowed outbound" layer
law. That document is a superseded proposal (its own header says so) and `06`
decided the layout is "an ownership map, not a prohibition on ordinary package
imports". Enforcing that law was tried in an earlier round and reverted.

**Scope, stated honestly — three things this cannot see:**

1. **Surface shrinkage.** Removing a name from ``__all__`` while a consumer still
   imports it *from a submodule path* produces no finding. This detects bypass,
   not incompleteness.
2. **Submodule-path imports.** ``from film_pipeline.storage.store import X`` is
   out of scope here; cross-package *private* module imports are covered by
   ``test_boundary_law.py``.
3. **Re-export wrappers added purely to satisfy it.** Which is why AGENTS.md
   bans that: the fix is to declare the name or route the consumer, not to add a
   pass-through.

Packages with **no** ``__all__`` are skipped rather than failed. That is
deliberate for ``orchestration``: its root binds nothing, importing it loads no
submodules and no ``langgraph`` (verified), and a root ``__all__`` naming its
nine submodules would be a facade over the graph engine that risks making a
deliberately lazy import eager.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src" / "film_pipeline"

# Cross-package package-root imports of a name the owner does not declare,
# frozen 2026-09-26. Lower a count when you remove one; delete the row at zero.
#
# Empty on purpose: the tree currently has none. The one apparent case — three
# modules reaching `orchestration.orchestrator_state` through the package root —
# is NOT a finding here, because `orchestration/__init__.py` declares no `__all__`
# and packages without one are skipped by design (see the module docstring on why
# that root must stay bare). That submodule declares its own 39-name surface,
# guarded by `test_orchestrator_state_surface.py`. Recording it here would mean
# freezing something this sweep never measures.
KNOWN_UNDECLARED_ROOT_IMPORTS: dict[str, int] = {}


def _declared_surface() -> dict[str, set[str] | None]:
    """Map package name -> its ``__all__``, or None when it declares none."""
    surfaces: dict[str, set[str] | None] = {}
    for package_dir in sorted(p for p in _SRC.iterdir() if p.is_dir()):
        init = package_dir / "__init__.py"
        if not init.exists():
            continue
        declared: set[str] | None = None
        for node in ast.parse(init.read_text()).body:
            if not isinstance(node, ast.Assign):
                continue
            if not any(getattr(target, "id", None) == "__all__" for target in node.targets):
                continue
            value = node.value
            if not isinstance(value, ast.List):
                continue
            declared = {
                str(element.value)
                for element in value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            }
        surfaces[package_dir.name] = declared
    return surfaces


def _root_imports_by_consumer() -> dict[str, list[tuple[str, int]]]:
    """Cross-package ``from film_pipeline.<pkg> import <name>`` sites."""
    surfaces = _declared_surface()
    findings: dict[str, list[tuple[str, int]]] = {}

    for path in _SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        parts = path.relative_to(_SRC).parts
        source = parts[0] if len(parts) > 1 else None
        if source is None:
            continue
        relative = str(path.relative_to(_SRC))

        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            segments = node.module.split(".")
            if len(segments) != 2 or segments[0] != "film_pipeline":
                continue
            target = segments[1]
            if target == source:
                continue
            declared = surfaces.get(target)
            if declared is None:
                continue
            for alias in node.names:
                if alias.name not in declared:
                    findings.setdefault(relative, []).append((alias.name, node.lineno))
    return findings


def test_no_new_undeclared_root_import() -> None:
    """A consumer must not import an undeclared name from another package's root."""
    actual = _root_imports_by_consumer()
    new = {
        file: names
        for file, names in actual.items()
        if file not in KNOWN_UNDECLARED_ROOT_IMPORTS
        or len(names) > KNOWN_UNDECLARED_ROOT_IMPORTS[file]
    }

    assert not new, (
        "these import an undeclared name from another package's root: "
        f"{ {f: [n for n, _ in v] for f, v in new.items()} }. Either declare the "
        "name in the owner's __all__, or route the consumer through a declared "
        "one. Do not add a re-export wrapper purely to satisfy this."
    )


def test_recorded_undeclared_root_imports_are_not_stale() -> None:
    """A frozen count left too high would hide a regression."""
    actual = _root_imports_by_consumer()
    stale = {
        file: (recorded, len(actual.get(file, [])))
        for file, recorded in sorted(KNOWN_UNDECLARED_ROOT_IMPORTS.items())
        if len(actual.get(file, [])) < recorded
    }
    assert not stale, f"undeclared root imports improved (recorded -> actual): {stale}. Tighten."


@pytest.mark.parametrize(
    "package", sorted(p for p, names in _declared_surface().items() if names is not None)
)
def test_declared_surface_names_resolve(package: str) -> None:
    """Every name in a package's ``__all__`` must actually exist on the package."""
    import importlib

    module = importlib.import_module(f"film_pipeline.{package}")
    missing = sorted(name for name in module.__all__ if not hasattr(module, name))

    assert not missing, (
        f"{package}.__all__ names {missing}, which the package does not define. "
        "A declared surface that does not resolve is worse than none."
    )


def test_the_guard_has_something_to_check() -> None:
    """Guard the guard: an all-skipped sweep would silently prove nothing."""
    declared = [p for p, names in _declared_surface().items() if names is not None]
    assert len(declared) >= 15, (
        f"only {len(declared)} packages declare __all__; the sweep is checking almost nothing"
    )
