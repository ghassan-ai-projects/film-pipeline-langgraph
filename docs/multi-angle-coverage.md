# Multi-Angle Coverage

## Purpose

Some moments should be generated from multiple angles and assembled in post-production.

Instead of treating every generated clip as a separate story event, the system should support
**coverage groups**: several clips showing the same action, same environment state, and same
continuity moment from different camera angles.

This gives the editor options and can make final scenes feel more cinematic.

## When To Use Multi-Angle Coverage

Use coverage groups for:

- important emotional beats
- dialogue exchanges
- action beats
- reveals
- entrances and exits
- object handoffs
- character reactions
- scene transitions
- moments likely to need editorial control

Avoid coverage groups for:

- simple establishing shots
- abstract visual-poetry shots where continuity is loose
- low-priority shots
- expensive provider runs with low story value
- shots where repeating generation may increase identity drift

## Coverage Group Concept

A coverage group is one story moment with several planned camera angles.

Example:

```yaml
coverage_group_id: cov:S012:memory-reveal
scene_id: S012
story_moment: Leo sees the old brush and remembers his mother.
continuity_event: brush_reveal
environment_state: studio.act1_night_messy
character_state:
  leo: stunned_quiet
coverage_type: emotional_reveal
required_angles:
  - master_wide
  - close_reaction
  - insert_object
  - over_shoulder
editorial_intent: Build from object insert to face reaction.
```

## Coverage Shot Types

Suggested angle types:

- `master_wide`: establishes geography and blocking
- `medium_action`: shows body/action clearly
- `close_reaction`: emotional face read
- `insert_object`: prop or object detail
- `over_shoulder`: relationship between viewer/subject/object
- `profile`: silhouette, tension, intimacy
- `reverse_angle`: second character or opposite perspective
- `cutaway`: environment, hands, symbolic detail

## Matrix Integration

The master film matrix should support coverage groups.

Example rows:

```json
[
  {
    "shot_id": "S012-01A",
    "coverage_group_id": "cov:S012:memory-reveal",
    "coverage_role": "master_wide",
    "scene_id": "S012",
    "story_event_id": "event:brush-reveal",
    "environment": "env:studio",
    "environment_zone": "studio.desk_corner",
    "viewpoint": "wide_desk_to_canvas",
    "state_in_ref": "state:event:brush-reveal:in",
    "state_out_ref": "state:event:brush-reveal:out",
    "sync_group": "sync:brush-reveal",
    "duration_seconds": 8,
    "priority": "hero"
  },
  {
    "shot_id": "S012-01B",
    "coverage_group_id": "cov:S012:memory-reveal",
    "coverage_role": "close_reaction",
    "scene_id": "S012",
    "story_event_id": "event:brush-reveal",
    "environment": "env:studio",
    "environment_zone": "studio.desk_corner",
    "viewpoint": "close_leo_reaction",
    "state_in_ref": "state:event:brush-reveal:in",
    "state_out_ref": "state:event:brush-reveal:out",
    "sync_group": "sync:brush-reveal",
    "duration_seconds": 6,
    "priority": "hero"
  }
]
```

Important:
Multiple angles share the same story event and continuity state. They do not advance story
state independently unless the editor selects them as sequential action.

## Continuity Rules

All shots in a coverage group should share:

- same environment state
- same character state
- same wardrobe
- same prop positions
- same lighting state
- same story event
- same reference anchors

The camera changes. The world does not.

## Generation Strategy

### Strategy A. Generate Master First

Generate the master wide shot first.

Then use its first/last/mid frames as anchors for other angles when provider supports it.

Good for:

- continuity-heavy scenes
- environments with tricky geometry
- action beats

### Strategy B. Generate Reference-Driven Angles

Use the same character and environment reference sheets for each angle, without chaining
between angles.

Good for:

- dialogue
- reaction shots
- object inserts

### Strategy C. Generate From Selected Still

Extract a still from the best generated angle and use it as a visual anchor for related
angles.

Good for:

- character identity consistency
- same costume and lighting
- reaction inserts

### Strategy D. Generate Alternatives

Generate several versions of the same angle and select the best take.

Use sparingly for:

- hero shots
- final emotional beats
- expensive scenes where quality matters

## Prompt Assembly For Coverage

Coverage prompts should share a common event block.

```text
COVERAGE_EVENT_BLOCK
+ ENV_ROOT_BLOCK
+ ENV_FINGERPRINT
+ CHARACTER_BLOCKS
+ CONTINUITY_STATE
+ SHARED_ACTION
+ COVERAGE_ROLE
+ VIEWPOINT
+ CAMERA_LANGUAGE
+ NEGATIVES
```

The shared action stays the same. `COVERAGE_ROLE` and `VIEWPOINT` change.

## Coverage Validation

Coverage needs validation at two levels.

### Per-Clip Validation

Each generated angle must pass:

- prompt adherence
- character identity
- environment fidelity
- artifact check
- technical quality

### Cross-Angle Validation

The coverage group must pass:

- same environment
- same lighting
- same wardrobe
- same prop state
- same story moment
- no contradictory body/action state
- useful editorial variety

The key question:
Do these clips feel like different angles of the same moment?

## Post-Production Integration

Coverage groups should feed an edit decision process.

The editor agent should:

- inspect all angles
- select active takes
- choose order
- trim overlaps
- preserve continuity
- avoid repeating the same action awkwardly
- use inserts/reactions to hide weak motion

Assembly manifest should support coverage:

```json
{
  "coverage_group_id": "cov:S012:memory-reveal",
  "selected_shots": [
    {
      "shot_id": "S012-01C",
      "role": "insert_object",
      "in": 0.0,
      "out": 2.0
    },
    {
      "shot_id": "S012-01B",
      "role": "close_reaction",
      "in": 1.0,
      "out": 5.0
    },
    {
      "shot_id": "S012-01A",
      "role": "master_wide",
      "in": 4.0,
      "out": 8.0
    }
  ]
}
```

## Cost Policy

Multi-angle coverage multiplies generation cost, so it should be planned deliberately.

Use profiles:

- `draft`: no coverage except essential inserts
- `internal_review`: coverage for selected hero moments
- `studio`: coverage for key scenes
- `festival`: coverage for major emotional beats and transitions

The generation plan should estimate:

- cost per coverage group
- number of angles
- number of optional takes
- whether human approval is required

## Human Review

Before generating coverage, the review package should show:

- story moment
- why coverage is needed
- planned angles
- expected cost
- continuity risks
- post-production use

After generation, the review package should show:

- all angles
- validation scores
- cross-angle consistency report
- editor recommendation
- selected edit sequence

## When Coverage Is Enough

Coverage is enough when:

- at least one master or context shot works
- at least one emotional/action close-up works when needed
- inserts or cutaways exist for weak transitions when needed
- cross-angle validation passes
- editor can assemble the story moment without continuity contradictions

More angles are not automatically better. Too many weak angles create noise and cost.

## MCP Tools

Suggested tools:

- `plan_coverage_group`
- `list_coverage_groups`
- `inspect_coverage_group`
- `approve_coverage_generation`
- `validate_coverage_group`
- `select_coverage_takes`
- `assemble_coverage_group`

## Design Rule

Coverage groups let the film behave more like real production: generate a moment from
multiple useful angles, then make the final creative choice in the edit.
