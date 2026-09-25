"""Plan the generation batch: group shots, approve spend, persist the ledger."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from film_pipeline.graph.nodes._generation_prompts import (
    _load_artifact_data,
    _load_matrix_rows,
    _resolve_prompt_for_request,
)
from film_pipeline.graph.services import GraphServices

if TYPE_CHECKING:
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationMode


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
        ce_data = _load_artifact_data(new_state, services, cost_estimate_ref)
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


def _resolve_request_prompts(
    new_state: dict[str, Any],
    services: GraphServices,
) -> list[dict[str, Any]]:
    """Stamp each generation request with its resolved prompt text."""
    gen_requests = new_state.get("generation_requests")
    if not gen_requests:
        return []
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
    return resolved_requests


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


def _persist_planned_ledger(
    new_state: dict[str, Any],
    mgr: GenerationLedgerManager,
    project_id: str,
) -> None:
    """Record the planned ledger's mutable-file ref on state.

    The ledger is a mutable kind: it persists through the manager
    (``save_mutable``), never through versioned artifact saves. ``mgr.load``
    has already persisted the planned rows, so mint the ref from the stored
    envelope's revision instead of saving again.
    """
    from film_pipeline.schemas._base import FilmPhase
    from film_pipeline.schemas.artifact import ArtifactRef

    mgr.load(project_id)  # ensures the ledger exists and rows are persisted
    envelope = mgr.store.load_mutable_envelope(
        project_id, FilmPhase.GENERATION, "generation_ledger"
    )
    ledger_ref = ArtifactRef(
        artifact_id="generation_ledger",
        version=envelope.revision or 1,
        phase=FilmPhase.GENERATION.value,
    ).to_string()
    new_state["generation_ledger_ref"] = ledger_ref
    new_state.setdefault("artifact_refs", []).append(ledger_ref)


def _plan_generation_ledger(new_state: dict[str, Any], services: GraphServices | None) -> None:
    """Resolve prompts, plan the batch by grouping key, approve spend, persist ledger."""
    gen_requests = new_state.get("generation_requests")
    if not gen_requests or services is None:
        return

    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.providers.pricing import estimate_cost_for_duration

    project_id = str(new_state.get("project_id", ""))
    mgr = GenerationLedgerManager(services.artifact_store)

    resolved_requests = _resolve_request_prompts(new_state, services)
    groups = _group_requests_by_batch(resolved_requests)
    matrix_rows = {
        str(row.get("shot_id", "")): row for row in _load_matrix_rows(new_state, services)
    }

    for (provider, model, mode_str, prompt_ref), shot_ids in groups.items():
        estimated_costs = {
            shot_id: estimate_cost_for_duration(
                provider,
                model,
                float(matrix_rows.get(shot_id, {}).get("duration_seconds", 5) or 5),
            )
            for shot_id in shot_ids
        }
        mgr.plan_batch(
            project_id=project_id,
            shot_ids=shot_ids,
            provider=provider,
            model=model,
            prompt_ref=prompt_ref,
            mode=_parse_generation_mode(mode_str),
            estimated_costs=estimated_costs,
        )

    _approve_spend_with_ceiling(new_state, services, mgr, project_id)
    _persist_planned_ledger(new_state, mgr, project_id)
