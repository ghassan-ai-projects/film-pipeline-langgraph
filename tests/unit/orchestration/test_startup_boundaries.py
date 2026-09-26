"""Boundary guards for the graph package [B-F4].

Locks in the repair that removed fixture data from the production default
startup path:

1. No module under ``graph/`` may import ``film_pipeline.devharness`` (test
   fixtures) or ``film_pipeline.studio`` (composition root) — in any import
   statement, module-level or function-body.
2. Constructing mock-mode services pulls in no ``film_pipeline.devharness``
   modules; canned responses are injected from the composition root.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

_GRAPH_DIR = Path(__file__).resolve().parents[3] / "src" / "film_pipeline" / "graph"

_FORBIDDEN_ROOTS = ("film_pipeline.devharness", "film_pipeline.studio")


def _imported_modules(tree: ast.Module, current_package: str) -> set[str]:
    """Resolve module paths named by absolute and relative import statements."""
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue

        if node.level:
            package_parts = current_package.split(".")
            base_parts = package_parts[: len(package_parts) - (node.level - 1)]
            if node.module:
                base_parts.extend(node.module.split("."))
            base_module = ".".join(base_parts)
        else:
            base_module = node.module or ""

        if base_module:
            imported.add(base_module)
        for alias in node.names:
            if alias.name != "*" and base_module:
                imported.add(f"{base_module}.{alias.name}")
    return imported


def _module_path(path: Path) -> tuple[str, str]:
    """Return a Python module path and its package for a graph source file."""
    relative = path.relative_to(_GRAPH_DIR.parent.parent)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
        module = ".".join(parts)
        return module, module
    module = ".".join(parts)
    return module, module.rpartition(".")[0]


def _imports_forbidden(imported: set[str], roots: tuple[str, ...]) -> list[str]:
    return sorted(
        module
        for module in imported
        if any(module == root or module.startswith(f"{root}.") for root in roots)
    )


def test_graph_package_never_imports_testing_or_app() -> None:
    """AST sweep over every graph module, including lazy function-body imports."""
    offenders: list[str] = []
    for path in sorted(_GRAPH_DIR.rglob("*.py")):
        module, package = _module_path(path)
        tree = ast.parse(path.read_text())
        for imported in _imports_forbidden(_imported_modules(tree, package), _FORBIDDEN_ROOTS):
            offenders.append(f"{module} imports {imported}")
    assert not offenders, "forbidden graph imports:\n" + "\n".join(offenders)


def test_graph_composition_imports_remain_one_way() -> None:
    """Keep graph composition and its validators/subgraphs from reaching into nodes."""
    offenders: list[str] = []
    for path in sorted(_GRAPH_DIR.rglob("*.py")):
        relative = path.relative_to(_GRAPH_DIR)
        module, package = _module_path(path)
        roots: tuple[str, ...] = ()
        if len(relative.parts) == 1:
            roots = ("film_pipeline.orchestration.nodes", "film_pipeline.orchestration.subgraphs")
        elif relative.parts[0] == "subgraphs":
            roots = ("film_pipeline.orchestration.nodes",)
        if not roots:
            continue
        tree = ast.parse(path.read_text())
        for imported in _imports_forbidden(_imported_modules(tree, package), roots):
            offenders.append(f"{module} imports {imported}")
    assert not offenders, "forbidden graph ownership imports:\n" + "\n".join(offenders)


@pytest.mark.parametrize(
    ("source", "package", "expected"),
    [
        (
            "from film_pipeline.orchestration.nodes._shared import helper",
            "film_pipeline.orchestration",
            {
                "film_pipeline.orchestration.nodes._shared",
                "film_pipeline.orchestration.nodes._shared.helper",
            },
        ),
        (
            "from film_pipeline.orchestration import nodes as node_package",
            "film_pipeline.studio",
            {"film_pipeline.orchestration", "film_pipeline.orchestration.nodes"},
        ),
        (
            "from . import nodes as node_package",
            "film_pipeline.orchestration",
            {"film_pipeline.orchestration", "film_pipeline.orchestration.nodes"},
        ),
        (
            "from .. import nodes as node_package",
            "film_pipeline.orchestration.subgraphs",
            {"film_pipeline.orchestration", "film_pipeline.orchestration.nodes"},
        ),
        (
            "from .nodes import helper",
            "film_pipeline.orchestration.subgraphs",
            {
                "film_pipeline.orchestration.subgraphs.nodes",
                "film_pipeline.orchestration.subgraphs.nodes.helper",
            },
        ),
    ],
)
def test_import_resolver_covers_absolute_relative_and_reexport_forms(
    source: str, package: str, expected: set[str]
) -> None:
    """The ownership guard resolves module paths, not only literal AST module fields."""
    tree = ast.parse(source)
    assert _imported_modules(tree, package) == expected


def test_mock_service_construction_imports_no_testing_modules() -> None:
    """Run in a fresh interpreter so unrelated tests cannot preload fixtures."""
    code = (
        "import sys\n"
        "import tempfile\n"
        "from pathlib import Path\n"
        "from film_pipeline.studio.mock_responses import default_mock_responses\n"
        "from film_pipeline.orchestration.services import GraphServices\n"
        "root = Path(tempfile.mkdtemp())\n"
        "GraphServices.for_mock_runtime(\n"
        "    artifacts_root=str(root), mock_responses=default_mock_responses()\n"
        ")\n"
        "loaded = sorted(m for m in sys.modules if m.startswith('film_pipeline.devharness'))\n"
        "assert not loaded, f'devharness modules leaked into mock startup: {loaded}'\n"
        "print('CLEAN')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr
    assert "CLEAN" in result.stdout


def test_default_runtime_mode_builds_services_from_composition_root(tmp_path: Any) -> None:
    """The production default wiring passes injected canned responses."""
    from film_pipeline.studio.runtime import StudioRuntime

    rt = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
    assert rt.services is not None
    assert rt.services.prompt_runner.mock_responses, (
        "mock mode must receive injected canned responses"
    )
