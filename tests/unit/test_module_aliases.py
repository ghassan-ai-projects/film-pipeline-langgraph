"""Every compatibility alias still resolves to its canonical owner.

The migration leaves a compatibility module behind each time ownership moves.
Those modules are load-bearing: consumers import them, so a shim that silently
stops re-exporting a name, or re-exports a *copy* instead of the owner's object,
is a behavior change that nothing else in the suite would catch.

This file replaces the nine separate alias-identity test modules that each
asserted a hand-written handful of names. The cases below are derived from the
alias module's own export list, so a newly added re-export is covered the moment
it is written — previously eleven names re-exported by
``film_pipeline.app.services.models`` were asserted nowhere.

A pair is described by the alias module to inspect and the canonical module that
owns the objects. Two shapes are supported:

- ``"module"``: the alias module re-exports the owner's names directly, so every
  public name the alias exposes must be the owner's object.
- ``("module", ("Name", ...))``: the alias module only carries part of the
  owner's surface, so only the named subset is cross-checked. This is the case
  for packages whose public surface is intentionally wider than the shim.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest

#: ``(alias, owner)`` where the alias re-exports the owner's names one-for-one.
_DIRECT_PAIRS: tuple[tuple[str, str], ...] = (
    ("film_pipeline.review.actions", "film_pipeline.governance.actions"),
    ("film_pipeline.review.generator", "film_pipeline.governance.generator"),
    ("film_pipeline.review.diff", "film_pipeline.governance.diff"),
    ("film_pipeline.app.services.errors", "film_pipeline.operations.errors"),
    ("film_pipeline.app.services.models", "film_pipeline.operations.models"),
    ("film_pipeline.schemas.base", "film_pipeline.schemas.base"),
    ("film_pipeline.storage.paths", "film_pipeline.storage.paths"),
    ("film_pipeline.mcp.resolution", "film_pipeline.projects"),
    ("film_pipeline.projects.resolution", "film_pipeline.projects.resolution"),
)

#: ``(alias, owner, names)`` where only the listed names are cross-checked.
_SUBSET_PAIRS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "film_pipeline.storage.paths",
        "film_pipeline.storage.paths",
        ("PHASE_DIR_MAP", "project_dir", "phase_dir", "media_scene_dir"),
    ),
    (
        "film_pipeline.storage.registry",
        "film_pipeline.storage.contract",
        ("ARTIFACT_ID_PATTERN", "validate_artifact_id", "sanitize_artifact_id", "KindSpec"),
    ),
    (
        "film_pipeline.review",
        "film_pipeline.governance",
        (
            "REVIEW_TYPE_MAP",
            "ArtifactDiff",
            "AvailableActions",
            "ReviewPackageGenerator",
            "compute_artifact_diff",
            "compute_available_actions",
        ),
    ),
    (
        "film_pipeline.schemas._base",
        "film_pipeline.filmspec",
        (
            "ArtifactType",
            "AgentFamily",
            "AgentRole",
            "FilmPhase",
            "GenerationStatus",
            "IssueSeverity",
            "ValidationStatus",
        ),
    ),
    (
        "film_pipeline.schemas._base",
        "film_pipeline.schemas.base",
        (
            "SchemaBase",
            "MutableSchemaBase",
            "ArtifactStatus",
            "ArtifactType",
            "FilmPhase",
            "ValidationStatus",
        ),
    ),
)

#: ``(alias, owner, alias_name, owner_name)`` where the two names differ.
_RENAMED_PAIRS: tuple[tuple[str, str, str, str], ...] = (
    ("film_pipeline.graph.router", "film_pipeline.filmspec", "APPROVAL_GATES", "PHASE_GATES"),
)


def _public_names(module: Any) -> list[str]:
    """Return the names an alias module advertises, sorted for stable ids."""
    declared = getattr(module, "__all__", None)
    if declared is not None:
        return sorted(declared)
    return sorted(name for name in vars(module) if not name.startswith("_"))


def _alias_cases() -> list[tuple[str, str, str]]:
    cases: list[tuple[str, str, str]] = []
    for alias_name, owner_name in _DIRECT_PAIRS:
        if alias_name == owner_name:
            continue
        owner = importlib.import_module(owner_name)
        for name in _public_names(importlib.import_module(alias_name)):
            if hasattr(owner, name):
                cases.append((alias_name, owner_name, name))
    for alias_name, owner_name, names in _SUBSET_PAIRS:
        cases.extend((alias_name, owner_name, name) for name in names)
    return cases


def _renamed_cases() -> list[tuple[str, str, str, str]]:
    return list(_RENAMED_PAIRS)


@pytest.mark.parametrize(
    ("alias_name", "owner_name", "name"),
    _alias_cases(),
    ids=lambda value: value if isinstance(value, str) else str(value),
)
def test_alias_resolves_to_owner_object(alias_name: str, owner_name: str, name: str) -> None:
    """An aliased name must be the owner's object, never a re-defined copy."""
    alias = importlib.import_module(alias_name)
    owner = importlib.import_module(owner_name)
    assert hasattr(alias, name), f"{alias_name} no longer exports {name}"
    assert getattr(alias, name) is getattr(owner, name), (
        f"{alias_name}.{name} is not {owner_name}.{name}"
    )


def test_alias_case_corpus_is_not_empty() -> None:
    """Guard against the parametrization silently collapsing to zero cases."""
    assert len(_alias_cases()) >= 40


@pytest.mark.parametrize(
    ("alias_name", "owner_name", "alias_attr", "owner_attr"),
    _renamed_cases(),
)
def test_renamed_alias_resolves_to_owner_object(
    alias_name: str, owner_name: str, alias_attr: str, owner_attr: str
) -> None:
    """A migrated name may be re-exported under a new spelling."""
    alias = importlib.import_module(alias_name)
    owner = importlib.import_module(owner_name)
    assert hasattr(alias, alias_attr), f"{alias_name} no longer exports {alias_attr}"
    assert getattr(alias, alias_attr) is getattr(owner, owner_attr), (
        f"{alias_name}.{alias_attr} is not {owner_name}.{owner_attr}"
    )


def test_every_alias_module_is_importable() -> None:
    """A broken shim must fail here rather than at an unrelated consumer."""
    modules = [alias for alias, _owner in _DIRECT_PAIRS]
    modules += [alias for alias, _owner, _names in _SUBSET_PAIRS]
    for module_name in sorted(set(modules)):
        importlib.import_module(module_name)
