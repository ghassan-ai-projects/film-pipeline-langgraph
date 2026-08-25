"""Generation phase node and its prompt/matrix helpers."""

from __future__ import annotations

import contextlib
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from film_pipeline.graph.nodes._agent import (
    _propagate_side_effects,
    _save_artifact,
)
from film_pipeline.graph.nodes._context import (
    _parse_ref,
)
from film_pipeline.graph.nodes._shared import (
    _get_services,
    _is_new_issue,
    _is_new_ref,
    _phase_gate_updates,
)
from film_pipeline.graph.services import GraphServices

if TYPE_CHECKING:
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationMode


def _load_artifact_data(
    state: dict[str, Any],
    services: GraphServices,
    ref: str,
    phase_guesses: list[str] | None = None,
) -> Any:
    """Load artifact data by ref, trying a list of candidate phases."""
    if not ref or ":" not in ref:
        return None
    parsed = _parse_ref(ref)
    project_id = str(state.get("project_id", ""))
    if not project_id:
        return None
    from film_pipeline.schemas._base import FilmPhase

    phases = phase_guesses or ["gen_planning", "shot_bible", "visual_dev", "script"]
    for phase in phases:
        try:
            return services.artifact_store.load(
                project_id, FilmPhase(phase), parsed.artifact_id, parsed.version
            )
        except (FileNotFoundError, ValueError, KeyError):
            continue
    return None


def _load_matrix_rows(
    state: dict[str, Any],
    services: GraphServices,
) -> list[dict[str, Any]]:
    """Load rows from the master film matrix artifact."""
    shot_matrix_ref = str(state.get("shot_matrix_ref", ""))
    if not shot_matrix_ref:
        return []
    data = _load_artifact_data(state, services, shot_matrix_ref, ["shot_bible"])
    if not isinstance(data, dict):
        return []
    rows = data.get("rows", [])
    if isinstance(rows, list):
        return [r if isinstance(r, dict) else r.model_dump() for r in rows]
    return []


def _find_matrix_row(rows: list[dict[str, Any]], shot_id: str) -> dict[str, Any] | None:
    for row in rows:
        if str(row.get("shot_id", "")) == shot_id:
            return row
    return None


def _prompt_entry_from_row(row: dict[str, Any]) -> dict[str, Any]:
    """Map a master-matrix row onto the structured prompt-builder entry shape."""
    characters = row.get("characters") or []
    environment = str(row.get("environment", "") or "")
    subject_type = "environment" if not characters else "character"
    subject_id = environment if not characters else str(characters[0])
    return {
        "subject_type": subject_type,
        "subject_id": subject_id,
        "frame_role": str(row.get("camera_profile", "") or ""),
        "prompt_text": str(row.get("story_function", "") or ""),
        "lighting": str(row.get("lighting_state", "") or ""),
        "notes": str(row.get("environment_state", "") or ""),
    }


def _load_visual_dev_bible(
    services: GraphServices,
    project_id: str,
    bible_id: str,
) -> dict[str, Any] | None:
    """Load a visual_dev bible, returning None when absent or malformed."""
    from film_pipeline.schemas._base import FilmPhase

    try:
        data = services.artifact_store.load(project_id, FilmPhase("visual_dev"), bible_id, 1)
    except (FileNotFoundError, ValueError, KeyError):
        return None
    return data if isinstance(data, dict) else None


def _build_prompt_from_matrix_row(
    state: dict[str, Any],
    services: GraphServices,
    row: dict[str, Any],
) -> str:
    """Build a structured generation prompt from the shot matrix row."""
    from film_pipeline.generation.prompt_builder import build_structured_prompt

    characters = row.get("characters") or []
    environment = str(row.get("environment", "") or "")

    entry = _prompt_entry_from_row(row)

    constitution_ref = str(state.get("constitution_ref", "") or "")
    constitution = (
        _load_artifact_data(state, services, constitution_ref, ["constitution"])
        if constitution_ref
        else None
    )
    constitution = constitution if isinstance(constitution, dict) else None

    character_bible: dict[str, Any] | None = None
    project_id = str(state.get("project_id", ""))
    if characters:
        character_bible = _load_visual_dev_bible(services, project_id, "character_bible")
    elif environment:
        # Loaded despite being unconsumed here, matching the historical load path.
        _load_visual_dev_bible(services, project_id, "environment_bible")

    return build_structured_prompt(
        entry,
        character_bible=character_bible,
        constitution=constitution,
    )


def _compose_prompt_from_rctco(rctco: dict[str, Any]) -> str:
    """Compose fallback prompt text from an entry's RCTCO block."""
    parts: list[str] = []
    if rctco.get("r"):
        parts.append(str(rctco["r"]))
    if rctco.get("c1"):
        parts.append(str(rctco["c1"]))
    constraints = rctco.get("c2") or []
    if constraints:
        parts.append("Constraints:")
        parts.extend(f"- {c}" for c in constraints)
    context = rctco.get("t") or {}
    if context:
        parts.append("Context:")
        for key, value in context.items():
            parts.append(f"- {key}: {value}")
    return "\n\n".join(parts)


def _resolve_prompt_for_request(
    state: dict[str, Any],
    services: GraphServices,
    req: dict[str, Any],
    matrix_rows: list[dict[str, Any]],
) -> str:
    """Resolve a generation request's prompt_ref to actual prompt text."""
    prompt_ref = str(req.get("prompt_ref", "") or "")
    shot_id = str(req.get("shot_id", "") or "")

    if prompt_ref and services:
        data = _load_artifact_data(state, services, prompt_ref, ["gen_planning", "shot_bible"])
        entries = (data.get("entries") or []) if isinstance(data, dict) else []
        for entry in entries:
            if not isinstance(entry, dict) or str(entry.get("shot_id", "")) != shot_id:
                continue
            rendered = str(entry.get("rendered_prompt", "") or "")
            if rendered:
                return rendered
            rctco = entry.get("rctco")
            if isinstance(rctco, dict):
                return _compose_prompt_from_rctco(rctco)

    row = _find_matrix_row(matrix_rows, shot_id)
    if row is not None:
        return _build_prompt_from_matrix_row(state, services, row)

    return str(req.get("prompt", "") or "")


def _parse_generation_mode(mode_str: str) -> GenerationMode:
    """Parse a generation mode string, falling back to TEST when unknown."""
    from film_pipeline.schemas._base import GenerationMode

    mode = GenerationMode.TEST
    with contextlib.suppress(ValueError):
        mode = GenerationMode(mode_str)
    return mode


def _approve_spend_with_ceiling(
    new_state: dict[str, Any],
    services: GraphServices,
    mgr: GenerationLedgerManager,
    project_id: str,
) -> None:
    """Approve spend under a ceiling derived from the cost estimate (+10%)."""
    max_cost_usd = -1.0
    cost_estimate_ref = str(new_state.get("cost_estimate_ref", "") or "")
    if cost_estimate_ref:
        ce_data = _load_artifact_data(new_state, services, cost_estimate_ref, ["gen_planning"])
        if isinstance(ce_data, dict):
            raw_cost = ce_data.get("estimated_cost_usd")
            if raw_cost is not None:
                with contextlib.suppress(TypeError, ValueError):
                    max_cost_usd = float(raw_cost) * 1.1
    try:
        mgr.approve_spend(project_id, max_cost_usd=max_cost_usd)
    except ValueError as exc:
        new_state.setdefault("issues", []).append(
            {
                "severity": "blocking",
                "code": "generation_budget_exceeded",
                "message": str(exc),
            }
        )


def _ledger_rows_by_shot(
    services: GraphServices,
    project_id: str,
) -> dict[str, str]:
    """Map shot_id -> generation_id from the persisted generation ledger."""
    from film_pipeline.generation.ledger import GenerationLedgerManager

    mgr = GenerationLedgerManager(services.artifact_store)
    return {row.shot_id: row.generation_id for row in mgr.load(project_id).rows}


def _group_requests_by_batch(
    resolved_requests: list[dict[str, Any]],
) -> dict[tuple[str, str, str, str], list[str]]:
    """Group request shot_ids by their shared (provider, model, mode, prompt_ref) batch key."""
    from collections import defaultdict

    groups: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
    for req in resolved_requests:
        shot_id = str(req.get("shot_id", ""))
        if not shot_id:
            continue
        provider = str(req.get("provider", "mock-video-provider") or "mock-video-provider")
        model = str(req.get("model", "mock-fast") or "mock-fast")
        mode = _parse_generation_mode(str(req.get("mode", "test") or "test"))
        prompt_ref = str(req.get("prompt_ref", "") or "")
        groups[(provider, model, str(mode.value), prompt_ref)].append(shot_id)
    return groups


def _plan_generation_ledger(new_state: dict[str, Any], services: GraphServices | None) -> None:
    """Resolve prompts, plan the batch by grouping key, approve spend, persist ledger."""
    gen_requests = new_state.get("generation_requests")
    if not gen_requests or services is None:
        return

    from film_pipeline.generation.ledger import GenerationLedgerManager

    project_id = str(new_state.get("project_id", ""))
    mgr = GenerationLedgerManager(services.artifact_store)
    matrix_rows = _load_matrix_rows(new_state, services)

    resolved_requests: list[dict[str, Any]] = []
    for req in gen_requests:
        if not isinstance(req, dict):
            continue
        req = dict(req)
        resolved_prompt = _resolve_prompt_for_request(new_state, services, req, matrix_rows)
        req.setdefault("prompt_payload", {})["resolved_prompt"] = resolved_prompt
        resolved_requests.append(req)
    new_state["generation_requests"] = resolved_requests

    groups = _group_requests_by_batch(resolved_requests)

    for (provider, model, mode_str, prompt_ref), shot_ids in groups.items():
        mgr.plan_batch(
            project_id=project_id,
            shot_ids=shot_ids,
            provider=provider,
            model=model,
            prompt_ref=prompt_ref,
            mode=_parse_generation_mode(mode_str),
        )

    _approve_spend_with_ceiling(new_state, services, mgr, project_id)

    ledger = mgr.load(project_id)
    ledger_ref = _save_artifact(
        new_state,
        ledger,
        "generation_ledger",
        "generation",
        artifact_type="generation_ledger",
    )
    if ledger_ref:
        new_state["generation_ledger_ref"] = ledger_ref
        new_state.setdefault("artifact_refs", []).append(ledger_ref)


def _gate_dispatch_readiness(new_state: dict[str, Any]) -> None:
    """Gate C: validate dispatch readiness over the enriched requests."""
    gen_requests = new_state.get("generation_requests")
    if gen_requests is None:
        return
    from film_pipeline.graph.orchestrator_validators import validate_dispatch_readiness

    dispatch_issues = validate_dispatch_readiness(new_state, gen_requests)
    new_state.setdefault("issues", []).extend(dispatch_issues)


def _mark_matrix_rows_generated(new_state: dict[str, Any], services: GraphServices | None) -> None:
    """Emit a matrix patch marking requested shots generated with asset refs."""
    gen_requests = new_state.get("generation_requests")
    shot_matrix_ref = str(new_state.get("shot_matrix_ref", ""))
    if not gen_requests or not shot_matrix_ref:
        return

    from film_pipeline.schemas.matrix_patch import MatrixPatch, MatrixRowUpdate

    ledger_rows_by_shot: dict[str, str] = {}
    if services is not None:
        ledger_rows_by_shot = _ledger_rows_by_shot(services, str(new_state.get("project_id", "")))

    row_updates: list[Any] = []
    for req in gen_requests:
        if isinstance(req, dict):
            sid = str(req.get("shot_id", ""))
            asset_ref = str(
                req.get("asset_ref") or req.get("output_ref") or ledger_rows_by_shot.get(sid, "")
            )
            if sid:
                row_updates.append(
                    MatrixRowUpdate(
                        shot_id=sid,
                        set={"status": "generated"},
                        append={"asset_refs": [asset_ref]} if asset_ref else {},
                    )
                )

    if row_updates:
        patch = MatrixPatch(
            patch_id=f"generation_{new_state.get('project_id', '')}",
            matrix_ref=shot_matrix_ref,
            phase="generation",
            reason="Clips generated — updating row asset references and status.",
            updates=row_updates,
            created_by_agent="generation-scheduler-agent",
        )
        patch_ref = _save_artifact(
            new_state,
            patch,
            "matrix_patch_generation",
            "generation",
            artifact_type="generation_plan",
        )
        if patch_ref:
            new_state["generation_patch_ref"] = patch_ref
            new_state.setdefault("artifact_refs", []).append(patch_ref)


def generation_node(state: dict[str, Any]) -> dict[str, Any]:
    new_state = deepcopy(state)
    original = state
    gate_updates = _phase_gate_updates(new_state, phase="generation", gate="generation_batch")
    new_state.update(gate_updates)

    services = _get_services(new_state)
    _plan_generation_ledger(new_state, services)
    _gate_dispatch_readiness(new_state)
    _mark_matrix_rows_generated(new_state, services)

    updates: dict[str, Any] = dict(gate_updates)
    new_refs = [r for r in (new_state.get("artifact_refs", []) or []) if _is_new_ref(r, original)]
    if new_refs:
        updates["artifact_refs"] = new_refs
    new_issues = [i for i in (new_state.get("issues", []) or []) if _is_new_issue(i, original)]
    if new_issues:
        updates["issues"] = new_issues
    for key in ("generation_ledger_ref", "generation_patch_ref"):
        val = new_state.get(key)
        if val:
            updates[key] = val
    if "generation_requests" in new_state:
        # The generation_requests reducer upserts by request id, so returning
        # the enriched list updates entries in place without duplication.
        updates["generation_requests"] = new_state["generation_requests"]
    _propagate_side_effects(new_state, updates, state)
    return updates
