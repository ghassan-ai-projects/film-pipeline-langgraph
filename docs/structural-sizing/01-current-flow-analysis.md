# 01 — Current Flow: Where Sizing Breaks

## The Sizing Chain (current)

```
intake ──→ constitution ──→ development ──→ script ──→ visual_dev ──→ shot_bible ──→ gen_planning
  │                          │               │                        │
  │ target_runtime_seconds   │ scene count   │ 6 scenes               │ structure extractor
  │ 180s (WRONG)             │ "4-8 scenes"  │ (correct for 180s)     │ reads story text
  └──────────────────────────┴───────────────┴────────────────────────┴──→ derives shot counts
                                                                           from text, not target
```

## Root Cause: Intake Guesses Runtime

The intake agent is an LLM. It reads the idea and produces `target_runtime_seconds`. The
current template says "between 60 and 1800" — the LLM picks a low number for any simple-sounding
idea. A story about "an artist discovering a prehistoric cave" sounds simple → 180s.
A story about "a clockmaker who can stop time" sounds simple → 180s.

**Every downstream phase scales from this number.** If intake says 180s, development
produces 4-8 scenes, script writes 6 scenes, shot bible produces 13 shots. Everything
is internally consistent — but scaled to 3 minutes instead of 10.

## Where Each Phase Gets Its Sizing

| Phase | Sizing Input | How It's Used | Enforced? |
|-------|-------------|---------------|-----------|
| Intake | Idea text | LLM guesses runtime | No |
| Constitution | Idea + intake output | No sizing — creative only | N/A |
| Development | `{target_runtime_seconds}` in template | "1-4 min → 4-8 scenes" guideline | **No** — LLM may produce 4 when 8 needed |
| Script | Scene list from development | Writes scenes; no duration guidance | **No** — no check that content fills runtime |
| Structure Extractor | Story text + StoryBible | Derives shot count = runtime / avg_duration | Runs at shot_bible time, AFTER script |
| Shot Bible | ExecutionBrief (shot counts) | Must produce exactly N shots | **Yes** — Gate A validator |
| Gen Planning | Shot matrix | Groups into batches | **Yes** — Gate B validator (was broken) |

## The Two Gaps

### Gap 1: No Upstream Contract

The intake produces `target_runtime_seconds`, but there's no mechanism to ensure
development produces enough scenes to fill that runtime. The template says
"4-8 scenes for 1-4 min" but:
- The LLM might produce 4 scenes when 8 are needed
- There's no structural validator checking `scene_count * avg_scene_duration ≈ target_runtime`
- The structure extractor only runs at shot_bible time — 2 phases too late

### Gap 2: Structure Extractor Derives From Text, Not Target

The structure extractor reads the story text and StoryBible to extract runtime:
```
"Target runtime: use the EXACT runtime stated in the story."
```

But the story text was written for 180s! If intake guessed 180s, development
produced 4-8 scenes for 180s, and script wrote 6 scenes for 180s — the structure
extractor will "extract" 180s from the text. It's circular.

**What should happen:** The structure extractor should use the `target_runtime_seconds`
from the project profile as THE contract, then derive scene count, shot count, and
act distribution FROM that target, not from the story text.

## Why "Just Increase The Number" Doesn't Work

If we tell the LLM "write a 600s film" but don't enforce scene count:
- The LLM writes 6 scenes but makes each scene description longer
- Shot bible still produces 13 shots (derived from 6 scenes × ~2 shots/scene)
- Total runtime is calculated as 13 shots × ~12s = 156s — still wrong

**Runtime = scenes × shots_per_scene × avg_shot_duration**. You can't fix the output
by tweaking one number — you need the structural contract to flow through every phase.
