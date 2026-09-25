"""Legacy schema imports keep the same enum objects as the new vocabulary owner."""

from __future__ import annotations

import pytest

from film_pipeline import filmspec
from film_pipeline.graph.router import APPROVAL_GATES
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


def test_phase_gate_and_transition_aliases_share_their_owner() -> None:
    assert APPROVAL_GATES is filmspec.PHASE_GATES
    assert set(filmspec.PHASE_GATES) == set(filmspec.PHASE_SEQUENCE)
    assert (
        set(filmspec.PHASE_SEQUENCE)
        == filmspec.PHASE_AGNOSTIC_PHASES | filmspec.GENERATION_DEPENDENT_PHASES
    )
    assert _base.TRANSITION_TYPES is filmspec.TRANSITION_TYPES
    assert _base.LEGACY_TRANSITION_ALIASES is filmspec.LEGACY_TRANSITION_ALIASES
