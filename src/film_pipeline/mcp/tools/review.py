"""Review package generation, approval, and revision tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _active_project_id, _error, _ok, _services

if TYPE_CHECKING:
    from film_pipeline.schemas._base import FilmPhase
    from film_pipeline.schemas.approval import ReviewPackage


def _collect_phase_artifacts(
    store: Any, project_id: str, phase: FilmPhase
) -> list[dict[str, object]]:
    """Summarize the artifacts stored for the reviewed phase."""
    artifacts = store.list_artifacts(project_id, phase)
    return [
        {
            "artifact_id": a.artifact_id,
            "artifact_type": a.artifact_type,
            "phase": str(a.phase.value),
            "version": a.version,
            "status": a.status,
        }
        for a in artifacts
    ]


def _build_review_package(
    state: dict[str, Any],
    phase: FilmPhase,
    phase_label: str,
    artifact_list: list[dict[str, object]],
    router_result: Any,
    blocking_issues: list[dict[str, Any]],
) -> ReviewPackage | None:
    """Build the structured review package; None when generation fails."""
    from film_pipeline.review.generator import ReviewPackageGenerator

    try:
        generator = ReviewPackageGenerator()
        pkg = generator.build(
            project_id=str(state["project_id"]),
            phase=phase,
            summary=f"Review package for {phase_label} phase",
            current_artifacts=cast(list[str], [a["artifact_id"] for a in artifact_list]),
            validation_results=[
                r.get("validator_id", "") for r in state.get("_validation_reports", [])
            ],
            open_issues=[i.get("message", "") for i in blocking_issues],
            orchestrator_recommendation=_build_orchestrator_recommendation(state, router_result),
            has_blocking_issues=len(blocking_issues) > 0,
        )
    except Exception:
        return None
    return pkg


def _blocking_issues(state: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the open issues whose severity is blocking."""
    return [i for i in state.get("issues", []) if i.get("severity") == "blocking"]


async def review_phase_artifacts(args: dict[str, object]) -> dict[str, object]:
    """Build a review package for the current phase with orchestrator recommendations.

    Returns a structured ReviewPackage instead of a plain artifact list.
    The package includes candidate vs approved diffs, validation results,
    open issues, risks, cost impact, and recommended next actions.
    """
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    if project_id is None:
        return _error("No active project.")
    state = rt.get_project(project_id)
    if state is None:
        return _error("No active project.")
    phase = str(args.get("phase", state.get("current_phase", "")))
    if not phase:
        return _error("No phase specified and no active phase.")
    project_id = str(state["project_id"])
    from film_pipeline.schemas._base import FilmPhase

    try:
        fp = FilmPhase(phase)
    except ValueError:
        return _error(f"Unknown phase: {phase}")

    store = _services(rt).artifact_store
    artifact_list = _collect_phase_artifacts(store, project_id, fp)

    # Build a review package using the ReviewPackageGenerator
    from film_pipeline.graph import orchestrator_state as ostate
    from film_pipeline.graph.router import compute_actions

    ostate.ensure_orchestrator_state(state)

    router_result = compute_actions(state)
    blocking_issues = _blocking_issues(state)

    pkg = _build_review_package(state, fp, phase, artifact_list, router_result, blocking_issues)
    if pkg is None:
        # Fallback to simple artifact list if generator fails
        return _ok(artifacts=artifact_list, phase=phase)

    return _ok(
        review_package=pkg.model_dump(mode="json"),
        phase=phase,
        router=router_result.__dict__,
    )


def _build_orchestrator_recommendation(state: dict[str, Any], router_result: Any) -> str:
    """Build a human-readable orchestrator recommendation for a review package."""
    action = router_result.next_action
    if action == "wait_for_human":
        return f"Review the {router_result.human_gate} package and approve or request revision."
    if action == "handle_blockers":
        return "Blocking issues detected. Resolve before advancing."
    if action == "escalate_to_human":
        return "Pipeline requires human decision — budget, provider, or quality threshold reached."
    if action == "escalate_to_failure_handler":
        return "Provider error requires triage by failure-handling agent."
    if action == "continue_unrelated_work":
        return (
            "Generation is blocked (provider health or failure), "
            "but planning and validation can continue."
        )
    if action == "present_review_package":
        return "Review the candidate artifacts and approve or request revision."
    if action == "revise":
        return "Pending revision must be resolved before approval."
    if action.startswith("advance_to_"):
        next_phase = action[len("advance_to_") :]
        return f"Phase complete. Ready to advance to {next_phase}."
    return f"Current action: {action}."


async def approve_phase(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    try:
        state = rt.approve_phase()
        return _ok(project_id=state["project_id"], current_phase=state.get("current_phase"))
    except ValueError as e:
        return _error(str(e))


async def request_revision(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    try:
        state = rt.request_revision(note=str(args.get("note", "")))
        return _ok(
            project_id=state["project_id"],
            current_phase=state.get("current_phase"),
            issues=state.get("issues", []),
        )
    except ValueError as e:
        return _error(str(e))
