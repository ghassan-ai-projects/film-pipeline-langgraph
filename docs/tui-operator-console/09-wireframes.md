# Wireframes

## Purpose

These are low-fidelity layout guides for implementation. They define information priority,
not visual polish.

## Shell Layout

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Film Pipeline TUI    Project: after-the-fall-001    Phase: script    Mode: real        │
│ Providers: 1 healthy / 1 degraded    Reviews: 2 pending    Refresh: 12s ago            │
├───────────────┬──────────────────────────────────────────────────────┬───────────────────┤
│ Projects      │ Main Workspace                                       │ Context Drawer    │
│               │                                                      │                   │
│ > After Fall  │ Dashboard / Review / Artifacts / Validation / ...    │ Raw JSON          │
│   blocked     │                                                      │ Metadata          │
│   script      │                                                      │ Help              │
│               │                                                      │ Confirm preview   │
│   North Wind  │                                                      │                   │
│   running     │                                                      │                   │
│   visual_dev  │                                                      │                   │
│               │                                                      │                   │
│   Glass Lake  │                                                      │                   │
│   complete    │                                                      │                   │
│   delivery    │                                                      │                   │
├───────────────┴──────────────────────────────────────────────────────┴───────────────────┤
│ : command palette   g d dashboard   g r review   a approve   r revise   ? help         │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

## Dashboard

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Current Phase: script                 Next Action: present_review_package                │
│ Route Reason: script phase needs creator-review approval                                │
├───────────────────────────────┬───────────────────────────────┬──────────────────────────┤
│ Eligible Actions              │ Blocked Actions               │ Risk Snapshot            │
│ approve_phase                 │ start_generation              │ 2 blocking issues        │
│ request_revision              │ rollback_to_checkpoint        │ provider degraded        │
│ inspect_review_package        │ because no confirmation yet   │ budget healthy           │
├───────────────────────────────┴───────────────────────────────┴──────────────────────────┤
│ Review Cycle: active round 2        Candidate Refs: script:v3, scene_list:v2            │
│ Approved Refs: script:v2            Pending Revisions: 1                                 │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Latest Issues                                                                      More │
│ [blocking] dialogue voice drift in scene 4                                              │
│ [warning ] payoff unclear in final beat                                                 │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ Recent Activity                                                                         │
│ 12:10 reviewer_agent completed                                                           │
│ 12:11 validator script_structure blocked                                                 │
│ 12:12 orchestrator routed to present_review_package                                      │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

## Review Workspace

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Review Package: script                                                                   │
│ Recommendation: revise                                                                   │
├───────────────────────┬──────────────────────────────────────────────────────────────────┤
│ Candidate Artifacts   │ Review Summary                                                   │
│ > script:v3           │ - pacing improved in act 2                                       │
│   scene_list:v2       │ - dialogue voice drift remains in scene 4                        │
│                       │ - validator consensus: blocked                                   │
├───────────────────────┼──────────────────────────────────────────────────────────────────┤
│ Approved Baselines    │ Diff                                                              │
│ script:v2             │ - 3 scenes changed                                               │
│                       │ - 1 new thread introduced                                        │
├───────────────────────┼──────────────────────────────────────────────────────────────────┤
│ Open Issues           │ Revision Notes Editor                                            │
│ [B] dialogue drift    │ preserve: opening exchange                                       │
│ [W] payoff clarity    │ change: scene 4 voice and ending payoff                          │
│                       │ blocking reason: validator blocked                               │
├───────────────────────┴──────────────────────────────────────────────────────────────────┤
│ [A] Approve   [R] Request Revision   [E] Escalate   [D] Defer                            │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

## Artifact Reader

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Artifact: script:v3     Phase: script     Status: candidate                              │
├───────────────────────┬────────────────────────────────────────────────┬─────────────────┤
│ Outline               │ Body                                           │ Metadata        │
│ > Scene 1             │ INT. STATION - DAWN                            │ created_by      │
│   Scene 2             │ ...                                            │ parents         │
│   Scene 3             │                                                │ validations     │
│   Scene 4             │                                                │ approval_ref    │
│   Scene 5             │                                                │ built_from      │
├───────────────────────┴────────────────────────────────────────────────┴─────────────────┤
│ / search   n next match   p prev match   v compare versions                               │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

## Checkpoint And Rollback

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Checkpoints                                                                              │
├───────────────────────────────┬──────────────────────────────────────────────────────────┤
│ Timeline                      │ Selected Checkpoint                                       │
│ > script-approved-v2          │ phase: script                                             │
│   before-gen-batch-1          │ reason: Approved at script                               │
│   shot-bible-approved-v1      │ artifacts: script:v2 scene_list:v2                       │
│                               │                                                          │
│                               │ Invalidation Preview                                      │
│                               │ will_revert: script                                       │
│                               │ will_invalidate: shot_bible:v1 prompts:v1                │
│                               │ requires_human_confirmation: true                         │
├───────────────────────────────┴──────────────────────────────────────────────────────────┤
│ [C] Compare Versions   [I] Invalidation Report   [R] Rollback                             │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

## Provider Operations

```text
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ Providers                                                                                │
├───────────────────────────────┬──────────────────────────────────────────────────────────┤
│ Provider List                 │ Detail                                                    │
│ > seedance-openrouter         │ status: degraded                                          │
│   imagen4-gemini              │ recent error: quota exhausted                             │
│                               │ safe_to_continue_other_work: true                         │
│                               │ active jobs: 2                                            │
│                               │ suggested next step: continue planning, delay generation  │
├───────────────────────────────┴──────────────────────────────────────────────────────────┤
│ [H] Refresh Health   [L] List Jobs   [X] Resolve Block                                   │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```
