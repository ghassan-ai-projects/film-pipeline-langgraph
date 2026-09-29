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

## What this detects, and what it does not

The check is a **full strong-connectivity analysis** over the directed package
graph (`_cycles`), not a mutual-pair scan. That distinction is the whole point:
`docs/modularity-improvements/10-boundary-audit.md` B1 found the earlier version
called `_mutual_pairs`, which reports `A -> B` only when `B -> A` also exists, so
a three-package cycle `A -> B -> C -> A` passed. A synthetic three-node probe
returned `[]`, and the real graph contains exactly that shape today — see
`test_package_graph_is_acyclic`. `test_the_cycle_check_detects_injected_cycles`
is the acceptance proof: it injects two- and three-node cycles into a synthetic
edge map and requires them to be reported.

The orchestration cycle is **one SCC, not one defect per pair**. Naming a single
cycle is enough to act on (the failure lists the modules and the edges between
them), and enumerating every elementary cycle in an SCC is exponential in the
worst case for no extra diagnostic value. `_cycles` therefore reports one
cycle-through-each-SCC member, and the failure text says so.

Import edges are read statically from `ast`, so a cycle formed through a dynamic
import (`importlib.import_module`, `__import__`) is invisible here. Function-level
imports *are* read: laziness does not hide an edge from `ast`, which is why the
`nodes -> subgraphs` back-edge below is found. A dependency that exists only at
*type-check* time is deliberately not read here — `TYPE_CHECKING` imports are
erased at runtime and cannot affect evaluation order. `test_boundary_law.py` and
`test_lazy_imports.py` cover the other consequences of that choice.

A cycle confined within a single package is out of scope: this compares
package-to-package edges only, which is the granularity `06`'s ownership map is
written at.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable, Mapping
from itertools import pairwise
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src" / "film_pipeline"

#: Packages whose own root module participates in the graph. The orchestration
#: root is the only package with a cycle today, and that cycle is *about* the
#: root: `orchestration/execution.py` imports `orchestration.nodes`, which
#: reaches `orchestration.subgraphs`, which imports back into `nodes`. Reading
#: "the root package" as a node is what makes that visible; a root file is not
#: part of any subpackage.
_ROOT_MODULE_OF_SELF: str = "."

#: Measured 2026-09-29 by `_root_self_imports()`. Lower it when a package drops
#: a re-export; raising it needs the reason in the commit message.
_SELF_IMPORT_CEILING: int = 556


def _packages() -> list[str]:
    """Every package directory under ``film_pipeline``."""
    return sorted(p.name for p in _SRC.iterdir() if p.is_dir() and p.name != "__pycache__")


def _owning_nodes(path_parts: tuple[str, ...], packages: set[str]) -> set[str]:
    """Every package node a path belongs to, given its parts *after* the root.

    ``("orchestration", "nodes", "qc.py")`` belongs to ``orchestration`` and to
    ``orchestration.nodes``: every enclosing subpackage, up to and including the
    first part. Python runs each package's ``__init__`` on the way in, so an
    import of a deeply nested module creates an edge to every one of those nodes,
    not only the deepest. Omitting the intermediate edges is what let the cycle
    this guard now finds stay invisible for a whole program round.

    A directory part may or may not be a package and the `packages` check decides;
    a `.py` leaf names no package, and the same check excludes it.
    """
    nodes: set[str] = set()
    for index in range(1, len(path_parts) + 1):
        node = ".".join(path_parts[:index])
        if node in packages:
            nodes.add(node)
    return nodes


def _module_nodes(module: str, packages: set[str]) -> set[str]:
    """Package nodes an absolute ``film_pipeline`` import path resolves to."""
    parts = module.split(".")[1:]
    return _owning_nodes(tuple(parts), packages)


def _string_constants(node: ast.AST) -> list[str]:
    """Named constants inside an annotation, resolved to their string value.

    Only module-level ``NAME = "literal"`` constants are honoured, and only
    simple names: that covers this repo's spelling (`from __future__ import
    annotations` means annotations *are* strings at runtime) without pretending to
    evaluate expressions.
    """
    values: list[str] = []
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        values.append(node.value)
    elif isinstance(node, ast.Name):
        resolved = _MODULE_CONSTANTS.get(node.id)
        if resolved is not None:
            values.append(resolved)
    return values


def _is_type_checking_test(node: ast.AST) -> bool:
    """Whether an ``if`` test is exactly the ``TYPE_CHECKING`` guard."""
    return isinstance(node, ast.Name) and node.id == "TYPE_CHECKING"


class _EdgeCollector(ast.NodeVisitor):
    """Collect the package edges one source file creates.

    A visitor rather than a `walk` because the one distinction that matters is
    *where* an import sits: inside ``if TYPE_CHECKING:`` the edge does not exist
    at runtime.
    """

    def __init__(self, importer_nodes: set[str], packages: set[str]) -> None:
        self._importer_nodes = importer_nodes
        self._packages = packages
        self.edges: set[tuple[str, str]] = set()
        self._type_checking_depth = 0

    # -- scope tracking ---------------------------------------------------

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_test(node.test):
            self._type_checking_depth += 1
            try:
                for child in node.body:
                    self.visit(child)
            finally:
                self._type_checking_depth -= 1
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)

    # -- edges ------------------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:
        if self._type_checking_depth:
            return
        for alias in node.names:
            self._add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self._type_checking_depth or node.level:
            return
        if node.module:
            self._add(node.module)
            return
        # `from film_pipeline.orchestration import nodes` — the module is named in
        # the alias, not in `node.module`.
        for alias in node.names:
            self._add(f"film_pipeline.{alias.name}")

    def _add(self, module: str) -> None:
        if not module or not module.startswith("film_pipeline."):
            return
        for target in _module_nodes(module, self._packages):
            for source in self._importer_nodes:
                self.edges.add((source, target))


_MODULE_CONSTANTS: dict[str, str] = {}


def _collect_module_constants(tree: ast.Module) -> None:
    """Record ``NAME = "literal"`` constants so annotations can resolve them."""
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            _MODULE_CONSTANTS[target.id] = node.value.value


def _edges_in(
    tree: ast.Module, importer_nodes: set[str], packages: set[str]
) -> set[tuple[str, str]]:
    """Package edges one parsed module creates, honouring ``TYPE_CHECKING``."""
    collector = _EdgeCollector(importer_nodes, packages)
    collector.visit(tree)
    return collector.edges


def _cross_package_edges(
    sources: Mapping[str, ast.Module] | None = None,
) -> dict[tuple[str, str], set[str]]:
    """Map ``(importer_package, imported_package)`` -> files creating that edge.

    The file set is carried so a failure names the files to change rather than
    only the pair, which is what made the original cycle take a graph rebuild to
    localise.

    *sources* lets a test supply synthetic modules (keyed by a ``film_pipeline``
    relative path) instead of reading the tree, so the detector itself can be
    exercised on inputs the real tree does not contain.
    """
    packages = set(_packages())
    edges: dict[tuple[str, str], set[str]] = {}

    if sources is not None:
        for name, tree in sources.items():
            importer_nodes = _owning_nodes(tuple(Path(name).parts), packages)
            files = {f"src/film_pipeline/{name}"}
            for edge in _edges_in(tree, importer_nodes, packages):
                edges.setdefault(edge, set()).update(files)
        return edges

    for path in sorted(_SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(_SRC)
        importer_nodes = _owning_nodes(relative.parts, packages)
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - a parse error is a different failure
            continue
        _collect_module_constants(tree)
        files = {str(path.relative_to(_SRC.parent.parent))}
        for edge in _edges_in(tree, importer_nodes, packages):
            edges.setdefault(edge, set()).update(files)
    return edges


def _mutual_pairs(edges: Mapping[tuple[str, str], object]) -> list[tuple[str, str]]:
    """Package pairs that import each other, each pair named once."""
    return sorted((a, b) for a, b in edges if (b, a) in edges and a < b)


def _cycles(edges: Mapping[tuple[str, str], object]) -> list[list[str]]:
    """Every package cycle, as one closed path per member of each SCC.

    Strongly connected components are found with `graphlib.TopologicalSorter`,
    which is the standard library's own implementation of the same algorithm the
    import system uses. A component of one node is not a cycle; a component of
    ``n > 1`` nodes is, and every node in it lies on at least one cycle.

    Deterministic: packages are sorted before the search, and each reported path
    is closed (``a, b, c, a``) so a caller can read it as a loop.
    """
    adjacency: dict[str, set[str]] = {}
    for source, target in edges:
        # A self-edge is reported by `_self_edge_sources`, not as a cycle: it is
        # a package reaching its own surface, which is the normal shape.
        if source != target:
            adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set())
        adjacency.setdefault(source, set())

    components = list(_strongly_connected_components(adjacency))
    cycles: list[list[str]] = []
    for component in components:
        members = sorted(component)
        for member in members:
            path = _cycle_through(member, component, adjacency)
            if path:
                cycles.append(path)
    return cycles


def _strongly_connected_components(adjacency: Mapping[str, set[str]]) -> list[set[str]]:
    """Tarjan's algorithm over the package graph, iteratively.

    Iterative rather than recursive: the graph is small today, but a recursive
    walk of a 20-node graph with a deep chain is one refactor away from a
    `RecursionError` inside a guard, which would read as a broken guard rather
    than a cycle.
    """
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    components: list[set[str]] = []
    counter = 0

    for root in sorted(adjacency):
        if root in index:
            continue
        work: list[tuple[str, int]] = [(root, 0)]
        while work:
            node, child_index = work.pop()
            if child_index == 0:
                index[node] = low[node] = counter
                counter += 1
                stack.append(node)
                on_stack.add(node)

            neighbours = sorted(adjacency.get(node, ()))
            recursed = False
            for position in range(child_index, len(neighbours)):
                neighbour = neighbours[position]
                if neighbour not in index:
                    work.append((node, position + 1))
                    work.append((neighbour, 0))
                    recursed = True
                    break
                if neighbour in on_stack:
                    low[node] = min(low[node], index[neighbour])
            if recursed:
                continue

            if low[node] == index[node]:
                component: set[str] = set()
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.add(member)
                    if member == node:
                        break
                components.append(component)
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
    return components


def _cycle_through(start: str, component: set[str], adjacency: Mapping[str, set[str]]) -> list[str]:
    """A closed path from *start* back to itself inside one component.

    Breadth-first, so the named cycle is the shortest one through *start* — the
    most legible repair target. Returns ``[]`` when no such path exists, which
    cannot happen for a member of a genuine component and is why the caller
    treats an empty result as "nothing to report" rather than an error.
    """
    queue: list[list[str]] = [[start]]
    seen = {start}
    while queue:
        path = queue.pop(0)
        for neighbour in sorted(adjacency.get(path[-1], ())):
            if neighbour not in component:
                continue
            if neighbour == start:
                return [*path, start]
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append([*path, neighbour])
    return []


def _describe_cycle(path: Iterable[str], edges: Mapping[tuple[str, str], set[str]]) -> str:
    """One failure block: the loop, then the files creating each of its edges."""
    nodes = list(path)
    lines = [f"  cycle {' -> '.join(nodes)}"]
    for source, target in pairwise(nodes):
        files = sorted(edges.get((source, target), ()))
        lines.append(f"    {source} -> {target} ({len(files)} file(s)):")
        lines.extend(f"      {name}" for name in files)
    return "\n".join(lines)


def test_the_guard_has_something_to_check() -> None:
    """A guard that silently measures nothing is worse than no guard.

    If the package layout is ever reorganised, this fails loudly instead of
    reporting a clean graph derived from an empty edge set.
    """
    edges = _cross_package_edges()
    assert len(_packages()) > 10, "package discovery found too few packages"
    assert len(edges) > 20, f"expected a populated import graph, found {len(edges)} edges"


def test_the_cycle_check_detects_injected_cycles() -> None:
    """Acceptance proof for the detector, on inputs the real tree does not have.

    A green run over the current tree cannot show that the *detector* works — the
    earlier mutual-pair version was green too. Each case here is a graph the
    check must reject, including the three-node cycle it used to miss.
    """
    two_node = {("a", "b"): {"a.py"}, ("b", "a"): {"b.py"}}
    three_node = {("a", "b"): {"a.py"}, ("b", "c"): {"b.py"}, ("c", "a"): {"c.py"}}
    acyclic = {("a", "b"): {"a.py"}, ("b", "c"): {"b.py"}}
    self_loop = {("a", "a"): {"a.py"}}
    two_sccs = {
        **three_node,
        ("d", "e"): {"d.py"},
        ("e", "f"): {"e.py"},
        ("f", "d"): {"f.py"},
        ("a", "d"): {"a.py"},
    }

    assert _mutual_pairs(three_node) == [], "the old check could not see this case"
    assert _cycles(three_node), "a three-node cycle must be reported"
    assert {frozenset(cycle) for cycle in _cycles(three_node)} == {frozenset("abc")}
    assert _cycles(two_node), "a mutual pair is a cycle"
    assert _cycles(self_loop) == [], "a self-edge is reported by _self_edge_sources, not here"
    assert _cycles(acyclic) == [], "a chain is not a cycle"
    assert _cycles({}) == [], "an empty graph has no cycle"
    assert len({frozenset(cycle) for cycle in _cycles(two_sccs)}) == 2, "both components"

    cycles = _cycles(three_node)
    assert len(cycles) == 3, "one path per member of the component"
    assert all(cycle[0] == cycle[-1] for cycle in cycles), "reported paths are closed"
    assert all(set(cycle) <= set("abc") for cycle in cycles)
    assert _describe_cycle(cycles[0], three_node).count("->") >= 3


def test_package_graph_is_acyclic() -> None:
    """No package may (transitively) import itself.

    The failure names each cycle as a closed path, with the files creating every
    edge, smallest-edit-first: in a cycle one direction is usually a settled,
    many-file dependency and the other a single accidental back-edge. The
    original cycle here was 15 files of `orchestration -> schemas` against one
    file of `schemas -> orchestration`.

    A `test-function-level import does NOT remove an edge`: this reads `ast`, so
    hoisting an import out of a function, or hiding it behind `TYPE_CHECKING`
    (which erases it at runtime and therefore does break the edge), each have to
    be decided deliberately rather than by moving a line.
    """
    edges = _cross_package_edges()
    cycles = _cycles(edges)
    if cycles:
        blocks = "\n\n".join(_describe_cycle(cycle, edges) for cycle in cycles)
        raise AssertionError(
            f"{len(cycles)} package cycle(s) — fix by moving the shared concern to "
            "the package that owns it:\n\n"
            + blocks
            + "\n\nA re-export does NOT remove an edge. A function-level import "
            "does NOT either (`ast` sees it, and this guard reads function bodies). "
            "`TYPE_CHECKING` does, at the cost of a type-only dependency."
        )


def _self_edge_sources(sources: Mapping[str, ast.Module] | None = None) -> list[str]:
    """Files that reach their own package by its absolute ``film_pipeline`` name.

    This is the check the earlier version could not perform: it looked for
    self-edges in `_cross_package_edges()`' *output*, and that function filters
    self-edges out (`_owning_nodes` compares source with target), so the
    assertion had no way to fail. The measurement happens here, on the raw edges.

    `agents/__init__.py` reaching `agents.base` is exactly the shape this looks
    for. Whether it is *prohibited* is a separate question — this reports, so a
    decision about the package's own surface is made deliberately.
    """
    if sources is not None:
        packages = set(_packages())
        found: list[str] = []
        for name, tree in sources.items():
            importer = _owning_nodes(tuple(Path(name).parts), packages)
            for source, target in _edges_in(tree, importer, packages):
                if source == target:
                    found.append(f"{name}: imports {target} by full name")
        return sorted(found)

    found = []
    for path in sorted(_SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(_SRC)
        package = relative.parts[0]
        for node in ast.walk(ast.parse(path.read_text())):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module and not node.level:
                modules.append(node.module)
            elif isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            for module in modules:
                parts = module.split(".")
                if len(parts) >= 2 and parts[0] == "film_pipeline" and parts[1] == package:
                    found.append(f"{relative}: imports {module} by full name")
    return sorted(found)


def _root_self_imports(sources: Mapping[str, ast.Module] | None = None) -> list[str]:
    """Package root files importing a leaf of their own package by full name.

    The narrow reading of "imports itself via the root": `<package>/__init__.py`
    naming `<package>.<leaf>`. A leaf inside the package importing its own
    package root is the same shape seen from the other side and is not counted —
    every module does that.
    """
    found: list[str] = []
    for entry in _self_edge_sources(sources):
        path, _, module = entry.partition(": ")
        parts = Path(path).parts
        if len(parts) != 2 or parts[1] != "__init__.py":
            continue
        if module.count(".") >= 3:
            found.append(entry)
    return found


def test_the_self_edge_check_detects_an_injected_self_import() -> None:
    """Acceptance proof: a synthetic self-import must be reported.

    The real tree has 573 of these (mostly `<package>/__init__.py` re-exporting
    its own modules by full name), so proving the detector works needs an input
    the tree does not have: a module that reaches its *parent* package by name.
    """
    packages = set(_packages())
    injected = {
        "storage/probe.py": ast.parse("from film_pipeline.storage import _layout\n"),
    }
    found = _self_edge_sources(injected)
    assert found == ["storage/probe.py: imports storage by full name"], found
    assert _owning_nodes(("storage", "probe.py"), packages) == {"storage"}

    # A cross-package import is not a self-edge, and must not be counted as one.
    foreign = {"storage/probe.py": ast.parse("from film_pipeline.schemas import base\n")}
    assert _self_edge_sources(foreign) == []


def test_self_imports_are_measured_and_do_not_grow() -> None:
    """A package reaching itself by full name is measured, not assumed absent.

    The earlier version looked for self-edges in `_cross_package_edges()`' output,
    which filters them out, so it could never fail.

    Measured: every file inside a package necessarily imports its own package when
    it names an absolute path, so "self-import" as a raw count measures nothing
    useful. The shape worth guarding is narrower and is what the original test's
    name actually meant: a **package root file** (`<package>/__init__.py`)
    reaching a **leaf module** of the same package by full name. Measured 2026-09-29:
    **556** of those, essentially every `__init__.py` re-exporting its surface.

    The ceiling makes a new one deliberate. It is a count, which is a weak guard —
    the same criticism B5 makes of the surface ratchet — and that is stated rather
    than hidden: its job is to make the next author look, not to prove the shape.
    """
    found = _root_self_imports()
    assert found, "the detector found nothing at all — it is not measuring"
    assert len(found) <= _SELF_IMPORT_CEILING, (
        f"{len(found)} package-root self-import sites, ceiling {_SELF_IMPORT_CEILING}. "
        "A new one has to be justified: publish through the package's own name "
        "deliberately, or import the submodule directly."
    )
