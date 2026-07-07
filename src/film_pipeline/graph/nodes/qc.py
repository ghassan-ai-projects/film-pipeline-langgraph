"""QC phase node and validator-runner helpers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from film_pipeline.graph.nodes._agent import (
    _propagate_side_effects,
    _run_agent,
    _save_artifact,
)
from film_pipeline.graph.nodes._context import (
    _get_template_registry,
)
from film_pipeline.graph.nodes._shared import (
    _get_services,
    _is_new_issue,
    _is_new_ref,
    _phase_gate_updates,
)


def qc_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state
    gate_updates = _phase_gate_updates(new_state, phase="qc", gate="qc")
    new_state.update(gate_updates)

    # Run validators against upstream artifacts FIRST
    _run_validators(new_state)

    # ── Emit matrix patch from validator findings ────────────────────────
    pending_updates = new_state.pop("_pending_row_updates", [])
    shot_matrix_ref = str(new_state.get("shot_matrix_ref", ""))
    if pending_updates and shot_matrix_ref:
        from film_pipeline.schemas.matrix_patch import MatrixPatch

        patch = MatrixPatch(
            patch_id=f"qc_{new_state.get('project_id', '')}",
            matrix_ref=shot_matrix_ref,
            phase="qc",
            reason="QC validators produced per-row findings — updating status and validation refs.",
            updates=pending_updates,
            created_by_agent="clip-validator",
        )
        patch_ref = _save_artifact(
            new_state,
            patch,
            "matrix_patch_qc",
            "qc",
            artifact_type="consensus_report",
        )
        if patch_ref:
            new_state["qc_patch_ref"] = patch_ref
            new_state.setdefault("artifact_refs", []).append(patch_ref)

    # Then synthesize their findings into a unified QC report
    result = _run_agent(
        new_state,
        agent_id="clip-validator",
        phase="qc",
        task=(
            "Synthesize all validator reports into a unified QC consensus: "
            "identify agreement areas, resolve conflicts, produce weighted "
            "pass/fail/block recommendation with actionable feedback."
        ),
    )
    report = result.get("consensus_report")
    if report is not None:
        ref = _save_artifact(new_state, report, "consensus_report", "qc")
        if ref:
            new_state["consensus_report_ref"] = ref
            new_state.setdefault("artifact_refs", []).append(ref)

    # Compute partial update from before/after diff
    updates: dict[str, Any] = dict(gate_updates)
    new_refs = [r for r in (new_state.get("artifact_refs", []) or []) if _is_new_ref(r, original)]
    if new_refs:
        updates["artifact_refs"] = new_refs
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    for key in ("consensus_report_ref", "qc_patch_ref"):
        val = new_state.get(key)
        if val:
            updates[key] = val
    _propagate_side_effects(new_state, updates, state)
    return updates


def _run_validators(state: dict[str, Any]) -> None:
    """Run validators against current-phase artifacts.

    Blocking findings are added to ``state["issues"]``, which prevents
    phase advancement via ``compute_actions()``.

    For the ``qc`` phase, validators inspect artifacts from all upstream
    phases (script, visual_dev, etc.) so that the QC node produces a
    comprehensive validation report.
    """
    services = _get_services(state)
    if services is None:
        return

    from film_pipeline.schemas._base import FilmPhase

    store = services.artifact_store
    phase = str(state.get("current_phase", ""))
    project_id = str(state.get("project_id", ""))

    # Determine which phases to scan for artifacts.
    if phase == "qc":
        load_phases: list[FilmPhase] = [
            FilmPhase("intake"),
            FilmPhase("constitution"),
            FilmPhase("development"),
            FilmPhase("script"),
            FilmPhase("visual_dev"),
            FilmPhase("shot_bible"),
            FilmPhase("gen_planning"),
        ]
    else:
        load_phases = [FilmPhase(phase)]

    # Collect artifacts by trying each upstream phase.
    artifact_data: dict[str, Any] = {}
    artifact_refs = state.get("artifact_refs", [])
    for ref_str in artifact_refs:
        ref_str = str(ref_str)
        if ":" not in ref_str:
            continue
        parts = ref_str.split(":")
        artifact_id = parts[1] if len(parts) > 1 else ref_str
        version_str = parts[2] if len(parts) > 2 else "1"
        version = int(version_str.lstrip("v"))
        for fp in load_phases:
            try:
                artifact_data[artifact_id] = store.load(project_id, fp, artifact_id, version)
                break
            except (FileNotFoundError, ValueError):
                continue

    issues: list[dict[str, Any]] = list(state.get("issues", []))

    # --- Phase-specific validator dispatch ---

    if phase in ("script", "qc") and artifact_data:
        _run_script_validators(artifact_data, issues, state, services)

    if phase in ("visual_dev", "qc") and artifact_data:
        _run_reference_validators(artifact_data, issues, state, services)

    if phase in ("gen_planning", "qc") and artifact_data:
        _run_prompt_validators(artifact_data, issues, state, services)

    if phase in ("shot_bible", "qc") and artifact_data:
        _run_continuity_validators(artifact_data, issues, state, services)

    if phase in ("post", "assembly", "qc") and artifact_data:
        _run_assembly_validators(artifact_data, issues, state, services)

    if phase == "delivery" and artifact_data:
        _run_delivery_validators(artifact_data, issues, state, services)

    state["issues"] = issues

    # --- Build consensus report when multiple validators ran ----------
    _build_consensus_if_needed(state, phase)


def _build_consensus_if_needed(state: dict[str, Any], phase: str) -> None:
    """Build a consensus report when multiple validators produced reports."""
    reports = state.get("_validation_reports", [])
    if len(reports) < 2:
        return

    from film_pipeline.validation.consensus import ConsensusBuilder

    artifact_refs: list[str] = state.get("artifact_refs", [])

    try:
        consensus = ConsensusBuilder().build(reports, artifact_refs)
    except Exception:
        return

    # Save consensus report as an artifact
    ref = _save_artifact(state, consensus, "consensus_report", phase)
    if ref:
        state["consensus_report_ref"] = ref
        state.setdefault("artifact_refs", []).append(ref)


def _pick_artifact(
    artifact_data: dict[str, Any],
    *artifact_ids: str,
) -> dict[str, Any] | None:
    """Return the first loaded artifact matching the given ids.

    Validators are written against one specific artifact shape; feeding them
    an arbitrary artifact produces false blocking findings (e.g. the script
    validator reporting "no scenes" when handed a project profile).
    """
    for artifact_id in artifact_ids:
        candidate = artifact_data.get(artifact_id)
        if isinstance(candidate, dict):
            return candidate
    return None


def _run_script_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run the two script-phase validators against loaded artifacts."""
    from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
    from film_pipeline.validation.impl.script_structure import ScriptStructureValidator

    artifact = _pick_artifact(artifact_data, "script", "scene_list")
    if artifact is None:
        return
    for vcls in (ScriptStructureValidator, DialogueVoiceValidator):
        try:
            instance = vcls()
            instance.set_services(
                adapter=getattr(services.prompt_runner, "model_adapter", None),
                router=getattr(services.prompt_runner, "model_router", None),
                template_registry=_get_template_registry(),
            )
            report = instance.run(artifact, context=state)
        except Exception:
            continue
        _append_validator_report(report, issues, state)


def _run_reference_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run reference usability validator against visual_dev artifacts."""
    from film_pipeline.validation.impl.reference_usability import ReferenceUsabilityValidator

    artifact = _pick_artifact(artifact_data, "reference_index")
    if artifact is None:
        return
    try:
        instance = ReferenceUsabilityValidator()
        instance.set_services(
            adapter=getattr(services.prompt_runner, "model_adapter", None),
            router=getattr(services.prompt_runner, "model_router", None),
        )
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_prompt_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run prompt readiness validator against gen_planning artifacts."""
    from film_pipeline.validation.impl.prompt_readiness import PromptReadinessValidator

    artifact = _pick_artifact(artifact_data, "prompt_registry", "execution_brief")
    if artifact is None:
        return
    try:
        instance = PromptReadinessValidator()
        instance.set_services(
            adapter=getattr(services.prompt_runner, "model_adapter", None),
            router=getattr(services.prompt_runner, "model_router", None),
        )
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_continuity_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run scene continuity validator against shot_bible artifacts."""
    from film_pipeline.validation.impl.scene_continuity import SceneContinuityValidator

    artifact = _pick_artifact(artifact_data, "shot_matrix", "shot_bible")
    if artifact is None:
        return
    if "shots" not in artifact and isinstance(artifact.get("rows"), list):
        # The shot matrix stores per-shot rows under "rows"; the continuity
        # validator reads "shots".
        artifact = {**artifact, "shots": artifact["rows"]}
    try:
        instance = SceneContinuityValidator()
        instance.set_services(
            adapter=getattr(services.prompt_runner, "model_adapter", None),
            router=getattr(services.prompt_runner, "model_router", None),
        )
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_assembly_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run assembly validator against post/assembly artifacts."""
    from film_pipeline.validation.impl.assembly import AssemblyValidator

    artifact = _pick_artifact(artifact_data, "assembly_manifest", "review_cut", "final_cut")
    if artifact is None:
        return
    try:
        instance = AssemblyValidator()
        instance.set_services(
            adapter=getattr(services.prompt_runner, "model_adapter", None),
            router=getattr(services.prompt_runner, "model_router", None),
        )
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _run_delivery_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run delivery completeness validator against delivery artifacts."""
    from film_pipeline.validation.impl.delivery_completeness import (
        DeliveryCompletenessValidator,
    )

    artifact = _pick_artifact(artifact_data, "delivery_manifest", "delivery_package")
    if artifact is None:
        return
    try:
        instance = DeliveryCompletenessValidator()
        instance.set_services(
            adapter=getattr(services.prompt_runner, "model_adapter", None),
            router=getattr(services.prompt_runner, "model_router", None),
        )
        report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


def _append_validator_report(
    report: Any,
    issues: list[dict[str, Any]],
    state: dict[str, Any],
) -> None:
    """Append a validator report's findings to issues and state."""
    reports = state.setdefault("_validation_reports", [])
    reports.append(report.model_dump())

    for bi in report.blocking_issues:
        issues.append(
            {
                "issue_id": f"val:{report.validator_id}:{bi.code}",
                "severity": "blocking",
                "code": bi.code,
                "message": bi.message,
                "validator_id": report.validator_id,
            }
        )

    for w in report.warnings:
        issues.append(
            {
                "issue_id": f"val:{report.validator_id}:{w.code}",
                "severity": "warning",
                "code": w.code,
                "message": w.message,
                "validator_id": report.validator_id,
            }
        )

    # ── Track per-row findings for matrix patch emission ──────────────
    from film_pipeline.schemas.matrix_patch import MatrixRowUpdate

    pending: list[Any] = state.setdefault("_pending_row_updates", [])
    for finding in report.blocking_issues + report.warnings:
        shot_id = getattr(finding, "affected_shot", None)
        if shot_id:
            pending.append(
                MatrixRowUpdate(
                    shot_id=str(shot_id),
                    append={"validation_refs": [report.validator_id]},
                    set={
                        "status": "failed"
                        if getattr(finding, "severity", "") == "blocking"
                        else "validated",
                    },
                )
            )
