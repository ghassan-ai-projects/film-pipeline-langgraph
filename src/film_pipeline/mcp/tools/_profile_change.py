"""Mid-project profile-change workflow: ``propose`` and ``approve`` tools.

Split from ``mcp/tools/config.py`` so the read-only profile/runtime
introspection tools stay separate from the write path that validates
requested stacks, resolves and diffs configurations, persists proposal,
approval, and project-config artifacts, and invalidates downstream work.
``config`` re-exports the two public tools so original import paths keep
resolving.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from film_pipeline.checkpoints.invalidation import InvalidationEngine
from film_pipeline.config.profile_resolver import (
    config_diff,
    load_profile_stack,
    merge_profile_changes,
    requested_profile_changes,
    resolve_config_or_error,
    resolve_config_pair,
    resolved_config_state_keys,
    resolved_raw,
)
from film_pipeline.mcp.tools.context import ToolContext
from film_pipeline.mcp.tools.spec import ToolArgs, ToolGroup, ToolSpec
from film_pipeline.schemas.approval import ProfileChangeApproval, ProfileChangeProposal
from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef
from film_pipeline.schemas.base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.storage.contract import sanitize_artifact_id

from .helpers import (
    _error,
    _ok,
    _services,
    register_profile_providers,
)


async def propose_profile_change(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Propose a mid-project change to the profile stack.

    Validates the requested profiles, resolves the projected configuration,
    computes a diff against the current resolved config, and stores a pending
    ``ProfileChangeProposal`` artifact. The change is not applied until a
    human approves it via ``approve_profile_change``.
    """
    rt = ctx.runtime
    state = ctx.project_state()
    project_id = str(state["project_id"])

    reason = str(args.get("reason", "")).strip()
    if not reason:
        return _error("reason is required.")
    proposed_by = str(args.get("proposed_by", "operator")).strip() or "operator"

    changes = requested_profile_changes(args)
    if not changes:
        return _error("At least one profile change is required.")

    current_stack = load_profile_stack(state)
    new_stack = merge_profile_changes(current_stack, changes)

    configs = resolve_config_pair(current_stack, new_stack)
    if isinstance(configs, str):
        return _error(configs)
    resolved_current, resolved_new = configs
    diff = config_diff(resolved_raw(resolved_current), resolved_raw(resolved_new))

    proposal = _new_proposal(
        project_id,
        proposed_by,
        reason,
        int(state.get("profile_version", 0)),
        (current_stack, new_stack),
        diff,
    )
    proposal_ref = _save_proposal_artifact(rt, project_id, proposal)

    return _ok(
        proposal_id=proposal.proposal_id,
        project_id=project_id,
        previous_profile_stack=current_stack,
        proposed_profile_stack=new_stack,
        projected_config_diff=diff,
        proposal_ref=proposal_ref,
        message="Profile change proposed. Approve with approve_profile_change.",
    )


async def approve_profile_change(ctx: ToolContext, args: dict[str, object]) -> dict[str, object]:
    """Approve a pending profile-change proposal and apply it to the project.

    Requires ``confirmed=True``. Bumps ``profile_version``, re-resolves the
    configuration, persists a new ``project_config`` artifact, invalidates
    downstream artifacts, and records the approval.
    """
    rt = ctx.runtime
    state = ctx.project_state()
    project_id = str(state["project_id"])

    proposal_id = str(args.get("proposal_id", "")).strip()
    if not proposal_id:
        return _error("proposal_id is required.")

    approved_by = str(args.get("approved_by", "operator")).strip() or "operator"
    note = str(args.get("note", ""))

    proposal = _load_pending_proposal(rt, project_id, proposal_id)
    if isinstance(proposal, str):
        return _error(proposal)

    new_stack = dict(proposal.proposed_profile_stack)
    resolved = resolve_config_or_error(new_stack)
    if isinstance(resolved, str):
        return _error(resolved)

    new_version = int(state.get("profile_version", 0)) + 1
    _apply_resolved_config(state, new_stack, resolved, new_version)
    register_profile_providers(rt, new_stack, resolved_raw(resolved))

    config_ref, inv_ref = _commit_profile_config(
        rt, project_id, proposal_id, new_version, resolved, new_stack
    )

    approval = _approval_record(proposal, approved_by, note, new_version, config_ref, inv_ref)
    approval_ref = _save_approval_artifact(rt, project_id, approval)
    _finalize_approval(rt, project_id, proposal, approval)

    return _ok(
        approval_id=approval.approval_id,
        proposal_id=proposal_id,
        project_id=project_id,
        profile_version=new_version,
        profile_stack=new_stack,
        resolved_config_ref=config_ref,
        invalidation_report_ref=inv_ref,
        approval_ref=approval_ref,
        message="Profile change approved and applied.",
    )


def _load_pending_proposal(
    rt: Any,
    project_id: str,
    proposal_id: str,
) -> ProfileChangeProposal | str:
    """Load the proposal, returning an error message when missing or not pending."""
    proposal = _load_proposal_artifact(rt, project_id, proposal_id)
    if proposal is None:
        return f"Profile change proposal '{proposal_id}' not found."
    if proposal.status != "pending":
        return f"Proposal '{proposal_id}' is {proposal.status}, not pending."
    return proposal


def _new_proposal(
    project_id: str,
    proposed_by: str,
    reason: str,
    previous_version: int,
    stacks: tuple[dict[str, str], dict[str, str]],
    diff: dict[str, Any],
) -> ProfileChangeProposal:
    """Build the pending ``ProfileChangeProposal`` body."""
    current_stack, new_stack = stacks
    return ProfileChangeProposal(
        proposal_id=f"profile-change:{uuid4().hex[:8]}",
        project_id=project_id,
        proposed_by=proposed_by,
        reason=reason,
        previous_profile_stack=current_stack,
        proposed_profile_stack=new_stack,
        previous_profile_version=previous_version,
        projected_config_diff=diff,
        status="pending",
        created_at=datetime.now(UTC),
    )


def _apply_resolved_config(
    state: Any,
    new_stack: dict[str, str],
    resolved: dict[str, object],
    new_version: int,
) -> None:
    """Bump the project's profile version and cache the resolved configuration."""
    state["profile_version"] = new_version
    state.update(resolved_config_state_keys(new_stack, resolved))


def _commit_profile_config(
    rt: Any,
    project_id: str,
    proposal_id: str,
    profile_version: int,
    resolved: dict[str, object],
    profile_stack: dict[str, str],
) -> tuple[str, str]:
    """Persist the resolved config artifact and invalidate downstream artifacts."""
    config_ref = _save_resolved_config_artifact(
        rt, project_id, profile_version, resolved_raw(resolved), profile_stack
    )
    inv_ref = _invalidate_for_profile_change(rt, project_id, proposal_id)
    return config_ref, inv_ref


def _approval_record(
    proposal: ProfileChangeProposal,
    approved_by: str,
    note: str,
    profile_version: int,
    config_ref: str,
    invalidation_report_ref: str,
) -> ProfileChangeApproval:
    """Build the approval record for an approved proposal."""
    return ProfileChangeApproval(
        approval_id=f"profile-approval:{uuid4().hex[:8]}",
        proposal_id=proposal.proposal_id,
        project_id=proposal.project_id,
        approved_by=approved_by,
        note=note,
        profile_version=profile_version,
        new_profile_stack=dict(proposal.proposed_profile_stack),
        new_resolved_config_ref=config_ref,
        invalidation_report_ref=invalidation_report_ref,
        created_at=datetime.now(UTC),
    )


def _finalize_approval(
    rt: Any,
    project_id: str,
    proposal: ProfileChangeProposal,
    approval: ProfileChangeApproval,
) -> None:
    """Mark the proposal approved, persist project state, and record the audit entry."""
    _save_proposal_artifact(rt, project_id, proposal.model_copy(update={"status": "approved"}))
    rt.persist_project_state(project_id)
    rt.record_audit(
        approval.approved_by,
        "approve_profile_change",
        project_id=project_id,
        proposal_id=approval.proposal_id,
        profile_version=str(approval.profile_version),
        approval_id=approval.approval_id,
    )


class _ProjectConfigBody(BaseModel):
    profile_version: int
    profile_stack: dict[str, str]
    resolved_config: dict[str, object]


def _save_intake_artifact(
    rt: Any,
    project_id: str,
    artifact_id: str,
    body: BaseModel,
    *,
    artifact_type: ArtifactType,
    status: ArtifactStatus,
    created_by: str,
) -> str:
    """Persist ``body`` as the next version of an intake-phase artifact.

    Returns the ``artifact:<phase>:<id>:v<version>`` reference used by tool
    responses.
    """
    store = _services(rt).artifact_store
    version = store.next_version(project_id, "intake", artifact_id)
    meta = ArtifactMetadata(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        project_id=project_id,
        phase=FilmPhase("intake"),
        version=version,
        status=status,
        created_by=created_by,
        created_at=datetime.now(UTC),
    )
    ref: ArtifactRef = store.save(body, meta)
    return ref.to_string()


def _save_proposal_artifact(
    rt: Any,
    project_id: str,
    proposal: ProfileChangeProposal,
) -> str:
    return _save_intake_artifact(
        rt,
        project_id,
        _proposal_artifact_id(proposal.proposal_id),
        proposal,
        artifact_type=ArtifactType.REVISION_REQUEST,
        status=ArtifactStatus.CANDIDATE,
        created_by="propose_profile_change",
    )


def _proposal_artifact_id(proposal_id: str) -> str:
    return f"profile_change_proposal__{sanitize_artifact_id(proposal_id)}"


def _load_proposal_artifact(
    rt: Any,
    project_id: str,
    proposal_id: str,
) -> ProfileChangeProposal | None:
    store = _services(rt).artifact_store
    artifact_id = _proposal_artifact_id(proposal_id)
    version = store.latest_version(project_id, "intake", artifact_id)
    if version <= 0:
        return None
    try:
        data = store.load(project_id, FilmPhase("intake"), artifact_id, version)
        return ProfileChangeProposal.model_validate(data)
    except Exception:
        return None


def _save_approval_artifact(
    rt: Any,
    project_id: str,
    approval: ProfileChangeApproval,
) -> str:
    return _save_intake_artifact(
        rt,
        project_id,
        f"profile_change_approval__{sanitize_artifact_id(approval.approval_id)}",
        approval,
        artifact_type=ArtifactType.APPROVAL_RECORD,
        status=ArtifactStatus.APPROVED,
        created_by="approve_profile_change",
    )


def _save_resolved_config_artifact(
    rt: Any,
    project_id: str,
    profile_version: int,
    resolved_config: dict[str, object],
    profile_stack: dict[str, str],
) -> str:
    body = _ProjectConfigBody(
        profile_version=profile_version,
        profile_stack=profile_stack,
        resolved_config=resolved_config,
    )
    return _save_intake_artifact(
        rt,
        project_id,
        f"project_config_v{profile_version}",
        body,
        artifact_type=ArtifactType.PROJECT_CONFIG,
        status=ArtifactStatus.APPROVED,
        created_by="approve_profile_change",
    )


def _invalidate_for_profile_change(rt: Any, project_id: str, proposal_id: str) -> str:

    engine = InvalidationEngine()
    report = engine.report(
        rollback_target=f"profile-change:{proposal_id}",
        artifact_types=["project_config", "prompt_package", "generation_plan", "coverage_group"],
    )
    return _save_intake_artifact(
        rt,
        project_id,
        f"invalidation_report_profile_change__{sanitize_artifact_id(proposal_id)}",
        report,
        artifact_type=ArtifactType.INVALIDATION_REPORT,
        status=ArtifactStatus.CANDIDATE,
        created_by="approve_profile_change",
    )


# ── Tool declarations ────────────────────────────────────────────────────────
# Declared next to the handlers they describe (doc 04 slice 1).


class ProposeProfileChangeArgs(ToolArgs):
    """Arguments for `propose_profile_change`.

    The five profile fields are the stack `PROFILE_STACK_KEYS` reads; a blank one
    leaves that slot unchanged.
    """

    reason: str = Field(default="", description="Why the change is proposed.")
    proposed_by: str = Field(default="", description="Who proposed it.")
    film_type_profile: str = Field(default="", description="New film-type profile stem.")
    quality_profile: str = Field(default="", description="New quality profile stem.")
    provider_profile: str = Field(default="", description="New provider profile stem.")
    review_profile: str = Field(default="", description="New review profile stem.")
    auto_approve_profile: str = Field(default="", description="New auto-approve profile stem.")


class ApproveProfileChangeArgs(ToolArgs):
    """Arguments for `approve_profile_change`."""

    proposal_id: str = Field(description="Pending proposal to approve.")
    note: str = Field(default="", description="Note to record with the approval.")
    approved_by: str = Field(default="", description="Who approved it.")


PROFILE_CHANGE_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="propose_profile_change",
        group=ToolGroup.CONFIG,
        description="Propose a mid-project change to the profile stack for human approval.",
        args=ProposeProfileChangeArgs,
        handler=propose_profile_change,
        mutates=True,
        active_project=True,
    ),
    ToolSpec(
        name="approve_profile_change",
        group=ToolGroup.CONFIG,
        description="Approve a pending profile change and apply it to the project.",
        args=ApproveProfileChangeArgs,
        handler=approve_profile_change,
        mutates=True,
        confirm=True,
        active_project=True,
    ),
)
