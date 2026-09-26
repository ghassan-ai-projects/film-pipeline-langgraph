"""The agent roster — which agents exist, and what each one is contracted to do.

``MVP_AGENTS`` is the set of agents this system runs. Most are wired into a
graph phase; the four visual-development bible creators are invoked through MCP
(``mcp.tools.bibles``) instead. Both kinds live here, because a roster row is
what makes an agent resolvable — its contract, implementation class, prompt
template, model profile, and mock response are all looked up by id.

Agents that are not invoked by anything yet (character-dossier,
prompt-composition, continuity-ledger, generation-scheduler,
scene-continuity-validator, full-movie-flow-validator, kb-curator) are kept out
until they are wired in. Their implementation classes and schema tests remain in
the codebase for future phases.

This is a data module, not a package: it declares records and nothing else. The
module that *validates* them, supports lookup, and binds them to implementation
classes is ``agents.registry``.

Each row's ``produces`` names the key its ``execute()`` returns the primary
artifact under — the key consumers read from a run's result dict. That is the
authoritative field; ``output_artifacts`` is the free-form capability
vocabulary and is not a result-dict contract.

Registration is not routing: being on this roster does not put an agent into a
graph phase. Which agent a phase routes to is ``orchestration._agent_routing``'s
decision and is deliberately untouched by membership here.
"""

from __future__ import annotations

from film_pipeline.schemas.base import AgentFamily, AgentRole
from film_pipeline.schemas.handoff import AgentRegistration

MVP_AGENTS: list[AgentRegistration] = [
    AgentRegistration(
        agent_id="orchestrator-agent",
        family=AgentFamily.OPERATIONS,
        role=AgentRole.ORCHESTRATOR,
        capabilities=["flow_routing", "arbitration", "phase_transition"],
        input_artifacts=["project_profile", "phase_state"],
        output_artifacts=["routing_decision"],
        produces="action",
        allowed_kb_domains=["operations", "governance"],
        blocked_kb_domains=[],
        prompt_framework="RCTCO",
        default_model_profile="strict_validator",
        reviewed_by=["human"],
        failure_modes=["wrong_phase_transition", "stale_state"],
    ),
    AgentRegistration(
        agent_id="intake-classifier-agent",
        family=AgentFamily.PRODUCER,
        role=AgentRole.CREATOR,
        capabilities=["input_classification", "signal_extraction"],
        input_artifacts=["user_idea"],
        output_artifacts=["classified_input"],
        produces="profile",
        allowed_kb_domains=["operations"],
        blocked_kb_domains=["cost"],
        prompt_framework="RCTCO",
        default_model_profile="creative_writer",
        reviewed_by=["orchestrator-agent"],
        failure_modes=["misclassification", "missed_signal"],
    ),
    AgentRegistration(
        agent_id="film-constitution-agent",
        family=AgentFamily.DEVELOPMENT,
        role=AgentRole.CREATOR,
        capabilities=["theme_definition", "tone_setting", "visual_language"],
        input_artifacts=["classified_input", "resolved_config"],
        output_artifacts=["film_constitution"],
        produces="constitution",
        allowed_kb_domains=["creative-writing", "tone"],
        blocked_kb_domains=["cost", "providers"],
        prompt_framework="RCTCO",
        default_model_profile="creative_writer",
        reviewed_by=["orchestrator-agent", "human"],
        failure_modes=["generic_tone", "weak_theme", "unfilmable_visual_language"],
    ),
    AgentRegistration(
        agent_id="treatment-agent",
        family=AgentFamily.DEVELOPMENT,
        role=AgentRole.CREATOR,
        capabilities=["treatment_writing", "act_mapping", "scene_listing"],
        input_artifacts=["film_constitution"],
        output_artifacts=["treatment", "act_map", "scene_list"],
        produces="treatment",
        allowed_kb_domains=["creative-writing"],
        blocked_kb_domains=["cost", "providers"],
        prompt_framework="RCTCO",
        default_model_profile="creative_writer",
        reviewed_by=["orchestrator-agent", "human"],
        failure_modes=["missing_acts", "weak_structure", "overlong"],
    ),
    AgentRegistration(
        agent_id="screenwriter-agent",
        family=AgentFamily.SCREENWRITING,
        role=AgentRole.CREATOR,
        capabilities=["scene_writing", "dialogue", "scene_intents"],
        input_artifacts=["treatment", "act_map", "scene_list", "film_constitution"],
        output_artifacts=["script", "scene_intents"],
        produces="script",
        allowed_kb_domains=["creative-writing", "dialogue", "character"],
        blocked_kb_domains=["cost", "providers"],
        prompt_framework="RCTCO",
        default_model_profile="creative_writer",
        reviewed_by=["orchestrator-agent", "human"],
        failure_modes=["voice_inconsistency", "tone_drift", "missing_scenes"],
    ),
    AgentRegistration(
        agent_id="structure-extractor-agent",
        family=AgentFamily.SCREENWRITING,
        role=AgentRole.CREATOR,
        capabilities=["structure_extraction", "runtime_estimation", "anchor_identification"],
        input_artifacts=["story_bible", "script"],
        output_artifacts=["execution_brief"],
        produces="execution_brief",
        allowed_kb_domains=["operations", "creative-writing"],
        blocked_kb_domains=["cost", "providers"],
        prompt_framework="RCTCO",
        default_model_profile="schema_enforcer",
        reviewed_by=["orchestrator-agent"],
        failure_modes=["wrong_shot_count", "missed_anchor", "wrong_runtime"],
    ),
    AgentRegistration(
        agent_id="reference-strategy-planner",
        family=AgentFamily.REFERENCE,
        role=AgentRole.CREATOR,
        capabilities=["reference_planning", "quality_thresholds"],
        input_artifacts=["character_bible", "environment_bible", "film_constitution"],
        output_artifacts=["reference_strategy"],
        produces="reference_index",
        allowed_kb_domains=["reference-images", "visual-design"],
        blocked_kb_domains=["cost"],
        prompt_framework="RCTCO",
        default_model_profile="visual_reasoner",
        reviewed_by=["orchestrator-agent", "human"],
        failure_modes=["low_quality_refs", "missing_subjects", "moderation_risk"],
    ),
    AgentRegistration(
        agent_id="shot-design-agent",
        family=AgentFamily.DIRECTING,
        role=AgentRole.CREATOR,
        capabilities=["shot_design", "matrix_assembly", "coverage_planning"],
        input_artifacts=["script", "scene_intents", "character_bible", "environment_bible"],
        output_artifacts=["shot_bible", "master_film_matrix"],
        produces="shot_matrix",
        allowed_kb_domains=["directing", "camera"],
        blocked_kb_domains=["cost"],
        prompt_framework="RCTCO",
        default_model_profile="creative_writer",
        reviewed_by=["orchestrator-agent", "human"],
        failure_modes=["missing_coverage", "weak_shot_design", "unsupported_camera"],
    ),
    AgentRegistration(
        agent_id="provider-planning-agent",
        family=AgentFamily.PROMPT_PLANNING,
        role=AgentRole.CREATOR,
        capabilities=["provider_selection", "cost_estimation"],
        input_artifacts=["prompt_registry", "master_film_matrix", "resolved_config"],
        output_artifacts=["provider_plan"],
        produces="cost_estimate",
        allowed_kb_domains=["providers", "cost"],
        blocked_kb_domains=[],
        prompt_framework="RCTCO",
        default_model_profile="operations_triage",
        reviewed_by=["orchestrator-agent", "human"],
        failure_modes=["wrong_provider", "cost_overrun", "incompatible_capabilities"],
    ),
    AgentRegistration(
        agent_id="clip-validator",
        family=AgentFamily.QC,
        role=AgentRole.VALIDATOR,
        capabilities=["clip_quality", "prompt_adherence", "identity_consistency"],
        input_artifacts=["generated_clip", "prompt_registry", "validation_ledger"],
        output_artifacts=["validation_report"],
        produces="consensus_report",
        allowed_kb_domains=["validation", "quality"],
        blocked_kb_domains=["cost"],
        prompt_framework="RCTCO",
        default_model_profile="strict_validator",
        reviewed_by=["orchestrator-agent", "human"],
        failure_modes=["false_pass", "missed_identity_drift", "too_lenient"],
    ),
    AgentRegistration(
        agent_id="failure-handling-agent",
        family=AgentFamily.OPERATIONS,
        role=AgentRole.OPERATOR,
        capabilities=["error_classification", "recovery_decision", "retry_policy"],
        input_artifacts=["generation_ledger", "provider_error", "budget_state"],
        output_artifacts=["failure_decision"],
        produces="assembly_manifest",
        allowed_kb_domains=["operations", "providers"],
        blocked_kb_domains=[],
        prompt_framework="RCTCO",
        default_model_profile="operations_triage",
        reviewed_by=["orchestrator-agent"],
        failure_modes=["wrong_error_class", "premature_retry", "missed_escalation"],
    ),
    # --- Visual-development bible creators ---------------------------------
    # Invoked through MCP (`mcp.tools.bibles`) rather than a graph phase, but
    # they are agents like any other: the roster declares them so the MCP path
    # and the graph path resolve contracts, implementations, templates, and
    # mocks from one place. The contracts below were the MCP tools' own local
    # literals before this move; they are copied verbatim so nothing drifts.
    AgentRegistration(
        agent_id="camera-bible-agent",
        family=AgentFamily.DEVELOPMENT,
        role=AgentRole.CREATOR,
        capabilities=["camera_design"],
        input_artifacts=["film_constitution"],
        output_artifacts=["camera_language_bible"],
        produces="camera_bible",
        allowed_kb_domains=["visual-design", "camera"],
        blocked_kb_domains=["cost", "providers"],
        prompt_framework="RCTCO",
        default_model_profile="creative_writer",
        reviewed_by=["orchestrator-agent", "human"],
        failure_modes=["generic_lenses", "unfilmable_movement", "missing_default_profile"],
    ),
    AgentRegistration(
        agent_id="character-bible-agent",
        family=AgentFamily.DEVELOPMENT,
        role=AgentRole.CREATOR,
        capabilities=["character_development"],
        input_artifacts=["script", "film_constitution"],
        output_artifacts=["character_bible"],
        produces="character_bible",
        allowed_kb_domains=["character", "creative-writing"],
        blocked_kb_domains=["cost", "providers"],
        prompt_framework="RCTCO",
        default_model_profile="creative_writer",
        reviewed_by=["orchestrator-agent", "human"],
        failure_modes=["flat_identity", "unusable_identity_block", "missing_voice_rules"],
    ),
    AgentRegistration(
        agent_id="environment-bible-agent",
        family=AgentFamily.DEVELOPMENT,
        role=AgentRole.CREATOR,
        capabilities=["environment_design"],
        input_artifacts=["script", "film_constitution"],
        output_artifacts=["environment_bible"],
        produces="environment_bible",
        allowed_kb_domains=["visual-design", "creative-writing"],
        blocked_kb_domains=["cost", "providers"],
        prompt_framework="RCTCO",
        default_model_profile="creative_writer",
        reviewed_by=["orchestrator-agent", "human"],
        failure_modes=["missing_zones", "inconsistent_lighting", "weak_locked_prompt_block"],
    ),
    AgentRegistration(
        agent_id="style-bible-agent",
        family=AgentFamily.DEVELOPMENT,
        role=AgentRole.CREATOR,
        capabilities=["style_definition"],
        input_artifacts=["film_constitution", "environment_bible"],
        output_artifacts=["style_bible"],
        produces="style_bible",
        allowed_kb_domains=["visual-design", "tone"],
        blocked_kb_domains=["cost", "providers"],
        prompt_framework="RCTCO",
        default_model_profile="creative_writer",
        reviewed_by=["orchestrator-agent", "human"],
        failure_modes=["generic_palette", "tone_mismatch", "unstated_mood"],
    ),
]
