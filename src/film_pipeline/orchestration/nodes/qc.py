"""QC phase node and validator-runner helpers."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from film_pipeline.orchestration.nodes._agent import (
    _propagate_side_effects,
    _run_agent,
    _save_artifact,
)
from film_pipeline.orchestration.nodes._context import (
    _get_template_registry,
)
from film_pipeline.orchestration.nodes._shared import (
    _is_new_issue,
    _is_new_ref,
    _phase_gate_updates,
)
from film_pipeline.orchestration.services import _get_services

_ValidatorRunner = Callable[
    [dict[str, Any], list[dict[str, Any]], dict[str, Any], Any],
    None,
]

# Ref-valued state keys qc_node copies into its update once validators set them.
_QC_REF_KEYS: tuple[str, ...] = ("consensus_report_ref", "qc_patch_ref")


def qc_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    gate_updates = _phase_gate_updates(new_state, phase="qc", gate="qc")
    new_state.update(gate_updates)

    _run_validators(new_state)
    _emit_matrix_patch_from_findings(new_state)
    _synthesize_consensus_report(new_state)

    updates = _collect_updates(gate_updates, new_state, state, _QC_REF_KEYS)
    _propagate_side_effects(new_state, updates, state)
    return updates


def _collect_updates(
    gate_updates: dict[str, Any],
    new_state: dict[str, Any],
    original: dict[str, Any],
    ref_keys: tuple[str, ...],
) -> dict[str, Any]:
    """Compute the partial update from a before/after diff of the node state."""
    updates: dict[str, Any] = dict(gate_updates)
    new_refs = [r for r in (new_state.get("artifact_refs", []) or []) if _is_new_ref(r, original)]
    if new_refs:
        updates["artifact_refs"] = new_refs
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    for key in ref_keys:
        val = new_state.get(key)
        if val:
            updates[key] = val
    return updates


def _emit_matrix_patch_from_findings(state: dict[str, Any]) -> None:
    """Persist a matrix patch from the per-row findings validators collected."""
    pending_updates = state.pop("_pending_row_updates", [])
    shot_matrix_ref = str(state.get("shot_matrix_ref", ""))
    if pending_updates and shot_matrix_ref:
        from film_pipeline.schemas.matrix_patch import MatrixPatch

        patch = MatrixPatch(
            patch_id=f"qc_{state.get('project_id', '')}",
            matrix_ref=shot_matrix_ref,
            phase="qc",
            reason="QC validators produced per-row findings — updating status and validation refs.",
            updates=pending_updates,
            created_by_agent="clip-validator",
        )
        patch_ref = _save_artifact(
            state,
            patch,
            "matrix_patch_qc",
            "qc",
            artifact_type="consensus_report",
        )
        if patch_ref:
            state["qc_patch_ref"] = patch_ref
            state.setdefault("artifact_refs", []).append(patch_ref)


def _synthesize_consensus_report(state: dict[str, Any]) -> None:
    """Synthesize validator reports into a unified QC consensus artifact."""
    result = _run_agent(
        state,
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
        ref = _save_artifact(state, report, "consensus_report", "qc")
        if ref:
            state["consensus_report_ref"] = ref
            state.setdefault("artifact_refs", []).append(ref)


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

    phase = str(state.get("current_phase", ""))

    artifacts = _collect_artifacts(state, services)

    issues: list[dict[str, Any]] = list(state.get("issues", []))
    _execute_phase_validators(state, artifacts, issues, services)
    state["issues"] = issues

    _build_consensus_if_needed(state, phase)


def _collect_artifacts(state: dict[str, Any], services: Any) -> dict[str, Any]:
    """Load artifacts referenced by ``state["artifact_refs"]`` from their phases."""

    from film_pipeline.schemas.artifact import ArtifactRef
    from film_pipeline.schemas.base import FilmPhase

    store = services.artifact_store
    project_id = str(state.get("project_id", ""))
    artifact_data: dict[str, Any] = {}
    for ref_str in state.get("artifact_refs", []):
        ref_str = str(ref_str)
        try:
            parsed = ArtifactRef.from_string(ref_str)
        except ValueError:
            continue
        try:
            artifact_data[parsed.artifact_id] = store.load(
                project_id, FilmPhase(parsed.phase), parsed.artifact_id, parsed.version
            )
        except (FileNotFoundError, ValueError):
            continue
    return artifact_data


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


def _as_shots_view(artifact: dict[str, Any]) -> dict[str, Any]:
    """Adapt a shot-matrix artifact to the shots view the continuity validator reads.

    The shot matrix stores per-shot rows under "rows"; the continuity
    validator reads "shots".
    """
    if "shots" not in artifact and isinstance(artifact.get("rows"), list):
        return {**artifact, "shots": artifact["rows"]}
    return artifact


def _instantiate_validator(
    vcls: type[Any],
    services: Any,
    *,
    with_templates: bool = False,
) -> Any:
    """Instantiate a validator wired to the model adapter and router."""
    instance = vcls()
    kwargs: dict[str, Any] = {
        "adapter": getattr(services.prompt_runner, "model_adapter", None),
        "router": getattr(services.prompt_runner, "model_router", None),
    }
    if with_templates:
        kwargs["template_registry"] = _get_template_registry()
    instance.set_services(**kwargs)
    return instance


def _validate_artifact(
    vcls: type[Any],
    artifact: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
    *,
    with_templates: bool = False,
    pass_state_as_context: bool = False,
) -> None:
    """Record one validator's findings on an artifact; a failing validator is skipped.

    A validator that cannot instantiate or run must not abort the whole QC
    pass, so its exception is swallowed here (matching every call site).
    """
    try:
        instance = _instantiate_validator(vcls, services, with_templates=with_templates)
        if pass_state_as_context:
            report = instance.run(artifact, context=state)
        else:
            report = instance.run(artifact)
    except Exception:
        return
    _append_validator_report(report, issues, state)


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
        _validate_artifact(
            vcls,
            artifact,
            issues,
            state,
            services,
            with_templates=True,
            pass_state_as_context=True,
        )


def _run_reference_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run reference usability validator against visual_dev artifacts."""
    from film_pipeline.validation.impl.reference_usability import ReferenceUsabilityValidator

    artifact = _pick_artifact(artifact_data, "reference_index")
    if artifact is not None:
        _validate_artifact(ReferenceUsabilityValidator, artifact, issues, state, services)


def _run_prompt_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run prompt readiness validator against gen_planning artifacts."""
    from film_pipeline.validation.impl.prompt_readiness import PromptReadinessValidator

    artifact = _pick_artifact(artifact_data, "prompt_registry", "execution_brief")
    if artifact is not None:
        _validate_artifact(PromptReadinessValidator, artifact, issues, state, services)


def _run_continuity_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run scene continuity validator against shot_bible artifacts."""
    from film_pipeline.validation.impl.scene_continuity import SceneContinuityValidator

    artifact = _pick_artifact(artifact_data, "shot_matrix", "shot_bible")
    if artifact is not None:
        _validate_artifact(
            SceneContinuityValidator,
            _as_shots_view(artifact),
            issues,
            state,
            services,
        )


def _run_assembly_validators(
    artifact_data: dict[str, Any],
    issues: list[dict[str, Any]],
    state: dict[str, Any],
    services: Any,
) -> None:
    """Run assembly validator against post/assembly artifacts."""
    from film_pipeline.validation.impl.assembly import AssemblyValidator

    artifact = _pick_artifact(artifact_data, "assembly_manifest", "review_cut", "final_cut")
    if artifact is not None:
        _validate_artifact(AssemblyValidator, artifact, issues, state, services)


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
    if artifact is not None:
        _validate_artifact(DeliveryCompletenessValidator, artifact, issues, state, services)


_VALIDATOR_RUNNERS: tuple[tuple[set[str], _ValidatorRunner], ...] = (
    ({"script", "qc"}, _run_script_validators),
    ({"visual_dev", "qc"}, _run_reference_validators),
    ({"gen_planning", "qc"}, _run_prompt_validators),
    ({"shot_bible", "qc"}, _run_continuity_validators),
    ({"post", "assembly", "qc"}, _run_assembly_validators),
    ({"delivery"}, _run_delivery_validators),
)


def _execute_phase_validators(
    state: dict[str, Any],
    artifacts: dict[str, Any],
    issues: list[dict[str, Any]],
    services: Any,
) -> None:
    """Run each validator runner whose phase membership contains the current phase."""
    if not artifacts:
        return
    phase = str(state.get("current_phase", ""))
    for phases, runner in _VALIDATOR_RUNNERS:
        if phase in phases:
            runner(artifacts, issues, state, services)


def _append_validator_report(
    report: Any,
    issues: list[dict[str, Any]],
    state: dict[str, Any],
) -> None:
    """Append a validator report's findings to issues and state."""
    reports = state.setdefault("_validation_reports", [])
    reports.append(report.model_dump())

    severities = (
        ("blocking", report.blocking_issues),
        ("warning", report.warnings),
    )
    for severity, findings in severities:
        for finding in findings:
            issues.append(_issue_entry(report, finding, severity))

    _track_matrix_row_updates(state, report)


def _issue_entry(report: Any, finding: Any, severity: str) -> dict[str, Any]:
    """Build one issue dict from a single validator finding."""
    return {
        "issue_id": f"val:{report.validator_id}:{finding.code}",
        "severity": severity,
        "code": finding.code,
        "message": finding.message,
        "validator_id": report.validator_id,
    }


def _track_matrix_row_updates(state: dict[str, Any], report: Any) -> None:
    """Record per-row findings so qc_node can emit a matrix patch."""
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
