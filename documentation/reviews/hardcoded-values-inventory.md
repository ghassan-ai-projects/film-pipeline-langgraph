# Hardcoded Values & Dead-Config Inventory

**Branch:** `review/prep-production-quality`
**Date:** 2026-06-28

This audit answers: "what creative/structural values are hardcoded, and which
profile fields are silently ignored?" It is the evidence base for the
implementation plan (`prep-production-implementation-plan.md`).

The recurring pattern: **profiles advertise creative intent, but the code reads an
LLM guess (or a hardcoded constant) instead.** The profile values are merged into
`resolved_config` and then never read.

> **Re-verified 2026-08-26** against `src/` on branch `clean-code-followups`
> (post 240-file sweep + phase-2 fixes). Original findings are kept below for
> history; each section carries a dated re-check note and corrected file/line
> citations. Headline changes: runtime is now user input and gone from profiles;
> pacing/shot-density moved to a single source (`graph/scope_contract.py`);
> pricing moved to a single source (`providers/pricing.py`); model routing gained
> a per-profile config override channel; intake's magic `300` fallback was
> collapsed (the named constant `_FALLBACK_RUNTIME_SECONDS` now lives only in
> `agents/impl/structure_extractor_agent.py`). See
> `prep-production-implementation-plan.md` for the workstreams that landed.

---

## A. Dead profile config (loaded into `resolved_config`, never read)

Verified by grepping every field across `src/`:

| Profile field | Where it's declared | Reads in `src/` | Status |
| --- | --- | --- | --- |
| `target_runtime_seconds` | `film-type.*.yaml` | 0 reads from config | **DEAD** — runtime comes from intake LLM (`intake_agent._coerce_runtime_seconds`), profile value ignored |
| `film_type` | `film-type.*.yaml` | re-derived by LLM | **DEAD** — `intake_agent._coerce_film_type(data.get("film_type"))` reads the model output, not the profile |
| `pacing` | `film-type.*.yaml` | 0 (vocab mismatch) | **DEAD** — profile says `character_driven`/`meditative`/`irregular`; code uses `slow_cinema`/`standard`/`dynamic` from the structure-extractor LLM, default `"standard"` |
| `story_structure` | `film-type.*.yaml` | 1 (unfilled placeholder) | **DEAD** — only appears as `{story_structure}` in the assembly-validator template; never populated |
| `dialogue_weight` | `film-type.*.yaml` | 0 | **DEAD** |
| `visual_style` | `film-type.*.yaml` | 0 | **DEAD** |
| `camera_default` | `film-type.*.yaml` | 0 | **DEAD** |
| `writing_style` | `film-type.*.yaml` | 2 (conflict check only) | **PARTIAL** — only used by `config/validator.py` to flag a poetry+dialogue conflict; never shapes output |

**2026-08 re-check (verified against `src/`):**
- `target_runtime_seconds` → **RESOLVED**: removed from all `profiles/film-type.*.yaml`;
  runtime is user input (`submit_idea` hint, `mcp/tools/intake.py:14-17`) and
  user-supplied values are authoritative in prep (`graph/nodes/prep.py`, `_coerce_user_runtime`).
- `pacing` → **RESOLVED**: read from resolved config (`scope_contract.pacing_from_config`,
  `graph/scope_contract.py:129-134`) and mapped to canonical styles via the alias table
  (`:33-46`); canonical vocabulary centralized in `schemas/constraints.py:61`.
- `film_type` → **largely unchanged**: intake still coerces the LLM guess
  (`agents/impl/intake_agent.py:45`); the profile value is merged into constraints only when
  extraction supplied none (`graph/nodes/prep.py:100-101`).
- `story_structure` → **still dead**: the `{story_structure}` placeholder
  (`agents/prompt_templates/defaults/validators.py:292`) has no writer anywhere in `src/`.
- `dialogue_weight`, `camera_default` → **still dead** (0 reads outside schema definitions).
- `visual_style` → profile field **still unread**, but a sibling now exists: a heuristic
  extractor derives a visual style from the idea text (`constraints/extractor.py:149,244`) —
  from user prose, not the profile.
- `writing_style` → **unchanged**: conflict check only (`config/validator.py:42-43`).

**Implication:** choosing `film-type.visual_poetry` vs `film-type.narrative` changes
almost nothing in the actual generation. The look/pacing/structure come from
per-idea LLM guesses, not the profile the operator selected.

---

## B. The three-act lock (schema-level hardcode)

`ActMap` (`schemas/story_bible.py:24`) has exactly three fixed fields:

```python
class ActMap(SchemaBase):
    act1_setup: str
    act2_confrontation: str
    act3_resolution: str
```

This makes a 3-act structure **structurally impossible to escape**, even though
profiles advertise other structures:
- `film-type.visual_poetry.yaml` → `story_structure: montage`
- `film-type.experimental.yaml` → `story_structure: free_form`

Neither can be represented. The hardcode is reinforced in many places:
- Prompts: "the StoryBible has **exactly 3 acts**" and forced `act_1/act_2/act_3`
  movement ids (`defaults.py:62`, `:95`, `:512`).
- Validators: `validate_execution_brief` treats `< 2` movements as blocking and
  `> 5` as "suspicious" (`orchestrator_validators.py:92,100`), and cross-checks the
  three fixed act fields (`:168`).
- Agents: `development_agent.py:53`, `screenwriter_agent.py:82` hardcode the three
  field names.

**2026-08 re-check:** still fully accurate structurally — `ActMap` is unchanged at
`schemas/story_bible.py:24`. File/line citations moved with the prompt-template and
validator-package splits: the forced act ids now live in
`agents/prompt_templates/defaults/spine.py:29-31`, `:64`, `:84-96` and
`.../production.py:130-131`, `:154`; the `< 2` / `> 5` movement bounds are
`graph/orchestrator_validators/brief.py:57`, `:65` and the act-field cross-check is
`brief.py:98-112`; the hardcoded field names are `agents/impl/development_agent.py:28-30`
and `agents/impl/screenwriter_agent.py:109-111`.

---

## C. Magic numbers (creative constants buried in code)

| Value | Location | Notes |
| --- | --- | --- |
| Shot-duration averages `{slow_cinema:12.5, standard:7.5, dynamic:3.5}` | `orchestrator_validators.py:120` **and** `defaults.py:70` | **Duplicated** in code + prompt → drift risk. Not profile-driven. Exceeds provider single-clip limits (~8-10s). |
| Scene-count ranges `4-8 / 8-15 / 12-25` | `defaults.py:274` | Open ranges, satisfied at the floor. Not film-type aware. |
| Runtime tolerance `±20%` (brief), `±10%` (shot structure) | `orchestrator_validators.py:124,260` | Hardcoded; should relate to quality profile. |
| `300` runtime fallback (×2) + `"300"` default | `intake_agent.py:80,82`, `nodes.py:96` | Silent fallback can override operator intent. |
| Stall `max_rounds` = **5** default but called with **3** | `orchestrator_state.py:260` vs `nodes.py:1855` | Inconsistent convergence cap. |
| Word floor "150+ words per creative field" | `defaults.py:24` | Rewards verbosity, not craft. |
| Theme count "3-5 themes" | `defaults.py:269` | Hardcoded. |
| Movement bounds `< 2` block / `> 5` suspicious | `orchestrator_validators.py:92,100` | Encodes the 3-act assumption. |
| Validation thresholds default `85/75/60` | `validation/thresholds.py` | Profiles define `validation.thresholds`; needs verification that resolved-config values actually reach the validators (suspected partial wiring). |

**2026-08 re-check (verified against `src/`):**
- Shot-duration averages → **RESOLVED**: the duplicated dicts are gone; one density
  table now lives in `graph/scope_contract.py:26-30` (`slow_cinema 9.0 / standard 6.5 /
  dynamic 4.0`, deliberately capped ≤ ~9 s so a shot maps to a single provider clip)
  and is shared with the orchestrator validators via `avg_shot_duration_for`
  (`scope_contract.py:119-126`) — no more code-vs-prompt drift.
- Scene-count ranges → **RESOLVED**: scene targets derive from runtime ÷
  seconds-per-scene with an 80% minimum-scene floor (`scope_contract.py:57-58,95-96`);
  an explicit user scene count overrides the derivation and is held exactly (`:90-93`).
- Runtime tolerance → **still hardcoded**, new locations:
  `graph/orchestrator_validators/brief.py:83` (±20%) and
  `.../prep_gates.py:111` (±10%).
- `300` runtime fallback → **partially resolved**: intake's two occurrences were
  collapsed (commit R-106); the surviving fallback is the named constant
  `_FALLBACK_RUNTIME_SECONDS = 300`
  (`agents/impl/structure_extractor_agent.py:16`, used at `:99`, `:123`). The
  `"300"` string default persists at `graph/nodes/_context.py:70`.
- Stall `max_rounds` 5 vs 3 → **still true**: `graph/orchestrator_state.py:260`
  (default 5) vs `graph/nodes/_repair_loop.py:72` (called with 3).
- Word floor "150+ words" → **RESOLVED**: removed; no trace in `src/`.
- Theme count "3-5 themes" → **still hardcoded**:
  `agents/prompt_templates/defaults/spine.py:266`.
- Movement bounds → **still true**, locations updated (see Section B re-check).
- Validation thresholds → **clarified**: defaults are now a four-status contract —
  pass ≥ 85 / pass-with-notes ≥ 75 / needs-revision ≥ 65 / blocked < 65
  (`schemas/registries/validator_registry.py:17-19`), and several validators pass
  explicit stricter sets (e.g. delivery completeness 90/80/80,
  `validation/impl/delivery_completeness.py:114`). The suspected partial wiring is
  confirmed: no code path feeds resolved-config `validation.thresholds` into the
  validators, so profile-defined thresholds still would not take effect.

---

## E. Model routing — fully hardcoded (largest dead-config surface)

`ModelRouter` is **always constructed with no arguments** in every production path
(`graph/services.py:49,72`, `mcp/tools/__init__.py:2481`), so it always uses the
module-level constant `_DEFAULT_PROFILES` (`agents/model_routing/__init__.py:14`).
The module docstring claims *"Model profiles are loaded from config"* — that is
**not true** in any wired path.

Hardcoded in that dict (8 profiles):
- **Model IDs** — `deepseek/deepseek-chat` (primary for creative/strict/schema) and
  `google/gemini-3-flash-preview` (primary for visual/ops/draft). Changing the model
  requires a code edit.
- **Temperatures** — `creative_writer 0.7`, `cheap_draft 0.8`, `visual_reasoner 0.3`,
  `operations_triage 0.2`, `strict_validator 0.1`, `schema_enforcer 0.0`, …
- **Token limits** — `8192` (creative) / `4096` (all others).
- `top_p 0.95`, `frequency_penalty 0.3`.

Consequences:
- The `models:` sections in `mock-demo.yaml`, `local-real-provider.yaml`, and the
  `review_models:` / `quality.*` model configs are **DEAD** — never reach the router.
- The agent→profile mapping `_AGENT_PROFILE_MAP` (`graph/nodes.py:46`) is also a
  hardcoded dict.
- Retry temperature `0.1` is hardcoded in `agents/runner.py:219,270`;
  `model_adapter.py` defaults to `temperature 0.7` / `0.2` and `max_tokens 4096`.

**2026-08 re-check (verified against `src/`):** partially superseded by WS-G
(config-driven routing). A real override channel now exists:
`_model_overrides_for` reads `resolved_config["model_profiles"][<profile>]`
(`graph/nodes/_context.py:405-418`) and every agent call threads it into
`ModelRouter.resolve_model_params` (`graph/nodes/_agent.py:149-158`,
`agents/runner.py:176`), so per-profile model / temperature / token changes no
longer require a code edit. Caveats: base profiles still come from the in-code
`_DEFAULT_PROFILES` and routers are still constructed with no arguments
(`graph/services.py:76,94`, `mcp/tools/reference_generation/composites.py:226`);
the agent→profile mapping moved to `graph/nodes/_context.py:27`; retry
temperature 0.1 is now at `agents/runner.py:254,275`; `model_adapter.py` defaults
are unchanged. Quality-profile `models:` lists are read only as a real-mode
allowlist (`mcp/tools/helpers.py:142-146`); `FILM_PIPELINE_MODEL_OVERRIDE`
writes `models.creative_writer.primary` (`config/runtime_overrides.py:16`) but
nothing reads that path back into the router.

## F. Provider pricing — hardcoded rates

| Rate | Location |
| --- | --- |
| Seedance `$0.18/s` | `providers/factory.py:107`, `adapters/seedance_openrouter.py:161` (duplicated), and again in the planner prompt `defaults.py:582` |
| Veo `$0.10/s` "placeholder rate" | `providers/factory.py:109`, `adapters/veo_fast.py:69` |
| Imagen `$0.02` / `$0.05` per image | `adapters/imagen4_gemini.py:154-155` |
| Planner-prompt price list (`Seedance $0.18`, `Veo 3.1 Fast $0.50`, `Veo Lite $0.25`, `Imagen $0.02`) | `defaults.py:582` — **disagrees** with the adapter rates above |

The prompt's price list and the adapter rates are **inconsistent** ($0.50 vs $0.10
for Veo), so planned cost and charged cost will diverge.

**2026-08 re-check (verified against `src/`):** resolved by WS-H — single-source
`providers/pricing.py` (`PROVIDER_PRICING`, `rate_for`, `pricing_prompt_block`).
The factory delegates (`providers/factory.py:107-110`), Seedance's `estimate_cost`
delegates to `rate_for("seedance-openrouter")`
(`adapters/seedance_openrouter.py:162-164`; `$0.18` survives only as docstring
prose at `:4`), Veo delegates (`adapters/veo_fast.py:65-67`), and the planner no
longer carries a hand-written price list — it renders
`pricing_prompt_block()` into prompt context
(`graph/nodes/_agent_prompt_context.py:51-53`), eliminating the $0.50-vs-$0.10
disagreement. Residual gap: `adapters/imagen4_gemini.py:158-165` still returns
literal tiered rates (`$0.10` ultra / `$0.02` fast / `$0.05` default) while the
central table lists Imagen at a flat `$0.02` — the ultra/default tiers are not in
the single source.

## G. Generation / image constants

| Value | Location |
| --- | --- |
| Min resolution `512px` | `generation/frame_heuristics.py:53`, prompt `agents/prompt_templates/defaults/validators.py:196` *(re-pointed 2026-08-26; was `:63` / `defaults.py:939`)* |
| `maxOutputTokens 1024` (frame/sheet reviewers) | `generation/gemini_client.py:40` *(moved to the shared Gemini call site; was cited at `frame_reviewer.py:206` / `sheet_reviewer.py:196` — per fleet flag R-056)* |
| Reviewer temperature `0.2` | `generation/gemini_client.py:40` *(same single call site as above)* |
| Default `quality_score 80.0` in reference template | `agents/prompt_templates/defaults/production.py:60` *(was `defaults.py:446`)* |
| Negative-prompt / expression text blocks | `generation/prompt_builder.py:15,20,24,40` (hardcoded craft text) *(was `:16,32,351`)* |
| `re_anchor_every_n_clips`, drift rules | profile-defined in `base.studio.yaml`; verify they reach the generation loop — *2026-08 verification: still declared (`profiles/base.studio.yaml:43-47`) but no consumer anywhere in `src/film_pipeline/generation/`; confirmed **not** reaching the generation loop* |

## D. Recommended disposition

For each, the choice is **make it live (profile-driven)** or **delete it (remove the
false promise)**:

1. **Runtime** → remove from profiles entirely; becomes **user input** (see plan). *(done — WS-A)*
2. **film_type** → make the operator-selected profile value authoritative; intake
   may *confirm* but not silently override. *(open — see Section A re-check)*
3. **pacing** → unify vocabulary, make profile-driven; derive shot-duration band
   from it via a single source of truth (delete the duplicated dicts). *(done — `graph/scope_contract.py`)*
4. **Shot-duration table / scene-density table** → one config-driven table keyed by
   `film_type × pacing`, replacing the magic numbers and open ranges. *(done in code, keyed by canonical pacing — `scope_contract._DENSITY`; not profile-configurable)*
5. **Tolerances / thresholds** → source from the quality profile. *(open — still hardcoded, see Section C re-check)*
6. **Act structure** → introduce a variable movement model driven by
   `story_structure` (larger, schema-touching — flagged as its own workstream). *(open)*
7. **Dead fields with no consumer** (`dialogue_weight`, `visual_style`,
   `camera_default`) → either wire into the relevant prompt context or remove from
   profiles so the config stops lying. *(deferred per plan WS-F(style); heuristic extractor covers idea-text visual style only)*
