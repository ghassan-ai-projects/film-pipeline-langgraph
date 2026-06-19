"""Smoke tests verifying the package imports and constants are wired."""

from __future__ import annotations

from film_pipeline import __version__, project_name


def test_version_is_string() -> None:
    assert isinstance(__version__, str)
    assert __version__ == "0.2.0"


def test_project_name() -> None:
    assert project_name() == "film-pipeline"


def test_subpackages_importable() -> None:
    """Every planned subsystem module must be importable as a sub-package."""
    expected = [
        "film_pipeline.config",
        "film_pipeline.schemas",
        "film_pipeline.artifacts",
        "film_pipeline.graph",
        "film_pipeline.kb",
        "film_pipeline.agents",
        "film_pipeline.review",
        "film_pipeline.validation",
        "film_pipeline.providers",
        "film_pipeline.checkpoints",
        "film_pipeline.mcp",
        "film_pipeline.post",
    ]
    for module_name in expected:
        __import__(module_name)
