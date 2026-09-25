"""Smoke tests verifying the package imports and constants are wired."""

from __future__ import annotations

import importlib

from film_pipeline import __version__, project_name


def test_version_is_string() -> None:
    assert isinstance(__version__, str)
    assert __version__ == "0.4.0"


def test_project_name() -> None:
    assert project_name() == "film-pipeline"


def test_subpackages_importable() -> None:
    """Every shipped subsystem package must actually import.

    A bare ``__import__`` loop cannot fail loudly enough: it swallows nothing
    but also asserts nothing, so a missing module and a healthy one look the
    same. This asserts each import resolves to a real package object.
    """
    expected = [
        "film_pipeline.agents",
        "film_pipeline.studio",
        "film_pipeline.artifacts",
        "film_pipeline.checkpoints",
        "film_pipeline.cli",
        "film_pipeline.config",
        "film_pipeline.constraints",
        "film_pipeline.devharness",
        "film_pipeline.filmspec",
        "film_pipeline.generation",
        "film_pipeline.governance",
        "film_pipeline.orchestration",
        "film_pipeline.kb",
        "film_pipeline.mcp",
        "film_pipeline.operations",
        "film_pipeline.post",
        "film_pipeline.projects",
        "film_pipeline.providers",
        "film_pipeline.review",
        "film_pipeline.schemas",
        "film_pipeline.storage",
        "film_pipeline.validation",
    ]
    for module_name in expected:
        module = importlib.import_module(module_name)
        assert module.__name__ == module_name
        assert hasattr(module, "__file__") or hasattr(module, "__path__")
