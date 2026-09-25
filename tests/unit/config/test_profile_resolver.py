"""Tests for the neutral profile resolver used by MCP tools and OperatorService."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, cast

from film_pipeline.config.profile_resolver import (
    canonicalize_profile_stack,
    provider_specs,
    provider_specs_from_raw,
    resolve_project_config,
)


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


def _is_app_or_provider_import(module: str) -> bool:
    return any(
        module == forbidden or module.startswith(f"{forbidden}.")
        for forbidden in ("film_pipeline.studio", "film_pipeline.providers")
    )


def test_canonicalize_profile_stack_resolves_existing_profiles() -> None:
    stack = canonicalize_profile_stack(
        {
            "film_type_profile": "narrative",
            "quality_profile": "draft",
            "provider_profile": "mock-demo",
        }
    )
    assert stack["film_type_profile"] == "film-type.narrative"
    assert stack["quality_profile"] == "quality.draft"
    assert stack["provider_profile"] == "mock-demo"
    assert stack["review_profile"] == ""
    assert stack["auto_approve_profile"] == ""


def test_canonicalize_profile_stack_ignores_missing_keys() -> None:
    stack = canonicalize_profile_stack({})
    assert all(value == "" for value in stack.values())


def test_resolve_project_config_includes_base_and_profiles() -> None:
    stack = {
        "film_type_profile": "film-type.narrative",
        "quality_profile": "quality.draft",
        "provider_profile": "mock-demo",
        "review_profile": "",
        "auto_approve_profile": "",
    }
    resolved = resolve_project_config(stack)
    raw = cast(dict[str, object], resolved["raw"])
    assert isinstance(raw, dict)
    sources = cast(list[str], resolved["sources"])
    assert "base.studio" in sources
    assert "film-type.narrative" in sources
    assert "quality.draft" in sources
    assert isinstance(resolved["conflicts"], list)


def test_provider_specs_from_raw_extracts_video_and_image_providers() -> None:
    providers: dict[str, Any] = {
        "video": [{"provider_id": "seedance-openrouter", "models": ["seedance-2"]}],
        "image": [{"provider_id": "gemini-imagen-4", "models": ["imagen-4"]}],
        "order": ["seedance-openrouter"],
    }
    specs = provider_specs_from_raw(providers)
    ids = {spec["provider_id"] for spec in specs}
    assert ids == {"seedance-openrouter", "gemini-imagen-4"}


def test_provider_specs_from_raw_deduplicates_providers() -> None:
    providers: dict[str, Any] = {
        "video": [{"provider_id": "seedance-openrouter", "models": []}],
        "order": ["seedance-openrouter"],
    }
    specs = provider_specs_from_raw(providers)
    assert len(specs) == 1


def test_provider_specs_returns_empty_when_no_providers() -> None:
    assert provider_specs({}, {}) == []


def test_provider_specs_uses_resolved_config_when_no_provider_profile() -> None:
    resolved_config: dict[str, Any] = {
        "providers": {
            "video": [{"provider_id": "seedance-openrouter", "models": []}],
        }
    }
    specs = provider_specs({}, resolved_config)
    assert specs[0]["provider_id"] == "seedance-openrouter"


def test_profile_resolver_does_not_import_app_or_provider_modules() -> None:
    src_root = Path(__file__).resolve().parents[3] / "src"
    config_root = src_root / "film_pipeline/config"
    violations: list[str] = []
    for source_path in sorted(config_root.rglob("*.py")):
        tree = ast.parse(source_path.read_text())
        package_parts = source_path.relative_to(src_root).parts[:-1]
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for imported in _import_targets(node, package_parts):
                if _is_app_or_provider_import(imported):
                    violations.append(f"{source_path}:{node.lineno}: {imported}")

    assert violations == []


def test_config_import_guard_resolves_relative_and_package_reexports() -> None:
    package_parts = ("film_pipeline", "config")
    relative_import = ast.parse("from ..providers import credentials").body[0]
    package_reexport = ast.parse("from film_pipeline import providers").body[0]

    assert any(
        _is_app_or_provider_import(target)
        for target in _import_targets(relative_import, package_parts)
    )
    assert any(
        _is_app_or_provider_import(target)
        for target in _import_targets(package_reexport, package_parts)
    )
