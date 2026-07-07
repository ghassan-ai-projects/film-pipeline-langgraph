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


def validate_planning_completeness(
    _state: dict[str, Any],
    shot_matrix: Any,
    cost_estimate: Any,
) -> list[dict[str, Any]]:
    """Gate B: Check field completeness and non-placeholder cost estimates.

    Returns a list of blocking issues (empty list = pass).
    """
    issues: list[dict[str, Any]] = []

    # Unpack rows
    rows: list[Any] = []
    if hasattr(shot_matrix, "rows"):
        rows = shot_matrix.rows
    elif isinstance(shot_matrix, dict):
        raw = shot_matrix.get("rows", [])
        rows = raw if isinstance(raw, list) else []

    # --- Check field completeness per row ---
    # prompt_ref is filled BY gen_planning (via matrix patch), not a prerequisite.
    # A valid shot needs a camera_profile and at least one subject: either
    # characters OR environment. Environment-only establishing shots are valid
    # and should not be blocked for lacking characters.
    REQUIRED_FIELDS = [
        ("camera_profile", "camera_profile"),
    ]

    incomplete_rows: list[str] = []
    for row in rows:
        shot_id = str(_row_attr(row, "shot_id", "?") or "?")
        missing: list[str] = []
        for field_name, display_name in REQUIRED_FIELDS:
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

        if missing:
            incomplete_rows.append(f"{shot_id}: missing {', '.join(missing)}")

    if incomplete_rows:
        issues.append(
            _blocking(
                "incomplete_shot_rows",
                f"{len(incomplete_rows)} shot row(s) have missing generation-critical "
                f"fields: {'; '.join(incomplete_rows[:5])}"
                + ("..." if len(incomplete_rows) > 5 else ""),
            )
        )

    # --- Check cost estimate is non-placeholder ---
    if cost_estimate is not None:
        clip_count: int = 0
        total_cost: float = 0.0
        if hasattr(cost_estimate, "clip_count"):
            clip_count = int(getattr(cost_estimate, "clip_count", 0) or 0)
        elif isinstance(cost_estimate, dict):
            raw_count = cost_estimate.get("clip_count", cost_estimate.get("total_clips", 0))
            clip_count = int(raw_count) if raw_count is not None else 0
        if hasattr(cost_estimate, "estimated_cost_usd"):
            total_cost = float(getattr(cost_estimate, "estimated_cost_usd", 0.0) or 0.0)
        elif isinstance(cost_estimate, dict):
            raw_cost = cost_estimate.get(
                "estimated_cost_usd",
                cost_estimate.get("total_cost_usd", cost_estimate.get("total_cost", 0.0)),
            )
            total_cost = float(raw_cost) if raw_cost is not None else 0.0

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
    else:
        issues.append(
            _blocking(
                "missing_cost_estimate",
                "No cost estimate produced by generation planning. "
                "Cannot validate dispatch readiness.",
            )
        )

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


def validate_dispatch_readiness(
    _state: dict[str, Any],
    generation_requests: Any,
) -> list[dict[str, Any]]:
    """Gate C: Check that generation requests are dispatchable.

    Returns a list of blocking issues (empty list = pass).
    """
    issues: list[dict[str, Any]] = []

    if generation_requests is None:
        issues.append(
            _blocking(
                "no_generation_requests",
                "No generation requests exist. Cannot dispatch to provider.",
            )
        )
        return issues

    requests: list[Any] = []
    if isinstance(generation_requests, list):
        requests = generation_requests
    elif hasattr(generation_requests, "requests"):
        requests = getattr(generation_requests, "requests", [])
    elif isinstance(generation_requests, dict):
        reqs = generation_requests.get(
            "requests", generation_requests.get("generation_requests", [])
        )
        if isinstance(reqs, list):
            requests = reqs

    if not requests:
        issues.append(
            _blocking(
                "empty_generation_requests",
                "Generation requests list is empty. Nothing to dispatch.",
            )
        )
        return issues

    # Check each request has minimum dispatchable fields
    undispatchable: list[str] = []
    for i, req in enumerate(requests):
        shot_id = "?"
        if isinstance(req, dict):
            shot_id = str(req.get("shot_id", req.get("clip_id", f"request_{i}")))
            has_provider = bool(req.get("provider"))
            has_model = bool(req.get("model"))
            prompt_val = req.get("prompt")
            payload_val = req.get("prompt_payload")
            has_prompt = prompt_val is not None or payload_val is not None
        else:
            shot_id = str(_row_attr(req, "shot_id", f"request_{i}"))
            has_provider = bool(_row_attr(req, "provider", None))
            has_model = bool(_row_attr(req, "model", None))
            prompt_val = _row_attr(req, "prompt", None)
            payload_val = _row_attr(req, "prompt_payload", None)
            has_prompt = prompt_val is not None or payload_val is not None

        # Accept a plain prompt or a resolved prompt inside a payload.
        resolved_prompt = ""
        if isinstance(req, dict):
            payload = req.get("prompt_payload") or {}
            if isinstance(payload, dict):
                resolved_prompt = str(payload.get("resolved_prompt", "") or "")
        else:
            payload = _row_attr(req, "prompt_payload", {})
            if isinstance(payload, dict):
                resolved_prompt = str(payload.get("resolved_prompt", "") or "")
        has_resolved_prompt = bool(resolved_prompt)

        if not (has_provider and has_model and has_prompt and has_resolved_prompt):
            undispatchable.append(shot_id)

    if undispatchable:
        issues.append(
            _blocking(
                "undispatchable_requests",
                f"{len(undispatchable)} request(s) are not dispatchable "
                f"(missing provider, model, or prompt): "
                f"{', '.join(undispatchable[:5])}" + ("..." if len(undispatchable) > 5 else ""),
            )
        )

    return issues
