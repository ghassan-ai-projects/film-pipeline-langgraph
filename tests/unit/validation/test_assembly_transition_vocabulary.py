"""AssemblyValidator gates exactly the unified transition vocabulary.

Proves end-to-end through ``run()`` that every value in TRANSITION_TYPES
passes, legacy spellings resolve explicitly via LEGACY_TRANSITION_ALIASES,
and unmapped values are flagged as unknown.
"""

from __future__ import annotations

import pytest

from film_pipeline.post.transition_agent import TRANSITION_TYPES
from film_pipeline.schemas.base import LEGACY_TRANSITION_ALIASES
from film_pipeline.schemas.validation import ValidationIssue, ValidationReport
from film_pipeline.validation.impl.assembly import AssemblyValidator


def _manifest_with_transition_type(transition_type: str) -> dict[str, object]:
    """Well-formed two-clip manifest whose single transition uses transition_type."""
    return {
        "cut_id": "cut-vocab",
        "clip_order": [
            {"shot_id": "S001", "in_seconds": 0, "out_seconds": 5},
            {"shot_id": "S002", "in_seconds": 5, "out_seconds": 10},
        ],
        "transitions": [
            {
                "from_shot_id": "S001",
                "to_shot_id": "S002",
                "transition_type": transition_type,
            },
        ],
        "missing_assets": [],
        "audio_plan": {"cue_points": [], "dialogue_track_refs": []},
        "color_plan": {"look": "warm_cinematic", "per_scene": {}},
    }


def _unknown_type_issue(report: ValidationReport) -> ValidationIssue | None:
    """Return the unknown-transition-type blocking issue, when present."""
    return next((i for i in report.blocking_issues if "unknown type" in i.message), None)


class TestCanonicalTransitionTypesPass:
    @pytest.mark.parametrize("transition_type", TRANSITION_TYPES)
    def test_canonical_types_raise_no_unknown_type_issue(self, transition_type: str) -> None:
        report = AssemblyValidator().run(_manifest_with_transition_type(transition_type))
        assert _unknown_type_issue(report) is None


class TestLegacyTransitionAliases:
    @pytest.mark.parametrize(("legacy", "canonical"), sorted(LEGACY_TRANSITION_ALIASES.items()))
    def test_legacy_spelling_resolves_onto_canonical_member(
        self, legacy: str, canonical: str
    ) -> None:
        assert canonical in TRANSITION_TYPES
        report = AssemblyValidator().run(_manifest_with_transition_type(legacy))
        assert _unknown_type_issue(report) is None


class TestUnmappedTransitionTypesFlagged:
    def test_wipe_without_canonical_equivalent_is_flagged(self) -> None:
        report = AssemblyValidator().run(_manifest_with_transition_type("wipe"))
        issue = _unknown_type_issue(report)
        assert issue is not None
        assert issue.code == "broken_transitions"
        assert "'wipe'" in issue.message

    def test_empty_transition_type_is_skipped(self) -> None:
        report = AssemblyValidator().run(_manifest_with_transition_type(""))
        assert _unknown_type_issue(report) is None
