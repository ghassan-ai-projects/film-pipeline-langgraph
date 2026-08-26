# Narrative and Creator Systems

## Design principle

The system should generate **inside an authored possibility space**, not generate the
possibility space while the viewer waits. The creator defines what the story can mean. The
runtime decides how an accepted intervention travels through that space and how to perform
the next segment.

This separation is the core safeguard for dramatic quality and creator sovereignty.

## Four-layer narrative model

### 1. Immutable constitution

The constitution is valid for every branch:

- theme and emotional promise;
- world rules and historical facts;
- character identities, core motivations, and prohibited transformations;
- visual, camera, voice, music, and performance rules;
- rating, safety, rights, territory, and accessibility constraints;
- dramatic obligations that every valid ending must resolve;
- creator-declared exclusions.

An intervention that conflicts with this layer is repaired or declined. No model may silently
rewrite it.

### 2. Branch state

Branch state records mutable truth:

- events that occurred and their causal parents;
- what each character knows, believes, wants, and conceals;
- relationships, trust, injuries, possessions, location, and time;
- promises, planted facts, open questions, and deadlines;
- chosen direction and its committed consequence;
- candidate ending classes still reachable;
- safety and rights decisions;
- delivered artifact lineage.

This state is typed and transactional. A scene is not committed because a model produced
plausible prose; it commits only when its state transition validates.

### 3. Dramatic plan

The dramatic plan looks further ahead than the media buffer. It contains:

- current dramatic question;
- tension and emotional trajectory;
- next required reveal, reversal, escalation, or payoff;
- character-specific action intentions;
- admissible convergence points;
- ending viability and distance;
- recovery paths if a candidate branch fails.

The plan is revised after a committed intervention, but it cannot erase prior obligations.

### 4. Playable segment plan

This is the short-horizon performance contract:

- scene objective and causal change;
- beats, dialogue intent, blocking, shot plan, and duration;
- continuity anchors and reference assets;
- caption, audio-description, and localization tracks;
- generation route, validation deadline, fallback, and cost cap.

The separation between dramatic plan and segment plan prevents a low-level media model from
becoming the story authority.

## Agency taxonomy

Every intervention and consequence should be labeled before evaluation.

| Agency class | What changes | Example | Counts as material agency? |
|---|---|---|---|
| Cosmetic | Presentation only | Wardrobe accent, camera emphasis | No |
| Expressive | How the viewer's intent is voiced | Gentle versus confrontational phrasing | Not alone |
| Tactical | Immediate method | Distract a guard versus bargain | Sometimes |
| Relational | Trust, loyalty, disclosure, conflict | Confide in one character | Yes |
| Epistemic | What becomes known or believed | Reveal the letter now | Yes |
| Structural | Reachable scenes or ending class | Save the witness, closing one ending | Yes |
| Constitutional | Theme, core identity, safety, world law | Turn the protagonist into a different person | Never viewer-mutable |

A natural-language direction can map to more than one class, but the runtime must expose what
it accepted. “Make it darker” might alter performance tone; it does not authorize violence or
rewrite the rating.

## Narrative structures to compare

### Branch tree

Easy to inspect and pre-render; growth is exponential without convergence. Use only for small
controls and ending paths.

### Foldback graph

Branches reconverge at authored bottlenecks while carrying state forward. Good fit for the
anchor if convergence preserves meaning rather than resetting it.

### Storylets / quality-gated beats

Small authored units become eligible when state preconditions hold. This supports recombination
and drama management but shifts work into precise preconditions, effects, and coverage.

### Planner-led story

A planner chooses actions that satisfy dramatic obligations. It offers flexibility but needs
strict causal state, bounded action schemas, and a validator independent of the planner.

### Character simulation

Characters act from goals and beliefs. It can create surprise, but emergent behavior does not
guarantee escalation, climax, pacing, or a satisfying ending.

### Recommended hybrid

Use authored ending classes and major obligations; state-gated storylets for dramatic beats;
bounded character proposals for local behavior; and a drama manager that selects among valid
candidates. Generation realizes the selected beat. It does not decide whether the beat is
dramatically admissible.

## Setup, payoff, and ending integrity

Every planted fact has:

- a source and delivered segment;
- viewers and characters who know it;
- valid interpretations;
- required or optional payoff;
- latest acceptable payoff horizon;
- ending classes it enables or blocks.

Every branch evaluation checks:

1. Were prior facts preserved?
2. Did the intervention have a causal effect?
3. Did the scene advance or intentionally delay a dramatic obligation?
4. Is at least one creator-approved ending still reachable?
5. Did pacing gain a new beat rather than merely add content?

“Endless middle” is a specific failure state: the branch remains locally plausible but stops
closing obligations or moving toward an ending. The drama manager must detect and force an
escalation, convergence, or safe ending path.

## Creator workflow

### 1. Author

The creator supplies the constitution, state schema, cast and environment bibles, ending
classes, obligations, mutable surfaces, storylets, fallback scenes, and evaluation rubrics.
AI assistance may propose material, but provenance and approval remain explicit.

### 2. Compile

The system converts authoring artifacts into a machine-checkable story package:

- invariant rules;
- action/intent vocabulary;
- state preconditions and effects;
- reachability graph;
- generation/reference packets;
- validation policies;
- rights and territory policies;
- safe fallback inventory.

Compilation should find unreachable endings, orphaned obligations, impossible preconditions,
unsafe combinations, missing access tracks, and unbounded branch surfaces before publication.

### 3. Simulate

Run many cheap story-state trajectories before generating media. The creator sees:

- branch coverage and convergence;
- canonical contradictions;
- ending distribution;
- consequence distance;
- intervention rejection and fallback rates;
- repeated beats and character flattening;
- estimated media cost;
- paths requiring human review.

### 4. Preview and approve

Creators preview representative branches, risky joins, all ending classes, fallbacks, and
accessibility/localization tracks. Approval applies to a versioned story package and provider
policy, not forever to any output a future model might generate.

### 5. Publish and operate

Publication freezes a compatible runtime contract. Updating a constitution, provider, model,
or reference asset creates a new release. Existing session manifests retain their original
version metadata.

### 6. Observe and repair

The creator receives aggregated, privacy-minimized evidence:

- where viewers intervene;
- accepted/repaired/declined intent distribution;
- branches with low narrative scores or high fallback;
- continuity, safety, and access-track defects;
- ending distribution and abandoned sessions;
- generation and review cost.

The tool must not turn these signals into an automatic engagement optimizer that erodes the
creator's theme or encourages compulsive use.

## Required creator tools

- constitution and permission editor;
- intent/action vocabulary editor;
- story-state and obligation inspector;
- branch graph plus state-diff view;
- causal trace from intervention to consequence;
- ending reachability and coverage report;
- character knowledge/belief timeline;
- generated media and provenance review;
- safety, rights, and accessibility policy preview;
- cost and fallback simulator;
- version comparison, rollback, asset revocation, and takedown;
- representative-path sampling rather than impossible exhaustive review.

The existing film pipeline already has useful concepts—typed artifacts, bibles, validation,
review packages, approvals, and checkpoints—but an interactive creator tool also needs
simulation and coverage. More generation without branch observability would increase risk and
manual work.

## Branch amplification and review burden

With `d` decision points and `b` choices per point, a naive tree has `b^d` leaves. Four binary
decisions are manageable at 16 paths; twelve produce 4,096. Natural-language inputs make the
surface effectively open even if the internal intent vocabulary is finite.

The design controls growth through:

- a bounded semantic intent vocabulary;
- state-equivalent path merging;
- foldback points;
- reusable storylets and shots;
- separation of expressive variation from causal state;
- representative and risk-weighted path sampling;
- cached fallbacks;
- expiration and garbage collection for unused candidates.

It must still report the real amplification. Deduplication is not permission to hide how many
state combinations, media variants, and policy paths require assurance.

## Creative evaluation rubric

Use blinded human reviewers, including at least one interactive-narrative practitioner and one
film/story practitioner. Score each complete branch, not isolated clips.

| Dimension | Core question | Critical failure |
|---|---|---|
| Causal agency | Can the reviewer trace a material consequence to the intervention? | Choice is ignored or contradicted |
| Character truth | Do actions follow established desire, knowledge, and relationship state? | Character changes only to satisfy the branch |
| Setup/payoff | Are planted facts remembered and resolved intentionally? | Required payoff disappears |
| Escalation | Does each segment change pressure or understanding? | Repetition or endless middle |
| Pacing | Do interaction windows and generated material preserve dramatic rhythm? | Waiting or choice UI destroys tension |
| Tone and theme | Does variation remain recognizably the same work? | Branch becomes a different genre/value system |
| Ending | Does the conclusion resolve the branch's obligations and choices? | Abrupt or interchangeable ending |
| Audiovisual continuity | Do identity, place, props, voice, camera, and sound remain intentional? | Unmotivated drift breaks comprehension |
| Viewer labor | Is input expressive without becoming constant editing work? | Viewer must rescue or rewrite the system |

Model-based checks may screen for structural defects. They cannot establish that a performance
is moving, funny, frightening, or worth watching.

## Creator sovereignty requirements

- Creator invariants override viewer direction and provider improvisation.
- The creator can see and limit every mutable surface.
- Rights and safety rules are immutable inside a published version.
- Generated assets remain traceable to inputs, model, policy, and approval.
- A creator can revoke future use of an asset and initiate takedown without rewriting audit
  history.
- The system reveals generated versus authored material.
- Viewer contributions do not silently become training or globally reusable story material.
- Compensation, residuals, and ownership are contract questions recorded per production, not
  inferred by the software.

## Hard creative stop conditions

Stop the prototype or fall back to simpler branching if:

- reviewers cannot reliably distinguish causal from cosmetic consequences;
- the corrective loop reduces critical canon violations only by refusing most valid input;
- ending quality drops materially below the pre-rendered control;
- creators cannot understand why a branch occurred;
- representative coverage requires near-exhaustive manual review;
- the only way to maintain continuity is to remove the promised agency;
- the interaction windows create more cognitive work than dramatic value.
