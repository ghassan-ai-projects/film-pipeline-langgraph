"""Provider package direction guards."""

from __future__ import annotations

import ast
from pathlib import Path

from tests.unit._import_guard import import_targets


def _is_adapter_subpackage(module: str) -> bool:
    adapter_package = "film_pipeline.providers.adapters"
    return module == adapter_package or module.startswith(f"{adapter_package}.")


def test_import_target_resolver_catches_adapter_import_forms() -> None:
    package_parts = ("film_pipeline", "providers")
    imports = (
        "import film_pipeline.providers.adapters.imagen4_gemini",
        "from film_pipeline.providers import adapters",
        "from .adapters import Imagen4GeminiProvider",
    )

    for statement in imports:
        node = ast.parse(statement).body[0]
        assert any(_is_adapter_subpackage(module) for module in import_targets(node, package_parts))


def test_provider_root_does_not_import_adapter_subpackage() -> None:
    src_root = Path(__file__).resolve().parents[3] / "src"
    providers_root = src_root / "film_pipeline/providers"
    violations: list[str] = []

    for source_path in sorted(providers_root.glob("*.py")):
        tree = ast.parse(source_path.read_text())
        package_parts = source_path.relative_to(src_root).parts[:-1]
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for imported in import_targets(node, package_parts):
                if _is_adapter_subpackage(imported):
                    violations.append(f"{source_path}:{node.lineno}: {imported}")

    assert violations == []
