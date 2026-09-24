"""Round-trip serialization and validation tests for every schema.

Each test creates a model with representative data, asserts key invariants,
serializes to JSON, deserializes back, and confirms equality.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TypeVar

import pytest
from pydantic import ValidationError

from film_pipeline.schemas import (
    ActMap,
    AgentHandoff,
    AgentRegistration,
    ApprovalRecord,
    ArtifactMetadata,
    ArtifactRef,
    ArtifactStatus,
    ArtifactType,
    AssemblyManifest,
    AudioPlan,
    AuditLogEntry,
    BranchMetadata,
    BudgetState,
    CameraLanguageBible,
    CameraProfile,
    ChainingConfig,
    CharacterBible,
    CharacterIdentity,
    CharacterTruth,
    CheckpointMetadata,
    ClipOrderEntry,
    ColorPlan,
    ConsensusReport,
    ContinuityLedger,
    ContinuityLedgerEntry,
    CoverageGroup,
    DeliveryPackage,
    EmotionalArc,
    EnvironmentBible,
    EnvironmentFingerprint,
    EnvironmentZone,
    FailureClass,
    FailureDecision,
    FailureRecoveryRecord,
    FilmConstitution,
    FilmPhase,
    FilmType,
    GenerationLedger,
    GenerationLedgerRow,
    GenerationMode,
    GenerationRequest,
    GenerationStatus,
    InvalidationReport,
    IssueRecord,
    IssueSeverity,
    KbAuthority,
    KBConflictRecord,
    KBContextPacket,
    KBExcludedRef,
    KBItemMetadata,
    LightingState,
    Logline,
    MasterFilmMatrix,
    MasterFilmMatrixRow,
    Premise,
    ProjectConfig,
    ProjectIdentity,
    ProjectProfile,
    PromptRegistry,
    PromptRegistryEntry,
    ProviderHealthState,
    ProviderStatus,
    QualityLevel,
    RCTCOPrompt,
    ReferenceIndex,
    ReferenceIndexEntry,
    RelationshipMap,
    ResumeToken,
    ReviewerScore,
    RevisionRequest,
    RollbackOutcome,
    RollbackRecord,
    RoutingDecision,
    SceneIntent,
    SceneList,
    SchemaBase,
    SetupPayoffEntry,
    SpendRecord,
    StateRecord,
    StoryBible,
    TransitionPlan,
    Treatment,
    ValidationIssue,
    ValidationLedgerEntry,
    ValidationModality,
    ValidationReport,
    ValidationScope,
    ValidationStatus,
    Viewpoint,
    VoiceRules,
    WardrobeRules,
)
from film_pipeline.schemas.registries import (
    AgentRegistryEntry,
    CostProfile,
    ModelRegistry,
    ModelRegistryEntry,
    ProviderCapabilities,
    ProviderRegistry,
    ProviderRegistryEntry,
    ValidatorRegistry,
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.validation import AgreementLevel

# --- Helpers --------------------------------------------------------------


def _ts() -> datetime:
    return datetime(2026, 6, 19, 12, 0, 0, tzinfo=UTC)


_T = TypeVar("_T", bound=SchemaBase)


def _round_trip[T: SchemaBase](model: T) -> T:
    """Serialize → deserialize → equality, preserving concrete type."""
    dumped = model.model_dump(mode="json")
    json_str = json.dumps(dumped)
    revived = type(model).model_validate_json(json_str)
    assert revived == model
    return revived


# --- Project --------------------------------------------------------------


def test_project_identity_round_trip() -> None:
    identity = ProjectIdentity(
        project_id="film_2026_0001",
        slug="memory-in-color",
        title="Memory In Color",
        aliases=["painter memory film"],
    )
    out = _round_trip(identity)
    assert out.slug == "memory-in-color"
    assert "painter memory film" in out.aliases


def test_project_profile_minimal() -> None:
    identity = ProjectIdentity(project_id="film_2026_0001", slug="x", title="X")
    profile = ProjectProfile(
        identity=identity,
        film_type=FilmType.NARRATIVE,
        target_runtime_seconds=30,
    )
    out = _round_trip(profile)
    assert out.target_runtime_seconds == 30
    assert out.aspect_ratio == "16:9"
    assert out.delivery_modes == ["mp4"]


def test_project_config_requires_timestamps() -> None:
    identity = ProjectIdentity(project_id="p", slug="s", title="T")
    profile = ProjectProfile(identity=identity, target_runtime_seconds=10)
    cfg = ProjectConfig(
        profile=profile,
        resolved_provider="mock-video-provider",
        resolved_quality="studio",
        resolved_review_strategy="multi_model_panel",
        created_at=_ts(),
        updated_at=_ts(),
    )
    assert cfg.created_at == _ts()


# --- Film Constitution ----------------------------------------------------


def test_film_constitution_invariants() -> None:
    fc = FilmConstitution(
        project_id="film_2026_0001",
        theme="Memory persists in color",
        tone="melancholic",
        emotional_promise="quiet reconciliation",
        visual_language="painterly",
        camera_philosophy="observational",
        quality_bar="festival",
        character_truths=[CharacterTruth(character_id="c1", truth="Leo is patient.")],
        taboo_mistakes=["no exposition dumps"],
    )
    out = _round_trip(fc)
    assert out.character_truths[0].truth == "Leo is patient."
    assert out.taboo_mistakes == ["no exposition dumps"]


# --- Story Bible ----------------------------------------------------------


def test_story_bible_round_trip() -> None:
    logline = Logline(text="A lonely painter reconnects with memory through color.")
    premise = Premise(text="...", dramatic_question="Can art heal?")
    act_map = ActMap(act1_setup="lonely", act2_confrontation="memory", act3_resolution="accept")
    scenes = SceneList(
        scenes=[
            SceneIntent(
                scene_id="S001",
                dramatic_function="setup",
                emotional_shift="isolated",
                conflict="no audience",
                outcome="longing",
            )
        ]
    )
    treatment = Treatment(text="long text", themes=["memory"], act_map=act_map)
    bible = StoryBible(
        project_id="p",
        logline=logline,
        premise=premise,
        treatment=treatment,
        act_map=act_map,
        scene_list=scenes,
        setup_payoff_map=[
            SetupPayoffEntry(
                setup_scene_id="S001",
                payoff_scene_id="S010",
                description="brush appears",
            )
        ],
    )
    out = _round_trip(bible)
    assert out.scene_list.scenes[0].scene_id == "S001"


# --- Character ------------------------------------------------------------


def test_character_bible_required_fields() -> None:
    cb = CharacterBible(
        character_id="c1",
        project_id="p",
        visual_identity=CharacterIdentity(
            character_id="c1", name="Leo", role="protagonist", identity_block="..."
        ),
        voice_rules=VoiceRules(cadence="slow", vocabulary=["brush", "canvas"]),
        wardrobe_rules=WardrobeRules(baseline="wool sweater"),
        emotional_arc=EmotionalArc(
            start_state="isolated",
            midpoint_state="haunted",
            end_state="peaceful",
        ),
        relationship_map=[RelationshipMap(other_character_id="c2", relation="mentor")],
        must_not_change=["face shape"],
    )
    assert cb.voice_rules.vocabulary == ["brush", "canvas"]


# --- Environment ----------------------------------------------------------


def test_environment_bible_full() -> None:
    zone = EnvironmentZone(
        zone_id="desk_corner",
        description="Desk area",
        allowed_viewpoints=["desk_to_canvas"],
    )
    vp = Viewpoint(viewpoint_id="desk_to_canvas", description="...", lens="35mm")
    ls = LightingState(state_id="act1_night_cool", description="cool blue")
    env = EnvironmentBible(
        environment_id="env:studio",
        project_id="p",
        name="Studio",
        locked_prompt_block="...",
        zones=[zone],
        viewpoints=[vp],
        lighting_states=[ls],
        fingerprint=EnvironmentFingerprint(text="same studio"),
        reference_assets=["ref:env:studio:board:v1"],
        must_not_change=["no extra windows"],
    )
    out = _round_trip(env)
    assert out.zones[0].zone_id == "desk_corner"


# --- Camera ---------------------------------------------------------------


def test_camera_language_bible() -> None:
    cp = CameraProfile(
        profile_id="cam:modern_tense",
        use_case="dramatic dialogue",
        lens="50mm",
        framing="tight",
        movement="static",
        depth_of_field="shallow",
        emotional_meaning="intimate",
    )
    bible = CameraLanguageBible(
        project_id="p", profiles=[cp], default_profile_id="cam:modern_tense"
    )
    assert bible.profiles[0].lens == "50mm"


# --- Matrix ---------------------------------------------------------------


def test_matrix_row_defaults() -> None:
    row = MasterFilmMatrixRow(
        shot_id="S001-01",
        act_id="A1",
        sequence_id="SEQ001",
        scene_id="S001",
        scene_intent_ref="artifact:scene-intent:S001",
        duration_seconds=8,
        priority="hero",
        risk_level="medium",
        characters=["char:leo"],
        environment="env:studio",
        camera_profile="cam:modern_tense",
        chaining=ChainingConfig(return_last_frame=True),
    )
    out = _round_trip(row)
    assert out.status == "planned"
    assert out.chaining.return_last_frame is True


def test_matrix_aggregate() -> None:
    row = MasterFilmMatrixRow(
        shot_id="S001-01",
        act_id="A1",
        sequence_id="SEQ001",
        scene_id="S001",
        scene_intent_ref="x",
        duration_seconds=8,
    )
    cov = CoverageGroup(
        coverage_group_id="cov:S012:reveal",
        scene_id="S012",
        story_moment="brush reveal",
        continuity_event="reveal",
        coverage_type="emotional_reveal",
        required_angles=["master_wide", "close_reaction"],
    )
    matrix = MasterFilmMatrix(project_id="p", rows=[row], coverage_groups=[cov])
    assert matrix.rows[0].shot_id == "S001-01"


# --- Continuity -----------------------------------------------------------


def test_continuity_ledger_entry() -> None:
    entry = ContinuityLedgerEntry(
        shot_id="S001-01",
        action="Leo paints",
        state_in=[StateRecord(label="mood", description="tired")],
        state_out=[StateRecord(label="mood", description="focused")],
        character_state={"leo": "focused"},
        continuity_risks=["lighting change"],
    )
    ledger = ContinuityLedger(project_id="p", entries=[entry])
    assert ledger.entries[0].character_state["leo"] == "focused"


# --- Reference ------------------------------------------------------------


def test_reference_index_entry_locking() -> None:
    e = ReferenceIndexEntry(
        reference_id="ref:char:leo:identity:v1",
        asset_path="characters/CHAR_001/identity-sheet.png",
        asset_type="character_identity_sheet",
        subject_type="character",
        subject_id="char:leo",
        quality_score=84,
        locked=True,
        status=ArtifactStatus.APPROVED,
    )
    assert e.status == ArtifactStatus.APPROVED
    assert e.locked is True


# --- Prompt ---------------------------------------------------------------


def test_rctco_render() -> None:
    p = RCTCOPrompt(
        r="writer",
        c1="draft scene",
        t={"scene_id": "S001"},
        c2=["preserve voice"],
        o_format="json",
        o_schema_ref="script-scene:v1",
    )
    rendered = p.render()
    assert "Role: writer" in rendered
    assert "Draft scene" in rendered or "draft scene" in rendered
    assert "preserve voice" in rendered


def test_prompt_registry_entry() -> None:
    p = PromptRegistryEntry(
        prompt_id="prompt:S001-01:v1",
        agent_id="prompt-composition-agent",
        shot_id="S001-01",
        rctco=RCTCOPrompt(r="x", c1="y"),
    )
    assert p.rctco.c1 == "y"


# --- Generation -----------------------------------------------------------


def test_generation_request_idempotency_key_required() -> None:
    r = GenerationRequest(
        generation_request_id="g1",
        project_id="p",
        shot_id="S001-01",
        provider="mock-video-provider",
        model="mock-fast",
        prompt_ref="prompt:S001-01:v1",
        idempotency_key="k",
    )
    assert r.mode == GenerationMode.TEST


def test_generation_ledger_row_defaults() -> None:
    row = GenerationLedgerRow(
        generation_request_id="g1",
        generation_id="gen:1",
        project_id="p",
        shot_id="S001-01",
        mode=GenerationMode.PRODUCTION,
        provider="seedance",
        model="seedance-2.0",
        prompt_ref="p",
    )
    assert row.status == GenerationStatus.PREPARED
    assert row.next_action == "submit"


def test_resume_token_required_fields() -> None:
    t = ResumeToken(
        resume_token="r",
        project_id="p",
        generation_id="g",
        graph_node="poll",
        last_safe_step="x",
        next_action="poll",
        created_at=_ts(),
    )
    assert t.can_continue_automatically is True


# --- Validation -----------------------------------------------------------


def test_validation_report_statuses() -> None:
    r = ValidationReport(
        validation_id="v1",
        validator_id="scene-writing-validator",
        scope=ValidationScope.SCENE,
        modalities=[ValidationModality.TEXT],
        score=85.0,
        status=ValidationStatus.PASS_WITH_NOTES,
        warnings=[
            ValidationIssue(code="W1", message="dialogue dense", severity=IssueSeverity.WARNING)
        ],
    )
    assert r.warnings[0].code == "W1"


def test_validation_issue_severity_uses_shared_enum() -> None:
    """Typed construction lands on the shared IssueSeverity vocabulary."""
    issue = ValidationIssue(code="W1", message="dense", severity=IssueSeverity.WARNING)
    assert issue.severity is IssueSeverity.WARNING
    assert issue.severity.value == "warning"
    revived = _round_trip(issue)
    assert revived.severity == "warning"
    assert json.loads(json.dumps(revived.model_dump(mode="json")))["severity"] == "warning"


def test_validation_issue_coerces_wire_format_severity() -> None:
    """Persisted JSON carrying a plain severity string validates and normalizes."""
    issue = ValidationIssue.model_validate(
        {"code": "W1", "message": "dense", "severity": "blocking"}
    )
    assert issue.severity is IssueSeverity.BLOCKING


def test_validation_issue_rejects_unknown_severity() -> None:
    with pytest.raises(ValidationError):
        ValidationIssue.model_validate({"code": "X1", "message": "mystery", "severity": "critical"})


@pytest.mark.parametrize("level", ["high", "medium", "low"])
def test_consensus_agreement_level_vocabulary(level: AgreementLevel) -> None:
    report = ConsensusReport(
        review_id="r1",
        agreement_level=level,
        consensus_status=ValidationStatus.PASS,
    )
    assert report.agreement_level == level


def test_consensus_report_rejects_unknown_agreement_level() -> None:
    with pytest.raises(ValidationError):
        ConsensusReport.model_validate(
            {
                "review_id": "r1",
                "agreement_level": "very_high",
                "consensus_status": "pass",
            }
        )


def test_consensus_report() -> None:
    cs = ConsensusReport(
        review_id="r1",
        artifact_refs=["a"],
        reviewers=[
            ReviewerScore(
                model_id="gpt-5",
                validator_id="x",
                score=85,
                status=ValidationStatus.PASS,
            ),
            ReviewerScore(
                model_id="gemini-flash",
                validator_id="x",
                score=81,
                status=ValidationStatus.NEEDS_REVISION,
            ),
        ],
        agreement_level="medium",
        consensus_status=ValidationStatus.NEEDS_REVISION,
        disagreements=["score spread"],
        orchestrator_recommendation="revise",
    )
    assert len(cs.reviewers) == 2


# --- Assembly -------------------------------------------------------------


def test_assembly_manifest_required() -> None:
    m = AssemblyManifest(
        cut_id="cut1",
        project_id="p",
        clip_order=[
            ClipOrderEntry(
                shot_id="S001-01",
                source_asset_ref="assets/S001-01/take-001.mp4",
                in_seconds=0.0,
                out_seconds=8.0,
            )
        ],
        transitions=[
            TransitionPlan(from_shot_id="S001-01", to_shot_id="S001-02", transition_type="cut")
        ],
        audio_plan=AudioPlan(),
        color_plan=ColorPlan(look="warm"),
        duration_total_seconds=30.0,
    )
    assert m.transitions[0].transition_type == "cut"


# --- Artifact / Approval / Revision / Audit ------------------------------


def test_artifact_metadata_invariants() -> None:
    m = ArtifactMetadata(
        artifact_id="artifact:script:S001:v1",
        artifact_type=ArtifactType.SCRIPT,
        project_id="p",
        phase=FilmPhase.SCRIPT,
        version=1,
        created_by="screenwriter-agent",
        created_at=_ts(),
        parents=[ArtifactRef(artifact_id="artifact:scene-intent:S001:v1", version=1)],
    )
    assert m.status == ArtifactStatus.CANDIDATE


def test_approval_record() -> None:
    a = ApprovalRecord(
        approval_id="ap1",
        project_id="p",
        phase=FilmPhase.SCRIPT,
        action="approve",
        note="ok",
        approver_id="human:owner",
        created_at=_ts(),
    )
    assert a.actor_type == "human"


def test_revision_request() -> None:
    r = RevisionRequest(
        revision_id="rev1",
        project_id="p",
        phase=FilmPhase.SCRIPT,
        requester_id="human:owner",
        note="dialogue too dense",
        from_version=1,
        created_at=_ts(),
    )
    assert r.to_version is None


def test_audit_log_entry() -> None:
    e = AuditLogEntry(
        entry_id="e1",
        project_id="p",
        timestamp=_ts(),
        actor_type="orchestrator",
        actor_id="orchestrator-agent",
        action="phase_advanced",
        cost_estimate_usd=2.5,
    )
    assert e.action == "phase_advanced"


# --- KB -------------------------------------------------------------------


def test_kb_item_metadata() -> None:
    item = KBItemMetadata(
        id="kb.policy.prompt.rctco.v1",
        title="RCTCO Prompt Framework",
        authority=KbAuthority.CANONICAL,
        domains=["prompting"],
        applies_to_phases=["all"],
        summary="Role/Core Task/Context/Constraints/Output",
    )
    assert item.authority == KbAuthority.CANONICAL


def test_kb_context_packet_excluded_refs() -> None:
    pkt = KBContextPacket(
        kb_context_id="kbctx:x",
        project_id="p",
        phase="generation",
        agent_id="a",
        task="t",
        excluded_refs=[KBExcludedRef(ref="kb.archive.x", reason="superseded")],
    )
    assert pkt.excluded_refs[0].reason == "superseded"


def test_kb_conflict_record() -> None:
    c = KBConflictRecord(
        conflict_id="c1",
        items=["kb.x", "kb.y"],
        description="conflict",
        detected_at=_ts(),
    )
    assert c.resolved is False


# --- Budget ---------------------------------------------------------------


def test_budget_state_remaining() -> None:
    b = BudgetState(project_id="p", cap_usd=10.0, spent_usd=3.0)
    assert b.remaining_usd == 7.0


def test_spend_record() -> None:
    s = SpendRecord(
        spend_id="s1",
        project_id="p",
        generation_id="g1",
        provider="seedance",
        amount_usd=1.0,
        mode="test",
        created_at=_ts(),
    )
    assert s.amount_usd == 1.0


# --- Provider health ------------------------------------------------------


def test_provider_health_blocked() -> None:
    s = ProviderHealthState(
        provider_id="seedance",
        status=ProviderStatus.BLOCKED_QUOTA,
        blocked_reason="quota_exhausted",
    )
    assert s.status == ProviderStatus.BLOCKED_QUOTA


@pytest.mark.parametrize("state", ["ok", "low", "exhausted"])
def test_provider_health_quota_and_credit_states_accept_contract_values(state: str) -> None:
    s = ProviderHealthState.model_validate(
        {"provider_id": "seedance", "quota_state": state, "credit_state": state}
    )
    assert s.quota_state == state
    assert s.credit_state == state


@pytest.mark.parametrize("field", ["quota_state", "credit_state"])
def test_provider_health_rejects_invalid_state_values(field: str) -> None:
    with pytest.raises(ValidationError):
        ProviderHealthState.model_validate({"provider_id": "seedance", field: "unknown"})


# --- Failure decisions ---------------------------------------------------


def test_failure_decision_blocking() -> None:
    d = FailureDecision(
        decision_id="fd1",
        project_id="p",
        phase="generation",
        error_class=FailureClass.PROVIDER_ACCOUNT,
        severity="blocking",
        safe_to_retry=False,
        safe_to_continue_other_work=True,
        next_graph_action="human_escalation",
        human_message="Provider has no remaining credit.",
    )
    assert d.error_class == FailureClass.PROVIDER_ACCOUNT
    assert d.severity == "blocking"
    assert d.safe_to_retry is False
    assert d.safe_to_continue_other_work is True


def test_failure_decision_recoverable() -> None:
    d = FailureDecision(
        decision_id="fd2",
        project_id="p",
        phase="generation",
        error_class=FailureClass.RECOVERABLE_EXECUTION,
        severity="non_blocking",
        safe_to_retry=True,
        next_graph_action="retry",
        human_message="Timeout — safe to retry.",
    )
    assert d.severity == "non_blocking"
    assert d.safe_to_retry is True
    assert d.next_graph_action == "retry"


def test_failure_recovery_record() -> None:
    r = FailureRecoveryRecord(
        recovery_id="rec1",
        failure_decision_id="fd1",
        project_id="p",
        phase="generation",
        attempt_count=1,
    )
    assert r.attempt_count == 1
    assert r.resolved is False
    assert r.max_attempts == 3


# --- Issue ---------------------------------------------------------------


def test_issue_record_resolve() -> None:
    i = IssueRecord(
        issue_id="i1",
        project_id="p",
        phase="generation",
        severity=IssueSeverity.BLOCKING,
        code="IDENTITY_DRIFT",
        message="face drifted",
        created_at=_ts(),
    )
    assert not i.resolved


# --- Checkpoint ----------------------------------------------------------


def test_checkpoint_metadata() -> None:
    c = CheckpointMetadata(
        checkpoint_id="cp1",
        project_id="p",
        phase=FilmPhase.SCRIPT,
        created_at=_ts(),
        reason="human approved script v3",
        git_commit="abc123",
        git_tag="checkpoint/script-approved-v3",
    )
    assert c.git_tag == "checkpoint/script-approved-v3"


def test_invalidation_report() -> None:
    r = InvalidationReport(
        rollback_target="version:script:v3",
        will_revert=["script"],
        will_invalidate=["scene_intents:v4"],
    )
    assert r.requires_human_confirmation is True


def test_rollback_record() -> None:
    r = RollbackRecord(
        rollback_id="rb1",
        project_id="p",
        target_checkpoint_id="cp1",
        invalidation_report_ref="inv1",
        performed_by="human:owner",
        created_at=_ts(),
        outcome=RollbackOutcome.SUCCESS,
    )
    assert r.outcome == "success"


def test_rollback_outcome_vocabulary() -> None:
    assert RollbackOutcome.SUCCESS.value == "success"
    assert RollbackOutcome.PARTIAL.value == "partial"
    assert RollbackOutcome.FAILED.value == "failed"


def test_rollback_record_outcome_uses_str_enum() -> None:
    r = RollbackRecord(
        rollback_id="rb2",
        project_id="p",
        target_checkpoint_id="cp1",
        invalidation_report_ref="inv1",
        performed_by="system",
        created_at=_ts(),
        outcome=RollbackOutcome.PARTIAL,
    )
    assert r.outcome is RollbackOutcome.PARTIAL
    assert r.outcome.value == "partial"
    revived = _round_trip(r)
    assert revived.outcome == "partial"
    assert json.loads(json.dumps(revived.model_dump(mode="json")))["outcome"] == "partial"


def test_rollback_record_coerces_wire_format_outcome() -> None:
    record = RollbackRecord.model_validate(
        {
            "rollback_id": "rb2b",
            "project_id": "p",
            "target_checkpoint_id": "cp1",
            "invalidation_report_ref": "inv1",
            "performed_by": "system",
            "created_at": "2026-06-19T12:00:00Z",
            "outcome": "failed",
        }
    )
    assert record.outcome is RollbackOutcome.FAILED


def test_rollback_record_rejects_unknown_outcome() -> None:
    with pytest.raises(ValidationError):
        RollbackRecord.model_validate(
            {
                "rollback_id": "rb3",
                "project_id": "p",
                "target_checkpoint_id": "cp1",
                "invalidation_report_ref": "inv1",
                "performed_by": "system",
                "created_at": "2026-06-19T12:00:00Z",
                "outcome": "skipped",
            }
        )


def test_branch_metadata() -> None:
    b = BranchMetadata(
        branch_id="b1",
        project_id="p",
        base_checkpoint_id="cp1",
        purpose="alternate ending",
    )
    assert b.active is False


# --- Handoff / Routing ---------------------------------------------------


def test_agent_handoff() -> None:
    h = AgentHandoff(
        handoff_id="h1",
        from_agent="a1",
        to_agent="a2",
        project_id="p",
        task="t",
        expected_output_schema="schema:v1",
    )
    assert h.validation_required == []


def test_routing_decision_explainable() -> None:
    r = RoutingDecision(
        routing_decision_id="r1",
        selected_agent="dialogue-agent",
        reason="validator flagged voice",
        input_refs=["x"],
        expected_output="dialogue_revision",
        candidate_agents=["pacing-agent", "dialogue-agent"],
    )
    assert r.selected_agent == "dialogue-agent"


def test_agent_registration() -> None:
    from film_pipeline.schemas._base import AgentFamily, AgentRole

    a = AgentRegistration(
        agent_id="dialogue-agent",
        family=AgentFamily.SCREENWRITING,
        role=AgentRole.CREATOR,
        capabilities=["dialogue"],
        allowed_kb_domains=["character"],
        blocked_kb_domains=["provider"],
        prompt_framework="RCTCO",
        default_model_profile="creative_writer",
        reviewed_by=["dialogue-voice-validator"],
        failure_modes=["generic_voice"],
    )
    assert a.role == AgentRole.CREATOR


# --- Delivery ------------------------------------------------------------


def test_delivery_package() -> None:
    pkg = DeliveryPackage(
        package_id="d1",
        project_id="p",
        files=[{"path": "final.mp4", "type": "video"}],
        is_complete=True,
    )
    assert pkg.is_complete is True
    assert pkg.subtitles_included is False


# --- Registries ----------------------------------------------------------


def test_provider_registry_entry() -> None:
    e = ProviderRegistryEntry(
        provider_id="mock-video-provider",
        provider_type="video",
        models=["mock-fast"],
        capabilities=ProviderCapabilities(
            text_to_video=True,
            return_last_frame=True,
            max_duration_seconds=30,
        ),
        cost_profile=CostProfile(unit="second", estimated_rate_usd=0.0),
        failure_modes=["timeout", "quota"],
    )
    assert e.capabilities.return_last_frame is True
    assert e.cost_profile.estimated_rate_usd == 0.0


def test_validator_registry_entry() -> None:
    e = ValidatorRegistryEntry(
        validator_id="clip-quality-validator",
        scope=ValidationScope.CLIP,
        modalities=[ValidationModality.VIDEO],
        thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=60),
    )
    assert e.thresholds.pass_at == 85


def test_model_registry_entry() -> None:
    e = ModelRegistryEntry(
        model_id="gpt-5",
        provider="openai",
        strengths=["creative writing"],
        modalities=["text"],
        preferred_tasks=["dialogue"],
    )
    assert e.model_id == "gpt-5"


def test_agent_registry_entry() -> None:
    from film_pipeline.schemas._base import AgentFamily, AgentRole

    e = AgentRegistryEntry(
        agent_id="dialogue-agent",
        family=AgentFamily.SCREENWRITING,
        role=AgentRole.CREATOR,
        capabilities=["dialogue"],
        prompt_framework="RCTCO",
    )
    assert e.enabled is True


def test_validation_ledger_entry() -> None:
    r = ValidationReport(
        validation_id="v1",
        validator_id="v",
        scope=ValidationScope.SCENE,
        modalities=[ValidationModality.TEXT],
        score=85,
        status=ValidationStatus.PASS,
    )
    e = ValidationLedgerEntry(report=r, project_id="p", phase="script")
    assert e.report.score == 85


# --- _base helpers --------------------------------------------------------


def test_schema_version_default() -> None:
    identity = ProjectIdentity(project_id="p", slug="s", title="T")
    assert identity.schema_version == "v1"


def test_schema_base_extra_ignored() -> None:
    """Extra fields are silently dropped so LLM output with commentary fields works."""
    result = ProjectIdentity.model_validate(
        {"project_id": "p", "slug": "s", "title": "T", "extra_field": "nope"}
    )
    assert result.project_id == "p"
    assert not hasattr(result, "extra_field")


def test_quality_level_enum() -> None:
    assert QualityLevel.FESTIVAL.value == "festival"
    assert FilmType.NARRATIVE.value == "narrative"
    assert QualityLevel.FESTIVAL in QualityLevel


def test_prompt_registry_aggregate() -> None:
    p = PromptRegistryEntry(
        prompt_id="p1",
        agent_id="a",
        rctco=RCTCOPrompt(r="r", c1="c"),
    )
    reg = PromptRegistry(project_id="p", entries=[p])
    assert len(reg.entries) == 1


def test_generation_ledger_aggregate() -> None:
    row = GenerationLedgerRow(
        generation_request_id="g1",
        generation_id="gen:1",
        project_id="p",
        shot_id="S001-01",
        mode=GenerationMode.TEST,
        provider="mock",
        model="mock-fast",
        prompt_ref="prompt",
    )
    led = GenerationLedger(project_id="p", rows=[row])
    assert led.rows[0].generation_id == "gen:1"


def test_reference_index_aggregate() -> None:
    e = ReferenceIndexEntry(
        reference_id="ref:1",
        asset_path="a.png",
        asset_type="character_identity_sheet",
        subject_type="character",
        subject_id="c1",
        quality_score=80,
    )
    idx = ReferenceIndex(project_id="p", entries=[e])
    assert idx.entries[0].reference_id == "ref:1"


def test_registries_aggregates() -> None:
    p_reg = ProviderRegistry(providers=[])
    v_reg = ValidatorRegistry(validators=[])
    m_reg = ModelRegistry(models=[])
    assert p_reg.providers == []
    assert v_reg.validators == []
    assert m_reg.models == []
