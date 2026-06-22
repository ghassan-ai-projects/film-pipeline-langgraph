# Systematic Agent Prompt Review

## Rating Scale
- **🟢 Strong**: Clear instructions, explicit output format, good constraints
- **🟡 Adequate**: Works but could be more specific
- **🔴 Weak**: Missing context, vague output format, needs rewrite

---

## 1. Intake Agent — 🟢 Strong

| Field | Assessment |
|-------|-----------|
| Role | Clear |
| Core Task | Good — lists all outputs |
| Context | Adequate — `{idea}` only, fine for first phase |
| Constraints | Excellent — concrete rules: "never use 1 second", specific genre tags, valid delivery modes |
| Output | Explicit JSON template with all fields |
| Agent | Good coercion helpers (runtime, film_type, delivery_modes) |
| Task string | Good — lists all expected outputs |

**Minor gaps:**
- No mention of what downstream agents need from the profile (constitution needs film_type, gen_planner needs budget_cap)
- The output says `"classified_input": "..."` but doesn't explain what this is — it's a prose summary of the classification

---

## 2. Constitution Agent — 🟡 Adequate

| Field | Assessment |
|-------|-----------|
| Role | Adequate |
| Core Task | Vague — "Define the theme, tone, emotional promise" — what makes a good constitution? |
| Context | Adequate — `{idea}` only, but constitution should also see the classified_input from intake |
| Constraints | Good — "specific and actionable, not vague" |
| Output | Explicit JSON template |
| Agent | Simple, works |
| Task string | Good |

**Gaps to fix:**
- **Context missing**: Should include `{classified_input}` from intake — the intake agent already classified the film type, which should constrain the constitution
- **Core task needs examples**: "For a visual_poetry film type: theme should be philosophical/abstract. For narrative: theme should be character-driven."
- **No quality bar guidance**: The constraint says "The quality bar must define measurable thresholds" but gives no examples. Add: "e.g., 'Every frame must look like a painting', 'No shot shall exceed 15 seconds', 'All characters must maintain consistent facial features'"

---

## 3. Development Agent — 🟡 Adequate

| Field | Assessment |
|-------|-----------|
| Role | Adequate |
| Core Task | Generic — "Create a Treatment and SceneList" |
| Context | Has `{constitution_content}` — correct |
| Constraints | Good — "Every scene must have dramatic function, emotional shift, conflict, outcome" |
| Output | Explicit JSON template |
| Agent | Good, handles missing act_map |
| Task string | Good |

**Gaps to fix:**
- **Scene count guidance**: For a short film, the agent should know the expected scene count. Add: "For a 1-4 minute film: 4-8 scenes. For 5-10 minutes: 8-15 scenes. For 10-20 minutes: 12-25 scenes."
- **Missing ExecutionBrief awareness**: The treatment should acknowledge target runtime. The scene list should be sized for the runtime.
- **Act map is buried**: The output template shows `act_map` inside `treatment`, but the agent parses it from `treatment.act_map`. The template should make it a top-level key.

---

## 4. Screenwriter Agent — 🟡 Adequate

| Field | Assessment |
|-------|-----------|
| Role | Adequate |
| Core Task | Generic — "Create a StoryBible and Script" |
| Context | Good — has treatment, scene_list, constitution |
| Constraints | Good |
| Output | Partial JSON template — says `"...": "... (full StoryBible schema)"` instead of actual fields |
| Agent | Good parsing |
| Task string | Good |

**Gaps to fix:**
- **Output format is incomplete**: The template says `"... (full StoryBible schema)"` — this is a placeholder, not a template. The LLM might produce wrong field names.
- **Missing scene count**: Should say "Write exactly the number of scenes from the SceneList. Do not add or remove scenes."
- **Missing runtime awareness**: The script should acknowledge target runtime. For dialogue-free films, action lines become more important.
- **No dialogue guidance**: Should say "If the constitution specifies a dialogue-free film, use action lines only, no dialogue blocks."

---

## 5. Structure Extractor Agent — 🟢 Strong

| Field | Assessment |
|-------|-----------|
| Role | Clear |
| Core Task | Excellent — formula-based derivation: `total_shots = runtime / avg_duration` |
| Context | Has `{idea}`, `{story_bible_content}`, `{script_scene_count}` |
| Constraints | Excellent — "Never fabricate", "MUST use act_1/act_2/act_3", "Shot counts MUST be positive" |
| Output | Explicit JSON template with example values |
| Agent | Good, handles coercion |
| Task string | In node, not in template |

**Minor gaps:**
- The formula says "total_shots = target_runtime / avg_shot_duration" but doesn't check that `total_shots >= scene_count` (the cross-validator catches this, but the agent should too)
- Should explicitly say: "Distribute `total_shots` shots across acts. Each act gets `shots_per_act = total_shots * (scenes_in_act / total_scenes)`. Round to nearest integer."

---

## 6. Visual Dev Agent — 🟢 Strong

| Field | Assessment |
|-------|-----------|
| Role | Clear |
| Core Task | Good — explains provider tiers (fast/standard/ultra) |
| Context | Has script, story_bible, constitution — correct |
| Constraints | Good |
| Output | Excellent — very explicit JSON template with all fields |
| Agent | Good, handles string input |
| Task string | Good |

**Minor gaps:**
- **Missing character/environment count**: Should say "Produce reference entries for every character and environment mentioned in the script."
- **Missing ExecutionBrief**: Should know the target shot count to size references appropriately.

---

## 7. Shot Bible Agent — 🟢 Strong (v3)

| Field | Assessment |
|-------|-----------|
| Role | Clear — "PRIMARY job is to produce exactly the right number" |
| Core Task | Excellent — STEP 1/2/3 with explicit count checks |
| Context | Has ExecutionBrief, script, visual refs |
| Constraints | Excellent — numbered 1-6 with COUNT FIRST |
| Output | Explicit JSON template with count comments |
| Agent | Good, handles list/dict parsing |
| Task string | Good |

**Only remaining issue**: LLMs fundamentally struggle with counting. The prompt is as good as it can be. The repair loop with feedback injection is the safety net.

---

## 8. Gen Planner Agent — 🟡 Adequate

| Field | Assessment |
|-------|-----------|
| Role | Adequate — "respecting structural requirements" |
| Core Task | Adequate — mentions ExecutionBrief but no step-by-step |
| Context | Has ExecutionBrief, shot_matrix, budget — correct |
| Constraints | Good — "Every shot must have a plan entry" |
| Output | **🔴 Weak** — just "Respond with valid JSON matching the GenerationPlan schema" — no template! |
| Agent | Good parsing |
| Task string | Good |

**Gaps to fix:**
- **Output format is missing**: Needs an explicit JSON template like the other agents have
- **No pricing data**: The constraint says "use the provider's pricing model" but the prompt doesn't include actual prices. Should include a price table
- **No step-by-step instructions**: Should be: "STEP 1: Count shots in matrix. STEP 2: Group by provider. STEP 3: Estimate per-shot cost. STEP 4: Verify clip_count matches total shots."

---

## 9. QC Synthesizer Agent — 🔴 Weak

| Field | Assessment |
|-------|-----------|
| Role | Adequate |
| Core Task | Generic — "Synthesize multiple validator reports" |
| Context | **🔴 Weak** — `{validator_report_refs}` contains REFS, not content. The actual report content isn't injected! |
| Constraints | Adequate — consensus rules |
| Output | **🔴 Weak** — "Respond with valid JSON matching the QC synthesis report schema" — no template |
| Agent | Has list/dict fix, works |
| Task string | Good |

**Critical gaps:**
- **Context is empty**: The `{validator_report_refs}` variable is just a string of ref IDs. No actual report content is loaded. The LLM has nothing to synthesize.
- **Output format missing**: Needs explicit JSON template with `reviewers[]`, `consensus_status`, `agreement_level`, etc.
- **No guidance on consensus computation**: "Agreement level: 'high' if >75% of reviewers agree, 'medium' if 50-75%, 'low' if <50%"

---

## 10. Assembly Agent — 🔴 Weak

| Field | Assessment |
|-------|-----------|
| Role | Adequate |
| Core Task | Generic — "Create an assembly plan" |
| Context | **🔴 Weak** — `{media_refs}` contains refs, not content. The actual generated media and shot matrix content aren't injected |
| Constraints | Adequate |
| Output | **🔴 Weak** — no JSON template |
| Agent | Good parsing |
| Task string | Generic (unchanged) |

**Critical gaps:**
- **Context is empty**: Same problem as QC — refs without content
- **Output format missing**: Needs explicit JSON template
- **No shot-order guidance**: Should say "Arrange clips in the order defined by shot_matrix. Transition between scenes with cuts or fades based on emotional intent."

---

## Cross-Agent Issues

### 1. Context injection gap for QC and Assembly
The `_inject_artifact_context` function loads content for known refs (constitution, treatment, script, etc.) but `validator_report_refs` and `media_refs` aren't in the artifact map. The templates reference these variables but they're empty strings.

### 2. ExecutionBrief should flow to more agents
Currently the ExecutionBrief is injected for: shot_bible, gen_planner. It should also flow to: visual_dev, screenwriter, development — so they can size their output appropriately.

### 3. Price data missing
The gen_planner needs actual provider pricing to estimate costs. Without it, cost estimates are always $0 (placeholder). Add a price table to the gen_planner context.

### 4. Output format inconsistency
Strong templates (intake, constitution, visual_dev, shot_bible) have explicit JSON output templates. Weak templates (screenwriter, gen_planner, qc, assembly) say "match the schema" without showing the schema. The LLM may guess wrong field names.

---

## Priority Fixes

| Priority | Agent | Fix |
|----------|-------|-----|
| **P0** | QC Synthesizer | Add report content to context + explicit JSON output template |
| **P0** | Gen Planner | Add explicit JSON output template |
| **P1** | Assembly | Add media/shot content to context + JSON output template |
| **P1** | Constitution | Add classified_input context + theme examples |
| **P1** | Screenwriter | Complete the output template (no `"... (full schema)"` placeholder) |
| **P2** | Development | Add scene count guidance |
| **P2** | All agents | Add ExecutionBrief context where relevant |
| **P3** | Gen Planner | Add provider pricing table to context |
