"""Tool export facade with lazy handlers and the runtime injection hook.

Handlers are imported on first use so registration never imports a tool package
while that package is initializing. The public names and callable identities stay
the same as the original eager facade.

## Why the tool list is derived, not written here

This mapping used to be a hand-maintained `name -> module` dict, one of **three**
places the tool list was declared: `registry.py`'s `_register(...)` calls, this
dict, and the `.pyi` stub beside it. Adding a tool meant editing all three, and
nothing failed if you forgot one — the tool simply was not importable by name, or
not registered, depending on which copy you missed.

The list now comes from the `ToolSpec` declarations themselves, which are the one
place a tool states its name and its module. `registry.register_all_tools` remains
the authority for *what is registered*; this is only the lazy import path for
`from film_pipeline.mcp.tools import <handler>`, which tests and the CLI use.
"""

from __future__ import annotations

import ast
from functools import lru_cache as _lru_cache
from importlib import import_module
from pathlib import Path as _Path
from typing import Any

from film_pipeline.studio.runtime import get_runtime as get_runtime

_TOOLS_DIR = _Path(__file__).resolve().parent

_NON_TOOL_EXPORTS: dict[str, str] = {
    "register_all_tools": "film_pipeline.mcp.registry",
}


@_lru_cache(maxsize=1)
def _tool_modules() -> dict[str, str]:
    """Map each declared tool to the module whose `ToolSpec` declares it.

    Parsed rather than imported: importing every tool module here would defeat the
    laziness this facade exists to provide, and would run at package-init time,
    which is the cycle this file is careful to avoid.
    """
    mapping: dict[str, str] = {}
    package_root = _TOOLS_DIR.parent.parent
    for path in sorted(_TOOLS_DIR.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - a syntax error fails elsewhere first
            continue
        relative = path.relative_to(package_root).with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts.pop()
        module = "film_pipeline." + ".".join(parts)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            if node.func.id != "ToolSpec":
                continue
            name = next(
                (
                    kw.value.value
                    for kw in node.keywords
                    if kw.arg == "name" and isinstance(kw.value, ast.Constant)
                ),
                None,
            )
            if isinstance(name, str):
                mapping[name] = module
    mapping.update(_NON_TOOL_EXPORTS)
    return mapping


def __getattr__(name: str) -> Any:
    module_name = _tool_modules().get(name)
    if module_name is None:
        raise AttributeError(name)
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_tool_modules()))


_TOOL_MODULES = _tool_modules()

__all__ = sorted((*_TOOL_MODULES, "get_runtime"))
