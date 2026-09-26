"""QC subgraph — fan-out validators, reduce reports, build consensus.

Phase 7: parallel validator execution via LangGraph Send API.
The parent graph invokes this subgraph; internally validators fan out,
run concurrently, and reduce into a consensus report.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send

from film_pipeline.orchestration.state_schema import StudioGraphState

# ── Worker nodes ───────────────────────────────────────────────────────


def script_structure(state: StudioGraphState) -> dict[str, object]:
    return _run_validator("script-structure", "ScriptStructureValidator", state)


def dialogue_voice(state: StudioGraphState) -> dict[str, object]:
    return _run_validator("dialogue-voice", "DialogueVoiceValidator", state)


def reference_usability(state: StudioGraphState) -> dict[str, object]:
    return _run_validator("reference-usability", "ReferenceUsabilityValidator", state)


def prompt_readiness(state: StudioGraphState) -> dict[str, object]:
    return _run_validator("prompt-readiness", "PromptReadinessValidator", state)


def scene_continuity(state: StudioGraphState) -> dict[str, object]:
    return _run_validator("scene-continuity", "SceneContinuityValidator", state)


def assembly(state: StudioGraphState) -> dict[str, object]:
    return _run_validator("assembly", "AssemblyValidator", state)


_VALIDATOR_MAP: dict[str, str] = {
    "script-structure": "ScriptStructureValidator",
    "dialogue-voice": "DialogueVoiceValidator",
    "reference-usability": "ReferenceUsabilityValidator",
    "prompt-readiness": "PromptReadinessValidator",
    "scene-continuity": "SceneContinuityValidator",
    "assembly": "AssemblyValidator",
}


def _skipped_validator_update(validator_id: str, reason: str | None = None) -> dict[str, object]:
    """Build the worker update recording why a validator did not run."""
    report: dict[str, object] = {"validator_id": validator_id, "status": "skipped"}
    if reason is not None:
        report["reason"] = reason
    return _worker_update(report)


def _failed_validator_update(validator_id: str) -> dict[str, object]:
    """Build the worker update recorded when a validator run raises."""
    return _worker_update({"validator_id": validator_id, "status": "failed"})


def _worker_update(report: dict[str, object]) -> dict[str, object]:
    """Wrap a single validator report into both QC report channels."""
    return {
        "_qc_reports": [report],
        "_qc_raw_reports": [report],
    }


def _run_validator(
    validator_id: str, _class_name: str, state: StudioGraphState
) -> dict[str, object]:
    """Run a single validator in parallel and append its report to the raw channel."""
    from film_pipeline.orchestration.services import _get_services

    srv: Any = _get_services(dict(state))
    if srv is None:
        return _skipped_validator_update(validator_id)

    validator = _resolve_validator_instance(srv, validator_id)
    if validator is None:
        return _skipped_validator_update(validator_id)

    artifact = _load_artifact_for_validator(state, validator_id)
    if not artifact:
        return _skipped_validator_update(validator_id, reason="no artifact")

    try:
        report = validator.run(artifact)
    except Exception:
        return _failed_validator_update(validator_id)

    return {
        "_qc_reports": [
            {
                "validator_id": validator_id,
                "score": report.score,
                "status": str(report.status),
                "blocking_count": len(report.blocking_issues),
                "warning_count": len(report.warnings),
            }
        ],
        "_qc_raw_reports": [report.model_dump()],
    }


def _resolve_validator_instance(srv: Any, validator_id: str) -> Any:
    """Resolve a validator class from the registry and instantiate it."""

    from film_pipeline.validation.impl.assembly import AssemblyValidator
    from film_pipeline.validation.impl.dialogue_voice import DialogueVoiceValidator
    from film_pipeline.validation.impl.prompt_readiness import PromptReadinessValidator
    from film_pipeline.validation.impl.reference_usability import (
        ReferenceUsabilityValidator,
    )
    from film_pipeline.validation.impl.scene_continuity import SceneContinuityValidator
    from film_pipeline.validation.impl.script_structure import ScriptStructureValidator

    cls_map: dict[str, Any] = {
        "ScriptStructureValidator": ScriptStructureValidator,
        "DialogueVoiceValidator": DialogueVoiceValidator,
        "ReferenceUsabilityValidator": ReferenceUsabilityValidator,
        "PromptReadinessValidator": PromptReadinessValidator,
        "SceneContinuityValidator": SceneContinuityValidator,
        "AssemblyValidator": AssemblyValidator,
    }
    cls = _VALIDATOR_MAP.get(validator_id, "")
    vcls = cls_map.get(cls)
    if vcls is None:
        return None

    instance = vcls()
    if hasattr(instance, "set_services") and hasattr(srv, "prompt_runner"):
        pr = srv.prompt_runner
        if hasattr(pr, "model_adapter"):
            from contextlib import suppress

            with suppress(Exception):
                instance.set_services(
                    adapter=pr.model_adapter,
                    router=pr.model_router if hasattr(pr, "model_router") else None,
                )
    return instance


# Which artifact (by id, in preference order) each validator inspects.
_VALIDATOR_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "script-structure": ("script", "scene_list"),
    "dialogue-voice": ("script", "scene_list"),
    "reference-usability": ("reference_index",),
    "prompt-readiness": ("prompt_registry", "execution_brief"),
    "scene-continuity": ("shot_matrix", "shot_bible"),
    "assembly": ("assembly_manifest", "review_cut", "final_cut"),
}


def _load_artifact_for_validator(
    state: StudioGraphState, validator_id: str
) -> dict[str, Any] | None:
    """Load the specific artifact the validator is written against.

    Feeding a validator an arbitrary artifact produces false blocking
    findings (e.g. the script validator reporting "no scenes" when handed a
    project profile), so each validator only runs when its artifact exists.
    """
    from copy import deepcopy

    from film_pipeline.orchestration.services import _get_services

    srv: Any = _get_services(dict(state))
    if srv is None:
        return None

    project_id = str(state.get("project_id", ""))
    wanted = _VALIDATOR_ARTIFACTS.get(validator_id, ())
    # One index scan replaces the old all-phase brute force: latest version
    # per artifact id, with the phase the store recorded for it.
    latest_by_id: dict[str, Any] = {}
    for meta in srv.artifact_store.list_artifacts(project_id):
        current = latest_by_id.get(meta.artifact_id)
        if current is None or meta.version > current.version:
            latest_by_id[meta.artifact_id] = meta
    for artifact_id in wanted:
        meta = latest_by_id.get(artifact_id)
        if meta is None:
            continue
        try:
            data = srv.artifact_store.load(project_id, meta.phase, artifact_id, meta.version)
        except (FileNotFoundError, ValueError):
            continue
        if isinstance(data, dict) and data:
            data = deepcopy(data)
            if artifact_id == "shot_matrix" and isinstance(data.get("rows"), list):
                # Continuity validator reads "shots"; the matrix stores "rows".
                data.setdefault("shots", data["rows"])
            return data
    return None


# ── Fan-out router ─────────────────────────────────────────────────────

# Worker node names in fan-out order; the Send router, the conditional-edge
# path map, and the worker→reduce edges must all agree on this sequence.
_WORKER_NODES: tuple[str, ...] = (
    "script_structure",
    "dialogue_voice",
    "reference_usability",
    "prompt_readiness",
    "scene_continuity",
    "assembly",
)


def fan_out_validators(state: StudioGraphState) -> list[Send]:
    """Create one Send per validator for parallel execution."""
    return [Send(node, dict(state)) for node in _WORKER_NODES]


# ── Reduce node ────────────────────────────────────────────────────────


def _findings_to_issues(raw_reports: list[dict[str, Any]]) -> list[dict[str, object]]:
    """Translate raw validator findings into issues the approval gate can see."""
    issues: list[dict[str, object]] = []
    for report in raw_reports:
        validator_id = str(report.get("validator_id", ""))
        for severity, key in (("blocking", "blocking_issues"), ("warning", "warnings")):
            for finding in report.get(key, []) or []:
                if not isinstance(finding, dict):
                    continue
                issues.append(
                    {
                        "issue_id": f"val:{validator_id}:{finding.get('code', '?')}",
                        "severity": severity,
                        "code": str(finding.get("code", "?")),
                        "message": str(finding.get("message", "")),
                        "validator_id": validator_id,
                    }
                )
    return issues


def reduce_qc_reports(state: StudioGraphState) -> dict[str, object]:
    """Collect parallel validator reports and finish the QC phase step.

    Besides gathering reports, this node owns the QC phase transition: it
    marks ``current_phase`` and the human gate flags (the fan-out workers
    only produce reports) and translates validator findings into issues so
    the approval gate sees them.
    """
    from film_pipeline.orchestration.orchestrator_state import require_human_approval

    raw_raw = state.get("_qc_raw_reports", [])
    raw: list[dict[str, Any]] = list(raw_raw) if isinstance(raw_raw, list) else []

    auto = not require_human_approval(dict(state))
    update: dict[str, object] = {
        # _qc_reports/_qc_raw_reports are reducer channels already holding the
        # workers' outputs; re-emitting them here would duplicate entries.
        "_validation_reports": raw,
        "current_phase": "qc",
        "approved": auto,
        "human_approval_required": not auto,
        "human_approval_phase": "qc",
    }
    if not raw:
        update["_qc_reports"] = []
    issues = _findings_to_issues(raw)
    if issues:
        update["issues"] = issues
    return update


# ── Subgraph factory ───────────────────────────────────────────────────


def build_qc_subgraph() -> CompiledStateGraph:
    """Build the QC subgraph with parallel validator fan-out via Send."""
    builder = StateGraph(StudioGraphState)

    builder.add_node("fan_start", _passthrough)
    builder.add_node("script_structure", script_structure)
    builder.add_node("dialogue_voice", dialogue_voice)
    builder.add_node("reference_usability", reference_usability)
    builder.add_node("prompt_readiness", prompt_readiness)
    builder.add_node("scene_continuity", scene_continuity)
    builder.add_node("assembly", assembly)
    builder.add_node("reduce_qc_reports", reduce_qc_reports)

    builder.set_entry_point("fan_start")
    builder.add_conditional_edges(
        "fan_start",
        fan_out_validators,  # type: ignore[arg-type]
        list(_WORKER_NODES),
    )

    for worker in _WORKER_NODES:
        builder.add_edge(worker, "reduce_qc_reports")

    builder.add_edge("reduce_qc_reports", END)
    return builder.compile()


def _passthrough(_state: StudioGraphState) -> dict[str, object]:
    return {}
