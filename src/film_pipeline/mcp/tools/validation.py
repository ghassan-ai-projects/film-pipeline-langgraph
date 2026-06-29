"""Validation run, report, and issue-listing tools."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg

from .helpers import (
    _active_project_id,
    _error,
    _load_artifact,
    _load_latest_reference_index,
    _ok,
    _report_summary,
    _services,
)


async def run_validation(args: dict[str, object]) -> dict[str, object]:
    """Run validators for the current phase and persist ValidationReport."""
    rt = tools_pkg.get_runtime()
    active = rt.get_active()
    if not active:
        return _error("No active project.")
    project_id = str(active["project_id"])
    phase_str = str(active.get("current_phase", "visual_dev"))
    store = _services(rt).artifact_store

    try:
        from film_pipeline.schemas._base import FilmPhase

        fp = FilmPhase(phase_str)
    except ValueError:
        return _error(f"Unknown phase: {phase_str}")

    reports: list[dict[str, object]] = []
    saved_refs: list[str] = []

    try:
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType
        from film_pipeline.schemas.artifact import ArtifactMetadata

        if phase_str == "visual_dev":
            art_data = _load_latest_reference_index(rt, project_id, active)
            if art_data is not None:
                from film_pipeline.validation.impl.reference_usability import (
                    ReferenceUsabilityValidator,
                )

                validator = ReferenceUsabilityValidator()
                report = validator.run(art_data)
                reports.append(_report_summary(report))
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
                ref = store.save(report, meta)
                saved_refs.append(ref)

        elif phase_str == "script":
            try:
                art_data = store.load(project_id, fp, "script", 1)
            except (FileNotFoundError, ValueError):
                art_data = None
            if art_data is not None:
                from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
                from film_pipeline.validation.impl.script_structure import ScriptStructureValidator

                for vcls in (ScriptStructureValidator, DialogueVoiceValidator):
                    validator = vcls()  # type: ignore[assignment]
                    report = validator.run(art_data)
                    reports.append(_report_summary(report))
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
                    ref = store.save(report, meta)
                    saved_refs.append(ref)
    except Exception as exc:
        return _error(f"Validation run failed: {exc}")

    if not reports:
        return _ok(message="No validators found for this phase.")
    active["_validation_reports"] = reports
    active.setdefault("validation_refs", []).extend(saved_refs)
    rt.projects[project_id] = active
    rt._persist_project_state(project_id)
    return _ok(phase=phase_str, reports=reports, saved_refs=saved_refs)


async def get_validation_report(args: dict[str, object]) -> dict[str, object]:
    """Return validation reports for the active project's current phase.

    Reads from stored ``_validation_reports`` in project state (populated
    by the QC node). Falls back to live validator runs if no stored reports.
    """
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    state = rt.get_project(project_id)
    if state is None:
        return _error("No active project.")

    # Check stored reports first (from QC node) — works even without a
    # current phase because the data is already persisted in state.
    stored = state.get("_validation_reports")
    if stored and isinstance(stored, list):
        return _ok(
            phase=str(state.get("current_phase", "")),
            reports=list(stored),
            source="qc_node",
            message=f"{len(stored)} validation report(s) from QC node.",
        )

    phase_str = str(state.get("current_phase", ""))
    if not phase_str:
        return _error("No active phase to validate (and no stored reports).")

    # Fallback: run validators live
    from film_pipeline.schemas._base import FilmPhase

    try:
        fp = FilmPhase(phase_str)
    except ValueError:
        return _error(f"Unknown phase: {phase_str}")

    reports: list[dict[str, object]] = []
    store = _services(rt).artifact_store

    # --- Phase-specific validator dispatch ---

    if phase_str == "script":
        art_data = _load_artifact(store, project_id, fp, "script", 1)
        if art_data is not None:
            from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
            from film_pipeline.validation.impl.script_structure import ScriptStructureValidator

            for vcls in (ScriptStructureValidator, DialogueVoiceValidator):
                validator = vcls()
                report = validator.run(art_data)
                reports.append(_report_summary(report))

    elif phase_str == "visual_dev":
        art_data = _load_latest_reference_index(rt, project_id, state)
        if art_data is not None:
            from film_pipeline.validation.impl.reference_usability import (
                ReferenceUsabilityValidator,
            )

            ref_validator = ReferenceUsabilityValidator()
            report = ref_validator.run(art_data)
            reports.append(_report_summary(report))

    elif phase_str == "gen_planning":
        art_data = _load_artifact(store, project_id, fp, "prompt_registry", 1)
        if art_data is not None:
            from film_pipeline.validation.impl.prompt_readiness import PromptReadinessValidator

            pr_validator = PromptReadinessValidator()
            report = pr_validator.run(art_data)
            reports.append(_report_summary(report))

    elif phase_str == "shot_bible":
        art_data = _load_artifact(store, project_id, fp, "shot_bible", 1)
        if art_data is not None:
            from film_pipeline.validation.impl.scene_continuity import SceneContinuityValidator

            sc_validator = SceneContinuityValidator()
            report = sc_validator.run(art_data)
            reports.append(_report_summary(report))

    elif phase_str in ("post", "assembly"):
        art_data = _load_artifact(store, project_id, fp, "assembly_manifest", 1)
        if art_data is not None:
            from film_pipeline.validation.impl.assembly import AssemblyValidator

            asm_validator = AssemblyValidator()
            report = asm_validator.run(art_data)
            reports.append(_report_summary(report))

    elif phase_str == "delivery":
        art_data = _load_artifact(store, project_id, fp, "delivery_package", 1)
        if art_data is not None:
            from film_pipeline.validation.impl.delivery_completeness import (
                DeliveryCompletenessValidator,
            )

            dc_validator = DeliveryCompletenessValidator()
            report = dc_validator.run(art_data)
            reports.append(_report_summary(report))

    return _ok(phase=phase_str, reports=reports, source="live")


async def list_validation_issues(args: dict[str, object]) -> dict[str, object]:
    """List all validation issues for the active project's current phase.

    Reads from stored ``issues`` in project state (populated by QC node).
    """
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    state = rt.get_project(project_id)
    if state is None:
        return _error("No active project.")

    # Read from stored issues first — works even without a current phase.
    stored_issues = state.get("issues", [])
    issues: list[dict[str, object]] = []
    if isinstance(stored_issues, list):
        for issue in stored_issues:
            if isinstance(issue, dict) and "validator_id" in issue:
                issues.append(
                    {
                        "code": str(issue.get("code", "")),
                        "message": str(issue.get("message", "")),
                        "severity": str(issue.get("severity", "")),
                        "validator_id": str(issue.get("validator_id", "")),
                    }
                )

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
