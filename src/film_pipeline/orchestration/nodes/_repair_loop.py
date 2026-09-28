"""Bounded repair loop — re-run the current phase's agent under convergence control.

After three repair rounds without resolution the loop marks the phase stalled
and returns control to the human gate instead of cycling forever.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

from film_pipeline.filmspec import blocking_issues
from film_pipeline.orchestration.nodes._agent import _save_artifact
from film_pipeline.orchestration.nodes.generation import generation_node
from film_pipeline.orchestration.nodes.prep import (
    constitution_node,
    development_node,
    intake_node,
    script_node,
)
from film_pipeline.orchestration.nodes.visual import (
    gen_planning_node,
    shot_bible_node,
    visual_dev_node,
)
from film_pipeline.orchestration.nodes.wrapup import delivery_node, post_node
from film_pipeline.orchestration.state_schema import StudioGraphState

if TYPE_CHECKING:
    from film_pipeline.schemas.repair import (
        GlobalRepairIssue,
        RepairFeedback,
        RowRepairInstruction,
    )


class _LazyQcPhaseNode:
    """Stand-in for the QC phase node inside ``_PHASE_NODES``.

    ``_PHASE_NODES`` is built at module import, and resolving the QC row there
    means importing ``subgraphs.qc`` while ``nodes`` is still initialising —
    which is a genuine ``ImportError: partially initialized module`` the moment
    anything imports ``subgraphs.qc`` first, and an
    ``orchestration <-> nodes <-> subgraphs`` cycle either way.

    This defers the import to first use and forwards every call, so the row is
    still *the graph's own node*:

    - ``_PHASE_NODES["qc"] is _PHASE_NODES["qc"]`` (identity, what the parity
      guard checks),
    - calling it runs the same compiled subgraph `build_graph` wires,
    - ``isinstance(x, CompiledStateGraph)`` is False, so
      ``studio._graph_exec._call_phase_node`` needs its own resolution — see
      :func:`resolved_phase_node`, which both callers use.
    """

    _node: Any = None

    def __call__(self, state: dict[str, Any]) -> Any:
        return self.resolve()(state)

    def resolve(self) -> Any:
        if self._node is None:
            from film_pipeline.orchestration.subgraphs.qc import qc_phase_node

            self._node = qc_phase_node()
        return self._node


_QC_PHASE_NODE = _LazyQcPhaseNode()


def resolved_phase_node(phase: str) -> Any:
    """Return the phase's node, resolving a deferred one to its real object.

    ``_PHASE_NODES`` holds ``_LazyQcPhaseNode`` for ``qc``; every consumer that
    needs the underlying callable — or needs to know whether it is a compiled
    subgraph — goes through here rather than reaching into the table.
    """
    node = _PHASE_NODES[phase]
    return node.resolve() if isinstance(node, _LazyQcPhaseNode) else node


# ── Phase node registry (for repair routing) ────────────────────────────
#
# Every phase maps to the *same object* `build_graph` registers for
# `<phase>_node`, so a phase cannot run one implementation on its first pass and
# another on repair. `tests/unit/orchestration/test_graph_manual_path_parity.py`
# asserts that identity for all eleven phases.
#
# `qc_phase_node()` is memoised in `subgraphs.qc`, so this row and
# `studio.graph_factory`'s `add_node("qc_node", ...)` hold the *same* compiled
# object rather than two equal compilations. It is resolved through
# `_qc_phase_node()` for the cycle reason stated there.

_PHASE_NODES: dict[str, Any] = {
    "intake": intake_node,
    "constitution": constitution_node,
    "development": development_node,
    "script": script_node,
    "visual_dev": visual_dev_node,
    "shot_bible": shot_bible_node,
    "gen_planning": gen_planning_node,
    "generation": generation_node,
    # QC's repair pass must run the same object the graph wires for its first
    # pass: the parallel subgraph. `nodes.qc.qc_node` was a second, sequential
    # implementation that did different work (and skipped the matrix patch and
    # consensus steps the subgraph lacked). See
    # `documentation/qc-single-implementation.md` for the decision.
    "qc": _QC_PHASE_NODE,
    "post": post_node,
    "delivery": delivery_node,
}


def _start_round(
    state: StudioGraphState, phase: str
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

    blocking = blocking_issues(issues)
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
    state: Mapping[str, object],
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
    state: StudioGraphState,
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


def repair_phase_node(state: StudioGraphState) -> dict[str, Any]:
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
    revision_update: StudioGraphState = {}
    if state.get("_resume_to_repair"):
        from film_pipeline.orchestration.nodes.approval import request_revision_node
        from film_pipeline.orchestration.state_schema import merge_issues

        revision_update = request_revision_node(state)
        existing_issues = list(state.get("issues", []) or [])
        # `deepcopy` (not `dict(state)`) keeps the declared type: a plain dict
        # copy is not assignable to the TypedDict.
        merged: StudioGraphState = deepcopy(state)
        merged["issues"] = merge_issues(existing_issues, revision_update.get("issues", []))
        state = merged

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
