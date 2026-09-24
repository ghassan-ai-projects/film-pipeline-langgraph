"""Tests for the canonical artifact ref grammar (storage upgrade D5)."""

from __future__ import annotations

import pytest

from film_pipeline.schemas.artifact import ArtifactRef


class TestRefRoundTrip:
    def test_canonical_form_round_trips(self) -> None:
        ref = ArtifactRef.from_string("artifact:script:script:v3")
        assert ref == ArtifactRef(artifact_id="script", version=3, phase="script")
        assert ref.to_string() == "artifact:script:script:v3"

    def test_legacy_phase_less_form_parses(self) -> None:
        ref = ArtifactRef.from_string("artifact:film_constitution:v1")
        assert ref.artifact_id == "film_constitution"
        assert ref.version == 1
        assert ref.phase is None
        assert ref.to_string() == "artifact:film_constitution:v1"

    def test_legacy_colon_bearing_id_parses_whole(self) -> None:
        """Pre-validation ids could contain colons; they must not lose segments."""
        ref = ArtifactRef.from_string("artifact:profile_change_proposal:profile-change:abc:v2")
        assert ref.artifact_id == "profile_change_proposal:profile-change:abc"
        assert ref.version == 2
        assert ref.phase is None

    def test_phase_vocabulary_disambiguates_four_segment_refs(self) -> None:
        """A real phase in position 2 means canonical form, not a colon id."""
        ref = ArtifactRef.from_string("artifact:intake:graph_state:v4")
        assert ref.phase == "intake"
        assert ref.artifact_id == "graph_state"

    @pytest.mark.parametrize(
        "bad", ["nonsense", "artifact:budget_state:cash", "artifact:x:v", "artifact:v3"]
    )
    def test_malformed_refs_are_rejected(self, bad: str) -> None:
        with pytest.raises(ValueError, match="Invalid artifact ref"):
            ArtifactRef.from_string(bad)
