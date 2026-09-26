"""Resolve a package's declared and reachable surface at runtime, not from AST.

## Why runtime resolution, and not an AST literal parser

Two things break naive AST parsing of `__all__`:

1. **Computed `__all__`.** `mcp/tools/__init__.py` declares
   `__all__ = sorted((*_TOOL_MODULES, "get_runtime"))` — an `ast.Call`, not an
   `ast.List`. `test_public_surface.py`'s original parser only accepted a literal
   list, so it read that package's surface as `None` and *silently skipped* it,
   hiding **77** declared names. A silent skip in a guard is worse than no guard:
   it reports clean while measuring nothing.
2. **PEP 562 lazy re-exports.** `mcp/__init__.py` and `operations/__init__.py`
   define a module-level `__getattr__` that imports on attribute access, so names
   like `MCPServer` are absent from `vars(module)` yet resolve perfectly. A
   checker using `vars()` would call them missing and report a false bug.

Both are resolved by importing the package and reading `hasattr` / `__all__` from
the live object. This module is the one place that logic lives; the guards import
it rather than each re-deriving it.

## Cost, stated plainly

Importing 20 packages is slower than parsing 20 files, and it executes package
import side effects. That is acceptable here: the packages are already imported by
the rest of the suite, and correctness beats speed for a guard that must not
silently skip. It is also why this is a helper module and not duplicated inline.
"""

from __future__ import annotations

import importlib
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FILM_PIPELINE = _REPO_ROOT / "src" / "film_pipeline"


@lru_cache(maxsize=1)
def packages() -> tuple[str, ...]:
    """Every package under ``film_pipeline``, sorted."""
    return tuple(
        sorted(p.name for p in _FILM_PIPELINE.iterdir() if p.is_dir() and p.name != "__pycache__")
    )


@cache
def declared_surface(package: str) -> frozenset[str] | None:
    """The package's ``__all__`` as a frozenset, or None when it declares none.

    Read from the imported module, so a computed ``__all__`` resolves correctly
    and a PEP 562 ``__getattr__`` does not confuse the result.
    """
    module = importlib.import_module(f"film_pipeline.{package}")
    names = getattr(module, "__all__", None)
    if names is None:
        return None
    return frozenset(str(name) for name in names)


@cache
def reachable_public_names(package: str) -> frozenset[str]:
    """Public *symbols* reachable as attributes of the package root.

    Submodules are excluded: importing `film_pipeline.schemas.artifact` binds
    `artifact` on the package, but a submodule is a path, not an exported symbol.
    Uses ``hasattr`` so PEP 562 re-exports count.
    """
    import types

    module = importlib.import_module(f"film_pipeline.{package}")
    found: set[str] = set()
    for name in dir(module):
        if name.startswith("_"):
            continue
        try:
            value: Any = getattr(module, name)
        except AttributeError:  # pragma: no cover - a broken __getattr__
            continue
        if isinstance(value, types.ModuleType):
            continue
        found.add(name)
    return frozenset(found)


@cache
def public_module_names(package: str) -> tuple[str, ...]:
    """Dotted names of the package's public (non-underscore) modules.

    A package with no ``__all__`` still has a surface: these. ``__init__`` is
    excluded because it *is* the root, not a module under it.
    """
    root = _FILM_PIPELINE / package
    names: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root)
        if relative.name == "__init__.py":
            continue
        parts = relative.parts
        if any(part.startswith("_") for part in parts[:-1]):
            continue
        module = parts[-1][:-3]
        if module.startswith("_"):
            continue
        names.append(".".join((*parts[:-1], module)))
    return tuple(names)
