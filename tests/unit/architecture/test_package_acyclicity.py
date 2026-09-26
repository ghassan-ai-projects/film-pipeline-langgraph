"""The package dependency graph must stay acyclic.

## Why this guard exists, and why only this guard

`06-independent-review-and-decision.md` section 4 decided the package layout is
"an ownership map, **not a prohibition on ordinary package imports**. Tighten a
dependency only when it removes a proven cycle or unsafe reach-in." This file
enforces exactly the clause that decision kept: **cycles**. It does not enforce
`03-target-architecture.md`'s "Allowed outbound" layer law, which is a superseded
proposal — an earlier round graded every import against it, froze 73 edges as
debt, and was re-scoped for enforcing a rejected design. Do not add a layer
whitelist here.

A cycle among packages is a real defect in a way that a "wrong direction" import
is not: it means two packages cannot be understood, tested, or extracted
independently, and it makes the import graph's evaluation order depend on which
module happens to be imported first. The measured state when this guard was added
(2026-09-26) was exactly one such cycle — `orchestration <-> schemas` — caused by
`schemas/runtime_state.py` importing `orchestration.state_schema` to check
persisted graph-state keys. Its own docstring conceded the inversion. The check
moved to the module that owns `StudioGraphState`, and the graph became acyclic.

## What this cannot see

Import edges are read statically from `ast`, so a cycle formed through a dynamic
import (`importlib.import_module`, `__import__`) is invisible here. The one cycle
this guard was written against was a *function-level* lazy import, which this does
detect — laziness does not hide an edge from `ast`. Also note that a cycle
confined within a single package is out of scope: this compares package-to-package
edges only, which is the granularity `06`'s ownership map is written at.
"""

from __future__ import annotations

import ast
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src" / "film_pipeline"


def _packages() -> list[str]:
    """Every package directory under ``film_pipeline``."""
    return sorted(p.name for p in _SRC.iterdir() if p.is_dir() and p.name != "__pycache__")


def _cross_package_edges() -> dict[tuple[str, str], set[str]]:
    """Map ``(importer_package, imported_package)`` -> files creating that edge.

    The file set is carried so a failure names the files to change rather than
    only the pair, which is what made the original cycle take a graph rebuild to
    localise.
    """
    packages = set(_packages())
    edges: dict[tuple[str, str], set[str]] = {}
    for path in sorted(_SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        importer = path.relative_to(_SRC).parts[0]
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - a parse error is a different failure
            continue
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            for module in modules:
                if not module.startswith("film_pipeline."):
                    continue
                parts = module.split(".")
                if len(parts) < 2 or parts[1] not in packages or parts[1] == importer:
                    continue
                edges.setdefault((importer, parts[1]), set()).add(
                    str(path.relative_to(_SRC.parent.parent))
                )
    return edges


def _mutual_pairs(edges: dict[tuple[str, str], set[str]]) -> list[tuple[str, str]]:
    """Package pairs that import each other, each pair named once."""
    return sorted((a, b) for a, b in edges if (b, a) in edges and a < b)


def test_the_guard_has_something_to_check() -> None:
    """A guard that silently measures nothing is worse than no guard.

    If the package layout is ever reorganised, this fails loudly instead of
    reporting a clean graph derived from an empty edge set.
    """
    edges = _cross_package_edges()
    assert len(_packages()) > 10, "package discovery found too few packages"
    assert len(edges) > 20, f"expected a populated import graph, found {len(edges)} edges"


def test_package_graph_is_acyclic() -> None:
    """No two packages may import each other.

    A mutual pair is the layering defect this guard exists to prevent. The
    failure names the *smaller* side first: in a cycle, one direction is usually a
    settled, many-file dependency and the other is a single accidental back-edge,
    so the short list is the actionable one. The original cycle here was 15 files
    of `orchestration -> schemas` against one file of `schemas -> orchestration`.
    """
    edges = _cross_package_edges()
    mutual = _mutual_pairs(edges)
    if mutual:
        blocks: list[str] = []
        for a, b in mutual:
            forward, backward = edges[(a, b)], edges[(b, a)]
            if len(forward) <= len(backward):
                first, second = (a, b, forward), (b, a, backward)
            else:
                first, second = (b, a, backward), (a, b, forward)
            (fa, fb, ffiles), (sa, sb, sfiles) = first, second
            blocks.append(
                f"  cycle {a} <-> {b}\n"
                f"    {fa} -> {fb} ({len(ffiles)} file(s)) — look here first:\n"
                + "".join(f"      {f}\n" for f in sorted(ffiles))
                + f"    {sa} -> {sb} ({len(sfiles)} file(s))"
            )
        raise AssertionError(
            "Mutual package dependency (a cycle):\n\n"
            + "\n".join(blocks)
            + "\nFix by moving the shared concern to the package that owns it. "
            "A re-export, a `TYPE_CHECKING` guard, or a function-level lazy import "
            "does NOT remove the edge — this guard reads `ast`, so all three are "
            "still detected. The original fix moved the check to the module that "
            "owned the contract it enforced."
        )


def test_no_package_imports_itself_via_the_root() -> None:
    """A package importing through its own name is a sign of a moved module."""
    edges = _cross_package_edges()
    self_edges = sorted(a for a, b in edges if a == b)
    assert self_edges == [], f"packages importing themselves: {self_edges}"
