# Project Intake

## Purpose

The user's first input is the seed of the whole film. It might be one sentence, a rough idea,
a detailed treatment, a script fragment, or a config file plus a prompt.

The system should not assume all first inputs are equally complete. It should classify,
extract, infer, and ask for approval before turning the input into a project contract.

## Input Types

### 1. Short Idea

Example:

```text
A lonely painter reconnects with memory through color.
```

Needs:

- genre inference
- tone inference
- runtime suggestion
- story expansion
- assumptions listed clearly

### 2. Medium Creative Brief

Example:

```text
An 8-minute melancholic arthouse film about a painter who slowly reconnects with memory
through color. Minimal dialogue, painterly visuals, festival style.
```

Needs:

- style extraction
- profile selection
- missing constraints filled from defaults
- confirmation of inferred structure

### 3. Detailed Project Brief

May include:

- story
- characters
- locations
- desired style
- runtime
- references
- delivery format
- budget
- provider preference

Needs:

- structured extraction
- conflict detection
- preservation of user intent
- no unnecessary reinvention

### 4. Script Or Treatment Input

May include:

- full script
- act outline
- scene list
- dialogue
- shot ideas

Needs:

- document classification
- structure parsing
- gap detection
- conversion into story bible and scene intents

### 5. Config File Plus Prompt

May include:

- explicit profile choices
- style choices
- provider choices
- budget
- review strictness

Needs:

- config validation
- prompt inference only for missing values
- clear precedence rules

## Intake Pipeline

### Step 1. Preserve Raw Input

Store the original user input unchanged.

Artifact:

```text
intake/raw-user-input.md
```

Why:
The system should always be able to return to what the user actually said.

### Step 2. Classify Input

Classify the input by type and completeness.

Fields:

- `input_type`
- `completeness_level`
- `detected_film_type`
- `detected_style`
- `detected_constraints`
- `confidence`

Example:

```json
{
  "input_type": "medium_creative_brief",
  "completeness_level": "partial",
  "detected_film_type": "narrative",
  "detected_style": ["arthouse_drama", "painterly_realism"],
  "detected_constraints": ["minimal_dialogue", "festival_style"],
  "confidence": 0.78
}
```

### Step 3. Extract Structured Signals

Extract:

- premise
- theme
- protagonist
- conflict
- desired tone
- desired runtime
- visual style
- camera style
- pacing
- audience
- delivery intent
- budget
- providers
- constraints
- forbidden directions

### Step 4. Infer Missing Values

Use defaults and profiles to fill gaps.

Rules:

- inferred values must be marked as inferred
- confidence must be recorded
- important inferred values require human approval
- explicit user config overrides inference

### Step 5. Detect Ambiguity And Conflict

Examples:

- user asks for `festival` quality but `free_only` budget
- user asks for `visual_poetry` but also dense dialogue
- user asks for same character continuity but provides no character description
- user asks for many locations but very small budget

Output:

- warnings
- conflicts
- suggested resolution
- whether human confirmation is required

### Step 6. Generate Project Brief

Turn the raw input into a structured first project artifact.

Artifact:

```text
intake/project-brief.v1.yaml
```

Suggested fields:

```yaml
project:
  title: null
  working_title: ""
  film_type: ""
  target_runtime_minutes: null
  delivery_intent: []

creative:
  premise: ""
  theme: ""
  tone: ""
  writing_style: ""
  movie_style: ""
  visual_style: ""
  camera_style: ""
  pacing: ""

story:
  protagonist: ""
  conflict: ""
  transformation: ""
  ending_intent: ""

production:
  budget_cap_usd: null
  preferred_providers: []
  human_review_level: ""
  quality_profile: ""

constraints:
  must_include: []
  must_avoid: []
  assumptions: []
  open_questions: []
```

### Step 7. Resolve Project Config

Merge:

- studio defaults
- selected profiles
- user config
- prompt-derived inference
- normalization

Output:

```text
project-config.resolved.yaml
```

### Step 8. Create Intake Review Package

Before continuing, show the human:

- raw input
- extracted signals
- inferred values
- assumptions
- conflicts
- proposed project config
- orchestrator recommendation

Human decision:

- approve
- revise values
- answer open questions
- provide more material
- stop project

## RCTCO Intake Prompt

The intake agent should use RCTCO.

```json
{
  "r": "You are a film project intake strategist for a professional AI film studio.",
  "c1": "Analyze the user's first input and convert it into a structured project brief and config inference report.",
  "t": {
    "user_input": "raw user prompt or uploaded brief",
    "available_profiles": [],
    "style_catalogs": [],
    "studio_defaults": []
  },
  "c2": {
    "constraints": [
      "Preserve the user's actual intent.",
      "Do not invent major story details without marking them as assumptions.",
      "Prefer config inference over asking questions unless ambiguity is material.",
      "Flag conflicts clearly."
    ]
  },
  "o": {
    "format": "json",
    "schema_ref": "intake-analysis-report:v1"
  }
}
```

## Question Policy

The system should avoid interrogating the user too early.

Ask questions only when:

- the answer changes the project direction materially
- the config conflict cannot be safely resolved
- budget/provider choice creates risk
- creative intent is contradictory
- a mandatory field cannot be inferred

Otherwise:

- make a reasonable assumption
- mark it as inferred
- show it in the intake review package

## Intake Agents

Suggested agents:

- intake-classifier-agent
- story-signal-extractor
- style-inference-agent
- config-inference-agent
- conflict-detector-agent
- project-brief-synthesizer
- intake-review-package-agent

## Intake Validation

Validators:

- input-completeness-validator
- style-compatibility-validator
- config-conflict-validator
- budget-feasibility-validator
- project-brief-validator

Validation should not require a fully developed story. It should only confirm the project
has enough direction to begin development.

## Output Of Intake

Final intake outputs:

```text
intake/
  raw-user-input.md
  intake-analysis-report.json
  project-brief.v1.yaml
  project-config.resolved.yaml
  intake-review-package.md
```

The approved project config becomes the first locked artifact in the production.

## Project Identity And Future Requests

After project creation, every future request must resolve to a project.

The system should assign stable identifiers:

- `project_id`: immutable machine id, such as `film_2026_0001`
- `slug`: human-readable stable name, such as `memory-in-color`
- `title`: editable display title, such as `Memory In Color`
- `aliases`: optional alternate names supplied by the user

Example:

```yaml
project_id: film_2026_0001
slug: memory-in-color
title: Memory In Color
aliases:
  - painter memory film
  - color painter project
```

### How Users Refer To A Project

Users should be able to refer to a project by:

- project id
- slug
- exact title
- registered alias
- current active project in the session

Examples:

```text
Continue film_2026_0001
Open memory-in-color
Show me the references for Memory In Color
Approve the script for the painter memory film
```

### Active Project Context

OpenClaw talks to the studio through MCP, so active project resolution is an MCP concern
before it is a graph concern. The MCP layer should maintain an active project per
conversation/session when possible.

Rules:

- if one project is active, user can say "continue", "show references", or "approve this phase"
- if no project is active, the system asks for project id, slug, or title
- if multiple projects match, the system shows candidates and asks the user to choose
- destructive or expensive actions should still confirm the resolved project

### Project Lookup

The MCP surface should expose project lookup tools:

- `list_projects`
- `find_project`
- `set_active_project`
- `get_active_project`
- `get_project_summary`

Suggested lookup behavior:

1. Try exact `project_id`.
2. Try exact slug.
3. Try exact title.
4. Try alias.
5. Try fuzzy title match.
6. If ambiguous, ask user to pick.

### Request Envelope

Every MCP request should resolve into a request envelope before the orchestrator changes
state:

```json
{
  "request_id": "req_000123",
  "project_ref": "memory-in-color",
  "resolved_project_id": "film_2026_0001",
  "active_phase": "visual_development",
  "user_intent": "inspect_reference_images",
  "requires_confirmation": false
}
```

This prevents agents from acting on the wrong film.

### Project Context In Artifacts

Every artifact should include:

- `project_id`
- `project_slug`
- `phase`
- `artifact_id`
- `version`

This matters because multiple films may share agents, providers, validators, and KB context.

### Ambiguity Policy

The system should not guess when project identity is ambiguous.

Examples that require clarification:

- two projects have similar titles
- user says "the painter film" and multiple aliases match
- a request would spend budget but no active project is set
- a request would approve or reject a phase for an inferred project

For low-risk read-only queries, fuzzy matching can show likely candidates. For approval,
generation, deletion, provider spend, or final delivery, explicit project resolution is
required.
