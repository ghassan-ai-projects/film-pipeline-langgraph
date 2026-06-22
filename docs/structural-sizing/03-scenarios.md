# 03 — Scenario Simulations

## Scenario A: 60s Micro-Film

**Idea:** "A single raindrop falls on a leaf."

**Expected flow:**
1. Intake: classifies as `visual_poetry`, runtime=60s, pacing=slow_cinema
2. Structure: `target=60, avg_shot=12.5s, total_shots=5, scenes=1`
3. Development: MUST produce 1 scene
4. Script: 1 scene with detailed visual description, no dialogue
5. Shot Bible: 5 shots × ~12s each = 60s

**Current problem:** Intake might guess 120s or 30s. No enforcement of scene=1.

**With new system:** Structure extractor runs before development, sets `scene_count=1`.
Development MUST produce 1 scene. Script writes 1 rich scene. Shot bible produces 5 shots.

---

## Scenario B: 180s Short (current Primordial Stroke)

**Idea:** "An artist paralyzed in his studio discovers a crack in his canvas
that opens into a prehistoric cave."

**Expected flow:**
1. Intake: narrative, 180s, standard pacing
2. Structure: `target=180, avg_shot=7.5s, total_shots=24, scenes=4-6`
3. Development: MUST produce 4-6 scenes
4. Script: 4-6 scenes with action and minimal dialogue
5. Shot Bible: 24 shots × ~7.5s each = 180s

**Current problem:** Actually produced correctly! 6 scenes, 13 shots is low but
the shot durations (8-18s) fill the runtime. The creative output was fine for 180s.

**With new system:** Same, but development is contractually required to produce
4-6 scenes (not 2 or 10).

---

## Scenario C: 600s Narrative (the 10-minute Primordial Stroke)

**Idea:** Same as B, but intended for 10 minutes.

**Expected flow:**
1. Intake: narrative, 600s, standard pacing
2. Structure: `target=600, avg_shot=7.5s, total_shots=80, scenes=13`
3. Development: MUST produce 13 scenes (spread across 3 acts: 4-5-4)
4. Script: 13 scenes with substantial action and dialogue
5. Shot Bible: 80 shots × ~7.5s each = 600s

**Current problem:** Intake says 180s → everything scales down. With the fix to
intake template, intake should now say 600s for a multi-location journey with
character development. But development still has no enforcement.

**With new system:**
1. Intake produces 600s (fixed template)
2. Structure extractor runs before development: `scene_count=13, shot_count=80`
3. Development MUST produce 13 scenes. If it produces 6 → repair.
4. Script writes 13 scenes with guidance: "~46s per scene"
5. Shot bible produces 80 shots. Gate A enforces.

**Key metric:** Runtime = scenes × avg_scene_duration = 13 × 46s = 598s ≈ 600s ✅

---

## Scenario D: 1800s Epic

**Idea:** "A three-generation saga of a family of lighthouse keepers."

**Expected flow:**
1. Intake: narrative, 1800s, slow_cinema pacing
2. Structure: `target=1800, avg_shot=12.5s, total_shots=144, scenes=30`
3. Development: MUST produce 30 scenes (3 acts × 10 scenes each)
4. Script: 30 scenes with full dialogue and action
5. Shot Bible: 144 shots × ~12.5s = 1800s

**Current problem:** Intake would never guess 1800s. Even with better template,
the LLM might cap at 600-900s. Development would produce at most 25 scenes
(per current template: "10-20 min film → 12-25 scenes").

**With new system:**
- Template needs explicit upper-end sizing: "20-30 min film → 25-40 scenes"
- Structure extractor derives exact numbers from formula, not from LLM guess
- Development gets a hard number, not a range

---

## Scenario E: What Happens When LLM Produces Too Few Scenes?

**Setup:** Target is 600s, structure requires 13 scenes. Development produces 6.

**Current behavior:** Nothing catches it. Script writes 6 scenes. Shot bible
produces shots for 6 scenes. Total runtime ~160s. Nobody notices.

**With new system:**
1. Gate 0 validator runs after development: `scene_count=6, required=13` → BLOCKING
2. Repair feedback: "Expected 13 scenes across 3 acts, got 6. You need to add
   7 more scenes. Suggested: 3 in act 1, 2 in act 2, 2 in act 3."
3. Development re-runs with feedback
4. If still wrong after 3 attempts → escalate to human

---

## Scenario F: What Happens When Shot Durations Don't Add Up?

**Setup:** Shot bible produces 24 shots but total duration = 150s (target was 180s).

**Current behavior:** Gate A validator (`validate_shot_structure`) catches this:
"Total duration 150s vs target 180s" → BLOCKING → repair.

**With new system:** Same — Gate A already handles this. No change needed.

---

## Scenario G: User Specifies Runtime Explicitly

**Setup:** User says "I want a 10-minute film" when creating the project.

**Desired behavior:** The `create_film_project` MCP tool should accept an optional
`target_runtime_seconds` parameter that OVERRIDES the intake agent's estimate.

**Current behavior:** No way to specify runtime. Intake always guesses.

**With new system:**
1. MCP tool adds optional `target_runtime_seconds` parameter
2. If provided, stored in project state as `user_specified_runtime`
3. Intake agent sees this and uses it instead of guessing
4. Structure extractor also uses it as the contract

---

## Summary: What Needs To Change

| Change | Priority | Effort |
|--------|----------|--------|
| Move structure extractor before development | P0 | Medium |
| Add scene_count to ExecutionBrief schema | P0 | Small |
| Gate 0: scene count validator | P0 | Small |
| Development template: hard scene count, not range | P0 | Small |
| Script template: per-scene duration guidance | P1 | Small |
| Better intake sizing (done in `bad0de2`) | P0 | Done |
| MCP: user-specified runtime override | P1 | Small |
| Structure extractor: derive FROM target, not text | P0 | Small |
