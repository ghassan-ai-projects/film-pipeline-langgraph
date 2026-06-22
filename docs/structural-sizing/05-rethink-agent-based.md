# Rethink: Agent-Based Structural Reasoning, Not Hard Validators

## The Wrong Pattern (what I proposed)

```
development → Gate 0: scene_count >= 13? NO → BLOCKING → repair with "expected 13, got 6"
```

This is a factory QA conveyor belt. Count mismatches, flag errors, send back.
It assumes we know the right answer in advance and the LLM just needs to hit a number.

## Why This Fails With Real LLMs

1. **"Expected 13 scenes" might be wrong.** Maybe the LLM wrote 6 very dense
   scenes that are actually 100s each. The hard validator would reject valid output.

2. **"Add 7 more scenes" is bad feedback.** The LLM will pad with filler scenes
   that don't serve the story. Quality drops.

3. **The orchestrator should do the reasoning, not the validator.** The
   orchestrator has access to the full state — constitution, treatment, script,
   target runtime — and should THINK about whether the output is appropriate.

## The Right Pattern

The orchestrator agent (not the validator) inspects the output holistically:

```
Orchestrator reads:
  - Target runtime: 600s
  - Film type: narrative, standard pacing
  - Treatment: 6 scenes across 3 acts
  - Script: 6 scenes written

Orchestrator reasons:
  "This is a 600s narrative with 6 scenes. That's ~100s per scene.
   Standard pacing expects ~45s per scene. Either each scene needs to
   be extremely dense, or we need more scenes. Given the treatment
   describes a journey through multiple locations with character
   development, 6 scenes feels thin. I'll ask the development agent
   to expand to 10-12 scenes while preserving the narrative arc."

Orchestrator action:
  → Single repair: "The 6-scene structure feels thin for a 600s narrative.
    Consider splitting scene 3 (cave exploration) into 2-3 distinct moments
    of discovery, and scene 4 (leaving his mark) into setup and execution."
```

**Key difference:** The orchestrator doesn't say "expected 13, got 6." It says
"this specific scene could be split for better pacing at this runtime." It gives
creative, contextual feedback, not numeric targets.

## Sequential vs Parallel Validation

### Parallel (wrong):
```
Validator 1: checks scene count
Validator 2: checks act distribution
Validator 3: checks dialogue density
Validator 4: checks shot count
→ 4 issues at once → LLM tries to fix all → produces mediocre output
```

### Sequential (right):
```
Round 1: Orchestrator identifies most impactful issue → "scene count is low"
Round 2: Development agent fixes scene count → re-runs script
Round 3: Orchestrator checks result → "scene count fixed, but act 2 is too short"
Round 4: Development agent rebalances acts
Round 5: Orchestrator checks → "structure looks good, proceed"
```

One issue per round. Each round has a focused, single-task prompt.
The LLM can handle one creative fix at a time much better than five.

## How The Orchestrator Should Think

The orchestrator agent should receive:
- The target runtime and film type
- The current phase's output
- The constitution (quality bar, visual language)
- Upstream artifacts for context

It should produce:
- A qualitative assessment (not a score)
- Zero or one prioritized issue
- Specific, creative feedback for that issue

When all is well: "Output is structurally sound for the target runtime. Proceed."

## What Changes In Practice

### Remove hard validators
Gate 0 (scene count), Gate B (clip count) — these should be orchestrator
judgments, not mechanical checks. The orchestrator CAN check counts, but
it should do so with contextual reasoning, not `if count < required: block`.

### The orchestrator becomes a phase
Instead of validators running as side-effects after each phase node, the
orchestrator should be a dedicated phase that runs between creative phases:

```
intake → constitution → orchestrator_review → development → orchestrator_review → script → ...
```

Each `orchestrator_review` call:
1. Loads all artifacts produced so far
2. Reads the target runtime and film type
3. Produces a structured assessment
4. If issues found: returns ONE prioritized issue with creative feedback
5. If clean: returns approval signal

### Repair is focused
When the orchestrator flags an issue, the repair feedback contains:
- The specific artifact that needs work
- What's wrong (qualitative, with examples from the output)
- One specific suggestion (not a list)
- What to preserve (don't throw out good work)

### Convergence is natural
After 2-3 rounds, if the orchestrator still sees issues, it escalates to human
with its reasoning trail. The human can see: "I noticed X, suggested Y, agent
produced Z, still not right because..."

## Concrete Example: The Primordial Stroke

**Current system (would produce with hard validators):**
```
Orchestrator: "Expected 13 scenes for 600s narrative, got 6. Add 7 scenes."
Agent: Adds 7 filler scenes → 13 thin scenes → bad output
```

**Agent-based system:**
```
Orchestrator (Round 1):
  "Reading the treatment: 6 scenes across 3 acts for a 600s narrative.
   Standard pacing suggests ~13 scenes. Looking at the content: scene 2
   (canvas cracks, transition) is doing double duty — both the inciting
   incident AND the world transition. Consider splitting into:
   - Scene 2a: The crack appears, Artist investigates
   - Scene 2b: The transition through the crack into the cave
   This preserves the arc while giving each moment room to breathe."

Agent: Rewrites treatment with 7 scenes, splitting scene 2.

Orchestrator (Round 2):
  "7 scenes, better structure. Act 3 (return to studio, transformed
   creation) is a single scene. For a 600s arc, the return-to-world
   moment deserves its own scene before the final creation scene.
   Consider a scene where the Artist first sees his studio with
   new eyes, BEFORE he begins painting."

Agent: Adds scene for "seeing the studio anew" → 8 scenes.

Orchestrator (Round 3):
  "8 scenes with good pacing. The arc is clear. Scene durations
   should average ~75s each. The script content per scene looks
   sufficient — proceed."
```

This is creative direction, not QA inspection. The orchestrator acts like a
story editor, not a test suite.
