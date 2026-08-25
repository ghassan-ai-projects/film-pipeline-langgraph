"""Approval gate, revision, and repair nodes — the human-in-the-loop control plane."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

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

if TYPE_CHECKING:
    from film_pipeline.schemas.repair import (
        GlobalRepairIssue,
        RepairFeedback,
        RowRepairInstruction,
    )


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


def _count_blocking_issues(state: dict[str, Any]) -> int:
    """Count blocking-severity entries in state's issues (pure read)."""
    issues = state.get("issues", []) or []
    return sum(1 for i in issues if i.get("severity") == "blocking")


def _orchestrator_working_state(state: dict[str, Any]) -> dict[str, Any]:
    """Deep-copied ``_orchestrator__*`` slice of state with defaults ensured."""
    from film_pipeline.graph.orchestrator_state import ensure_orchestrator_state

    working = {
        key: deepcopy(value) for key, value in state.items() if key.startswith("_orchestrator__")
    }
    ensure_orchestrator_state(working)
    return working


def _apply_headless_decision(state: dict[str, Any], stalled: bool) -> dict[str, Any] | None:
    """Apply an autonomous orchestrator decision; ``None`` falls through to the fallback."""
    if stalled:
        return None
    orch_decision = _run_orchestrator_agent(state)
    if orch_decision is None:
        return None
    action = orch_decision.get("action", "escalate")
    if action == "approve":
        return approve_phase_node(state)
    if action == "revise":
        state["_repair_feedback"] = orch_decision.get("feedback", "")
        preserve = orch_decision.get("preserve", [])
        if preserve:
            state["_repair_feedback"] += "\n\nPreserve: " + "; ".join(str(p) for p in preserve)
        return request_revision_node(state)
    # escalate: fall through to clean/buggy fallback below
    return None


def _advisory_recommendation(state: dict[str, Any], stalled: bool) -> dict[str, Any] | None:
    """Run the orchestrator agent for an advisory recommendation; the human decides."""
    if stalled:
        return None
    orch_decision = _run_orchestrator_agent(state)
    if orch_decision is None:
        return None
    return {
        "action": orch_decision.get("action", "escalate"),
        "feedback": orch_decision.get("feedback", ""),
        "preserve": orch_decision.get("preserve", []),
    }


def _build_gate_payload(
    state: dict[str, Any],
    phase: str,
    stalled: bool,
    recommendation: dict[str, Any] | None,
) -> dict[str, Any]:
    """Assemble the interrupt payload shown to the human reviewer (pre-interrupt only)."""
    gate = str(state.get("human_approval_phase", ""))
    blocking_count = _count_blocking_issues(state)

    allowed_actions: list[str] = []
    if blocking_count == 0:
        allowed_actions.append("approve_phase")
    if stalled:
        allowed_actions.append("escalate")
    else:
        allowed_actions.append("request_revision")

    return {
        "project_id": state.get("project_id", ""),
        "phase": phase,
        "gate": gate,
        "artifact_refs": state.get("artifact_refs", []),
        "blocking_issue_count": blocking_count,
        "stalled": stalled,
        "allowed_actions": allowed_actions,
        "recommendation": recommendation,
    }


def _normalize_decision(decision: Any) -> tuple[str, str, dict[str, Any]]:
    """Normalize a resume value into ``(action, note, external_state)``.

    ``external_state`` carries mutations sent via ``Command(resume=...)``;
    empty when the resume value does not bear a dict-shaped ``_external_state``.
    """
    if isinstance(decision, dict):
        external_state = decision.get("_external_state")
        return (
            str(decision.get("action", "")),
            str(decision.get("note", "")),
            external_state if isinstance(external_state, dict) else {},
        )
    if isinstance(decision, str):
        return decision, "", {}
    return "await", "", {}


def _merge_external_fixes(
    state: dict[str, Any],
    state_updates: dict[str, Any],
) -> dict[str, Any]:
    """Merge externally resolved issues into state before the approval guard runs.

    Ordering matters: stale blockers (already fixed outside the graph) would
    otherwise wedge the gate.
    """
    if not state_updates.get("issues"):
        return state
    from film_pipeline.graph.state_schema import merge_issues

    return {
        **state,
        "issues": merge_issues(
            cast("list[dict[str, object]]", state.get("issues", [])),
            cast("list[dict[str, object]]", state_updates["issues"]),
        ),
    }


def _route_decision(
    state: dict[str, Any],
    action: str,
    note: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch a normalized gate decision; unrecognized actions yield bare updates."""
    if action in ("approve", "approve_phase"):
        result = approve_phase_node(state)
        result.update(updates)
        return result
    if action in ("revise", "request_revision"):
        if note:
            state["_revision_note"] = note
        result = request_revision_node(state)
        result.update(updates)
        return result
    return updates


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
        return _apply_headless_decision(state, stalled) or (
            approve_phase_node(state)
            if _count_blocking_issues(state) == 0
            else {"approved": False, "human_approval_required": False}
        )

    # ── Human gate (default) ───────────────────────────────────────────
    # The orchestrator may prepare a recommendation, but the human decides.
    recommendation = _advisory_recommendation(state, stalled)

    from langgraph.types import interrupt

    payload = _build_gate_payload(state, phase, stalled, recommendation)

    decision = interrupt(payload)
    action, note, external_state = _normalize_decision(decision)
    state_updates = _apply_external_state(state, external_state) if external_state else {}
    state = _merge_external_fixes(state, state_updates)
    return _route_decision(state, action, note, state_updates)


def approve_phase_node(state: dict[str, Any]) -> dict[str, Any]:
    """Approve the current phase. Returns a partial state update.

    Returning the full state would re-append every entry of the
    append-only reducer channels (``issues``, ``artifact_refs``, ...), so
    only the keys this node actually changes are returned.
    """
    # ── Guard: reject approval when structural issues exist ──────────
    if _count_blocking_issues(state):
        return {"approved": False, "_approval_blocked_by_issues": True}

    # Promote all candidate refs to approved
    from film_pipeline.graph.orchestrator_state import (
        get_candidate_refs,
        set_approved_ref,
    )

    working = _orchestrator_working_state(state)
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
    from film_pipeline.graph.orchestrator_state import add_revision_request

    working = _orchestrator_working_state(state)
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


def _start_round(
    state: dict[str, Any], phase: str
) -> tuple[int, dict[str, Any], dict[str, Any] | None]:
    """Advance convergence once; return (round_num, convergence_update, stall_update).

    ``increment_convergence_round`` must run exactly once per repair round,
    before the stall check, so ``phase_fn`` and the returned update agree.
    """
    from film_pipeline.graph.orchestrator_state import (
        increment_convergence_round,
        is_stalled,
        mark_stalled,
    )

    # Track repair attempts (on the shared state so phase_fn sees the round,
    # and returned explicitly so the update survives the node boundary).
    round_num = increment_convergence_round(state, phase)
    convergence_update = deepcopy(state.get("_orchestrator__convergence", {}))

    if is_stalled(state, phase, max_rounds=3):
        mark_stalled(state, phase, f"Repair failed after {round_num} rounds.")
        return (
            round_num,
            convergence_update,
            {
                "_orchestrator__convergence": deepcopy(state.get("_orchestrator__convergence", {})),
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
    return result
