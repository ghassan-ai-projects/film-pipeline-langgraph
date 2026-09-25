# 03 — Audit: Configuration, Profiles, and Defaults

**Commit audited:** `fb85baa0e6b769b709791a96a89980089304bf13` (branch `modular-app`,
`Merge pull request #29 from ghassan-ai-projects/storage-upgrade`).

**Method:** all evidence read and re-verified against `HEAD` via `git show HEAD:<path>`.
Conforms to `docs/modular-architecture/00-methodology-and-quality-bar.md` §1.6.

**Independent verification (revision 2).** This file was re-checked by a second agent in
`docs/modular-architecture/reviews/verify-03.md`: **9 CONFIRMED, 1 DOWNGRADED
(F-CFG-01), 1 CONFIRMED-with-score-correction (F-CFG-02), 1 CORRECTED (F-CFG-04),
1 STRENGTHENED (F-CFG-03), 0 REJECTED.** Revision 2 resolves all eight disputes recorded
there; every correction was re-verified against HEAD by the author before being applied.
Changes in this revision: F-CFG-01 downgraded Critical→High and its blast radius rewritten;
F-CFG-02 score 25→16 and one anchor fixed; F-CFG-03 given an *existing* divergence in place
of its mutation scenario; F-CFG-04 counts corrected (22 explicit literals, all 22 zero-width,
18 of them `85/75/75`) here and in the §4 table; F-CFG-06 extended from four to five cap
spellings (adding `budget_cap_usd`) and F-CFG-12 given its second CWD-relative corpus root
(`kb/paths.py` vs `app/smoke.py`); the `creative_writer` hardcode inside the env-override
table now flagged in §3; four §1 coverage defects fixed; every reference to a now-absent
`architecture.py` removed from §6/§7 and prior art and recorded only in §8 H1; the finding
index re-tallied to **5 Critical, 6 High, 2 Medium**.

**Verification record (post-verification additions).** Two coverage holes reported by the
adversarial pass (`docs/modular-architecture/reviews/adversarial-coverage.md` §H3 and §H7)
were independently re-verified against `fb85baa` and admitted as findings after revision 2
closed. Bar A6 re-verification of these two blocks is **PENDING**: every anchor and
reproduce command was run by this author from the pristine snapshot
(`git archive fb85baa | tar -x -C /tmp/snap`), not by a second agent.

- **Findings after this revision: 15** — **5 Critical, 8 High, 2 Medium** (Critical: 02, 03,
  04, 05, 06; High: 01, 07, 08, 09, 10, 13, 14, 15; Medium: 11, 12).
- **Added post-verification (PENDING VERIFICATION):** F-CFG-14 — the pacing vocabulary is
  re-declared in four places and the two mapping tables already disagree (O1, High
  3 × 4 = 12), source §H3; it contradicts the §5 A2 "FIXED" verdict for the vocabulary half,
  as stated in its Prior-art note.
- **Added post-verification (PENDING VERIFICATION):** F-CFG-15 — the model-input size cap is
  code-only policy and the readiness gate already disagrees with the shot-matrix truncation
  site (8000 vs 6000), with paid-review sampling re-derived per branch (O5, High
  3 × 4 = 12), source §H7; scoped to what is provably divergent or unguarded, with the
  excluded H7 anchors named in its Blast-radius note.

**Path conventions.** Anchors starting with `src/`, `tests/`, `profiles/`,
`documentation/` or `docs/` are repo-relative. Bare package-relative anchors
(`config/loader.py:30`, `graph/scope_contract.py:58`) are relative to `src/film_pipeline/`.
Within a quoted block, a repeated `:NNN` continues the file named immediately before it.
**Anchor check (revision 2):** all 347 `file:line` anchors in this document were mechanically
resolved against `git ls-tree HEAD`; **343 resolve** (274 by full path, 69 by an unambiguous
path suffix such as `impl/script_structure.py` → `src/film_pipeline/validation/impl/script_structure.py`)
and every one points inside its file's line count. **No anchor resolved ambiguously.** The
only 4 unresolvable ones are all the deliberately-labelled stale prior-art citation
`graph/nodes.py:46` — that path does not exist at HEAD; the file is now
`graph/nodes/_context.py`. A second path, `src/film_pipeline/architecture.py`, is cited in
prose only (never as an anchor): it does not exist in this checkout at all, which §7 and §8 H1
state explicitly.

> **No working-tree caveat applies at revision 2.** `git status --porcelain` is empty and
> `src/film_pipeline/architecture.py` is absent from the working tree as well as from
> `fb85baa`. During the original audit a concurrent agent briefly held an uncommitted
> ownership-declaration layer in this checkout; it was subsequently removed. Because it
> cannot be verified by a reader at `fb85baa`, no finding or recommendation here depends on
> it; it survives only as the explicitly-labeled hypothesis H1 in §8.


---

## 1. Coverage

### 1.1 Scope files and verdicts

| Scope file / area | At HEAD | Verdict |
|---|---|---|
| `config/__init__.py` | 21 lines | **has findings** — public API omits the profile-resolution surface (F-CFG-12) |
| `config/loader.py` | 49 lines | **has findings** — CWD-relative `profiles/` root (F-CFG-12) |
| `config/merger.py` | 36 lines | **clean** — deep-merge grammar is single-owner here |
| `config/profile_resolver.py` | 219 lines | **has findings** — stack key set (F-CFG-07), provider shape (F-CFG-05), hardcoded base name |
| `config/resolver.py` | 65 lines | **has findings** — second reader of `FILM_PIPELINE_QUALITY` (F-CFG-09), process-env-only resolution (F-CFG-11) |
| `config/runtime_overrides.py` | 73 lines | **has findings** — the env-var allowlist (F-CFG-08, F-CFG-11) and the `creative_writer` hardcode inside it (F-CFG-01) |
| `config/validator.py` | 81 lines | **has findings** — provider-lineup parser diverges (F-CFG-05) |
| `profiles/` (13 YAML) | 13 files | **has findings** — two profile schemas; seven distinct budget key names across the profile layers (F-CFG-06) |
| `app/bootstrap.py` | 78 lines | **has findings** — second `profiles/` CWD probe (F-CFG-12) |
| `app/runtime.py` (config parts) | 461 lines | **has findings** — `FILM_PIPELINE_MCP_MODE` reader (`:456`) and `FILM_PIPELINE_RUNTIME_ROOT` re-read (`:59`), both process-env-only (F-CFG-11) |
| `agents/model_routing/__init__.py` | 161 lines | **has findings** — `_FALLBACK_PROFILES` (F-CFG-01) |
| `graph/_agent_routing.py` | 211 lines | **has findings** — reads `resolved_review_strategy`, a key with no writer (F-CFG-10) |
| `graph/services.py` | 137 lines | **has findings** — constructs `ModelRouter()` without project profiles (F-CFG-01); 2× `FILM_PIPELINE_NO_PERSIST` (F-CFG-08) |
| `mcp/tools/_profile_change.py` | 473 lines (read fully) | **has findings** — third stack key set (F-CFG-07), shallow diff, `profile_stack` writer (F-CFG-09) |
| `mcp/tools/registry.py` | 387 lines | **clean** — registration only; no config resolution |
| `cli/run.py` (config parts) | 297 lines | **has findings** — CLI profile defaults duplicate profile layers; `FILM_PIPELINE_NO_PERSIST` reader (F-CFG-08, F-CFG-13) |
| `generation/*.py` | 12 files / 2169 lines | **has findings** — 9× `duration_seconds` default `5`, `_PASS_THRESHOLD`, Gemini params (F-CFG-13) |
| `validation/*.py` | 5 files / 572 lines | **has findings** — parallel registries (F-CFG-03), threshold band grammar (F-CFG-04) |
| `providers/factory.py`, `providers/credentials.py` | — | **has findings** — hardcoded capability defaults (F-CFG-13); `.env` split policy (F-CFG-11) |
| `graph/graph.py`, `app/_persistence.py`, `app/logging_setup.py`, `app/safety.py` | — | **has findings** — persistence-policy readers (F-CFG-08) |
| `kb/paths.py`, `app/smoke.py` | — | **has findings** — CWD-relative KB corpus root, second instance of the F-CFG-12(a) pattern (F-CFG-12) |

Nothing in scope was omitted. No package was silently skipped.

### 1.2 Profile tree inventory (`profiles/`)

13 files, all `.yaml`. **There is no manifest file** — `find profiles -type f` returns
exactly the 13 YAML files. The blueprint requires profile validation of "referenced
providers exist / referenced validators exist / referenced models exist"
(`documentation/architecture-blueprint.md:1295-1300`), and there is no artifact at HEAD
that lists valid profile names for that check.

| Category | Count | Files |
|---|---|---|
| base | 1 | `base.studio.yaml` |
| `film-type.*` | 3 | `film-type.experimental.yaml`, `film-type.narrative.yaml`, `film-type.visual_poetry.yaml` |
| `quality.*` | 3 | `quality.draft.yaml`, `quality.festival.yaml`, `quality.studio.yaml` |
| `provider.*` | 2 | `provider.free_or_low_cost.yaml`, `provider.seedance_primary.yaml` |
| `review.*` | 1 | `review.strict_continuity.yaml` |
| uncategorised standing profiles | 3 | `auto-approve.yaml`, `local-real-provider.yaml`, `mock-demo.yaml` |

Two profile schemas coexist with no schema owner:

- **Studio schema** — top-level keys (`profiles/base.studio.yaml:4-101`: `phases`, `review`,
  `budget`, `model_profiles`, `generation`, `delivery`).
- **Named-profile schema** — a `profile:` identity block plus `studio:`/`providers:`/
  `models:`/`validators:`/`checkpoints:` (`profiles/mock-demo.yaml:5-43`,
  `profiles/local-real-provider.yaml:6-47`, `profiles/auto-approve.yaml:8-15`).

Reproduce: `grep -rln '^profile:' profiles/` → **3** of 13 files carry a `profile:` identity
block (`auto-approve.yaml`, `local-real-provider.yaml`, `mock-demo.yaml`), and
`mcp/tools/config.py:37-39` is the only
reader of it, for display only. The stack identity used by resolution is the **file
stem** (`config/profile_resolver.py:45` `stack[key] = src.path.stem`), so the two
identity conventions are unlinked.

---

## 2. Findings

### F-CFG-01 — Model-profile defaults are declared twice: profile YAML and a code fallback

- **Class:** O1
- **Severity:** High (impact 3 × drift 4 = 12) — *downgraded from Critical 16 by
  `reviews/verify-03.md`; accepted, see the drift proof.*
- **Concern:** Which model id, max_tokens, temperature, top_p and frequency_penalty back each logical model profile, **and** which profile names are legal at all.
- **De-facto owners (three):**
  - `profiles/base.studio.yaml:43-85` — the declared project-facing source of truth — `model_profiles:\n  creative_writer:\n    primary: deepseek/deepseek-chat`
  - `src/film_pipeline/agents/model_routing/__init__.py:18-69` — a verbatim second copy — `_FALLBACK_PROFILES: dict[str, dict[str, object]] = {` / `"primary": "deepseek/deepseek-chat",`
  - `src/film_pipeline/agents/registry.py:15-17` — a **third** copy, which derives the set of *legal* profile names from the code fallback rather than from the YAML — `def _default_model_profiles() -> set[str]:` … `return {*ModelRouter().list_profiles(), "orchestrator"}` (verified: 9 names, none sourced from `profiles/`)
- **Drift proof:** *two mutation scenarios, one in each direction, neither caught by a test.*
  Verified mechanically that the YAML map and `_FALLBACK_PROFILES` are **byte-identical
  today** (8 profiles, exact dict equality), and that the override path rescues the
  primary graph path — so the exposure is narrower than revision 1 claimed. Reproduced:
  ```
  fallback primary        : deepseek/deepseek-chat
  with resolved-config ov : MUTATED/model-from-yaml
  _FALLBACK still         : deepseek/deepseek-chat
  ```
  The YAML **does** reach the router on project paths, because
  `graph/nodes/_context.py:410` `model_profiles = resolved_config.get("model_profiles", {})`
  and `:413` `override = model_profiles.get(model_profile)` feed
  `src/film_pipeline/graph/nodes/_agent.py:153` `model_overrides = _model_overrides_for(state, resolved_profile)` into
  `agents/runner.py:176` `) = router.resolve_model_params(model_profile, model_overrides)`,
  where `src/film_pipeline/agents/model_routing/__init__.py:153-155` applies `profile = dict(base)` … `profile.update({k: v for k, v in overrides.items() if v is not None})`.
  **Scenario (a) — forward, uncaught:** edit `profiles/base.studio.yaml:45`
  `primary: deepseek/deepseek-chat`. `_FALLBACK_PROFILES` keeps the old value and no test
  fails (`tests/unit/agents/model_routing/test_routing.py:101` pins the *fallback* literal
  `assert model == "deepseek/deepseek-chat"`), so callers that build `ModelRouter()` with no
  resolved config keep the stale model — `src/film_pipeline/mcp/tools/reference_generation/composites.py:231` `router = ModelRouter()`
  and `src/film_pipeline/agents/registry.py:15-17`.
  **Scenario (b) — inverse, and stricter:** add `model_profiles.<new_profile>` to
  `base.studio.yaml` and reference it from an agent contract's `default_model_profile`.
  Registration fails — `agents/registry.py:77-83` raises
  `f"'{contract.default_model_profile}'."` when the name is not in
  `self.known_model_profiles`, and that set is built from the code fallback, so the YAML
  edit alone is not enough. **No test fails** on the YAML side. The seam therefore requires
  a coordinated code edit in both directions.
- **Reproduce:** equality (above), plus
  `.venv/bin/python -c "from film_pipeline.agents.registry import _default_model_profiles as f;print(sorted(f()))"` → 9 names from code, not from `profiles/`
- **Blast radius:** `agents/model_routing`, `agents/registry`, `mcp/tools/reference_generation`.
  Narrower than revision 1 stated: the project graph path and both project-creation paths
  (`app/services/operator.py:144`, `mcp/tools/projects.py:117`) supply resolved-config
  overrides, so a profile edit **does** take effect there. The real exposure is (i) direct
  `ModelRouter()` callers with no resolved config, and (ii) a new profile name that cannot be
  registered from the profile alone.
- **Candidate owner module:** `config` — owns the *name→params* model-profile vocabulary; `agents/model_routing` becomes a pure consumer that must receive resolved profiles, and `agents/registry` must derive legal names from the same owner.
- **Extraction sketch:** move the map into `profiles/base.studio.yaml` only; change
  `ModelRouter.profiles` to a required constructor argument; have
  `_default_model_profiles()` read the same owner instead of `ModelRouter()`. Guard tests:
  `set(ModelRouter.required_profile_names()) == set(base.studio.yaml["model_profiles"])`, and
  a test that asserting a new YAML-only profile name from an agent contract succeeds.
- **Prior art:** §E of `documentation/reviews/hardcoded-values-inventory.md:156-171`
  describes `_FALLBACK_PROFILES` as an intentional "compatibility fallback". This audit
  disagrees with the *intent*, not the observation: the fallback is a second normative model
  with no agreement test, and it additionally gates registration (`agents/registry.py:15-17`).
- **Verifier:** STRENGTHENED on scope (third owner + inverse mutation found by
  `reviews/verify-03.md`), DOWNGRADED on severity (16 → 12).

---

### F-CFG-02 — Agent→model-profile mapping is duplicated **and already divergent**

- **Class:** O1 (with an existing divergence, so the seam is no longer theoretical)
- **Severity:** Critical (impact 4 × drift 4 = 16) — *score corrected from 5 × 5 = 25 by
  `reviews/verify-03.md`; accepted, because the map side **is** test-pinned by
  `tests/unit/graph/test_agent_profile_routing.py:21`,`:25`, so drift cannot be 5. The
  *contract* side is free, so no test pins the **agreement** → drift 4.*
- **Concern:** Which model profile each agent uses for its model calls.
- **De-facto owners:**
  - `src/film_pipeline/agents/mvp/__init__.py` — declaration on the agent contract — `agent_id="intake-classifier-agent",` (`:31`) with `default_model_profile="creative_writer",` (`:40`); `agent_id="structure-extractor-agent",` (`:87`) with `default_model_profile="schema_enforcer",` (`:96`)
  - `src/film_pipeline/graph/nodes/_context.py:27-52` — a hand-maintained mirror used at call time — `_AGENT_PROFILE_MAP: dict[str, str] = {` containing `"structure-extractor-agent": "strict_validator",` (`:39`) and `"intake-classifier-agent": "operations_triage",` (`:44`)
- **Drift proof:** **existing divergence**, confirmed by executing both sides.
  `intake-classifier-agent`: declared `creative_writer` (`agents/mvp/__init__.py:40`) vs used
  `operations_triage` (`src/film_pipeline/graph/nodes/_context.py:44`) — different model
  (`deepseek/deepseek-chat` 8192 tok / temp 0.7 vs `google/gemini-3-flash-preview` 4096 tok /
  temp 0.2). `structure-extractor-agent`: declared `schema_enforcer` (`:96`) vs used
  `strict_validator` (`:39`) — temp 0.0 vs 0.1. `agents/registry.py:77-83`
  (`_reject_unknown_model_profile`) validates only
  that `contract.default_model_profile` is a *known profile name* — it never resolves the
  model. Reproduce:
  ```
  .venv/bin/python -c "from film_pipeline.graph.nodes import _AGENT_PROFILE_MAP as M;from film_pipeline.agents.mvp import MVP_AGENTS as A;print([(a.agent_id,a.default_model_profile,M.get(a.agent_id)) for a in A if a.default_model_profile!=M.get(a.agent_id)])"
  ```
  → `[('intake-classifier-agent', 'creative_writer', 'operations_triage'), ('structure-extractor-agent', 'schema_enforcer', 'strict_validator')]`
  The guard test makes this permanent rather than catching it: it asserts only key
  *presence* (`tests/unit/graph/test_agent_profile_routing.py:39-40`
  `assert agent.agent_id in _AGENT_PROFILE_MAP`) and at `:21` and `:25` it **pins the
  divergent values** (`_AGENT_PROFILE_MAP["structure-extractor-agent"] == "strict_validator"`,
  `_AGENT_PROFILE_MAP["intake-classifier-agent"] == "operations_triage"`).
- **Reproduce:** `.venv/bin/python -c "from film_pipeline.graph.nodes import _AGENT_PROFILE_MAP as M;from film_pipeline.agents.mvp import MVP_AGENTS as A;print([(a.agent_id,a.default_model_profile,M.get(a.agent_id)) for a in A if a.default_model_profile!=M.get(a.agent_id)])"` → `[('intake-classifier-agent', 'creative_writer', 'operations_triage'), ('structure-extractor-agent', 'schema_enforcer', 'strict_validator')]`
- **Blast radius:** every agent model call routed through
  `src/film_pipeline/graph/nodes/_agent.py:152`
  `resolved_profile = _AGENT_PROFILE_MAP.get(agent_id, "operations_triage")`, plus the
  `model_overrides` lookup at `src/film_pipeline/graph/nodes/_agent.py:153`. The operator's declared per-agent model
  policy in the profile stack is silently overridden for two of eleven MVP agents.
- **Candidate owner module:** `agents` — the agent contract already carries
  `default_model_profile`; `graph/nodes` must read it from the resolved registration
  instead of keeping a second table.
- **Extraction sketch:** delete `_AGENT_PROFILE_MAP`; at `src/film_pipeline/graph/nodes/_agent.py:152` read
  `routing.contract.default_model_profile`. Guard test: for every `MVP_AGENTS` entry assert
  the *resolved* profile equals `default_model_profile`, and assert `_AGENT_PROFILE_MAP`
  no longer exists.
- **Prior art:** §E of `documentation/reviews/hardcoded-values-inventory.md:177-178` noted
  "The agent→profile mapping `_AGENT_PROFILE_MAP` (`graph/nodes.py:46` — a path that does **not** exist at HEAD) is also a hardcoded
  dict." **What is new:** the file moved to `graph/nodes/_context.py:27`, and this audit is
  the first to demonstrate the map **already disagrees** with `agents/mvp/__init__.py` on two
  agents and that the existing test enshrines the disagreement.

---

### F-CFG-03 — Two parallel validator registries with overlapping ids and no agreement test

- **Class:** O4
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** Which validators exist and with what declared contract (scope, modalities, model profile, thresholds, blocking/warning conditions).
- **De-facto owners:**
  - `src/film_pipeline/validation/validators/__init__.py:11` — declarative list — `MVP_VALIDATORS: list[ValidatorRegistryEntry] = [` … `validator_id="reference-usability-validator",` (`:74`)
  - `src/film_pipeline/validation/impl/reference_usability.py:193` — the same entry re-created inside each validator's constructor — `validator_id="reference-usability-validator",`
- **Drift proof:** **existing divergence of normative content — present today, not
  hypothetical.** Six ids are declared in
  both places (`assembly-validator` `src/film_pipeline/validation/validators/__init__.py:158` ↔ `src/film_pipeline/validation/impl/assembly.py:205`;
  `dialogue-voice-validator` `:44` ↔ `src/film_pipeline/validation/impl/dialogue_voice.py:176`;
  `prompt-readiness-validator` `:95` ↔ `src/film_pipeline/validation/impl/prompt_readiness.py:160`;
  `reference-usability-validator` `:74` ↔ `src/film_pipeline/validation/impl/reference_usability.py:193`;
  `scene-continuity-validator` `:127` ↔ `src/film_pipeline/validation/impl/scene_continuity.py:213`;
  `scene-writing-validator` `:34` ↔ `src/film_pipeline/validation/impl/script_structure.py:133`). The
  `reference-usability-validator` rows are verbatim identical, so that pair is pure
  duplication — but `scene-writing-validator` **already disagrees**:
  - `validation/validators/__init__.py:40` — `blocking_conditions=["missing_scene_intent", "no_conflict"],`
  - `validation/impl/script_structure.py:139` — `blocking_conditions=["missing_scene_intent", "no_conflict", "scene_count_under_min"],`

  Same `validator_id` (`:34` vs `:133`), same thresholds (`:39` vs `:138`), different declared
  blocking contract: the impl copy adds a third blocking condition the registry row does not
  declare. Because the object emits reports from its own entry
  (`validation/base.py:263` `status = score_to_status(score, self.entry.thresholds)` and
  `:277` `validator_id=self.entry.validator_id`), and the impl constructs that entry itself
  (`src/film_pipeline/validation/impl/script_structure.py:131-141`), a registry lookup (`validation/registry.py:30-40`)
  today returns a contract that disagrees with the object producing reports. No test fails.
  `MVP_VALIDATORS` is consumed at `tests/e2e/conftest.py:63` and **7×** in
  `tests/unit/validation/test_registry.py:41,46,53,59,65,71,76`, and is re-exported at
  `validation/__init__.py:17` — but no consumer compares the two registries. The impl
  entries also diverge in *membership*: `delivery-completeness-validator`
  (`src/film_pipeline/validation/impl/delivery_completeness.py:109`) has no row in `MVP_VALIDATORS`, and
  `MVP_VALIDATORS` has 9 ids with no impl class.
- **Reproduce:** `grep -rn 'validator_id=' src/film_pipeline/validation --include='*.py' | sed 's/.*validator_id="\([^"]*\)".*/\1/' | sort | uniq -c | sort -rn` and `git show HEAD:src/film_pipeline/validation/validators/__init__.py | sed -n '40p'; git show HEAD:src/film_pipeline/validation/impl/script_structure.py | sed -n '139p'`
- **Blast radius:** `validation`, `app/smoke`, `tests/e2e`. Registry lookups
  (`validation/registry.py:30-40`) return contracts that disagree with the objects actually
  producing reports.
- **Candidate owner module:** `validation` — one registry; validator classes must receive
  their entry from the registry rather than constructing it.
- **Extraction sketch:** make `ValidatorRegistryEntry` data live only in
  `validation/validators/__init__.py`; change `BaseValidator.__init__` to take a
  `validator_id` and look the entry up. Guard test (the `RegistryAgreement` shape): assert
  `{c.validator_id for c in impl classes} ⊆ {e.validator_id for e in MVP_VALIDATORS}` with
  recorded non-members, and assert every shared id has identical `thresholds`
  **and identical `blocking_conditions`**.
- **Prior art:** `documentation/reviews/hardcoded-values-inventory.md:146-152` clarifies the
  four-status contract but frames thresholds as the only issue. **What is new:** the
  registry duplication itself, that the *registered* entry is not the one used for scoring,
  and the `scene-writing-validator` blocking-contract divergence.
- **Verifier:** STRENGTHENED by `reviews/verify-03.md`, which found the existing
  `blocking_conditions` divergence that revision 1 missed; the mutation scenario it replaced
  is retained in spirit by the identical-`reference-usability` pair above.

---

### F-CFG-04 — The score→status band grammar has a documented default that no registered validator uses

- **Class:** O1
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** The score bands that classify a validator score into pass / pass-with-notes / needs-revision / blocked.
- **De-facto owners:**
  - `src/film_pipeline/schemas/registries/validator_registry.py:17-19` — the class default — `pass_at: float = Field(default=85.0, ge=0, le=100)` / `review_at: float = Field(default=75.0, ge=0, le=100)` / `block_below: float = Field(default=65.0, ge=0, le=100)`
  - `src/film_pipeline/validation/thresholds.py:15-19` — the documented contract — `pass ≥ 85` / `pass_with_notes ≥ 75` / `needs_revision ≥ 65` / `blocked < 65`
  - `src/film_pipeline/validation/validators/__init__.py` and `src/film_pipeline/validation/impl/*.py` — **22 explicit literal re-statements**, e.g. `src/film_pipeline/validation/validators/__init__.py:79` `thresholds=ValidatorThresholds(pass_at=85, review_at=75, block_below=75),`
- **Drift proof:** **existing divergence, with a behavioural consequence — and it is total,
  not partial.** AST enumeration of every `ValidatorThresholds(...)` call under
  `src/film_pipeline`: **23 calls total, 22 with explicit kwargs, and all 22 have
  `review_at == block_below`** — breakdown 18 × `85/75/75`, 3 × `80/70/70`
  (`validators/__init__.py:59,69,142`), 1 × `90/80/80`
  (`src/film_pipeline/validation/impl/delivery_completeness.py:114`); the 23rd is the bare default at
  `validation/thresholds.py:21`. With `score_to_status` (`validation/thresholds.py:23-29`),
  a score of 70 against a `85/75/75` entry fails `score >= t.pass_at` (85), fails
  `score >= t.review_at` (75), and fails `score >= t.block_below` (75) → `BLOCKED`. The
  `NEEDS_REVISION` band `[block_below, review_at)` therefore has **zero width for every one
  of the 22 explicit entries**, contradicting the docstring contract at
  `src/film_pipeline/validation/thresholds.py:15-19` that reserves 65–75 for `needs_revision`. The class default
  `85/75/65` (`schemas/registries/validator_registry.py:17-19`) is used by no call site.
  Mutation: change `block_below` default at `src/film_pipeline/schemas/registries/validator_registry.py:19` from 65 to 70; the 22
  explicit literals keep their values and **no test fails**, because the literals do not read
  the default — `tests/unit/validation/test_thresholds.py:31-36` pins only a hand-written
  `90/80/70` object, never a registered entry's band.
- **Reproduce:** `grep -rn 'pass_at=' src/film_pipeline --include='*.py' | wc -l` → `22` and `grep -rn 'block_below=75' src/film_pipeline --include='*.py' | wc -l` → `18`. *(Revision 1 reported `24`/`20`. The `24` is what `grep -rn 'pass_at'` — no `=` — returns: the 22 call sites plus the schema declaration `src/film_pipeline/schemas/registries/validator_registry.py:17` `pass_at: float = Field(default=85.0, ge=0, le=100)` and the reader `src/film_pipeline/validation/thresholds.py:23` `if score >= t.pass_at:`. The count is 22 explicit literals; corrected per `reviews/verify-03.md` and re-derived above.)* The zero-width claim is best re-derived by AST rather than grep:
  ```bash
  .venv/bin/python -c "import ast,pathlib; C=[dict((k.arg,k.value.value) for k in n.keywords if k.arg) for p in pathlib.Path('src/film_pipeline').rglob('*.py') for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,ast.Call) and getattr(n.func,'id',None)=='ValidatorThresholds']; C=[c for c in C if c]; print(len(C), sum(1 for c in C if c['review_at']==c['block_below']))"
  ```
  → `22 22`
- **Blast radius:** `validation`, `schemas/registries`. Any human-facing validation verdict
  sits on the wrong side of the block line; a "needs revision" score is reported as blocked.
- **Candidate owner module:** `schemas/registries` — one `ValidatorThresholds` vocabulary and
  one published band table; `validation` consumes it and must not re-spell literals.
- **Extraction sketch:** add named band constants (`DEFAULT_BANDS`, `STRICT_BANDS`) beside
  `ValidatorThresholds` and replace all 22 literals with references; guard test asserts
  `t.block_below < t.review_at` for every registered entry and that no `ValidatorThresholds(`
  literal appears outside `schemas/registries`.
- **Prior art:** `documentation/reviews/hardcoded-values-inventory.md:146-152` and
  `profiles/base.studio.yaml:103-107` both record that profile-configured thresholds do not
  reach validators. **What is new:** the divergence is *inside* code between the class
  default and the call-site literals, which is independent of the profile-wiring gap.
- **Verifier:** CORRECTED by `reviews/verify-03.md` — the behaviour claim holds and is
  stronger than revision 1 stated (22 of 22, not 20 of 24); the denominator and both grep
  results were wrong and are fixed above.

---

### F-CFG-05 — Provider-lineup parsing: the conflict validator understands one of the two profile shapes

- **Class:** O1
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** Which providers make up a project's lineup, and whether that lineup is all-free/all-mock.
- **De-facto owners:**
  - `src/film_pipeline/config/validator.py:26` — reads only the `order` list — `provider_order: list[str] = (resolved.get("providers", {}) or {}).get("order", [])`
  - `src/film_pipeline/config/profile_resolver.py:83-88` — handles both shapes — `specs = _specs_from_typed_sections(providers) + _specs_from_order_list(providers)`
  - `src/film_pipeline/graph/nodes/_context.py:434-448` — a third, independent two-shape parser — `order = providers.get("order", [])` … `video = providers.get("video")`
- **Drift proof:** **existing divergence, executed.** `profiles/mock-demo.yaml:15-21` and
  `profiles/local-real-provider.yaml:16-22` declare providers under `providers.video[].provider_id`
  with no `order` key. Resolving a festival stack against the all-mock profile therefore
  yields no conflict:
  ```
  .venv/bin/python -c "
  from film_pipeline.config.resolver import ConfigResolver
  r=ConfigResolver().resolve(['base.studio','film-type.narrative','quality.festival','mock-demo'])
  print([(c.code,c.severity) for c in r.conflicts], (r.raw['providers'] or {}).get('order',[]))"
  ```
  → `[] []` (no conflict; `order` empty), while the same lineup expressed as an `order`
  list *does* fire the documented blocking check —
  `ConfigResolver().validator.validate({... 'providers': {'order': ['mock-video-provider']}})`
  → `[('festival_free_conflict', 'blocking')]`. Meanwhile
  `profile_resolver.provider_specs_from_raw` on the same raw config returns both mock
  providers, so the resolver and the validator disagree about what the lineup *is*.
- **Reproduce:**
  ```bash
  .venv/bin/python -c "from film_pipeline.config.resolver import ConfigResolver; r=ConfigResolver().resolve(['base.studio','film-type.narrative','quality.festival','mock-demo']); print([(c.code,c.severity) for c in r.conflicts], (r.raw['providers'] or {}).get('order',[]))"
  # -> [] []
  .venv/bin/python -c "from film_pipeline.config.validator import ConfigValidator; print([(c.code,c.severity) for c in ConfigValidator().validate({'quality_profile':'festival','providers':{'order':['mock-video-provider']}})])"
  # -> [('festival_free_conflict', 'blocking')]
  ```
- **Blast radius:** `config`, `graph/nodes/_context`, `mcp/tools/planning`. A festival-quality
  project on a zero-cost mock lineup passes the pre-start config gate
  (`mcp/tools/projects.py:70-88` `_validate_resolved_profile`) that exists precisely to stop it.
- **Candidate owner module:** `config` — one provider-lineup normalizer; `validator.py` and
  `_context._preferred_providers` must call it instead of re-parsing.
- **Extraction sketch:** make `provider_specs_from_raw` the single parser; have
  `_detect_festival_free_conflict` and `_preferred_providers` consume its output. Guard test:
  for every file in `profiles/`, assert the validator's free-only verdict and the resolver's
  ordered provider list are derived from the same normalized spec list.
- **Prior art:** new. `documentation/reviews/hardcoded-values-inventory.md` §F covers provider
  *pricing*, not lineup shape parsing.

---

### F-CFG-06 — The budget cap is spelled five ways; the profile value never reaches `BudgetState`

- **Class:** O1
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** The project's spend cap, its auto-approval threshold, and the phase split.
- **De-facto owners:**
  - `profiles/base.studio.yaml:33-37` — the profile vocabulary — `project_cap_usd: 100` / `per_phase_cap_usd: 25` / `max_auto_approved_cost_usd: 1.0` / `human_approval_above_usd: 5.0`
  - `profiles/local-real-provider.yaml:36-39` — a second profile vocabulary for the same concern — `max_total_usd: 100.0` / `auto_approve_up_to: 2.50` / `per_clip_limit: 10.0`
  - `src/film_pipeline/graph/nodes/_context.py:424` — a reader that hardcodes the try-both-order — `for key in ("project_cap_usd", "max_total_usd"):`
  - `src/film_pipeline/mcp/tools/planning.py:22` — the runtime default that actually decides the cap — `cap = float(cast(float, args.get("cap_usd", 100.0)))`
  - `src/film_pipeline/schemas/budget.py:44` — a third default for the same knob — `human_approval_above_usd: float = Field(default=1.0, ge=0)`
  - `src/film_pipeline/schemas/project.py:43` and `src/film_pipeline/schemas/constraints.py:93` — the **fifth** spelling, `budget_cap_usd` — `budget_cap_usd: float | None = Field(default=None, ge=0, description="Hard spend cap.")`; written from idea extraction at `constraints/extractor.py:154` (`"budget_cap_usd": self._extract_budget(normalized),`) and `agents/impl/intake_agent.py:49` (`budget_cap_usd=_coerce_budget_cap(data.get("budget_cap_usd")),`), and prompted for at `agents/prompt_templates/defaults/spine.py:170` (`'  "budget_cap_usd": null,\n'`)
- **Drift proof:** **existing divergence + an unwired profile value.**
  (a) `human_approval_above_usd` has the value `5.0` at `profiles/base.studio.yaml:37` and at
  `mcp/tools/planning.py:43` (`human_approval_above_usd=5.0,`) but `1.0` in the schema
  (`schemas/budget.py:44`); a `BudgetState` built without the explicit kwarg (as at
  `tests/unit/test_schemas.py:671`) approves spend up to 1.0, not 5.0.
  (b) The profile cap never reaches the persisted budget: `initialize_budget` reads only
  `args.get("cap_usd", 100.0)` and `BudgetState` is constructed nowhere else in `src/`
  (`grep -rn 'BudgetState(' src/film_pipeline` → one site, `mcp/tools/planning.py:33`). Mutation: set
  `budget.project_cap_usd: 5` in a profile layer; `BudgetState.cap_usd` stays 100.0 and
  **no test fails** — `tests/unit/test_config.py:200` asserts the resolved dict, not the
  budget artifact.
  (c) A fourth spelling, `cap_usd`, is read by the planner context
  (`graph/context_packets.py:122` `cap = budget.get("cap_usd", 0) if isinstance(budget, dict) else 0`).
  (d) A fifth spelling, `budget_cap_usd`, is carried on `ProjectProfile`
  (`schemas/project.py:43`) and `ProjectConstraints` (`schemas/constraints.py:93`) and is
  written by the extractor (`constraints/extractor.py:154`) and the intake agent
  (`agents/impl/intake_agent.py:49`). It is never mapped to `BudgetState.cap_usd`: the five
  `budget_cap_usd` occurrences in `src/` are two schema declarations
  (`schemas/project.py:43`, `schemas/constraints.py:93`), two write sites
  (`constraints/extractor.py:154`, `agents/impl/intake_agent.py:49`) and one prompt-template
  string (`agents/prompt_templates/defaults/spine.py:170`) — no reader — and the only
  `BudgetState(...)` construction site in `src/` is `mcp/tools/planning.py:33`. So a
  `budget_cap_usd` extracted from the idea text and a `project_cap_usd` declared in a profile
  both fail to reach the object that gates spend, which reads only the `cap_usd` tool
  argument default.
- **Reproduce:** `grep -rnE 'project_cap_usd|per_phase_cap_usd|max_total_usd|auto_approve_up_to|max_auto_approved_cost_usd|human_approval_above_usd|per_clip_limit|budget_cap_usd' profiles/ src/film_pipeline --include='*.yaml' --include='*.py'` → 23 matches (12 in `profiles/` across 5 files, 11 in `src/`); drop the `budget_cap_usd` alternative and it is 18. *(Revision 1's pattern also omitted `per_phase_cap_usd` and `budget_cap_usd` and reported "four ways"; corrected per `reviews/verify-03.md`.)*
- **Blast radius:** `config`, `graph/nodes/_context`, `graph/context_packets`,
  `mcp/tools/planning`, `schemas/budget`, `schemas/project`, `schemas/constraints`,
  `constraints`, `agents/impl`. The advertised spend cap is decorative; the
  effective cap is a tool argument default, and a cap stated in the idea text reaches a
  field that nothing reads.
- **Candidate owner module:** `schemas/budget` (vocabulary) + `config` (profile mapping) —
  one `BudgetPolicy` type with one profile key path; `initialize_budget` must project the
  resolved config, not `args.get`.
- **Extraction sketch:** declare `budget:` keys once in the schema; have
  `initialize_budget` read `state["resolved_config"]["budget"]` and fail loudly on an
  unknown key. Guard test: assert no reader contains a two-key fallback tuple, and that
  every `budget.*` leaf in `profiles/` maps to a declared field.
- **Prior art:** §C of `documentation/reviews/hardcoded-values-inventory.md:84-88` lists the
  budget-gate knobs as awaiting spend tracking. **What is new:** the *key vocabulary* split
  (five spellings, across the profile, schema, runtime and extraction layers) and the
  demonstrated non-arrival of the profile cap at `BudgetState`.
- **Verifier:** CONFIRMED, with a missed fifth spelling added per `reviews/verify-03.md`.

---

### F-CFG-07 — The profile-stack key set is defined three times

- **Class:** O1
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** The ordered set of profile slots that make up a project's stack, and their layering order.
- **De-facto owners:**
  - `src/film_pipeline/config/profile_resolver.py:34-40` — key→prefix mapping — `mapping = {` … `"auto_approve_profile": ("",),`
  - `src/film_pipeline/config/profile_resolver.py:56-62` — the same five keys again as the merge order — `for key in (\n        "film_type_profile",\n        "quality_profile",`
  - `src/film_pipeline/mcp/tools/_profile_change.py:36-42` — a third copy as the accepted-args tuple — `_PROFILE_STACK_KEYS = (\n    "film_type_profile",`
- **Drift proof:** mutation scenario. Add a sixth slot `"delivery_profile"` to
  `src/film_pipeline/mcp/tools/_profile_change.py:36-42` only. `propose_profile_change` (`src/film_pipeline/mcp/tools/_profile_change.py:64-69`)
  accepts the argument, `_merge_profile_changes` stores it, and
  `resolve_project_config` (`src/film_pipeline/config/profile_resolver.py:51-68`) silently ignores it because its
  order list at `:56-62` and mapping at `:34-40` do not know the key. The projected diff
  comes back empty and the proposal reports "no change"; **no test fails** — the contract
  test enumerates *profile file* leaves (`tests/unit/config/test_config_contract.py:298`),
  not stack keys. The reverse edit (adding the key to `profile_resolver.py` only) makes
  `propose_profile_change` reject a legitimate request.
- **Reproduce:** `grep -rn 'quality_profile' src/film_pipeline/config/profile_resolver.py src/film_pipeline/mcp/tools/_profile_change.py`
- **Blast radius:** `config`, `mcp/tools/_profile_change`, `app/services/operator`,
  `mcp/tools/projects`. A profile slot can be half-added: accepted at the tool surface,
  dropped at resolution.
- **Candidate owner module:** `config` — one `PROFILE_STACK_SLOTS` ordered tuple with
  declared prefixes; all three sites consume it.
- **Extraction sketch:** export `STACK_SLOTS: tuple[ProfileSlot, ...]` from `config`; derive
  the mapping, the merge order, and `_PROFILE_STACK_KEYS` from it. Guard test: assert the
  tool's accepted key tuple equals the resolver's ordered slot tuple.
- **Prior art:** new.

---

### F-CFG-08 — `FILM_PIPELINE_NO_PERSIST` is one policy decision re-derived in six modules

- **Class:** O5
- **Severity:** High (impact 4 × drift 3 = 12)
- **Concern:** Whether the process persists state and artifacts durably.
- **De-facto owners (7 read sites, 6 modules):**
  - `src/film_pipeline/app/_persistence.py:51-53` — the declared owner —
    `return bool(os.getenv("FILM_PIPELINE_PERSIST_STATE")) and not bool(\n        os.getenv("FILM_PIPELINE_NO_PERSIST")\n    )`
  - `src/film_pipeline/graph/services.py:31` — `if os.getenv("FILM_PIPELINE_NO_PERSIST"):` (chooses a temp artifact root)
  - `src/film_pipeline/graph/services.py:48` — `profile = PROFILE_SANDBOX if os.getenv("FILM_PIPELINE_NO_PERSIST") else PROFILE_PRODUCTION` (chooses a storage profile)
  - `src/film_pipeline/graph/graph.py:43` — `if os.getenv("FILM_PIPELINE_NO_PERSIST") or not os.getenv("FILM_PIPELINE_PERSIST_STATE"):` (chooses the checkpointer)
  - `src/film_pipeline/app/logging_setup.py:80` — `if os.getenv("FILM_PIPELINE_NO_PERSIST")` (file-handler choice)
  - `src/film_pipeline/mcp/server.py:243` — `if not os.getenv("FILM_PIPELINE_NO_PERSIST"):`
  - `src/film_pipeline/cli/run.py:226` — `persist_enabled=not bool(os.getenv("FILM_PIPELINE_NO_PERSIST")),`
- **Drift proof:** the readers do not agree on the *combination* of flags.
  `app/_persistence.py:51-53` requires `PERSIST_STATE` **and** not `NO_PERSIST`;
  `graph/graph.py:43` applies the same conjunction; but `graph/services.py:31` and `:48`,
  `src/film_pipeline/app/logging_setup.py:80`, `mcp/server.py:243` and `cli/run.py:226` test `NO_PERSIST`
  **alone**. Mutation: set `FILM_PIPELINE_NO_PERSIST=0` (a falsy-but-set string, which
  `os.getenv` returns as `"0"` — truthy). `use_persistent_runtime` treats `"0"` as
  "no-persist on"; `mcp/server.py:243` likewise. But add a third flag-shaped variant — set
  `FILM_PIPELINE_PERSIST_STATE` absent and `FILM_PIPELINE_NO_PERSIST=0`: `graph/graph.py:43`
  returns `MemorySaver()` while `cli/run.py:226` computes `persist_enabled=False` and
  `src/film_pipeline/graph/services.py:48` picks `PROFILE_SANDBOX` — three sites, three independent derivations, and
  **no test fails** because each is tested only through its own module (e.g.
  `tests/unit/app/test_logging_setup.py:149`, `tests/unit/test_entrypoints.py:34`).
- **Reproduce:** `grep -rn 'FILM_PIPELINE_NO_PERSIST' src/film_pipeline --include='*.py'`
- **Blast radius:** `app`, `graph`, `mcp`, `cli`. A mis-set flag can persist artifacts to a
  real root while the graph checkpointer stays in memory (or the reverse), producing a
  project that appears durable and resumes empty.
- **Candidate owner module:** `app/_persistence` — already the declared owner; every other
  site must call `use_persistent_runtime()`.
- **Extraction sketch:** make `use_persistent_runtime()` the only `FILM_PIPELINE_*PERSIST*`
  reader; pass the resolved boolean down (`GraphServices.for_*`, `configure_logging`,
  `_default_checkpointer`). Guard test: assert the string `FILM_PIPELINE_NO_PERSIST` occurs
  in exactly one source file.
- **Prior art:** none at HEAD. There is no committed ownership-declaration layer in this
  checkout (`src/film_pipeline/architecture.py` does not exist; see §7 and H1). During the
  original audit a concurrent agent briefly held an uncommitted draft that declared this
  concern as a policy point owned by `app/_persistence.py` with the same six reader modules
  and seven exemptions; that draft is now absent and post-dated `fb85baa`, so it **cannot**
  be cited as prior art. This audit reaches the conclusion from HEAD evidence alone, and the
  single-reader guard above is the only proposed enforcement. The
  findings are convergent, not copied.

---

### F-CFG-09 — `profile_stack` has three writers, and they disagree about the environment override

- **Class:** O3
- **Severity:** High (impact 4 × drift 3 = 12)
- **Concern:** The persisted profile stack that identifies which profiles a project ran under.
- **De-facto owners (writers):**
  - `src/film_pipeline/app/services/operator.py:143` — `state["profile_stack"] = profile_stack` (writes the canonicalized request stack, uncorrected)
  - `src/film_pipeline/mcp/tools/projects.py:115` — `state["profile_stack"] = effective_stack` (writes a stack **patched from the resolved config**)
  - `src/film_pipeline/mcp/tools/_profile_change.py:280` — `state["profile_stack"] = new_stack` (writes the approved proposal stack)
- **Drift proof:** **existing divergence between two writers of the same state key.**
  `mcp/tools/projects.py:107-113` re-derives the quality slot from the *resolved* config —
  `quality = str(raw_config.get("quality_profile", "")).strip()` … `effective_stack["quality_profile"] = (quality if quality.startswith("quality.") else f"quality.{quality}")` —
  which is the value `FILM_PIPELINE_QUALITY` wrote via `config/runtime_overrides.py:13`
  (`"FILM_PIPELINE_QUALITY": ("quality_profile",),`). `OperatorService._resolve_and_store_profiles`
  (`app/services/operator.py:132-146`) writes the stack from `canonicalize_profile_stack`
  with **no** such correction, even though it then resolves the same config. Mutation: run
  `create_film_project` through the MCP tool and through `OperatorService` with
  `FILM_PIPELINE_QUALITY=festival`; the two paths persist different `profile_stack` values
  for identical inputs, and **no test fails** — the operator-path test asserts the resolved
  config, not the stack (`tests/unit/app/services/test_operator_service.py`).
- **Reproduce:** `git show HEAD:src/film_pipeline/mcp/tools/projects.py | sed -n '105,120p'` vs `git show HEAD:src/film_pipeline/app/services/operator.py | sed -n '132,146p'`
- **Blast radius:** `app/services`, `mcp/tools`, reproducibility of the resolved-config
  artifact (`mcp/tools/_profile_change.py:434-454` persists `profile_stack` as the project
  contract). Two projects with identical profiles can record different contracts.
- **Candidate owner module:** `config` — a single `apply_env_overrides_to_stack()` (or a
  single `ProjectConfigRecord` writer) that both call paths use.
- **Extraction sketch:** one function `record_project_config(state, request)` in `config`
  used by both `operator` and `projects`; guard test asserts the two entry points produce an
  identical `(profile_stack, resolved_config)` pair for the same request under a set env var.
- **Prior art:** none at HEAD — see §7 and H1: no state-channel declaration layer exists in
  this checkout, and the brief uncommitted draft observed during the original audit is now
  absent. Nothing outside this audit records `profile_stack` as a single-writer channel.

---

### F-CFG-10 — `resolved_review_strategy` is read from resolved config but has no writer, and no profile key

- **Class:** O8
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** How the multi-model review strategy declared in the profile stack reaches agent routing.
- **De-facto owners / broken seam:**
  - `src/film_pipeline/graph/_agent_routing.py:204-211` — the reader, documented as profile-driven — `def _resolve_review_strategy(state: dict[str, Any]) -> str:\n    """Resolve the review strategy from the active profile's resolved config."""` … `strategy = resolved_config.get("resolved_review_strategy", "")` (`:208`)
  - `src/film_pipeline/schemas/project.py:62` — a state field nobody writes — `resolved_review_strategy: str = Field(description="Review strategy applied.")`
  - `profiles/base.studio.yaml:18` (and `profiles/quality.draft.yaml:2-4`, `profiles/review.strict_continuity.yaml:1-4`) — the profile key that is actually declared — `strategy: multi_model_panel`, `min_reviewers: 2`
- **Drift proof:** an existing structural gap, verified by exhaustive grep across
  `src/`, `tests/`, `profiles/` and both doc trees: the only three occurrences of
  `resolved_review_strategy` are the reader (`src/film_pipeline/graph/_agent_routing.py:208`), the schema field
  (`schemas/project.py:62`) and one test keyword (`tests/unit/test_schemas.py:177`). **No
  production code writes it.** `AgentRouteResult.review_strategy` therefore always falls back
  to its `"single"` default (`src/film_pipeline/graph/_agent_routing.py:27`), even though four profile files declare
  `review.strategy: multi_model_panel`. The key names also differ (`review.strategy` vs
  `resolved_review_strategy`), so even a writer of `resolved_config["review"]` would not be
  found. Mutation: set `review.strategy: single` in a quality profile; routing is unchanged
  (already single), and **no test fails** — `tests/unit/config/test_config_contract.py:66-75`
  explicitly lists `("review", "strategy")` in `KNOWN_DEAD_GROUPS` as "not implemented".
- **Reproduce:** `grep -rn 'resolved_review_strategy\|review.*strategy' src/film_pipeline profiles --include='*.py' --include='*.yaml'`
- **Blast radius:** `graph/_agent_routing`, `config`, `validation/consensus`. The
  multi-reviewer consensus builder exists (`validation/consensus.py:17-55`) but nothing
  connects a profile's `min_reviewers`/`strategy` to it; the human-facing review depth is
  always single.
- **Candidate owner module:** `config` — publish a single `resolved_review_policy` block
  from the resolved config; `graph/_agent_routing` reads that key only.
- **Extraction sketch:** in `config`, project `review.strategy` → `review_policy.strategy`
  at resolve time; delete `resolved_review_strategy` from the schema or make `config` the
  only writer. Guard test: assert the key read at `src/film_pipeline/graph/_agent_routing.py:208` is written by
  `config` (the `READERS`-annotation style of `tests/unit/config/test_config_contract.py:144-192`), and that
  `KNOWN_DEAD_GROUPS` no longer contains `("review", "strategy")`.
- **Prior art:** `documentation/reviews/hardcoded-values-inventory.md:60-65` records
  `review.strategy` as a deferred unread key. **What is new:** the reader on the *consumer*
  side (`src/film_pipeline/graph/_agent_routing.py:208`) that reads a differently-named key nothing writes — the
  seam is not merely unwired, it is mis-keyed.

---

### F-CFG-11 — Two environment-resolution policies: provider credentials fall back to `.env`, config knobs do not

- **Class:** O5
- **Severity:** Medium (impact 2 × drift 3 = 6)
- **Concern:** How an environment-sourced setting is resolved (process env only, or env-then-`.env`).
- **De-facto owners:**
  - `src/film_pipeline/providers/credentials.py:46-52` — env-then-`.env` — `env_value = os.environ.get(env_var)` … `dotenv_value = _read_dotenv(Path.cwd()).get(env_var)`
  - `src/film_pipeline/config/runtime_overrides.py:35-44` — process env only — `env = os.environ if environ is None else environ`
  - `src/film_pipeline/app/runtime.py:456` — process env only — `return _normalize_server_mode(os.getenv("FILM_PIPELINE_MCP_MODE", "mock"))`
- **Drift proof:** mutation scenario. Put `FILM_PIPELINE_QUALITY=festival` in `./.env` and
  nothing in the process env. `src/film_pipeline/config/resolver.py:46` (`os.getenv("FILM_PIPELINE_QUALITY", "").strip()`)
  and `src/film_pipeline/config/runtime_overrides.py:38` (`raw_value = env.get(env_var)`) both see nothing, so the
  project resolves at `studio` quality — while `OPENROUTER_API_KEY` in the same `.env` file
  *is* honoured (`src/film_pipeline/providers/credentials.py:49`), so real generation proceeds. **No test fails**:
  `.env` behaviour is tested only for credentials. `.env` support is also CWD-relative
  (`src/film_pipeline/providers/credentials.py:49` `Path.cwd()`), so it is unavailable to a service started elsewhere.
- **Reproduce:** `grep -rn 'os.getenv\|os.environ' src/film_pipeline --include='*.py'` and compare with `grep -rn 'env_or_dotenv' src/film_pipeline --include='*.py'`
- **Blast radius:** `config`, `app`, `providers`. Operators reasonably expect one `.env` to
  configure the studio; half of it silently does not apply.
- **Candidate owner module:** `config` — one `EnvironmentSource` used by the override table,
  the mode resolver, and the credential lookup (the last delegating to `providers` for the
  secret-name map).
- **Extraction sketch:** expose `config.environment.get(name)` with the env-then-`.env`
  policy; route `runtime_overrides`, `_configured_server_mode`, `_persistence`, and
  `credentials.env_or_dotenv` through it. Guard test: assert a `.env` file in a temp CWD
  affects both a `FILM_PIPELINE_*` override and a credential lookup.
- **Prior art:** new.

---

### F-CFG-12 — `profiles/` is located twice from the process CWD, and `config`'s public API omits its own resolver

- **Class:** O7 / O8
- **Severity:** Medium (impact 3 × drift 2 = 6)
- **Concern:** Where the profile corpus lives, and which module the profile-resolution contract belongs to.
- **De-facto owners:**
  - `src/film_pipeline/config/loader.py:30` — `profiles_dir: Path = Path("profiles")`
  - `src/film_pipeline/app/bootstrap.py:32` — `if Path("profiles").is_dir():`
  - `src/film_pipeline/kb/paths.py:10-13` — the same CWD-relative corpus-root pattern for the KB manifest, second instance — `candidates = (\n        Path("film-knowledge-base/manifest.yaml"),\n        Path("film-knowledge-base/index/kb-manifest.yaml"),\n    )`
  - `src/film_pipeline/app/smoke.py:55` — a third copy that hardcodes only one of those two candidates and skips the probe order — `path = Path("film-knowledge-base/index/kb-manifest.yaml")`
  - `src/film_pipeline/config/__init__.py:11-21` — the declared public API, which does **not** name the profile-resolution surface — `__all__ = [\n    "ENV_OVERRIDE_MAP",`
- **Drift proof:** (a) The relative root is resolved against `Path.cwd()` in two modules that
  never consult each other, and `src/film_pipeline/app/bootstrap.py:34` reports
  `"profiles/ directory not found. Create it with at least one profile YAML."` while
  `src/film_pipeline/config/loader.py:37` raises `f"Profile not found: {path}"` — a different message for the same
  missing corpus. Mutation: run the CLI from a subdirectory; `bootstrap_ok()`
  (`src/film_pipeline/app/bootstrap.py:25-27`) returns `False` and `ProfileLoader().load(...)` raises, but
  **no test fails** — `tests/conftest.py:30` sets `FILM_PIPELINE_STORAGE_ROOT` to an absolute
  temp path and the tests `chdir` nowhere, so every test runs from the repo root.
  (a′) The identical pattern recurs one package over: `app/bootstrap.py:38` probes the KB
  manifest only through `kb_manifest_path()` (`if kb_manifest_path().exists():`), but
  `app/smoke.py:55` bypasses that helper and hardcodes
  `Path("film-knowledge-base/index/kb-manifest.yaml")` directly. The two disagree about the
  candidate list: `kb_manifest_path()` also accepts `film-knowledge-base/manifest.yaml`, so a
  checkout that satisfies the bootstrap reports "Manifest not found" from the smoke check.
  Both are CWD-relative, so both silently evaluate to nothing outside the repo root, and no
  test covers either path (`tests/conftest.py:30` never `chdir`s).
  (b) `git show HEAD:src/film_pipeline/config/__init__.py | grep -c profile_resolver` → `0`,
  yet 5 modules reach the submodule directly:
  `from film_pipeline.config.profile_resolver import …` at `mcp/tools/_profile_change.py:21`,
  `mcp/tools/config.py:12`, `mcp/tools/planning.py:9`, `mcp/tools/projects.py:8`,
  `mcp/tools/helpers.py:14`. The `config` package's advertised contract (9 exported names) is
  not the surface its callers use.
- **Reproduce:** `grep -rn 'Path("profiles")' src/film_pipeline --include='*.py'` → 2; `grep -rn 'Path("film-knowledge-base' src/film_pipeline --include='*.py'` → 3 (`kb/paths.py:11-12`, `app/smoke.py:55`); `grep -rn 'config.profile_resolver import' src/film_pipeline --include='*.py' | wc -l` → `5`
- **Blast radius:** `config`, `app`, `kb`, `mcp/tools`. Editor/test tooling and any non-root
  invocation silently sees zero profiles *and* zero KB manifest; the config package cannot
  enforce a boundary on a contract it does not declare.
- **Candidate owner module:** `config` — own the corpus root (absolute, overridable through
  the `EnvironmentSource` of F-CFG-11) and re-export `load_profile_flex`,
  `canonicalize_profile_stack`, `resolve_project_config`, `provider_specs`,
  `register_project_providers`, `missing_provider_credentials` in `__all__`.
- **Extraction sketch:** `config.profiles_root()` resolving an absolute path once;
  `bootstrap` calls it instead of probing CWD; add the six names to `config.__all__` and a
  boundary test asserting no module imports the `config.profile_resolver` submodule path.
- **Prior art:** new.

---

### F-CFG-13 — Hardcoded numeric defaults that duplicate a profile value

- **Class:** O5
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** The numeric defaults for generation timing, provider duration limits, and reviewer scoring.
- **De-facto owners (counts are mechanical; see §4 for the full table):**
  - `profiles/base.studio.yaml:89` — `duration_seconds: 1` (and `profiles/quality.draft.yaml:8`)
    vs **9** sites defaulting the shot duration to `5`, e.g.
    `src/film_pipeline/generation/executor.py:178` — `duration = float(shot_row.get("duration_seconds", 5) or 5)`
  - `profiles/provider.seedance_primary.yaml:9` — `max_duration_seconds: 15` vs
    `src/film_pipeline/providers/factory.py:65` — `max_duration_seconds=15,` and
    `src/film_pipeline/providers/factory.py:100` — `max_duration_seconds=30,` (and `:74` `15`, `:83` `1`, `:92` `1`)
  - `src/film_pipeline/schemas/registries/validator_registry.py:17` — `pass_at: float = Field(default=85.0` vs
    `src/film_pipeline/generation/frame_reviewer.py:43` — `_PASS_THRESHOLD = 28.0` (a 28/40 = 70% pass bar, unrelated to the 85/75 band)
- **Drift proof:** mutation scenario for each. Set `generation.duration_seconds: 12` in a
  quality profile; none of the 9 `duration_seconds` readers consults `generation`, so the
  effective default stays 5 and **no test fails** —
  `tests/unit/config/test_config_contract.py:99` lists `("generation", "duration_seconds")` in
  `KNOWN_DEAD_GROUPS`, i.e. the deadness is *declared*, which is exactly why it cannot
  regress loudly. Set `providers.max_duration_seconds: 8` in a provider profile; the built
  adapter keeps the factory literal (`src/film_pipeline/providers/factory.py:65`) because
  `build_provider_adapter` (`src/film_pipeline/providers/factory.py:18-32`) never reads it, and
  `tests/unit/config/test_config_contract.py:131` again lists it as known-dead.
- **Reproduce:**
  ```bash
  grep -rcE '"duration_seconds", *5' src/film_pipeline --include='*.py' | grep -v ':0' | awk -F: '{s+=$2} END {print s}'   # -> 9
  grep -rn 'max_duration_seconds=' src/film_pipeline/providers/factory.py   # -> 5 sites: :65 15, :74 15, :83 1, :92 1, :100 30
  grep -rn '_PASS_THRESHOLD' src/film_pipeline/generation/ --include='*.py'   # -> frame_reviewer.py:43 definition, :222 use
  ```
- **Blast radius:** `generation`, `providers`, `mcp/tools`, `app/services`. Planned shot
  durations and provider limits disagree with the operator's profile, and can exceed
  provider single-clip limits.
- **Candidate owner module:** `config` — the profile is the only place these numbers are
  declared; the readers must receive them (or the keys must be deleted from `profiles/`).
- **Extraction sketch:** delete the dead profile keys, or thread them through
  `GraphServices`/`ProviderRegistryEntry` and remove the literals. Guard test: for each
  numeric profile leaf, assert either a reader exists or the key is absent (tighten
  `KnownDead` so the count of known-dead numeric leaves can only go down).
- **Prior art:** §C and §G of `documentation/reviews/hardcoded-values-inventory.md`
  (lines 109-152, 215-224) cover the underlying dead-config pattern. **What is new:** the
  counts (9 duration sites, 5 factory capability literals), the `frame_reviewer`
  `_PASS_THRESHOLD` bar, and the observation that the known-dead registry *codifies* the
  drift rather than preventing it.

---

### F-CFG-14 — The pacing mapping rule is split between two alias tables with partly disjoint key alphabets and an unpinned silent fallback

- **Class:** O1
- **Severity:** Medium (impact 2 × drift 4 = 8) — *re-scoped and re-scored from High (impact 3 × drift 4 = 12) by `reviews/verify-16.md` §2.5, which measured the two tables as agreeing on every shared key; impact 2 because no production path composes the asymmetry and no currently shipped value is wrong, drift 4 because adding a key to one table alone passes CI.*
- **Concern:** Which lexicon a raw pacing string goes through — the profile / film-type vocabulary or free-text prose — and what happens when the string is absent from the table it reaches. Two alias tables implement the rule with partly disjoint key alphabets, four alias rows are duplicated verbatim, and an unknown key falls through to `standard` silently.
- **De-facto owners (the mapping-rule half only; the schema-declaration half is `F-ARTIFACT-14`'s):**
  - `src/film_pipeline/graph/scope_contract.py:33-46` — mapping table #1, the profile / film-type lexicon (10 keys) — `_PACING_ALIASES: dict[str, str] = {`
  - `src/film_pipeline/constraints/_keywords.py:46-57` — mapping table #2, the free-prose lexicon (10 keys) — `_PACING_KEYWORDS: dict[str, str] = {`
  - `src/film_pipeline/graph/scope_contract.py:64` — table #1's only read, with the unknown-key fallthrough — `canon = _PACING_ALIASES.get(str(pacing).strip().lower())`
  - `src/film_pipeline/graph/scope_contract.py:125-126` — the second silent fallthrough, on the shot-duration lookup — `canon = _PACING_ALIASES.get(str(pacing_style or "").strip().lower(), STANDARD)` / `return _DENSITY.get(canon, _DENSITY[STANDARD])[0]`
  - `src/film_pipeline/constraints/extractor.py:232-236` — table #2's only consumer — `keyword = _first_matching_keyword(text, _PACING_PREFERENCE)` … `return _PACING_KEYWORDS[keyword]`
  - `src/film_pipeline/graph/scope_contract.py:17-19` — the three canonical constants both tables target — `SLOW_CINEMA = "slow_cinema"` / `STANDARD = "standard"` / `DYNAMIC = "dynamic"`
- **Drift proof:** *asymmetric coverage with a silent, unpinned fallback — not two tables returning different answers.* Measured directly: **7 shared keys, 0 value conflicts** — the three canonical spellings plus the four alias rows `action`, `contemplative`, `fast` and `meditative` carry identical values in both tables. The divergence is the **key alphabets**: table #2 alone knows `slow` / `slow cinema` / `moderate`; table #1 alone knows `character_driven` / `irregular` / `narrative`. Silent failure: a raw `slow cinema` that reaches table #1's entry point is not rejected — `normalize_pacing("slow cinema", None)` and `avg_shot_duration_for("slow cinema")` return `standard` / `6.5` (6.5 s/shot), while table #2 assigns the same words `slow_cinema` (9.0 s/shot). The fallthrough is documented and test-pinned (`tests/unit/graph/test_scope_contract.py:30` `assert normalize_pacing("nonsense", "also_nonsense") == "standard"`), so nothing raises and nothing counts the substitution. No test compares the two tables, so adding the missing key to exactly one of them passes CI. The executed substitution is real arithmetic but latent: no shipped profile feeds a table-#2-only key to table #1, and the one production path that composes the fallback — the unvalidated `ExecutionBrief.pacing_style` bridge — is **`F-ARTIFACT-14`'s** harm chain (audit 07), not re-argued here. **Withdrawn by `reviews/verify-16.md` §2.3:** the earlier claim that the two lookup tables "return different canonical values for the same input" is false — every shared key agrees — so the divergence is asymmetric coverage, not disagreement.
- **Reproduce:**
  ```bash
  .venv/bin/python -c "from film_pipeline.constraints._keywords import _PACING_KEYWORDS as K; from film_pipeline.graph.scope_contract import _PACING_ALIASES as A, normalize_pacing, avg_shot_duration_for; common=sorted(set(K)&set(A)); print('common keys:', common); print('value conflicts on common keys:', {k:(K[k],A[k]) for k in common if K[k]!=A[k]}); print('constraints-only:', sorted(set(K)-set(A))); print('scope-only:', sorted(set(A)-set(K))); print('slow cinema ->', K['slow cinema'], 'vs', normalize_pacing('slow cinema', None), '| avg_shot', avg_shot_duration_for('slow cinema'))"
  ```
  ```
  common keys: ['action', 'contemplative', 'dynamic', 'fast', 'meditative', 'slow_cinema', 'standard']
  value conflicts on common keys: {}
  constraints-only: ['moderate', 'slow', 'slow cinema']
  scope-only: ['character_driven', 'irregular', 'narrative']
  slow cinema -> slow_cinema vs standard | avg_shot 6.5
  ```
- **Blast radius:** `graph/scope_contract` (the density model: an unrecognized pacing value silently plans standard shot durations), `constraints/extractor` (the prose lexicon), and the prompt templates that interpolate `{pacing_style}` (`src/film_pipeline/agents/prompt_templates/defaults/spine.py:36`, `:54`). A profile or operator who writes a prose form into a pacing field gets standard pacing with no message. `profiles/film-type.narrative.yaml:4` (`pacing: character_driven`) and `profiles/film-type.experimental.yaml:4` (`pacing: irregular`) are handled only by table #1; `slow cinema` / `slow` / `moderate` only by table #2.
- **Candidate owner module:** `schemas` — publishes one `PacingStyle` vocabulary (the schema-declaration half owned by `F-ARTIFACT-14`) plus one `normalize_pacing(raw) -> PacingStyle`; both tables become views over it.
- **Extraction sketch:** merge `_PACING_ALIASES` and `_PACING_KEYWORDS` into one table on the owner, keyed by the union of both alphabets, and route `constraints/extractor._extract_pacing`, `derive_scope_contract` and `avg_shot_duration_for` through it. Guard tests: every value is a member of the canonical vocabulary; every key of the merged table normalizes to its declared value; no alias row is declared twice; both entry points call the owner. **Coordination with `F-PHASE-02` (audit 01):** `constraints/_keywords.py` also holds `_PHASE_KEYWORDS` (`:153-165`), the analogous phase-vocabulary table owned by `F-PHASE-02` (`audit/01-phase-model-and-transitions.md:209`); any extraction that moves or regenerates this module must keep that table in step, and `audit/01` remains the owner of the phase half of the "one file, parallel keyword tables" seam.
- **Prior art:** `documentation/reviews/hardcoded-values-inventory.md:35` records pacing as **DEAD — vocab mismatch** ("profile says `character_driven`/`meditative`/`irregular`; code uses `slow_cinema`/`standard`/`dynamic`"); `:46-48` marks it **RESOLVED**; `documentation/reviews/prep-production-implementation-plan.md:112` asks to "Unify the pacing vocabulary"; `documentation/reviews/prep-production-quality-review.md:75-77` flags sizing as pacing-blind. Inside this audit, §5 row A2 grades "pacing dead / vocabulary mismatch" **FIXED** and §6 lists "Pacing → shot/scene density" as single-owner. **The vocabulary half is not unified:** the *dead* half is fixed (`pacing_from_config`, `src/film_pipeline/graph/scope_contract.py:129-134`, now reads the profile key), but the two tables with different alphabets still implement the mapping and nothing compares them; `docs/modular-architecture/01-ownership-map.md:373` already says "pacing vocabulary now DISTRIBUTED (H3)". **Ownership of this seam's two halves:** `F-CFG-14` (this finding, Medium 8) owns the mapping rule — which lexicon each entry point accepts, the two alias tables and the silent fallback; `F-ARTIFACT-14` (`audit/07-artifact-refs-and-schemas.md:794`, High 12) owns the schema-declaration half — one closed `pacing_style` vocabulary typed as a `Literal` at `src/film_pipeline/schemas/constraints.py:61` and as bare `str` at `src/film_pipeline/schemas/execution_brief.py:51` and `src/film_pipeline/schemas/scope_contract.py:23`, one instance of its five-field / 24-declaration closed-vocabulary seam; the `ExecutionBrief` → `src/film_pipeline/graph/orchestrator_validators/brief.py:113` harm belongs to that finding. `F-PHASE-02` (`audit/01`, Critical 16) owns the analogous phase vocabulary. **What is new here:** the measured 7-key / 0-conflict result, the asymmetric alphabets, the unpinned silent fallback, and the executed substitution `slow cinema → standard / 6.5`.
- **Verifier:** CORRECTED by `reviews/verify-16.md` §2 — headline mechanism refuted (the shared keys agree), scope narrowed to the mapping rule, severity High 12 → Medium 8, `src/film_pipeline/schemas/scope_contract.py:23` cited under its owner, and the `F-ARTIFACT-14` / `F-PHASE-02` cross-references added.
- **Provenance:** uncovered by the adversarial coverage pass (`reviews/adversarial-coverage.md` §H3); added post-verification; re-scoped and re-scored by `reviews/verify-16.md` §2.

---

### F-CFG-15 — The model-input size cap is code-only policy and the gate already disagrees with the truncation site (8000 vs 6000)

- **Class:** O5
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** How much model-facing text a prompt may carry is re-derived at four sites in two packages — one readiness limit and three silent slice caps — and the shot-matrix builder already uses a different number (6000) than the gate (8000); the paid-review sampling rate is a fourth, per-branch re-derivation in `generation`.
- **De-facto owners:**
  - `src/film_pipeline/validation/impl/prompt_readiness.py:15` — the declared prompt-size limit — `MAX_PROMPT_LENGTH: Final[int] = 8000  # characters`
  - `src/film_pipeline/validation/impl/prompt_readiness.py:83` — its only enforcement — `if len(rendered) <= MAX_PROMPT_LENGTH:`
  - `src/film_pipeline/mcp/tools/bibles/character.py:39` — silent truncation of the script text — `{script_text[:8000]}`
  - `src/film_pipeline/mcp/tools/bibles/environment.py:40` — the same truncation re-spelled — `{script_text[:8000]}`
  - `src/film_pipeline/mcp/tools/bibles/shot.py:184` — a third, *different* truncation — `f"Script:\n{script_text[:6000]}\n\n"`
  - `src/film_pipeline/generation/frame_reviewer.py:68`, `:82`, `:88` — the paid-review sampling rate re-chosen per branch — `return _spot_check(frame_role, frame_index, per_ten=3)` (`:68`, `:82`) and `return _spot_check(frame_role, frame_index, per_ten=5)` (`:88`)
- **Drift proof:** existing divergence plus a mutation scenario, both silent. **(a)** The gate admits any rendered prompt of ≤ 8000 chars (`validation/impl/prompt_readiness.py:83`) while `mcp/tools/bibles/shot.py:184` slices the same `script_text` to 6000 before the matrix model sees it: a 7,000-character script passes readiness (reproduced below) and is truncated by 1,000 characters with no error, no warning and no counter, so `MasterFilmMatrix` is planned from an incomplete script. The two `[:8000]` builders (`mcp/tools/bibles/character.py:39`, `mcp/tools/bibles/environment.py:40`) happen to match the gate, which is exactly why the 6000 site stays invisible: each builder is its own authority and nothing compares them. No test pins the relationship — `tests/unit/validation/test_impl_validators.py:442-461` exercises only a 9,000-char prompt against the gate (so a gate moved across the 6000/8000 band is not distinguished) and `tests/unit/mcp/tools/test_bibles.py:22-47` tests `_extract_script_text` but never the slice length. **(b)** Change `per_ten=3` at `generation/frame_reviewer.py:68` to `per_ten=4`; `:82` keeps 3 and `:88` keeps 5, and `tests/unit/generation/test_frame_reviewer.py` still passes — it covers `front-face`, `wide-establishing`, `lighting-*`, `detail-*`, the first three `expression-*` frames and `scale_sheet` (`:42-77`) and never asserts an alt-angle spot-check rate — so the paid-review cost per ten frames changes with no failing test.
- **Reproduce:**
  ```bash
  cd ${REPO_ROOT}
  grep -rn "MAX_PROMPT_LENGTH\|_RECENT_CHECKPOINT_LIMIT\|_SCENE_SPACING_SECONDS\|per_ten=\|\[:8000\]\|\[:6000\]" src/film_pipeline --include=*.py
  UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "from film_pipeline.validation.impl.prompt_readiness import MAX_PROMPT_LENGTH; print('gate limit', MAX_PROMPT_LENGTH, '| admits a 7000-char script:', 7000 <= MAX_PROMPT_LENGTH)"
  grep -cE "^\|.*(MAX_PROMPT_LENGTH|_RECENT_CHECKPOINT_LIMIT|per_ten|_SCENE_SPACING)" docs/modular-architecture/audit/03-config-profile-and-defaults.md || true  # the §4 numeric table: 0
  ```
  ```
  src/film_pipeline/post/audio_design_agent.py:10:_SCENE_SPACING_SECONDS = 30.0
  src/film_pipeline/post/audio_design_agent.py:46:                    start_seconds=i * _SCENE_SPACING_SECONDS,
  src/film_pipeline/post/audio_design_agent.py:71:                start_seconds=i * _SCENE_SPACING_SECONDS,
  src/film_pipeline/mcp/tools/bibles/character.py:39:{script_text[:8000]}
  src/film_pipeline/mcp/tools/bibles/environment.py:40:{script_text[:8000]}
  src/film_pipeline/mcp/tools/bibles/shot.py:184:        f"Script:\n{script_text[:6000]}\n\n"
  src/film_pipeline/mcp/tools/checkpoints.py:21:_RECENT_CHECKPOINT_LIMIT = 20
  src/film_pipeline/mcp/tools/checkpoints.py:82:    return cps[-_RECENT_CHECKPOINT_LIMIT:]
  src/film_pipeline/validation/impl/prompt_readiness.py:15:MAX_PROMPT_LENGTH: Final[int] = 8000  # characters
  src/film_pipeline/validation/impl/prompt_readiness.py:83:    if len(rendered) <= MAX_PROMPT_LENGTH:
  src/film_pipeline/validation/impl/prompt_readiness.py:90:                f"Prompt '{prompt_id}' is {len(rendered)} chars (> {MAX_PROMPT_LENGTH} limit)."
  src/film_pipeline/generation/frame_reviewer.py:68:            return _spot_check(frame_role, frame_index, per_ten=3)
  src/film_pipeline/generation/frame_reviewer.py:82:        return _spot_check(frame_role, frame_index, per_ten=3)
  src/film_pipeline/generation/frame_reviewer.py:88:        return _spot_check(frame_role, frame_index, per_ten=5)
  gate limit 8000 | admits a 7000-char script: True
  0
  ```
- **Blast radius:** `validation` (the readiness gate), `mcp/tools/bibles` (three prompt builders), `generation` (paid-review sampling). Scripts between 6000 and 8000 characters are certified ready and then silently half-fed to the shot-matrix model; each builder, and each sampling branch, can drift independently with a green CI. **Deliberately not covered here** (H7 is broader than what reproduces as distributed ownership): `mcp/tools/checkpoints.py:21` `_RECENT_CHECKPOINT_LIMIT = 20` with its single read at `:82`, `post/audio_design_agent.py:10-12`, `app/logging_setup.py:22-23` and `providers/mock_image_provider.py:16` are each single-module constants with no second authority — incompleteness, not an ownership seam; and the retry counts are **refuted as anchored** — `agents/runner.py:299/320/338` are the error/log *strings* of the ladder, not a numeric authority (the "3" is the structural three-stage sequence at `:376-382`), while `mcp/tools/reference_generation/retry_loop.py:214` `for attempt in range(3):` governs reference generation, a different subsystem, so pairing them as "two independent retry counts" is not supported by those anchors.
- **Candidate owner module:** `config` — publishes one model-input/cost limit block (e.g. `max_model_prompt_chars`, `paid_review_per_ten`) in the resolved configuration; `validation`, `mcp/tools/bibles` and `generation` consume it.
- **Extraction sketch:** add the limits to the profile default layer (mirroring the `_FALLBACK_PROFILES` shape owned by F-CFG-01) behind one frozen value object; replace `MAX_PROMPT_LENGTH` and the three `[:N]` literals with one owner helper `truncate_for_model(text) -> tuple[str, bool]` that reports truncation so callers can log/count it; move the three `per_ten` choices into one table keyed by frame role. Guard tests: a literal sweep asserting no `[:8000]` / `[:6000]` / `MAX_PROMPT_LENGTH` remains outside the owner; a boundary test that a script of exactly the owner limit is not truncated while limit + 1 is *and* reports truncation; a role-table test that every `frame_role` prefix maps to one declared rate.
- **Prior art:** **new.** No prior-art document mentions these values: `grep -rn "MAX_PROMPT_LENGTH\|8000\|6000\|per_ten" documentation/audit-findings.md documentation/reviews/ docs/clean-code-refactor/` returns no numeric-cap hit (`documentation/reviews/arch-lens-observability.md:111` cites the 3-attempt ladder only for its discarded error text, not as numeric policy). Audit 03's §4 numeric table lists none of them — the tabular count command above returns `0`. **What is new:** the executed divergence between the 8000 gate and the 6000 slice, the gate-admits-7000 proof, the `per_ten` mutation, and the anchor corrections recorded in the Blast-radius note.
- **Provenance:** uncovered by the adversarial coverage pass (`reviews/adversarial-coverage.md` §H7); added post-verification.

---

## 3. Env-var ownership table

Produced by `grep -rnE 'os\.(environ|getenv)' src/film_pipeline --include='*.py'` plus a
literal-name sweep (`grep -rnE '"(FILM_PIPELINE_[A-Z_]+|TMPDIR|TEMP|TMP|OPENROUTER_API_KEY|GOOGLE_API_KEY|ZAI_API_KEY|ZAI_BASE_URL)"' src/film_pipeline --include='*.py'`).

| Var | Readers (`file:line`) | Owner |
|---|---|---|
| `FILM_PIPELINE_NO_PERSIST` | `app/_persistence.py:52`, `app/logging_setup.py:80`, `cli/run.py:226`, `graph/graph.py:43`, `graph/services.py:31`, `graph/services.py:48`, `mcp/server.py:243` (**7 readers / 6 modules**) | **distributed** (`app/_persistence.py:45-53` is the declared owner; 6 sites bypass it) → F-CFG-08 |
| `FILM_PIPELINE_PERSIST_STATE` | `app/_persistence.py:51`, `graph/graph.py:43`; written at `mcp/server.py:244` | distributed (2 readers + 1 writer) |
| `FILM_PIPELINE_QUALITY` | `config/resolver.py:46` (replaces the stack layer), `config/runtime_overrides.py:13` (sets the config key) | **distributed** — two mechanisms → F-CFG-09 |
| `FILM_PIPELINE_MCP_MODE` | `app/bootstrap.py:72`, `app/runtime.py:456`; written at `app/services/operator.py:191` | distributed (2 readers + 1 mutation of global env) |
| `FILM_PIPELINE_RUNTIME_ROOT` | `app/_persistence.py:41`, `app/runtime.py:59` | distributed (2 readers; both re-implement the empty-string check) |
| `FILM_PIPELINE_STORAGE_ROOT` | `artifacts/storage.py:86` (name declared `:28`); referenced in messages at `app/safety.py:63`, `:87`, `cli/run.py:114` | **single** (`artifacts/storage.py`, the storage owner) |
| `FILM_PIPELINE_ALLOW_DELETE` | `app/safety.py:129` | single |
| `FILM_PIPELINE_CONFIRM_REAL` | `cli/run.py:155` | single |
| `FILM_PIPELINE_LOG_LEVEL` | `app/logging_setup.py:28` (name declared `:20` via `_LEVEL_ENV_VAR`) | single |
| `FILM_PIPELINE_MAX_SCENES` | `config/runtime_overrides.py:14` | single (override table) |
| `FILM_PIPELINE_SKIP_VISUAL_DEV` | `config/runtime_overrides.py:15` | single (override table) |
| `FILM_PIPELINE_MODEL_OVERRIDE` | `config/runtime_overrides.py:18` | single (override table) |
| `FILM_PIPELINE_MAX_CONTEXT_CHARS` | `config/runtime_overrides.py:19` | single (override table) |
| `FILM_PIPELINE_SEARCH_API` | `config/runtime_overrides.py:20` | single (override table) |
| `FILM_PIPELINE_APPROVAL_MODE` | `config/runtime_overrides.py:21` | single (override table) |
| `OPENROUTER_API_KEY` | `providers/credentials.py:46` via map `:68`; consumed by `app/bootstrap.py:76-77` through `is_configured` | single (`providers/credentials.py`) |
| `GOOGLE_API_KEY` | `providers/credentials.py:46` via map `:69-73`; consumed at `generation/gemini_client.py:26` (`lookup("gemini-imagen-4")`) | single |
| `ZAI_API_KEY` | `providers/credentials.py:46` via map `:74` | single |
| `ZAI_BASE_URL` | `agents/model_adapter.py:122` — `env_or_dotenv("ZAI_BASE_URL")` | single |
| `TMPDIR` / `TEMP` / `TMP` | `app/safety.py:38` (single loop) | single |

**Vars with 2+ independent readers:** `FILM_PIPELINE_NO_PERSIST` (7),
`FILM_PIPELINE_PERSIST_STATE` (2), `FILM_PIPELINE_QUALITY` (2),
`FILM_PIPELINE_MCP_MODE` (2), `FILM_PIPELINE_RUNTIME_ROOT` (2).

**Structural note:** the seven `FILM_PIPELINE_*` override knobs at
`config/runtime_overrides.py:13-21` go through one allowlisted table and are
single-owner. That is the one clean env pattern in the package and is the template
F-CFG-08 and F-CFG-11 should follow. **One caveat inside that clean table:** the
`FILM_PIPELINE_MODEL_OVERRIDE` row hardcodes a profile *name* owned by F-CFG-01's
vocabulary — `config/runtime_overrides.py:18`,
`"FILM_PIPELINE_MODEL_OVERRIDE": ("model_profiles", "creative_writer", "primary"),`. The profile
name `creative_writer` is declared in code (`agents/model_routing/__init__.py:19`) and in
`profiles/base.studio.yaml:44`; the guard test iterates the table but only asserts the *path
string* is accessed somewhere in `src/` (`tests/unit/config/test_config_contract.py:286-292`,
`assert _path_is_read(path, access_paths) or _known_dead_reason(path) is not None`), so it would
not notice the YAML key being renamed away. F-CFG-01's mutation is what makes this row
non-clean: the env knob's target is a name from the fallback vocabulary, not a name
validated against the loaded profiles.

---

## 4. Hardcoded numeric defaults / thresholds duplicating a profile value

Counts reproducible with the listed command.

| Value in code | Sites (count) | Profile counterpart | Reproduce |
|---|---|---|---|
| shot `duration_seconds` default `5` | 9 — `app/services/_generation_ops.py:136`, `graph/nodes/_generation_batch_planning.py:150`, `agents/impl/shot_bible_agent.py:88`, `mcp/tools/planning.py:179`, `mcp/tools/planning.py:183`, `mcp/tools/generation/dispatch.py:146`, `mcp/tools/generation/planning.py:97`, `generation/executor.py:116`, `generation/executor.py:178` | `profiles/base.studio.yaml:89` `duration_seconds: 1`; `profiles/quality.draft.yaml:8` `duration_seconds: 1` | `grep -rcE '"duration_seconds", *5' src/film_pipeline --include='*.py' \| grep -v ':0' \| awk -F: '{s+=$2} END {print s}'` → `9` |
| runtime fallback `300` | 3 — `agents/impl/intake_agent.py:79` (`return 300`), `agents/impl/structure_extractor_agent.py:16` (`_FALLBACK_RUNTIME_SECONDS = 300`), `graph/nodes/_context.py:70` (`"300"`) | runtime is user input, not a profile value (inventory §A re-check) | `grep -rnE '\b300\b' src/film_pipeline/agents src/film_pipeline/graph/nodes --include='*.py'` |
| `max_duration_seconds` capability literals | 5 — `providers/factory.py:65` `15`, `:74` `15`, `:83` `1`, `:92` `1`, `:100` `30` | `profiles/provider.seedance_primary.yaml:9` `15`; `profiles/provider.free_or_low_cost.yaml:6` `10`; `profiles/mock-demo.yaml:43` `30`; `profiles/local-real-provider.yaml:46` `15` | `grep -rn 'max_duration_seconds=' src/film_pipeline/providers/factory.py` |
| validator band default `85/75/65` | 1 schema default + **22** explicit call-site literals, **all 22 zero-width** (18 × `85/75/75`, 3 × `80/70/70`, 1 × `90/80/80`); a 23rd `ValidatorThresholds()` call at `validation/thresholds.py:21` passes no literals | `validation.thresholds` block **deleted** from `base.studio.yaml` (`:103-107`) | AST walk (not grep): 23 `ValidatorThresholds(` calls → 22 with all three kwargs, 22 with `review_at == block_below`; breakdown `{(85,75,75): 18, (80,70,70): 3, (90,80,80): 1}`; `grep -rn 'block_below=75' src/film_pipeline --include='*.py' \| wc -l` → `18` |
| per-frame reviewer pass bar `28.0` / 40 (70%) | 1 — `generation/frame_reviewer.py:43`, used `:222` | none (no profile key) | `grep -rn '_PASS_THRESHOLD' src/film_pipeline/generation/` |
| Gemini reviewer `temperature 0.2` / `maxOutputTokens 1024` | 1 — `generation/gemini_client.py:40` | `profiles/base.studio.yaml:43-85` `model_profiles` (reviewer profiles carry `max_tokens`/`temperature`) | `grep -n 'generationConfig' src/film_pipeline/generation/gemini_client.py` |
| `ModelAdapter` sampling defaults `4096`/`0.7`/`0.2`/`0.3` | `agents/model_adapter.py:66-67`, `:175-176`, `:215-216`, `:306-307` | `profiles/base.studio.yaml:43-85` per-profile `max_tokens`/`temperature` | `grep -n 'max_tokens\|temperature' src/film_pipeline/agents/model_adapter.py` |
| retry temperature `0.1` | 2 — `agents/runner.py:275`, `:332` | none (not a profile key) | `grep -n 'temperature=0.1' src/film_pipeline/agents/runner.py` |
| min image resolution `512` | 1 — `generation/frame_heuristics.py:53` | none | `git show HEAD:src/film_pipeline/generation/frame_heuristics.py \| sed -n '53p'` |
| scene floor fraction `0.8`; density `9.0/6.5/4.0` | `graph/scope_contract.py:26-30`, `graph/scope_contract.py:58` | `pacing` profile key feeds it (`graph/scope_contract.py:133`) but the numbers are code-only | `grep -n '_DENSITY\|_MIN_SCENE_FRACTION' src/film_pipeline/graph/scope_contract.py` |
| runtime tolerances `0.20` / `0.10` | 2 — `graph/orchestrator_validators/brief.py:116`, `graph/orchestrator_validators/prep_gates.py:121` | none (inventory recommends quality profile) | `grep -rn 'tolerance = target \*' src/film_pipeline/graph/orchestrator_validators/` |
| stall rounds `5` default vs `3` call | `graph/orchestrator_state.py:362` (`max_rounds: int = 5`) vs `graph/nodes/_repair_loop.py:72` (`max_rounds=3`) | none | `grep -rn 'max_rounds' src/film_pipeline/graph/orchestrator_state.py src/film_pipeline/graph/nodes/_repair_loop.py` |

---

## 5. Prior-art reconciliation

Source: `documentation/reviews/hardcoded-values-inventory.md` (branch
`review/prep-production-quality`, re-verified 2026-08-26 on `arch-improvement-review`, plus a
2026-09 §E re-check). Each row states the status **at `fb85baa`** with evidence.

| # | Prior finding | Status at HEAD | Evidence |
|---|---|---|---|
| A1 | `target_runtime_seconds` dead in `film-type.*.yaml` | **FIXED** | `git show HEAD:profiles/film-type.narrative.yaml` has 7 lines and no such key; count is 0 in all three film-type files |
| A2 | `pacing` dead / vocabulary mismatch | **FIXED** | read via `graph/scope_contract.py:133` `pacing = resolved_config.get("pacing")`; alias table `graph/scope_contract.py:33-46` |
| A3 | `film_type` re-derived by LLM | **still present (unchanged)** | `graph/nodes/prep.py` falls back to the profile only when extraction is empty (per inventory `:49-51`); not re-audited here |
| A4 | `story_structure` dead | **still present (worsened in clarity)** | only occurrence in `src/` is the unfilled template placeholder `agents/prompt_templates/defaults/validators.py:292` — `"STORY STRUCTURE:\n{story_structure}\n\n"`; no writer |
| A5 | `dialogue_weight`, `camera_default` dead | **still present** | `grep -rn 'dialogue_weight' src/film_pipeline --include='*.py'` → 0 hits; same for `camera_default` |
| A6 | `visual_style` dead as a profile field | **still present** | no reader of resolved-config `visual_style`; the hits are a *different* concern — `constraints/extractor.py:149`, `:244` derive it from user prose |
| A7 | `writing_style` used only by the conflict check | **still present** | `config/validator.py:42-43` `writing_style = str(resolved.get("writing_style", "")).lower()` |
| A8 | `profile.version`, `phases`, `models.default`, `limits.max_scenes`, `studio.skip_visual_dev`, `generation.search_api`, `review.strategy` unread | **still present, and now codified** | `tests/unit/config/test_config_contract.py:50-64`, `:66-75` list them in `KNOWN_DEAD_GROUPS`; the test *requires* the exemption to exist |
| B | The three-act lock (`ActMap` fixed at 3 fields) | **still present** | `schemas/story_bible.py:24-29` — `act1_setup: str` / `act2_confrontation: str` / `act3_resolution: str` (`:27-29`) |
| C1 | Shot-duration dicts duplicated (code + prompt) | **FIXED** | single table `graph/scope_contract.py:26-30` `_DENSITY`; shared via `avg_shot_duration_for` (`:119-126`) |
| C2 | Scene-count ranges `4-8/8-15/12-25` | **FIXED** | derived; floor constant `graph/scope_contract.py:58` `_MIN_SCENE_FRACTION = 0.8` |
| C3 | Runtime tolerance `±20%` / `±10%` hardcoded | **still present (locations updated)** | `src/film_pipeline/graph/orchestrator_validators/brief.py:116` `tolerance = target * 0.20  # 20% tolerance for estimated runtime`; `src/film_pipeline/graph/orchestrator_validators/prep_gates.py:121` `tolerance = target * 0.10  # 10% tolerance` (prior art cited `src/film_pipeline/graph/orchestrator_validators/brief.py:83` / `src/film_pipeline/graph/orchestrator_validators/prep_gates.py:111` — **citations drifted**) |
| C4 | `300` runtime fallback (×2) | **WORSE than recorded** | the 2026-08 re-check claims intake's occurrences were "collapsed" to a single named constant, but a raw literal survives at `agents/impl/intake_agent.py:79` `return 300` **alongside** `agents/impl/structure_extractor_agent.py:16` `_FALLBACK_RUNTIME_SECONDS = 300` and `graph/nodes/_context.py:70` `"300"` — 3 sites, not 1 |
| C5 | Stall `max_rounds` 5 default vs 3 called | **still present (citation drifted)** | `graph/orchestrator_state.py:362` `def is_stalled(state: dict[str, Any], phase: str, *, max_rounds: int = 5) -> bool:` vs `graph/nodes/_repair_loop.py:72` `if is_stalled(state, phase, max_rounds=3):` (prior art cited `src/film_pipeline/graph/orchestrator_state.py:260`; line 260 is now `cycle["status"] = status`) |
| C6 | Word floor "150+ words" | **FIXED** | no trace in `src/` |
| C7 | Theme count "3-5 themes" | **still present** | `agents/prompt_templates/defaults/spine.py:266` `"2. Identify 3-5 themes.\n"` |
| C8 | Movement bounds `< 2` block / `> 5` suspicious | **still present (citation drifted)** | `graph/orchestrator_validators/brief.py:90` `if len(brief.movements) < 2:` inside `_movement_count_issues` (`:87`); the `> 5` bound is in the same function (prior art cited `src/film_pipeline/graph/orchestrator_validators/brief.py:57`, `:65`) |
| C9 | Validation thresholds `85/75/60` not profile-driven | **still present, and the profile block was deleted** | `profiles/base.studio.yaml:103-107` documents the deletion; `validation/thresholds.py:21` `t = thresholds or ValidatorThresholds()`. **New (this audit):** the code-internal divergence of F-CFG-04 |
| E1 | `_FALLBACK_PROFILES` mirrors the base profile | **still present** | F-CFG-01; verified byte-identical via the equality command |
| E2 | `_AGENT_PROFILE_MAP` hardcoded (`graph/nodes.py:46`) | **still present, moved, and WORSE** | now `graph/nodes/_context.py:27`; **already diverges** from `agents/mvp/__init__.py:40`, `:96` on two agents (F-CFG-02) |
| E3 | Retry temperature `0.1`; `model_adapter` defaults `0.7`/`0.2`/`4096` | **still present** | `agents/runner.py:275`, `:332`; `agents/model_adapter.py:66-67`, `:215-216` |
| F | Provider pricing hardcoded / prompt disagreed with adapters | **FIXED** | single source `providers/pricing.py:36` `PROVIDER_PRICING` with `rate_for` (`:73`) and `pricing_prompt_block` (`:116`) |
| G1 | Min resolution `512px` | **still present (citation drifted)** | `generation/frame_heuristics.py:53` `if w < 512 or h < 512:` (prior art cited `:53` — accurate; the prompt twin `agents/prompt_templates/defaults/validators.py:196` also still says `(< 512px)`) |
| G2 | Gemini `maxOutputTokens 1024` + reviewer temp `0.2` | **still present** | `generation/gemini_client.py:40` `"generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},` |
| G3 | Default `quality_score 80.0` in reference template | **still present** | `agents/prompt_templates/defaults/production.py:60` `'        "quality_score": 80.0,\n'` |
| G4 | `re_anchor_every_n_clips` + drift rules never reach the generation loop | **still present, and now codified** | declared at `profiles/base.studio.yaml:91-95` and `profiles/review.strict_continuity.yaml:6-9`; `tests/unit/config/test_config_contract.py:89-105` lists all five keys in `KNOWN_DEAD_GROUPS` |

**Citation drift is systematic.** Five prior-art line anchors no longer point at the
described code (`src/film_pipeline/graph/orchestrator_validators/brief.py:83`, `src/film_pipeline/graph/orchestrator_state.py:260`, `_AGENT_PROFILE_MAP graph/nodes.py:46`,
movement bounds `brief.py:57/65`, `intake` fallback). This validates the methodology's §1.6.5
rule and the note already recorded in `tests/unit/config/test_config_contract.py:14`
("that document's citations have drifted before").

---

## 6. Clean concerns

Each with the guard test that pins it, or an explicit note that no guard exists.

| Concern | Single owner | Evidence | Guard test |
|---|---|---|---|
| Profile **merging** semantics (scalars replace, lists replace, dicts recurse) | `config/merger.py` | `src/film_pipeline/config/merger.py:21-36` — `_deep_merge` is the only merge implementation; no second deep-merge in `src/` | `tests/unit/test_config.py` merge cases; no dedicated agreement test, but no mirror exists to disagree with |
| Profile **loading** (YAML → `ProfileSource`) | `config/loader.py` | `src/film_pipeline/config/loader.py:32-40`; the only `yaml.safe_load` of a profile | `tests/unit/test_config.py:20`, `tests/unit/config/test_profile_resolver.py:50` |
| **Phase vocabulary** (`FilmPhase` is canonical) | `schemas` | the declared mirror pair lives in an architecture-ownership file that **does not exist in this checkout** (`git show HEAD:src/film_pipeline/architecture.py` → `fatal: path 'src/film_pipeline/architecture.py' does not exist in 'HEAD'`); at `fb85baa` the real mirrors are `graph/_action_routing.PHASE_ORDER` and `artifacts/paths.PHASE_DIR_MAP` | no guard at HEAD — the mirror declaration is not in `fb85baa`, so this agreement is unenforced |
| **Provider pricing** (rate per provider/model) | `providers/pricing.py` | `PROVIDER_PRICING` (`:36`), `rate_for` (`:73`), `pricing_prompt_block` (`:116`); adapters delegate (`inventory` §F re-check, confirmed by grep) | `tests/unit/providers/test_pricing.py` |
| **Storage root** resolution | `artifacts/storage.py` | `STORAGE_ROOT_ENV` declared and read only at `:28`/`:86`; consumers use `resolve_storage_root()` | `tests/unit/artifacts/test_storage.py:29-78`, `tests/unit/artifacts/test_storage_guards.py` |
| **Env-override allowlist** | `config/runtime_overrides.py` | the 7-row `ENV_OVERRIDE_MAP` (`:12-22`) is the only writer of override paths; fail-closed by construction | `tests/unit/config/test_config_contract.py:286-292` asserts every mapped path is read or explicitly known-dead |
| **Pacing → shot/scene density** | `graph/scope_contract.py` | `_DENSITY` (`:26-30`), `avg_shot_duration_for` (`:119-126`) shared with orchestrator validators; `pacing_from_config` (`:129-134`) | `tests/unit/test_orchestrator_validators.py`, `tests/unit/graph/test_shot_bible_structure.py:197-198` |
| **Config-conflict detection** | `config/validator.py` | `ConfigValidator.validate` (`:70-81`) is the only conflict producer; `ResolvedConfig.is_blocked` (`src/film_pipeline/config/resolver.py:24-25`) is its only consumer | `tests/unit/test_config.py:196-240` — but see F-CFG-05: coverage is limited to one provider shape |
| **`ApprovalGate` / phase subset vocabulary** | `schemas` | mirrors `graph/_action_routing.APPROVAL_GATES`; the mirror declaration lives in the architecture-ownership file that is absent from this checkout, so at `fb85baa` the agreement is simply unguarded — no test asserts the two vocabularies match | no guard at HEAD |

---

## 7. Candidate module boundary — the config/profile owner

**Proposed module:** `film_pipeline.config` (already the package; the change is
*consolidation*, not a new package).

**One-sentence responsibility:** resolve the ordered profile stack plus environment
overrides into one validated, typed project configuration, and be the only module that
reads the profile corpus or a `FILM_PIPELINE_*` configuration variable.

**Non-goals (explicitly not owned):**
- does not define domain schemas — `budget`, `generation`, `review`, and
  `validation` thresholds are owned by `schemas` (F-CFG-04, F-CFG-06);
- does not choose models or sample parameters — it publishes them, `agents/model_routing`
  consumes them (F-CFG-01);
- does not decide persistence — it exposes the resolved flags; `app/_persistence` owns the
  decision (F-CFG-08);
- does not execute validators or score reports — `validation` does (F-CFG-03);
- does not own the phase vocabulary — `schemas.FilmPhase` does.

**Public API to declare (currently missing from `config/__init__.py:11-21`, i.e. `src/film_pipeline/config/__init__.py`):**

| Symbol | Currently imported from | Callers |
|---|---|---|
| `load_profile_flex` | `config.profile_resolver:8` | `mcp/tools/config.py:12`, `mcp/tools/helpers.py:14` |
| `canonicalize_profile_stack` | `config.profile_resolver:31` | `mcp/tools/projects.py:9`, `app/services/operator.py:133` |
| `resolve_project_config` | `config.profile_resolver:51` | `mcp/tools/projects.py:174`, `mcp/tools/_profile_change.py:214-224`, `app/services/operator.py:142` |
| `provider_specs` / `provider_specs_from_raw` | `config.profile_resolver:149`, `:83` | `mcp/tools/planning.py:9` |
| `register_project_providers` | `config.profile_resolver:173` | `mcp/tools/_profile_change.py:21`, `mcp/tools/projects.py:8` |
| `missing_provider_credentials` | `config.profile_resolver:199` | `mcp/tools/projects.py:8` |
| `profiles_root()` *(new)* | — | `config/loader.py:30`, `app/bootstrap.py:32` (F-CFG-12) |
| `STACK_SLOTS` *(new)* | — | `config/profile_resolver.py:34`, `:56`, `mcp/tools/_profile_change.py:36` (F-CFG-07) |
| `environment` accessor *(new)* | — | `config/resolver.py:46`, `config/runtime_overrides.py:35`, `app/runtime.py:456`, `app/_persistence.py:41`, `providers/credentials.py:46` (F-CFG-11) |

**Invariants the owner must enforce:**
1. Every `profiles/*.yaml` leaf is either read by production code or absent (today enforced
   by `tests/unit/config/test_config_contract.py:295-304` *with an escape hatch* — the
   `KNOWN_DEAD_GROUPS` list at `:43-138` must shrink, not merely exist).
2. One provider-lineup normalization (F-CFG-05).
3. One budget vocabulary (F-CFG-06).
4. One profile-stack slot set (F-CFG-07).
5. `FILM_PIPELINE_*` configuration variables are read in exactly one module (F-CFG-08, F-CFG-11).

**Guard tests that fail if ownership regresses:**
- `test_config_contract.py` tightened: the known-dead set must be a *subset* of a recorded
  baseline, so drift can only decrease.
- A mirror test over the model-profile vocabulary: `base.studio.yaml["model_profiles"]` keys
  == the router's required profile names (kills F-CFG-01).
- An agent-profile agreement test: for every `MVP_AGENTS` entry,
  `resolved_profile == contract.default_model_profile` (kills F-CFG-02).
- A registry-agreement test: impl validator ids ⊆ `MVP_VALIDATORS` ids with recorded
  non-members, and identical thresholds per shared id (kills F-CFG-03).
- Band sanity test: `t.block_below < t.review_at <= t.pass_at` for every registered entry
  (kills F-CFG-04).
- An env-ownership test: the literal `FILM_PIPELINE_NO_PERSIST` occurs in exactly one source
  file (kills F-CFG-08).

**Reconciliation with an architecture-ownership declaration layer: none exists at HEAD.** A
file named `src/film_pipeline/architecture.py` is often cited as the home for this boundary —
by the two prior-art entries in F-CFG-09 and F-CFG-12 above and by the phase/approval
vocabulary rows of §6 — but it is **not in this checkout**: `git show
HEAD:src/film_pipeline/architecture.py` → `fatal: path 'src/film_pipeline/architecture.py'
does not exist in 'HEAD'`, `ls src/film_pipeline/architecture.py` → `No such file or directory`,
and `git status --porcelain` is empty (the whole of `docs/` is gitignored, `.gitignore:2`, so
this audit file is itself untracked). During the original audit a concurrent agent briefly
held an uncommitted draft of that file plus `tests/architecture/`; both are now absent, and
**revision 2 removes every claim that depended on them**. So the honest statement at `fb85baa`
is: the ownership-guard machinery this boundary needs (`VocabularyMirror`-style vocabulary
mirrors for F-CFG-01/02/04/05/06/07, `RegistryAgreement`-style registry agreement for
F-CFG-03, state-channel and policy-point guards for F-CFG-08/09) **does not exist**, in any
form, committed or otherwise. Every one of this audit's thirteen findings is therefore
currently unenforced, and any future declaration file must be *committed* to count as a
guard — until then the guard tests listed above are the only mechanism proposed here.

---

## 8. Unverified hypotheses (explicitly not findings)

Per §1.6.6, these are labeled and excluded from the finding count.

1. **H1 — A future architecture-ownership layer may resolve some findings.** At `fb85baa`
   there is no such layer: `src/film_pipeline/architecture.py` and `tests/architecture/` are
   both absent from this checkout (`git status --porcelain` empty; `git show HEAD:src/film_pipeline/architecture.py`
   → `fatal: path … does not exist`). A concurrent agent briefly held an uncommitted draft of
   both during the original audit. **Hypothesis:** if a committed guard declaring the
   persistence policy point lands, F-CFG-08 moves from "unrecorded seam" to "recorded debt
   with exemptions". I did not run `tests/architecture` (it did not exist as a trackable
   target), so this is explicitly unverified and not counted as a finding.
2. **H2 — CLI default profiles duplicate layer defaults.** `cli/run.py:91-103` defaults
   `--provider-profile provider.seedance_primary`, `--quality-profile quality.studio`,
   `--film-type-profile film-type.narrative`, and `cli/driver.py:99-101` maps them
   positionally into the stack. I did not establish that a *profile* also declares these as
   defaults (the base profile declares no default stack), so this is a CLI-surface
   duplication risk, not a demonstrated divergence. Not counted as a finding.
3. **H3 — `_config_diff` is shallow.** `mcp/tools/_profile_change.py:190-198` compares only
   top-level keys (`if k in old and old[k] != new[k]:`), so a change confined to a nested
   value (e.g. `model_profiles.creative_writer.temperature`) reports `changed: []` in the
   human-approval payload. I traced no test asserting a nested diff, but did not execute the
   tool end-to-end, so I record it as a hypothesis rather than a finding.
4. **H4 — `graph/services.py:65` leaves `validator_registry` unset in production.**
   `_build_services_for_mode` (`app/runtime.py:433-443`) never assigns it and `for_mock_runtime`
   / `for_real_runtime` do not either. I did not confirm whether some other path injects it
   at graph-run time, so the claim "no validator registry is wired in production" is unverified.

---

## 9. Finding index

| Id | Title | Class | Severity | Score |
|---|---|---|---|---|
| F-CFG-01 | Model-profile defaults declared twice (profile YAML + code fallback) | O1 | High | 12 |
| F-CFG-02 | Agent→model-profile map duplicated and already divergent | O1 | Critical | 16 |
| F-CFG-03 | Two parallel validator registries, no agreement test | O4 | Critical | 16 |
| F-CFG-04 | Score→status band grammar: documented default vs 22 literals | O1 | Critical | 16 |
| F-CFG-05 | Provider-lineup parsing understands one of two profile shapes | O1 | Critical | 16 |
| F-CFG-06 | Budget cap spelled five ways; profile value never reaches `BudgetState` | O1 | Critical | 16 |
| F-CFG-07 | Profile-stack key set defined three times | O1 | High | 9 |
| F-CFG-08 | `FILM_PIPELINE_NO_PERSIST` re-derived in six modules | O5 | High | 12 |
| F-CFG-09 | `profile_stack` has three writers that disagree on env correction | O3 | High | 12 |
| F-CFG-10 | `resolved_review_strategy` read but never written | O8 | High | 9 |
| F-CFG-11 | Two env-resolution policies (`.env` vs process env) | O5 | Medium | 6 |
| F-CFG-12 | `profiles/` located twice from CWD; `config` API omits its resolver | O7 / O8 | Medium | 6 |
| F-CFG-13 | Hardcoded numeric defaults duplicating profile values | O5 | High | 9 |
| F-CFG-14 | Pacing vocabulary re-declared four times; the two mapping tables disagree | O1 | High | 12 |
| F-CFG-15 | Model-input size cap code-only; gate 8000 vs truncation 6000 | O5 | High | 12 |

**13 findings: 5 Critical, 6 High, 2 Medium.** (Revision 1 tallied 6/5/2 from its
uncorrected scores for F-CFG-01 and F-CFG-02; `reviews/verify-03.md` downgraded F-CFG-01 to
High 12 and re-scored F-CFG-02 to Critical 16, moving one finding from Critical to High.)
**Post-verification additions: F-CFG-14 and F-CFG-15 → 15 findings: 5 Critical, 8 High,
2 Medium** (both PENDING bar-A6 verification; see the header verification record).
