# Product Intent For A TUI

## Problem Statement

The repo already has the right control boundary: MCP. The missing piece is operator
throughput.

Today an operator must mentally stitch together:

- project creation
- phase status
- approval gates
- review packages
- artifact diffs
- validator output
- provider health
- checkpoints and rollback

That is workable for debugging. It is weak for production operation.

## Root Cause Analysis

### Symptom

The pipeline can be controlled, but not comfortably operated.

### 5 Whys

1. Why is operation slower than it should be?
   Because the operator works through low-level tool calls and JSON payloads.
2. Why is that a problem?
   Because the workflow is review-heavy, stateful, and interruption-driven.
3. Why does that matter here more than in a simple CLI?
   Because film production generates many artifacts, decisions, issues, and baselines per
   phase.
4. Why can MCP alone not solve the operator-experience issue?
   Because MCP defines contracts, not information density, navigation, or decision UX.
5. Why should this become a TUI instead of a web app first?
   Because the product is already terminal-native, local-first, engineer-operated, and
   strongly aligned with stdio MCP.

### Root Cause

The real gap is not missing orchestration. It is missing operator packaging around
existing orchestration.

## Product Goal

Build a TUI that makes the studio operable under real review pressure while preserving the
existing MCP-first architecture.

## Product Non-Goals

Do not use the TUI to:

- replace MCP as the external contract
- implement a second approval state machine
- hide important risk or cost signals behind “simple mode”
- create a heavyweight frontend platform before operator workflows stabilize

## Design Principles

### 1. Operator first

The TUI is for the human responsible for decisions, not for passive spectators.

### 2. Evidence over decoration

Every major action should show:

- what changed
- what is blocked
- why the orchestrator chose this path
- what the operator can safely do next

### 3. Review-package centric

The unit of decision is the review package, not the raw artifact list.

### 4. Fast keyboard operation

The operator must be able to:

- switch projects
- inspect current phase
- open blockers
- compare candidate vs approved artifacts
- approve or request revision

without mouse dependency.

### 5. Safe by default

Actions with cost or reversibility impact must require explicit confirmation.

## Success Definition

The TUI is successful when a new operator can:

1. create or open a project
2. understand current phase and next action in under 30 seconds
3. inspect the current review package without leaving the shell
4. approve, revise, or escalate safely
5. investigate blockers, provider issues, and rollback impact from one interface
