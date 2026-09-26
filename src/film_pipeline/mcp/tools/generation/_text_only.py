"""Text-only generation policy: satisfy generation gates without media."""

from __future__ import annotations

from typing import Any

from film_pipeline.filmspec import (
    is_text_only_policy as is_text_only_policy,
)
from film_pipeline.filmspec import text_only_generation_requests

from ..helpers import _ok, _services


def _text_only_requests(
    project_id: str,
    shot_rows: list[dict[str, Any]],
    provider: str,
    model: str,
) -> list[dict[str, Any]]:
    """One completed request per shot row, or a single fallback row."""
    return text_only_generation_requests(project_id, shot_rows, provider, model)


def _apply_text_only_state(active: dict[str, Any], requests: list[dict[str, object]]) -> None:
    """Record requests, flag completion, and drop stale blocking issues."""
    active["generation_requests"] = requests
    active["_text_only_generation_completed"] = True
    from film_pipeline.filmspec import STALE_GENERATION_REQUEST_CODES
    from film_pipeline.orchestration.state_schema import remove_issues_by_code

    remove_issues_by_code(active, STALE_GENERATION_REQUEST_CODES)


def _ensure_text_only_manifest_entry(store: Any, project_id: str) -> None:
    """Add the text-only-delivery entry to the asset manifest once."""
    from film_pipeline.storage.manifest import (
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
