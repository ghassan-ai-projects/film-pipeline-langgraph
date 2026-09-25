"""Tests for review package generator."""

from __future__ import annotations

from film_pipeline.governance.generator import REVIEW_TYPE_MAP, ReviewPackageGenerator
from film_pipeline.schemas.base import FilmPhase


class TestGenerator:
    def test_build_basic(self) -> None:
        gen = ReviewPackageGenerator()
        pkg = gen.build(
            project_id="p1",
            phase=FilmPhase.SCRIPT,
            summary="Script v3 complete.",
            current_artifacts=["artifact:script:S001:v3"],
            orchestrator_recommendation="approve",
        )
        assert pkg.project_id == "p1"
        assert pkg.phase == FilmPhase.SCRIPT
        assert pkg.type == "script_review"
        assert pkg.summary == "Script v3 complete."
        assert "artifact:script:S001:v3" in pkg.artifacts
        assert "approve_phase" in pkg.available_actions

    def test_build_all_phases_have_types(self) -> None:
        gen = ReviewPackageGenerator()
        for phase in FilmPhase:
            pkg = gen.build(
                project_id="p1",
                phase=phase,
                summary="test",
            )
            assert pkg.type != "", f"Phase {phase} has no review type"

    def test_build_with_previous_diff(self) -> None:
        gen = ReviewPackageGenerator()
        pkg = gen.build(
            project_id="p1",
            phase=FilmPhase.SCRIPT,
            summary="test",
            current_artifacts=["artifact:script:S001:v3", "artifact:script:S002:v1"],
            previous_approved_artifacts=["artifact:script:S001:v2"],
        )
        assert "artifact:script:S002:v1" in pkg.diff_from_approved["added"]
        assert "artifact:script:S001:v3" in pkg.diff_from_approved["changed"]
        assert len(pkg.diff_from_approved["removed"]) == 0

    def test_build_with_blocking_issues(self) -> None:
        gen = ReviewPackageGenerator()
        pkg = gen.build(
            project_id="p1",
            phase=FilmPhase.GENERATION,
            summary="test",
            has_blocking_issues=True,
        )
        assert "approve_phase" in pkg.blocked_actions
        assert "approve_phase" not in pkg.available_actions
        assert "request_revision" in pkg.available_actions

    def test_build_with_checkpoint(self) -> None:
        gen = ReviewPackageGenerator()
        pkg = gen.build(
            project_id="p1",
            phase=FilmPhase.GENERATION,
            summary="test",
            has_checkpoint=True,
        )
        assert "rollback_to_checkpoint" in pkg.available_actions

    def test_build_without_checkpoint(self) -> None:
        gen = ReviewPackageGenerator()
        pkg = gen.build(
            project_id="p1",
            phase=FilmPhase.GENERATION,
            summary="test",
        )
        assert "rollback_to_checkpoint" in pkg.blocked_actions

    def test_build_with_risks_and_issues(self) -> None:
        gen = ReviewPackageGenerator()
        pkg = gen.build(
            project_id="p1",
            phase=FilmPhase.POST,
            summary="Assembly ready.",
            open_issues=["missing_transition_S001_002"],
            risks=["Audio sync may drift in final export"],
            cost_impact={"estimated_remaining": "$0.50", "within_budget": "true"},
        )
        assert len(pkg.open_issues) == 1
        assert len(pkg.risks) == 1
        assert pkg.cost_impact["estimated_remaining"] == "$0.50"

    def test_build_with_validation_results(self) -> None:
        gen = ReviewPackageGenerator()
        pkg = gen.build(
            project_id="p1",
            phase=FilmPhase.QC,
            summary="QC complete.",
            validation_results=["validation:clip:S001:v1", "validation:scene:1:v1"],
        )
        assert len(pkg.validation_results) == 2

    def test_build_empty_artifacts(self) -> None:
        gen = ReviewPackageGenerator()
        pkg = gen.build(
            project_id="p1",
            phase=FilmPhase.INTAKE,
            summary="Empty project intake.",
        )
        assert pkg.artifacts == []
        assert pkg.diff_from_approved == {"added": [], "changed": [], "removed": []}

    def test_review_type_map_covers_all_phases(self) -> None:
        for phase in FilmPhase:
            assert phase in REVIEW_TYPE_MAP, f"Missing review type for {phase}"
