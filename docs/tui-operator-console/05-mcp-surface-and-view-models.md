# MCP Surface And View Models

## Principle

The TUI should consume stable view models from a gateway layer, not raw tool payloads
scattered across widgets.

Those gateway methods should be backed by shared application services. MCP remains one
adapter, not the only possible integration path.

## Current MCP Surface Relevance

The existing tool groups are enough to shape a strong V1, but not every area is fully wired.
Some tools are still stubbed, so the service layer should become the source of backend
truth while MCP catches up as a public surface.

Strongest current groups:

- project
- state
- review
- artifact
- validation
- checkpoint
- provider
- audit

Generation and assembly tools become more important in V2.

## Required TUI View Models

## 1. Project List Item

Derived from:

- `ProjectService.list_projects()`
- `OrchestrationService.get_dashboard_summary()`

Fields:

- `project_id`
- `title`
- `current_phase`
- `status`
- `has_blockers`
- `awaiting_review`
- `last_updated_at`

## 2. Dashboard Summary

Derived from:

- `ProjectService.get_project_summary()`
- `OrchestrationService.get_dashboard_summary()`

Fields:

- `current_phase`
- `next_action`
- `route_reason`
- `eligible_actions`
- `blocked_actions`
- `pending_revisions`
- `candidate_refs`
- `approved_refs`
- `budget_snapshot`
- `provider_blocked`

## 3. Review Workspace Model

Derived from:

- `ReviewService.get_review_workspace()`

Fields:

- `phase`
- `candidate_artifacts`
- `approved_baselines`
- `diff_summary`
- `validation_refs`
- `open_issues`
- `risk_summary`
- `cost_impact`
- `orchestrator_recommendation`
- `available_actions`
- `blocked_actions`

## 4. Artifact Detail Model

Derived from:

- `ArtifactService.list_artifacts()`
- `ArtifactService.inspect_artifact()`
- `CheckpointService.compare_versions()`
- `CheckpointService.list_artifact_versions()`

Fields:

- `artifact_ref`
- `artifact_type`
- `phase`
- `version`
- `status`
- `created_by`
- `parents`
- `validation_refs`
- `approval_ref`
- `body`

## 5. Validation Workspace Model

Derived from:

- `ValidationService.get_validation_workspace()`

Fields:

- `report_ref`
- `blocking_issues`
- `non_blocking_issues`
- `validator_results`
- `consensus_summary`

## 6. Checkpoint Workspace Model

Derived from:

- `CheckpointService.list_checkpoints()`
- `CheckpointService.get_checkpoint()`
- `CheckpointService.compare_versions()`
- `CheckpointService.preview_rollback()`

Fields:

- `checkpoint_id`
- `phase`
- `reason`
- `created_at`
- `artifact_versions`
- `diff_summary`
- `invalidation_preview`

## 7. Provider Operations Model

Derived from:

- `ProviderService.list_provider_status()`
- `ProviderService.get_generation_overview()`

Fields:

- `provider_id`
- `status`
- `capabilities`
- `active_jobs`
- `failure_summary`
- `safe_to_continue_other_work`

## 8. Audit Feed Model

Derived from:

- `AuditService.get_audit_feed()`
- `OrchestrationService.explain_last_decision()`
- `OrchestrationService.explain_agent_routing()`
- `OrchestrationService.explain_kb_context()`

Fields:

- `timestamp`
- `actor`
- `action`
- `target`
- `summary`
- `details_ref`

## Suggested Gaps To Close In MCP

The TUI can ship without new contracts, but these additions would improve it:

### 1. Bulk project summary tool

Problem:

`list_projects` alone is too thin for a good triage rail.

Recommended tool:

- `list_project_summaries`

### 2. Operator inbox tool

Problem:

The TUI will otherwise compute “what needs attention” client-side from many calls.

Recommended tool:

- `list_operator_actions`

Return:

- pending reviews
- blocked projects
- budget approvals
- provider incidents
- stalled phases

### 3. Review-package preview tool

Problem:

The rail may need lightweight review metadata without loading the full package.

Recommended tool:

- `get_review_status`

### 4. Event feed tool

Problem:

Polling is acceptable first, but not ideal long term.

Recommended additions later:

- `list_runtime_events`
- `subscribe_runtime_events` if streaming is introduced

## Mapping Rule

Service models are backend truth.

Gateway models adapt those service results to the UI.

Formatting belongs in the TUI.

Public interoperability belongs in MCP contracts.

This keeps the backend reusable and the UI replaceable.
