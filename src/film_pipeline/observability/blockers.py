"""Blocking reason reporter — what is blocking progress and why."""

from __future__ import annotations

from dataclasses import dataclass, field

from film_pipeline.schemas._base import FilmPhase


@dataclass
class BlockEntry:
    """A single blocking issue with explanation."""

    phase: FilmPhase
    reason: str
    severity: str = "blocking"  # blocking | warning
    resolution: str = ""
    blocking_since: str = ""


@dataclass
class BlockerReport:
    """Report of all blocking issues across the project."""

    project_id: str
    blocks: list[BlockEntry] = field(default_factory=list)

    @property
    def has_blockers(self) -> bool:
        return any(b.severity == "blocking" for b in self.blocks)

    @property
    def total_blockers(self) -> int:
        return sum(1 for b in self.blocks if b.severity == "blocking")

    @property
    def summary(self) -> str:
        if not self.blocks:
            return "No blockers. All phases clear."
        block_count = self.total_blockers
        first = self.blocks[0]
        if block_count == 1:
            return f"1 blocker: {first.phase.value} — {first.reason}"
        return f"{block_count} blockers. First: {first.phase.value} — {first.reason}"


@dataclass
class BlockerReporter:
    """Produces BlockerReports from project state."""

    def report(
        self,
        project_id: str,
        open_issues: list[dict[str, str]] | None = None,
    ) -> BlockerReport:
        """Build a blocker report from open issues."""
        report = BlockerReport(project_id=project_id)

        for issue in open_issues or []:
            report.blocks.append(
                BlockEntry(
                    phase=FilmPhase(issue.get("phase", "script")),
                    reason=issue.get("reason", "Unknown"),
                    severity=issue.get("severity", "blocking"),
                    resolution=issue.get("resolution", ""),
                )
            )

        return report

    def can_proceed(self, report: BlockerReport) -> bool:
        return not report.has_blockers
