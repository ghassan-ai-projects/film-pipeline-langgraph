"""Bounded repair loop — re-run the current phase's agent under convergence control.

After three repair rounds without resolution the loop marks the phase stalled
and returns control to the human gate instead of cycling forever.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from film_pipeline.orchestration.nodes._agent import _save_artifact
from film_pipeline.orchestration.nodes.generation import generation_node
from film_pipeline.orchestration.nodes.prep import (
    constitution_node,
    development_node,
    intake_node,
    script_node,
)
from film_pipeline.orchestration.nodes.qc import qc_node
from film_pipeline.orchestration.nodes.visual import (
    gen_planning_node,
    shot_bible_node,
    visual_dev_node,
)
from film_pipeline.orchestration.nodes.wrapup import delivery_node, post_node

if TYPE_CHECKING:
    from film_pipeline.schemas.repair import (
        GlobalRepairIssue,
        RepairFeedback,
        RowRepairInstruction,
    )


# ── Phase node registry (for repair routing) ────────────────────────────

_PHASE_NODES: dict[str, Any] = {
    "intake": intake_node,
    "constitution": constitution_node,
    "development": development_node,
    "script": script_node,
    "visual_dev": visual_dev_node,
    "shot_bible": shot_bible_node,
    "gen_planning": gen_planning_node,
    "generation": generation_node,
    "qc": qc_node,
    "post": post_node,
    "delivery": delivery_node,
}


def _start_round(
    state: dict[str, Any], phase: str
) -> tuple[int, dict[str, Any], dict[str, Any] | None]:
    """Advance convergence once; return (round_num, convergence_update, stall_update).

    ``increment_convergence_round`` must run exactly once per repair round,
    before the stall check, so ``phase_fn`` and the returned update agree.
    """
    from film_pipeline.orchestration.orchestrator_state import (
        get_convergence,
        increment_convergence_round,
        is_stalled,
        mark_stalled,
    )

    # Track repair attempts (on the shared state so phase_fn sees the round,
    # and returned explicitly so the update survives the node boundary).
    round_num = increment_convergence_round(state, phase)
    convergence_update = get_convergence(state)

    if is_stalled(state, phase, max_rounds=3):
        mark_stalled(state, phase, f"Repair failed after {round_num} rounds.")
        return (
            round_num,
            convergence_update,
            {
                "_orchestrator__convergence": get_convergence(state),
                "_stalled_phase": phase,
            },
        )
    return round_num, convergence_update, None


def _classify_findings(
    issues: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, str]]], list[GlobalRepairIssue]]:
    """Split blocking+warning findings into row-keyed issues and global issues."""
    from film_pipeline.schemas.repair import GlobalRepairIssue

    blocking = [i for i in issues if i.get("severity") == "blocking"]
    all_findings = blocking + [i for i in issues if i.get("severity") == "warning"]

    row_issues: dict[str, list[dict[str, str]]] = {}
    global_issues: list[GlobalRepairIssue] = []

    for finding in all_findings:
        shot_id = str(finding.get("shot_id", finding.get("affected_shot", "")))
        if shot_id:
            row_issues.setdefault(shot_id, []).append(
                {
                    "code": str(finding.get("code", "?")),
                    "field": str(finding.get("field", finding.get("affected_field", ""))),
                    "message": str(finding.get("message", "")),
                    "recommended_action": str(
                        finding.get("suggestion", finding.get("recommended_action", ""))
                    ),
                }
            )
        else:
            global_issues.append(
                GlobalRepairIssue(
                    code=str(finding.get("code", "?")),
                    message=str(finding.get("message", "")),
                    recommended_action=str(finding.get("suggestion", "")),
                )
            )
    return row_issues, global_issues


def _build_row_instructions(
    row_issues: dict[str, list[dict[str, str]]],
) -> list[RowRepairInstruction]:
    """Materialize per-row repair instructions that preserve unlisted fields."""
    from film_pipeline.schemas.repair import RowRepairInstruction

    failed_rows: list[RowRepairInstruction] = []
    for sid, issue_list in row_issues.items():
        failed_rows.append(
            RowRepairInstruction(
                shot_id=sid,
                issues=issue_list,
                preserve_other_fields=True,
            )
        )
    return failed_rows


def _build_repair_feedback(
    state: dict[str, Any],
    phase: str,
    round_num: int,
    row_issues: dict[str, list[dict[str, str]]],
    global_issues: list[GlobalRepairIssue],
    passed_ids: list[str],
) -> RepairFeedback:
    """Assemble the structured RepairFeedback for this repair round."""
    from film_pipeline.schemas.repair import RepairFeedback

    return RepairFeedback(
        repair_id=f"repair:{phase}:r{round_num}",
        phase=phase,
        round=round_num,
        project_id=str(state.get("project_id", "")),
        failed_rows=_build_row_instructions(row_issues),
        passed_row_ids=passed_ids,
        global_issues=global_issues,
        previous_artifact_ref=str(state.get("shot_matrix_ref", "")),
        convergence_round=round_num,
    )


def _persist_feedback(
    state: dict[str, Any],
    feedback: RepairFeedback,
    phase: str,
) -> None:
    """Attach feedback to the caller's state dict ahead of the phase re-run."""
    # Persist as artifact so the agent can load structured data
    feedback_ref = _save_artifact(
        state,
        feedback,
        f"repair_feedback_{phase}",
        phase,
        artifact_type="script",
    )
    if feedback_ref:
        state["repair_feedback_ref"] = feedback_ref

    # Also inject the rendered context for direct use (backward compat)
    state["_repair_feedback"] = feedback.to_agent_context()


def repair_phase_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generic repair: re-run the current phase's agent to fix issues.

    Checks convergence tracking — after 3 repair rounds without resolution,
    marks the phase as stalled and returns to human.

    Builds structured ``RepairFeedback`` (saved as artifact) so agents
    know exactly which rows to fix/preserve instead of guessing from text.
    """
    # A revision requested after a restart may have no resumable LangGraph
    # interrupt. The graph entry route marks that recovery case explicitly;
    # materialize the same revision update that await_approval would have
    # produced before entering the normal bounded repair loop.
    revision_update: dict[str, Any] = {}
    if state.get("_resume_to_repair"):
        from film_pipeline.orchestration.nodes.approval import request_revision_node
        from film_pipeline.orchestration.state_schema import merge_issues

        revision_update = request_revision_node(state)
        existing_issues = list(state.get("issues", []) or [])
        state = dict(state)
        state.update(revision_update)
        state["issues"] = merge_issues(existing_issues, revision_update.get("issues", []))

    phase = str(state.get("current_phase", ""))
    phase_fn = _PHASE_NODES.get(phase)
    if phase_fn is None:
        return {
            "issues": [
                {
                    "severity": "warning",
                    "code": "no_repair_handler",
                    "message": f"No repair handler for phase '{phase}'.",
                }
            ]
        }

    round_num, convergence_update, stall_update = _start_round(state, phase)
    if stall_update:
        return stall_update

    passed_ids: list[str] = []
    row_issues, global_issues = _classify_findings(state.get("issues", []))
    feedback = _build_repair_feedback(
        state, phase, round_num, row_issues, global_issues, passed_ids
    )
    _persist_feedback(state, feedback, phase)

    # Re-run the phase node — gates will re-validate. Carry the convergence
    # counter into the returned update so repair rounds are durable.
    result = cast(dict[str, Any], phase_fn(state))
    result.setdefault("_orchestrator__convergence", convergence_update)
    if revision_update.get("issues"):
        result["issues"] = list(revision_update["issues"]) + list(result.get("issues", []))
    if "_orchestrator__pending_revisions" in revision_update:
        result["_orchestrator__pending_revisions"] = revision_update[
            "_orchestrator__pending_revisions"
        ]
    result["_resume_to_repair"] = False
    return result
