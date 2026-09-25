# verify-04 — adversarial verification of `audit/04-agent-registry-and-prompts.md`

- **Verifier:** independent agent (did not write the audit), bar A6
- **Repo:** `${REPO_ROOT}`, branch `modular-app`, HEAD `fb85baa0e6b769b709791a96a89980089304bf13`
- **Working tree at verification:** clean (`git status --porcelain` empty), unlike the dirty snapshot recorded in the audit §7.1. All anchors re-read via `git show HEAD:<path>`.
- **Method:** every anchor read at HEAD; roster computed mechanically with a throwaway `/tmp` script (no repo files modified); reproduce commands re-run verbatim.

## Verdict table

| finding | verdict | one-line reason |
|---|---|---|
| F-AGENT-01 | CONFIRMED | both divergent rows reproduce (`creative_writer`/`operations_triage`, `schema_enforcer`/`strict_validator`), runtime reads the map at `_agent.py:152`, no test pins the agreement |
| F-AGENT-02 | **DOWNGRADED** | divergence is real, but the printed Reproduce block does not run (missing `src/` prefix → `FileNotFoundError`) and the declared field has *zero* production readers, so no deliverable impact → High (3×5=15), not Critical |
| F-AGENT-03 | CONFIRMED | guards unreachable (`known_*` set only in tests), 7/11 unknown outputs and the 8 unknown KB domains reproduce exactly |
| F-AGENT-04 | CONFIRMED | `ModelRouter` has no `resolve`; `chat() -> str`; real runtime wires `ModelAdapter` (`services.py:102`) so 5 MCP bible tools raise `AttributeError`; pre-existing defect verified |
| F-AGENT-05 | CONFIRMED | reproduce output matches (`tpl-only = delivery-completeness-validator`, 9 registry-only ids); `template_id` never a lookup key; `llm_enabled=True` on one impl |
| F-AGENT-06 | CONFIRMED (dispute) | 4 divergent renderers and the dead `prompt_runner.build` branch hold, but drift-proof item 3 is false (see disputes) |
| F-AGENT-07 | CONFIRMED | 4-strategy vs 3-strategy vs 1-unwrap divergence verified; `_parse_validation_response` is separately tested |
| F-AGENT-08 | CONFIRMED | `scene_count_under_min` divergence reproduces; `graph/services.py:65` is `None`; `_VALIDATOR_MAP` dispatch verified |
| F-AGENT-09 | CONFIRMED | counts `4 11 4 5`, `orchestrator` 5 vs `orchestrator-agent` 4, generation-only 7 — all reproduce; one wrong anchor (`:30`) |
| F-AGENT-10 | CONFIRMED | `class-only=['visual-dev-agent']`, `profile-only` = 10 ids, `PHASE_ORDER` missing `generation`/`delivery` — all reproduce |

**Totals: 8 CONFIRMED, 1 DOWNGRADED, 1 CONFIRMED-with-dispute, 0 REJECTED.**

## Roster reconciliation (independently computed)

Sources enumerated with `.venv/bin/python /tmp/recon.py` (imports the real objects, not regexes):

| id | source | rows |
|---|---|---|
| S1 | `agents.mvp.MVP_AGENTS` | 11 |
| S2 | `agents.impl.registry.AGENT_CLASS_BY_ID` | 12 |
| S3a | `prompt_templates.defaults.load_all` (agent templates) | 11 |
| S3b | `prompt_templates.defaults.load_validator_templates` | 7 |
| S4 | `graph.nodes._context._AGENT_PROFILE_MAP` | 21 |
| S5 | `app.mock_responses.default_mock_responses()` | 11 |
| S6 | `graph._agent_routing._PHASE_DEFAULT_AGENTS` | 9 |
| S7 | `agent_id=` literals in `graph/nodes/*.py` | 11 |
| S8 | `AgentRegistration(agent_id=…)` in `mcp/tools/bibles/*.py` | 5 |
| S9 | `applies_to_agents` tokens in `kb-manifest.yaml` (excl. `all`) | 6 |

Set differences (exact):

- `S2 − S1 = {visual-dev-agent}` — 1 orphan alias. §2.3(b) CONFIRMED.
- `S4 − S1 = {character-dossier-agent, config-inference-agent, continuity-ledger-agent, environment-bible-agent, full-movie-flow-validator, generation-scheduler-agent, kb-curator-agent, prompt-composition-agent, scene-continuity-validator, visual-dev-agent}` — 10 orphan rows, matches §2.3(c).
- `S3a − S1 = {}` and `S1 − S3a = {}` — agent templates and roster are in exact bijection.
- `S5 − S1 = {}`, `S7 − S1 = {}` — mocks and call sites are in exact bijection.
- `S6 − S1 = {}`; `S1 − S6 = {orchestrator-agent, structure-extractor-agent}` (these two route via `_default_agent_for`'s fallback literal, not the table).
- `S8 − S1 = {camera-bible-agent, character-bible-agent, environment-bible-agent, style-bible-agent}` (4). The audit's "declared only in S8 (3)" is right (environment also lives in S4); its §2.4 wording "3 MCP-only agent ids" should say 3 *S8-only*, 4 total MCP ids absent from the roster.
- `S9 − S1 = {generation-agent, orchestrator, prompt-composition-agent, provider-agent, qc-agent}` (5); S9-only = 4 (prompt-composition also sits in S4).
- `PHASE_ORDER (11) − _PHASE_DEFAULT_AGENTS.keys() = {generation, delivery}` — matches §2.4/§2.3(f) F-AGENT-10.
- `S4` values are 21/21 valid `ModelRouter.list_profiles()` entries, as claimed.

Every claimed membership in §2.2 reproduced. No mismatch claimed by the audit was refuted.

## Agreement test: none exists

Searched `tests/` directly. No `test_registry_agreement.py`; `applies_to_agents` appears in **zero** tests; `_PHASE_DEFAULT_AGENTS` appears in **zero** tests; no test compares an `MVP_AGENTS` field *value* to `_AGENT_PROFILE_MAP` or to `AGENT_CLASS_BY_ID`. The only roster guards are forward-only `tests/unit/agents/test_mvp_invariants.py:38-69` (class/template/resolvable-profile/mock) and `tests/unit/graph/test_agent_profile_routing.py:35-40` (membership). §2.4 and §5 absence claims CONFIRMED. `tests/unit/agents/test_impl_registry.py:21-23` is indeed vacuous.

## F-AGENT-02 — DOWNGRADED (Critical 20 → High 15)

- **Evidence is genuine.** `mvp/__init__.py:162` `output_artifacts=["failure_decision"]`, `impl/registry.py:29` `"failure-handling-agent": AssemblyAgent`, `assembly_agent.py:64` `return {"assembly_manifest": manifest}`, `wrapup.py:30` `manifest = result.get("assembly_manifest")`. Consumers reading impl keys, not declared outputs, verified at `prep.py:205` (`constitution`), `visual.py:50` (`reference_index`), `visual.py:438` (`shot_matrix`), `qc.py:107` (`consensus_report`).
- **Counter-evidence 1 — Reproduce is broken (§1.6.4).** The block resolves `cls.__module__.replace('.','/') + '.py'` against CWD, yielding `film_pipeline/agents/impl/orchestrator_agent.py`, which does not exist: `FileNotFoundError`. It needs a `src/` prefix. Re-run with the prefix, set-overlap holds for 4 agents (intake, treatment, screenwriter, structure-extractor), not "exactly one" — the claim only holds under *set equality*, which the text does not state.
- **Counter-evidence 2 — no impact path.** `grep -rn "output_artifacts" src/` shows the only *reads* outside definitions are `registry.py:72,88,121` (validation, allowlist `None` in production) and `runner.py:468` / `handoff.py:37`, both inside `HandoffManager`/`create_handoff`, reachable from no production caller. The impl and every consumer agree with each other; the declared field is inert. No wrong behavior reaches a human deliverable.
- **Recomputed:** impact 3 (wrong internal behavior / latent trap, recoverable) × drift 5 (no test) = **15 → High**. The audit's own mutation scenario ("nothing observable changes") concedes the impact.
- Secondary: the drift-proof sentence "the only readers are `runner.py:468` and `handoff.py:37`" is contradicted by F-AGENT-03's own `registry.py:118-122` anchor within the same document.

## Missed in scope

1. **Agent-identity branches in prompt-context assembly (O5).** `graph/nodes/_agent_prompt_context.py:94` `if agent_id == "orchestrator-agent":` and `:148` `if agent_id == "structure-extractor-agent" and context_vars.get("script_content"):` re-derive per-agent prompt policy at the call site. §1.3's coverage table labels this file "has findings (F-AGENT-05 supporting)", but F-AGENT-05 never cites it and neither does §6. This is a genuine per-agent policy seam that the proposed `AGENTS` descriptor should own; it currently ships as a coverage claim with no finding.
2. **Third value authority for `scene-continuity-validator`.** `graph/nodes/_context.py:41` `"scene-continuity-validator": "strict_validator",` while the validator registry declares the same id with `model_profile="multimodal_reviewer"` (`validation/validators/__init__.py:131`, `validation/impl/scene_continuity.py:217`). Same id, two contradictory model profiles, and nothing compares them. F-AGENT-05 covers the dual *key space*; it does not record this concrete *value* divergence, which is stronger evidence than the `template_id` argument.
3. **Unguarded profile-id alias.** `agents/registry.py:17` `return {*ModelRouter().list_profiles(), "orchestrator"}` injects a legacy profile alias that no `default_model_profile` uses; `_AGENT_PROFILE_MAP` has no `orchestrator` key either. A second, unguarded id-space for profiles, adjacent to F-AGENT-01 but not recorded.
4. **Mis-attributed ownership-map row.** The §4 row "Actual model id / sampling params … Distributed (3) — F-AGENT-01, 04" points at `_FALLBACK_PROFILES` vs `profiles/base.studio.yaml:43`, but neither F-AGENT-01 nor F-AGENT-04 analyses that pair — it is `audit/03-config-profile-and-defaults.md` F-CFG-01. Either cross-reference it or drop the attribution.

## Disputes requiring the author to fix

1. **F-AGENT-02** — Reproduce block raises `FileNotFoundError` (missing `src/`); "agree on exactly one agent" is only true under set equality (overlap holds for 4). Fix the command and state the comparison.
2. **F-AGENT-02** — Severity: recompute to **High (3×5=15)**; the declared field has no production reader and no user-visible effect (§1.5 impact 3, not 4).
3. **F-AGENT-06** — drift-proof item 3 is **false**: `schemas/prompt.py:RCTCOPrompt`/`PromptRegistry`/`PromptRegistryEntry` *are* referenced by tests — `tests/unit/test_schemas.py:393-403` calls `RCTCOPrompt.render()`, `:408`/`:1032-1037` use `PromptRegistryEntry`/`PromptRegistry`. The stated grep ("`src/ tests/` finds no other use") is wrong; amend to "dead in `src/` outside `schemas/__init__.py:108`, but schema-tested". The reproduce grep also never surfaces renderer 1 (`runner.py:43-52`, `__post_init__`, not `def render`).
4. **F-AGENT-04** — "`grep -rn '\\.resolve(' src/` shows exactly two such calls" is false: 14 hits, mostly `pathlib.Path.resolve` (`app/safety.py`, `app/logging_setup.py`, `mcp/resolution.py`, `testing/in_memory_git.py`, …). Only `model_router.resolve(` has the two bible hits. Also `_shared.py:135` is `created_by=created_by`, not a `created_by="mcp.generate_*"` literal; those literals are `camera.py:95`, `character.py:199`, `environment.py:178`, `style.py:90`, `shot.py:82`.
5. **F-AGENT-09** — anchor "`:30` `provider-agent`" is wrong: line 30 is `applies_to_agents: [prompt-composition-agent, generation-agent]`. `provider-agent` is at `:62`.
6. **F-AGENT-10** — "the same 13 fields as `AgentRegistration` … plus `enabled`" is off by one: both share **12** fields; `enabled` is the 13th.
7. **Small numeric/anchor nits:** F-AGENT-03 mutation text says `mb-manifest.yaml` (typo for `kb-manifest.yaml`); F-AGENT-08 cites `tests/unit/validation/test_registry.py:41` (actual construction at `:40`) and `tests/e2e/conftest.py:63` (actual `:62`); §2.4 references an undefined source **S10** (only S1–S9 are defined in §2.1); §1.3's "F-AGENT-05 supporting" tag for `_agent_prompt_context.py` is unsupported.
8. **Candidate-owner tension:** §6's non-goals cede phase/task routing to `graph/_agent_routing.py`, yet F-AGENT-10's extraction sketch adds a `_PHASE_DEFAULT_AGENTS.keys() ⊇ PHASE_ORDER` guard test under `agents.registry`. Audit 02 nominates a single `phases.py` catalog owning "order + gate + default agent + node". Reconcile which candidate owns the phase→default-agent map. (`agents.registry` itself is otherwise coherent and distinct from the `phase-model` and `config` candidates.)

## Overall verdict

The cluster's core seams are real and independently reproduced — the F-AGENT-04 dead real-model MCP path is the most serious and is confirmed live — but F-AGENT-02 must be downgraded (broken reproduce + no impact path), F-AGENT-06's third drift proof is false, and four anchors/counts need correction before this audit can ship under bar A2/A6.
