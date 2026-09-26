"""Tests for the canonical artifact ref grammar (storage upgrade D5)."""

from __future__ import annotations

import pytest

from film_pipeline.schemas.artifact import ArtifactRef


class TestRefRoundTrip:
    def test_canonical_form_round_trips(self) -> None:
        ref = ArtifactRef.from_string("artifact:script:script:v3")
        assert ref == ArtifactRef(artifact_id="script", version=3, phase="script")
        assert ref.to_string() == "artifact:script:script:v3"

    def test_phase_is_required(self) -> None:
        ref = ArtifactRef(artifact_id="script", version=1, phase="script")
        assert ref.to_string() == "artifact:script:script:v1"

    @pytest.mark.parametrize(
        "bad",
        [
            "nonsense",
            "artifact:budget_state:cash",
            "artifact:x:v",
            "artifact:v3",
            # Pre-upgrade phase-less forms no longer parse.
            "artifact:script:v1",
        ],
    )
    def test_malformed_refs_are_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError, match="Invalid artifact ref"):
            ArtifactRef.from_string(bad)
