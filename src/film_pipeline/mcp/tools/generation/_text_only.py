"""Text-only generation policy: satisfy generation gates without media."""

from __future__ import annotations

from typing import Any

from ..helpers import _ok, _services

_STALE_ISSUE_CODES = frozenset({"empty_generation_requests", "no_generation_requests"})


def _is_text_only_policy(state: dict[str, Any]) -> bool:
    return str(state.get("generation_policy", "")).lower() == "text_only"


def _completed_request_row(
    project_id: str,
    provider: str,
    model: str,
    shot_id: str,
    prompt_payload: dict[str, object],
) -> dict[str, object]:
    """Build one completed text-only generation request row."""
    return {
        "generation_request_id": f"text-only-{project_id}-{shot_id}",
        "generation_id": f"text-only-{project_id}-{shot_id}",
        "project_id": project_id,
        "shot_id": shot_id,
        "mode": "text_only",
        "provider": provider,
        "model": model,
        "prompt_ref": "",
        "prompt_payload": prompt_payload,
        "reference_refs": [],
        "status": "completed",
    }


def _text_only_requests(
    project_id: str,
    shot_rows: list[dict[str, Any]],
    provider: str,
    model: str,
) -> list[dict[str, object]]:
    """One completed request per shot row, or a single fallback row."""
    requests: list[dict[str, object]] = []
    for row in shot_rows:
        shot_id = str(row.get("shot_id", "") or row.get("scene_id", "")).strip()
        if not shot_id:
            continue
        requests.append(
            _completed_request_row(
                project_id, provider, model, shot_id, {"text_only": True, "shot_id": shot_id}
            )
        )
    if not requests:
        requests.append(
            _completed_request_row(project_id, provider, model, "all", {"text_only": True})
        )
    return requests


def _apply_text_only_state(active: dict[str, Any], requests: list[dict[str, object]]) -> None:
    """Record requests, flag completion, and drop stale blocking issues."""
    active["generation_requests"] = requests
    active["_text_only_generation_completed"] = True
    issues = active.get("issues", [])
    if isinstance(issues, list):
        active["issues"] = [
            issue
            for issue in issues
            if not (isinstance(issue, dict) and issue.get("code") in _STALE_ISSUE_CODES)
        ]


def _ensure_text_only_manifest_entry(store: Any, project_id: str) -> None:
    """Add the text-only-delivery entry to the asset manifest once."""
    from film_pipeline.artifacts.manifest import (
        AssetEntry,
        AssetManifest,
        read_manifest,
        write_manifest,
    )

    manifest = read_manifest(project_id, root=store.root)
    entries = list(manifest.entries) if manifest else []
    if not any(entry.asset_id == "text-only-delivery" for entry in entries):
        entries.append(
            AssetEntry(
                asset_id="text-only-delivery",
                kind="text_only_delivery",
                shot_id="",
                scene_id="",
                path="",
            )
        )
        write_manifest(AssetManifest(project_id=project_id, entries=entries), root=store.root)


def _complete_text_only_generation(
    rt: Any, active: dict[str, Any], project_id: str
) -> dict[str, object]:
    """Satisfy generation gates without producing clips or frames via MCP tools."""
    from film_pipeline.generation.executor import GenerationExecutor

    if active.get("_text_only_generation_completed"):
        return _ok(text_only=True, completed=1, rows=[])

    store = _services(rt).artifact_store
    executor = GenerationExecutor(store, rt.provider_adapters)
    shot_rows = executor.load_shot_rows(project_id)
    provider, model = rt.default_video_provider()
    requests = _text_only_requests(project_id, shot_rows, provider, model)
    _apply_text_only_state(active, requests)
    _ensure_text_only_manifest_entry(store, project_id)

    rt.projects[project_id] = active
    rt._persist_project_state(project_id)
    return _ok(text_only=True, completed=len(requests), rows=[])
