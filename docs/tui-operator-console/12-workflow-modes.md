# Workflow Modes

## Purpose

The project should support manual and automatic operation explicitly, not only as an
accidental result of profile flags.

This document defines workflow mode as a first-class project setting.

## Current State

Today, approval behavior is effectively profile-driven:

- `require_human_approval: true` means manual gates
- `require_human_approval: false` means headless auto-approve

That works, but it is too implicit for a product-facing TUI.

## Recommended Model

Add a first-class project setting:

- `workflow_mode`

Allowed values:

- `manual`
- `hybrid`
- `automatic`

Profiles still matter, but only as defaults and policy inputs.

## Goals

This should make the system:

- easier to understand
- easier to inspect in the TUI
- easier to change safely per project
- flexible enough for both studio operators and film creators

## Mode Definitions

## 1. Manual

Meaning:

- every major gate requires human approval
- the graph pauses at review gates
- costly and risky actions always require explicit human action

Use when:

- the film creator wants close creative control
- quality is more important than throughput
- the project is high-risk, experimental, or expensive

Default expectation:

- best default for creator-led work

## 2. Hybrid

Meaning:

- safe, cheap, or routine actions may continue automatically
- creative-significant, costly, risky, or blocking decisions still require human review

Use when:

- the user wants speed without losing control
- the studio is doing iterative work with selective human gates

Default expectation:

- best general-purpose mode for active production

## 3. Automatic

Meaning:

- the pipeline runs headless where policy allows
- human intervention happens only on escalation, hard blockers, or policy boundaries

Use when:

- running mock/demo/headless workflows
- doing batch or CI-style processing

Default expectation:

- best for automation, not for creator-led exploration

## Decision Model

Workflow mode should not be a single yes/no gate flag.

The service layer should evaluate:

- `workflow_mode`
- gate type
- risk level
- cost threshold
- provider state
- unresolved blocking issues
- project policy

Then decide:

- auto-continue
- require review
- require explicit approval
- escalate

## Recommended Gate Classes

Define each gate with a class:

- `creative`
- `cost`
- `quality`
- `delivery`
- `recovery`

Examples:

- script approval: `creative`, `quality`
- generation spend approval: `cost`
- rollback confirmation: `recovery`
- final delivery approval: `delivery`

## Recommended Policy Behavior

### Manual

- all major gates require human action

### Hybrid

- `creative`, `delivery`, and `recovery` gates always require human action
- `cost` gates require human action above threshold
- `quality` gates auto-pass only when no blocking issues exist and policy allows

### Automatic

- gates auto-pass by default
- escalate on blockers, failures, policy conflicts, or spend thresholds

## Profiles And Workflow Mode

Profiles should remain useful.

Recommended rule:

- profiles provide default workflow mode and policy thresholds
- project settings store the resolved active workflow mode
- project-level override is allowed when policy permits

That means:

- profile = default behavior template
- project state = actual active behavior

## TUI Requirements

The TUI should make workflow mode obvious.

Show in:

- global header
- project summary
- project creation flow
- project settings screen or modal

The TUI should also explain:

- why the current step is waiting for human review
- why a step auto-continued
- why a step escalated despite automatic mode

## Service-Layer Requirements

Add service concepts such as:

- `WorkflowMode`
- `GatePolicy`
- `GateDecision`

Possible responsibilities:

- `ProjectService` stores and updates project workflow mode
- `OrchestrationService` evaluates gate decisions
- `ReviewService` exposes whether a gate is manual, auto-passed, or escalated

## Suggested Data Shape

Example project-level fields:

- `workflow_mode`
- `workflow_mode_source`
- `allow_workflow_override`
- `auto_approve_cost_limit_usd`
- `manual_gate_classes`

Example gate-decision fields:

- `gate_id`
- `gate_class`
- `workflow_mode`
- `decision`
- `reason`
- `requires_human`

## Creator-Flexibility Implications

This is important for film creators.

Why:

- creators often want manual control on script, treatment, visual direction, and shot intent
- they may still want automation for repetitive safe steps

So workflow mode should support:

- project-wide default mode
- eventual per-phase or per-gate overrides

Not necessarily in V1, but the model should allow it.

## Recommendation For V1

Implement:

- project-level `workflow_mode`
- three modes: `manual`, `hybrid`, `automatic`
- profile-provided defaults
- visible mode in TUI
- service-layer gate decision logic

Delay:

- per-phase override editing
- per-gate override editing
- complex rule builders in UI

## Acceptance Criteria

- manual workflow is a first-class supported mode
- automatic workflow remains supported
- hybrid mode is defined clearly enough to implement
- profile defaults do not hide the active project behavior
- TUI can show and explain current workflow mode and gate decisions
