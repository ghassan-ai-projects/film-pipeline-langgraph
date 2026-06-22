# Orchestrator Design

## Principle

The orchestrator owns outcomes, not tasks.

Specialist agents should:

- propose
- enrich
- validate
- repair

The orchestrator should:

- define the required artifact contract
- compare actual outputs against the contract
- route follow-up work to the right agent
- stop phase advancement when the contract is not met

## Target Behavior

For a film like Camino del Genesis, the orchestrator should carry a film-level execution brief:

- target runtime: 240 seconds
- movement structure: `5 + 5 + 5 + 4` authored shots, plus final black hold if applicable
- pacing style: slow cinema, mostly 10 to 15 second shots
- mandatory visual anchors: young man, eagle, bee, almond tree, insect, ants, ripple motif
- mandatory environment progression: barren -> green -> split -> yellow-rose climax

That brief should be visible to every downstream agent, but enforced by the orchestrator.

## Delegation Model

### 1. Screenwriter or narrative agent

Responsible for:

- movement structure
- story beats
- timing intent
- key motifs

Must emit:

- explicit movement ids
- target duration per movement
- expected shot count per movement

### 2. Shot design agent

Responsible for:

- decomposing each movement into concrete shots
- assigning duration, camera intent, subject set, and environment state

Must emit one row per shot with:

- `shot_id`
- `movement_id`
- `scene_id`
- `duration_seconds`
- `characters`
- `environment`
- `camera_profile`
- `prompt_ref` or prompt payload ref
- `reference_strategy_ref`
- `generation_order`

### 3. Reference strategy or visual-dev agent

Responsible for:

- character anchors
- environment anchors
- style anchors
- camera/look anchors when needed

Must resolve the references that shot design claims to use.

### 4. Prompt or generation-planning agent

Responsible for:

- provider selection
- model selection
- prompt package construction
- cost estimation
- dependency ordering

Must not rely on empty placeholders.

### 5. Validators

Responsible for:

- structural completeness
- runtime consistency
- prompt readiness
- dispatch readiness

## Orchestrator Control Loop

### Gate A: Narrative to shot decomposition

The orchestrator compares:

- authored movement count
- expected shots per movement
- authored runtime

against:

- produced shot rows
- summed durations

If mismatched, the orchestrator re-routes to shot design with a repair brief.

### Gate B: Shot decomposition to planning

The orchestrator checks for empty or weak operational fields:

- missing `prompt_ref`
- missing character/environment refs
- missing camera profile
- missing generation order

If incomplete, it routes to the agent best positioned to fill the gap:

- shot design for semantic row fixes
- visual-dev for missing refs
- planning for provider and cost gaps

### Gate C: Planning to dispatch

The orchestrator verifies:

- non-zero clip count
- non-zero estimated cost when using paid providers
- dispatchable prompt payload
- provider/model availability

If any request is symbolic rather than executable, the phase does not advance.

## New Agent Responsibilities

The orchestrator does not need to do creative decomposition itself. It needs better enforcement and repair routing.

Recommended helper responsibilities:

- `structure-auditor-agent`: compares authored movement spec to shot rows
- `runtime-auditor-agent`: checks duration totals and pacing windows
- `dispatch-readiness-agent`: checks prompt, refs, provider, and cost completeness

These can be validators or review agents. The orchestrator remains the owner of the decision.

## Minimal Implementation Strategy

1. Make the orchestrator store an explicit film execution brief after script approval.
2. Require shot design output to include `movement_id` and complete row fields.
3. Add hard validation on shot counts and runtime totals before planning.
4. Add hard validation on dispatch readiness before provider submission.
5. Route failed gates to the narrowest repair agent instead of advancing optimistically.
