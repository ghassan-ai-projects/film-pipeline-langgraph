"""Text-only generation-request builders.

Moved out of `filmspec` (doc 06 slice 6.7). `filmspec` describes itself as "pure
vocabulary: phases, enums, transitions, generation-request codes", and these two
functions are not vocabulary — they *build rows*, deciding an id scheme, a field set
and a fallback rule.

They lived there because two callers needed to agree: the operator service and the MCP
tool path. `operations._generation_ops` was deleted with the orphaned operator surface
(doc 03 slice 1), leaving one caller, which is exactly the condition doc 06 named for
moving them: "after doc 03 there is one. Move them then, not before."

`TEXT_ONLY_POLICY` and `is_text_only_policy` stay in `filmspec`: the policy *string* is
vocabulary, and the predicate is the one-line rule that reads it. Only the row
construction moved.
"""

from __future__ import annotations

from typing import Any


def text_only_generation_request(
    project_id: str,
    shot_id: str,
    provider: str,
    model: str,
) -> dict[str, Any]:
    """Build one completed text-only generation request row.

    The text-only policy satisfies the generation gates without producing media.
    Both the operator service and the MCP tool path build these rows, and they
    must agree on the id scheme and field set, so the shape is declared once.
    The ``shot_id`` of ``"all"`` marks the single fallback row used when no shot
    rows exist, and carries no ``shot_id`` in its prompt payload.
    """
    payload: dict[str, Any] = {"text_only": True}
    if shot_id != "all":
        payload["shot_id"] = shot_id
    return {
        "generation_request_id": f"text-only-{project_id}-{shot_id}",
        "generation_id": f"text-only-{project_id}-{shot_id}",
        "project_id": project_id,
        "shot_id": shot_id,
        "mode": "text_only",
        "provider": provider,
        "model": model,
        "prompt_ref": "",
        "prompt_payload": payload,
        "reference_refs": [],
        "status": "completed",
    }


def text_only_generation_requests(
    project_id: str,
    shot_rows: list[dict[str, Any]],
    provider: str,
    model: str,
) -> list[dict[str, Any]]:
    """Build one completed text-only request per shot row, or a single fallback.

    Rows without a usable ``shot_id`` (falling back to ``scene_id``) are
    skipped; if that leaves nothing, the fallback ``"all"`` row is emitted so
    the generation gate is still satisfied.
    """
    requests: list[dict[str, Any]] = []
    for row in shot_rows:
        shot_id = str(row.get("shot_id", "") or row.get("scene_id", "")).strip()
        if not shot_id:
            continue
        requests.append(text_only_generation_request(project_id, shot_id, provider, model))
    if not requests:
        requests.append(text_only_generation_request(project_id, "all", provider, model))
    return requests


#: The one message for "this request has no project to act on". It lives in the
#: shared vocabulary module because both the MCP dispatcher and the tool layer

__all__ = [
    "text_only_generation_request",
    "text_only_generation_requests",
]
