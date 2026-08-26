# Phase 02 — Truth Defaults

**Status:** APPROVED — both plan reviews PASS (architecture lens; completeness & correctness lens). Amendments (a)-(l) folded.
through the standard two-lens plan review before any implementation.
**Roadmap items:** P0 #4 (Flx-F10 imagen pricing delegation), P0 #5 (Flx-F9 config-contract test),
P0 #6 (O-F6 truthful `get_blockers`), P0 #7 (O-F10 logging bootstrap).

## Item 1 — Imagen pricing delegation [Flx-F10]

Ground truth:
- `providers/adapters/imagen4_gemini.py:162-169`: `estimate_cost()` carries tier literals —
  `"ultra"`→`0.10`, `"fast"`→`0.02`, else `0.05` — private to the adapter.
- `providers/pricing.py:27-33`: `PROVIDER_PRICING["gemini-imagen-4"|"imagen-4"] = 0.02`
  ("Imagen 4 (fast)") — flat, tier-blind; `rate_for(provider_id)` (:38-43) takes no model.
- Consequence: planner prompt block (`pricing_prompt_block()`) advertises $0.02 while ultra bills
  $0.10 — cost-integrity of planning prompts broken.

Candidate design (per roadmap): extend `rate_for(provider_id, model=None)`; add a tier map
(`ultra`/`fast`/default) under the imagen entries; adapter `estimate_cost` delegates to
`pricing.rate_for(provider_id=…, model=model_id)`. Parametrized test asserting
`estimate_cost == rate_for(...)` for every tier, plus prompt-block label honesty (label per tier or
explicit "from $" wording — decide in review). Keep `_UNKNOWN_PROVIDER_RATE` behavior.

## Item 2 — Config-contract test [Flx-F9]

Ground truth:
- `config/runtime_overrides.py:12-20`: seven env overrides; `FILM_PIPELINE_MODEL_OVERRIDE` writes
  `("models","creative_writer","primary")` which **no code reads** (review-verified mis-wiring).
- Dead knobs recorded: `base.studio.yaml:43` `re_anchor_every_n_clips` (zero consumers),
  `base.studio.yaml:56-60` profile thresholds unread (schema defaults 85/75/65 vs per-entry
  literals 85/75/75 disagree).
- `hardcoded-values-inventory.md` is the seeded KNOWN_DEAD allowlist source.

Candidate design: a unit test that walks resolved default-profile leaves + every
`ENV_OVERRIDE_MAP` path and asserts each has ≥1 reader (grep-based AST scan over `src/`) or an
allowlist row citing the inventory doc (`KNOWN_DEAD: <reason>`). Fails today on the three known
items — fixing them (wire model override to a read path or delete the env var) is part of this
phase; deleting a documented env knob requires operator-guide sync.

## Item 3 — Truthful `get_blockers` [O-F6]

Ground truth:
- `app/runtime.py:364-377`: `get_blockers` filters `self.block_entries`; sole writer `add_blocker`
  has zero callers → always `[]`.
- Consumer chain: MCP tool `mcp/tools/state.py:77-82` → response `{blockers, has_blockers}`;
  operations guide directs users to this tool.
- Truthful sources available on state: `compute_actions(state).blocked`
  (`graph/_action_routing.py:343`) and blocking issues.

Candidate design: derive blockers from live project state via `compute_actions` + blocking-issue
scan; keep response shape exactly ({blockers: list[dict[str,str]], has_blockers: bool}). Decide in
review whether dead `add_blocker`/`block_entries` machinery is deleted (C7 no-dead-code) or marked
DORMANT per Flx-F8 convention.

## Item 4 — Logging bootstrap [O-F10]

Ground truth:
- Zero logging configuration anywhere in src (no dictConfig/basicConfig); 14+ modules use
  `getLogger(__name__)`; stderr must stay WARNING-safe because MCP stdio shares the stream.

Candidate design: small `observability/logging_config.py` (or `app/` — decide via boundary law)
with `configure_logging(level_env="FILM_PIPELINE_LOG_LEVEL", runtime_root=…)`: stdio handler at
WARNING to stderr, richer rotating file handler under the runtime root when persistence enabled,
idempotent (guard against duplicate handlers on re-invocation). Call from the three entrypoints:
MCP server main, TUI app start, CLI driver. Unit tests: idempotency, env-level mapping, file
handler placement; no network.

## Acceptance criteria (phase bar, same shape as Phase 01)

1. Planner-visible imagen rates equal billed rates for all tiers; estimate-vs-pricing parametrized
   test proves it.
2. Config contract enforced by CI: every leaf/env-path read or explicitly KNOWN_DEAD with cited
   reason; known violations fixed or allowlisted deliberately.
3. `get_blockers` returns live-derived blockers; response shape unchanged; guide-recommended flow
   actually works.
4. Logging configured at all three entrypoints, stdio-safe, idempotent, tested.
5. `make ci-check` green; two plan reviews + three implementation reviews PASS at ≥4/5.

## Ground-truth re-verification (post-Phase-01 tree, planning time)

First-hand checks while plan reviews run; supersede line numbers above where they drifted:

1. `pricing.py` structure: `_PricingEntry` TypedDict `{unit, rate_usd, label}`; imagen aliases
   share one label and `pricing_prompt_block()` dedupes by label — tier honesty therefore needs
   per-tier labels OR explicit "from $" wording (the open question flagged for review).
2. `block_entries`: exactly 3 references, all in `app/runtime.py` (field :49, reader :365,
   writer :370). Not serialized by checkpoints/persistence anywhere → deletion carries no
   stored-state deserialization hazard.
3. `get_blockers` has a SECOND production consumer the draft missed:
   `app/services/operator.py:439` (`_has_blockers`) ORs it with its own blocking-issue scan
   (`_blocking_state_issues`). Truthful derivation must serve both call sites and should reuse
   shared blocking-issue logic rather than duplicate it.
4. Logger census: exactly 14 modules use `getLogger(__name__)`.
5. Entrypoints: `mcp/server.py`, `tui/app.py`, `cli/driver.py`; `cli/run.py` (console script)
   delegates to the driver → three wiring points cover all four surfaces.
6. KNOWN_DEAD source doc lives at `documentation/reviews/hardcoded-values-inventory.md`
   (not docs root) with dated re-verification notes; confirms `re_anchor_every_n_clips`
   (`profiles/base.studio.yaml:43-47`, zero consumers) and that resolved-config
   `validation.thresholds` never reaches validators.
7. Mis-wiring detail: `FILM_PIPELINE_MODEL_OVERRIDE` → `("models","creative_writer","primary")`;
   no code reads `models.<profile>.primary`. Profile→model selection flows through
   `_AGENT_PROFILE_MAP` (`graph/nodes/_context.py:28-53`) + ModelRouter. Inventory notes model
   routing gained a per-profile override channel post-sweep — candidate wire-in target if the
   knob is kept.

## Plan review #1 — architecture lens: APPROVE (recorded)

Scores per item 4–5; zero direction rejections. Structural facts contributed: `observability/`
package already exists (audit/blockers/metrics siblings); `get_next_actions`
(`mcp/tools/state.py:63-74`) already establishes the mcp→graph.router derivation pattern;
all `rate_for` callers are single-positional and none request imagen ids.

Required amendments folded into the design below:

- **(a)** Imagen tier map must make the default tier explicit: `{ultra: 0.10, fast: 0.02}` +
  base rate **0.05** for unknown/default models (adapter bills 0.05 today; the flat 0.02 entry
  misprices default too).
- **(b)** Prompt honesty pinned: render ONE LINE PER TIER with exact rates
  ("Imagen 4 Ultra: $0.10/image", …); label dedupe becomes tier-aware. No "from $" wording.
- **(c)** Parity test includes `model=None` case, not just named tiers.
- **(d)** Threshold literal corrected: yaml is pass 85 / review 75 / block **60** vs schema
  default 65. Schema is the typed source → align yaml 60→65 deliberately (or document delta);
  decision recorded at implementation.
- **(e)** Config-contract test docstring enumerates recognized reader idioms (subscript chains,
  `.get()` chains, typed-model attribute access) so scanner blind spots can't mint false
  KNOWN_DEAD rows.
- **(f)** MODEL_OVERRIDE disposition decided during implementation with evidence: check whether
  ModelRouter/model resolution can read `models.creative_writer.primary` from resolved config
  without new coupling; record either way; operator-guide sync if deleted.
- **(g)** `get_blockers` derivation site pinned: MCP tool layer (mirror `get_next_actions`);
  do NOT add graph-state loading into `StudioRuntime.get_blockers`.
- **(h)** Factual correction: `add_blocker` has one test caller (`tests/unit/test_mcp.py:696`)
  — deletion updates/removes that test.
- **(i)** DELETE over DORMANT for the `block_entries` trio (C7): no roadmap row plans a writer,
  unlike existing dormant-writer annotations which await wired consumers.
- **(j)** Wiring points named: MCP server serve path, TUI app start, CLI `run.py` main
  (headless driver paths traverse it); idempotency guard makes double-config harmless but one
  CLI call site is cleaner.
- **(k)** Persistence-disabled branch explicit: stderr-only logging, tested no-file-handler.

## Completeness-lens evidence (orchestrator-verified while reviewer infra stalls)

The completeness reviewer stalled twice and ignored two interrupts; its narrowed re-review is
pending. Meanwhile all three of its remaining questions were answered first-hand:

1. **Tier-blind rates beyond imagen: NONE.** `seedance_openrouter.py:168` and `veo_fast.py:71`
   already delegate to `rate_for(...)`; `imagen4_gemini.py:162-169` literals are the sole
   divergence. The parity contract test will parametrize across ALL THREE adapters anyway —
   locking the delegation pattern in cheaply.
2. **Docs-sync inventory:** only `documentation/openclaw-mcp-operator-guide.md` references
   `get_blockers` (:73, :665). NO operator doc mentions `FILM_PIPELINE_MODEL_OVERRIDE` →
   deleting it (if (f) lands there) requires no guide sync. No doc mentions
   `FILM_PIPELINE_LOG_LEVEL`; adding a one-line guide note is optional polish.
3. **Dropped promises: NONE.** Roadmap items #4–#7 map 1:1 onto Items 1–4 + amendments (a)-(k).

## Plan review #2 — completeness & correctness lens: APPROVE (recorded)

Scores: claim-accuracy 5 · coverage 5 · test-evidence 4 (gating on its finding 1) · docs-sync 5.
Findings 2–4 independently CONFIRMED my orchestrator-verified evidence above. Required addition
folded into Item 1:

- **(l)** `mcp/tools/planning.py:107-124` `_build_generation_plan` bills
  `sum(duration * 0.02)` — seconds × per-IMAGE imagen rate, every shot tagged `tier="fast"` +
  `gemini-imagen-4` utilization regardless of actual provider. Same Flx-F10 class on the MCP
  fallback-planner surface. Item 1's parity/contract tests must pin this derivation against
  `rate_for`/`unit_for` with correct per-second/per-image semantics; fix the unit error and
  false provider/tier tagging.

**Status: APPROVED for implementation** (both lenses APPROVE; amendments (a)-(l) folded).

## Implementation order

Item 1 (+l: pricing tiers + adapter delegation + prompt lines + planning-tool fix + parity
tests) → Item 3 (delete block_entries trio incl. test_mcp caller; MCP tool derives truthfully
from compute_actions + blocking issues; response shape unchanged; simplify
operator._has_blockers whose runtime half was always []) → Item 2 (config-contract test lands
after fixes so it passes: KNOWN_DEAD rows cite inventory; yaml threshold aligned to schema;
MODEL_OVERRIDE disposition recorded) → Item 4 (observability/logging_config.py + three wiring
points + idempotency/persistence-off tests).

## Plan review #2 (ORIGINAL completeness lens, delayed arrival): APPROVE — supersedes where noted

Scores 4/4/4/4; conditional on folding six REQUIRED amendments (evidence-additions and recorded
decisions only; explicitly none require re-review). Where this conflicts with earlier records,
THIS review wins:

- **(m) MODEL_OVERRIDE → REWIRE, not delete.** Real read path found:
  `resolved_config["model_profiles"][<profile>]` via `_context.py:405-419` → `runner.py:176`
  (`_model_overrides_for` → `resolve_model_params` partial overrides). Change map entry to
  `("model_profiles", "creative_writer", "primary")`; amend pinning test
  `tests/unit/test_config.py:142-155`. Verified no operator-facing doc references the var.
- **(n) Logging placement → `app/logging_setup.py`, NOT observability/.** Resolves the (j)
  conflict: observability is the package O-F1 flags as having zero production callers — do not
  resurrect a dormant package for one bootstrap function; entrypoint binaries already compose
  from app/.
- **(o) Thresholds are a THREE-way disagreement:** yaml `base.studio.yaml:55-59`
  (85/75/60) vs schema defaults 85/75/65 (`validator_registry.py:17-19`) vs per-entry literals
  85/75/75 (+ variants). Decision: DELETE the `validation.thresholds` block from
  base.studio.yaml (aligning would imply values that are never read); per-entry
  ValidatorThresholds literals authoritative; config-wiring deferred to C-6.
- **(p) Contract-test scope pinned:** files = base.studio.yaml + non-film-type overlays
  (quality/provider/mock-demo/local-real/auto-approve) + all ENV_OVERRIDE_MAP paths;
  film-type overlay corpus (dialogue_weight, visual_style, camera_default, story_structure)
  wholesale-KNOWN_DEAD citing inventory §A, wire-or-delete deferred to WS-F/C-6. Reader
  semantics: path counts as read iff AST scan finds each segment as string literal in src/ OR
  explicit READERS annotation in the test. Extend estimate-vs-pricing parity to seedance +
  veo_fast (mock providers excluded, docstring states why); adopt per-tier labels
  (Imagen 4 Ultra / Imagen 4 Fast / Imagen 4 standard-default); record factory.cost_profile
  default-tier limitation.
- **(q) Item 3 confirmations folded:** operator.py:439 reconciled by delegating _has_blockers'
  runtime half away (derive once in MCP tool; operator uses blocking-issue scan);
  test_mcp.py:699 rewritten to seed realistic blocking state; DELETE over DORMANT recorded;
  zero-serialization evidence recorded.
- **(r) Item 4 spec pinned:** entrypoints = `mcp/server.py:234 main()`,
  `cli/run.py main()` (console script; driver.run_headless stays library), `tui/app.py:272
  main()`; rule: only console-script binaries configure logging. File handler when
  persistence enabled → `<runtime_root>/logs/film_pipeline.log`, RotatingFileHandler 5×1MB,
  idempotency via handler-identity check; stderr capped WARNING for stdio safety.

All REQUIRED amendments (a)-(r) folded. Implementation begins next.

## Implementation record (pre-review)

- **Item 1 [Flx-F10 + (l)]:** pricing.py gains optional `tiers` map per entry
  (`{"ultra": 0.10, "fast": 0.02}` + standard 0.05); `rate_for(provider_id, model=None)`
  matches tier keys by lowercase substring (adapter semantics preserved); adapter
  estimate_cost delegates; prompt block renders one line per tier + "(standard)".
  mcp/tools/planning.py `_build_generation_plan` now bills the catalog-default video provider
  via rate_for with per-shot estimated_cost and honest provider_utilization (unit error +
  false imagen tagging gone). Tests: tier/alias/unknown cases, three-adapter parity table
  (incl. model=None + unknown models), prompt-line assertions, planning-tool cost derivation.
- **Item 2 [Flx-F9]:** MODEL_OVERRIDE rewired to ("model_profiles","creative_writer","primary")
  [(m)]; validation.thresholds deleted from base + all three quality overlays [(o)];
  tests/unit/config/test_config_contract.py enforces env paths + every profile leaf read via
  AST literal scan, with grouped KNOWN_DEAD rows citing the inventory doc, READERS escape hatch,
  and a guard that the named Flx-F9 failures stay deliberate.
- **Item 3 [O-F6]:** MCP get_blockers derives from compute_actions(state).blocked + blocking
  issues, shape-stable ({action,reason} entries); block_entries/add_blocker/runtime.get_blockers
  deleted (C7); operator._has_blockers reduced to its truthful state-scan half; wired blocker
  test rewritten to seed realistic blocking state.
- **Item 4 [O-F10]:** app/logging_setup.configure_logging — stderr WARNING-capped (stdio-safe),
  rotating file handler <root>/logs/film_pipeline.log 5×1MB when persistence enabled,
  handler-marker idempotency; wired at mcp/server.main, tui/app.main, cli/run.main only.
  Tests: idempotency, level mapping incl. unknown fallback, file placement, no-file branches,
  persistence-env honored.
