"""Tests for the blocking-reason reporter."""

from __future__ import annotations

from film_pipeline.observability.blockers import BlockEntry, BlockerReport, BlockerReporter
from film_pipeline.schemas._base import FilmPhase


class TestBlockerReport:
    def test_no_blockers_summary(self) -> None:
        report = BlockerReport(project_id="p1")
        assert report.has_blockers is False
        assert report.total_blockers == 0
        assert report.summary == "No blockers. All phases clear."

    def test_single_blocker_summary(self) -> None:
        report = BlockerReport(
            project_id="p1",
            blocks=[BlockEntry(phase=FilmPhase.SCRIPT, reason="missing scenes")],
        )
        assert report.has_blockers is True
        assert report.total_blockers == 1
        assert report.summary == "1 blocker: script — missing scenes"

    def test_multiple_blockers_summary_counts_only_blocking(self) -> None:
        report = BlockerReport(
            project_id="p1",
            blocks=[
                BlockEntry(phase=FilmPhase.SCRIPT, reason="missing scenes"),
                BlockEntry(phase=FilmPhase.QC, reason="low score", severity="warning"),
                BlockEntry(phase=FilmPhase.SHOT_BIBLE, reason="shot count mismatch"),
            ],
        )
        assert report.total_blockers == 2
        assert report.summary == "2 blockers. First: script — missing scenes"


class TestBlockerReporter:
    def test_report_builds_entries_from_open_issues(self) -> None:
        reporter = BlockerReporter()
        report = reporter.report(
            "p1",
            open_issues=[
                {"phase": "script", "reason": "thin scenes", "severity": "blocking"},
                {"phase": "qc", "reason": "minor note", "severity": "warning"},
            ],
        )
        assert report.project_id == "p1"
        assert len(report.blocks) == 2
        assert report.has_blockers is True

    def test_report_with_no_issues_is_clear(self) -> None:
        reporter = BlockerReporter()
        report = reporter.report("p1")
        assert report.blocks == []
        assert reporter.can_proceed(report) is True

    def test_can_proceed_false_when_blocking(self) -> None:
        reporter = BlockerReporter()
        report = reporter.report("p1", open_issues=[{"reason": "x"}])
        assert reporter.can_proceed(report) is False
