# Prep-Production Quality Review

**Branch:** `review/prep-production-quality`
**Date:** 2026-06-28
**Scope:** LangGraph implementation, prompt framework, prep-production phases
(intake → constitution → development → script → visual_dev → shot_bible), nodes,
graph construction — assessed against the stated vision: a world-class assistant
for Oscar-level movie creation.

**Symptoms reported by the user when creating new projects:**
1. Number of scenes is not enough.
2. Runtime is shorter than expected.
3. Story is not good enough.

This document explains the root causes, ranked by leverage, and proposes fixes.

---

## TL;DR

The architecture is sound — clean supervisor graph, real artifact
versioning/handoffs, genuinely excellent validator rubrics, real structural gates
(A/B/C) downstream. The problem is **not** plumbing. It is that **creative scope is
measured after the fact instead of being decided up front and enforced**, and
**the prep phases are almost entirely ungated**.

Three structural facts drive all three symptoms:

- **Scope flows backward.** The `ExecutionBrief` (shot count, runtime, pacing) is
  *reverse-engineered from the already-written story* by the structure extractor at
  the **shot_bible** phase. So a thin story produces a thin brief, and every
  downstream gate then faithfully enforces the thin brief. The runtime/scene targets
  never get a chance to shape the story — they only describe it.
- **Prep is ungated.** Gates A/B/C only cover `shot_bible`, `gen_planning`,
  `generation`. The phases that actually determine scene count and story quality —
  `constitution`, `development`, `script` — have **no blocking validators at all**.
  The script validators exist and are good, but they only run in the **qc** phase,
  long after the script is approved and downstream work is built on it.
- **The one prep gate that exists is told to be lenient.** The orchestrator review
  (the only autonomous quality check during prep) is instructed verbatim: *"Do not
  reject output just because a number is lower than some formula… If the content is
  rich enough despite fewer scenes, approve it."* It is single-model, gives "ONE
  focused suggestion," and caps at 3 rounds.

Net effect: ranges get satisfied at the floor, nobody raises the floor, and the
only reviewer is instructed to wave thin work through.

---

## Symptom 1 — "Number of scenes is not enough"

### Root causes

1. **Range prompts are satisfied at the minimum.** `_development_creator`
   (`defaults.py:259`) instructs: `4-10 min film → 8-15 scenes`. LLMs reliably pick
   the low end of an open range. A 5-minute film gets 8 scenes, not 12-15. Nothing
   pulls it up.

2. **No scene-count floor enforced in code.** `DevelopmentAgent.validate()`
   (`development_agent.py:85`) only checks `len(scene_list.scenes) > 0`.
   `ScreenwriterAgent.validate()` (`screenwriter_agent.py:163`) only checks
   `len(script.scenes) > 0`. Neither relates scene count to runtime.

3. **The only scene-count check fires too late and the wrong direction.**
   `validate_execution_brief` raises `brief_shots_less_than_scenes` only at
   shot_bible, and it enforces `total_shots >= scene_count` — i.e. it *locks in* the
   low scene count rather than questioning it. There is no check anywhere that scene
   count is *sufficient* for the runtime.

4. **Scenes can be silently dropped between development and script.** The
   screenwriter re-derives its **own** `scene_list` (`screenwriter_agent.py:91`)
   independently of the development `SceneList`. There is no validation that
   `script scene count == development scene count`. Scenes vanish with no alarm.

5. **Sizing is film-type/pacing-blind.** A 5-minute dynamic thriller (~40 shots) and
   a 5-minute visual poem (~24 shots) collapse to the same "8-15 scenes" guidance.
   Scene density should be a function of `runtime × film_type × pacing`.

---

## Symptom 2 — "Runtime is shorter than expected"

### Root causes

1. **The runtime target is an intake guess that nothing downstream is obligated to
   fill.** Intake estimates `target_runtime_seconds`. The structure extractor then
   computes `total_shots = runtime / avg_shot_duration` — but it does so *from the
   thin story*, distributing shots "proportional to each act's scene count." Few
   scenes → few shots → the shot matrix sums to a short runtime, and Gate A's ±10%
   tolerance is measured against a target the brief already deflated.

2. **`_coerce_runtime_seconds` silently rewrites to 300s** on weak output
   (`intake_agent.py:62`). If the user expected longer, the floor caps perception,
   and the value is never re-examined against story scope.

3. **Pacing durations exceed provider clip limits.** The pacing model uses
   `slow_cinema → 12.5s avg`, `standard → 7.5s` (`defaults.py`,
   `orchestrator_validators.py:120`). Seedance/Veo clips are typically ≤ 8-10s, so
   long "single shots" cannot be generated as one clip — they get truncated or split,
   shrinking effective runtime versus the plan. The pacing model and the provider
   capabilities are not reconciled.

4. **Compounding shrinkage.** Thin scenes → conservative shots-per-scene → durations
   nudged down to satisfy "match the brief" → final cut well under the intended
   runtime. Each step is individually "valid"; the product of them is short.

---

## Symptom 3 — "Story is not good enough"

### Root causes

1. **The deep-craft prep agents are orphaned.** `character_bible_agent.py`,
   `environment_bible_agent.py`, `camera_bible_agent.py`, `style_bible_agent.py`
   exist but are **not in `AGENT_CLASS_BY_ID`** (`impl/registry.py`) and **not wired
   into the graph**. So there are **no character dossiers, no environment bible, no
   style bible, no camera bible**. The screenwriter writes dialogue with zero
   character grounding.

2. **A flagship validator is inert because its inputs never exist.** The
   `dialogue-voice` validator (`defaults.py:806`) is excellent — but its prompt
   consumes `{character_dossiers}` and the `must_not_change` traits. Those artifacts
   are never produced, so on real data the validator has nothing to check against.

3. **Quality is one-shot.** Development and script are each a single LLM pass. There
   is no beat-sheet stage, no "deepen subtext" pass, no expansion loop. The only
   iteration is the orchestrator revise loop — capped at 3 rounds, limited to "ONE
   focused suggestion," and explicitly lenient.

4. **Script craft is checked in the wrong place.** `ScriptStructureValidator` and
   `DialogueVoiceValidator` (both with strong rubrics) only run inside `qc_node`
   (`nodes.py:1300`, gated on `phase in ("script","qc")` but only *invoked* from QC).
   By the time QC runs, the script was approved phases ago and visual_dev/shot_bible
   are built on top of it. Findings can't cleanly gate the script.

5. **Creators don't get the rubrics the validators grade them against.** The
   validators know exactly what "good" means (conflict presence, voice
   differentiation, subtext, organic exposition). The *writing* prompts never state
   these standards — so the writer isn't aiming at the target it will be judged on.

6. **Fidelity loss through compaction.** Upstream artifacts are compacted to
   `DEFAULT_MAX_CONTEXT_CHARS` (`nodes.py:_inject_artifact_context`); the
   orchestrator only sees theme/tone + 200 chars of visual language. Rich creative
   nuance from the constitution is truncated before it reaches the screenwriter.

7. **The screenwriter re-derives the treatment** (`treatment_text`, `act_map`, a
   second `scene_list`) instead of honoring development's — inviting drift between the
   approved treatment and the script.

8. **Generic "quality = length" directive.** `_QUALITY_DIRECTIVE` rewards verbosity
   ("aim for 150+ words per creative field") rather than dramatic craft.

---

## What is already strong (preserve these)

- Clean supervisor graph with per-phase approval gates and a real human-interrupt
  path (`graph.py`, `await_approval_node`).
- Real artifact store with versioning, `built_from` dependency tracking, and
  idempotent handoff records (`_save_artifact`, `_record_handoff`).
- Genuinely excellent validator rubrics — these are the best creative asset in the
  codebase and should drive the *creation* prompts too.
- Real structural gates A/B/C downstream with sensible tolerances.
- Matrix-patch model for incremental row updates is clean and auditable.

---

## Recommendations (ranked by leverage)

### R1 — Flip scope from backward-measured to forward-contract *(highest leverage)*
Compute a **Story Scope Contract** at intake/constitution time from
`runtime × film_type × pacing`: target scene count (a concrete number, not a range),
beats per act, target shots, and shots/scene band. Persist it as a first-class
artifact. Make `development` and `script` **fill the contract**, and make the
existing structure extractor *consume* it instead of re-deriving structure from the
finished story. This single change addresses Symptoms 1 and 2 at the source.

### R2 — Add blocking gates to the prep phases
Introduce a `development`/`script` structural gate (analogous to Gate A) that blocks
when scene count is under the contract, when script scene count ≠ development scene
count, or when projected runtime (scenes × expected shots × avg duration) falls below
target. Run `ScriptStructureValidator` and `DialogueVoiceValidator` **at the script
phase**, not only at QC.

### R3 — Make sizing concrete and film-type aware
Replace open ranges in `_development_creator` with a single target number derived
from the contract, plus a hard minimum. Provide a per-`film_type`/`pacing` density
table rather than one global range.

### R4 — Wire in the orphaned craft agents
Register and sequence `character-bible`, `environment-bible`, `style-bible`,
`camera-bible` between constitution and script (or as a parallel "story bible"
subgraph). This makes the `dialogue-voice` validator real and grounds the
screenwriter. Addresses Symptom 3 directly.

### R5 — Rebalance the orchestrator review
Remove the "do not reject because a number is lower than a formula" instruction for
prep phases; let the contract be enforced as blocking. Reserve the lenient,
content-over-count judgment for genuinely subjective calls, not for scene-count
shortfalls. Consider the `multi_model_panel` review strategy (already in the festival
profile) for the **story**, not just clips.

### R6 — Give creators the graders' rubrics
Inject the validator rubrics (conflict, voice differentiation, subtext, organic
exposition) into the development and screenwriter prompts as explicit targets, and
replace "150+ words" with craft criteria.

### R7 — Reconcile pacing durations with provider clip limits
Cap per-shot duration in the pacing model to what providers can actually generate as
a single clip, or model multi-clip shots explicitly so planned runtime survives
generation.

### R8 — Reduce fidelity loss
Raise/relax compaction for the constitution and treatment on the critical creative
path, or pass key creative fields verbatim rather than summarized.

---

## Suggested sequencing

1. **R1 + R2 + R3** together — they share the Story Scope Contract artifact and fix
   Symptoms 1 & 2 at the root.
2. **R4 + R6** — depth and grounding for Symptom 3.
3. **R5 + R7 + R8** — polish and consistency.

Each step should land with unit + integration tests per the product standard
(`documentation/product-completion/00-product-standard.md`): "Claims without behavior
tests do not count as evidence."

---

## Key file references

| Concern | File |
| --- | --- |
| Graph construction & phase wiring | `src/film_pipeline/graph/graph.py` |
| Phase nodes / agent lifecycle | `src/film_pipeline/graph/nodes.py` |
| Prompt framework (all templates) | `src/film_pipeline/agents/prompt_templates/defaults.py` |
| Scene-count sizing | `defaults.py` `_development_creator` |
| Runtime/shot math | `defaults.py` `_structure_extractor`; `orchestrator_validators.py` |
| Prep gates (A/B/C only) | `src/film_pipeline/graph/orchestrator_validators.py` |
| Orchestrator review leniency | `defaults.py` `_orchestrator_review` |
| Wired vs orphaned agents | `src/film_pipeline/agents/impl/registry.py` |
| Runtime coercion floor | `src/film_pipeline/agents/impl/intake_agent.py` |
