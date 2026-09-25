"""Legacy schema imports keep the same enum objects as the new vocabulary owner."""

from __future__ import annotations

import pytest

from film_pipeline import filmspec
from film_pipeline.schemas import _base


@pytest.mark.parametrize(
    "name",
    [
        "ArtifactType",
        "AgentFamily",
        "AgentRole",
        "FilmPhase",
        "GenerationStatus",
        "IssueSeverity",
        "ValidationStatus",
    ],
)
def test_schema_enum_import_is_an_alias(name: str) -> None:
    assert getattr(_base, name) is getattr(filmspec, name)
