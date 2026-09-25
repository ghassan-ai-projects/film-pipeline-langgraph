"""Old schema base imports remain aliases of the public owner."""

from __future__ import annotations

import pytest

from film_pipeline.schemas import _base, base


@pytest.mark.parametrize(
    "name",
    [
        "SchemaBase",
        "MutableSchemaBase",
        "ArtifactStatus",
        "ArtifactType",
        "FilmPhase",
        "ValidationStatus",
    ],
)
def test_old_base_import_is_the_public_object(name: str) -> None:
    assert getattr(_base, name) is getattr(base, name)
