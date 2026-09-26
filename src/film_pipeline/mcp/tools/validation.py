"""Validation run, report, and issue-listing tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeGuard

import film_pipeline.mcp.tools as tools_pkg

from .helpers import (
    _active_project_id,
    _error,
    _load_artifact,
    _load_latest_reference_index,
    _no_active_project,
    _ok,
    _report_summary,
    _services,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from film_pipeline.schemas.base import FilmPhase
    from film_pipeline.schemas.validation import ValidationReport
    from film_pipeline.storage.store import ArtifactStore


def _parse_phase(phase_str: str) -> FilmPhase | None:
    """Parse a phase string into a FilmPhase, or None when unknown."""
    from film_pipeline.schemas.base import FilmPhase

    try:
        return FilmPhase(phase_str)
    except ValueError:
        return None


def _require_project(args: dict[str, object], rt: Any) -> tuple[str, dict[str, object]] | None:
    """Resolve (project_id, state) for a request, or None when unavailable."""
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return None
    state = rt.get_project(project_id)
    if state is None:
        return None
    return project_id, state


def _stored_qc_reports(state: dict[str, object]) -> list[object] | None:
    """Return QC-node reports persisted in project state, or None."""
    stored = state.get("_validation_reports")
    if stored and isinstance(stored, list):
        return list(stored)
    return None


@dataclass(frozen=True)
class _PhaseSpec:
    """One live-validation arm.

    ``phases`` selects the arm (membership only); the position of a spec in
    the table returned by ``_live_validator_specs`` encodes execution order.
    """

    phases: tuple[str, ...]
    load: Callable[[], Any]
    validators: Callable[[], tuple[type[Any], ...]]


def _script_validators() -> tuple[type[Any], ...]:
    """Import script-phase validators lazily, preserving run order."""
    from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
    from film_pipeline.validation.impl.script_structure import ScriptStructureValidator

    return (ScriptStructureValidator, DialogueVoiceValidator)


def _reference_validators() -> tuple[type[Any], ...]:
    """Import visual-development validators lazily."""
    from film_pipeline.validation.impl.reference_usability import (
        ReferenceUsabilityValidator,
    )

    return (ReferenceUsabilityValidator,)


def _gen_planning_validators() -> tuple[type[Any], ...]:
    """Import gen-planning validators lazily."""
    from film_pipeline.validation.impl.prompt_readiness import PromptReadinessValidator

    return (PromptReadinessValidator,)


def _shot_bible_validators() -> tuple[type[Any], ...]:
    """Import shot-bible validators lazily."""
    from film_pipeline.validation.impl.scene_continuity import SceneContinuityValidator

    return (SceneContinuityValidator,)


def _assembly_validators() -> tuple[type[Any], ...]:
    """Import post/assembly validators lazily."""
    from film_pipeline.validation.impl.assembly import AssemblyValidator

    return (AssemblyValidator,)


def _delivery_validators() -> tuple[type[Any], ...]:
    """Import delivery-phase validators lazily."""
    from film_pipeline.validation.impl.delivery_completeness import (
        DeliveryCompletenessValidator,
    )

    return (DeliveryCompletenessValidator,)


def _latest_or_first(store: ArtifactStore, project_id: str, fp: FilmPhase, artifact_id: str) -> Any:
    """Load the artifact's latest version (v1 probe when absent); None on failure."""
    version = max(1, store.latest_version(project_id, fp.value, artifact_id))
    return _load_artifact(store, project_id, fp, artifact_id, version)


def _live_validator_specs(
    rt: Any, store: ArtifactStore, project_id: str, fp: FilmPhase
) -> list[_PhaseSpec]:
    """Build the ordered phase→(loader, validators) table for one live run."""
    return [
        _PhaseSpec(
            phases=("script",),
            load=lambda: _latest_or_first(store, project_id, fp, "script"),
            validators=_script_validators,
        ),
        _PhaseSpec(
            phases=("visual_dev",),
            load=lambda: _load_latest_reference_index(rt, project_id, rt.get_project(project_id)),
            validators=_reference_validators,
        ),
        _PhaseSpec(
            phases=("gen_planning",),
            load=lambda: _latest_or_first(store, project_id, fp, "prompt_registry"),
            validators=_gen_planning_validators,
        ),
        _PhaseSpec(
            phases=("shot_bible",),
            load=lambda: _latest_or_first(store, project_id, fp, "shot_bible"),
            validators=_shot_bible_validators,
        ),
        _PhaseSpec(
            phases=("post", "assembly"),
            load=lambda: _latest_or_first(store, project_id, fp, "assembly_manifest"),
            validators=_assembly_validators,
        ),
        _PhaseSpec(
            phases=("delivery",),
            load=lambda: _latest_or_first(store, project_id, fp, "delivery_package"),
            validators=_delivery_validators,
        ),
    ]


def _run_live_validators(
    rt: Any, store: ArtifactStore, project_id: str, fp: FilmPhase, phase_str: str
) -> list[dict[str, object]]:
    """Run the phase-appropriate validators live against stored artifacts."""
    reports: list[dict[str, object]] = []
    for spec in _live_validator_specs(rt, store, project_id, fp):
        if phase_str not in spec.phases:
            continue
        art_data = spec.load()
        if art_data is None:
            continue
        for vcls in spec.validators():
            reports.append(_report_summary(vcls().run(art_data)))
    return reports


def _save_report(
    store: ArtifactStore, report: ValidationReport, project_id: str, fp: FilmPhase
) -> str:
    """Persist a ValidationReport as a candidate artifact and return its ref."""
    from datetime import UTC, datetime

    from film_pipeline.schemas.artifact import ArtifactMetadata
    from film_pipeline.schemas.base import ArtifactStatus, ArtifactType

    meta = ArtifactMetadata(
        artifact_id="validation_report",
        artifact_type=ArtifactType.VALIDATION_REPORT,
        project_id=project_id,
        phase=fp,
        version=1,
        status=ArtifactStatus.CANDIDATE,
        created_by="mcp.run_validation",
        created_at=datetime.now(UTC),
    )
    return store.save(report, meta).to_string()


def _run_validators_saving_reports(
    store: ArtifactStore,
    project_id: str,
    fp: FilmPhase,
    validators: tuple[type[Any], ...],
    art_data: Any,
) -> tuple[list[dict[str, object]], list[str]]:
    """Run validators over one artifact, returning summaries with saved refs."""
    reports: list[dict[str, object]] = []
    saved_refs: list[str] = []
    for vcls in validators:
        report = vcls().run(art_data)
        reports.append(_report_summary(report))
        saved_refs.append(_save_report(store, report, project_id, fp))
    return reports, saved_refs


def _validate_visual_dev(
    rt: Any,
    store: ArtifactStore,
    project_id: str,
    fp: FilmPhase,
    state: dict[str, object],
) -> tuple[list[dict[str, object]], list[str]]:
    """Validate the latest reference index when one exists."""
    art_data = _load_latest_reference_index(rt, project_id, state)
    if art_data is None:
        return [], []
    return _run_validators_saving_reports(store, project_id, fp, _reference_validators(), art_data)


def _validate_script(
    store: ArtifactStore, project_id: str, fp: FilmPhase
) -> tuple[list[dict[str, object]], list[str]]:
    """Validate the versioned script when one exists."""
    try:
        version = max(1, store.latest_version(project_id, fp.value, "script"))
        art_data = store.load(project_id, fp, "script", version)
    except (FileNotFoundError, ValueError):
        return [], []
    return _run_validators_saving_reports(store, project_id, fp, _script_validators(), art_data)


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


def _record_validation_results(
    rt: Any,
    project_id: str,
    active: dict[str, Any],
    reports: list[dict[str, object]],
    saved_refs: list[str],
) -> None:
    """Write validation outcomes into project state and persist them."""
    active["_validation_reports"] = reports
    active.setdefault("validation_refs", []).extend(saved_refs)
    rt.projects[project_id] = active
    rt._persist_project_state(project_id)


async def run_validation(args: dict[str, object]) -> dict[str, object]:
    """Run validators for the current phase and persist ValidationReport."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _no_active_project()
    project_id = str(active["project_id"])
    phase_str = str(active.get("current_phase", "visual_dev"))
    store = _services(rt).artifact_store

    fp = _parse_phase(phase_str)
    if fp is None:
        return _error(f"Unknown phase: {phase_str}")

    reports: list[dict[str, object]] = []
    saved_refs: list[str] = []

    try:
        if phase_str == "visual_dev":
            reports, saved_refs = _validate_visual_dev(rt, store, project_id, fp, active)
        elif phase_str == "script":
            reports, saved_refs = _validate_script(store, project_id, fp)
    except Exception as exc:
        return _error(f"Validation run failed: {exc}")

    if not reports:
        return _ok(message="No validators found for this phase.")
    _record_validation_results(rt, project_id, active, reports, saved_refs)
    return _ok(phase=phase_str, reports=reports, saved_refs=saved_refs)


async def get_validation_report(args: dict[str, object]) -> dict[str, object]:
    """Return validation reports for the active project's current phase.

    Reads from stored ``_validation_reports`` in project state (populated
    by the QC node). Falls back to live validator runs if no stored reports.
    """
    rt = tools_pkg.get_runtime()
    resolved = _require_project(args, rt)
    if resolved is None:
        return _no_active_project()
    project_id, state = resolved

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

    fp = _parse_phase(phase_str)
    if fp is None:
        return _error(f"Unknown phase: {phase_str}")

    store = _services(rt).artifact_store
    return _ok(
        phase=phase_str,
        reports=_run_live_validators(rt, store, project_id, fp, phase_str),
        source="live",
    )


async def list_validation_issues(args: dict[str, object]) -> dict[str, object]:
    """List all validation issues for the active project's current phase.

    Reads from stored ``issues`` in project state (populated by QC node).
    """
    rt = tools_pkg.get_runtime()
    resolved = _require_project(args, rt)
    if resolved is None:
        return _no_active_project()
    _project_id, state = resolved

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
