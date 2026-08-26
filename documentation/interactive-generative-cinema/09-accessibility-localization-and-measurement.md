# Accessibility, Localization, and Measurement

## Principle

Accessibility and localization are part of branch correctness. A generated consequence is not
playable if a viewer cannot perceive the changed dialogue, operate the decision window, or
receive an equivalent meaning in the selected language.

The anchor excludes no viewer by assuming a touchscreen, fast reading, hearing, color vision,
or a fixed response time.

## Accessible interaction contract

Every decision window must support the same semantic intervention through:

- remote, keyboard, pointer, touch, switch, and programmatic controls;
- screen-reader-labeled bounded choices;
- optional voice input with confirmation before commit;
- extended or disabled timers;
- pause-and-decide mode;
- reduced cognitive-load wording;
- visible focus, non-color-only status, and error recovery.

If natural-language input is unavailable to an access mode or locale, creator-approved bounded
choices must remain first-class, not a low-quality afterthought.

No response timer may silently select an agency-bearing default. Timeout policy is explicit:
pause, continue along a disclosed neutral fallback, or resume later. The choice depends on the
creator's pacing contract and the viewer's settings.

## Generated access tracks

Every playable segment manifest carries version-matched:

- dialogue transcript and speaker identity;
- captions/subtitles with timing and meaningful sound cues;
- audio-description track or description events;
- language, reading-level, and provenance metadata;
- validation status and fallback reference.

Media cannot be swapped after caption/audio-description validation without invalidating those
tracks. If a last-second fallback changes the segment, it must atomically switch media and all
access tracks.

### Captions and subtitles

- Preserve clues, interruptions, uncertainty, off-screen speech, and speaker changes.
- Keep timing readable across generated edit changes.
- Do not expose hidden dramatic state in captions.
- Validate names and invented terms against the story package.
- Retain authored fallback captions for every fallback segment.

### Audio description

- Describe consequence-relevant visual changes, not every generated detail.
- Reserve mix space in the segment plan rather than overlaying description after generation.
- Avoid narrating an inference as fact when the film intentionally preserves ambiguity.
- Validate that new dialogue does not collide with description timing.

### Sensory and cognitive safety

- Declare flash, strobe, rapid motion, loudness, and intense-content limits in the constitution.
- Provide reduced-motion and photosensitivity-safe media routes.
- Keep interaction frequency low enough to preserve attention.
- Explain repaired or declined directions in plain language.
- Let viewers review the accepted intent before a high-impact commit when pacing permits.

## Localization model

Localization is a state-preserving transformation, not a text replacement.

The locale packet contains:

- translated dialogue intent and surface line;
- character voice and formality rules;
- clue, pun, idiom, cultural, rating, and taboo annotations;
- pronunciation and speaker identity;
- caption and description conventions;
- lip-sync/performance route;
- human approval and fallback coverage.

A localized branch must preserve:

- causal information;
- what each character knows and implies;
- relationship status and power;
- dramatic ambiguity;
- rating and safety constraints;
- ending reachability.

Unsupported locale or voice capability must produce an explicit fallback—such as original audio
with validated subtitles—rather than silently using an unvalidated model or different policy.

## Accessibility and localization failure policy

| Failure | Playback behavior |
|---|---|
| Caption track missing or stale | Do not play generated segment for caption-dependent session; use matched fallback |
| Audio description collision | Use alternate mix/fallback; record defect |
| Voice input uncertain | Ask for confirmation or show mapped bounded choice |
| Timer expires | Apply viewer's declared pause/neutral-continuation policy |
| Locale changes clue meaning | Reject localized segment; use approved original/subtitle route |
| Locale moderation unavailable | Decline free text and offer validated bounded choices |
| Photosensitivity validator fails | Route to reduced-motion authored fallback |

## Measurement constructs

The program must not treat engagement as proof of quality. Each construct has a separate
measure and evidence owner.

| Construct | Operational measure | Evidence needed |
|---|---|---|
| Causal agency | Viewer identifies what their choice changed and trace agrees | Viewer response + event/state trace |
| Choice comprehension | Viewer explains accepted intent before consequence | Short task/question |
| Narrative coherence | Facts, motivation, chronology, setup/payoff remain compatible | Structural checks + blinded human review |
| Narrative satisfaction | Complete-branch rating and qualitative explanation | Viewer study, not clip judge |
| Ending quality | Obligations resolved and ending feels earned | Story expert + viewer review |
| Character continuity | Severity-weighted identity/voice/motivation defects per minute | Validators + human review |
| Accessibility parity | Same semantic choice and story information across access modes | Disabled-participant evaluation + conformance checks |
| Localization fidelity | Causal/relational/tonal meaning preserved | Bilingual/cultural review |
| Operational playability | Stalls, fallback, recovery, consequence latency | Client and trace receipts |
| Creator controllability | Creator predicts, inspects, repairs, and approves branch behavior | Task-based creator study |
| Safety | Critical incident rate and correct fail-closed behavior | Red team + scenario receipts |
| Economics | Cost per successful delivered minute | Provider, infrastructure, review, and support receipts |

## Comparative study design

Compare the same anchor across:

1. fixed linear cut;
2. conventional pre-rendered branching;
3. governed text/storyboard generation;
4. selective generated audiovisual hybrid.

The comparison should separate:

- interaction grammar from media novelty;
- perceived agency from branch count;
- generated content from slower or longer content;
- accessibility setting from product variant;
- first-run novelty from replay value.

Use within-subject or carefully balanced between-subject designs only after checking carryover
and spoiler effects. Randomize presentation order where valid. Pre-register exclusions and
analysis. Report sample composition and uncertainty; do not universalize a convenience sample.

## Human review roles

- film/story practitioners assess dramatic structure and performance;
- interactive-narrative practitioners assess agency and authoring model;
- target viewers assess comprehension, satisfaction, pacing, and value;
- disabled viewers assess real access modes, not simulated compliance alone;
- bilingual/cultural reviewers assess localized meaning;
- safety specialists assess adversarial trajectories;
- operators assess diagnosability and recovery.

An LLM may extract state conflicts or prepare samples. It must not grade its own story as the
sole judge. Research on automatic story evaluation finds limitations and non-uniform correlation
with human judgment, reinforcing the need for human evidence
([Chhun et al., TACL 2024](https://doi.org/10.1162/tacl_a_00689), accessed 2026-08-25).

## Candidate experiment thresholds

Before participant recruitment, define:

- minimum detectable agency improvement over pre-rendered branching;
- non-inferiority margins for narrative and ending quality;
- zero-tolerance critical canon, safety, and access failures;
- acceptable repair/decline/fallback rates by reason;
- p95 consequence latency and stall ceilings;
- maximum creator hours and review amplification;
- maximum cost per successful viewer-minute;
- sample-size rationale and stopping rule.

This research intentionally does not invent those product thresholds. The plan offers prototype
targets for system engineering, while value and non-inferiority thresholds require product and
research owners before a real study.

## Privacy in measurement

- Collect the minimum event and response data needed for the registered questions.
- Do not infer emotion, health, politics, sexuality, or other sensitive traits from viewing
  behavior.
- Keep raw natural-language directions out of analytics by default; store normalized intent
  and aggregate reason codes where sufficient.
- Separate operational logs, research data, and shareable branch manifests.
- Define consent, withdrawal, retention, deletion, incident hold, and provider-use terms before
  external participants.
- Do not reuse viewer contributions for model training or other productions without a separate,
  explicit agreement.

## Pass condition

This workstream passes only when every generated branch can be operated and understood through
the supported access modes and locales, evaluation distinguishes the claimed constructs, and
the evidence does not rely on engagement metrics or model self-grading as a proxy for human
meaning.
