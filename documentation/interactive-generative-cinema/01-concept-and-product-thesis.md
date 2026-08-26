# Concept and Product Thesis

## Executive thesis

The idea is worth continuing to research, but the candidate product is narrower than “generate
a movie in real time.” The leading desk-research version is provisionally called **authored
possibility cinema**: creators define a story
world, immutable truths, dramatic obligations, acceptable variation, and ending classes;
the viewer directs unresolved parts of that world; the system commits a governed consequence
and delivers a coherent audiovisual branch.

This preserves what makes a film a film—composition, pacing, performance, theme, and an
ending—while adding causal agency. An unrestricted prompt-to-video stream would maximize
surface freedom but weaken authorship, safety, narrative structure, reproducibility, and the
ability to promise an ending worth reaching.

The near-term opportunity is therefore not a personalized feature film generated frame by
frame. It is a bounded, 10–12 minute, stylized experience with four interventions, a rolling
buffer, authored fallbacks, and a shareable version manifest. That is a falsifiable experiment,
not yet a product claim.

## Root problem

The viewer does not actually want “more generated pixels.” The proposed value is:

> I can make a meaningful choice inside a story I care about, see the world respond without
> breaking its truth, and finish with a version that feels authored for me rather than merely
> assembled around me.

This creates four simultaneous jobs:

| Actor | Job | Failure that destroys value |
|---|---|---|
| Viewer | Influence the story and understand the consequence | False choice, confusing causality, waiting, or incoherence |
| Creator | Bound the possibility space without authoring every path | Loss of voice, branch explosion, unreviewable output, or hidden manual work |
| Rights holder | Control where protected characters, voices, music, and worlds may go | Unauthorized transformation, territory, attribution, or revocation failure |
| Operator | Deliver a safe, reliable session at a predictable cost | Stalls, unsafe branches, provider failure, denial-of-wallet, or irreproducible incidents |

The system succeeds only if all four jobs remain compatible. Optimizing solely for viewer
freedom is not a product strategy.

## The category boundary

Interactive generative cinema sits between several established categories but is not
identical to any of them.

| Category | State authority | Media production | Viewer agency | Primary quality test |
|---|---|---|---|---|
| Linear film | Fixed edit | Fully authored | Interpretive | Is the film good? |
| Branching film | Authored branch graph | Pre-rendered | Discrete, finite | Are choices meaningful and paths polished? |
| Role-playing game | Game simulation | Rendered by engine | Continuous action | Is the system expressive and playable? |
| AI companion / NPC | Agent memory and policy | Dialogue/avatar | Conversational | Is the relationship believable and safe? |
| Generative video tool | Prompt/job | Generated clips | Creator-directed | Is the output useful and controllable? |
| Proposed experience | Governed story state | Hybrid cached/generated segments | Bounded causal direction | Does agency improve a coherent cinematic arc? |

The boundary matters. If interaction becomes continuous locomotion, inventory, combat, and
systemic physics, the product is a game. If the user repeatedly edits shots, it is a creation
tool. If content adapts invisibly to inferred emotions, it is personalization and profiling.
The anchor attempts to stay cinematic by using four authored decision windows and uninterrupted
viewing between them. Whether viewers experience it as watching, directing, playing, or editing
is a study outcome, not something the architecture can declare. Evaluation must measure those
roles, interruption cost, and cinematic absorption explicitly.

## Experience contract

### Viewer role

The anchor viewer is a **guest director of consequence**, not a screenwriter or actor. They
may express intent—trust a suspect, protect a secret, confront a character, change a tactical
priority—but cannot rewrite established history, identity, safety policy, or the film's theme.

This framing provides freedom at the level most viewers can reason about. Asking viewers to
write dialogue, lenses, blocking, and edit rhythm every two minutes would turn cinematic
attention into production labor.

### Interaction grammar

Each decision window offers two layers:

1. two or three creator-approved directions that reveal the meaningful dimensions of choice;
2. an optional one-sentence direction mapped into the same governed intent space.

The system responds immediately with one of four transparent outcomes:

- **accepted** — a consequence contract is committed;
- **repaired** — the direction is narrowed while preserving its intent;
- **declined** — it conflicts with canon, safety, rights, or capability, with a short reason;
- **fallback** — the intent is accepted, but a cached/authored segment is used to preserve
  playback.

Natural language is never a direct media-generation prompt. The mapping layer protects the
creative constitution and makes decisions measurable.

### Consequence contract

Every accepted intervention creates a typed contract before media generation:

- intended causal change;
- affected characters, goals, relationships, and open dramatic obligations;
- facts that become true, false, or remain unresolved;
- latest segment by which the change must be visible;
- allowed tones and visual surfaces;
- safety and rights constraints;
- viable ending classes after the change;
- planned fallback;
- validation criteria.

This contract prevents the common failure where the interface records a choice but the story
quietly ignores it.

### Session and version semantics

- A session owns one ordered event log and one committed story-state lineage.
- Delivered segments are immutable. Future plans may be invalidated, but the past is not
  regenerated.
- A fork starts from a committed decision boundary and creates a new lineage.
- “Replay” means redelivering retained media and decision events, not asking providers to
  reproduce stochastic outputs.
- A shared version exposes only the minimum manifest and media permitted by its owner and
  rights policy.
- “Canon” belongs to the creator-authored world. A viewer branch is personal continuity, not
  automatically new global canon.

## Narrative design position

Meaningful agency is not proportional to the number of branches. A choice is meaningful when
the viewer understands the decision, the world remembers it, and it changes a valued outcome
or relationship. Cosmetic changes can add recognition, but they must not be reported as causal
agency.

The anchor should use a **foldback with stateful consequences**:

- several local paths and performances;
- persistent relationship, knowledge, and obligation state;
- convergence onto a manageable number of high-quality dramatic sequences;
- three authored ending classes with generated or selected variations.

This controls combinatorial growth without erasing consequences. Convergence is acceptable
when the route changes meaning; it is false choice when all routes are interchangeable and
the state is forgotten.

The 2005 *Façade* architecture remains a useful precedent: it combined thousands of authored
joint dialogue behaviors with higher-level story beats and a drama manager rather than asking
one generator to invent plot, character, and performance at once
([Mateas and Stern](https://doi.org/10.1609/aiide.v1i1.18722), accessed 2026-08-25). That is
evidence for hierarchical authoring and drama management, not evidence that modern video
generation can deliver the anchor.

## Why now, and why not yet

Three technology curves are converging:

- language models can plan, classify intent, maintain structured state, and generate bounded
  dialogue;
- video and audio models can create increasingly controllable short segments;
- world models can demonstrate interactive visual environments at real-time frame rates.

However, the curves do not yet combine into a proven cinematic system. Google DeepMind reports
that Genie 3 can run at 24 fps, 720p, with consistency for a few minutes, while also stating
limited action space, difficulty with multiple independent agents, and only a few minutes of
continuous interaction
([Genie 3](https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/), accessed
2026-08-25). A current long-video research survey reports that many state-of-the-art systems
still operate on short clips and struggle with multi-subject identity, scene layout, and motion
coherence beyond those clips
([Elmoghany et al.](https://arxiv.org/abs/2507.07202), accessed 2026-08-25).

Those facts support a hybrid experiment. They do not support unconstrained, multi-character,
feature-length, photorealistic generation.

## Product alternatives

### A. Pre-rendered branching

Highest immediate playback quality and simplest safety review. It is a mandatory control in
the experiment. Its weakness is authoring amplification and limited natural-language reach.

### B. Authored branches plus generated dialogue/transitions

Adds recognizable responsiveness without asking generation to carry whole scenes. This is
the lowest-risk generative audiovisual candidate and should be the first live-media rung.

### C. Rolling-horizon hybrid cinema

Maintains a committed playable buffer, generates candidate future segments, and selects or
falls back before playback. This best represents the product thesis and is the recommended
prototype target after story-state simulation passes.

### D. Game-engine performance with generative drama

Offers predictable rendering latency, explicit world state, and stronger continuity. It may
be the most production-viable architecture, but it shifts cost toward asset creation, rigging,
animation systems, and engine expertise, and may feel more like a narrative game.

### E. Fully neural real-time movie

Most novel and least controllable. Current public demonstrations do not establish complex
multi-character drama, dialogue performance, long-arc causality, moderation, replay, or unit
economics. Keep it as a research watch item, not the prototype dependency.

## Distinctive value test

The concept earns investment only if the hybrid prototype beats conventional branching on
all of these:

- bounded language increases supported-intent coverage, intent match, or perceived personal
  authorship without confusing consequence comprehension;
- narrative satisfaction and ending quality do not materially decline;
- creator effort per accepted possibility does not explode;
- intervention-to-consequence latency preserves viewing flow;
- critical canon and safety violations remain zero;
- cost per successful viewer-minute stays inside a predeclared prototype envelope.

Menu and language inputs can commit the same consequence contract, so language does not
inherently create more causal agency. Test a matched factorial design: menu versus bounded
language, crossed with authored versus generated surface realization, while story topology,
consequences, duration, and production quality stay fixed. Report unique supported intents,
intent-match accuracy, repair friction, consequence comprehension, perceived authorship, and
causal outcome separately. If the hybrid improves novelty but not these outcomes, the simpler
branching form wins.

## Recommendation at the product level

Keep the concept at **Position 2: research direction with a conditional prototype path**. The
package does not fix the owner, staff/time ceiling, budget, or stop date required to authorize
Position 3. Do not reposition the existing film pipeline or begin a platform rewrite. If a
separate bounded charter is approved, first prove causal narrative agency and continuity in
text/storyboard form. Only then consider selective live media.

The strongest initial title is stylized, dialogue-led, small-cast, small-location, and designed
around decisions with delayed dramatic meaning rather than physical spectacle. That choice is
not merely cheaper; it aligns the medium with what the system must prove.
