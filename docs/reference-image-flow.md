# Reference Image Flow

## Purpose

Reference images are one of the most important assets in the whole pipeline. They are the
visual contract that stabilizes characters, environments, props, tone, and camera language
before expensive video generation starts.

The goal is not to create pretty concept art. The goal is to create **AI-usable visual
anchors** that downstream video models can actually follow.

## Core Principle

Reference images should answer three questions:

- What must stay the same?
- What is allowed to vary?
- What should the video model never invent?

If a reference image does not help answer those questions, it is decoration, not production
reference.

## Reference Image Types

### 1. Character Identity Sheet

Purpose:
Lock the character's face, body, wardrobe, and visual identity.

Should include:

- dominant front face
- three-quarter face angles
- profile when useful
- full body
- wardrobe baseline
- expression strip
- detail insets for eyes, hands, scars, props, texture

### 2. Costume And State Sheet

Purpose:
Track approved costume variations and story-state changes.

Should include:

- default costume
- damaged or changed costume
- emotional or physical state variants
- act-specific looks

### 3. Environment Board

Purpose:
Lock a location's geometry, mood, lighting, materials, and palette.

Should include:

- dominant wide establishing view
- alternate angles
- lighting variants
- important props
- texture details
- palette strip

Rule:
Environment boards should usually have no characters. They are for spatial consistency.

### 4. Prop And Object Sheet

Purpose:
Lock important story objects.

Should include:

- clean isolated view
- in-hand scale view
- damaged or changed state if relevant
- material detail

### 5. Scale Sheet

Purpose:
Lock relative proportions.

Should include:

- main characters side by side
- height or scale markers
- key object scale
- environment scale when relevant

### 6. Style And Color Board

Purpose:
Lock the visual mood without over-constraining content.

Should include:

- palette
- texture examples
- light behavior
- contrast examples
- grain or softness reference

### 7. Camera Reference Board

Purpose:
Show framing and camera grammar.

Should include:

- close-up style
- wide shot style
- movement mood
- lens feeling
- composition examples

## Reference Planning Flow

### Phase 1. Reference Strategy

Before generating images, create a reference strategy.

Inputs:

- film constitution
- story bible
- character bible
- environment bible
- camera language bible
- master film matrix
- risk register

Outputs:

- reference matrix
- reference priority list
- provider plan
- validation plan
- cost estimate

Questions:

- Which characters need hard identity locking?
- Which environments need geometry locking?
- Which props are story-critical?
- Which scenes are high drift risk?
- Which references may trigger provider moderation?
- Which references are needed before shot bible approval?

### Phase 2. Prompt Block Lock

Reference prompts must use the same locked blocks as video prompts.

Lock before generation:

- character identity blocks
- environment blocks
- camera blocks
- global negatives
- style constraints

If a locked block changes, related references need a new version.

### Phase 3. Base Frame Generation

Generate base frames using image providers, not video providers.

Generate:

- character angles
- expressions
- body and wardrobe views
- environment angles
- lighting variants
- prop views
- detail insets
- scale frames

Use provider tiers deliberately:

- cheap/fast provider for bulk frames
- stronger provider for hero faces and critical props
- image-to-image for identity angle consistency
- manual/human selection for critical anchors when needed

### Phase 4. Per-Frame Validation

Validate individual frames before building composite sheets.

Automatic checks:

- file exists
- resolution is high enough
- image is not corrupt
- image is not blank
- subject is visible
- face exists for character frames

AI review checks:

- prompt match
- artifact freedom
- subject clarity
- technical quality
- AI usability

Decision:

- pass: use in composite
- fail: regenerate or replace
- repeated fail: keep best attempt and flag for human review

### Phase 5. Composite Sheet Construction

Build production reference sheets from accepted frames.

Rules:

- labels go in margins, not over image tiles
- dominant tile shows the most important anchor
- layout should communicate hierarchy
- character sheets prioritize face identity
- environment sheets prioritize spatial geometry
- sheets should be readable at the size used by the video provider

### Phase 6. Composite Validation

Validate the final sheet, not only the individual tiles.

Character sheet validation:

- same identity across tiles
- strong dominant face anchor
- clear wardrobe
- useful expression range
- no confusing duplicates
- no contradictory features

Environment board validation:

- coherent spatial layout
- same location across angles
- lighting variants make sense
- props and materials are stable
- no characters unless intentionally included

Camera/style board validation:

- clear style signal
- not too visually noisy
- compatible with selected film style
- useful for prompt assembly

### Phase 7. Delta Regeneration

If a sheet fails, replace only failing tiles when possible.

Examples:

- face drift in side angle: regenerate side angle only
- wrong expression: regenerate that expression tile only
- environment geometry conflict: replace contradictory angle
- bad label placement: rebuild sheet layout, not image frames

### Phase 8. Registration

Approved references are registered into the reference index.

Each reference receives:

- reference id
- type
- subject id
- file path
- provider
- prompt id
- validation score
- approved usage
- moderation risk
- version
- locked status

### Phase 9. Matrix And Continuity Integration

The master film matrix and continuity ledger reference approved images.

Each shot can point to:

- character sheet
- environment board
- prop sheet
- style board
- camera board
- previous frame anchor
- re-anchor frame

## When We Have Enough References

Enough does not mean "many images." Enough means the references can stabilize the film.

### Character Is Ready When

- front face is strong
- at least two side or angle references are usable
- full body or wardrobe is clear
- required expressions are represented
- identity is consistent across tiles
- validator passes identity usability
- human can recognize the character across the sheet

Minimum for minor character:

- one identity sheet
- one wardrobe/body view

Minimum for main character:

- identity sheet
- body/wardrobe sheet
- expression strip
- detail insets if features matter
- scale reference if appearing with others

### Environment Is Ready When

- one wide establishing view is strong
- at least one alternate angle confirms geometry
- lighting profile is clear
- key props and materials are visible
- no contradictory layout appears
- environment validator passes usability

Minimum for minor environment:

- one environment board

Minimum for recurring environment:

- wide view
- alternate angle
- lighting variant
- material/prop details

### Story Object Is Ready When

- object silhouette is clear
- material is clear
- scale is clear
- changed states are represented if story-relevant

### Stop Rule

Stop generating more references when:

- required validators pass
- human review passes
- missing references no longer create generation risk
- additional references would add noise or contradictory signals

More references can make results worse if they confuse the model.

## When A Reference Is Bad For AI

A reference may be visually attractive but bad for generation.

Bad reference signs:

- too many competing subjects
- inconsistent face across tiles
- contradictory wardrobe
- cluttered environment with unclear layout
- labels or text over image content
- strong style mismatch with desired output
- extreme crop that hides necessary identity
- dramatic lighting that obscures the face
- impossible geometry
- wrong aspect or resolution for provider
- contains elements likely to trigger moderation
- too abstract for a shot that needs concrete continuity

AI-unusable references should be tagged:

- `too_noisy`
- `identity_unclear`
- `geometry_unclear`
- `style_conflict`
- `moderation_risk`
- `low_resolution`
- `text_bleed_risk`
- `contradictory`

## Reference Validation Scores

Suggested statuses:

- `approved`: usable and locked
- `approved_with_notes`: usable but needs careful prompt support
- `needs_delta_fix`: specific tile or detail needs replacement
- `needs_regeneration`: sheet cannot safely guide generation
- `human_review_required`: model judgment is uncertain or creative tradeoff exists
- `rejected`: harmful or unusable for AI generation

Suggested thresholds:

- character sheet: 80%
- environment board: 80%
- prop sheet: 80%
- style board: 75%
- camera board: 75%
- scale sheet: 80%

## Multi-Model Reference Review

Important references should receive multi-model review.

Use multi-model review for:

- main character identity sheets
- recurring environments
- reference sheets for expensive scenes
- references with moderation risk
- final locked reference index

Recommended reviewers:

- visual identity reviewer
- production usability reviewer
- continuity reviewer
- provider-risk reviewer

The consensus report should preserve disagreements. If one model says the sheet is beautiful
but another says it is poor for AI continuity, that disagreement matters.

## Final Shape

The final reference package should look like this:

```text
references/
  index/
    reference-index.json
    reference-validation-summary.json
  characters/
    CHAR_001/
      identity-sheet.png
      costume-sheet.png
      expression-sheet.png
      master-frames/
      validation-report.json
  environments/
    ENV_001/
      environment-board.png
      lighting-board.png
      material-details.png
      master-frames/
      validation-report.json
  props/
    PROP_001/
      prop-sheet.png
      state-variants.png
      validation-report.json
  style/
    visual-style-board.png
    camera-style-board.png
    color-palette.png
  scale/
    scale-sheet.png
  review-packages/
    reference-review-package-v1.md
```

The key machine-readable output is:

```text
references/index/reference-index.json
```

That index is what the master film matrix, continuity ledger, prompt registry, and validators
should use.

## Reference Index Core Schema

```json
{
  "reference_id": "ref:char:leo:identity:v1",
  "project_id": "project:example",
  "type": "character_identity_sheet",
  "subject_id": "char:leo",
  "path": "references/characters/CHAR_001/identity-sheet.png",
  "source_frames": [],
  "provider": "imagen-fast",
  "prompt_refs": [],
  "approved_for": ["prompt_anchor", "clip_validation", "re_anchor"],
  "not_approved_for": [],
  "validation": {
    "status": "approved",
    "score": 84,
    "reports": []
  },
  "ai_usability": {
    "score": 86,
    "risks": [],
    "notes": ""
  },
  "version": 1,
  "locked": true
}
```

## RCTCO Requirement

All reference-generation and reference-validation prompts should use RCTCO:

- Role: the specialist role, such as reference art director or production usability validator
- Core Task: generate, validate, repair, or summarize a specific reference artifact
- Context: film constitution, bibles, matrix rows, style profile, provider constraints
- Constraints: exact frame requirements, negatives, no text over tiles, provider limits
- Output Format: reference artifact, JSON validation report, or delta-regeneration plan

## Human Review

Human review is required before locking:

- main character identity sheets
- recurring environment boards
- final reference index
- any reference tagged `human_review_required`

The review package should show:

- reference sheet
- intended use
- validation score
- risks
- model disagreements
- what shots/scenes depend on it
- orchestrator recommendation

## What To Avoid

- generating references before story and character intent are stable
- using concept art as production reference without validation
- letting every shot have a unique style reference
- overloading one reference sheet with too many ideas
- using labels inside image tiles
- accepting beautiful images that fail identity or geometry needs
- treating references as optional after generation starts

Reference images are production infrastructure. Once approved, they become part of the film's
state.
