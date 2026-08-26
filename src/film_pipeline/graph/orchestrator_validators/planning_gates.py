"""Gate B and Gate C: planning completeness and dispatch readiness."""

from __future__ import annotations

from typing import Any

from film_pipeline.graph.orchestrator_validators._shared import (
    _blocking,
    _extract_rows,
    _extract_scene_ids,
    _row_attr,
)

# ── Gate B: Generation planning completeness ──────────────────────────────

# prompt_ref is filled BY gen_planning (via matrix patch), not a prerequisite.
_PLANNING_REQUIRED_FIELDS: list[tuple[str, str]] = [
    ("camera_profile", "camera_profile"),
]


def _matrix_rows(shot_matrix: Any) -> list[Any]:
    """Unpack rows from a ShotMatrix object or dict (no list coercion)."""
    rows: list[Any] = []
    if hasattr(shot_matrix, "rows"):
        rows = shot_matrix.rows
    elif isinstance(shot_matrix, dict):
        raw = shot_matrix.get("rows", [])
        rows = raw if isinstance(raw, list) else []
    return rows


def _row_missing_fields(row: Any) -> list[str]:
    """Return display names of generation-critical fields missing from a row.

    A valid shot needs a camera_profile and at least one subject: either
    characters OR environment. Environment-only establishing shots are valid
    and should not be blocked for lacking characters.
    """
    missing: list[str] = []
    for field_name, display_name in _PLANNING_REQUIRED_FIELDS:
        value = _row_attr(row, field_name, None)
        if value is None or (isinstance(value, (str, list)) and not value):
            missing.append(display_name)

    # Subject: characters OR environment must be populated.
    characters = _row_attr(row, "characters", None)
    environment = _row_attr(row, "environment", None)
    has_characters = isinstance(characters, list) and len(characters) > 0
    has_environment = isinstance(environment, str) and environment.strip()
    if not (has_characters or has_environment):
        missing.append("characters or environment")
    return missing


def _incomplete_row_issues(rows: list[Any]) -> list[dict[str, Any]]:
    """Blocking issue when shot rows lack generation-critical fields."""
    incomplete_rows: list[str] = []
    for row in rows:
        shot_id = str(_row_attr(row, "shot_id", "?") or "?")
        missing = _row_missing_fields(row)
        if missing:
            incomplete_rows.append(f"{shot_id}: missing {', '.join(missing)}")
    if not incomplete_rows:
        return []
    suffix = "..." if len(incomplete_rows) > 5 else ""
    return [
        _blocking(
            "incomplete_shot_rows",
            f"{len(incomplete_rows)} shot row(s) have missing generation-critical "
            f"fields: {'; '.join(incomplete_rows[:5])}" + suffix,
        )
    ]


def _estimate_clip_count(cost_estimate: Any) -> int:
    """Read the clip count from an object or dict cost estimate."""
    if hasattr(cost_estimate, "clip_count"):
        return int(getattr(cost_estimate, "clip_count", 0) or 0)
    if isinstance(cost_estimate, dict):
        raw_count = cost_estimate.get("clip_count", cost_estimate.get("total_clips", 0))
        return int(raw_count) if raw_count is not None else 0
    return 0


def _estimate_total_cost(cost_estimate: Any) -> float:
    """Read the estimated USD cost from an object or dict cost estimate."""
    if hasattr(cost_estimate, "estimated_cost_usd"):
        return float(getattr(cost_estimate, "estimated_cost_usd", 0.0) or 0.0)
    if isinstance(cost_estimate, dict):
        raw_cost = cost_estimate.get(
            "estimated_cost_usd",
            cost_estimate.get("total_cost_usd", cost_estimate.get("total_cost", 0.0)),
        )
        return float(raw_cost) if raw_cost is not None else 0.0
    return 0.0


def _cost_gate_issues(cost_estimate: Any) -> list[dict[str, Any]]:
    """Check the cost estimate exists and is non-placeholder."""
    if cost_estimate is None:
        return [
            _blocking(
                "missing_cost_estimate",
                "No cost estimate produced by generation planning. "
                "Cannot validate dispatch readiness.",
            )
        ]
    clip_count = _estimate_clip_count(cost_estimate)
    total_cost = _estimate_total_cost(cost_estimate)
    issues: list[dict[str, Any]] = []
    if clip_count == 0:
        issues.append(
            _blocking(
                "zero_clip_count",
                "Generation plan has 0 clips. Cannot dispatch to provider.",
            )
        )
    if total_cost == 0.0 and clip_count > 0:
        issues.append(
            _blocking(
                "placeholder_cost",
                "Generation plan has non-zero clips but $0.00 estimated cost. "
                "Cost estimate must reflect real provider pricing.",
            )
        )
    return issues


def validate_planning_completeness(
    _state: dict[str, Any],
    shot_matrix: Any,
    cost_estimate: Any,
) -> list[dict[str, Any]]:
    """Gate B: Check field completeness and non-placeholder cost estimates.

    Returns a list of blocking issues (empty list = pass).
    """
    issues = _incomplete_row_issues(_matrix_rows(shot_matrix))
    issues.extend(_cost_gate_issues(cost_estimate))
    return issues


def validate_shot_scene_references(
    script: Any,
    shot_matrix: Any,
) -> list[dict[str, Any]]:
    """Ensure every shot row references a scene that exists in the script."""
    scene_ids = _extract_scene_ids(script)
    rows = _extract_rows(shot_matrix)
    if not scene_ids or not rows:
        return []

    missing: list[str] = []
    for row in rows:
        scene_id = str(_row_attr(row, "scene_id", "") or "")
        shot_id = str(_row_attr(row, "shot_id", "?") or "?")
        if scene_id and scene_id not in scene_ids:
            missing.append(f"{shot_id}->{scene_id}")

    if not missing:
        return []
    return [
        _blocking(
            "shot_scene_reference_mismatch",
            f"{len(missing)} shot row(s) reference scenes that do not exist in the script: "
            f"{', '.join(missing[:8])}" + ("..." if len(missing) > 8 else ""),
        )
    ]


# ── Gate C: Dispatch readiness ────────────────────────────────────────────


def _request_field(req: Any, key: str, default: Any) -> Any:
    """Read a field from a request, handling both dict and object requests."""
    if isinstance(req, dict):
        return req.get(key, default)
    return _row_attr(req, key, default)


def _generation_requests_list(generation_requests: Any) -> list[Any]:
    """Unpack the request list from a list, envelope object, or dict."""
    if isinstance(generation_requests, list):
        return generation_requests
    if hasattr(generation_requests, "requests"):
        return getattr(generation_requests, "requests", [])
    if isinstance(generation_requests, dict):
        reqs = generation_requests.get(
            "requests", generation_requests.get("generation_requests", [])
        )
        if isinstance(reqs, list):
            return reqs
    return []


def _request_shot_id(req: Any, index: int) -> str:
    """Best-effort shot id for an undispatchable-request report."""
    if isinstance(req, dict):
        return str(req.get("shot_id", req.get("clip_id", f"request_{index}")))
    return str(_row_attr(req, "shot_id", f"request_{index}"))


def _resolved_prompt_of(req: Any) -> str:
    """Accept a plain prompt or a resolved prompt inside a payload."""
    payload = _request_field(req, "prompt_payload", {})
    if isinstance(payload, dict):
        return str(payload.get("resolved_prompt", "") or "")
    return ""


def _is_dispatchable_request(req: Any) -> bool:
    """Check that one request carries provider, model, and prompt data."""
    has_provider = bool(_request_field(req, "provider", None))
    has_model = bool(_request_field(req, "model", None))
    prompt_val = _request_field(req, "prompt", None)
    payload_val = _request_field(req, "prompt_payload", None)
    has_prompt = prompt_val is not None or payload_val is not None
    has_resolved_prompt = bool(_resolved_prompt_of(req))
    return has_provider and has_model and has_prompt and has_resolved_prompt


def _undispatchable_request_issues(requests: list[Any]) -> list[dict[str, Any]]:
    """Blocking issue listing requests missing dispatch-critical fields."""
    undispatchable = [
        _request_shot_id(req, i)
        for i, req in enumerate(requests)
        if not _is_dispatchable_request(req)
    ]
    if not undispatchable:
        return []
    suffix = "..." if len(undispatchable) > 5 else ""
    return [
        _blocking(
            "undispatchable_requests",
            f"{len(undispatchable)} request(s) are not dispatchable "
            f"(missing provider, model, or prompt): "
            f"{', '.join(undispatchable[:5])}" + suffix,
        )
    ]


def validate_dispatch_readiness(
    _state: dict[str, Any],
    generation_requests: Any,
) -> list[dict[str, Any]]:
    """Gate C: Check that generation requests are dispatchable.

    Returns a list of blocking issues (empty list = pass).
    """
    if generation_requests is None:
        return [
            _blocking(
                "no_generation_requests",
                "No generation requests exist. Cannot dispatch to provider.",
            )
        ]

    requests = _generation_requests_list(generation_requests)
    if not requests:
        return [
            _blocking(
                "empty_generation_requests",
                "Generation requests list is empty. Nothing to dispatch.",
            )
        ]

    return _undispatchable_request_issues(requests)
