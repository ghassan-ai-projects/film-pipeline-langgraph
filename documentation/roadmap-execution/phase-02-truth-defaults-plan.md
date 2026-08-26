# Phase 02 — Truth Defaults (DRAFT)

**Status:** DRAFT — ground truth verified at Phase-01 planning time; candidate designs below go
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
