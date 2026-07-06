"""Approval gate, revision, and repair nodes — the human-in-the-loop control plane."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, cast

from film_pipeline.graph.nodes._agent import (
    _run_agent,
    _save_artifact,
)
from film_pipeline.graph.nodes._shared import (
    _apply_external_state,
    _get_services,
    _require_human_approval,
)
from film_pipeline.graph.nodes.generation import generation_node
from film_pipeline.graph.nodes.prep import (
    constitution_node,
    development_node,
    intake_node,
    script_node,
)
from film_pipeline.graph.nodes.qc import qc_node
from film_pipeline.graph.nodes.visual import (
    gen_planning_node,
    shot_bible_node,
    visual_dev_node,
)
from film_pipeline.graph.nodes.wrapup import delivery_node, post_node


def _run_orchestrator_agent(state: dict[str, Any]) -> dict[str, Any] | None:
    """Run the orchestrator agent to decide approve/revise/escalate.

    Returns the agent's decision dict or ``None`` if the agent is unavailable
    (no services, no model — fall through to human gate).
    """
    services = _get_services(state)
    if services is None:
        return None

    result = _run_agent(
        state,
        agent_id="orchestrator-agent",
        phase=str(state.get("current_phase", "")),
        task=(
            "Review the phase output against the target runtime and constitution. "
            "Decide: approve (output is sound), revise (give one focused suggestion), "
            "or escalate (stuck or fundamentally wrong)."
        ),
    )
    if result.get("status") in ("no_services", "agent_not_found", "no_impl"):
        return None
    action = result.get("action")
    if action not in ("approve", "revise", "escalate"):
        return None
    return result


def await_approval_node(state: dict[str, Any]) -> dict[str, Any]:
    """Pause the graph for human review. Resumes via Command(resume=decision).

    When ``require_human_approval`` is enabled (the default), the node always
    calls LangGraph's ``interrupt()`` so the human gate cannot be silently
    bypassed. The orchestrator agent may produce a recommendation, but it is
    only advisory and is surfaced inside the interrupt payload.

    In headless / auto-approve mode the orchestrator agent may act
    autonomously; when it is unavailable or escalates, clean phases are
    approved and phases with blocking issues are routed to the bounded repair
    loop.

    Short-circuits when ``approved`` is already ``True`` — the phase node
    auto-approved (e.g. headless/auto-approve profile). The downstream
    ``after_approval`` routing will advance to the next phase.
    """
    if state.get("approved"):
        return {}

    from film_pipeline.graph.orchestrator_state import is_stalled

    phase = str(state.get("current_phase", ""))
    stalled = is_stalled(state, phase)
    require_human = _require_human_approval(state)

    # ── Headless / auto-approve mode ───────────────────────────────────
    if not require_human:
        if not stalled:
            orch_decision = _run_orchestrator_agent(state)
            if orch_decision is not None:
                action = orch_decision.get("action", "escalate")
                if action == "approve":
                    return approve_phase_node(state)
                if action == "revise":
                    state["_repair_feedback"] = orch_decision.get("feedback", "")
                    preserve = orch_decision.get("preserve", [])
                    if preserve:
                        state["_repair_feedback"] += "\n\nPreserve: " + "; ".join(
                            str(p) for p in preserve
                        )
                    return request_revision_node(state)
                # escalate: fall through to clean/buggy fallback below

        issues: list[dict[str, Any]] = state.get("issues", [])
        blocking_count = sum(1 for i in issues if i.get("severity") == "blocking")
        if blocking_count == 0:
            return approve_phase_node(state)
        return {"approved": False, "human_approval_required": False}

    # ── Human gate (default) ───────────────────────────────────────────
    # The orchestrator may prepare a recommendation, but the human decides.
    recommendation: dict[str, Any] | None = None
    if not stalled:
        orch_decision = _run_orchestrator_agent(state)
        if orch_decision is not None:
            recommendation = {
                "action": orch_decision.get("action", "escalate"),
                "feedback": orch_decision.get("feedback", ""),
                "preserve": orch_decision.get("preserve", []),
            }

    from langgraph.types import interrupt

    gate = str(state.get("human_approval_phase", ""))
    issues = state.get("issues", [])
    blocking_count = sum(1 for i in issues if i.get("severity") == "blocking")

    allowed_actions: list[str] = []
    if blocking_count == 0:
        allowed_actions.append("approve_phase")
    if stalled:
        allowed_actions.append("escalate")
    else:
        allowed_actions.append("request_revision")

    payload: dict[str, Any] = {
        "project_id": state.get("project_id", ""),
        "phase": phase,
        "gate": gate,
        "artifact_refs": state.get("artifact_refs", []),
        "blocking_issue_count": blocking_count,
        "stalled": stalled,
        "allowed_actions": allowed_actions,
        "recommendation": recommendation,
    }

    decision = interrupt(payload)
    state_updates: dict[str, Any] = {}

    # Normalize the decision
    if isinstance(decision, dict):
        action = str(decision.get("action", ""))
        note = str(decision.get("note", ""))
        external_state = decision.get("_external_state")
        if isinstance(external_state, dict):
            state_updates = _apply_external_state(state, external_state)
    elif isinstance(decision, str):
        action = decision
        note = ""
    else:
        action = "await"

    if state_updates.get("issues"):
        # Apply externally resolved issues before the approval guard runs so
        # stale blockers (already fixed outside the graph) cannot wedge it.
        from film_pipeline.graph.state_schema import merge_issues

        state = {
            **state,
            "issues": merge_issues(
                cast("list[dict[str, object]]", state.get("issues", [])),
                cast("list[dict[str, object]]", state_updates["issues"]),
            ),
        }

    if action in ("approve", "approve_phase"):
        result = approve_phase_node(state)
        result.update(state_updates)
        return result
    if action in ("revise", "request_revision"):
        if note:
            state["_revision_note"] = note
        result = request_revision_node(state)
        result.update(state_updates)
        return result
    return state_updates


def approve_phase_node(state: dict[str, Any]) -> dict[str, Any]:
    """Approve the current phase. Returns a partial state update.

    Returning the full state would re-append every entry of the
    append-only reducer channels (``issues``, ``artifact_refs``, ...), so
    only the keys this node actually changes are returned.
    """
    # ── Guard: reject approval when structural issues exist ──────────
    issues: list[dict[str, Any]] = state.get("issues", []) or []
    blocking = [i for i in issues if i.get("severity") == "blocking"]
    if blocking:
        return {"approved": False, "_approval_blocked_by_issues": True}

    # Promote all candidate refs to approved
    from film_pipeline.graph.orchestrator_state import (
        ensure_orchestrator_state,
        get_candidate_refs,
        set_approved_ref,
    )

    working = {
        key: deepcopy(value) for key, value in state.items() if key.startswith("_orchestrator__")
    }
    ensure_orchestrator_state(working)
    for family, ref in get_candidate_refs(state).items():
        set_approved_ref(working, family, ref)

    return {
        "approved": True,
        "human_approval_required": False,
        "_approval_blocked_by_issues": False,
        "_orchestrator__approved_refs": working.get("_orchestrator__approved_refs", {}),
    }


def request_revision_node(state: dict[str, Any]) -> dict[str, Any]:
    """Route the current phase to revision. Returns a partial state update."""
    revision_note = str(state.get("_revision_note", ""))
    # Record durable revision request via orchestrator state helpers
    from film_pipeline.graph.orchestrator_state import (
        add_revision_request,
        ensure_orchestrator_state,
    )

    working = {
        key: deepcopy(value) for key, value in state.items() if key.startswith("_orchestrator__")
    }
    ensure_orchestrator_state(working)
    artifact_refs = list(state.get("artifact_refs", []) or [])
    add_revision_request(working, artifact_refs, note="Human requested revision.")

    return {
        "approved": False,
        "human_approval_required": False,
        "_revision_note": "",
        "issues": [
            {
                "issue_id": "rev",
                "severity": "warning",
                "code": "REVISION_REQUESTED",
                "message": revision_note or "Human requested revision.",
            }
        ],
        "_orchestrator__pending_revisions": working.get("_orchestrator__pending_revisions", []),
    }


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


def repair_phase_node(state: dict[str, Any]) -> dict[str, Any]:
    """Generic repair: re-run the current phase's agent to fix issues.

    Checks convergence tracking — after 3 repair rounds without resolution,
    marks the phase as stalled and returns to human.

    Builds structured ``RepairFeedback`` (saved as artifact) so agents
    know exactly which rows to fix/preserve instead of guessing from text.
    """
    from film_pipeline.graph.orchestrator_state import (
        increment_convergence_round,
        is_stalled,
        mark_stalled,
    )
    from film_pipeline.schemas.repair import (
        GlobalRepairIssue,
        RepairFeedback,
        RowRepairInstruction,
    )

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

    # Track repair attempts (on the shared state so phase_fn sees the round,
    # and returned explicitly so the update survives the node boundary).
    round_num = increment_convergence_round(state, phase)
    convergence_update = deepcopy(state.get("_orchestrator__convergence", {}))

    if is_stalled(state, phase, max_rounds=3):
        mark_stalled(state, phase, f"Repair failed after {round_num} rounds.")
        return {
            "_orchestrator__convergence": deepcopy(state.get("_orchestrator__convergence", {})),
            "_stalled_phase": phase,
        }

    # ── Build structured repair feedback ──────────────────────────────
    issues: list[dict[str, Any]] = state.get("issues", [])
    blocking = [i for i in issues if i.get("severity") == "blocking"]
    all_findings = blocking + [i for i in issues if i.get("severity") == "warning"]

    # Separate row-level from global issues
    row_issues: dict[str, list[dict[str, str]]] = {}
    global_issues: list[GlobalRepairIssue] = []
    passed_ids: list[str] = []

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

    # Build row instructions
    failed_rows: list[Any] = []
    for sid, issue_list in row_issues.items():
        failed_rows.append(
            RowRepairInstruction(
                shot_id=sid,
                issues=issue_list,
                preserve_other_fields=True,
            )
        )

    # Determine passed rows from patch history
    previous_artifact = str(state.get("shot_matrix_ref", ""))
    feedback = RepairFeedback(
        repair_id=f"repair:{phase}:r{round_num}",
        phase=phase,
        round=round_num,
        project_id=str(state.get("project_id", "")),
        failed_rows=failed_rows,
        passed_row_ids=passed_ids,
        global_issues=global_issues,
        previous_artifact_ref=previous_artifact,
        convergence_round=round_num,
    )

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

    # Re-run the phase node — gates will re-validate. Carry the convergence
    # counter into the returned update so repair rounds are durable.
    result = cast(dict[str, Any], phase_fn(state))
    result.setdefault("_orchestrator__convergence", convergence_update)
    return result
