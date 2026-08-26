# Interactive Generative Cinema — Decision-Grade Research Plan

Status: expanded after adversarial plan review; ready for research

## Research question

Can the existing LangGraph Film Studio evolve into a system that starts from a governed
story world and generates a coherent film progressively, while a viewer changes its course,
without sacrificing narrative quality, identity and world continuity, safety, cost control,
creator intent, accessibility, or the ability to reproduce and audit each viewer's version?

## Decision this research must support

Choose one of four positions:

1. **Reject** the concept as technically, creatively, legally, or economically premature.
2. **Research direction only**: retain it as a long-range direction with named evidence gaps.
3. **Bounded prototype**: authorize a time-boxed experiment alongside the current pipeline.
4. **Near-term product direction**: fund productization after live technical and user evidence.

The recommendation must name the evidence required to move to the next position. It must
not confuse a compelling demo with a production-capable product.

Desk research plus a read-only repository audit may recommend at most position 3, and only
as a bounded experiment with a budget, stop date, and falsifiable gates. It cannot recommend
position 4. If the non-compensable pre-prototype gates in this plan are not met, the maximum
recommendation is position 2.

The present research does **not** choose an owner, staff-hour ceiling, cash/local-compute cap,
or stop date on the user's behalf. Until those are explicitly fixed, the honest decision is
position 2 with a conditional path to position 3. A position-3 authorization must name:

- creative, engineering, and measurement owners;
- the one title/fixture and exact repository write boundary;
- maximum elapsed days and staff-hours;
- external-provider/data/participant limits and local-compute/cash ceilings;
- required evidence deliverables and exit report;
- stop date and the non-compensable failure rules below.

## Working definition

"Interactive generative cinema" means a viewer experiences a time-based audiovisual story
whose future scenes can change in response to explicit choices, natural-language direction,
or observed interaction. The system preserves a stable authored world, generates or selects
the next playable segment within a latency budget, and records the resulting branch as a
replayable, inspectable version.

This is not assumed to mean unconstrained, frame-by-frame video generation. The research
must compare at least these execution models:

- pre-rendered branching;
- authored scene graph with generated transitions;
- rolling-horizon generation from a bounded story graph;
- fully generative real-time world simulation;
- game-engine rendering with generative narrative, dialogue, or cinematography;
- hybrid local and cloud generation with prefetching.

The research must keep these categories separate: interactive film, personalization,
branching narrative, generative audiovisual media, live world simulation, and an editing
tool. Crossing a category boundary is a product decision, not a terminology shortcut.

## Anchor scenario

All candidate architectures and estimates must first be evaluated against the same anchor,
so the conclusion is not assembled from incompatible demos.

### Baseline experience

- A single viewer watches a 10–12 minute stylized dramatic mystery.
- The story has three fictional adult characters, two connected locations, an authored
  premise, world rules, character constitutions, dramatic obligations, and three valid
  ending classes.
- The viewer may intervene at four authored decision windows, roughly every 90–150 seconds.
- An intervention may be a bounded choice or one sentence of natural-language direction.
  Natural language is mapped to a governed intent vocabulary; it is not an unrestricted
  prompt passed directly to media generation.
- An intervention must produce a materially different consequence within the next two
  playable segments while preserving prior facts and the creative constitution.
- The system may prefetch, reuse authored assets, generate transitions, or degrade to a safe
  branch. Playback should not depend on generating every frame after the intervention.
- The completed session is represented by a versioned manifest containing inputs,
  decisions, state transitions, policy decisions, artifact identifiers, model/provider
  metadata, and hashes sufficient to inspect and replay the delivered version.

This anchor intentionally tests the product claim—meaningful viewer direction inside a
coherent film—without making photorealistic live video the entry requirement.

### Required variants

The research must state how conclusions change for:

1. discrete choices with mostly pre-rendered branches;
2. bounded natural-language direction with generated dialogue or transitions;
3. game-engine rendering with generated narrative and performance control;
4. rolling audiovisual generation with a precomputed horizon;
5. a 30–45 minute episode with more branches and persistent viewer history.

Each variant must reuse the anchor's characters, world, and evaluation rubric where
possible. Capability evidence from one variant may not be silently generalized to another.

### Anchor exclusions

The initial recommendation must not depend on multiplayer, open worlds, passive biometric
or emotion inference, minors, real-person likenesses, user-uploaded copyrighted characters,
public user-generated publishing, unrestricted sexual or violent content, feature-length
runtime, photorealism, or synchronous generation of every final frame. These are later risk
extensions, not hidden assumptions in the baseline.

## Operational definitions and candidate SLO vocabulary

The research must use the following terms consistently. Values below are prototype target
hypotheses to test, not claims about current provider capability.

| Term | Operational meaning | Anchor measurement or target hypothesis |
|---|---|---|
| Playable segment | Continuous audiovisual unit with an immutable delivered manifest | 20–60 seconds |
| Decision window | Point where the viewer can influence unresolved future events | Four per anchor session |
| Interaction acknowledgement | Client confirms that an input was accepted, rejected, or needs repair | p95 at or below 500 ms |
| Consequence latency | Time from accepted input to the start of the first materially responsive segment | p50 at or below 10 s; p95 at or below 30 s |
| Narrative response distance | Number of segments before a material consequence is visible | No more than two |
| Playback stall | Unplanned interval with no playable story or intentional interaction UI | p95 below 1 s; no single stall above 3 s |
| Safe fallback rate | Accepted interactions resolved through a disclosed authored or cached fallback | Reported separately; target ceiling to be derived |
| Intervention acceptance rate | Valid in-scope interventions that affect story state rather than being ignored | Target to be derived and tested |
| Material agency | Independent raters can identify a causal story consequence attributable to the choice | Rubric and threshold defined before study |
| Canon violation | Delivered content contradicts an immutable world, character, safety, or prior-event fact | Zero critical violations; rate for lesser violations reported |
| Identity continuity failure | Character appearance, voice, role, motivation, or relationship changes without story cause | Severity-weighted rate per delivered minute |
| Replay fidelity | Ability to redeliver the exact delivered artifact sequence from its manifest | 100% for retained artifacts; regeneration is a separate metric |
| Recovery time | Time to resume a session after worker/provider failure without losing committed choices | p95 target to be derived |
| Cost per delivered viewer-minute | All variable generation, validation, moderation, storage, and egress cost divided by playable minutes | Range with cache and retry sensitivity |
| Branch amplification | New stored/generated artifacts per accepted intervention relative to a linear run | Measured by execution model |

Every reported latency or reliability result must name percentile, observation window,
sample size, region, cache state, concurrency, media quality, and fallback behavior. Average
latency alone is insufficient. “Real time,” “coherent,” “consistent,” “replayable,” and
“personalized” may not appear as unqualified capability claims.

## Quality bar

The final package is satisfactory only if it:

- separates current facts, source-backed inferences, hypotheses, and proposals;
- uses current primary sources for technical capabilities and authoritative sources for
  legal or policy claims;
- studies both adjacent products and failed or limiting approaches, not only promotional
  examples;
- distinguishes interactivity, personalization, branching narrative, generative video,
  world models, and game-engine simulation;
- quantifies latency, throughput, storage, and cost with explicit assumptions and ranges;
- treats narrative coherence, character identity, audiovisual continuity, moderation,
  provenance, rights, privacy, security, accessibility, and abuse resistance as first-class
  system requirements;
- evaluates creator control, tooling, and authorship, not only viewer freedom;
- maps the idea to the repository's actual MCP, LangGraph, artifact, checkpoint, validation,
  provider, approval, and test contracts;
- distinguishes documented architecture, implemented behavior, tested behavior, live proof,
  and missing capability;
- proposes a narrow, falsifiable prototype before any platform rewrite;
- identifies what can be proven with mocks, what needs live providers, and what requires
  creator or viewer studies;
- ends with a clear recommendation, staged roadmap, kill criteria, unknowns, and evidence
  gaps;
- receives explicit product, narrative/creative, creator-workflow, architecture,
  operations/economics, safety/rights, security/privacy, accessibility/localization, and
  measurement reviews, with corrections incorporated or disagreements recorded.

## Claims and evidence protocol

### Claim classes

Every material statement in the final package must be identifiable as one of:

- **Fact** — directly supported by cited evidence in the stated scope and date.
- **Inference** — a reasoned conclusion from named facts, with the reasoning exposed.
- **Hypothesis** — falsifiable but not yet demonstrated.
- **Proposal** — a recommended design or action, not evidence that it works.

### Evidence hierarchy

1. Repository code, tests, executed commands, and retained receipts for current-project facts.
2. Primary technical sources, papers, standards, product documentation, and measured demos.
3. Authoritative regulators, statutes, court material, and recognized standards bodies for
   legal or governance claims.
4. Independent evaluations, credible reporting, and direct creator/user evidence.
5. Vendor marketing, commentary, or unsourced demonstrations only as leads—not as sole
   support for a decision-critical claim.

Provider capability, price, quota, and policy claims must carry an access date and scope.
Decision-critical claims should be triangulated with at least two independent evidence
types; exceptions require an explicit evidence-gap label. Legal issues must be framed for
qualified review, not presented as legal conclusions.

### Claim ledger

Maintain a ledger with: claim ID, exact claim, class, decision/workstream, scope and as-of
date, source or repository evidence, confidence, counterevidence, assumptions, validation
needed, and disposition. Quantitative models must expose formulas, units, ranges, cache and
retry assumptions, and sensitivity cases. Unsupported precision is prohibited.

For market precedents, record what was actually shipped, what was a research demo, whether
interaction was live or pre-authored, observable adoption evidence, and shutdown or failure
evidence. Absence of public evidence must remain “unknown,” not become a negative fact.

## Hard decision rubric

### Evidence scores

Score each decision dimension from 0 to 3:

- **0 — contradicted or unknown:** no usable evidence, or evidence fails the requirement;
- **1 — plausible:** source-backed rationale or mock proof only;
- **2 — bounded evidence:** measured proof in a representative prototype or credible
  equivalent, with important limits;
- **3 — product evidence:** repeatable live results at target quality, load, cost, and user
  conditions, with operational receipts.

Required dimensions are: viewer value and agency; narrative quality; creator value and
control; audiovisual continuity; latency and fallback; safety and rights; security and
privacy; accessibility and localization; replay/auditability; technical integration;
reliability/operations; and unit economics/distribution.

Scores cannot be averaged to hide a zero. The final memo must show evidence, score,
confidence, owner, and next experiment for every dimension.

### Position thresholds

- **Position 1:** one or more kill criteria is evidenced and has no credible bounded
  mitigation, or the concept adds no distinctive value over simpler branching media.
- **Position 2:** the thesis remains plausible, but any pre-prototype gate is below 1 or the
  repository/market evidence cannot justify a bounded experiment.
- **Position 3:** every pre-prototype gate is at least 1, no kill criterion is active, the
  anchor has a falsifiable experiment design, and budget/external-mutation limits are fixed.
- **Position 4:** every dimension is at least 2 and the non-compensable product dimensions
  named below are 3, based on live provider, prototype, creator, viewer, safety, and load
  evidence. Desk research cannot reach this threshold.

### Non-compensable gates and kill criteria

For position 3, there must be a credible, testable path for all of the following. For
position 4, each must be directly demonstrated:

1. **Meaningful agency:** interventions produce understandable, causal changes without
   reducing the experience to arbitrary prompt output.
2. **Narrative integrity:** the story constitution and prior committed facts survive accepted
   interventions at the agreed critical-violation threshold.
3. **Playable delivery:** consequence latency, stalls, and fallback are compatible with the
   intended experience; hidden waiting is not counted as success.
4. **Governed control:** disallowed input and output can fail closed without corrupting or
   silently advancing the story.
5. **Rights-safe inputs:** the anchor can be built with documented authority over character,
   voice, music, environment, and training/reference inputs used by the project.
6. **Replay and audit:** every delivered version and policy/state transition is attributable
   and inspectable; exact artifact replay does not depend on nondeterministic regeneration.
7. **Bounded economics:** cost, concurrency, quota, fallback, storage, and egress have an
   explicit viable envelope rather than an unbounded subsidy assumption.
8. **Creator sovereignty:** authors can define invariants, inspect branches, revoke assets,
   and understand what viewers are permitted to change.
9. **Repository isolation:** the experiment can be added without destabilizing the existing
   linear film pipeline or bypassing its MCP-first and approval contracts.
10. **Privacy and security:** the baseline does not require covert profiling, persistent raw
    prompts, or unbounded tool/media access, and has a credible abuse boundary.

Any of these is a kill criterion for the proposed architecture if a representative test
fails twice after one predeclared corrective iteration, or if the only mitigation negates
the core user value. The concept itself should be rejected only when all materially simpler
execution models also fail; otherwise reject the architecture and retain the narrower one.

## Research workstreams

Each workstream must produce claims for the ledger, explicit unknowns, and a recommendation
impact. Workstreams may share evidence but not silently share conclusions.

### 1. Product thesis and experience boundary

- Define viewer, creator, rights-holder, and operator jobs to be done.
- Compare interaction grammars: discrete choice, direction, intent, role-play, and passive
  adaptation.
- Determine when interaction improves cinema and when it becomes a game, toy, or editing
  tool.
- Define authorship boundaries and the minimum stable creative constitution.
- Define session, replay, share, fork, canon, ending, ownership, and multiplayer semantics.
- Compare the concept against simpler substitutes and define its distinctive value.

### 2. Narrative systems and creative quality

- Specify story-world, immutable canon, mutable state, character constitution, dramatic
  obligations, planted/payoff facts, pacing, tone, and ending constraints.
- Compare authored graphs, drama managers, hierarchical planners, agent improvisation, and
  hybrid approaches.
- Define the separation between long-horizon arc planning and segment-level performance.
- Study causal memory, contradiction detection, branch convergence, recovery, and intentional
  discontinuity.
- Define “material agency,” “coherence,” “good ending,” and creative failure with creator and
  viewer rubrics rather than model self-evaluation alone.
- Test the risk of false choice, endless middles, tonal drift, character flattening, and
  optimization for engagement over authored meaning.

### 3. Creator tooling and production workflow

- Map how a creator defines the world bible, permissions, mutable surfaces, prohibited arcs,
  performance references, fallback branches, and acceptance criteria.
- Specify preview, branch simulation, diff, annotation, approval, provenance, asset revocation,
  rollback, and publication workflows.
- Quantify authoring burden and branch-review amplification.
- Define collaboration, versioning, credits, residual/revenue, and audit needs without
  presuming a specific labor or rights conclusion.
- Determine the minimum tooling needed for the anchor; do not hide manual operator labor.

### 4. Market, precedent, and failure landscape

- Interactive film and branching-story precedents.
- AI-native entertainment and generative media products.
- AI non-player characters, narrative directors, and game-engine approaches.
- Generative video, audio, speech, character, and world-model capabilities.
- Research systems for interactive or long-form coherent generation.
- Evidence of demand, retention, creator adoption, business models, shutdowns, and failure
  modes.
- Comparability table against the anchor, including what each precedent does not prove.

### 5. Feasibility and systems model

- End-to-end latency budget and rolling-horizon scheduling.
- Story planning versus moment-to-moment rendering.
- Branch state, world state, memory, causal consistency, and deterministic state replay.
- Character, environment, camera, voice, music, and prop continuity.
- Generation, validation, fallback, prefetch, caching, and graceful degradation.
- Provider portability, observability, idempotency, recovery, and cost controls.
- Storage growth, branch deduplication, cancellation, and garbage collection.
- Separate control-plane, story-state, media-generation, validation, and delivery paths.

### 6. Distribution, client, and operations

- Client interaction, buffering, adaptive delivery, session handoff, reconnect, and version
  compatibility.
- CDN/cache implications of per-viewer branches and access-controlled assets.
- Concurrency, queueing, regional availability, provider quota, rate limits, and load shedding.
- Cross-device and low-bandwidth degradation, captions/audio-description synchronization,
  telemetry, support, incident response, deletion, and retention.
- Export, sharing, fork permissions, content disclosure, and platform/store constraints.
- Define what runs at edge, client, project infrastructure, and provider, with trust boundaries.

### 7. Economics and business constraints

- Compute cost per delivered viewer-minute across candidate architectures.
- Include generation, validation, moderation, retries, cache misses, storage, egress, support,
  creator labor, and waste from abandoned/prefetched branches.
- Model low/base/high cases for concurrency, branch reuse, quality, and provider pricing.
- Compare subscription, ticket, session, creator-license, and sponsored economics without
  treating speculative demand as revenue evidence.
- Establish the maximum affordable prototype and product envelopes before recommending them.

### 8. Safety, rights, and governance

- Input, output, likeness, copyright, music, voice, trademark, and training/reference rights.
- Minor safety, sexual and violent content, self-harm, persuasion, harassment, political
  manipulation, parasocial design, and compulsive engagement risks.
- Moderation latency, policy enforcement, appeal, creator escalation, and safe branch repair.
- Provenance, watermarking, disclosure, consent, territory, revocation, and export controls.
- Jurisdiction-sensitive obligations, clearly labeled as issues for qualified legal review.
- Threat model creator/viewer conflict: viewer freedom cannot silently override creator or
  rights-holder constraints.

### 9. Security and privacy

- Data-flow and trust-boundary diagram for prompts, profiles, story state, media, telemetry,
  provider calls, and shared versions.
- Prompt injection, tool abuse, artifact poisoning, cross-session leakage, unauthorized
  branch access, model/provider compromise, denial-of-wallet, and provenance tampering.
- Data minimization, purpose limitation, consent, retention/deletion, regional handling, and
  controls for inferred preferences.
- Separate explicit personalization from passive behavioral or biometric adaptation.
- Define tenant/session isolation, authorization, signed manifests, audit-log integrity,
  secrets boundaries, rate limits, and abuse response requirements.

### 10. Accessibility and localization

- Captions, subtitles, audio description, dialogue clarity, photosensitivity, motion,
  cognitive load, input alternatives, time limits, and screen-reader interaction.
- Maintain synchronized accessibility tracks when branches change at runtime.
- Study localization of dialogue, performance, lip movement, signs, culture, safety policy,
  and authored meaning; translation is not presumed sufficient.
- Define locale-specific fallback and quality review, and prevent unsupported languages from
  silently receiving degraded or unsafe behavior.
- Include disabled users and multilingual creators/viewers in later evaluation design.

### 11. Repository adaptation and current capability evidence matrix

- Audit current capability and readiness without modifying production code.
- Map reusable contracts and architectural mismatches.
- Propose a domain model and boundaries, MCP tool and LangGraph changes, and artifact,
  branch/checkpoint, validation, review, and provider changes.
- Preserve the current linear pipeline and mandatory human gates.
- Identify the smallest isolated experiment seam; do not propose a platform rewrite first.

The repository report must include a current capability evidence matrix with these columns:

| Need | Required behavior | Documentation evidence | Code/symbol evidence | Test/command evidence | Maturity | Reuse or gap | Validation needed |
|---|---|---|---|---|---|---|---|

Allowed maturity values are: **documented only**, **implemented but untested**, **unit-tested**,
**integration-tested**, **live-proven**, **partial**, and **missing**. Architecture documents
are intent, not implementation evidence. A test name is not proof until its assertion and
execution status are inspected. The matrix must cover at least MCP boundaries, graph loop,
artifacts and lineage, state/checkpoints, review gates, validators, providers, streaming,
cancellation, concurrency, observability, security, and cost metering.

### 12. Measurement, validation, and roadmap

- Define an experiment ladder from text/story-state simulation to a bounded playable
  audiovisual scene.
- Pre-register success/failure thresholds, fixtures, evaluator independence, sample size
  rationale, and corrective-iteration limit before each experiment.
- Use deterministic structural checks where possible, human creator/viewer judgment where
  meaning is evaluated, and provider receipts where live capability is claimed.
- Separate offline metrics from observed viewer value; model-as-judge scores alone cannot
  establish agency, coherence, accessibility, safety, or demand.
- Include counterfactuals: linear version, pre-rendered branching version, and at least one
  simpler hybrid.
- Measure time-to-first-play, consequence latency, stalls, continuity failures, critical
  canon violations, agency, narrative satisfaction, creator control, authoring effort,
  intervention rejection/fallback, safety outcomes, cost, and recovery.
- Add red-team, failure-injection, load, deletion, replay, localization, and accessibility
  scenarios.
- Produce phase gates, budgets, stop conditions, evidence receipts, and owners.

## Research method and execution order

1. Freeze this expanded plan, rubric, anchor, exclusions, and claims protocol.
2. Inspect current repository contracts, implementation, tests, and architecture sources
   without modifying production code; build the current capability evidence matrix.
3. Search current web sources, prioritizing primary, authoritative, and independently
   measured evidence; build the source registry and claim ledger concurrently.
4. Normalize every precedent and capability claim against the anchor and required variants.
5. Build narrative, creator-workflow, system, security/privacy, distribution, accessibility,
   economic, and measurement models.
6. Synthesize the repository adaptation and a bounded experiment program.
7. Score the hard decision rubric, apply the non-compensable gates, and draft the decision
   memo before writing a roadmap.
8. Run independent review lenses, disposition every finding, and revise the package.
9. Validate internal links, source coverage, claim classes, quantitative assumptions,
   terminology, evidence dates, and completion against the quality bar.

No workstream may upgrade another workstream's unknown into an assumption merely to complete
the recommendation. Conflicts go into the decision memo and review record.

## Planned deliverables

- `README.md` — index and executive decision memo, including rubric scores and recommendation;
- `00-research-plan.md` — plan, quality bar, decision protocol, and plan-review record;
- `01-concept-and-product-thesis.md` — anchor, experience boundary, substitutes, and product
  choices;
- `02-landscape-and-evidence.md` — precedents, competitors, research, failures, and
  anchor-comparability table;
- `03-narrative-and-creator-systems.md` — story control, creative quality, authoring, and
  creator workflow;
- `04-technical-feasibility.md` — candidate architectures, latency, continuity, replay,
  security, and technical limits;
- `05-repository-adaptation.md` — current-state evidence matrix and proposed integration;
- `06-prototype-and-validation-roadmap.md` — experiments, controls, gates, metrics, budgets,
  and kill criteria;
- `07-safety-rights-and-governance.md` — threat model, privacy, rights, moderation, and
  governance requirements;
- `08-economics-distribution-and-operations.md` — unit economics, client/delivery model,
  scaling, and operations;
- `09-accessibility-localization-and-measurement.md` — inclusive experience requirements and
  evaluation design;
- `10-claims-and-evidence-ledger.md` — material claims, classes, confidence, counterevidence,
  and validation gaps;
- `11-review-record.md` — independent findings, dispositions, corrections, and disagreements;
- `sources.md` — source registry with publisher, title, date, access date, source type,
  relevant claims, and limitations.

## Review protocol

Each lens must return blocking findings, important findings, evidence gaps, and a verdict of
**pass**, **pass with recorded risk**, or **revise**. A revise verdict requires correction and
one re-review. Unresolved disagreements remain visible in `11-review-record.md`.

Required lenses are:

- **Product and substitution:** distinctive user value, category boundary, scope, and demand
  evidence.
- **Narrative and creative:** agency, authorship, story quality, character/world integrity,
  and ending behavior.
- **Creator workflow:** controllability, review burden, rights, provenance, and production
  usability.
- **Architecture and repository:** evidence matrix accuracy, system boundaries, state,
  isolation, failure semantics, and migration risk.
- **Reliability, distribution, and economics:** SLO measurability, latency, capacity, fallback,
  cost completeness, and operational viability.
- **Safety, rights, and governance:** abuse cases, consent, provenance, moderation, labor and
  rights questions, and jurisdictional caveats.
- **Security and privacy:** threat model, authorization, isolation, minimization, retention,
  integrity, and denial-of-wallet.
- **Accessibility and localization:** inclusive interaction, synchronized access tracks,
  language/cultural quality, and degradation behavior.
- **Measurement science:** construct validity, baselines, evaluator independence, sample
  rationale, preregistered thresholds, and claim/evidence alignment.
- **Adversarial decision review:** strongest case against the recommendation, simpler viable
  alternative, non-compensable gates, and whether the desk-research ceiling was respected.

## Initial hypotheses to challenge

- A compelling first product is probably not free-form, frame-by-frame generation.
- Rolling-horizon generation can hide some latency, but only inside bounded narrative and
  visual constraints.
- The existing artifact lineage, validation, checkpoints, and human gates are useful, while
  the phase-oriented batch graph is not sufficient for a live session loop.
- The first defensible prototype should prove narrative agency and continuity before it
  proves photorealistic real-time rendering.
- Per-viewer video generation is likely too costly for mass-market synchronous use today;
  a hybrid of authored assets, cached branches, game-engine rendering, and selective
  generation may be more viable.
- Natural-language freedom may increase perceived agency while reducing creator control,
  safety, evaluability, and narrative quality.
- The creator workflow and branch-review burden may be a harder constraint than generation
  capability.

These are hypotheses, not starting conclusions. The final recommendation must report
disconfirming evidence.

## Scope boundaries

This work is research and planning. It will not implement production code, contact vendors,
spend provider credits, conduct a real creator or viewer study, run an unapproved live
provider benchmark, or make legal conclusions. Any capability claim that requires those
actions remains an explicit validation gap.

The work may inspect repository code and execute existing local, non-mutating checks if
needed to establish current capability. It may estimate a prototype but may not call an
estimate a measured result. A prototype recommendation authorizes a separate build decision;
it does not authorize implementation, external publication, data collection, or provider
spend.

## Plan-review record

### Accepted amendments

- Added a fixed anchor scenario, comparable variants, and explicit exclusions to prevent
  incompatible demos from driving one conclusion.
- Added operational definitions and prototype SLO hypotheses for latency, stalls, agency,
  continuity, replay, recovery, cost, and branch growth.
- Added a scored decision rubric, a maximum desk-research recommendation, non-compensable
  gates, architecture-versus-concept kill semantics, and a bounded corrective loop.
- Added a claim taxonomy, evidence hierarchy, claim ledger, triangulation rule, repository
  evidence standard, and quantitative-model requirements.
- Split out previously under-specified narrative systems, creator tooling, distribution,
  accessibility/localization, security/privacy, and measurement workstreams.
- Required a current capability evidence matrix that separates documentation, code, tests,
  execution, and live proof.
- Expanded deliverables and independent review lenses so every added workstream has a durable
  output and adversarial review.

### Deferred from this research phase

- Live provider benchmarks, prototype implementation, paid-provider use, production load
  tests, creator/viewer studies, market sizing, vendor procurement, legal opinions, labor
  agreements, and production launch design.
- Multiplayer, biometric adaptation, real-person likeness, minors, public UGC, open worlds,
  and feature-length generation remain post-anchor risk extensions.
- Final numeric product SLOs, acceptable unit economics, and study thresholds must be derived
  from product context or measured evidence; this plan supplies candidate prototype
  vocabulary and forces those values to be declared before execution.

No accepted gap-review finding was rejected. Suggestions that require evidence collection
are deferred to the research workstreams rather than presumed in the plan.
