# Scene-Centric Workflow

## Purpose

The TUI should support scene-by-scene navigation and targeted scene changes as a first-class
workflow.

This is not just artifact inspection. It is a creative steering workflow.

## Why It Matters

Film creators rarely think only in terms of whole-project phases. They often think in units
such as:

- scene
- beat
- shot cluster
- character moment

If the TUI is only phase-centric, it will feel operational but not creative.

## Main Requirement

A user must be able to:

- open the scene list
- navigate scene by scene
- inspect the current scene deeply
- review scene-specific issues
- request targeted improvements for one scene
- compare revised scene output against baseline

## Recommended Scene Workspace

Add a scene-oriented workspace within `Review` or `Artifacts`.

Recommended layout:

- scene navigator rail
- active scene reader
- scene metadata and dependencies panel
- scene issues panel
- scene actions panel

## Scene Navigator

Each scene row should show:

- scene id
- scene heading or title
- dramatic function
- status
- candidate vs approved indicator
- issue count

## Active Scene Reader

Show:

- scene heading
- action lines
- dialogue
- intent or dramatic purpose
- related validation notes

## Scene Dependencies Panel

Show references to:

- story/treatment source
- character constraints
- environment constraints
- shot-intent links
- upstream approved baseline

This matters because many scene changes have continuity implications.

## Scene Issues Panel

Show issues that belong specifically to the scene:

- dialogue voice problems
- continuity breaks
- pacing problems
- theme or payoff weaknesses
- visual consistency concerns

## Scene Actions

Required actions:

- `review scene`
- `request scene revision`
- `compare scene versions`
- `mark for later`
- `jump to previous/next scene`

Later possible actions:

- `request shot-plan refresh for this scene`
- `request scene-specific validator rerun`

## Scope Rule

The TUI should allow targeted scene changes, but the backend must stay honest about scope.

That means:

- user can ask to improve one scene
- service layer decides whether the repair is scene-local or has downstream invalidation
- TUI must show that scope clearly

Example:

- changing dialogue wording may be scene-local
- changing scene outcome may affect later scenes and shot plans

## Recommended Backend Concepts

Add service concepts such as:

- `SceneSummary`
- `SceneDetail`
- `SceneRevisionRequest`
- `SceneComparison`
- `SceneImpactPreview`

## Recommended Services

Likely responsibilities:

- `ArtifactService.list_scenes(project_id)`
- `ArtifactService.get_scene_detail(project_id, scene_id)`
- `ReviewService.get_scene_review_workspace(project_id, scene_id)`
- `ReviewService.request_scene_revision(project_id, scene_id, notes)`
- `ValidationService.list_scene_issues(project_id, scene_id)`
- `CheckpointService.compare_scene_versions(project_id, scene_id, from_ref, to_ref)`

Scene workflow rule:

- `Scenes` owns targeted scene revision requests
- `Review` owns phase-level acceptance of the resulting candidate package

## TUI Requirements

### Navigation

- `[` previous scene
- `]` next scene
- scene search by id, heading, or keyword
- jump from issue to scene

### Revision

Revision for a scene should support:

- preserve
- improve
- remove
- clarify
- continuity fix
- tone fix
- dialogue fix

### Comparison

The user should be able to compare:

- approved scene vs candidate scene
- revision A vs revision B
- current scene vs upstream treatment intent

## Relationship To Phase-Centric Review

Scene-centric review should not replace phase review.

It should sit under it:

- phase review decides whether the whole artifact package is good enough
- scene review lets the user target exactly where change is needed

That is the right balance between creative control and system coherence.

## V1 Recommendation

Implement:

- scene list navigation
- scene detail reader
- scene-specific issue panel
- scene revision request flow
- scene compare view

Delay:

- direct scene editing in the TUI
- multi-scene batch editing
- beat-level editing UI

## Acceptance Criteria

- a user can move scene by scene quickly
- a user can understand one scene in isolation and in context
- a user can request targeted scene improvement
- the TUI explains whether a scene change is local or has wider impact
