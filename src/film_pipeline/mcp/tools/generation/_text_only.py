"""Text-only generation policy: satisfy generation gates without media."""

from __future__ import annotations

from typing import Any

from ..helpers import _ok, _services


def _is_text_only_policy(state: dict[str, Any]) -> bool:
    return str(state.get("generation_policy", "")).lower() == "text_only"


def _complete_text_only_generation(
    rt: Any, active: dict[str, Any], project_id: str
) -> dict[str, object]:
    """Satisfy generation gates without producing clips or frames via MCP tools."""
    from film_pipeline.artifacts.manifest import (
        AssetEntry,
        AssetManifest,
        read_manifest,
        write_manifest,
    )
    from film_pipeline.generation.executor import GenerationExecutor

    if active.get("_text_only_generation_completed"):
        return _ok(text_only=True, completed=1, rows=[])

    executor = GenerationExecutor(_services(rt).artifact_store, rt.provider_adapters)
    shot_rows = executor.load_shot_rows(project_id)
    provider, model = rt.default_video_provider()
    requests: list[dict[str, object]] = []
    for row in shot_rows:
        shot_id = str(row.get("shot_id", "") or row.get("scene_id", "")).strip()
        if not shot_id:
            continue
        requests.append(
            {
                "generation_request_id": f"text-only-{project_id}-{shot_id}",
                "generation_id": f"text-only-{project_id}-{shot_id}",
                "project_id": project_id,
                "shot_id": shot_id,
                "mode": "text_only",
                "provider": provider,
                "model": model,
                "prompt_ref": "",
                "prompt_payload": {"text_only": True, "shot_id": shot_id},
                "reference_refs": [],
                "status": "completed",
            }
        )
    if not requests:
        requests.append(
            {
                "generation_request_id": f"text-only-{project_id}-all",
                "generation_id": f"text-only-{project_id}-all",
                "project_id": project_id,
                "shot_id": "all",
                "mode": "text_only",
                "provider": provider,
                "model": model,
                "prompt_ref": "",
                "prompt_payload": {"text_only": True},
                "reference_refs": [],
                "status": "completed",
            }
        )
    active["generation_requests"] = requests
    active["_text_only_generation_completed"] = True
    stale_codes = {"empty_generation_requests", "no_generation_requests"}
    issues = active.get("issues", [])
    if isinstance(issues, list):
        active["issues"] = [
            issue
            for issue in issues
            if not (isinstance(issue, dict) and issue.get("code") in stale_codes)
        ]

    store = _services(rt).artifact_store
    manifest = read_manifest(project_id, root=store._root)
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
        write_manifest(AssetManifest(project_id=project_id, entries=entries), root=store._root)

    rt.projects[project_id] = active
    rt._persist_project_state(project_id)
    return _ok(text_only=True, completed=len(requests), rows=[])
