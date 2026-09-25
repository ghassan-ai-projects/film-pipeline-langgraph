"""E2E Scenario 6: Continuity drift — detection stops work and flags repair."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.orchestration.router import compute_actions
from film_pipeline.orchestration.services import GraphServices
from film_pipeline.studio.runtime import StudioRuntime
from film_pipeline.validation.impl.scene_continuity import SceneContinuityValidator


@pytest.mark.e2e
class TestContinuityDrift:
    def test_continuity_issues_are_detectable(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services
        rt.create_project("continuity-test", "Continuity Test")
        rt.set_active("continuity-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "A time-loop thriller."
        project["current_phase"] = "generation"
        project["issues"] = [
            {
                "issue_id": "cont-1",
                "severity": "blocking",
                "code": "CHARACTER_STATE_MISMATCH",
                "message": "Character Elara eye color mismatch.",
            }
        ]
        rt.projects["continuity-test"] = project

        issues = project.get("issues", [])
        assert any(i["code"] == "CHARACTER_STATE_MISMATCH" for i in issues)

    def test_blocked_phase_flags_repair_action(
        self,
        graph_services: GraphServices,
        tmp_path: Path,
    ) -> None:
        rt = StudioRuntime(runtime_root=tmp_path / "runtime")
        rt.services = graph_services
        rt.create_project("repair-test", "Repair Test")
        rt.set_active("repair-test")
        project = rt.get_active()
        assert project is not None
        project["idea"] = "Repair test."
        project["current_phase"] = "generation"
        project["issues"] = [
            {"issue_id": "c1", "severity": "blocking", "code": "CONTINUITY_GAP", "message": "Gap."}
        ]
        rt.projects["repair-test"] = project

        result = compute_actions(project)
        assert result.blocked, "Router should report blocked state"

    def test_continuity_validator_detects_drift(self) -> None:
        """SceneContinuityValidator catches character state mismatch."""
        validator = SceneContinuityValidator()
        artifact = {
            "shots": [
                {
                    "shot_id": "S001",
                    "characters": [
                        {"character_id": "alex", "state": "angry", "position": "doorway"}
                    ],
                    "lighting": "warm",
                    "props": ["key"],
                    "wardrobe": {"alex": "red_jacket"},
                },
                {
                    "shot_id": "S002",
                    "characters": [{"character_id": "alex", "state": "calm", "position": "desk"}],
                    "lighting": "warm",
                    "props": ["key"],
                    "wardrobe": {"alex": "red_jacket"},
                },
            ]
        }
        report = validator.run(artifact)
        assert any(i.code == "character_state_mismatch" for i in report.blocking_issues)

    def test_clean_sequence_passes(self) -> None:
        """A shot sequence with no drift passes validation."""
        validator = SceneContinuityValidator()
        artifact = {
            "shots": [
                {
                    "shot_id": "S001",
                    "characters": [],
                    "lighting": "daylight",
                    "props": ["cup"],
                    "wardrobe": {},
                },
                {
                    "shot_id": "S002",
                    "characters": [],
                    "lighting": "daylight",
                    "props": ["cup"],
                    "wardrobe": {},
                },
            ]
        }
        report = validator.run(artifact)
        assert report.status.value == "pass"
