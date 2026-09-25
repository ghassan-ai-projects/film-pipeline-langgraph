"""Shared helpers for the source-level import-direction guards.

Several boundary guards parse a package's source and ask "what modules does
this file import?". That resolution has to understand absolute imports,
relative imports, and ``from X import Y`` / ``from X import Y as Z`` re-export
forms, or a guard silently stops guarding. It is one rule, so it lives here.
"""

from __future__ import annotations

import ast


def import_targets(node: ast.AST, package_parts: tuple[str, ...]) -> list[str]:
    """Resolve the module targets named by one import statement.

    ``package_parts`` is the dotted parent package the statement appears in,
    used to resolve relative imports. Returns the base module plus each named
    submodule, so ``from a.b import c`` yields ``["a.b", "a.b.c"]``. Star
    imports contribute the base module only.
    """
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if not isinstance(node, ast.ImportFrom):
        return []

    if node.level:
        parent_size = len(package_parts) - node.level + 1
        base = package_parts[: max(parent_size, 0)]
    else:
        base = ()
    module_parts = tuple(node.module.split(".")) if node.module else ()
    imported_parts = (*base, *module_parts)
    targets = [".".join(imported_parts)] if imported_parts else []
    targets.extend(
        ".".join((*imported_parts, *alias.name.split(".")))
        for alias in node.names
        if alias.name != "*"
    )
    return targets


def imported_modules(tree: ast.Module, package_parts: tuple[str, ...]) -> set[str]:
    """Every module target imported anywhere in ``tree``."""
    found: set[str] = set()
    for node in ast.walk(tree):
        found.update(import_targets(node, package_parts))
    return found


def package_parts_for(path: object, relative_to: object) -> tuple[str, ...]:
    """Derive the dotted package parts of a source file from its location."""
    from pathlib import Path as _Path

    source = _Path(str(path))
    root = _Path(str(relative_to))
    parts = list(source.relative_to(root).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return tuple(parts)
