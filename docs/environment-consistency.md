# Environment Consistency

## Problem

AI video models often treat every prompt as a chance to rebuild the world. Even if three
clips are meant to happen in the same room, the generated clips may change walls, furniture,
lighting direction, props, scale, or geography.

The solution is to model environments as structured production assets, not prose.

## Core Principle

Every location needs:

- what never changes
- what can change
- what camera angle is being used
- what local zone the shot happens in
- what lighting/time state is active
- which reference image anchors the shot

The prompt should say **same environment, different viewpoint**, not simply repeat a loose
description of the environment.

## Environment Hierarchy

### 1. Root Environment

The root environment is the canonical location.

Example:

```text
ENV_STUDIO = Leo's narrow artist studio
```

It defines the permanent truth:

- room geometry
- architectural layout
- fixed furniture
- wall/floor materials
- major props
- windows and doors
- spatial scale
- default palette

### 2. Environment Zones

A root environment can contain zones.

Example:

- `studio.canvas_wall`
- `studio.desk_corner`
- `studio.window_side`
- `studio.floor_area`
- `studio.doorway`

Zones let the model move within the same place without reinventing it.

### 3. Viewpoints

Each zone should have approved viewpoints.

Example:

- `wide_establishing`
- `over_canvas_to_artist`
- `desk_to_canvas`
- `low_floor_angle`
- `doorway_into_room`
- `profile_against_window`

The viewpoint changes the camera, not the world.

### 4. Environment State

Some things can change over time, but only as tracked state.

Examples:

- time of day
- lighting mode
- mess level
- weather outside window
- props moved by story action
- damage or transformation

These should be represented as named states, not ad hoc prompt changes.

Example:

```yaml
environment_state: studio.act1_night_messy
lighting_state: laptop_cool_blue
mess_state: high
```

## Environment Bible Structure

Suggested schema:

```yaml
environment_id: env:studio
name: Leo's Artist Studio
root_prompt_block: >
  Narrow cluttered artist studio at night, rectangular room, large blank canvas on wooden
  easel at the north wall, cluttered desk on the left wall, laptop glow, paint tubes,
  brushes, paint-splattered wooden floor, single window with drawn curtain on the right wall.

invariants:
  geometry:
    - rectangular narrow room
    - canvas always on north wall
    - desk always on left wall
    - window always on right wall
    - door behind camera on south side
  fixed_objects:
    - wooden easel
    - cluttered desk
    - laptop
    - paint tubes
    - brush jar
    - wooden floor with paint splatter
  materials:
    - worn wooden floor
    - matte off-white walls
    - old wooden easel
  must_not_change:
    - no extra windows
    - no new furniture
    - no room expansion
    - no outdoor view unless curtain is opened by story state

zones:
  canvas_wall:
    description: Canvas, easel, paint area, north wall.
    allowed_viewpoints:
      - wide_front
      - over_shoulder_to_canvas
      - side_profile_canvas
  desk_corner:
    description: Left wall desk, laptop, smartphone, scattered notes.
    allowed_viewpoints:
      - desk_close
      - desk_to_canvas
      - over_laptop_glow

lighting_states:
  act1_night_cool:
    description: Cool blue laptop light and harsh overhead LED.
    shadow_direction: top-left to lower-right
    color_temperature: cool
  act3_golden_afternoon:
    description: Warm golden sunlight through open curtain.
    shadow_direction: right to left
    color_temperature: warm

reference_assets:
  board: references/environments/ENV_STUDIO/environment-board.png
  wide: references/environments/ENV_STUDIO/master-frames/wide.png
  desk: references/environments/ENV_STUDIO/master-frames/desk.png
  canvas: references/environments/ENV_STUDIO/master-frames/canvas.png
```

## Environment Fingerprint

Each environment should have a short fingerprint that appears in every related prompt.

The fingerprint is a compressed invariant block.

Example:

```text
ENV_FINGERPRINT: same narrow rectangular artist studio, canvas on north wall, desk on left
wall, window on right wall, paint-splattered wooden floor, old wooden easel, laptop glow,
no new furniture, no layout change.
```

This should be inserted into every shot prompt for that environment.

## Prompt Assembly For Same Environment

Use this order:

```text
ENV_ROOT_BLOCK
+ ENV_FINGERPRINT
+ ACTIVE_ZONE
+ VIEWPOINT
+ LIGHTING_STATE
+ STORY_STATE_CHANGES
+ CAMERA_LANGUAGE
+ CHARACTER_ACTION
+ ENVIRONMENT_REINFORCEMENT
+ NEGATIVES
```

Important:

- `ENV_ROOT_BLOCK` and `ENV_FINGERPRINT` stay stable.
- `ACTIVE_ZONE` changes when the shot moves within the location.
- `VIEWPOINT` changes the camera angle.
- `LIGHTING_STATE` changes only when the story requires it.
- `STORY_STATE_CHANGES` lists props or environmental changes caused by previous shots.

## Example Prompts

### Same Room, Wide View

```text
ENV_ROOT_BLOCK: Narrow cluttered artist studio at night, rectangular room, large blank
canvas on wooden easel at north wall, cluttered desk on left wall, laptop glow, paint tubes,
brushes, paint-splattered wooden floor, single window with drawn curtain on right wall.

ENV_FINGERPRINT: same narrow rectangular artist studio, canvas north wall, desk left wall,
window right wall, paint-splattered wooden floor, no new furniture, no layout change.

ZONE: canvas_wall. VIEWPOINT: wide_front, camera faces the north wall and sees the canvas,
desk remains visible on left edge, window remains on right edge.
```

### Same Room, Desk Angle

```text
ENV_ROOT_BLOCK: Narrow cluttered artist studio at night, rectangular room, large blank
canvas on wooden easel at north wall, cluttered desk on left wall, laptop glow, paint tubes,
brushes, paint-splattered wooden floor, single window with drawn curtain on right wall.

ENV_FINGERPRINT: same narrow rectangular artist studio, canvas north wall, desk left wall,
window right wall, paint-splattered wooden floor, no new furniture, no layout change.

ZONE: desk_corner. VIEWPOINT: desk_to_canvas, camera near the left wall desk looking across
the laptop toward the canvas on the north wall; same room geometry, same furniture positions.
```

The second prompt changes camera position, but it repeats the invariant layout.

## Matrix Integration

Each row in the master film matrix should include:

```json
{
  "environment": "env:studio",
  "environment_zone": "studio.desk_corner",
  "environment_state": "studio.act1_night_messy",
  "viewpoint": "desk_to_canvas",
  "lighting_state": "act1_night_cool",
  "environment_reference_refs": [
    "ref:env:studio:board:v1",
    "ref:env:studio:desk:v1"
  ],
  "environment_invariants_ref": "env:studio:invariants:v1"
}
```

## Environment Validation

Validate environments at several levels.

### Environment Bible Validation

Checks:

- root layout is concrete
- invariants are clear
- zones are defined
- viewpoints are defined
- lighting states are named
- must-not-change list exists

### Reference Board Validation

Checks:

- wide view communicates the environment
- alternate angles match same geometry
- lighting states do not contradict layout
- board is not visually noisy
- no accidental extra rooms or doors

### Prompt Readiness Validation

Checks:

- prompt includes root environment
- prompt includes fingerprint
- zone and viewpoint are valid
- lighting state is valid
- story changes are from continuity ledger
- negatives prevent layout drift

### Clip Validation

Checks:

- geometry matches environment bible
- fixed objects remain in expected relative positions
- lighting direction matches active lighting state
- props do not appear/disappear unexpectedly
- camera angle changes without changing the location

## When Environment References Are Enough

A recurring environment is ready when:

- root environment bible is approved
- wide reference is approved
- at least two alternate angles are approved
- lighting variants needed by the story are approved
- zones and viewpoints are mapped
- environment board passes validation
- prompt assembly can reference the same environment from different viewpoints

A minor environment can be simpler:

- one root description
- one reference board
- one or two allowed viewpoints

## Common Failure Modes

### Problem: Same Root, Different Room

Cause:
Prompt changes the description too much between clips.

Fix:
Use stable root block plus viewpoint-specific addendum.

### Problem: Same Room, Wrong Furniture Layout

Cause:
The model does not know object positions.

Fix:
Add spatial invariants and environment fingerprint to every prompt.

### Problem: Lighting Changes Randomly

Cause:
Lighting is described emotionally but not spatially.

Fix:
Use named lighting states with direction, source, and color temperature.

### Problem: Camera Angle Creates New Architecture

Cause:
Prompt says "different angle" without specifying where the camera is.

Fix:
Use approved viewpoints tied to zones.

### Problem: Environment Board Is Too Pretty But Not Useful

Cause:
Concept art has mood but no spatial clarity.

Fix:
Require wide establishing view, alternate angle, and fixed object list.

## Environment Agents

Suggested agents:

- environment-bible-agent
- location-map-agent
- zone-and-viewpoint-agent
- lighting-state-agent
- environment-reference-agent
- environment-prompt-composer
- environment-continuity-validator
- environment-clip-validator

## Human Review

Human review should approve:

- root environment bible
- recurring environment boards
- zone and viewpoint map
- major environment state changes
- any environment whose geometry is story-critical

The review package should show:

- root description
- invariants
- zone map
- reference board
- lighting variants
- sample prompts for different viewpoints
- validation findings

Environment consistency is not solved by repeating a sentence. It is solved by giving the
model a stable world model and then changing only the allowed layer for each shot.
