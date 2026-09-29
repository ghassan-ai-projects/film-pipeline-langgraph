"""Validation run, report, and issue-listing tools.

Transport only. The validation operation itself lives in
``orchestration.execution.run_validation`` (reached through
``StudioRuntime.run_validation``): it selects the phase's validators, records
their findings in project state, and saves each report as an artifact. These
handlers resolve the request, present the outcome, and read persisted state.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeGuard

from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec
from film_pipeline.schemas.base import FilmPhase

from .helpers import (
    _error,
    _ok,
    _report_summary,
)

if TYPE_CHECKING:
    from film_pipeline.schemas.base import FilmPhase


def _parse_phase(phase_str: str) -> FilmPhase | None:
    """Parse a phase string into a FilmPhase, or None when unknown."""

    try:
        return FilmPhase(phase_str)
    except ValueError:
        return None


def _stored_qc_reports(state: dict[str, object]) -> list[object] | None:
    """Return QC-node reports persisted in project state, or None."""
    stored = state.get("_validation_reports")
    if stored and isinstance(stored, list):
        return list(stored)
    return None


def _is_issue_row(issue: object) -> TypeGuard[dict[str, object]]:
    """Only rows carrying a validator_id qualify as validation issues."""
    return isinstance(issue, dict) and "validator_id" in issue


def _normalized_stored_issues(stored: object) -> list[dict[str, object]]:
    """Normalize raw stored QC issues into uniform dicts."""
    issues: list[dict[str, object]] = []
    if not isinstance(stored, list):
        return issues
    for raw_issue in stored:
        if not _is_issue_row(raw_issue):
            continue
        issues.append(
            {
                "code": str(raw_issue.get("code", "")),
                "message": str(raw_issue.get("message", "")),
                "severity": str(raw_issue.get("severity", "")),
                "validator_id": str(raw_issue.get("validator_id", "")),
            }
        )
    return issues


async def run_validation(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Run the current phase's validators and persist their reports.

    The phase scope, the selection, and the persistence all belong to the
    operation; this handler only refuses an unknown phase and shapes the
    response.

    A validator that could not run fails the *action*, and the reports its siblings
    produced are carried on the error rather than discarded: the QC chain is built
    to survive a crashing validator, so dropping every successful finding left the
    operator with a failed action and no evidence of the part that worked.
    """
    _ = args
    rt = ctx.runtime
    active = ctx.project_state()
    project_id = str(active["project_id"])
    phase_str = str(active.get("current_phase", "visual_dev"))

    if _parse_phase(phase_str) is None:
        return _error(f"Unknown phase: {phase_str}")

    try:
        outcome = rt.run_validation(project_id)
    except Exception as exc:
        return _error(f"Validation run failed: {exc}")

    reports = [_report_summary(report) for report in outcome.reports]
    if outcome.failures:
        return _error(
            f"Validation run failed: {outcome.failures[0]}",
            phase=outcome.phase,
            reports=reports,
            saved_refs=list(outcome.report_refs),
            validator_failures=list(outcome.failures),
        )
    if not reports:
        return _ok(message="No validators found for this phase.")
    return _ok(
        phase=outcome.phase,
        reports=reports,
        saved_refs=list(outcome.report_refs),
    )


async def get_validation_report(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Return validation reports for the active project's current phase.

    Reads from stored ``_validation_reports`` in project state (populated
    by the QC node). Falls back to running the same validation operation
    without persisting anything, so the report a caller sees is the report the
    validators actually produce.
    """
    rt = ctx.runtime
    state = ctx.project_state()

    # Stored QC reports work even without a current phase because they are
    # already persisted in state.
    stored = _stored_qc_reports(state)
    if stored is not None:
        return _ok(
            phase=str(state.get("current_phase", "")),
            reports=stored,
            source="qc_node",
            message=f"{len(stored)} validation report(s) from QC node.",
        )

    phase_str = str(state.get("current_phase", ""))
    if not phase_str:
        return _error("No active phase to validate (and no stored reports).")

    if _parse_phase(phase_str) is None:
        return _error(f"Unknown phase: {phase_str}")

    project_id = str(state["project_id"])
    try:
        outcome = rt.run_validation(project_id, persist=False)
    except Exception as exc:  # pragma: no cover - the operation reports its own failures
        return _error(f"Validation run failed: {exc}")
    return _ok(
        phase=phase_str,
        reports=[_report_summary(report) for report in outcome.reports],
        source="live",
    )


async def list_validation_issues(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """List all validation issues for the active project's current phase.

    Reads from stored ``issues`` in project state (populated by QC node).
    """
    _ = args
    state = ctx.project_state()

    issues = _normalized_stored_issues(state.get("issues"))

    if issues:
        return _ok(
            phase=str(state.get("current_phase", "")),
            issues=issues,
            message=f"{len(issues)} issue(s) found.",
        )

    phase_str = str(state.get("current_phase", ""))
    if not phase_str:
        return _ok(phase="", issues=[], message="No active phase and no stored issues.")

    return _ok(phase=phase_str, issues=[], message="No validation issues found.")


class RunValidationArgs(ToolArgs):
    """Arguments for `run_validation` (none)."""


class GetValidationReportArgs(ToolArgs):
    """Arguments for `get_validation_report` (none)."""


class ListValidationIssuesArgs(ToolArgs):
    """Arguments for `list_validation_issues` (none)."""


VALIDATION_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="get_validation_report",
        group=ToolGroup.VALIDATION,
        description="Read the current phase's validation report, from stored or live validators.",
        args=GetValidationReportArgs,
        handler=get_validation_report,
        active_project=True,
    ),
    ToolSpec(
        name="list_validation_issues",
        group=ToolGroup.VALIDATION,
        description="List the validation issues recorded for the current phase.",
        args=ListValidationIssuesArgs,
        handler=list_validation_issues,
        active_project=True,
    ),
)


RUN_VALIDATION = ToolSpec(
    name="run_validation",
    group=ToolGroup.VALIDATION,
    description="Run the validators for the current phase and persist the report.",
    args=RunValidationArgs,
    handler=run_validation,
    mutates=True,
    active_project=True,
)
