"""Plan the generation batch: group shots, approve spend, persist the ledger."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from film_pipeline.generation.ledger import GenerationLedgerManager
from film_pipeline.orchestration.nodes._generation_prompts import (
    _load_matrix_rows,
    _resolve_prompt_for_request,
)
from film_pipeline.orchestration.services import GraphServices
from film_pipeline.orchestration.state_schema import StudioGraphState
from film_pipeline.schemas.artifact import ArtifactRef
from film_pipeline.schemas.base import FilmPhase, GenerationMode

if TYPE_CHECKING:
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas.base import GenerationMode


def _parse_generation_mode(mode_str: str) -> GenerationMode:
    """Parse a generation mode string, falling back to TEST when unknown."""

    mode = GenerationMode.TEST
    with contextlib.suppress(ValueError):
        mode = GenerationMode(mode_str)
    return mode


def _resolve_request_prompts(
    new_state: StudioGraphState,
    services: GraphServices,
) -> list[dict[str, Any]]:
    """Stamp each generation request with its resolved prompt text."""
    gen_requests = new_state.get("generation_requests")
    if not gen_requests:
        return []
    matrix_rows = _load_matrix_rows(new_state, services)

    resolved_requests: list[dict[str, Any]] = []
    for raw_req in gen_requests:
        # No `isinstance(raw_req, dict)` guard: `generation_requests` is declared
        # `list[dict[str, object]]` on StudioGraphState, so the check is provably
        # always true and mypy reports it as unreachable.
        req: dict[str, Any] = dict(raw_req)
        resolved_prompt = _resolve_prompt_for_request(new_state, services, req, matrix_rows)
        payload = req.get("prompt_payload")
        request_payload: dict[str, Any] = payload if isinstance(payload, dict) else {}
        request_payload["resolved_prompt"] = resolved_prompt
        req["prompt_payload"] = request_payload
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
    new_state: StudioGraphState,
    mgr: GenerationLedgerManager,
    project_id: str,
) -> None:
    """Record the planned ledger's mutable-file ref on state.

    The ledger is a mutable kind: it persists through the manager
    (``save_mutable``), never through versioned artifact saves. ``mgr.load``
    has already persisted the planned rows, so mint the ref from the stored
    envelope's revision instead of saving again.
    """

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


def _plan_generation_ledger(new_state: StudioGraphState, services: GraphServices | None) -> None:
    """Resolve prompts, plan the batch by grouping key, approve spend, persist ledger."""
    gen_requests = new_state.get("generation_requests")
    if not gen_requests or services is None:
        return

    project_id = str(new_state.get("project_id", ""))
    mgr = GenerationLedgerManager(services.artifact_store)

    resolved_requests = _resolve_request_prompts(new_state, services)
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

    mgr.approve_spend(project_id)
    _persist_planned_ledger(new_state, mgr, project_id)
