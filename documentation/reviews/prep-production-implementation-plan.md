# Prep-Production Implementation Plan

**Branch:** `review/prep-production-quality`
**Date:** 2026-06-28
**Companion docs:** `prep-production-quality-review.md` (root-cause analysis),
`hardcoded-values-inventory.md` (evidence)

**Goal:** fix the three reported symptoms (too few scenes, runtime too short, story
not good enough) at the root by replacing "measure the story after the fact" with a
**forward, profile-driven, user-anchored Scope Contract**, and by removing dead
config so profiles mean what they say.

**Guiding decisions (confirmed with the user):**
- **Runtime is user input.** The operator supplies the expected length *with the
  idea*. It is the single authority. No profile constant, no LLM guess, no silent
  300s fallback overriding it.
- **Profiles drive *how* the runtime is filled** (film_type, pacing, structure),
  not the length itself.

---

## Architecture: the Story Scope Contract

A new first-class artifact computed **before development**, deterministic (pure
function, not an LLM call), from three inputs:

```
StoryScopeContract = f(
    target_runtime_seconds,   # USER INPUT (authority)
    film_type,                # PROFILE
    pacing,                   # PROFILE
)
```

It outputs concrete targets that downstream phases must **fill** (not be measured
against afterward):

```
StoryScopeContract:
  target_runtime_seconds: int        # echoed from user input
  film_type: str
  pacing: str
  movement_count: int                # from story_structure (not hardcoded 3)
  target_scene_count: int            # concrete number, not a range
  min_scene_count: int               # hard floor (blocking)
  target_shot_count: int             # runtime / avg_shot_duration(pacing)
  shots_per_scene_band: [int, int]
  avg_shot_duration_seconds: float   # single source of truth, from pacing
```

The existing `ExecutionBrief` stops being *reverse-engineered from the finished
story* and instead is **derived from / reconciled against** the contract. Flow flips
from backward (measure) to forward (contract → fill → verify).

---

## Workstreams

### WS-A — Runtime as user input  *(unblocks everything)*
- Add `target_runtime_seconds` (and an accepted `target_runtime_minutes` /
  natural-language convenience) to the input path:
  - `app/services/models.py` → `ProjectCreateRequest`, `submit_idea` signature.
  - `app/services/operator.py` → `create_project` / `submit_idea` seed
    `state["target_runtime_seconds"]` **before** `run_graph`.
  - `mcp/tools/__init__.py` → `create_film_project` / `submit_idea` accept the arg.
  - TUI submit path (`tui/`) → optional length prompt.
- Intake **honors** the seeded value: `intake_agent` uses it as authority; prose
  parsing only as a fallback when no explicit value is given; remove the silent
  `300` override of operator intent.
- Remove `target_runtime_seconds` from `film-type.*.yaml` (dead config).
- **Tests:** explicit length flows end to end; prose fallback; no-value behavior is
  an explicit error or documented default (not a silent 300).

### WS-B — Scope Contract artifact + density model
- New schema `schemas/scope_contract.py` (`StoryScopeContract`).
- New `graph/scope_contract.py` — pure derivation function + a **single** config
  table keyed by `film_type × pacing` (replaces the duplicated `pacing_avgs` dicts
  and the prose scene ranges). Table lives in a profile-readable place so it can be
  tuned without code edits.
- Compute the contract in a new step at the end of intake / start of constitution;
  persist as an artifact; put a ref in state.
- Unify the **pacing vocabulary** (profile `pacing` ↔ code `pacing_style`) and make
  it profile-driven instead of an LLM default.
- **Tests:** derivation is deterministic per (runtime, film_type, pacing);
  table-driven cases for each film_type; golden values.

### WS-C — Make development & script *fill* the contract
- Inject contract targets into the development and screenwriter prompt context
  (concrete numbers, not ranges). Replace `defaults.py` sizing block and the
  "150+ words" directive with contract-driven targets + the validator rubrics
  (conflict, voice, subtext) as explicit creative goals.
- `development_agent.validate()` / `screenwriter_agent.validate()` check scene count
  against `min_scene_count`.
- **Tests:** prompt context contains the right numbers; agent validate() rejects
  under-floor output.

### WS-D — Blocking prep gates (new Gate "S")
- New validators in `orchestrator_validators.py` (or a sibling) run at
  `development` and `script` phases:
  - scene count ≥ `min_scene_count` (blocking).
  - script scene count == development scene count (blocking — stops silent drops).
  - projected runtime (scenes × shots/scene × avg duration) within tolerance of
    target (blocking).
- Wire them into `development_node` / `script_node` like Gate A in `shot_bible_node`,
  and run `ScriptStructureValidator` + `DialogueVoiceValidator` **at the script
  phase**, not only QC.
- Structure extractor consumes the contract instead of re-deriving structure.
- **Tests:** integration — thin dev/script output produces blocking issues and
  routes to repair; on-target output advances.

### WS-E — Variable act/movement structure  *(schema-touching — decision required)*
- Replace the fixed 3-field `ActMap` with a list-based movement model driven by
  `story_structure` (three_act → 3, montage/free_form → N), so visual_poetry and
  experimental profiles become real.
- Touches: `schemas/story_bible.py`, `execution_brief.py`, both prep agents, the
  prompts, and the movement-count validators.
- **Larger blast radius** — recommend as a *second* PR after A–D land, behind a
  decision: keep 3-act-only for now, or generalize.

### WS-F — Tidy dead config
- For `dialogue_weight` / `visual_style` / `camera_default`: either wire into the
  relevant prompt context (preferred — they're cheap signal) or remove from profiles.
- Source runtime tolerances and validation thresholds from the quality profile.

### WS-G — Config-driven model routing  *(highest single quality lever)*
**Why outcome-relevant:** every creative agent currently runs on the same hardcoded
model (`deepseek/deepseek-chat`) at a fixed temperature, and the `models:` sections
in profiles are dead (`ModelRouter()` is always built with no args). Model choice per
task is the biggest under-used quality lever for Oscar-level writing.
- Make `ModelRouter` read `resolved_config["models"]` (profile-driven), falling back
  to the current defaults only when unspecified. Wire it at `graph/services.py:49,72`
  and `mcp/tools/__init__.py:2481`.
- Let the quality profile raise the model tier for the high-value creative agents
  (constitution, treatment, screenwriter) — e.g. festival → a top model, draft →
  cheap. Keep `_AGENT_PROFILE_MAP` but make the profile→model mapping config-driven.
- **Tests:** a profile that sets a different model actually changes the resolved
  model id for the screenwriter; default behavior unchanged when unset.

### WS-H — Single-source pricing  *(cost correctness)*
- One pricing table shared by the provider adapters **and** the planner prompt, so
  planned cost == charged cost. Remove the divergent `$0.50` vs `$0.10` Veo figures
  (`defaults.py:582` vs `adapters/veo_fast.py:69`). Inject the table into the planner
  prompt context instead of hardcoding prices in prose.
- **Tests:** planner cost estimate matches adapter `estimate_cost()` for the same shot.

### WS-I — Fail loud on the critical creative path  *(reveals hidden quality failures)*
**Why outcome-relevant:** ~18 broad `except` blocks in `nodes.py` silently swallow
failures. A swallowed error in `_inject_artifact_context` means an agent runs
*context-blind* (e.g. screenwriter with no constitution) and no one is told — a
plausible hidden cause of "story not good enough."
- On the critical creative path (constitution/treatment/script context injection),
  failures must surface as a blocking issue or hard error, not `except: pass`.
- Keep best-effort swallowing only for genuinely optional enrichment (e.g. metrics
  summaries), and log there instead of silently passing.
- **Tests:** a missing/corrupt upstream artifact on the critical path produces a
  visible blocking issue, not silent empty context.

### WS-K — Prompt craft overhaul (creator prompts)
**Why outcome-relevant:** the validator prompts have vivid expert personas and sharp
rubrics; the *creator* prompts (constitution, treatment, screenwriter, shot-bible)
are bland and reward length over craft. The agents that make the film got the
weakest prompts. Pairs with WS-G — a strong prompt on a strong model is what moves
story quality most.
- Give creative agents vivid expert personas (match the quality of the validator
  roles).
- Replace the "150+ words per field" directive with the validator rubrics restated
  as positive creation targets (conflict, voice differentiation, subtext, organic
  exposition).
- Operationalize the constitution: every downstream creative prompt must explicitly
  honor `character_truths` and never commit a `taboo_mistake`.
- Condition prompts on `film_type` / `pacing` so style reaches the writer.
- Move bulky inline JSON to a schema reference; spend the freed tokens on craft.
- De-hedge constraints (remove "where appropriate", "should", etc. — the same
  hedges the prompt-readiness validator blocks).
- Add 1–2 few-shot exemplars (great vs weak) for the screenwriter and constitution.
- Once the Scope Contract exists (WS-B), drop the LLM arithmetic from the
  structure-extractor / shot-bible prompts and let them focus on craft.
- **Tests:** template rendering includes persona + rubric + constitution taboos;
  existing schema-parse tests still pass (output_format contract unchanged).

### WS-J — Run the multi-model review the profiles already request
**Why outcome-relevant:** `base.studio`/`festival` profiles ask for
`multi_model_panel` with `min_reviewers: 2–3`, but prep review is single-model — the
quality gate you think exists isn't running. Also raise context fidelity for the
constitution/treatment so creative intent does not decay before the writer sees it.
- Honor `review.strategy` / `min_reviewers` for the **story** phases (constitution,
  development, script), producing a real consensus over multiple models.
- Stop truncating the constitution/treatment on the critical creative path (relax
  compaction or pass key fields verbatim).
- **Tests:** festival profile runs N reviewers on the script and blocks on
  disagreement; constitution content reaches the screenwriter un-truncated.

---

## Sequencing & PRs (ordered by outcome value)

Every workstream below changes the film that comes out. Pure code-quality refactors
(deepcopy-per-node, services-contextvar smuggling, agent-id naming, dead validator
branches, MemorySaver vs git checkpointer) are **explicitly deferred** — they do not
affect the output and can follow later.

1. **PR1 — WS-A** (runtime as user input). Small, unblocks everything; fixes "wrong
   length" at the source.
2. **PR2 — WS-B + WS-C + WS-D** (Scope Contract + enforcement). Core fix for "too few
   scenes" and "runtime too short." Shares one artifact, lands together.
3. **PR3 — WS-G** (config-driven model routing). Highest single quality lever for
   "story not good enough" — lets the screenwriter run on a top model per profile.
4. **PR4 — WS-I + WS-J** (fail loud on the creative path + run the multi-model review
   the profiles already request). Surfaces hidden quality failures and strengthens
   the gate.
5. **PR5 — WS-H + WS-F** (single-source pricing for cost correctness; tidy remaining
   dead config / profile-driven tolerances).
6. **PR6 — WS-E** (variable act structure) *if* we decide to generalize beyond 3 acts.
7. **Follow-on (separate plan)** — deeper "story" craft: wire in the orphaned
   character/environment/style/camera-bible agents and rebalance the lenient
   orchestrator review prompt. Tracked in the review doc.

If forced to pick three for maximum outcome impact: **PR1, PR2, PR3.**

---

## Definition of done (per product standard)

Each PR lands with unit + integration tests and, where operator-visible, an E2E
scenario — per `documentation/product-completion/00-product-standard.md`:
"Claims without behavior tests do not count as evidence." Specifically:
- A 5-minute idea + `film-type.narrative` produces a scene count and projected
  runtime that match the contract within tolerance — proven by an E2E test, not a
  prompt nudge.
- Selecting `film-type.visual_poetry` vs `narrative` produces measurably different
  scope (scene count / shot duration), proving the profile is no longer dead.

---

## Open decisions for the user

1. **WS-E (variable acts):** generalize the 3-act schema now, or keep 3-act and
   defer? (Affects whether montage/free_form profiles ever work.)
2. **No-runtime behavior:** if the operator omits the length, hard error or fall back
   to a documented per-film_type default?
3. **Depth follow-on (R4/R5):** include the craft-agent wiring + orchestrator
   rebalance in this effort, or schedule as a separate initiative?
