# verify-03 — Adversarial verification of `audit/03-config-profile-and-defaults.md`

**Verifier:** independent agent (did not write the audit). **Target:** branch `modular-app`,
`HEAD = fb85baa0e6b769b709791a96a89980089304bf13`, working tree clean at verification time.
Every anchor re-resolved with `git show HEAD:<path>` / `git grep HEAD`; every executable claim
re-run with `.venv/bin/python` (Python 3.12.13) from the repo root. No repo file was modified.

Verdict vocabulary: **CONFIRMED** (as written) · **DOWNGRADED** (severity recomputed lower) ·
**CORRECTED** (substance holds, cited numbers/anchors wrong) · **STRENGTHENED** (evidence found
that the audit under-reported).

| finding | verdict | one-line reason |
|---|---|---|
| F-CFG-01 | **DOWNGRADED** | Duplicate map is byte-identical, but the claimed consequence (“stale fallback live in every `ModelRouter()` path”) is false: the YAML reaches the router through `resolved_config["model_profiles"]` overrides; 16 → 12. |
| F-CFG-02 | **CONFIRMED** (score 25 → 16) | Divergence reproduced verbatim on two agents; but the map side *is* pinned by a test, so drift is 4 not 5; Critical retained. |
| F-CFG-03 | **STRENGTHENED** | Two registries confirmed; verifier also found an *existing* divergence (`scene-writing-validator.blocking_conditions`) the audit missed. |
| F-CFG-04 | **CORRECTED** | Band really is zero-width — for **22 of 22** explicit literals, not “20 of 24”; the reproduce greps return `22`/`18`, not `24`/`20`. |
| F-CFG-05 | CONFIRMED | Two-shape parser divergence reproduced exactly (`[] []` vs blocking conflict; resolver sees both mock providers). |
| F-CFG-06 | CONFIRMED | Profile cap never reaches `BudgetState`; single construction site `mcp/tools/planning.py:33` reads only `args.get("cap_usd", 100.0)`. (5th spelling missed; see disputes.) |
| F-CFG-07 | CONFIRMED | Three key sets resolve at the cited lines; mutation mechanics (`_PROFILE_STACK_KEYS` → `_requested_profile_changes` → ignored by resolver) verified. |
| F-CFG-08 | CONFIRMED | `grep` gives exactly 7 read sites in 6 modules; `graph/graph.py:43` conjunction vs `graph/services.py:31/:48` lone-flag divergence verified. |
| F-CFG-09 | CONFIRMED | Three `profile_stack` writers at the cited lines; `projects.py:107-113` env correction vs `operator.py:143` uncorrected stack verified. |
| F-CFG-10 | CONFIRMED | Exactly three `resolved_review_strategy` occurrences; no production writer; 4 profiles declare `strategy: multi_model_panel`, `quality.draft.yaml:3` says `single`. |
| F-CFG-11 | CONFIRMED | `.env` policy confined to `providers/credentials.py:46-52`; override table and `runtime.py:456` read process env only. |
| F-CFG-12 | CONFIRMED | Both `Path("profiles")` sites and all 5 submodule imports reproduce; line counts in §1.1 all exact. (One §1.1 path does not exist; see disputes.) |
| F-CFG-13 | CONFIRMED | `"duration_seconds", 5` grep returns exactly the 9 cited sites; 5 factory literals at `:65,:74,:83,:92,:100` verified. |

**13 findings — 9 CONFIRMED, 1 DOWNGRADED, 1 CONFIRMED-with-score-correction, 1 CORRECTED, 1 STRENGTHENED. 0 REJECTED.**

---

## Expanded non-CONFIRMED rows

### F-CFG-01 — DOWNGRADED: Critical (16) → High (12) [impact 3 × drift 4]

What holds: `_FALLBACK_PROFILES` (`src/film_pipeline/agents/model_routing/__init__.py:18-69`) is
**byte-identical** to `profiles/base.studio.yaml:43-85` (8 profiles; equality command prints
`True`); `graph/services.py:85` and `:103` do construct `ModelRouter()` with no profiles; the
mutation (“edit the YAML, no test compares the two maps”) is a formally valid §1.6.3(b) proof.

What is falsified: the drift-proof sentence

> “The stale value is then live in every path that constructs `ModelRouter()` with no argument:
> `src/film_pipeline/graph/services.py:85` … and `:103`.”

is not true for the graph agent path. That path supplies per-call overrides built from the
*resolved profile*, and the override wins inside the router:

- `src/film_pipeline/graph/nodes/_context.py:410` `model_profiles = resolved_config.get("model_profiles", {})`
- `src/film_pipeline/graph/nodes/_context.py:413` `override = model_profiles.get(model_profile)`
- `src/film_pipeline/graph/nodes/_agent.py:152-153` → `model_overrides = _model_overrides_for(state, resolved_profile)`
- `src/film_pipeline/agents/runner.py:176` `) = router.resolve_model_params(model_profile, model_overrides)`
- `src/film_pipeline/agents/model_routing/__init__.py:153-155`: `profile = dict(base)` … `profile.update({k: v for k, v in overrides.items() if v is not None})`

and `resolved_config` is populated on both project-creation paths
(`app/services/operator.py:144`, `mcp/tools/projects.py:117`). Verifier proof (throwaway script,
repo untouched) building the real YAML map, mutating `creative_writer.primary`, then calling
`ModelRouter().resolve_model_params("creative_writer", <yaml override>)`:

```
fallback primary: deepseek/deepseek-chat
resolve_model_params with resolved-config override -> MUTATED/model-from-yaml
```

So editing `base.studio.yaml:45` **does** change the model on the primary graph path. Residual
real exposure is narrower than claimed: direct `ModelRouter()` callers with no resolved config
(`mcp/tools/reference_generation/composites.py:231`) and `agents/registry.py:15-17`. Recomputed
impact 3 (wrong internal selection on non-project paths, recoverable) × drift 4 (no agreement
test) = **12 → High**. The seam is real; the blast-radius claim must be rewritten.

### F-CFG-02 — CONFIRMED; score corrected 25 → 16 (Critical retained)

Divergence is **real and reproduced verbatim** by the audit's own command:

```
[('intake-classifier-agent', 'creative_writer', 'operations_triage'), ('structure-extractor-agent', 'schema_enforcer', 'strict_validator')]
```

Enumeration of both maps (11 `MVP_AGENTS`, 22-entry `_AGENT_PROFILE_MAP`): only those two differ.
`agents/mvp/__init__.py:40`/`:96` vs `graph/nodes/_context.py:44`/`:39`; the guard test
`tests/unit/graph/test_agent_profile_routing.py:21` and `:25` does literal-pin the divergent map
values, and `:39-40` asserts only key presence; `tests/unit/agents/test_mvp_invariants.py:50-59`
checks only that `default_model_profile` is *resolvable*, never that routing agrees with it.
So the disagreement is enshrined, not caught — the audit's central claim stands.

Correction: drift cannot be 5. §1.5 defines 5 as “no test can fail when one site changes”; the
map side is pinned by `test_agent_profile_routing.py:21/:25`, so a map edit *does* fail a test.
The contract side is free, so no test pins the *agreement* → drift 4. Impact 4 (wrong model
policy for 2 of 11 agents every run, quality-visible but not durable corruption) × 4 = **16,
still Critical**. Anchor nit: `agents/registry.py:74-81` should be `:77-83`
(`_reject_unknown_model_profile`).

### F-CFG-03 — STRENGTHENED: an existing divergence the audit did not report

All six shared ids and all cited lines resolve; `reference-usability-validator` rows are indeed
verbatim identical. But the audit only demonstrates a *mutation* scenario while an **existing
divergence** is present, which is the stronger §1.6.3(a) proof:

- `src/film_pipeline/validation/validators/__init__.py:40` —
  `blocking_conditions=["missing_scene_intent", "no_conflict"],`
- `src/film_pipeline/validation/impl/script_structure.py:139` —
  `blocking_conditions=["missing_scene_intent", "no_conflict", "scene_count_under_min"],`

Same `validator_id="scene-writing-validator"` (`:34` vs `:133`), same thresholds
(`:39` vs `:138`), different declared blocking contract. Because scoring/reporting uses
`self.entry` (`validation/base.py:263`, `:277`) and the impl object constructs its own entry
(`impl/script_structure.py:131-141`), a registry lookup
(`validation/registry.py:30-40`) returns a contract that disagrees with the object emitting
reports — today, not hypothetically.

Also corrected: “the only consumer of `MVP_VALIDATORS` is `tests/e2e/conftest.py:63`” is wrong —
`tests/unit/validation/test_registry.py:41,46,53,59,65,71,76` consumes it 7 times, and
`validation/__init__.py:17` re-exports it. This does not weaken the finding (nothing compares the
two registries). Severity 4 × 4 = 16 stands; the finding should be upgraded from “mutation
scenario” to “existing divergence”.

### F-CFG-04 — CORRECTED: the divergence is worse, the counts are wrong

The behaviour claim is confirmed and **understated**. AST enumeration of every
`ValidatorThresholds(...)` call in `src/film_pipeline`:

```
ValidatorThresholds( total calls in src: 23 | explicit-kwarg: 22
zero-width (review_at == block_below): 22 of 22
```

Breakdown: 18 × `85/75/75`, 3 × `80/70/70` (`validators/__init__.py:59,69,142`),
1 × `90/80/80` (`impl/delivery_completeness.py:114`), plus one bare default at
`validation/thresholds.py:21`. **Every** explicit call site has `review_at == block_below`, so the
`[block_below, review_at)` band is zero-width for all 22 — the audit's “20 of the 24” understates
it and its denominator is wrong. The class default `85/75/65`
(`schemas/registries/validator_registry.py:17-19`) is used by no call site.

Mechanical falsification of the two reproduce commands (`grep -rn … --include='*.py' | wc -l`):

| command | audit | actual |
|---|---|---|
| `grep -rn 'pass_at=' src/film_pipeline` | 24 | **22** |
| `grep -rn 'block_below=75' src/film_pipeline` | 20 | **18** |

The “24” counts `class ValidatorThresholds(` (`validator_registry.py:14`), i.e. the class
definition, not a call site. The mutation claim (“change the default at `:19`; literals keep
their values; no test fails”) is valid: `tests/unit/validation/test_thresholds.py:31-36` pins only
a hand-written 90/80/70 object, never a registered entry's band. Severity 4 × 4 = 16 stands.

---

## Missed in scope (config/profile seams the audit did not report)

1. **Third copy of the model-profile vocabulary that gates agent registration.**
   `src/film_pipeline/agents/registry.py:15-17` —
   `return {*ModelRouter().list_profiles(), "orchestrator"}` — and `:77-83`
   `if contract.default_model_profile not in self.known_model_profiles: raise ValueError(...)`.
   The set of legal profile *names* therefore comes from the code fallback, not from
   `profiles/base.studio.yaml`. Consequence the audit never states: adding
   `model_profiles.<new_profile>` to `base.studio.yaml` (or a project layer) and referencing it
   from an agent contract fails at registry construction until `_FALLBACK_PROFILES` is also
   edited — the inverse direction of F-CFG-01's mutation. Same O1 seam, additional owner.
2. **`profiles/`-style CWD-relative corpus root, second instance (KB manifest).**
   `src/film_pipeline/kb/paths.py:8-16` builds `Path("film-knowledge-base/manifest.yaml")` /
   `Path("film-knowledge-base/index/kb-manifest.yaml")`, while `src/film_pipeline/app/smoke.py:55`
   independently hardcodes `Path("film-knowledge-base/index/kb-manifest.yaml")` and
   `app/bootstrap.py:38` probes only through `kb_manifest_path()`. Same O7/O8 pattern as
   F-CFG-12(a), same silent-CWD failure mode, not covered.
3. **Fifth cap spelling absent from F-CFG-06's own grep.** `budget_cap_usd` appears at
   `schemas/project.py:43`, `schemas/constraints.py:93`, `constraints/extractor.py:154`,
   `agents/impl/intake_agent.py:49` — and the finding's reproduce pattern list
   (`project_cap_usd|max_total_usd|auto_approve_up_to|max_auto_approved_cost_usd|human_approval_above_usd|per_clip_limit`)
   does not match it, so “spelled four ways” is an undercount of the vocabulary it claims to
   enumerate mechanically.
4. **Hardcoded profile name inside the “clean” env-override table.**
   `src/film_pipeline/config/runtime_overrides.py:18` —
   `"FILM_PIPELINE_MODEL_OVERRIDE": ("model_profiles", "creative_writer", "primary"),`.
   §3 calls this table “the one clean env pattern”; the row couples it to F-CFG-01's profile
   vocabulary, so renaming/removing `creative_writer` silently retargets the env knob.

## Disputes requiring the author to fix

1. **F-CFG-01 blast radius / drift proof** — delete “live in every path that constructs
   `ModelRouter()`”; the override path wins. Recompute severity 16 → 12 (High), and re-target the
   consequence to direct callers + `agents/registry.py:15-17`.
2. **F-CFG-02 score** — 5 × 5 = 25 is not defensible (map side is test-pinned); use 4 × 4 = 16.
   Also fix `agents/registry.py:74-81` → `:77-83`.
3. **F-CFG-03** — replace “mutation scenario” with the existing `scene-writing-validator`
   `blocking_conditions` divergence (`validators/__init__.py:40` vs `impl/script_structure.py:139`);
   correct “only consumer” (`tests/unit/validation/test_registry.py` uses it 7×).
4. **F-CFG-04** — replace `24`/`20` with `22 explicit literals, all 22 zero-width`
   (18 × `85/75/75`, 3 × `80/70/70`, 1 × `90/80/80`); the `24` in the grep output is the class
   definition line.
5. **F-CFG-06** — add `budget_cap_usd` to the spelling list and to the reproduce pattern; either
   claim five spellings or narrow the title.
6. **§1.1 coverage table** — `mcpserver.py` does not exist at HEAD
   (`git show HEAD:src/film_pipeline/mcpserver.py` → `fatal: path … does not exist`), which also
   falsifies the header's “the only unresolvable ones are …” claim (line 15-17). The
   `config/resolver.py` and `app/runtime.py` rows cross-reference **F-CFG-08**
   (`FILM_PIPELINE_NO_PERSIST`), which neither file reads; those readers belong to F-CFG-09/F-CFG-11.
7. **§1.2** — “only 4 of 13 files carry a `profile:` block”: actual is **3**
   (`grep -rln '^profile:' profiles/` → `auto-approve.yaml`, `local-real-provider.yaml`,
   `mock-demo.yaml`), consistent with the audit's own three-file enumeration on line 89.
8. **§6/§7 reconciliation** — the working tree is clean and `src/film_pipeline/architecture.py`
   does not exist in this checkout (`git status --porcelain` empty; file absent at HEAD). The
   §7 paragraph describing what that uncommitted layer “already provides”, and the §6 reliance on
   it for the phase-vocabulary guard, are stale for anyone reading at `fb85baa`; state this or
   drop it.

**§5 prior-art sample (≥3 “still present” + 1 “worse”), all verified at HEAD:** A4
`agents/prompt_templates/defaults/validators.py:292` quote exact; A5 `dialogue_weight` /
`camera_default` → 0 hits in `src/`; C7 `spine.py:266` `"2. Identify 3-5 themes.\n"`; G1
`frame_heuristics.py:53`; G2 `gemini_client.py:40`; G3 `production.py:60`; B `story_bible.py:24-29`;
C5 citation drift confirmed (`orchestrator_state.py:260` is now `cycle["status"] = status`, the
stall default is `:362`); C3/KB tolerances at `brief.py:116` / `prep_gates.py:121`. **Worse
claim C4 confirmed**: three `300` sites (`agents/impl/intake_agent.py:79`,
`agents/impl/structure_extractor_agent.py:16`, `graph/nodes/_context.py:70`), not one. **E2
confirmed** (already divergent). The prior-art section is accurate.

## Overall verdict

**Sound spine, imperfect arithmetic.** Every one of the thirteen findings is anchored to real
code at HEAD and none is rejected; the four high-stakes mechanical claims the brief targeted —
agent→profile divergence (F-CFG-02), duplicated fallback (F-CFG-01, duplication confirmed /
consequence overstated), zero-width threshold band (F-CFG-04, real and worse than stated) and
7-reader `FILM_PIPELINE_NO_PERSIST` (F-CFG-08, exact) — all survive as seams. Required fixes are
one severity downgrade (F-CFG-01), one overstated drift score (F-CFG-02), two count corrections
(F-CFG-04, §1.2), one strengthened drift proof (F-CFG-03), and four citation/coverage defects.
