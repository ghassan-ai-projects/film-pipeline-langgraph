# Hardcoded Values & Dead-Config Inventory

**Branch:** `review/prep-production-quality`
**Date:** 2026-06-28

This audit answers: "what creative/structural values are hardcoded, and which
profile fields are silently ignored?" It is the evidence base for the
implementation plan (`prep-production-implementation-plan.md`).

The recurring pattern: **profiles advertise creative intent, but the code reads an
LLM guess (or a hardcoded constant) instead.** The profile values are merged into
`resolved_config` and then never read.

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

## F. Provider pricing — hardcoded rates

| Rate | Location |
| --- | --- |
| Seedance `$0.18/s` | `providers/factory.py:107`, `adapters/seedance_openrouter.py:161` (duplicated), and again in the planner prompt `defaults.py:582` |
| Veo `$0.10/s` "placeholder rate" | `providers/factory.py:109`, `adapters/veo_fast.py:69` |
| Imagen `$0.02` / `$0.05` per image | `adapters/imagen4_gemini.py:154-155` |
| Planner-prompt price list (`Seedance $0.18`, `Veo 3.1 Fast $0.50`, `Veo Lite $0.25`, `Imagen $0.02`) | `defaults.py:582` — **disagrees** with the adapter rates above |

The prompt's price list and the adapter rates are **inconsistent** ($0.50 vs $0.10
for Veo), so planned cost and charged cost will diverge.

## G. Generation / image constants

| Value | Location |
| --- | --- |
| Min resolution `512px` | `generation/frame_heuristics.py:63`, prompt `defaults.py:939` |
| `maxOutputTokens 1024` (frame/sheet reviewers) | `generation/frame_reviewer.py:206`, `sheet_reviewer.py:196` |
| Reviewer temperature `0.2` | `generation/sheet_reviewer.py:196` |
| Default `quality_score 80.0` in reference template | `defaults.py:446` |
| Negative-prompt / expression text blocks | `generation/prompt_builder.py:16,32,351` (hardcoded craft text) |
| `re_anchor_every_n_clips`, drift rules | profile-defined in `base.studio.yaml`; verify they reach the generation loop |

## D. Recommended disposition

For each, the choice is **make it live (profile-driven)** or **delete it (remove the
false promise)**:

1. **Runtime** → remove from profiles entirely; becomes **user input** (see plan).
2. **film_type** → make the operator-selected profile value authoritative; intake
   may *confirm* but not silently override.
3. **pacing** → unify vocabulary, make profile-driven; derive shot-duration band
   from it via a single source of truth (delete the duplicated dicts).
4. **Shot-duration table / scene-density table** → one config-driven table keyed by
   `film_type × pacing`, replacing the magic numbers and open ranges.
5. **Tolerances / thresholds** → source from the quality profile.
6. **Act structure** → introduce a variable movement model driven by
   `story_structure` (larger, schema-touching — flagged as its own workstream).
7. **Dead fields with no consumer** (`dialogue_weight`, `visual_style`,
   `camera_default`) → either wire into the relevant prompt context or remove from
   profiles so the config stops lying.
