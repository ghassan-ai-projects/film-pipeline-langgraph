# Verify 05 — adversarial verification of `audit/05-provider-runtime-and-health.md`

Verifier: independent agent (did not write audit 05). Target: `modular-app` @ `fb85baa`.
`git status --porcelain -- src tests` is clean, so every source anchor read with
`git show HEAD:<path>` equals the working tree (`docs/` is gitignored and not in HEAD, so the
audit file itself is the on-disk artifact under test). Method: every `path:line` read with
`git show HEAD:<path>`, every reproduction re-executed with `.venv/bin/python` at HEAD,
plus additional counter-greps. No repo file was modified except this one.

## Verdict table

| finding id | verdict | one-line reason |
|---|---|---|
| F-PROV-01 | **CONFIRMED** | All 6 anchors resolve; 4 representations / 3 writers / 0 `update_provider_health` producers re-executed; CWD divergence reproduced verbatim; Critical (4×5=20) recomputes. (§1.6.2 quote for `:129-133` is off by one line — see Disputes D1.) |
| F-PROV-02 | **CONFIRMED** | `FailureClassifier` has 0 src callers (only its own def); 5 vocabularies verified; token-limit siblings live at `runner.py:18-19,239-240,280-281`; High (3×5=15) recomputes. |
| F-PROV-03 | **CONFIRMED** | Two `ProviderRegistry` classes + runtime dict + profile path verified; `zai` reproduction prints exactly the claimed output; High (3×5=15). One anchor is wrong (`factory.py:18` → the enforcing line is `:44`) — see Disputes D2. |
| F-PROV-04 | **CONFIRMED with corrections** | 14-call-site grep reproduces; rotation divergence reproduces exactly; but "never asserts a policy at the adapter or `ModelAdapter` layer" is **false** (tests do assert it) — see expanded row. |
| F-PROV-05 | **CONFIRMED** | Capability table has 0 readers; `_FALLBACK_PROFILES` == `base.studio.yaml:43-85`; self-referential tests verified; High (3×4=12). One off-by-one anchor (`:61-66` → function spans `62-68`) — see Disputes D3. |
| F-PROV-06 | **CONFIRMED** | Enum mapper `dispatch.py:182-196` vs string branches `executor.py:245-247` both exist; 3 `ProviderJob` reconstructions verified; mutation scenario is sound; High (3×4=12). |
| F-PROV-07 | **DOWNGRADED (in part)** | Rate duplicate + "unpinned" both true, but the O3 quota clause is out of taxonomy and the "Medium (3×3=9)" label contradicts §1.5 — see expanded row. |

Coverage totals: **7/7 findings survive in substance; 0 rejected; 1 class/severity defect (F-PROV-07); 1 overstated evidence sentence (F-PROV-04); 3 wrong/misleading anchors (D1–D3).**

**Health representations confirmed: 4** as claimed — `app/runtime.py:51` (stringly dict),
`providers/health.py:11-23` (dataclass), `schemas/provider_health.py:13-31` (Pydantic),
`graph/orchestrator_state.py:406-410` (+ channel decl `:129-133`) — **plus a fifth, unanalysed
declaration**: `graph/state_schema.py:178` `provider_health_snapshot: dict[str, object]` is a
public graph channel *distinct from* the namespaced `_orchestrator__provider_health_snapshot`
at `:195`; neither has a writer. See Missed M3.

---

## Expanded rows

### F-PROV-04 — CONFIRMED with corrections

Counter-evidence to the drift-proof sentence
*"`grep -rn "lookup(\|is_configured(\|env_or_dotenv(" tests/` … never asserts a policy at the adapter or `ModelAdapter` layer"*:

- `tests/unit/providers/test_veo_fast_provider.py:43-51` monkeypatches
  `film_pipeline.providers.adapters.veo_fast.lookup` and asserts
  `provider._api_key() == "secret-key"`.
- `tests/unit/providers/test_veo_fast_provider.py:33-40` asserts the raise path.
- `tests/unit/agents/test_model_adapter.py:149-156` monkeypatches
  `film_pipeline.agents.model_adapter.lookup` and asserts the raise path through `chat()`.
- `tests/unit/providers/test_imagen4_provider.py:53` asserts submit requires the Google key.

So the chosen grep is the wrong instrument: those tests call `_api_key()`/`chat()`, not
`lookup()`, and the grep cannot see them. What *is* unpinned is the specific divergence the
finding actually needs — **rotation freshness**: no test constructs an adapter, rotates the
env var, and re-reads (grep `rotat` over `tests/` → 0 hits; no seedance unit test exists;
`tests/unit/providers/` has no `test_seedance*`). The reproduction is valid and was re-run at
HEAD:

```
seedance sees: sk-first-key-12345678     # cached at seedance_openrouter.py:51
veo sees:      AIza-second-key-12345678  # re-read at veo_fast.py:25
```

Recommendation: delete the "never asserts a policy" clause and replace it with
"no test pins **rotation freshness**, and no test pins which provider id maps to which
model-provider credential". The "14" count also includes a non-credential read
(`model_adapter.py:122` `env_or_dotenv("ZAI_BASE_URL")`), so the honest count is 13 credential
plus 1 base-URL site; state it that way.

Class note: the second class **O2 (duplicated invariant enforcement)** is a stretch — no
validation/refusal is duplicated. `config/profile_resolver.py:204` importing the private
`_env_var_for` is textbook **O7 (leaked internals)**, and the read-policy-at-14-sites is **O5**.
Recommend `O5 + O7`. Recompute severity: unchanged **High** either way
(3×5=15 as written; 3×4=12 if one credits the adapter-level credential tests — the
rotation divergence itself remains unpinned, so 15 is defensible).

### F-PROV-07 — DOWNGRADED in part (keep the cost half; strike the O3 quota clause; fix the label)

**Stands (mechanically re-verified):**
- `app/mock_responses.py:14` literal `_SEEDANCE_RATE_USD_PER_SECOND = 0.18` duplicates
  `providers/pricing.py:39` (`"rate_usd": 0.18`).
- `grep -rn "_SEEDANCE_RATE" tests/ --include=*.py` → empty (unpinned), and
  `grep -rn "18.72" tests/` → no assertion of the total.
- `generation/ledger.py:99` is the only per-row `estimated_cost_usd` writer.

**Struck — O3 (split state authority) does not fit the quota/credit clause.** §1.4 defines O3 as
"one logical state is **written by 2+ modules** with no single writer", and §1.3 explicitly
excludes *incompleteness* from distributed ownership ("Findings must be one of these, not the
others"). Verified: `quota_remaining` (`providers/health.py:19`), `credit_remaining_usd`
(`:20`), `quota_state`/`credit_state` (`schemas/provider_health.py:20-27`) have **zero writers,
not two**. A dead field is incompleteness, not split authority. This half belongs in the
document's own "Unverified hypotheses"/hygiene section or must be re-argued under a fitting
class. Keep the O1 half.

**Struck in part — the impact narrative is mock-mode-only.** The duplicate rate lives in
`app/mock_responses.py`, which `app/runtime.py:438-442` wires through
`GraphServices.for_mock_runtime` only; real mode returns `for_real_runtime` at `:436-437`. The mutation
scenario is still real for the demo, but "the ledger bills the new one" is loose in mock mode:
the mock plan's provider id is `"seedance"`/model `"2.0"`
(`mock_responses.py:86-90`), which is not a `PROVIDER_PRICING` key, so
`estimate_cost_for_duration` bills `_UNKNOWN_PROVIDER_RATE = 0.0` (`pricing.py:57`).

**Recomputed severity:** the stated `Medium (impact 3 × drift 3 = 9)` is arithmetically
impossible under §1.5 — 9 is **High (9–15)**. The author must either (a) relabel to **High
(3×3=9)**, or (b) lower impact to 2 (demo/mock-only visible effect) and print
**Medium (2×3=6)**. Pick one; the current label is a bar-A2/§1.5 violation.

---

## Missed in scope

**M1. Provider API base URLs have no owner — the Gemini base URL is declared three times (O1).**
- `providers/adapters/imagen4_gemini.py:21` — `GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models"`
- `generation/gemini_client.py:13` — `GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"`
- `agents/model_adapter.py:296` — inline `"https://generativelanguage.googleapis.com/v1beta/models/"`

All three modules are explicitly in this audit's scope. Reproduce:
`grep -rn "generativelanguage.googleapis.com" src/ --include=*.py` → 3 hits;
`grep -rln "generativelanguage\|GEMINI_API" tests/ --include=*.py` → **empty** (unpinned).
Drift proof (mutation): change `imagen4_gemini.py:21` (e.g. `v1beta`→`v1`); the two review/model
callers keep `v1beta` and no test fails, so image generation and image review can hit different
API versions. Same pattern for OpenRouter: `agents/model_adapter.py:36` imports
`OPENROUTER_API` from a *media* adapter (`providers/adapters/seedance_openrouter.py:27`) rather
than from a provider config owner. Candidate owner: the proposed `provider-catalog` (an
endpoint facet) or a dedicated `provider-endpoints`. Severity: **High** by §1.5
(impact 3 × drift 5 = 15) — a partial edit passes every test.

**M2. The real-mode spend ceiling is computed from an LLM-authored number, not from `pricing`.**
F-PROV-07 treats the duplicate as a mock-fixture problem, but the same two-writer structure
exists in production: `agents/impl/gen_planner_agent.py:17` and `:73` turn the **model's**
`estimated_cost_usd` into the `CostEstimate` artifact; `graph/nodes/visual.py:493-500` persists
it; `graph/nodes/_generation_batch_planning.py:42-45` derives
`max_cost_usd = float(raw_cost) * 1.1` from it, while `generation/ledger.py:99` bills
`estimate_cost_for_duration`/`rate_for`. Nothing asserts the LLM number equals the pricing
number, so a stale `pricing_prompt_block` or a drifted model output silently mis-calibrates the
human spend gate in **real** mode. Cite `gen_planner_agent.py:17,73` in F-PROV-07 and raise its
impact accordingly (this is what makes the finding more than demo-only). Candidate owner:
`cost-accounting` / `provider-pricing`.

**M3. Two declared provider-health graph channels, only one has accessors.**
`graph/state_schema.py:178` `provider_health_snapshot: dict[str, object]` and `:195`
`_orchestrator__provider_health_snapshot` both exist; only the second has
`update_provider_health`/`get_*` (`orchestrator_state.py:406-443`). The F-PROV-01 ownership map
lists both lines but the finding counts only one checkpointed representation and does not flag
the duplicate public channel. Add it to F-PROV-01 or delete the dead channel.

**M4. Registry consumed as a raw `Mapping[str, Any]` at 4 call sites (O8 reader side).**
`generation/executor.py:58` takes `providers: Mapping[str, Any]`; called with the runtime dict at
`app/services/_generation_ops.py:150`, `mcp/tools/generation/_text_only.py:110`,
`mcp/tools/generation/dispatch.py:142`, `mcp/tools/planning.py:41,90`. F-PROV-03 covers the
*writer* side (`register_provider(id, adapter: Any)`) but never cites these readers, so its
"missing contract" claim under-states the blast radius.

---

## Disputes requiring the author to fix

- **D1 — F-PROV-01, §1.6.2 quote off by one.** `orchestrator_state.py:129-133` is cited, but the
  quoted block starts at **130** (`OrchChannelSpec(_PROVIDER_HEALTH_SNAPSHOT,`); line 129 is the
  `OrchChannelSpec(` opener. Use `:130-133` (verified: `grep -n "dormant writer"` →
  `:132` = `"dormant writer; wiring decided in D13/P1 (provider health)",`).
- **D2 — F-PROV-03, wrong anchor.** The drift proof says the unknown-id `ValueError` comes from
  "`factory.py:18`"; line 18 is `def build_provider_adapter(`. The enforcing line is
  `providers/factory.py:44` — `raise ValueError(f"Unsupported provider_id: {provider_id}")`
  (the finding's own de-facto-owner anchor `:34-44` is correct). Fix the `:18`.
- **D3 — F-PROV-05, off-by-one anchor.** `_select_image_provider` is cited as
  `reference_generation/index_files.py:61-66`; line 61 is blank, the function spans
  `62-68` (`def` at 62, `return None` at 68). The Coverage table already uses the correct `:62`.
- **D4 — F-PROV-01, unsupported clause.** "`check_readiness()` (`app/health.py:36-51`) reports
  provider readiness that no code path maintains" is wrong as written: `app/health.py:47` reads
  `rt.get_provider_health`, and that dict **is** maintained by `_provider_seeds.py:28,30,37`,
  `config/profile_resolver.py:196` and `mcp/tools/providers.py:32`. The defensible statements
  are (a) `check_readiness` has **no production caller** (grep `check_readiness src/` → only its
  def at `health.py:17`), and (b) it reads the runtime dict, **not** the unwritten graph
  snapshot. Rewrite the clause.
- **D5 — F-PROV-07, taxonomy + label.** See expanded row: drop O3 for the zero-writer quota
  fields (§1.3 incompleteness exclusion) and resolve the `3×3=9` vs "Medium" contradiction.
- **D6 — F-PROV-05 title counts "five modules"; the body lists seven sites** and the ownership
  map says "≥4" for models and "≥3" for ids. Reconcile the count in the title.
- **D7 — F-PROV-04, class.** Prefer `O5 + O7` over `O2 + O5` (private `_env_var_for` import is
  leaked internals, not duplicated enforcement).

---

## Overall verdict

**All seven findings are substantively confirmed at HEAD — no fabrication, no rejected finding —
but F-PROV-07 must be re-classified/re-severitied, F-PROV-04's "no test pins this" sentence must
be narrowed to rotation freshness, and four anchors/clauses (D1–D4) need line-level fixes before
the file can pass bar A6 cleanly.**
