"""Knowledge-base search and context-packet tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .helpers import (
    _error,
    _ok,
    require_project_state,
)

if TYPE_CHECKING:
    from film_pipeline.kb.manifest import KBManifest


def _load_kb_manifest() -> KBManifest | None:
    """Parse the knowledge-base manifest from its canonical path.

    Imports are deferred to call time so tests can patch
    ``film_pipeline.kb.paths.kb_manifest_path``. Returns ``None`` when no
    manifest exists on disk yet.
    """
    from film_pipeline.kb.manifest import KBManifest
    from film_pipeline.kb.paths import kb_manifest_path

    manifest_path = kb_manifest_path()
    if not manifest_path.exists():
        return None
    return KBManifest.from_yaml(manifest_path)


async def kb_search(args: dict[str, object]) -> dict[str, object]:
    query = str(args.get("query", ""))
    phase = str(args.get("phase", ""))
    try:
        from film_pipeline.kb.retrieval import KBRetrieval

        manifest = _load_kb_manifest()
        if manifest is None:
            return _ok(
                items=[],
                total=0,
                message="KB manifest not found.",
            )
        retrieval = KBRetrieval(manifest)
        items = retrieval.by_tags(
            phase=phase if phase else None,
        )
        return _ok(
            items=[
                {
                    "id": i.id,
                    "title": i.title,
                    "authority": i.authority.value,
                    "phases": i.applies_to_phases,
                }
                for i in items[:20]
            ],
            total=len(items),
            query=query,
        )
    except Exception as e:
        return _error(str(e))


async def kb_get_item(args: dict[str, object]) -> dict[str, object]:
    item_id = str(args.get("item_id", ""))
    try:
        manifest = _load_kb_manifest()
        if manifest is None:
            return _error("KB manifest not found.")
        item = manifest.get(item_id)
        if item is None:
            return _error(f"KB item not found: {item_id}")
        return _ok(
            id=item.id,
            title=item.title,
            authority=item.authority.value,
            status=item.status,
            domains=item.domains,
            summary=item.summary,
            applies_to_phases=item.applies_to_phases,
        )
    except Exception as e:
        return _error(str(e))


async def kb_get_context_packet(args: dict[str, object]) -> dict[str, object]:
    state = require_project_state(args)
    from film_pipeline.kb.packets import KBContextPacketBuilder

    try:
        manifest = _load_kb_manifest()
        if manifest is None:
            return _ok(packet={"items": []}, message="KB manifest not found.")
        builder = KBContextPacketBuilder(manifest=manifest)
        packet = builder.build(
            project_id=state["project_id"],
            phase=str(args.get("phase", state.get("current_phase", "intake"))),
            agent_id=str(args.get("agent_id", "orchestrator")),
            task=str(args.get("task", "current phase")),
        )
        return _ok(
            project_id=packet.project_id,
            phase=packet.phase,
            authority_policy_refs=packet.authority_policy_refs,
        )
    except Exception as e:
        return _error(str(e))


async def kb_explain_context_choice(args: dict[str, object]) -> dict[str, object]:
    return _ok(
        message="KB context is selected by phase and agent capability. "
        "Canonical rules (authority=CANONICAL) take priority over playbooks and case studies. "
        "Use kb_get_context_packet to see the current packet.",
    )
