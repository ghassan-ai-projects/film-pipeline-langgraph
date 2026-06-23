# Operator Jobs And Personas

## Primary Persona

### Studio Operator

This is the main TUI user.

Responsibilities:

- create and configure projects
- monitor pipeline progression
- inspect orchestrator recommendations
- approve or reject phase outputs
- manage provider and budget incidents
- trigger rollback or recovery

Needs:

- high information density
- reliable keyboard navigation
- clear risk and cost signals
- durable auditability

## Secondary Personas

### Creative Director

Focus:

- treatment, script, visual language, shot intent, review notes

TUI implication:

- artifact reading must feel good in terminal form
- revision workflow must support precise note entry

### Technical Operator

Focus:

- provider health
- stalled phases
- runtime failures
- checkpoint and resume behavior

TUI implication:

- separate operational visibility from creative review
- include health, logs, and rollback views

## Core Jobs To Be Done

### JTBD 1

When I open the studio, I want to immediately see what needs human attention so I do not
waste time hunting across tools.

### JTBD 2

When a phase is ready for review, I want the TUI to present the decision package in one
place so I can approve or revise with confidence.

### JTBD 3

When the pipeline is blocked, I want to know whether the problem is creative, validation,
budget, provider, or runtime so I can take the right action quickly.

### JTBD 4

When I consider rollback or regeneration, I want clear blast-radius information before I
commit to it.

### JTBD 5

When multiple projects are active, I want the TUI to help me triage by urgency, risk, and
phase state.

## Persona-Driven UX Requirements

The TUI should optimize for:

- triage first, detail second
- summaries first, raw JSON second
- hotkeys for frequent actions
- explicit action eligibility and blocked reasons
- safe, auditable confirmations for destructive or costly actions

The TUI should avoid:

- full-screen forms as the default interaction
- deep menu trees
- hiding candidate vs approved distinctions
- collapsing multiple failure types into a generic “error” state
