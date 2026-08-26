# Repository Adaptation Audit: Interactive Generative Cinema

Status: repository evidence audit and architecture proposal  
Audit date: 2026-08-25  
Repository snapshot: branch `code-improvments`, commit `b5b533e`, plus the uncommitted
working-tree changes disclosed below

## Executive finding

The repository has a useful **authoring-plane foundation**, not an interactive-cinema
runtime. Its strongest reusable elements are the approved creative bibles, typed artifact
metadata, checkpoint and rollback semantics, structured validation, provider job lifecycle,
generation ledger, and MCP mutation boundary. These can prepare and govern an interactive
experience bundle.

The current execution model should not be stretched into the viewer hot path. It is a fixed,
phase-oriented production graph invoked synchronously around large artifacts and human gates.
The anchor experience instead needs a session-scoped event log, optimistic concurrency,
rolling-horizon segment scheduling, deadline-aware validation, fallback selection, cancellation,
and a low-latency playback/event channel. None is presently demonstrated.

The safest seam is therefore:

1. keep the existing linear graph as the **studio authoring and publication plane**;
2. publish an immutable, approved `InteractiveExperienceBundle` from its artifacts;
3. add an isolated **interactive session runtime** with its own state machine and persistence;
4. admit every viewer mutation through typed MCP session tools;
5. deliver media through immutable resource references while events/status use a persistent
   streaming transport; and
6. export each completed session back into the existing artifact/audit world as a replayable
   `SessionManifest`.

This supports a bounded prototype without destabilizing the validated-clips workflow. It does
not prove playable latency, creative quality, safety, concurrency, or viable cost.

## Scope and evidence rules

This audit read the canonical architecture and product-completion documents, relevant source,
and relevant tests. It did not modify production code or tests. “Implemented” below means a
code path exists in the inspected snapshot. “Test observed” means assertions were read.
“Executed” means the focused command listed under [Validation performed](#validation-performed)
ran during this audit. Neither mocks nor constructed state count as live provider, concurrent
viewer, or audiovisual playback proof.

The current checkout was already dirty. Fourteen source files had unrelated modifications,
including `agents/model_adapter.py`, `agents/runner.py`, `generation/executor.py`, multiple graph
nodes, `mcp/server.py`, and checkpoint/validation MCP tools. The new research directory was also
untracked. This document describes the filesystem actually inspected, not a clean commit. Any
implementation planning should re-audit after those changes settle.

## Current capability evidence matrix

| Capability | Documented intent | Implemented symbols and behavior | Test/assertion evidence | Maturity for this idea | Missing live proof |
|---|---|---|---|---|---|
| MCP-first boundary | `documentation/architecture-blueprint.md:11-32` makes MCP the product boundary and lists approvals, generation, rollback, health, and export. | `ToolContract` records mutation, confirmation, checkpoint, and optional idempotency metadata (`src/film_pipeline/mcp/contract.py:45-57`). `MCPServer.call()` resolves a project, checks confirmation, and dispatches (`src/film_pipeline/mcp/server.py:28-57`, `146-190`). | Observed integration assertions drive create → idea → approval through MCP handlers (`tests/integration/test_mcp_flow.py:44-178`). Not executed in this audit. | Reusable control-plane concept; current contracts are underspecified. | No authenticated multi-viewer transport, session tools, high-rate call test, event subscription, or p95 acknowledgement measurement. |
| Phase graph and human gates | The architecture assigns state, interrupts, resumability, routing, validation, and approval to LangGraph (`documentation/architecture-blueprint.md:34-60`). | `build_graph()` wires eleven ordered phase nodes, consistency, approval, repair, and end (`src/film_pipeline/graph/graph.py:59-166`). `await_approval_node()` uses LangGraph `interrupt()` and keeps an agent recommendation advisory (`src/film_pipeline/graph/nodes/approval.py:61-187`). | Executed tests cover checkpointer selection/compilation and gate payload/approval blocking (`tests/unit/graph/test_graph.py:14-40`; `tests/unit/graph/test_real_human_gates.py:18-90`, `198-231`). | Strong offline workflow primitive; wrong state granularity for playback. | No session graph, intervention race, per-segment deadline, concurrent branch, or playback recovery test. |
| Creative constitution | The blueprint defines a film constitution as creative law (`documentation/architecture-blueprint.md:173-200`). | `FilmConstitution` types theme, tone, emotional promise, visual/camera language, character truths, taboo mistakes, and quality bar (`src/film_pipeline/schemas/film_constitution.py:14-44`). | Observed artifact-spine assertions require non-empty theme, tone, truths, and taboos (`tests/integration/test_artifact_spine.py:36-57`). Not executed. | Directly reusable as immutable creator policy after adding machine-checkable invariant IDs and severities. | No evidence that live generated branches obey it, no invariant coverage metric, and no creator study. |
| Story, character, and environment bibles | The blueprint treats canonical data structures as the production backbone (`documentation/architecture-blueprint.md:162-170`). | `StoryBible` contains act/scene/setup-payoff structure (`src/film_pipeline/schemas/story_bible.py:24-75`). `CharacterBible` locks identity, voice, relationships, references, and `must_not_change` (`src/film_pipeline/schemas/character.py:59-80`). `EnvironmentBible` locks prompt blocks, zones, viewpoints, lighting, references, and invariants (`src/film_pipeline/schemas/environment.py:48-68`). | Observed artifact-spine tests prove some persisted authoring outputs. Schema import/validation was exercised indirectly by the focused set, but no interactive behavior exists. | High-value inputs to an experience compiler. Current story model is an ordered scene list, not a causal choice graph. | No authored choice grammar, reachable-ending analysis, dramatic-obligation solver, state-variable ownership, or branch coherence study. |
| Continuity state | The blueprint calls for state-in/state-out continuity in the film matrix. | `ContinuityLedgerEntry` holds shot-boundary character, prop, wardrobe, environment, lighting, thread, risk, and anchor state (`src/film_pipeline/schemas/continuity.py:10-39`). | Executed validator tests detect undocumented character-state changes and pass a clean sequence (`tests/e2e/test_scenario_06_continuity_drift.py:64-112`). | Reusable vocabulary, but only linear adjacent-shot reasoning. | No causal world-state reducer, choice preconditions/effects, branch merge semantics, long-horizon contradiction checks, or delivered-media identity score. |
| Versioned artifacts and lineage | Product completion requires typed, persisted artifacts with metadata and lineage (`documentation/product-completion/02-phase-execution-and-artifacts.md:10-79`). | `ArtifactMetadata` includes parents, validation, approval, KB, schema version, and `built_from` (`src/film_pipeline/schemas/artifact.py:19-43`). `ArtifactStore` saves version and current JSON/metadata/Markdown and supports approval/supersession (`src/film_pipeline/artifacts/store.py:20-147`). | Executed tests cover save/load, sidecars, versions, approval, supersession, and filesystem review rendering (`tests/unit/test_artifacts.py:68-278`). | Good publication substrate for immutable experience and delivered-segment manifests. Not a hot event store. | No content hash in the core metadata, atomic multi-record commit, compare-and-swap, concurrent writer test, retention policy, object-store/CDN proof, or exact replay receipt for a viewer session. |
| Checkpoint, rollback, and branch vocabulary | The product standard requires real rollback and audit. | `CheckpointMetadata` links artifact versions, state, approvals, validation, budget, and git (`src/film_pipeline/schemas/checkpoint.py:19-38`). `BranchMetadata` and `BranchManager` create git-backed creative branches (`src/film_pipeline/schemas/checkpoint.py:63-70`; `src/film_pipeline/checkpoints/branches.py:12-44`). | Executed tests cover git-backed checkpoint metadata, rollback/invalidation, and alternate-ending branch creation (`tests/unit/checkpoints/test_checkpoints.py:50-220`). | Reusable for authoring experiments and session export. Git branches are not a per-viewer session mechanism. | No thousands-of-sessions scale, concurrent branch commits, segment-level recovery-time measurement, session fork/rejoin semantics, or retained-media replay test. |
| Provider abstraction | The blueprint defines build → submit → poll → download → metadata → estimate and optional cancel. | `BaseProviderAdapter` implements that contract synchronously (`src/film_pipeline/providers/base.py:14-82`). Registry lookup and enablement exist (`src/film_pipeline/providers/registry.py:10-32`). | Provider/mock tests exist; the focused set exercised executor behavior with test adapters, not live providers. | Reusable job adapter for background generation. It assumes whole jobs, not deadline-aware segment supply. | No measured latency distribution, queue delay, partial result, streaming decode, priority/deadline, cancellation effectiveness, concurrency/quota envelope, or live fallback routing proof. |
| Generation ledger and idempotency | Product completion requires durable, recoverable, duplicate-safe generation (`documentation/product-completion/05-generation-providers-and-post.md:10-60`). | Typed requests and rows track provider jobs, poll count, cost, output, error, resume token, and next action (`src/film_pipeline/schemas/generation.py:13-87`). `GenerationExecutor` plans, submits, polls, downloads, and records assets (`src/film_pipeline/generation/executor.py:55-287`). `GenerationLedgerManager.plan_batch()` de-duplicates by `shot_id` (`src/film_pipeline/generation/ledger.py:53-91`). | Executed unit/integration tests cover planning, idempotence, submit, poll, failure, status, local cancellation, and prompt resolution (`tests/unit/generation/test_executor.py:126-426`; `tests/integration/test_generation_mcp.py:47-163`). Executed E2E-labeled tests assert preserved job IDs, but two use constructed ledger objects rather than a real failed request (`tests/e2e/test_scenario_05_network_error.py:22-86`). | Useful background work ledger with mock-level evidence. Current de-duplication is too coarse for alternate branch takes and not concurrency-safe. | No real ambiguous-submit receipt, deterministic idempotency enforcement at provider boundary, simultaneous submit test, deadline expiry, stale-horizon cancellation, or cost-per-delivered-viewer-minute evidence. |
| Cancellation | Provider cancellation is part of the documented contract. | The base adapter defaults to unsupported (`src/film_pipeline/providers/base.py:79-82`). `cancel_generation_request()` marks an unsubmitted row cancelled or delegates to the provider (`src/film_pipeline/mcp/tools/generation/dispatch.py:188-239`). | Executed integration tests prove local cancellation before provider submission (`tests/integration/test_generation_mcp.py:132-149`). | Partial primitive. | No cancellation race, provider-side live cancellation, orphan-job reconciliation, sunk-cost accounting, branch invalidation fan-out, or cancellation latency measurement. |
| Validation and gating | Product completion says validation must change behavior (`documentation/product-completion/04-validation-and-mcp-product-surface.md:8-72`). | `BaseValidator.run()` converts findings into typed reports and a blocking status contract (`src/film_pipeline/validation/base.py:249-290`). Router blocks/revises on validation status (`src/film_pipeline/graph/router.py:239-276`). | Executed validator suite and continuity scenario cover rule findings and blocking behavior (`tests/unit/validation/test_impl_validators.py`; `tests/e2e/test_scenario_06_continuity_drift.py:64-112`). | Strong pattern for offline gates; not designed for a sub-second acknowledgement or bounded segment deadline. | No input moderation, output policy validator, branch-canon validator, deadline/circuit breaker, safe fallback under validator timeout, multimodal live evidence, or false-positive/false-negative study. |
| Streaming | No current product requirement for viewer playback streaming. | LangGraph itself can emit state values; an observed E2E test calls `graph.stream()` (`tests/e2e/test_graph_execution.py:51-65`). Production runtime instead uses blocking `graph.invoke()` (`src/film_pipeline/app/_graph_exec.py:40-76`). The stdio server reads one message and calls `asyncio.run()` per request (`src/film_pipeline/mcp/server.py:326-341`). | Graph stream test observed, not executed. No MCP streaming test exists in the audited set. | Framework capability only, not a product transport. | No Streamable HTTP/SSE/WebSocket delivery, events cursor, resumable subscription, backpressure, playback buffer, media range delivery, or stall measurement. |
| Audit and metrics | The architecture requires auditable actions; acceptance docs cite stored audit records. | Runtime persists a JSON audit list (`src/film_pipeline/app/_persistence.py:206-246`). Separate `AuditTrail` and `MetricsCollector` are explicitly in-memory and described as future production integrations (`src/film_pipeline/observability/audit.py:43-77`; `src/film_pipeline/observability/metrics.py:20-58`). | Observed happy-path E2E checks only that events exist (`tests/e2e/test_scenario_01_happy_path.py:83-91`). Not executed. | Useful event vocabulary, insufficient session observability. | No distributed trace context, intervention-to-segment causal ID, histograms/percentiles, queue depth, branch amplification, fallback reason, per-viewer cost, alert, or load-test receipts. |
| Budget and pricing | The graph considers budget and generation requires spend approval. | `BudgetState` tracks project/phase caps and spent amounts (`src/film_pipeline/schemas/budget.py:35-48`). Generation spend approval checks estimated batch total (`src/film_pipeline/generation/ledger.py:95-139`). Static provider rates exist (`src/film_pipeline/providers/pricing.py:16-58`). | Executed generation tests cover state transition, not realistic pricing or session economics. | Reusable accounting inputs; wrong unit of control. | No session cap, decision cap, reserved-vs-actual cost, cancelled-job charge, cache attribution, storage/egress, concurrency sensitivity, or cost per delivered viewer-minute. |
| Security and safety | Repository rules prohibit secrets and require confirmations for dangerous tools. | Envelopes carry actor fields but do not authenticate them (`src/film_pipeline/mcp/envelope.py:15-48`). Credentials come from environment/`.env` and have pattern redaction (`src/film_pipeline/providers/credentials.py:19-58`). Filesystem deletion has safe-root guards (`src/film_pipeline/app/safety.py:54-92`). | Security-focused tests exist for credentials and deletion safety; not executed in this audit. | Local-operator safety, not a multi-user trust boundary. | No authentication, authorization, tenant/session isolation, rate limits, replay protection, prompt-injection boundary, moderation evidence, privacy retention/deletion, abuse monitoring, or signed media access. |

## Reusable contracts

### Reuse without changing meaning

- `FilmConstitution`, `CharacterBible`, and `EnvironmentBible` should remain creator-approved
  immutable inputs. An interactive session may select among allowed variations but must not
  edit these source artifacts.
- `ArtifactMetadata` and `ArtifactStore` can publish the experience bundle and archive the final
  session manifest. Additive metadata fields or a specialized store adapter are preferable to
  changing existing artifact meaning.
- `ValidationReport` and validator registry conventions can represent publish-time and segment
  findings. Interactive validation needs additional deadline and fallback metadata, not an
  incompatible result shape.
- `BaseProviderAdapter` and provider registry can back asynchronous segment generation workers.
  The interactive scheduler should depend on a narrower job-service port rather than call
  concrete adapters from the session reducer.
- `GenerationLedgerRow` provides useful job-status vocabulary. Interactive segment jobs need a
  distinct ledger because a shot can have multiple branch-, horizon-, and session-specific
  attempts.
- MCP confirmation, project resolution, structured errors, and mutation catalog metadata should
  remain the external control convention.
- The current linear graph remains the only supported idea-to-validated-clips path until an
  interactive bundle passes its own publication gate.

### Reuse only after strengthening

- Convert creative prose that must be machine-enforced into stable invariant IDs, severity,
  scope, and deterministic predicates where possible. Preserve prose for human meaning.
- Treat `StoryBible.scene_list` as source material. Compile it into an explicit causal story
  graph with choice preconditions, effects, dramatic obligations, convergence points, and
  allowed endings.
- Give stored bundle and segment manifests content hashes and immutable references. Exact replay
  must resolve retained bytes; regeneration is a separate operation and cannot satisfy replay.
- Preserve the current approval distinction between candidate and approved. Add a separate
  publication status so “approved for production work” does not silently mean “safe for viewer
  interaction.”
- Carry `request_id`, `session_id`, `intervention_id`, `decision_id`, `segment_id`, graph state
  version, and provider job ID through audit, validation, generation, and delivery.

### Do not reuse as the session mechanism

- Do not create a git branch per viewer. `BranchManager` is suitable for a small number of
  creator experiments, not high-cardinality sessions.
- Do not append viewer state to `StudioGraphState`. Its scalar `current_phase` and project-level
  append channels describe production, not many concurrent timelines.
- Do not treat `current.json` artifact pointers as mutable live-session state.
- Do not call a human approval interrupt after every viewer intervention. The creator must
  pre-authorize a policy envelope; hot-path automation must fail closed or choose an approved
  fallback.

## Architectural mismatches and required corrections

### 1. Batch phase graph versus live session loop

`PHASE_ORDER` is a single list from intake through delivery
(`src/film_pipeline/graph/router.py:22-34`), and the runtime keys a graph thread by project ID
(`src/film_pipeline/app/_graph_exec.py:62-70`). Interactive playback requires many session IDs
per project, repeated decision windows, partially prepared futures, and independent failure
recovery. Reusing the project graph would couple one viewer's state to authoring state and make
concurrent sessions unsafe.

**Correction:** compile a separate `InteractiveSessionGraph` keyed by `session_id`. Keep the
hot deterministic state reducer small: accept/reject intent, commit world-state transition,
select branch, update horizon, expose next segment, and close. Narrative/model planning and
media jobs run as durable activities whose results are joined by IDs. Never hold playback open
while a large phase node runs.

### 2. MCP control plane versus high-frequency interaction

The MCP abstraction is appropriate for typed mutations, but the current implementation is a
single-process stdio request loop with generic empty schemas from `_make()`
(`src/film_pipeline/mcp/tools/registry.py:96-112`). It exposes tools, not subscriptions or media
resources. Async handlers do not make synchronous provider and filesystem work concurrent.

**Correction:** retain MCP as the mutation and inspection boundary, with real JSON Schemas
generated from Pydantic models. For the prototype's four decision windows, a persistent MCP
Streamable HTTP session can be sufficient if measured. Add a resumable server-to-client event
stream and immutable media resource references; binary media delivery through a CDN/object
store is data delivery, not a hidden state-mutation API. If MCP transport cannot meet the 500 ms
acknowledgement target under load, record that as an architectural result instead of silently
bypassing MCP.

### 3. Human approvals versus playback deadlines

Current major phase approvals are intentionally blocking and correct for studio production.
They are incompatible with a viewer waiting for the next segment.

**Correction:** split authority:

- creators approve constitution, intent vocabulary, reachable story graph, asset rights,
  fallback segments, safety policy, budget envelope, and publication;
- viewers choose only inside that published envelope;
- automated hot-path validators may accept, map, reject, or fall back, but never expand viewer
  authority;
- operators may pause an experience, revoke an asset, or terminate sessions through confirmed
  tools; and
- changes to published canon create a new bundle version. Existing sessions remain pinned or
  are terminated by explicit policy.

### 4. Artifacts versus event sourcing

The artifact store writes whole JSON documents to version and `current` files and derives the
next version by scanning the filesystem (`src/film_pipeline/artifacts/store.py:67-90`,
`154-167`). There is no atomic compare-and-swap. Two session writers could lose events or assign
the same version.

**Correction:** use an append-only session event store with a unique `(session_id, sequence)`
constraint, idempotency keys, expected-state-version checks, and atomic transaction boundaries.
Store large immutable media separately by digest. Project artifacts publish bundles and archive
final manifests; they do not coordinate live state.

### 5. Checkpoints and branches versus session scale

Git commits/tags offer inspectable authoring checkpoints. They amplify filesystem and process
cost if applied per segment or viewer.

**Correction:** snapshot the folded session state every bounded number of events and at each
committed decision. Recovery replays later events. Session forks share a parent manifest and
immutable segment refs; they do not copy media or create git branches. Export a completed session
to one existing artifact/checkpoint only when retention policy requires it.

### 6. Validators versus deadline-aware safe delivery

Current validators consume complete artifact dictionaries and may fall back from failed LLM
validation to rules (`src/film_pipeline/validation/base.py:77-93`). The continuity rule sees
only adjacent shot fields. An empty sequence scores 100
(`src/film_pipeline/validation/impl/scene_continuity.py:165-182`), which is safe for “nothing to
inspect” only if upstream completeness is independently enforced.

**Correction:** define four gate classes:

1. publish-time exhaustive graph/canon/rights/accessibility validation;
2. intervention input policy and intent-mapping validation;
3. plan-time causal/canon/budget/deadline validation; and
4. segment-time media, identity, prompt-adherence, continuity, and safety validation.

Every hot gate needs `deadline_at`, `validator_version`, `evidence_refs`, `timed_out`, and
`fallback_action`. Missing evidence or validator timeout cannot become a pass. A pre-approved
fallback segment must remain playable while repair continues off the hot path.

### 7. Provider jobs versus rolling-horizon supply

The current executor scans a shot matrix, sends whole jobs, polls them, then downloads outputs.
It does not express playback deadlines, horizon slots, priority inversion, cached alternatives,
or readiness probability.

**Correction:** a horizon scheduler maintains at least the committed segment plus candidate
successors. Each slot has a deadline, priority, dependency set, estimated cost, cache key, and
approved fallback. Workers may reuse current adapters initially, but scheduler decisions must
be provider-neutral and recorded. Stale speculative jobs are cancelled when useful and charged
to the branch that caused them.

### 8. Cancellation and supersession

Current cancellation targets one generation ID and may be unsupported by the provider. It does
not prevent a late completion from becoming visible after the viewer chose another branch.

**Correction:** every result is fenced by `session_id`, `horizon_epoch`, and `decision_id`.
Cancellation marks intent; a late job can be archived or cached but cannot populate the active
horizon unless its fence still matches. Reconciliation periodically accounts for orphan jobs.
### 9. Concurrency and consistency

`StudioRuntime` keeps projects and active project selection in process memory
(`src/film_pipeline/app/runtime.py:34-54`). Artifact saves and generation ledger updates rewrite
whole documents without locks. `shot_id` de-duplication also prevents legitimate alternate
takes while not protecting simultaneous processes.

**Correction:** make session mutations transactionally serialized per session, not globally.
Require `expected_state_version` and an idempotency key on every viewer mutation. Return a typed
conflict with the current version rather than last-write-wins. Provider dispatch uses a durable
outbox/lease so exactly-once business effects are achieved through idempotence even though
delivery is at least once.

### 10. Observability

Current collectors are in-memory and lack distributions. Interactive product decisions require
causal traces across input, policy, planning, validation, queueing, provider, delivery, and
playback.

**Correction:** emit traces and metrics for acknowledgement latency, consequence latency,
response distance, ready-buffer seconds, stalls, fallback reason/rate, canon/identity failures,
job waste, cache hit, branch amplification, recovery time, and cost per delivered viewer-minute.
Every metric needs experience version, region, provider/model, quality tier, cache state, and
concurrency cohort without placing raw viewer text in labels or logs.

### 11. Security, privacy, and abuse

Actor fields in `RequestEnvelope` are caller-supplied context, not authentication. Project
resolution is not authorization. A public viewer input also introduces prompt injection,
attempted policy escape, personal data, copyrighted-character requests, and denial-of-wallet
risks absent from the current local operator model.

**Correction:** authenticate users and services; authorize experience/session access; bind a
session token to its immutable experience version; rate-limit and quota by principal; validate
sequence/idempotency to resist replay; map natural language into a bounded intent vocabulary;
keep raw text out of generation prompts and long-term logs by default; moderate both input and
output; sandbox retrieval and tools; sign short-lived media access; encrypt transport/storage;
and implement retention, deletion, incident, and asset-revocation workflows. None of these is
proven by the current credential redaction or safe-delete code.

### 12. Unit economics

The current budget gates a production batch. Interactive economics include speculative work,
abandoned sessions, failed validation, cancelled provider jobs, cached branch reuse, storage,
egress, moderation, orchestration, and support.

**Correction:** reserve a per-session envelope at start, debit actual costs per job, expose a
remaining-cost forecast before accepting an expensive intervention, and select a pre-approved
fallback when the envelope would be exceeded. Report p50/p95 cost per delivered minute and
sensitivity to cache hit, choice distribution, concurrency, retry, and media quality.

## Proposed isolated architecture seam

```text
Existing studio authoring plane
  idea -> constitution -> story/visual bibles -> shot/generation plan -> approved assets
                                  |
                                  v
                     Experience compiler + publish gate
                                  |
                     immutable ExperienceBundle vN
                                  |
           +----------------------+----------------------+
           |                                             |
           v                                             v
MCP interactive control plane                    media resource plane
create/get/submit/fork/close                     immutable segment refs
           |                                     CDN/object-store bytes
           v
session command handler --CAS--> append-only session event store
           |                              |
           v                              v
deterministic state reducer         snapshot/replay/export
           |
           v
intent mapper -> policy/canon gate -> horizon scheduler -> durable job outbox
                                              |                 |
                                              v                 v
                                      fallback selector   provider workers
                                              |                 |
                                              +-------> segment validation
                                                               |
                                                               v
                                                   committed playable segment
```

### Ownership and package boundary

Add one deliberate domain package, `src/film_pipeline/interactive/`, only after updating the
architecture's package-boundary table. Suggested modules are:

- `schemas.py`: the typed models below;
- `compiler.py`: compile approved authoring artifacts into an experience bundle;
- `policy.py`: bounded intent and creator-invariant evaluation;
- `reducer.py`: pure `state + event -> state` fold;
- `sessions.py`: command handling, CAS, snapshots, and lifecycle;
- `story_graph.py`: reachability, preconditions/effects, obligations, and ending constraints;
- `horizon.py`: segment-slot planning and fallback selection;
- `jobs.py`: durable outbox, leases, fences, and reconciliation;
- `validation.py`: interactive validator orchestration and deadlines; and
- `telemetry.py`: causal events and metric names.

The package consumes existing domains through typed artifact/provider ports. It does not import
TUI, MCP handlers, or concrete filesystem paths. `graph` may host a separate session graph;
`mcp` maps typed requests into session commands. The current production graph is unchanged.

### Hot path state sequence

1. Client submits an intervention with session ID, idempotency key, and expected version.
2. Server authenticates/authorizes, validates size/rate, and returns an acknowledgement within
   the target whether accepted, rejected, duplicated, conflicted, or pending mapping.
3. Intent mapper produces only a governed intent. Raw text is not concatenated into a media
   prompt.
4. Policy/canon reducer evaluates preconditions and atomically appends a decision event plus the
   new canonical world-state version.
5. Horizon scheduler invalidates stale candidates, preserves the committed playable segment,
   and fills successor slots with cached/authored/generated options.
6. Validators either commit a segment or select a disclosed fallback before its deadline.
7. Client receives monotonic session events and retrieves immutable media by resource ref.
8. Close/export folds all committed events into a replay manifest containing exact segment refs
   and hashes.

## Proposed typed domain models

These are proposal-level Pydantic v2 contracts, not implemented behavior.

### Publication models

`InteractiveExperienceBundle`

- `experience_id`, `project_id`, `bundle_version`, `schema_version`, `published_at`;
- approved `constitution_ref`, story/character/environment/camera refs;
- `story_graph_ref`, `intent_vocabulary_ref`, `policy_bundle_ref`;
- `asset_manifest_ref`, `fallback_manifest_ref`, `rights_manifest_ref`;
- supported language/accessibility profiles;
- allowed provider/quality profiles and cost envelope;
- `content_hash`, `validation_refs`, `approval_ref`, and revocation status.

`StoryNode`

- `node_id`, `scene_intent_ref`, dramatic obligations introduced/resolved;
- entry/exit world-state predicates;
- playable segment candidates and fallback segment ref;
- decision-window definition, maximum dwell, and terminal ending class.

`StoryEdge`

- `edge_id`, `from_node_id`, `to_node_id`;
- allowed `intent_ids`, preconditions, deterministic state effects;
- creator priority, convergence group, prohibited outcomes, and cost/latency class.

`GovernedIntentDefinition`

- `intent_id`, human description, examples for mapping only;
- allowed parameter schema and value bounds;
- required/forbidden state predicates;
- safety class, cost class, and creator explanation.

### Session and event models

`InteractiveSession`

- `session_id`, `experience_id`, pinned `bundle_version`, principal pseudonymous ID;
- `status`, `state_version`, `event_sequence`, current node/segment;
- committed and candidate horizon epochs;
- locale/accessibility settings, budget reserved/spent;
- expiry/retention timestamps and parent session/decision for forks.

`CanonicalWorldState`

- versioned facts by stable ID;
- character, relationship, environment, prop, time, and revealed-knowledge state;
- unresolved threads, planted/payoff obligations, pacing/tone budget;
- immutable-fact digest and last committed decision ID.

`ViewerIntervention`

- `intervention_id`, `session_id`, `idempotency_key`, `expected_state_version`;
- input kind (`choice` or bounded natural language), value, locale;
- client timestamp and decision-window ID;
- optional privacy classification and explicit consent flags.

`IntentMapping`

- source intervention ID, mapped intent ID and typed parameters;
- confidence, ambiguity reasons, policy decision ref;
- disposition (`accepted`, `rejected`, `needs_clarification`, `fallback`);
- safe user-facing explanation and mapper/model version.

`DecisionCommit`

- `decision_id`, previous/new state version, chosen edge ID;
- exact input/mapping/policy refs;
- state patch plus before/after digests;
- horizon epoch, causal explanation, and committed timestamp.

`SessionEvent`

- `event_id`, `session_id`, monotonically increasing sequence, event type;
- causation/correlation IDs, state version, occurred/recorded times;
- typed payload, payload hash, actor/service identity, and schema version.

### Segment and execution models

`HorizonSlot`

- `slot_id`, `session_id`, `horizon_epoch`, ordinal, story node/edge;
- readiness state, deadline, priority, cache key, segment plan ref;
- primary and fallback segment refs; and cancellation/supersession fence.

`SegmentPlan`

- `segment_plan_id`, source state/decision/horizon versions;
- duration range, narrative intent, world-state in/out;
- character/environment/camera/audio/subtitle requirements;
- prompt/reference/provider plan refs;
- validation policy, maximum cost, deadline, and fallback ref.

`SegmentJob`

- `job_id`, `segment_plan_id`, attempt, provider/model, idempotency key;
- durable status, lease owner/expiry, provider job ID;
- queued/started/deadline/completed times;
- estimated/actual cost, cancellation request/outcome;
- input/output hashes, error class, and fence tuple.

`PlayableSegment`

- `segment_id`, immutable media/resource refs and byte hashes;
- source plan, decision, state, and experience versions;
- duration, codec/resolution/audio/subtitle metadata;
- validation/policy/provenance refs;
- readiness/expiry, fallback disclosure, and accessibility alternatives.

`SessionManifest`

- experience and bundle version;
- ordered decisions, state digests, and exact playable segment refs;
- input/policy/model/provider/validation metadata refs;
- cost totals, fallback/cancellation summary;
- audit root hash, retention class, and replay verification result.

## Proposed MCP product surface

All inputs and outputs must use explicit Pydantic-generated JSON Schemas. Every mutating call
must have a principal, request ID, session ID where applicable, idempotency key, and expected
version where applicable.

### Creator/operator tools

| Tool | Mutation and authority | Confirmation/idempotency |
|---|---|---|
| `compile_interactive_experience` | Compile approved project refs into a candidate bundle and static reachability report. Does not publish. | Idempotent by project inputs + compiler version. |
| `review_interactive_experience` | Return graph coverage, canon, fallback, rights, accessibility, cost, and validation evidence. | Read-only. |
| `publish_interactive_experience` | Freeze and expose one validated bundle version. | Explicit creator confirmation; checkpoint; idempotent publication key. |
| `pause_interactive_experience` | Reject new sessions/interventions while preserving replay. | Explicit operator confirmation. |
| `revoke_interactive_asset` | Prevent future delivery, identify affected sessions, and select safe replacement/termination policy. | Two-step impact report + confirmation. |
| `get_interactive_metrics` | Return SLO, fallback, violation, cost, and concurrency summaries with cohort definitions. | Read-only and privacy-aggregated. |

### Viewer/session tools

| Tool | Contract result | Notes |
|---|---|---|
| `create_interactive_session` | Pinned bundle version, session/version, first committed segment, event cursor, budget/privacy terms. | Idempotent; authenticated; no authoring mutation. |
| `get_interactive_session` | Sanitized state, current decision window, horizon readiness, next actions, and cursor. | Never exposes hidden branches, prompts, or private policy internals. |
| `submit_viewer_intervention` | `accepted`, `duplicate`, `conflict`, `rejected`, `needs_clarification`, or `fallback`, with acknowledgement time and causal ID. | Requires idempotency key and expected state version. Natural language is mapped, not forwarded. |
| `get_next_playable_segment` | Immutable segment metadata/resource ref or declared wait/fallback with retry/event cursor. | Read-only; must not trigger hidden unbounded spend. |
| `cancel_pending_direction` | Cancels only uncommitted horizon work caused by the named intervention. | Version checked; provider cancellation is best effort and separately reported. |
| `fork_interactive_session` | New session pinned to a committed decision and shared immutable history. | Explicit viewer action; policy and retention checked. |
| `close_interactive_session` | Final manifest ref and replay-verification state. | Idempotent. |
| `get_session_manifest` | Ordered decision/segment/audit summary within access policy. | Read-only. |

### Events and resources

Add a resumable session-event subscription with `after_sequence`/cursor semantics and bounded
retention. Events include acknowledgement, intent disposition, horizon update, segment ready,
fallback selected, recoverable error, and session closed. Events are advisory views of durable
state; reconnecting clients reconcile through `get_interactive_session`. Media resource refs
must be immutable and short-lived access must not alter the manifest identity.

## Migration and compatibility plan

### Stage 0 — Freeze the boundary

- Re-run the audit on a clean commit after current changes merge.
- Add contract tests proving the existing validated-clips workflow and tool catalog remain
  unchanged.
- Record current artifact/schema versions and define additive compatibility rules.
- Do not modify `PHASE_ORDER`, existing project IDs, or current artifact path semantics.

Exit: current focused and full repository gates are green on the chosen baseline.

### Stage 1 — Compile only

- Implement proposal schemas and an offline compiler from approved constitution/story/visual
  artifacts to a candidate experience bundle.
- Validate reachability, all decision windows, all ending classes, invariant coverage, fallback
  coverage, asset rights, accessibility metadata, and worst-case branch cost.
- Persist only candidate artifacts. No viewer session, provider call, or public endpoint.

Exit: the anchor bundle statically validates; every reachable node has an approved playable
fallback; failures are reproducible fixtures.

### Stage 2 — Deterministic text/story simulator

- Add append-only in-process/test session store behind a port, pure reducer, CAS/idempotency,
  session graph, and MCP tools.
- Use authored text segment manifests only. No paid providers.
- Add model-based/property tests for all choice sequences, duplicates, reorder, conflicts,
  crashes, forks, invalid inputs, and budget exhaustion.

Exit: exact replay and zero critical canon violations across the exhaustive bounded state space;
session isolation/load tests meet declared limits.

### Stage 3 — Pre-rendered branching prototype

- Use approved existing clips and deterministic transition selection.
- Add persistent event store, event subscription, media resources, telemetry, auth, and retention.
- Test the complete 10–12 minute anchor with four decision windows and disclosed fallbacks.

Exit: playback and consequence SLOs pass at target concurrency without generative providers.
This isolates whether the experience itself produces meaningful agency.

### Stage 4 — Generated dialogue/transition lane

- Enable generation only for a narrow segment class with authored fallbacks already buffered.
- Introduce horizon scheduling, durable outbox, fences, deadline-aware validation, cancellation
  reconciliation, and per-session budgets.
- Run live-provider experiments with retained latency, cost, validation, and media receipts.

Exit: predeclared live technical gates pass and independent raters find material agency without
excess canon/identity failures. Otherwise return to Stage 3 or stop.

### Stage 5 — Optional engine-rendered or rolling-video research

- Treat game-engine rendering and rolling audiovisual generation as separate experiments.
- Do not generalize results between them. Preserve the same bundle/session/event contracts where
  they actually fit.
- Require fresh economics, safety, accessibility, and distribution validation.

The existing linear film product remains compatible throughout because interactive publication
is additive, sessions pin immutable inputs, and no viewer event changes approved project state.

## Risk register and required validation

| Risk | Current repository signal | Prototype control | Evidence required before claiming solved |
|---|---|---|---|
| Viewer choice corrupts canon | Constitution and continuity schemas exist; no interactive reducer. | Immutable bundle, typed effects, CAS state fold, canon validator. | Exhaustive bounded paths plus adversarial natural-language trials; zero critical violations. |
| “Agency” is cosmetic | Current story is linear. | Require causal state effect and consequence within two segments. | Blinded rater study with predeclared material-agency rubric and simpler branching control. |
| Playback stalls | No playback runtime. | Buffered authored fallback and horizon readiness gate. | p50/p95 consequence latency and stalls under declared concurrency/cache/region. |
| Duplicate or stale decisions | Existing job de-duplication is shot-based and non-transactional. | Idempotency, expected version, event uniqueness, horizon fences. | Parallel/reordered/replayed request tests and crash recovery with no double commit. |
| Provider waste explodes cost | Batch estimates omit speculative/cancelled work. | Session reservation, job attribution, stale cancellation, cache, cost kill switch. | Actual invoices/receipts and sensitivity model per delivered viewer-minute. |
| Unsafe prompt escape | No public-input trust boundary. | Bounded intent vocabulary, separate mapper, policy gate, sandbox, no raw prompt forwarding. | Red-team corpus, moderation evaluation, audit of rejected/accepted false results. |
| Identity/continuity drift | Rule validator checks structured adjacent fields, not delivered media quality. | Multimodal segment validation plus immutable reference anchors and fallback. | Independent delivered-media scoring across branches and minutes, including false-negative audit. |
| Missing or timed-out validation passes | LLM failure may fall back to rules; empty continuity input scores 100. | Completeness gate, evidence-required status, deadline/fallback semantics. | Fault injection for missing media, validator outage, malformed result, and timeout. |
| Cross-session data leak | Runtime has global active project and no user auth. | Authenticated per-session authorization and storage partitions. | Tenant-isolation tests, access-control review, log/privacy inspection, penetration test before public access. |
| Session replay is nondeterministic | Artifact refs exist; no session manifest/hashes. | Event hash chain and exact immutable segment byte refs. | Destroy worker state, restore from store, reproduce exact ordered bytes and decision explanations. |
| Branch storage amplification | Git branches and filesystem artifacts are high overhead per viewer. | Event overlays, content-addressed shared media, retention tiers. | Storage/egress measurements for 10–12 and 30–45 minute variants at realistic choice distribution. |
| Revoked rights remain deliverable | Existing asset lineage does not define active session revocation. | Rights manifest, revocation index, signed short-lived access, terminate/replace policy. | End-to-end revocation drill with affected-session report and no new delivery. |
| Existing pipeline regresses | Temptation to alter the phase graph and core state. | Additive bundle/session package and characterization tests. | Current full CI/E2E/product gate plus new compatibility tests on every migration stage. |

## Validation required by layer

### Prove with deterministic tests

- schema rejection and migration;
- story graph reachability, ending and fallback coverage;
- pure world-state reducer invariants;
- intervention idempotency, duplicates, conflicts, reorder, and replay;
- session fork semantics and manifest hash verification;
- outbox leases, crash recovery, late-result fencing, and cancellation reconciliation;
- budget reservation and attribution;
- policy fail-closed behavior; and
- exact isolation between interactive state and existing project state.

### Prove with integration and load tests

- persistent MCP transport acknowledgement percentiles;
- event cursor reconnect and backpressure;
- transactional store contention and multi-worker ordering;
- media resource authorization and range delivery;
- scheduler readiness, fallback, and recovery at target concurrency;
- telemetry correlation without raw personal text; and
- storage/egress/retention at 10–12 and 30–45 minute scales.

### Prove only with live providers and retained receipts

- submit/poll/cancel latency and cancellation effectiveness;
- output readiness distributions by quality/cache/region/concurrency;
- actual variable cost including failures and discarded speculative jobs;
- delivered-media identity, prompt adherence, safety, and continuity;
- quota/outage failover without playback corruption; and
- exact recovery after an ambiguous provider failure.

### Prove only with creators and viewers

- material agency versus simpler authored branching;
- narrative coherence, pacing, surprise, and ending satisfaction;
- creator ability to express invariants and understand reachable outcomes;
- whether fallback disclosure preserves trust;
- accessibility of decision windows, captions, audio description, and input repair; and
- whether the experience feels like cinema, a game, or a novelty—and whether that distinction
  matters to the intended audience.

## Validation performed

Focused command executed on 2026-08-25:

```bash
UV_CACHE_DIR=.uv-cache uv run pytest --no-cov -q \
  tests/unit/graph/test_graph.py \
  tests/unit/graph/test_real_human_gates.py \
  tests/unit/test_artifacts.py \
  tests/unit/checkpoints/test_checkpoints.py \
  tests/unit/validation/test_impl_validators.py \
  tests/unit/generation/test_executor.py \
  tests/integration/test_generation_mcp.py \
  tests/e2e/test_scenario_05_network_error.py \
  tests/e2e/test_scenario_06_continuity_drift.py
```

Result: all 159 selected tests passed. An initial identical run without `--no-cov` also passed
all selected tests but exited nonzero because the repository applies the 90% whole-project
coverage threshold to a focused subset; reported subset coverage was 28.58%. The clean rerun
disabled coverage only to obtain an unambiguous behavior-test exit status.

Not executed: full unit suite, full integration suite, full E2E suite, `make ci-check`, live
provider tests, TUI/browser playback, load/concurrency tests, security tests, or any audiovisual
interactive session. Historical scorecard claims were read but are not treated as current
execution evidence.

## Recommendation from the repository lens

The repository supports **research direction** and can support a **bounded prototype** only if
the experiment starts with the additive experience-compiler/session seam above. It does not
support a near-term product claim.

The first implementation should be the deterministic text/story simulator, followed by a
pre-rendered branching anchor. Do not begin with live rolling video. That sequence tests the
distinctive thesis—meaningful viewer agency inside creator-governed cinema—before provider
latency and cost obscure whether the product idea works at all.

Repository-specific stop conditions are:

- the session runtime cannot remain isolated from `StudioGraphState` and current phase behavior;
- MCP acknowledgement cannot meet the declared target under representative load and no
  compliant transport solution is available;
- exact event/segment replay fails after one corrective iteration;
- bounded intent and canon enforcement cannot fail closed without making choices meaningless;
- the pre-rendered anchor cannot meet playback/fallback SLOs; or
- current validated-clips tests regress because of interactive changes.

Passing static schemas, mocks, or the focused tests above would establish plumbing only. The
decision to proceed beyond a bounded prototype requires live technical receipts and independent
creator/viewer evidence.
