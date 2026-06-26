"""Tests for structured repair feedback prompt rendering."""

from __future__ import annotations

import pytest

from film_pipeline.schemas.repair import (
    GlobalRepairIssue,
    RepairFeedback,
    RowRepairInstruction,
)


def test_repair_feedback_renders_preserve_and_row_specific_instructions() -> None:
    feedback = RepairFeedback(
        repair_id="repair:shot_bible:r2",
        phase="shot_bible",
        round=2,
        project_id="p1",
        passed_row_ids=[f"s{i:02d}" for i in range(25)],
        failed_rows=[
            RowRepairInstruction(
                shot_id="s99",
                issues=[
                    {
                        "code": "BAD_DURATION",
                        "field": "duration_seconds",
                        "message": "Duration exceeds movement range.",
                        "recommended_action": "Use 8-10 seconds.",
                    },
                    {"code": "MISSING_PROMPT", "message": "Prompt ref is absent."},
                ],
            )
        ],
        global_issues=[
            GlobalRepairIssue(
                code="RUNTIME_TOTAL",
                message="Total runtime is short.",
                recommended_action="Add two seconds to act_2 shots.",
            )
        ],
    )

    rendered = feedback.to_agent_context()

    assert "REPAIR ROUND 2" in rendered
    assert "PRESERVE these 25 rows verbatim" in rendered
    assert "s00, s01" in rendered
    assert "..." in rendered
    assert "[BAD_DURATION] Duration exceeds movement range. (field: duration_seconds)" in rendered
    assert "Use 8-10 seconds." in rendered
    assert "s99:" in rendered
    assert "(preserve all other fields)" in rendered
    assert "GLOBAL FIXES:" in rendered
    assert "[RUNTIME_TOTAL] Total runtime is short." in rendered


def test_repair_feedback_allows_regenerating_entire_failed_row() -> None:
    feedback = RepairFeedback(
        repair_id="repair:script:r1",
        phase="script",
        round=1,
        project_id="p1",
        failed_rows=[
            RowRepairInstruction(
                shot_id="scene_001",
                preserve_other_fields=False,
                issues=[{"code": "NO_CONFLICT", "message": "Scene lacks tension."}],
            )
        ],
    )

    rendered = feedback.to_agent_context()

    assert "scene_001: [NO_CONFLICT] Scene lacks tension." in rendered
    assert "preserve all other fields" not in rendered


def test_repair_feedback_rejects_invalid_rounds() -> None:
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        RepairFeedback(
            repair_id="repair:bad:r0",
            phase="script",
            round=0,
            project_id="p1",
        )
