# Knowledge Base Operating Model

## Purpose

The knowledge base is the studio memory system. It should not be a pile of documents that
agents search randomly. It should be organized, tagged, versioned, and retrieved through the
orchestrator so every agent gets the right knowledge at the right time.

The KB has three jobs:

- preserve lessons from previous films
- provide executable policy and reusable patterns
- help agents make better creative and operational decisions without flooding context

## Core Principle

Not every piece of knowledge has equal authority.

The system must distinguish between:

- active rules the pipeline must follow
- recommended patterns agents should consider
- historical lessons used for risk detection
- raw archive material used only when explicitly retrieved

This prevents older scripts, superseded provider rules, or one-off project choices from
overriding the current studio design.

## Recommended Structure

Suggested future structure:

```text
film-knowledge-base/
  index/
    kb-manifest.yaml
    source-registry.yaml
    concept-taxonomy.yaml
    embeddings/
  canonical/
    policies/
    schemas/
    rubrics/
    prompt-frameworks/
    provider-contracts/
  playbooks/
    writing/
    reference-images/
    environment-consistency/
    generation/
    validation/
    post-production/
    recovery/
  case-studies/
    primordial-stroke/
    camino-del-genesis/
    postmortems/
  examples/
    prompts/
    matrices/
    validation-reports/
    reference-packages/
    assembly-manifests/
  providers/
    seedance/
    veo/
    openrouter/
  archive/
    pdfs/
    legacy-skills/
    old-scripts/
    raw-notes/
  project-lessons/
    film_2026_0001/
```

The current `film-knowledge-base/` already contains many of these ingredients. The work is
mostly to classify and index them, not to start over.

## Knowledge Authority Levels

Every KB item should have an authority level.

### Level 1. Canonical Policy

Use for rules the system should enforce.

Examples:

- RCTCO prompt framework
- approved artifact schemas
- validation threshold policy
- checkpoint and resume policy
- provider adapter contract
- human approval gate policy

These can become config, schemas, validators, or graph guards.

### Level 2. Active Playbook

Use for recommended workflows.

Examples:

- reference image generation flow
- environment consistency method
- sequential clip generation
- multi-angle coverage strategy
- post-production assembly method

Agents should use these unless the project profile overrides them.

### Level 3. Case Study Lesson

Use for reasoning and risk detection.

Examples:

- postmortem mistakes
- previous film drift patterns
- cost surprises
- provider failure examples
- scenes where continuity broke

The orchestrator should use these to warn, validate, and ask better questions.

### Level 4. Raw Archive

Use for searchable background only.

Examples:

- PDFs
- old scripts
- older skills
- raw project notes
- generated carousels

Raw archive items should not become runtime policy until curated and promoted.

## KB Item Metadata

Every curated KB item should have metadata.

```yaml
id: kb.policy.prompt.rctco.v1
title: RCTCO Prompt Framework
authority: canonical
status: active
version: 1
domains:
  - prompting
  - agent-contracts
applies_to:
  phases:
    - all
  agents:
    - all
modalities:
  - text
source_refs:
  - film-knowledge-base/prompt-framework.md
last_reviewed: 2026-06-19
owner: studio
conflicts_with: []
supersedes: []
summary: Use Role, Core Task, Context, Constraints, and Output for agent prompts.
```

Required fields:

- `id`
- `title`
- `authority`
- `status`
- `version`
- `domains`
- `applies_to`
- `source_refs`
- `summary`

Useful optional fields:

- `provider`
- `film_type`
- `risk_tags`
- `cost_tags`
- `validation_tags`
- `supersedes`
- `conflicts_with`
- `examples`
- `embedding_refs`

## Taxonomy

The KB should be tagged across several dimensions so retrieval can be precise.

Domain tags:

- `creative-writing`
- `story-structure`
- `dialogue`
- `character`
- `environment`
- `camera`
- `reference-images`
- `prompting`
- `generation`
- `validation`
- `continuity`
- `provider`
- `cost`
- `post-production`
- `recovery`
- `mcp`

Phase tags:

- `intake`
- `constitution`
- `treatment`
- `script`
- `scene-design`
- `shot-design`
- `references`
- `generation`
- `clip-validation`
- `scene-validation`
- `act-validation`
- `movie-validation`
- `post-production`
- `delivery`
- `wrap`

Modality tags:

- `text`
- `image`
- `video`
- `audio`
- `metadata`
- `code`
- `schema`
- `prompt`

Risk tags:

- `identity-drift`
- `environment-drift`
- `continuity-break`
- `cost-overrun`
- `provider-failure`
- `moderation-risk`
- `weak-story`
- `bad-reference`
- `duplicate-generation`

## Extension Model

The KB should be easy to extend without breaking existing behavior.

New knowledge enters through an ingestion flow:

1. add source file or external note
2. create source registry entry
3. classify authority level
4. tag domains, phases, modalities, and risks
5. extract atomic knowledge cards
6. link to source references
7. run conflict detection against active policy
8. human approves promotion if it affects runtime behavior
9. update KB manifest and search index

Only human-approved items should become canonical policy.

Suggested source registry entry:

```yaml
source_id: source.article.film-pipeline-postmortem.v1
path: film-knowledge-base/articles/ART-029-film-pipeline-postmortem/article.md
source_type: postmortem
status: curated
authority_ceiling: case_study
domains:
  - generation
  - validation
  - recovery
  - cost
ingested_at: 2026-06-19
```

`authority_ceiling` prevents raw or anecdotal sources from accidentally becoming hard policy.

## Knowledge Cards

Large documents should be decomposed into small knowledge cards.

Example:

```yaml
id: kb.lesson.generation.no-duplicate-submit.v1
authority: canonical
domain: generation
phase: generation
risk_tags:
  - duplicate-generation
  - cost-overrun
statement: Do not resubmit a generation request when a provider job id may already exist.
reason: Ambiguous provider failures can still create billable jobs.
actionable_policy:
  - persist ledger before submit
  - store provider job id immediately
  - resume polling before any retry
source_refs:
  - film-knowledge-base/skills/film-production-pipeline/references/checkpoint-system.md
  - docs/clip-generation-execution.md
```

Cards are easier for retrieval than huge documents and easier for humans to review.

## Orchestrator Usage

The orchestrator should never dump the whole KB into an agent prompt.

Instead, it should build a KB context packet for each graph node.

Flow:

1. determine current project, phase, artifact, and task
2. identify active agent and allowed KB domains
3. retrieve canonical policies first
4. retrieve active playbooks second
5. retrieve case-study risks third
6. retrieve examples only if useful
7. summarize or compress retrieved context
8. attach source refs and authority levels
9. pass the packet into the agent using RCTCO
10. store the `kb_context_ref` on the produced artifact

Suggested context packet:

```json
{
  "kb_context_id": "kbctx:S001-01:prompt-composition:v1",
  "project_id": "film_2026_0001",
  "phase": "generation",
  "agent_id": "prompt-composition-agent",
  "task": "compose video prompt for shot S001-01",
  "authority_policy_refs": [
    "kb.policy.prompt.rctco.v1",
    "kb.policy.generation.no_duplicate_submit.v1"
  ],
  "playbook_refs": [
    "kb.playbook.reference_images.video_prompt_package.v1",
    "kb.playbook.environment.locked_prompt_block.v1"
  ],
  "case_study_refs": [
    "kb.lesson.environment_drift.primordial_stroke.v1"
  ],
  "examples": [],
  "excluded_refs": [
    {
      "ref": "kb.archive.seedance_legacy_retry_rule.v1",
      "reason": "Superseded by current provider-block policy."
    }
  ]
}
```

Every generated artifact should record which KB context influenced it. This gives us
debuggability when an agent makes a strange decision.

## Agent Access Rules

Each agent should declare what KB it can use.

Example:

```yaml
agent_id: environment-continuity-validator
allowed_kb_domains:
  - environment
  - continuity
  - validation
  - reference-images
required_authority:
  - canonical
  - active_playbook
optional_authority:
  - case_study
blocked_domains:
  - provider-pricing
  - dialogue-style
```

This keeps agents focused and reduces accidental contamination.

Examples:

- `dialogue-agent` gets character voice, theme, scene intent, and writing style playbooks.
- `reference-image-agent` gets character, environment, camera, provider image constraints, and bad-reference examples.
- `provider-planning-agent` gets provider contracts, cost policy, failure modes, and budget rules.
- `clip-validator` gets shot intent, prompt package, reference package, continuity ledger, and validation rubrics.
- `failure-handling-agent` gets provider health policy, error handling playbooks, budget state, and postmortem lessons.

## Retrieval Strategy

Use layered retrieval, not one generic vector search.

### 1. Deterministic Retrieval

Always include required canonical rules by id.

Examples:

- RCTCO framework for all prompts
- project config resolution policy during intake
- checkpoint policy before generation
- validation schema for validators

### 2. Tagged Retrieval

Retrieve by phase, domain, modality, and risk tags.

Example:

```yaml
phase: references
domains:
  - reference-images
  - character
  - environment
risks:
  - bad-reference
  - identity-drift
```

### 3. Semantic Retrieval

Use embeddings or search for nuanced creative and historical context.

Use for:

- similar story problems
- prior failure patterns
- style references
- unusual provider behavior

### 4. Example Retrieval

Retrieve examples only when the agent needs a format or pattern.

Examples should be labeled as examples, not policies.

## Conflict Handling

The KB will contain contradictions. That is normal.

Conflict rules:

- canonical policy beats playbook
- active playbook beats case study
- current project profile beats generic preference
- newer active version beats older active version
- superseded items are not injected unless explicitly requested
- raw archive never overrides curated knowledge

If two active canonical policies conflict, the orchestrator should create a KB conflict issue
and ask for human decision.

Example conflict:

- old skill says fallback provider after insufficient quota
- current direction says stop provider queue until credit issue is solved unless approved

Resolution:

- active policy: stop affected queue and ask human
- old lesson remains useful as historical context, not automatic behavior

## KB Feedback Loop

Every project should improve the KB.

At wrap, the orchestrator should ask:

- What failed?
- What worked?
- Which validations caught real problems?
- Which validations were noisy?
- Which references helped continuity?
- Which provider assumptions were wrong?
- Which prompts should become examples?
- Which policies need revision?

Outputs:

- project lesson cards
- provider incident records
- validation tuning notes
- prompt examples
- reference examples
- postmortem draft

New lessons should start as `case_study` or `project_lesson`, then be promoted later if they
prove reusable.

## MCP Tools

Because the project is MCP-first, KB operations should be exposed through MCP.

Suggested tools:

- `kb_search`
- `kb_get_item`
- `kb_list_sources`
- `kb_get_context_packet`
- `kb_explain_context_choice`
- `kb_add_source`
- `kb_ingest_source`
- `kb_create_card`
- `kb_propose_promotion`
- `kb_approve_promotion`
- `kb_report_conflict`
- `kb_list_conflicts`
- `kb_attach_lesson_to_project`
- `kb_export_project_lessons`

The user should be able to ask OpenClaw:

- "Why did the orchestrator use this rule?"
- "What lessons from the postmortem apply here?"
- "Show me all KB items affecting reference images."
- "Promote this lesson into an active playbook."
- "Do not use that old provider rule anymore."

## Storage And Indexing

The first MVP does not need a complex knowledge platform.

Start with:

- markdown/YAML files for curated cards
- a manifest file for item metadata
- ripgrep/full-text search
- optional embeddings later
- source refs stored on every context packet

Add later:

- vector index
- hybrid retrieval
- UI for promotion/review
- automatic card extraction
- conflict detector
- stale-policy detector

## Minimum MVP

For the first implementation, build:

1. KB manifest with authority levels and tags
2. curated cards for RCTCO, provider policy, checkpoints, validation, references, and continuity
3. orchestrator context-packet builder
4. per-agent KB access declarations
5. MCP tools for search, context inspection, and source lookup
6. artifact metadata field `kb_context_ref`
7. wrap-phase lesson capture

This gives us a living studio memory without letting the KB become noisy or dangerous.
