# Verify 09 — adversarial verification of `audit/09-kb-context-and-provenance.md`

Verifier: independent agent (did not write audit 09), per §1.6 / quality bar A6.
Repo state verified first: `git rev-parse HEAD` = `fb85baa0e6b769b709791a96a89980089304bf13`
(branch `modular-app`, `git status --porcelain` empty). Every anchor below was opened at HEAD.
File line-count claims in the Coverage table reproduce exactly (`wc -l` matches for all 15 files).
Reproduction scripts were run under `/tmp` only; no repo file was modified.

Verdict counts: **6 CONFIRMED, 4 DOWNGRADED, 0 REJECTED**.

---

## F-KBCTX-01 — builder never wired in production — **CONFIRMED** (Critical, 4×4 = 16)

- All anchors resolve verbatim: `graph/services.py:119` `"if self.kb_builder is not None:"`, `:120`
  `"result = self.kb_builder.build("`, `:129` `kb_context_id=f"kbctx:{project_id}:{phase}:{agent_id}:v1",`;
  factories `:87-91` / `:105-109` return `cls(...)` with no `kb_builder`; composition roots
  `app/runtime.py:437`/`:440` and `cli/driver.py:71`/`:75` confirmed by grep (the only
  `for_*_runtime` / `GraphServices(` sites under `src/`).
- Reproduced: `grep -rn "kb_builder" --include=*.py src/ tests/` → only `services.py:66/119/120`,
  `tests/e2e/conftest.py:108/126/137`, plus the fixture re-export `tests/smoke/conftest.py:10`.
  `:137` is the only *construction* that populates the field; the smoke suite inherits it through the
  re-export (precision note, not a falsification).
- `.venv/bin/python` run of `intake_node`/`qc_node`: `kb_for` returns the synthetic
  `kbctx:p1:intake:intake-classifier-agent:v1` / `kbctx:p1:qc:clip-validator:v1` — the fallback is the
  live producer, and `payload`/`authority_policy_refs` are empty by schema defaults.
- O6+O3 defensible; mutation scenario ("wire `for_mock_runtime` only") is sound: no test constructs
  services through a factory and asserts packet content; `test_services.py:131` pins the *fallback*
  and `:53` hand-injects the ref.
- Prior art confirmed at `documentation/audit-findings.md` (still open). **One anchor error**: the
  quoted `"GraphServices.kb_builder is None; graph nodes receive synthetic KB packets."` is at `:112`,
  not `:111` (`:111` is `"- \`kb_context_ref\` is declared on \`ArtifactMetadata\` but almost never populated."`).

## F-KBCTX-02 — three `kbctx:` grammars — **CONFIRMED** (High, 3×4 = 12)

- All three producers resolve exactly: `kb/packets.py:108`, `graph/services.py:129`,
  `graph/_agent_routing.py:201`; field declared `:26` `kb_context_ref: str = ""`, assigned `:75`.
- Orphan claim reproduced: `grep -rn "kb_context_ref" src/` shows the routing value is written but
  never read (no consumer of `AgentRouteResult.kb_context_ref` anywhere).
- Drift proof holds: `tests/unit/kb/test_packets.py:35` only asserts
  `startswith("kbctx:")`; `tests/unit/graph/test_services.py:53` and `tests/unit/agents/test_runner.py:87`
  use hand-written / round-tripped literals. No test pins arity agreement.
- O1 correct; impact 3 × drift 4 = 12 stands.

## F-KBCTX-03 — 11 artifact-write paths drop the column — **CONFIRMED** (Critical, 4×4 = 16)

- The reproduce command returns exactly the 11 claimed files, in a verifiable superset/order;
  each of the 11 cited `path:line` anchors resolves to `meta = ArtifactMetadata(`. `schemas/artifact.py:68`
  `kb_context_ref: str | None = None` and `store.py:157` copying `meta.kb_context_ref` through confirmed.
- **One evidence error shared with F-KBCTX-07**: the "same artifact family" example is wrong at the
  artifact level. `graph/nodes/visual.py:447` writes artifact_id `"shot_matrix"` (not
  `master_film_matrix`); `mcp/tools/bibles/shot.py:199` writes `"master_film_matrix"`. Reproduced with
  `.venv/bin/python` against `shot_bible_node`: `shot_bible shot_matrix type=shot_bible`. The 11-site
  omission itself is fully confirmed, so the severity is unaffected; the "MCP-vs-graph divergence for
  the same artifact family" new claim is not demonstrated.
- Prior art (`audit-findings.md:30`, `:111`) confirmed still open. Score 16 stands.

## F-KBCTX-04 — mutable meta drops the field, read prefers it — **DOWNGRADED** → Medium (2×4 = 8)

- Code asymmetry confirmed: `store.py:251` writes it into the mutable envelope; `_write_mutable_meta`
  (`:265`, construction `:279-289`, ends `created_by=meta.created_by,` → `checksum=checksum,`) does not
  pass it; read path `:538` `"kb_context_ref": meta.get("kb_context_ref"),` + `:547`/`:553`
  `return record.model_copy(update=mutable_fields)` + `:554` `_meta_record_to_metadata` → `:747`
  `kb_context_ref=raw.get("kb_context_ref")` confirmed.
- **No observable divergence at HEAD.** The only mutable writer is `generation/ledger.py:223`
  `meta = ArtifactMetadata(` … `created_by="generation-ledger-manager",` and it passes **no**
  `kb_context_ref` — the audit itself lists `generation/ledger.py:223` in F-KBCTX-03's 11 omitting
  sites. So envelope and `meta.json` both carry `None` today; the finding's sentence
  "its writer (`ledger.py:223`) and the envelope both carry the column" (line 243-244) contradicts
  F-KBCTX-03 and is false. The stated mutation ("fix `:279-289`") would still leave the ledger `None`.
- **O3 is misclassified.** Per §1.1/§1.3 distributed ownership needs 2+ *modules*; both paths live in
  `artifacts/store.py`, which the audit's own Clean-concerns row calls "the only module that writes these
  bytes". This is an intra-module robustness defect, not an ownership seam.
- Recompute: impact 2 (latent, no observable wrong data today; the real ledger gap is F-KBCTX-03) ×
  drift 4 (no test exercises a mutable KB-ref round-trip) = **8 Medium**.

## F-KBCTX-05 — `_last_kb_context_ref` is not a channel — **DOWNGRADED** → High (3×4 = 12)

- Mechanism confirmed: `grep -rn "_last_kb_context_ref" src/ tests/` → exactly `_agent.py:120` (write),
  `_agent_artifacts.py:106` (read), `tests/unit/graph/test_services.py:53`; `ORCH_CHANNELS`
  (`orchestrator_state.py:93-165`) has no KB row; `grep -n "kb" state_schema.py` is empty (and
  `class StudioGraphState` is at `:102`) — so the key dies at every node boundary.
- The qc divergence is **reproduced** (`.venv/bin/python`, `qc_node` with a pending row update):
  `qc matrix_patch_qc kb_context_ref=None` vs
  `qc consensus_report kb_context_ref='kbctx:p1:qc:clip-validator:v1'`.
- **Falsified blast radius.** The claim that `project_profile`, `project_constraints` and
  `scope_contract` "can never carry KB provenance" is false. Reproduced by running `intake_node`:
  ```
  intake project_profile      kb_context_ref='kbctx:p1:intake:intake-classifier-agent:v1'
  intake project_constraints  kb_context_ref='kbctx:p1:intake:intake-classifier-agent:v1'
  intake scope_contract       kb_context_ref='kbctx:p1:intake:intake-classifier-agent:v1'
  ```
  because `intake_node` runs the classifier agent (`prep.py:115` → `_classify_film_idea` → `_run_agent`
  at `prep.py:58`) on `new_state` *before* the saves at `:117`, `:131` and before
  `_attach_scope_contract(new_state, …)` at `:138` (save at `:175`).
- The count "the four node files with saves but no agent run" is also wrong: `grep -c` shows only
  `generation.py` (save 1 / run 0) and `_repair_loop.py` (save 1 / run 0); `qc.py` has run 1 and
  `prep.py` has run 4. Three of the six named artifact families do carry provenance.
- Recompute: impact 3 (provenance is absent for pre-agent saves and agent-less nodes, but is present
  on most artifacts) × drift 4 = **12 High**.

## F-KBCTX-06 — dead second context system — **DOWNGRADED** → Medium (2×3 = 6)

- Core confirmed: `grep -rn "scoped_context" src/ tests/` yields exactly one source hit
  (`_agent_prompt_context.py:116`), no template consumes it (all `{kb_refs}` placeholders come from
  `_agent_prompt_context.py:22`); `context_packets.py:4` docstring vs the live
  `_context.py:356` → `_compact_upstream_content` → `compact_json_context` with
  `DEFAULT_MAX_CONTEXT_CHARS = 6000` (`kb/compression.py:10`) confirmed. `PHASE_BUILDERS` is at `:128`,
  consumed only at `_agent_prompt_context.py:109-111`.
- **Drift proof invalid as written.** The audit's mutation — "change `build_shot_bible_context` to
  return `""`; every prompt is byte-identical **and no test fails**" — is false:
  `tests/unit/graph/test_context_packets.py:123-155`
  (`test_shot_bible_context_summarizes_execution_brief_and_script`) asserts
  `"Execution brief - 120s, measured"`, `"act_1: 4 shots ([8, 10])"`,
  `"Mandatory anchors: ['opening image']"`, `"Script has 2 scenes across 3 acts"`. The claim that the
  only outside references to `PHASE_BUILDERS` are `:196-202` ignores the seven content tests at
  `:40-183`, which pin every builder's output. A valid mutation would be renaming the
  `scoped_context` key or deleting `_attach_scoped_packet` (neither is tested).
- O6 is loose (nothing consumes the dead builders, so there is no output divergence), and impact is
  maintainer confusion plus a docstring that inverts the truth, not wrong runtime behavior.
- Recompute: impact 2 × drift 3 (the dead module's own tests pin its outputs; only the wiring is
  unguarded) = **6 Medium**.

## F-KBCTX-07 — MCP bible tools as a parallel implementation — **DOWNGRADED** → Medium (2×4 = 8)

- The bypass is confirmed: `mcp/tools/bibles/shot.py:182` `raw = runner.model_adapter.chat(` with
  `f"Script:\n{script_text[:6000]}\n\n"` (`:184`); `_shared.py:104` `if runner.model_adapter is None:`,
  `:106` `raw = runner.model_adapter.chat(prompt, model=runner.model_router.resolve("creative_writer"))`;
  `character.py:39` `{script_text[:8000]}`. Both go around `run_from_template`/`build_rctco`, the KB and
  `_context.py`.
- **The two-owner premise is false.** `grep -rn "master_film_matrix" src/` has **no graph-node hit**;
  `visual.py:447` writes artifact_id `"shot_matrix"`. Reproduced (`.venv/bin/python`, `shot_bible_node`):
  `shot_bible shot_matrix type=shot_bible kb_context_ref='kbctx:p1:shot_bible:shot-design-agent:v1'`
  vs the MCP path `mcp/tools/bibles/shot.py:199`
  `store, project_id, "master_film_matrix", ArtifactType.MASTER_FILM_MATRIX, matrix`. Different id
  **and** different type (`_context.py:308` maps `MasterFilmMatrix → "shot_bible"`, not
  `master_film_matrix`), so the graph is not a producer of the artifact the MCP produces.
- The other four named ids have **no graph producer at all**: no graph node runs a bible agent
  (`grep "agent_id=" graph/nodes/visual.py` → reference-strategy-planner, structure-extractor-agent,
  shot-design-agent, provider-planning-agent) and no graph node saves `character_bible`,
  `environment_bible`, `camera_language_bible` or `style_bible`; `graph/` never imports `mcp`.
  So 4 of the 5 "same artifacts" have a single producer, not two.
- Recompute: impact 2 (the MCP bibles are the only producer of those artifacts and bypass the KB;
  no id-level divergence is shown) × drift 4 = **8 Medium**. The real defect this finding points near
  is the matrix identity split in "Missed in scope" below.

## F-KBCTX-08 — the packet never reaches a prompt — **CONFIRMED** (Critical, 4×4 = 16)

- Every anchor resolves: `runner.py:400` `_kb_context: KBContextPacket,` (unused), `:415`
  `rendered_text = template.render(**(context_vars or {}))`, `:111-122` `_kb_context_section`
  reachable only from `build_rctco` (`:97`) → `run()` (`:384`, `:393`), `:410-411`
  `"forbidden for critical-path agents"`; `_agent_prompt_context.py:22` `"kb_refs": kb.kb_context_id,`;
  `packets.py:118` `payload=_build_payload_map(all_kept),`.
- Consumers reproduced: `grep -rn "kb_context\.payload\|kb\.payload" src/` → nothing;
  `grep -rn "\.examples(" src/` → nothing; `kb_refs` renders only the opaque id in 10 templates
  (`spine.py:61,132,212,290,392`, `production.py:40,124,201,269,321` = 5 + 5 distinct templates).
- `_generate_model_output` selection confirmed (`_agent.py:140-162` template path for impls, `:169`
  generic `run()` otherwise). Drift proof (mutating `_build_payload_map`) is valid.
- Nit: the cited test is named `test_build_rctco_empty_kb_context` (`tests/unit/agents/test_runner.py:124`),
  not `..._with_empty_...`. Score 16 stands.

## F-KBCTX-09 — three KB-root resolutions — **CONFIRMED** (Medium, 2×4 = 8)

- Anchors resolve: `kb/paths.py:11-12`; `app/smoke.py:55`
  `path = Path("film-knowledge-base/index/kb-manifest.yaml")`; `app/bootstrap.py:42`
  `"film-knowledge-base/index/kb-manifest.yaml not found. "` (checked via `kb_manifest_path()` at `:39`);
  `app/health.py:58`. `ls film-knowledge-base/manifest.yaml` → absent (only `index/kb-manifest.yaml`),
  so all three agree only by accident; the mutation scenario is valid and `smoke.py:55` would keep the
  stale path.
- **Anchor error**: the test that monkeypatches `kb_manifest_path` is
  `tests/unit/app/test_app_ops.py:173`; `:172` is `monkeypatch.setattr(bootstrap, "validate_environment", list)`.
  The smoke literal is at `tests/unit/test_app_smoke.py:32` as cited.
- Note: the proposed guard ("fail when `film-knowledge-base` appears in `src/` outside `kb/paths.py`")
  would false-positive on two docstrings (`agents/prompt_templates/registry.py:7`,
  `schemas/prompt.py:14`). O1+O5 and 2×4 = 8 stand.

## F-KBCTX-10 — governance output has no consumer — **CONFIRMED** (High, 3×3 = 9)

- Anchors resolve: `mcp/tools/kb.py:102-106` returns 3 of 10 fields; `packets.py:99-100`,
  `:116` `examples=[]`, `:117` `excluded_refs=all_excluded`, `:39-44` flattening;
  `schemas/kb.py:55` and `:62` `class KBConflictRecord(MutableSchemaBase)`;
  `conflicts.py:41-47` constructs records with `detected_at`; `retrieval.py:60-71` `examples()`.
- Consumers reproduced absent: `grep -rn "KBConflictRecord" src/` → only
  conflicts/packets/schemas (never persisted, never returned); `grep -rn "excluded_refs" src/` →
  writer + declaration only; no `.examples(` caller. `tests/e2e/test_scenario_08_kb_conflict.py:22`
  hand-constructs a `KBConflictRecord`, as claimed.
- Caveat for the severity model: `tests/unit/kb/test_packets.py:104-111`
  (`assert packet.examples == []`) *pins the dead behavior*, so the drift is asymmetric (a fix to
  `examples=[]` would fail a test; a change to the conflict/exclusion pipeline would not). Drift 3 as
  scored is acceptable; the finding should say the examples test enshrines the bug.
- O8 is a loose fit (the seam *has* a typed schema; what is missing is a reader). Score 9 stands.

---

## Missed in scope (distributed-ownership seams in KB / context / provenance)

1. **Two artifact identities for one matrix type (O4 parallel registries).**
   `artifacts/registry.py:157` registers `"shot_matrix"` and `:192` registers `"master_film_matrix"`,
   both rendered by `rendering.render_shot_matrix`; nothing enforces agreement. The graph writes
   `shot_matrix` typed `shot_bible` (`visual.py:447` + `_context.py:308`; reproduced above), while the
   MCP writes `master_film_matrix` typed `master_film_matrix` (`shot.py:199`). Two consumers demand the
   MCP id: `mcp/tools/planning.py:108` (loads `shot_bible/master_film_matrix`) with the error at `:230`
   `"MasterFilmMatrix not found. Run generate_shot_bible first."`, and
   `validation/validators/__init__.py:88` `input_schema="master_film_matrix"`. A graph-completed project
   therefore has no `master_film_matrix`, and an MCP-generated matrix is invisible to
   `shot_matrix_ref` downstream. No test compares the two ids.
2. **`kb_context_packet` is a registered artifact kind with no producer (O4).**
   `artifacts/registry.py:185` `"kb_context_packet": _spec("kb_context_packet")`; `grep -rn
   "kb_context_packet" src/ tests/` returns only the registry row, the `ArtifactType` member
   (`schemas/_base.py:66`) and one schema test. No code ever saves one, so even after F-KBCTX-01 is
   fixed a persisted `kb_context_ref` cannot resolve to an artifact. Audit 09 says the ref "points at a
   packet that does not exist" but never names the orphan kind/registry row.
3. **`_ARTIFACT_TYPE_BY_CLASS` (`_context.py:300-312`) is a second normative model that disagrees with
   the writers it serves.** `MasterFilmMatrix → "shot_bible"` (should be `master_film_matrix`) and no
   entry for `ExecutionBrief`, so `visual.py:119` writes `execution_brief` with
   `artifact_type=script` (reproduced: `shot_bible execution_brief type=script`). This map and the
   explicitly-passed `artifact_type=` strings in the MCP bibles must agree, and nothing checks them — O1.

## Disputes requiring the author to fix

1. **F-KBCTX-04 vs F-KBCTX-03 are mutually contradictory.** Line 243-244 says the ledger writer
   "carr[ies] the column"; F-KBCTX-03 (line 83, 179) lists `generation/ledger.py:223` among the 11
   sites that omit it. The latter is correct (`ledger.py:223-232` passes no `kb_context_ref`).
   F-KBCTX-04 must be reframed as a latent intra-module asymmetry, not an existing divergence, and its
   O3 class dropped (§1.3 requires 2+ modules; both writers are in `artifacts/store.py`).
2. **F-KBCTX-05's blast radius and node counts are wrong.** Delete `project_profile`,
   `project_constraints`, `scope_contract` from the "can never carry KB provenance" list (reproduced:
   all three carry `kbctx:p1:intake:intake-classifier-agent:v1`), and replace "four node files with
   saves but no agent run" with the two that actually qualify (`generation.py`, `_repair_loop.py`).
3. **F-KBCTX-06's mutation scenario is invalid.** Changing `build_shot_bible_context` to return `""`
   fails `tests/unit/graph/test_context_packets.py:123-155`; substitute a wiring mutation (rename the
   `scoped_context` key or delete `_attach_scoped_packet`) and correct the claim that `:196-202` are the
   only outside references.
4. **F-KBCTX-07's producer premise is false, and F-KBCTX-03 repeats it.** The graph never writes
   `master_film_matrix`; `visual.py:447` writes `shot_matrix` typed `shot_bible`. For 4 of the 5 named
   ids there is no graph producer at all. Re-derive the finding from the actual seam (registry-id split,
   missed-scope item 1).
5. **Prior-art/quote anchors to correct:** F-KBCTX-01 `audit-findings.md:111` → `:112`;
   F-KBCTX-09 `test_app_ops.py:172` → `:173`; F-KBCTX-08 test name
   `test_build_rctco_with_empty_kb_context` → `test_build_rctco_empty_kb_context`.
6. **F-KBCTX-01 coverage phrasing.** `tests/smoke/conftest.py:10` re-exports the
   `graph_services`/`kb_builder` fixtures, so smoke tests also run with a wired builder; "the *only*
   place in the repo that populates the field" should be stated as "the only construction site".
7. **Class corrections:** F-KBCTX-06 is not a lifecycle (O6) but dead parallel policy with no consumer;
   F-KBCTX-10's O8 label should note that the typed seam exists and only the reader is missing.

**Overall verdict: the audit's central KB-provenance claims are real but the file overstates three of
them and its two most serious drift proofs (F-KBCTX-05, F-KBCTX-07) contain demonstrably false
premises — merge after the four downgrades and the seven disputes are fixed.**
