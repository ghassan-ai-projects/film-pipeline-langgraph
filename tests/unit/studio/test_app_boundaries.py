"""Import-direction checks for the app composition package."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from tests.unit._import_guard import import_targets

_APP_DIR = Path(__file__).resolve().parents[3] / "src" / "film_pipeline" / "studio"
_FORBIDDEN_IMPORT = "film_pipeline.mcp"


def _import_targets(tree: ast.Module, current_package: str) -> set[str]:
    """Resolve the module targets named by absolute and relative imports.

    Delegates to the shared resolver in `tests.unit._import_guard`, which the
    `providers` and `schemas` boundary guards already use. This file carried its
    own copy of the same algorithm — including `importlib.util.resolve_name` for
    the relative case — and two resolvers behind three guards means a divergence
    could unguard one of them without any test noticing. The two agreed on every
    form when compared, so this is a consolidation, not a repair.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            found.update(import_targets(node, tuple(current_package.split("."))))
    return found


def _source_module(path: Path) -> tuple[str, str]:
    """Return the dotted module path and package for an app source file."""
    relative = path.relative_to(_APP_DIR.parent.parent)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
        module = ".".join(parts)
        return module, module
    module = ".".join(parts)
    return module, module.rpartition(".")[0]


def _forbidden_targets(targets: set[str]) -> list[str]:
    return sorted(
        target
        for target in targets
        if target == _FORBIDDEN_IMPORT or target.startswith(f"{_FORBIDDEN_IMPORT}.")
    )


def test_app_package_does_not_import_mcp() -> None:
    """Keep the application layer independent of its MCP operator surface."""
    offenders: list[str] = []
    for path in sorted(_APP_DIR.rglob("*.py")):
        module, package = _source_module(path)
        tree = ast.parse(path.read_text())
        for target in _forbidden_targets(_import_targets(tree, package)):
            offenders.append(f"{module} imports {target}")
    assert not offenders, "forbidden app imports:\n" + "\n".join(offenders)


@pytest.mark.parametrize(
    ("source", "current_package", "expected_forbidden"),
    [
        (
            "import film_pipeline.mcp.contract as contract",
            "film_pipeline.studio",
            {"film_pipeline.mcp.contract"},
        ),
        (
            "from film_pipeline.mcp import contract",
            "film_pipeline.studio",
            {"film_pipeline.mcp", "film_pipeline.mcp.contract"},
        ),
        (
            "from film_pipeline import mcp as module",
            "film_pipeline.studio",
            {"film_pipeline.mcp"},
        ),
        ("from .. import mcp", "film_pipeline.studio", {"film_pipeline.mcp"}),
        (
            "from .. import mcp",
            "film_pipeline.operations",
            {"film_pipeline.mcp"},
        ),
    ],
)
def test_app_boundary_resolves_absolute_relative_and_reexport_imports(
    source: str, current_package: str, expected_forbidden: set[str]
) -> None:
    """The guard resolves imported module targets, including aliases."""
    tree = ast.parse(source)
    targets = _import_targets(tree, current_package)
    assert set(_forbidden_targets(targets)) == expected_forbidden


def test_nested_app_scan_resolves_relative_import_to_mcp() -> None:
    """The filesystem-derived package path feeds nested relative resolution.

    The nested case now lives under `studio` itself: the operator surface moved
    to `operations`, so `app/services` is only a compatibility shim.
    """
    path = _APP_DIR / "bootstrap.py"
    _module, package = _source_module(path)
    tree = ast.parse("from .. import mcp")
    assert package == "film_pipeline.studio"
    assert _forbidden_targets(_import_targets(tree, package)) == ["film_pipeline.mcp"]
