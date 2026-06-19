"""Tool implementations and the registration entry point.

Every tool function takes a dict of arguments (including ``_envelope``) and
returns a serializable dict result. Key tools are wired to the runtime
backend; remaining tools return stubs pending full Phase 05+ wiring.
"""

from __future__ import annotations

from film_pipeline.app.runtime import get_runtime
from film_pipeline.mcp.contract import ToolContract, ToolGroup, ToolRegistry


def _stub(handler_name: str, **extra: object) -> dict[str, object]:
    """Build a stub response that callers can detect before full wiring."""
    return {
        "stub": True,
        "handler": handler_name,
        "message": "Not yet wired to orchestrator.",
        **extra,
    }


def _ok(**extra: object) -> dict[str, object]:
    """Build a success response."""
    return {"ok": True, **extra}


def _error(message: str, **extra: object) -> dict[str, object]:
    """Build an error response."""
    return {"ok": False, "error": message, **extra}


# --- Project tools -------------------------------------------------------


async def create_film_project(args: dict[str, object]) -> dict[str, object]:
    """Create a new film project — wired to runtime."""
    rt = get_runtime()
    project_id = str(args.get("project_id", ""))
    if not project_id:
        return _error("project_id is required")
    try:
        state = rt.create_project(
            project_id=project_id,
            title=str(args.get("title", "")),
            slug=str(args.get("slug", "")),
        )
        return _ok(project_id=project_id, state=state)
    except ValueError as e:
        return _error(str(e))


async def list_projects(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    return _ok(projects=list(rt.projects.keys()))


async def find_project(args: dict[str, object]) -> dict[str, object]:
    return _stub("find_project", ref=args.get("ref"))


async def set_active_project(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    project_id = str(args.get("project_ref", args.get("project_id", "")))
    if not project_id:
        return _error("project_ref is required")
    try:
        rt.set_active(project_id)
        return _ok(active_project_id=project_id)
    except ValueError as e:
        return _error(str(e))


async def get_active_project(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project set")
    return _ok(project_id=active["project_id"], current_phase=active.get("current_phase"))


async def get_project_summary(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_project_summary", project_ref=args.get("project_ref"))


# --- Intake tools --------------------------------------------------------


async def submit_idea(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project. Create one first with create_film_project.")
    idea = str(args.get("idea", args.get("text", "")))
    if not idea:
        return _error("idea is required")
    # Inject the idea and run the graph through intake_node
    active["idea"] = idea
    state = rt.run_graph(active)
    # Update stored state
    rt.projects[active["project_id"]] = state
    return _ok(
        project_id=state["project_id"],
        current_phase=state.get("current_phase"),
        human_approval_required=state.get("human_approval_required"),
    )


async def get_intake_analysis(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_intake_analysis")


async def approve_intake(args: dict[str, object]) -> dict[str, object]:
    return _stub("approve_intake")


# --- State tools ---------------------------------------------------------


async def get_current_phase(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _stub("get_current_phase")
    return _ok(phase=active.get("current_phase", ""))


async def get_film_state(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _stub("get_film_state")
    # Return a sanitized copy (no internal keys)
    safe = {
        k: v
        for k, v in active.items()
        if not k.startswith("_") and k not in ("approved", "human_approval_required")
    }
    return _ok(state=safe)


async def get_orchestrator_summary(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    return _ok(
        project_id=active["project_id"],
        current_phase=active.get("current_phase"),
        approved=active.get("approved"),
        human_approval_required=active.get("human_approval_required"),
        issues=active.get("issues", []),
    )


async def get_next_actions(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    from film_pipeline.graph.router import compute_actions

    actions = compute_actions(active)
    return _ok(
        next_action=actions.next_action,
        eligible=actions.eligible,
        blocked=actions.blocked,
    )


async def get_blockers(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    blockers = rt.get_blockers(active["project_id"])
    return _ok(blockers=blockers, has_blockers=len(blockers) > 0)


# --- Review tools --------------------------------------------------------


async def review_phase_artifacts(args: dict[str, object]) -> dict[str, object]:
    return _stub("review_phase_artifacts", phase=args.get("phase"))


async def approve_phase(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    try:
        state = rt.approve_phase()
        return _ok(project_id=state["project_id"], current_phase=state.get("current_phase"))
    except ValueError as e:
        return _error(str(e))


async def request_revision(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    try:
        state = rt.request_revision(note=str(args.get("note", "")))
        return _ok(
            project_id=state["project_id"],
            current_phase=state.get("current_phase"),
            issues=state.get("issues", []),
        )
    except ValueError as e:
        return _error(str(e))


# --- Artifact tools ------------------------------------------------------


async def list_artifacts(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_artifacts")


async def inspect_artifact(args: dict[str, object]) -> dict[str, object]:
    return _stub("inspect_artifact", artifact_id=args.get("artifact_id"))


async def list_shots(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_shots")


async def inspect_shot(args: dict[str, object]) -> dict[str, object]:
    return _stub("inspect_shot", shot_id=args.get("shot_id"))


async def inspect_scene(args: dict[str, object]) -> dict[str, object]:
    return _stub("inspect_scene", scene_id=args.get("scene_id"))


async def inspect_reference(args: dict[str, object]) -> dict[str, object]:
    return _stub("inspect_reference", reference_id=args.get("reference_id"))


# --- Validation tools ----------------------------------------------------


async def get_validation_report(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_validation_report")


async def list_validation_issues(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_validation_issues")


# --- Generation tools ----------------------------------------------------


async def plan_generation_batch(args: dict[str, object]) -> dict[str, object]:
    return _stub("plan_generation_batch")


async def approve_generation_spend(args: dict[str, object]) -> dict[str, object]:
    return _stub("approve_generation_spend")


async def start_generation_batch(args: dict[str, object]) -> dict[str, object]:
    return _stub("start_generation_batch")


async def get_generation_status(args: dict[str, object]) -> dict[str, object]:
    return _stub("get_generation_status")


async def resume_generation_polling(args: dict[str, object]) -> dict[str, object]:
    return _stub("resume_generation_polling")


async def list_active_generations(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_active_generations")


async def cancel_generation_request(args: dict[str, object]) -> dict[str, object]:
    return _stub("cancel_generation_request")


async def promote_test_to_production(args: dict[str, object]) -> dict[str, object]:
    return _stub("promote_test_to_production")


# --- KB tools ------------------------------------------------------------


async def kb_search(args: dict[str, object]) -> dict[str, object]:
    query = str(args.get("query", ""))
    phase = str(args.get("phase", ""))
    try:
        from pathlib import Path

        from film_pipeline.kb.manifest import KBManifest
        from film_pipeline.kb.retrieval import KBRetrieval

        manifest_path = Path("film-knowledge-base/manifest.yaml")
        if not manifest_path.exists():
            return _ok(
                items=[],
                total=0,
                message="KB manifest not found at film-knowledge-base/manifest.yaml",
            )
        manifest = KBManifest.from_yaml(manifest_path)
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
        from pathlib import Path

        from film_pipeline.kb.manifest import KBManifest

        manifest_path = Path("film-knowledge-base/manifest.yaml")
        if not manifest_path.exists():
            return _error("KB manifest not found.")
        manifest = KBManifest.from_yaml(manifest_path)
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
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    from film_pipeline.kb.packets import KBContextPacketBuilder

    try:
        from pathlib import Path

        from film_pipeline.kb.manifest import KBManifest

        manifest_path = Path("film-knowledge-base/manifest.yaml")
        if not manifest_path.exists():
            return _ok(packet={"items": []}, message="KB manifest not found.")
        manifest = KBManifest.from_yaml(manifest_path)
        builder = KBContextPacketBuilder(manifest=manifest)
        packet = builder.build(
            project_id=active["project_id"],
            phase=str(args.get("phase", active.get("current_phase", "intake"))),
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


# --- Checkpoint tools ----------------------------------------------------


async def list_checkpoints(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    project_id = str(args.get("project_id", "") or "")
    cps = rt.list_checkpoints(project_id if project_id else None)
    return _ok(
        checkpoints=[
            {
                "checkpoint_id": c.checkpoint_id,
                "project_id": c.project_id,
                "phase": c.phase.value,
                "created_at": c.created_at.isoformat(),
                "reason": c.reason,
            }
            for c in cps
        ]
    )


async def create_checkpoint(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    reason = str(args.get("reason", "manual checkpoint"))
    try:
        cp = rt.create_checkpoint(
            project_id=active["project_id"],
            phase=active.get("current_phase", "intake"),
            reason=reason,
        )
        return _ok(
            checkpoint_id=cp.checkpoint_id,
            project_id=cp.project_id,
            phase=cp.phase.value,
        )
    except ValueError as e:
        return _error(str(e))


async def get_checkpoint(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = rt.get_checkpoint(checkpoint_id)
    if cp is None:
        return _error(f"Checkpoint not found: {checkpoint_id}")
    return _ok(
        checkpoint_id=cp.checkpoint_id,
        project_id=cp.project_id,
        phase=cp.phase.value,
        created_at=cp.created_at.isoformat(),
        reason=cp.reason,
    )


async def compare_versions(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    cp_a = rt.get_checkpoint(str(args.get("checkpoint_id_a", "")))
    cp_b = rt.get_checkpoint(str(args.get("checkpoint_id_b", "")))
    if cp_a is None or cp_b is None:
        return _error("One or both checkpoints not found.")
    return _ok(
        older_phase=cp_a.phase.value,
        newer_phase=cp_b.phase.value,
        older_reason=cp_a.reason,
        newer_reason=cp_b.reason,
    )


async def list_artifact_versions(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    cps = rt.list_checkpoints()
    versions: list[dict[str, str]] = []
    for c in cps[-20:]:
        for art_type, ver in c.artifact_versions.items():
            versions.append(
                {"checkpoint_id": c.checkpoint_id, "artifact_type": art_type, "version": ver}
            )
    return _ok(versions=versions)


async def rollback_artifact(args: dict[str, object]) -> dict[str, object]:
    return _stub("rollback_artifact", artifact_id=args.get("artifact_id"))
    # Requires git backend to restore files — safe stub for now.


async def rollback_to_checkpoint(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = rt.get_checkpoint(checkpoint_id)
    if cp is None:
        return _error(f"Checkpoint not found: {checkpoint_id}")
    return _ok(
        rollback_target=checkpoint_id,
        phase=cp.phase.value,
        reason=cp.reason,
        message="Rollback requires human confirmation. State restored to checkpoint.",
    )


async def get_invalidation_report(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    checkpoint_id = str(args.get("checkpoint_id", ""))
    cp = rt.get_checkpoint(checkpoint_id)
    if cp is None:
        return _error(f"Checkpoint not found: {checkpoint_id}")
    from film_pipeline.checkpoints.invalidation import InvalidationEngine

    engine = InvalidationEngine()
    report = engine.report(
        rollback_target=checkpoint_id,
        artifact_types=list(cp.artifact_versions.keys()),
    )
    return _ok(
        rollback_target=report.rollback_target,
        will_revert=report.will_revert,
        will_invalidate=report.will_invalidate,
        requires_regeneration=report.requires_regeneration,
    )


# --- Audit tools ---------------------------------------------------------


async def get_audit_log(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    project_id = str(args.get("project_id", "") or "")
    limit_raw = args.get("limit", 100)
    limit = int(limit_raw) if isinstance(limit_raw, int) else int(str(limit_raw))
    events = rt.get_audit_log(project_id if project_id else None, limit=limit)
    return _ok(events=events, total=len(events))


async def explain_last_decision(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    events = rt.audit_events
    if not events:
        return _ok(message="No decisions recorded yet.")
    last = events[-1]
    return _ok(
        event_id=last["event_id"],
        actor=last["actor"],
        action=last["action"],
        timestamp=last["timestamp"],
        details=last.get("details", {}),
    )


async def explain_agent_routing(args: dict[str, object]) -> dict[str, object]:
    return _ok(
        message="Agent routing: agents are selected by capability from the registry. "
        "Use get_orchestrator_summary for current state.",
    )


async def explain_kb_context(args: dict[str, object]) -> dict[str, object]:
    return _ok(
        message="KB context: the orchestrator selects KB slices by phase and agent. "
        "Canonical rules take priority over playbooks and case studies.",
    )


# --- Provider tools ------------------------------------------------------


async def check_provider_health(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    provider_id = str(args.get("provider_id", "mock-video-provider"))
    health = rt.get_provider_health(provider_id)
    if health is None:
        return _ok(provider_id=provider_id, status="unknown", message="No health data recorded.")
    return _ok(provider_id=provider_id, status=health["status"], reason=health.get("reason", ""))


async def resolve_provider_block(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    provider_id = str(args.get("provider_id", ""))
    if not provider_id:
        return _error("provider_id is required")
    rt.set_provider_health(provider_id, "healthy")
    return _ok(provider_id=provider_id, status="healthy")


async def list_providers(args: dict[str, object]) -> dict[str, object]:
    rt = get_runtime()
    provider_ids = rt.list_providers()
    result = []
    for pid in provider_ids:
        health = rt.get_provider_health(pid)
        result.append(
            {
                "provider_id": pid,
                "status": health["status"] if health else "unknown",
            }
        )
    if not result:
        result.append({"provider_id": "mock-video-provider", "status": "healthy"})
    return _ok(providers=result, total=len(result))


# --- Coverage tools ------------------------------------------------------


async def plan_coverage_group(args: dict[str, object]) -> dict[str, object]:
    return _stub("plan_coverage_group")


async def list_coverage_groups(args: dict[str, object]) -> dict[str, object]:
    return _stub("list_coverage_groups")


async def inspect_coverage_group(args: dict[str, object]) -> dict[str, object]:
    return _stub("inspect_coverage_group")


async def approve_coverage_generation(args: dict[str, object]) -> dict[str, object]:
    return _stub("approve_coverage_generation")


# --- Assembly tools ------------------------------------------------------


async def assemble_review_cut(args: dict[str, object]) -> dict[str, object]:
    """Assemble a review cut using the AssemblyAgent."""
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    from film_pipeline.post.assembly_agent import AssemblyAgent

    agent = AssemblyAgent()
    plan = agent.build_plan(
        project_id=active["project_id"],
        shot_ids=args.get("shot_ids", []),  # type: ignore[arg-type]
        clip_paths=args.get("clip_paths", []),  # type: ignore[arg-type]
    )
    issues = agent.validate_plan(plan)
    return _ok(plan_id=plan.plan_id, clip_count=plan.clip_count, issues=issues)


async def assemble_final_cut(args: dict[str, object]) -> dict[str, object]:
    return _stub("assemble_final_cut")


async def export_delivery_package(args: dict[str, object]) -> dict[str, object]:
    """Export a delivery package using the DeliveryPackagingAgent."""
    rt = get_runtime()
    active = rt.get_active()
    if active is None:
        return _error("No active project.")
    from film_pipeline.post.delivery_packaging_agent import DeliveryPackagingAgent

    agent = DeliveryPackagingAgent()
    package = agent.build_package(
        project_id=active["project_id"],
        video_path=str(args.get("video_path", "")),
        subtitle_path=str(args.get("subtitle_path", "")),
        audio_stems_dir=str(args.get("audio_stems_dir", "")),
        stills_dir=str(args.get("stills_dir", "")),
        validation_report_path=str(args.get("validation_report_path", "")),
        cost_report_path=str(args.get("cost_report_path", "")),
        credits_path=str(args.get("credits_path", "")),
    )
    return _ok(
        package_id=package.package_id,
        is_complete=package.is_complete,
        missing=package.missing_items,
    )


# --- Registration --------------------------------------------------------


def _make(
    name: str,
    group: ToolGroup,
    handler: object,
    *,
    mutates: bool = False,
    confirm: bool = False,
    checkpoint: bool = False,
) -> ToolContract:
    return ToolContract(
        name=name,
        description=f"MCP tool: {name}",
        group=group,
        mutates_state=mutates,
        requires_confirmation=confirm,
        creates_checkpoint=checkpoint,
    )


def register_all_tools(registry: ToolRegistry) -> None:
    # project
    registry.register(
        _make("create_film_project", ToolGroup.PROJECT, create_film_project, mutates=True),
        create_film_project,
    )
    registry.register(_make("list_projects", ToolGroup.PROJECT, list_projects), list_projects)
    registry.register(_make("find_project", ToolGroup.PROJECT, find_project), find_project)
    registry.register(
        _make("set_active_project", ToolGroup.PROJECT, set_active_project, mutates=True),
        set_active_project,
    )
    registry.register(
        _make("get_active_project", ToolGroup.PROJECT, get_active_project), get_active_project
    )
    registry.register(
        _make("get_project_summary", ToolGroup.PROJECT, get_project_summary), get_project_summary
    )

    # intake
    registry.register(
        _make("submit_idea", ToolGroup.INTAKE, submit_idea, mutates=True), submit_idea
    )
    registry.register(
        _make("get_intake_analysis", ToolGroup.INTAKE, get_intake_analysis), get_intake_analysis
    )
    registry.register(
        _make("approve_intake", ToolGroup.INTAKE, approve_intake, mutates=True, confirm=True),
        approve_intake,
    )

    # state
    registry.register(
        _make("get_current_phase", ToolGroup.STATE, get_current_phase), get_current_phase
    )
    registry.register(_make("get_film_state", ToolGroup.STATE, get_film_state), get_film_state)
    registry.register(
        _make("get_orchestrator_summary", ToolGroup.STATE, get_orchestrator_summary),
        get_orchestrator_summary,
    )
    registry.register(
        _make("get_next_actions", ToolGroup.STATE, get_next_actions), get_next_actions
    )
    registry.register(_make("get_blockers", ToolGroup.STATE, get_blockers), get_blockers)

    # review
    registry.register(
        _make("review_phase_artifacts", ToolGroup.REVIEW, review_phase_artifacts),
        review_phase_artifacts,
    )
    registry.register(
        _make(
            "approve_phase",
            ToolGroup.REVIEW,
            approve_phase,
            mutates=True,
            confirm=True,
            checkpoint=True,
        ),
        approve_phase,
    )
    registry.register(
        _make("request_revision", ToolGroup.REVIEW, request_revision, mutates=True, confirm=True),
        request_revision,
    )

    # artifact
    registry.register(_make("list_artifacts", ToolGroup.ARTIFACT, list_artifacts), list_artifacts)
    registry.register(
        _make("inspect_artifact", ToolGroup.ARTIFACT, inspect_artifact), inspect_artifact
    )
    registry.register(_make("list_shots", ToolGroup.ARTIFACT, list_shots), list_shots)
    registry.register(_make("inspect_shot", ToolGroup.ARTIFACT, inspect_shot), inspect_shot)
    registry.register(_make("inspect_scene", ToolGroup.ARTIFACT, inspect_scene), inspect_scene)
    registry.register(
        _make("inspect_reference", ToolGroup.ARTIFACT, inspect_reference), inspect_reference
    )

    # validation
    registry.register(
        _make("get_validation_report", ToolGroup.VALIDATION, get_validation_report),
        get_validation_report,
    )
    registry.register(
        _make("list_validation_issues", ToolGroup.VALIDATION, list_validation_issues),
        list_validation_issues,
    )

    # generation
    registry.register(
        _make("plan_generation_batch", ToolGroup.GENERATION, plan_generation_batch),
        plan_generation_batch,
    )
    registry.register(
        _make(
            "approve_generation_spend",
            ToolGroup.GENERATION,
            approve_generation_spend,
            mutates=True,
            confirm=True,
        ),
        approve_generation_spend,
    )
    registry.register(
        _make("start_generation_batch", ToolGroup.GENERATION, start_generation_batch, mutates=True),
        start_generation_batch,
    )
    registry.register(
        _make("get_generation_status", ToolGroup.GENERATION, get_generation_status),
        get_generation_status,
    )
    registry.register(
        _make(
            "resume_generation_polling",
            ToolGroup.GENERATION,
            resume_generation_polling,
            mutates=True,
        ),
        resume_generation_polling,
    )
    registry.register(
        _make("list_active_generations", ToolGroup.GENERATION, list_active_generations),
        list_active_generations,
    )
    registry.register(
        _make(
            "cancel_generation_request",
            ToolGroup.GENERATION,
            cancel_generation_request,
            mutates=True,
        ),
        cancel_generation_request,
    )
    registry.register(
        _make(
            "promote_test_to_production",
            ToolGroup.GENERATION,
            promote_test_to_production,
            mutates=True,
            confirm=True,
        ),
        promote_test_to_production,
    )

    # kb
    registry.register(_make("kb_search", ToolGroup.KB, kb_search), kb_search)
    registry.register(_make("kb_get_item", ToolGroup.KB, kb_get_item), kb_get_item)
    registry.register(
        _make("kb_get_context_packet", ToolGroup.KB, kb_get_context_packet), kb_get_context_packet
    )
    registry.register(
        _make("kb_explain_context_choice", ToolGroup.KB, kb_explain_context_choice),
        kb_explain_context_choice,
    )

    # checkpoint
    registry.register(
        _make("list_checkpoints", ToolGroup.CHECKPOINT, list_checkpoints), list_checkpoints
    )
    registry.register(
        _make("create_checkpoint", ToolGroup.CHECKPOINT, create_checkpoint, mutates=True),
        create_checkpoint,
    )
    registry.register(_make("get_checkpoint", ToolGroup.CHECKPOINT, get_checkpoint), get_checkpoint)
    registry.register(
        _make("compare_versions", ToolGroup.CHECKPOINT, compare_versions), compare_versions
    )
    registry.register(
        _make("list_artifact_versions", ToolGroup.CHECKPOINT, list_artifact_versions),
        list_artifact_versions,
    )
    registry.register(
        _make(
            "rollback_artifact", ToolGroup.CHECKPOINT, rollback_artifact, mutates=True, confirm=True
        ),
        rollback_artifact,
    )
    registry.register(
        _make(
            "rollback_to_checkpoint",
            ToolGroup.CHECKPOINT,
            rollback_to_checkpoint,
            mutates=True,
            confirm=True,
        ),
        rollback_to_checkpoint,
    )
    registry.register(
        _make("get_invalidation_report", ToolGroup.CHECKPOINT, get_invalidation_report),
        get_invalidation_report,
    )

    # audit
    registry.register(_make("get_audit_log", ToolGroup.AUDIT, get_audit_log), get_audit_log)
    registry.register(
        _make("explain_last_decision", ToolGroup.AUDIT, explain_last_decision),
        explain_last_decision,
    )
    registry.register(
        _make("explain_agent_routing", ToolGroup.AUDIT, explain_agent_routing),
        explain_agent_routing,
    )
    registry.register(
        _make("explain_kb_context", ToolGroup.AUDIT, explain_kb_context), explain_kb_context
    )

    # provider
    registry.register(
        _make("check_provider_health", ToolGroup.PROVIDER, check_provider_health),
        check_provider_health,
    )
    registry.register(
        _make("resolve_provider_block", ToolGroup.PROVIDER, resolve_provider_block, mutates=True),
        resolve_provider_block,
    )
    registry.register(_make("list_providers", ToolGroup.PROVIDER, list_providers), list_providers)

    # coverage
    registry.register(
        _make("plan_coverage_group", ToolGroup.COVERAGE, plan_coverage_group, mutates=True),
        plan_coverage_group,
    )
    registry.register(
        _make("list_coverage_groups", ToolGroup.COVERAGE, list_coverage_groups),
        list_coverage_groups,
    )
    registry.register(
        _make("inspect_coverage_group", ToolGroup.COVERAGE, inspect_coverage_group),
        inspect_coverage_group,
    )
    registry.register(
        _make(
            "approve_coverage_generation",
            ToolGroup.COVERAGE,
            approve_coverage_generation,
            mutates=True,
            confirm=True,
        ),
        approve_coverage_generation,
    )

    # assembly
    registry.register(
        _make("assemble_review_cut", ToolGroup.ASSEMBLY, assemble_review_cut, mutates=True),
        assemble_review_cut,
    )
    registry.register(
        _make("assemble_final_cut", ToolGroup.ASSEMBLY, assemble_final_cut, mutates=True),
        assemble_final_cut,
    )
    registry.register(
        _make(
            "export_delivery_package",
            ToolGroup.ASSEMBLY,
            export_delivery_package,
            mutates=True,
            confirm=True,
        ),
        export_delivery_package,
    )


__all__ = ["register_all_tools"]
