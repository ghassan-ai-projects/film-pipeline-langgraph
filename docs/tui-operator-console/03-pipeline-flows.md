# Pipeline Flows In The TUI

## Principle

The TUI flow must mirror the real pipeline:

`project -> orchestrator state -> review package -> human action -> graph resume`

Not:

`project -> UI-local workflow -> backend reconciliation`

## Primary End-To-End Flow

### 1. Startup

The TUI boots, connects to the MCP server, runs health checks, lists projects, and loads
the active project summary.

### 2. Triage

The operator lands on the dashboard and sees:

- what is running
- what is waiting for review
- what is blocked
- what is risky

### 3. Open Review

If a project is awaiting review, `Review` becomes the default focus. The operator inspects
candidate artifacts, validation results, issues, and the orchestrator recommendation.

### 4. Decide

The operator selects one of:

- approve
- request revision
- escalate
- defer

### 5. Resume

The TUI calls the corresponding MCP tool and refreshes the affected project state.

## Per-Phase TUI Behavior

### Intake / Constitution / Development / Screenwriting

Primary content:

- long-form text artifacts
- thematic and structural validation
- revision notes

Best UI treatment:

- document reader
- diff between candidate and approved
- validator issue side panel

### Visual Development / Shot Bible / Generation Planning

Primary content:

- structured references
- matrix rows
- prompt readiness
- generation cost and provider plans

Best UI treatment:

- split table/detail layout
- row-level status and blockers
- risk/cost summary at top

### Generation / QC

Primary content:

- batch state
- provider incidents
- asset status
- QC validation

Best UI treatment:

- operations dashboard
- job timeline
- provider health strip
- quick links to failed items

### Post / Delivery

Primary content:

- assembly manifests
- completeness checks
- export status

Best UI treatment:

- delivery checklist
- artifact package inspector
- final approval card

## Important Secondary Flows

### Revision Flow

1. open current review package
2. select `request revision`
3. enter structured notes
4. submit MCP revision request
5. refresh until new candidate artifacts appear

Design requirement:

Revision notes should support both:

- free text
- structured prompts such as `preserve`, `change`, `blocking reason`

### Blocker Investigation Flow

1. open dashboard blocker card
2. drill into blocker list
3. inspect issue owner and source
4. branch to review, providers, or checkpoints

Design requirement:

Blocked actions must always show:

- action name
- block reason
- likely next operator step

### Rollback Flow

1. open checkpoints
2. select target checkpoint or artifact version
3. inspect invalidation report
4. confirm rollback
5. refresh project state and audit log

Design requirement:

Rollback UX must force blast-radius visibility before confirmation.

### Provider Incident Flow

1. provider health board shows degraded status
2. operator opens provider details
3. inspect active jobs, recent failures, safe-to-continue status
4. choose resolve, retry, wait, or re-route when supported

### Multi-Project Triage Flow

1. sort projects by urgency
2. open next actionable review
3. cycle through review queue

Design requirement:

The TUI should support an “operator inbox” view later.

## State Refresh Model

Short term:

- poll after mutations
- periodic refresh on active project summary

Medium term:

- incremental refresh by visible tab

Long term:

- event stream or push notifications if the MCP surface grows that capability
