"""Knowledge-base search and context-packet tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field

from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec

from .helpers import (
    _error,
    _ok,
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


async def kb_search(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
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


async def kb_get_item(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
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


async def kb_get_context_packet(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    _ = args
    state = ctx.project_state()
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


async def kb_explain_context_choice(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    return _ok(
        message="KB context is selected by phase and agent capability. "
        "Canonical rules (authority=CANONICAL) take priority over playbooks and case studies. "
        "Use kb_get_context_packet to see the current packet.",
    )


# ── Tool declarations ────────────────────────────────────────────────────────
# Declared next to the handlers they describe (doc 04 slice 1).


class KbSearchArgs(ToolArgs):
    """Arguments for `kb_search`."""

    query: str = Field(description="What to search the knowledge base for.")
    phase: str = Field(default="", description="Restrict to one phase; empty searches all.")


class KbGetItemArgs(ToolArgs):
    """Arguments for `kb_get_item`."""

    item_id: str = Field(description="Knowledge-base item to fetch.")


class KbGetContextPacketArgs(ToolArgs):
    """Arguments for `kb_get_context_packet`."""

    agent_id: str = Field(default="", description="Agent the packet is for.")
    phase: str = Field(default="", description="Phase the packet is for.")
    task: str = Field(default="", description="Task description to select context for.")


class KbExplainContextChoiceArgs(ToolArgs):
    """Arguments for `kb_explain_context_choice` (none)."""


KB_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="kb_search",
        group=ToolGroup.KB,
        description="Search the knowledge base by tag or text, optionally within one phase.",
        args=KbSearchArgs,
        handler=kb_search,
    ),
    ToolSpec(
        name="kb_get_item",
        group=ToolGroup.KB,
        description="Fetch one knowledge-base item by id.",
        args=KbGetItemArgs,
        handler=kb_get_item,
    ),
    ToolSpec(
        name="kb_get_context_packet",
        group=ToolGroup.KB,
        description="Build the knowledge-base context packet an agent would receive.",
        args=KbGetContextPacketArgs,
        handler=kb_get_context_packet,
        active_project=True,
    ),
    ToolSpec(
        name="kb_explain_context_choice",
        group=ToolGroup.KB,
        description="Explain how context selection works for each phase.",
        args=KbExplainContextChoiceArgs,
        handler=kb_explain_context_choice,
    ),
)
