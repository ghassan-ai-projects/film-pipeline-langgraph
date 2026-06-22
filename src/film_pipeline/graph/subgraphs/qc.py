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

from film_pipeline.graph.state_schema import StudioGraphState

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


def _run_validator(
    validator_id: str, _class_name: str, state: StudioGraphState
) -> dict[str, object]:
    """Run a single validator in parallel and return its report."""
    from film_pipeline.graph.nodes import _get_services

    srv: Any = _get_services(dict(state))
    if srv is None:
        return {
            "_qc_reports": [{"validator_id": validator_id, "status": "skipped"}],
        }

    validator = _resolve_validator_instance(srv, validator_id)
    if validator is None:
        return {
            "_qc_reports": [{"validator_id": validator_id, "status": "skipped"}],
        }

    artifact = _load_artifact_for_validator(state)
    if not artifact:
        return {
            "_qc_reports": [
                {
                    "validator_id": validator_id,
                    "status": "skipped",
                    "reason": "no artifact",
                }
            ],
        }

    try:
        report = validator.run(artifact)
    except Exception:
        return {
            "_qc_reports": [{"validator_id": validator_id, "status": "failed"}],
        }

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


def _load_artifact_for_validator(state: StudioGraphState) -> dict[str, Any] | None:
    """Load the first available artifact from state refs."""
    from copy import deepcopy

    from film_pipeline.graph.nodes import _get_services

    srv: Any = _get_services(dict(state))
    if srv is None:
        return None

    project_id = str(state.get("project_id", ""))
    for ref_str in state.get("artifact_refs", []) or []:
        ref_str = str(ref_str)
        if ":" not in ref_str:
            continue
        parts = ref_str.split(":")
        aid = parts[1] if len(parts) > 1 else ref_str
        version = int(parts[2].lstrip("v")) if len(parts) > 2 else 1
        try:
            from film_pipeline.schemas._base import FilmPhase

            for fp in FilmPhase:
                try:
                    data = srv.artifact_store.load(project_id, fp, aid, version)
                    if isinstance(data, dict) and data:
                        return deepcopy(data)
                except (FileNotFoundError, ValueError):
                    continue
        except Exception:
            continue
    return None


# ── Fan-out router ─────────────────────────────────────────────────────


def fan_out_validators(state: StudioGraphState) -> list[Send]:
    """Create one Send per validator for parallel execution."""
    return [
        Send("script_structure", dict(state)),
        Send("dialogue_voice", dict(state)),
        Send("reference_usability", dict(state)),
        Send("prompt_readiness", dict(state)),
        Send("scene_continuity", dict(state)),
        Send("assembly", dict(state)),
    ]


# ── Reduce node ────────────────────────────────────────────────────────


def reduce_qc_reports(state: StudioGraphState) -> dict[str, object]:
    """Collect parallel validator reports into state."""
    raw_raw = state.get("_qc_raw_reports", [])
    reports_raw = state.get("_qc_reports", [])
    raw: list[dict[str, Any]] = list(raw_raw) if isinstance(raw_raw, list) else []
    reports: list[dict[str, Any]] = list(reports_raw) if isinstance(reports_raw, list) else []
    return {
        "_qc_raw_reports": raw,
        "_qc_reports": reports,
    }


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
        [
            "script_structure",
            "dialogue_voice",
            "reference_usability",
            "prompt_readiness",
            "scene_continuity",
            "assembly",
        ],
    )

    for worker in (
        "script_structure",
        "dialogue_voice",
        "reference_usability",
        "prompt_readiness",
        "scene_continuity",
        "assembly",
    ):
        builder.add_edge(worker, "reduce_qc_reports")

    builder.add_edge("reduce_qc_reports", END)
    return builder.compile()


def _passthrough(_state: StudioGraphState) -> dict[str, object]:
    return {}
