"""SceneContinuityValidator — validates continuity across shot sequences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import (
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.validation.base import BaseValidator


@dataclass(frozen=True)
class _ShotSnapshot:
    """Continuity-relevant facts extracted from one shot."""

    index: int
    shot_id: str
    characters: list[dict[str, Any]]
    props: list[str]
    lighting: str
    wardrobe: dict[str, str]
    transition_reason: str


@dataclass(frozen=True)
class _ShotTrackers:
    """State carried from one shot to the next during the sequence scan."""

    character_states: dict[str, dict[str, str]]
    lighting: str
    props: set[str]
    wardrobe: dict[str, str]


def _empty_continuity_result() -> dict[str, Any]:
    """Result payload for an artifact that contains no shots."""
    return {
        "total_shots": 0,
        "issues": [],
        "character_state_mismatches": 0,
        "prop_disappearances": 0,
        "lighting_shifts": 0,
        "wardrobe_drifts": 0,
    }


def _shot_snapshot(shot: dict[str, Any], index: int) -> _ShotSnapshot:
    """Extract the continuity-relevant facts of a single shot."""
    return _ShotSnapshot(
        index=index,
        shot_id=str(shot.get("shot_id", shot.get("scene_id", f"shot-{index}"))),
        characters=shot.get("characters", []),
        props=shot.get("props", []),
        lighting=str(shot.get("lighting", "")),
        wardrobe=shot.get("wardrobe", {}),
        # `or ""` preserves HEAD truthiness: a falsy non-string (null/0/false)
        # must stay falsy so the missing-reason gate still fires.
        transition_reason=str(shot.get("state_transition_reason") or ""),
    )


def _current_character_states(
    characters: list[dict[str, Any]],
) -> dict[str, dict[str, str]]:
    """Map each character id to its declared state and position."""
    current_states: dict[str, dict[str, str]] = {}
    for char in characters:
        cid = str(char.get("character_id", "?"))
        state = str(char.get("state", ""))
        position = str(char.get("position", ""))
        current_states[cid] = {"state": state, "position": position}
    return current_states


def _is_unexplained_change(previous: str, current: str, reason: str) -> bool:
    """True when a tracked value changed and no transition reason is given."""
    return bool(previous) and bool(current) and previous != current and not reason


def _flag_unexplained_state_changes(
    snapshot: _ShotSnapshot,
    prev_character_states: dict[str, dict[str, str]],
    issues: list[dict[str, str]],
) -> int:
    """Flag character state changes without documented transition reasons."""
    flagged = 0
    for char in snapshot.characters:
        cid = str(char.get("character_id", "?"))
        state = str(char.get("state", ""))
        previous = prev_character_states.get(cid)
        if previous is None or not _is_unexplained_change(
            previous["state"], state, snapshot.transition_reason
        ):
            continue
        flagged += 1
        issues.append(
            {
                "code": "character_state_mismatch",
                "severity": "blocking",
                "message": (
                    f"Character '{cid}' state changed from "
                    f"'{previous['state']}' to '{state}' in shot '{snapshot.shot_id}' "
                    "without documented transition reason."
                ),
            }
        )
    return flagged


def _flag_disappeared_props(
    snapshot: _ShotSnapshot,
    prev_props: set[str],
    issues: list[dict[str, str]],
) -> int:
    """Flag props present in the previous shot but missing from this one."""
    if snapshot.index == 0 or not prev_props:
        return 0
    disappeared = prev_props - set(snapshot.props)
    if not disappeared:
        return 0
    issues.append(
        {
            "code": "prop_disappeared",
            "severity": "blocking",
            "message": (
                f"Props {sorted(disappeared)} present in previous shot "
                f"but missing from shot '{snapshot.shot_id}'."
            ),
        }
    )
    return 1


def _flag_lighting_shift(
    snapshot: _ShotSnapshot,
    prev_lighting: str,
    issues: list[dict[str, str]],
) -> int:
    """Flag lighting changes between consecutive shots."""
    if snapshot.index == 0 or not snapshot.lighting or not prev_lighting:
        return 0
    if prev_lighting == snapshot.lighting:
        return 0
    issues.append(
        {
            "code": "lighting_shift",
            "severity": "warning",
            "message": (
                f"Lighting changed from '{prev_lighting}' to '{snapshot.lighting}' "
                f"in shot '{snapshot.shot_id}'."
            ),
        }
    )
    return 1


def _flag_wardrobe_drift(
    snapshot: _ShotSnapshot,
    prev_wardrobe: dict[str, str],
    issues: list[dict[str, str]],
) -> int:
    """Flag characters whose outfit drifted from the previous shot."""
    if snapshot.index == 0 or not snapshot.wardrobe or not prev_wardrobe:
        return 0
    flagged = 0
    for cid, outfit in snapshot.wardrobe.items():
        prev_outfit = prev_wardrobe.get(cid)
        if not prev_outfit or prev_outfit == outfit:
            continue
        flagged += 1
        issues.append(
            {
                "code": "wardrobe_minor_drift",
                "severity": "warning",
                "message": (
                    f"Character '{cid}' outfit changed from "
                    f"'{prev_outfit}' to '{outfit}' in shot '{snapshot.shot_id}'."
                ),
            }
        )
    return flagged


def _trackers_before_first_shot() -> _ShotTrackers:
    """Fresh trackers for the start of the sequence scan."""
    return _ShotTrackers(character_states={}, lighting="", props=set(), wardrobe={})


def _trackers_after_shot(snapshot: _ShotSnapshot) -> _ShotTrackers:
    """Roll the trackers forward to compare against the next shot."""
    return _ShotTrackers(
        character_states=_current_character_states(snapshot.characters),
        lighting=snapshot.lighting,
        props=set(snapshot.props),
        wardrobe=snapshot.wardrobe,
    )


class SceneContinuityValidator(BaseValidator):
    """Validates continuity across shots: character state, prop presence,
    lighting consistency, and wardrobe drift.

    Matches the ``scene-continuity-validator`` contract.
    """

    def __init__(self) -> None:
        entry = ValidatorRegistryEntry(
            validator_id="scene-continuity-validator",
            scope=ValidationScope.SCENE,
            modalities=[ValidationModality.CONTINUITY],
            input_schema="scene_clips",
            model_profile="multimodal_reviewer",
            thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),
            blocking_conditions=["character_state_mismatch", "prop_disappeared"],
            warning_conditions=["lighting_shift", "wardrobe_minor_drift"],
        )
        super().__init__(entry)

    def _validate_rules(
        self,
        artifact: dict[str, Any],
        context: object = None,
    ) -> dict[str, Any]:
        """Inspect shots for continuity issues across the sequence."""
        _ = context
        shots: list[dict[str, Any]] = artifact.get("shots", artifact.get("scenes", []))
        if not shots:
            return _empty_continuity_result()

        issues: list[dict[str, str]] = []
        mismatch_counts: dict[str, int] = {
            "character_state_mismatches": 0,
            "prop_disappearances": 0,
            "lighting_shifts": 0,
            "wardrobe_drifts": 0,
        }
        trackers = _trackers_before_first_shot()

        for index, shot in enumerate(shots):
            snapshot = _shot_snapshot(shot, index)
            mismatch_counts["character_state_mismatches"] += _flag_unexplained_state_changes(
                snapshot, trackers.character_states, issues
            )
            mismatch_counts["prop_disappearances"] += _flag_disappeared_props(
                snapshot, trackers.props, issues
            )
            mismatch_counts["lighting_shifts"] += _flag_lighting_shift(
                snapshot, trackers.lighting, issues
            )
            mismatch_counts["wardrobe_drifts"] += _flag_wardrobe_drift(
                snapshot, trackers.wardrobe, issues
            )
            trackers = _trackers_after_shot(snapshot)

        return {
            "total_shots": len(shots),
            "issues": issues,
            **mismatch_counts,
        }

    def extract_score(self, raw: dict[str, Any]) -> float:
        total: int = raw.get("total_shots", 0)
        if total == 0:
            return 100.0

        char_mismatch: int = raw.get("character_state_mismatches", 0)
        prop_dis: int = raw.get("prop_disappearances", 0)
        light_shift: int = raw.get("lighting_shifts", 0)
        wd: int = raw.get("wardrobe_drifts", 0)

        score = 100.0
        # Blocking items cost more
        score -= char_mismatch * 20.0
        score -= prop_dis * 20.0
        # Warning items cost less
        score -= light_shift * 8.0
        score -= wd * 5.0
        return max(0.0, min(100.0, score))
