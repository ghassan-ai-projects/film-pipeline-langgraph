"""Schema package direction guards."""

from __future__ import annotations

import ast
from pathlib import Path


def _import_targets(node: ast.AST, package_parts: tuple[str, ...]) -> list[str]:
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


def _imports_registry_subpackage(node: ast.AST, package_parts: tuple[str, ...]) -> bool:
    registry_package = "film_pipeline.schemas.registries"
    return any(
        target == registry_package or target.startswith(f"{registry_package}.")
        for target in _import_targets(node, package_parts)
    )


def test_import_target_resolver_catches_registry_import_forms() -> None:
    package_parts = ("film_pipeline", "schemas")
    statements = (
        "import film_pipeline.schemas.registries.provider_registry as provider_registry",
        "from film_pipeline.schemas import registries as registry_package",
        "from film_pipeline.schemas.registries import ProviderRegistry",
        "from . import registries as registry_package",
        "from .registries import ProviderRegistry",
    )

    for statement in statements:
        node = ast.parse(statement).body[0]
        assert _imports_registry_subpackage(node, package_parts)


def test_schema_root_modules_do_not_import_registry_subpackage() -> None:
    src_root = Path(__file__).resolve().parents[3] / "src"
    schemas_root = src_root / "film_pipeline/schemas"
    violations: list[str] = []

    for source_path in sorted(schemas_root.glob("*.py")):
        package_parts = source_path.relative_to(src_root).parts[:-1]
        tree = ast.parse(source_path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and _imports_registry_subpackage(
                node, package_parts
            ):
                violations.append(f"{source_path}:{node.lineno}")

    assert violations == []
