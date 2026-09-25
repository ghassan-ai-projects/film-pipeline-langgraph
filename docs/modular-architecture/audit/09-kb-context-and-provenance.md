# Audit 09 — Knowledge base, context packets, and KB provenance

Audited at `modular-app` = `fb85baa0e6b769b709791a96a89980089304bf13` (`git rev-parse HEAD`,
clean tree). Method: full source reads of the KB package, the graph context/KB-provenance
path, the MCP KB and bible tools, and the artifact envelope/store provenance columns, plus
the greps recorded in each finding. Every anchor below was read at this commit.

**Verification status (fix loop).** This file was independently verified by a different agent;
its verdict record is `docs/modular-architecture/reviews/verify-09.md`: **6 CONFIRMED, 4
DOWNGRADED, 0 REJECTED**. Corrections applied here after re-verifying each dispute at HEAD:

| Finding | Verdict | Change in this revision |
|---|---|---|
| F-KBCTX-01 | CONFIRMED 16 | prior-art anchor `:111` → `:112`; "only place that populates the field" → "only construction site" (`tests/smoke/conftest.py:10` re-exports the fixture) |
| F-KBCTX-02 | CONFIRMED 12 | unchanged |
| F-KBCTX-03 | CONFIRMED 16 | removed the false "same artifact family (`master_film_matrix`)" example; drift proof re-based on the 11-site omission alone |
| F-KBCTX-04 | **DOWNGRADED → Medium 2×4 = 8** | reclassified out of O3 (intra-module asymmetry, one module); removed the claim that the ledger writer carries the column |
| F-KBCTX-05 | **DOWNGRADED → High 3×4 = 12** | blast radius corrected: `intake_node` artifacts *do* carry provenance (`prep.py:58` runs the classifier before the saves); narrowed to the two agent-less node files (`generation.py`, `_repair_loop.py`) plus the one pre-agent save inside `qc_node` |
| F-KBCTX-06 | **DOWNGRADED → Medium 2×3 = 6** | invalid mutation proof replaced (builder outputs *are* pinned by `tests/unit/graph/test_context_packets.py:40-183`); reclassified |
| F-KBCTX-07 | **DOWNGRADED → Medium 2×4 = 8** | two-producer premise falsified; rewritten to the single-producer KB bypass; the matrix identity split moved to F-KBCTX-11 |
| F-KBCTX-08 | CONFIRMED 16 | test name corrected to `test_build_rctco_empty_kb_context` |
| F-KBCTX-09 | CONFIRMED 8 | test anchor `test_app_ops.py:172` → `:173`; guard-test false-positive noted |
| F-KBCTX-10 | CONFIRMED 9 | O8 caveat added; the test that pins the dead `examples=[]` behaviour is now named |
| F-KBCTX-11/12/13 | **added after verification** | the verifier's three missed seams, re-verified at HEAD by this author (§"Added after verification") |

**Findings after this revision: 14** — 3 Critical, 6 High, 5 Medium, 0 Low. The ten verdicts above
cover F-KBCTX-01…10; the second verification round returned: `reviews/verify-20.md` judged
F-KBCTX-11 **DOWNGRADED** (Critical 16 → High 12), F-KBCTX-12 CONFIRMED (unchanged) and F-KBCTX-13
CONFIRMED-WITH-FIX; `reviews/verify-17.md` judged F-KBCTX-14 **CORRECTED** (High 12 retained after
citing audit 03 F-CFG-15):

- **Second-round corrections applied:** F-KBCTX-11 — its falsified `visual.py:447` mutation proof
  is replaced by the existing divergence alone, and it is re-scored High (3 × 4 = 12); F-KBCTX-13 —
  the unsourced `execution_brief type=script` reproduction is dropped and a shared-fix
  cross-reference to F-KBCTX-11 added (High 3 × 4 = 12 stands); F-KBCTX-14 — its false novelty
  claim is withdrawn (audit 03 F-CFG-15 already recorded the gate-and-MCP half) and its scope
  reduced to the producer budgets, High (3 × 4 = 12).

**Header-mix check** (the band is a function of the score per `00-methodology` §1.5; this prints
the mix the line above must match):

```bash
grep -h '^- \*\*Severity:\*\*' docs/modular-architecture/audit/09-kb-context-and-provenance.md \
  | sed 's/^- \*\*Severity:\*\* \([A-Za-z]*\).*/\1/' | sort | uniq -c
# ->  3 Critical / 6 High / 5 Medium
```

---

## Coverage

| Scope | Verdict |
|---|---|
| `kb/**` — `packets.py` (119), `retrieval.py` (116), `conflicts.py` (143), `compression.py` (106), `manifest.py` (76), `paths.py` (17), `__init__.py` (19) | read in full — findings F-KBCTX-01/02/06/08/09/10/12 |
| `graph/context_packets.py` (186) | read in full — **dead second context system**, F-KBCTX-06 |
| `graph/nodes/_context.py` (465) | read in full — live context assembly, F-KBCTX-06/09/13 |
| `graph/nodes/_agent.py` (238), `_agent_artifacts.py` (150), `_agent_prompt_context.py` (149), `_agent_handoff.py` (143) | read in full — F-KBCTX-02/05/08 |
| `graph/services.py` (137) | read in full — KB builder seam, F-KBCTX-01 |
| `graph/_agent_routing.py` (211) | read in full — orphan `kb_context_ref`, F-KBCTX-02 |
| `graph/state_schema.py`, `graph/orchestrator_state.py` (`ORCH_CHANNELS`) | read — channel law for `_last_kb_context_ref`, F-KBCTX-05 |
| `agents/runner.py` (471) | read in full — KB injection seam, F-KBCTX-08 |
| `agents/handoff.py` (51) | read in full — duplicate handoff creator, F-KBCTX-08 |
| `mcp/tools/kb.py` (116) | read in full — F-KBCTX-10 |
| `mcp/tools/bibles/**` (`__init__`, `_shared`, `character`, `environment`, `camera`, `style`, `shot`) | read — F-KBCTX-03/07 |
| `artifacts/envelope.py` (176), `artifacts/store.py` (kb-provenance paths) | read — F-KBCTX-03/04 |
| `artifacts/registry.py` (KindSpec + kind table), `mcp/tools/planning.py:101-115,230`, `validation/validators/__init__.py:88` | read — matrix identity split, orphan kind, inferred-type map (F-KBCTX-11/12/13, added after verification) |
| `app/bootstrap.py`, `app/smoke.py`, `app/runtime.py:433-443`, `cli/driver.py:69-82` | read — F-KBCTX-01/09 |
| `app/mock_responses.py` (435) | read — **contains no KB/knowledge/playbook/canonical data at all**; the cluster brief's "synthetic KB data" premise does **not** hold (see Unverified) |
| `film-knowledge-base/` at repo root | inspected — manifest exists only at `index/kb-manifest.yaml`; `film-knowledge-base/manifest.yaml` does **not** exist (F-KBCTX-09) |
| `tests/unit/kb/**`, `tests/unit/graph/test_services.py`, `tests/unit/graph/test_context_packets.py`, `tests/unit/artifacts/test_store_v2.py`, `tests/unit/agents/test_runner.py`, `tests/e2e/conftest.py` | read — guard-test gaps per finding |
| Prior art (`documentation/audit-findings.md`, `documentation/reviews/arch-lens-dataflow.md`, `docs/clean-code-refactor/*`) | searched — cited per finding |

Reproduce the whole cluster's file set:

```bash
wc -l src/film_pipeline/kb/*.py src/film_pipeline/graph/context_packets.py \
  src/film_pipeline/graph/nodes/_context.py src/film_pipeline/graph/nodes/_agent*.py \
  src/film_pipeline/agents/runner.py src/film_pipeline/mcp/tools/kb.py
```

---

## Context-builder inventory

Four independent systems assemble "what the agent sees". Only two are live, and the one the
KB package exists to feed is not wired at all. Every `path:line` below is quoted verbatim in the
finding named in its row.

| # | Builder | Entry point | Live callers | Overlaps with |
|---|---|---|---|---|
| **A** | `kb.packets.KBContextPacketBuilder` — manifest retrieval → authority/supersession resolution → packet (`packets.py:57-119`) | `build()` | `graph/services.py:120` (`kb_for`); `mcp/tools/kb.py:95` (`kb_get_context_packet`); `tests/e2e/conftest.py:137` only | Defines the *concept* of a per-agent KB slice. **Never invoked on the production graph path** (F-KBCTX-01). Output content is never read (F-KBCTX-08/10). |
| **B** | `graph.context_packets.build_*_context` — 7 phase builders producing compact strings (`context_packets.py:34-136`, `PHASE_BUILDERS:128`) | `_augment_phase_context` → `_attach_scoped_packet` (`_agent_prompt_context.py:98-116`) | **none** — writes `context_vars["scoped_context"]` (`:116`), a key no prompt template references | Duplicates C's job: it re-summarises the same upstream artifacts (constitution, treatment, script, matrix, budget) that System C loads and compacts. Its module docstring claims it "Replaces loading ALL artifacts and truncating at 6000 chars" (`context_packets.py:4`) — the code that actually runs is that truncation. |
| **C** | `graph.nodes._context` — live per-node assembly: upstream artifact injection + `compact_json_context` + orchestrator summary + config context (`_context.py:341-376`, `:55-64`, `:417-431`) | `_generate_model_output` (`_agent.py:146-150`) | every graph agent run (`_agent.py:148`) | Consumes `kb.compression` (`_context.py:12`) but never `kb.packets`/`kb.retrieval`. Adds its own ad-hoc truncations (`:110`, `:189`, `:215`, `:217`, `:241`). |
| **D** | `mcp.tools.bibles.*` — hand-rolled phase prompts + direct adapter calls | `generate_character_bible` etc. | MCP tool calls (`character.py:238-249`; `shot.py:182-190`) | Re-implements context assembly from raw artifacts with its own truncation (`character.py:39` `script_text[:8000]`, `shot.py:184` `script_text[:6000]`); bypasses `PromptRunner`, `_context.py`, and the KB entirely (F-KBCTX-07). |

Compression/bounding policy likewise has no single owner: `kb/compression.py:25`
(`compact_json_context`, 6000-char default `:10`), `providers/failure_classifier.py:214`
(`compress_prompt_for_retry`), and the ad-hoc `[:8000]`/`[:6000]`/`[:150]`/`[:80]` slices above.

Conflict detection, by contrast, is single-owner: `kb/conflicts.py:17` `AUTHORITY_RANK` has no
second definition anywhere in `src/` (see Clean concerns).

---

## `kb_context_ref` lifecycle

Format grammars are mixed (F-KBCTX-02); the column is a `str | None` with `None` default in
both the envelope (`envelope.py:111`) and the current-meta pointer (`:147`). Anchors are quoted
verbatim in the finding cited in each row.

| Stage | Site | Behaviour |
|---|---|---|
| **Created (intended)** | `kb/packets.py:108` — `f"kbctx:{project_id}:{agent_id}:{uuid4().hex[:8]}"` | unique per packet; **only reachable if `kb_builder` is wired** |
| **Created (fallback, live path)** | `graph/services.py:129` — `f"kbctx:{project_id}:{phase}:{agent_id}:v1"` | non-unique synthetic id; this is what production actually stamps (F-KBCTX-01) |
| **Created (orphan)** | `graph/_agent_routing.py:201` — `f"kbctx:{agent.agent_id}:{'+'.join(sorted(allowed))}"` | a third grammar, assigned to `AgentRouteResult.kb_context_ref` (`:26`, `:75`) and **read nowhere** (F-KBCTX-02) |
| **Handed to state** | `graph/nodes/_agent.py:120` — `state["_last_kb_context_ref"] = kb.kb_context_id` | node-local only; not a declared channel (F-KBCTX-05) |
| **Stamped onto artifact** | `graph/nodes/_agent_artifacts.py:86` — `kb_context_ref=provenance.kb_context_ref` | the **only** artifact-stamping site in `src/` |
| **Defaulted from state** | `_agent_artifacts.py:105-107` — `kb_context_ref if kb_context_ref is not None else state.get("_last_kb_context_ref")` | silently `None` when the key is absent (F-KBCTX-05) |
| **Handoff (live path)** | `graph/nodes/_agent_handoff.py:131-142` | handoff dict has **no** `kb_context_ref` key, though `route_result.kb_context_ref` is in scope at `:114` |
| **Handoff (unused paths)** | `agents/runner.py:465`, `agents/handoff.py:34` | both set `kb_context_ref=kb_context.kb_context_id`; `HandoffManager.create` has **no production caller**, `PromptRunner.create_handoff` has test callers only |
| **Persisted (versioned)** | `artifacts/store.py:157` (envelope), `:184` (`ArtifactCurrentMeta`) | written on both records |
| **Persisted (mutable)** | `artifacts/store.py:251` (envelope) but `:279-289` (`_write_mutable_meta`) **omits** the field | written then dropped from `meta.json` (F-KBCTX-04) |
| **Read back** | `artifacts/store.py:726` (envelope→metadata), `:747` (meta→metadata), `:536-541` + `:547`/`:553` (mutable-field override) | for mutable kinds the `meta.json` `None` **overwrites** the envelope value |
| **Dropped entirely** | 11 `ArtifactMetadata(...)` sites outside the graph save path | `post/subtitle_agent.py:97`, `post/delivery_packaging_agent.py:166`, `post/assembly_agent.py:121`, `mcp/tools/_profile_change.py:367`, `mcp/tools/bibles/_shared.py:127`, `mcp/tools/bibles/shot.py:74`, `mcp/tools/checkpoints.py:33`, `mcp/tools/planning.py:77`, `mcp/tools/reference_generation/index_files.py:86`, `mcp/tools/validation.py:186`, `generation/ledger.py:223` (F-KBCTX-03) |
| **Not carried in derived views** | `artifacts/envelope.py:151-167` (`ArtifactIndexEntry`), `store.py:754-767` (`_render_markdown`) | absent from the index and from `current.md` |

---

## Findings

### F-KBCTX-01 — The KB packet builder is never wired into production; the graph runs on a synthetic empty packet

- **Class:** O6 (parallel lifecycle) + O3 (split state authority)
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** who constructs the KB context packet that a graph agent run consumes.
- **De-facto owners:**
  - `src/film_pipeline/graph/services.py:119-127` — the real builder branch — `"if self.kb_builder is not None:"` / `"result = self.kb_builder.build("`
  - `src/film_pipeline/graph/services.py:128-134` — the synthetic fallback every production run takes — `"kb_context_id=f\"kbctx:{project_id}:{phase}:{agent_id}:v1\","`
  - `src/film_pipeline/graph/services.py:87-91` (`for_mock_runtime`) and `:105-109` (`for_real_runtime`) — both return `cls(...)` **without** `kb_builder`
  - `src/film_pipeline/app/runtime.py:437` / `:440` and `src/film_pipeline/cli/driver.py:71` / `:75` — the only two production composition roots, both calling those factories
  - `tests/e2e/conftest.py:137` — `"kb_builder=kb_builder,"` — the only **construction** site that populates the field; `tests/smoke/conftest.py:10` re-exports the fixture (`"kb_builder,"`), so the smoke suite also runs against a wired builder
- **Drift proof (existing divergence):** the graph path and the MCP path disagree today.
  `mcp/tools/kb.py:95` builds a real packet (`"builder = KBContextPacketBuilder(manifest=manifest)"`)
  from the on-disk manifest, while `_open_kb_session` (`_agent.py:113-118`) receives a packet
  with empty `authority_policy_refs`/`playbook_refs`/`case_study_refs`/`payload` because
  `kb_builder is None`. Mutation scenario: add `kb_builder=KBContextPacketBuilder(...)` to
  `for_mock_runtime` only (`services.py:87`); `for_real_runtime` (`:105`) keeps the fallback,
  and no test fails — the sole coverage of this seam pins the *fallback*
  (`tests/unit/graph/test_services.py:131` `"def test_graph_services_kb_for_without_builder()"`),
  and the only test that asserts a packet reaches an artifact injects the ref by hand
  (`tests/unit/graph/test_services.py:53` `"\"_last_kb_context_ref\": \"kbctx:p1:agent:test-1234\","`).
- **Reproduce:**
  ```bash
  grep -rn "kb_builder" --include=*.py src/ tests/
  grep -rn "ArtifactMetadata(" --include=*.py src/ | wc -l
  ```
- **Blast radius:** `graph/services.py`, `graph/nodes/_agent.py`, `app/runtime.py`, `cli/driver.py`.
  User-visible: every agent prompt in both mock and real mode carries an empty KB slice; the
  curated manifest (`film-knowledge-base/index/kb-manifest.yaml`, 12 items) has no runtime effect
  on graph execution, and `kb_context_ref` on artifacts points at a packet that does not exist —
  the target kind has no producer at all (F-KBCTX-12).
- **Candidate owner module:** `kb-context` — owns the one function that turns a manifest +
  (project, phase, agent, task) into the packet the graph hands to prompts.
- **Extraction sketch:** move packet construction behind a single `GraphServices` factory
  argument with no `None` branch — make the builder a required collaborator (or inject a
  `KBPacketSource` Protocol implemented by both `kb.packets` and a deferred loader), so there is
  one code path. Guard test: assert that `GraphServices.for_mock_runtime(...)` and
  `for_real_runtime(...)` return a packet with non-empty `authority_policy_refs` for
  `phase="constitution"` against the repo manifest, and that no `kbctx:...:v1` synthetic id is
  ever produced (fails today).
- **Prior art:** `documentation/audit-findings.md:112` — `"GraphServices.kb_builder is None; graph nodes receive synthetic KB packets."`;
  `:172` recommends `"Stamp kb_context_ref on every artifact by wiring KBContextPacketBuilder into GraphServices"`.
  **Still present at HEAD, unchanged** — now with the exact composition-root lines and the
  test-coverage gap that let it survive.

### F-KBCTX-02 — Three incompatible gadgets all mint `kbctx:` ids; two of them are not packet ids at all

- **Class:** O1 (duplicated normative model)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** the grammar of a KB provenance identifier.
- **De-facto owners:**
  - `src/film_pipeline/kb/packets.py:108` — `"kb_context_id=f\"kbctx:{project_id}:{agent_id}:{uuid4().hex[:8]}\","` (project, agent, random)
  - `src/film_pipeline/graph/services.py:129` — `"kb_context_id=f\"kbctx:{project_id}:{phase}:{agent_id}:v1\","` (project, phase, agent, constant)
  - `src/film_pipeline/graph/_agent_routing.py:196-201` — `"return f\"kbctx:{agent.agent_id}:{'+'.join(sorted(allowed))}\""` (agent + domains; no project, no packet)
- **Drift proof (existing divergence):** the three grammars disagree on arity and on the last
  segment. A consumer cannot parse a `kb_context_ref` back into packet coordinates: the live
  production value (`services.py:129`) is identical for every run of the same
  phase+agent (`:v1`), so provenance cannot resolve to the packet that was actually used, and
  the routing value (`_agent_routing.py:201`) contains no project or packet component at all.
  Mutation scenario: add a fourth component to `packets.py:108`; `services.py:129` and
  `_agent_routing.py:201` keep their old forms; no test fails (the greps below show the only
  assertions on this field are equality to a hand-injected literal or a round-trip of the same
  object).
- **Reproduce:**
  ```bash
  grep -rn "kbctx:" --include=*.py src/
  grep -rn "kbctx:" --include=*.py tests/
  ```
- **Blast radius:** `kb/packets.py`, `graph/services.py`, `graph/_agent_routing.py`,
  `artifacts/store.py` (opaque `str` column), any future provenance/audit query.
  User-visible: an auditor reading `kb_context_ref` on a delivered artifact cannot recover the
  KB slice that shaped it.
- **Candidate owner module:** `kb-context` — one constructor (`KBContextId.for_packet(...)`) and
  one parser; the schema field stays `str` but every producer goes through it.
- **Extraction sketch:** replace the three f-strings with a single value object that carries
  `project_id`/`agent_id`/`packet_uuid`, expose `to_ref()`/`parse()`, and delete
  `AgentRouteResult.kb_context_ref` + `_build_kb_context_ref` (F-KBCTX-08 shows it is dead).
  Guard test: `parse(ref)` round-trips for every producer, and a test asserts exactly one module
  in `src/` contains the literal `kbctx:`.
- **Prior art:** new.

### F-KBCTX-03 — `kb_context_ref` is silently dropped by 11 artifact-write paths outside the graph save helper

- **Class:** O3 (split state authority) + O8 (missing contract)
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** which writer is responsible for stamping KB provenance onto a new artifact version.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/_agent_artifacts.py:86` — the only stamping site — `"kb_context_ref=provenance.kb_context_ref,"`
  - `src/film_pipeline/mcp/tools/bibles/_shared.py:127-137` — hand-built metadata with no KB column — `"created_by=created_by,"`
  - `src/film_pipeline/mcp/tools/bibles/shot.py:74-84` — `"created_by=\"mcp.generate_shot_bible\","`
  - `src/film_pipeline/generation/ledger.py:223-231` — `"created_by=\"generation-ledger-manager\","`
- **Drift proof (existing divergence):** `ArtifactMetadata.kb_context_ref` defaults to `None`
  (`schemas/artifact.py:68`), so every construction site that omits it writes an envelope with a
  null provenance pointer (`store.py:157` copies the `None` through). Mechanically: exactly one
  site in `src/` ever supplies a value — the graph save helper
  (`_agent_artifacts.py:86` `"kb_context_ref=provenance.kb_context_ref,"`) — while all 11 sites
  listed below construct `ArtifactMetadata` with the field absent. Example: the MCP matrix
  producer `mcp/tools/bibles/shot.py:199` (`store, project_id, "master_film_matrix",
  ArtifactType.MASTER_FILM_MATRIX, matrix`) writes an envelope whose `kb_context_ref` is `None`.
  The only two tests that assert a non-null value inject it explicitly
  (`tests/unit/graph/test_services.py:60`, `tests/unit/artifacts/test_store_v2.py:126`).
  Mutation scenario: change the KB id grammar in `kb/packets.py:108`; the 11 sites below keep
  writing nothing, and no test fails.
- **Reproduce:**
  ```bash
  grep -rln "ArtifactMetadata(" --include=*.py src/ | grep -v __pycache__ | xargs grep -Ln "kb_context_ref"
  ```
  → exactly: `post/subtitle_agent.py`, `post/delivery_packaging_agent.py`,
  `post/assembly_agent.py`, `mcp/tools/_profile_change.py`, `mcp/tools/bibles/_shared.py`,
  `mcp/tools/bibles/shot.py`, `mcp/tools/checkpoints.py`, `mcp/tools/planning.py`,
  `mcp/tools/reference_generation/index_files.py`, `mcp/tools/validation.py`,
  `generation/ledger.py`.
- **Blast radius:** every MCP-initiated and post-production artifact write. User-visible: an
  operator asking "which KB rules produced this character bible / subtitle track / delivery
  package?" gets `null`; whether the column is populated depends entirely on which surface wrote
  the artifact, not on which KB context governed the work.
- **Candidate owner module:** `artifacts` (the *writer* of the provenance column) plus
  `kb-context` (the *value*). The artifact store should require the KB ref to be supplied or
  explicitly waived, not default to null.
- **Extraction sketch:** add a `provenance` parameter object to `ArtifactStore.save()` (or a
  `KbProvenance` value object on `ArtifactMetadata` construction) so an omitted ref is a type
  error rather than a silent `None`; migrate the 11 sites. Guard test: enumerate
  `ArtifactMetadata(` construction sites by AST and fail when one does not pass a
  `kb_context_ref` and is not on an explicit allowlist with a written reason.
- **Prior art:** `documentation/audit-findings.md:30` (`"kb_context_ref is not stamped on artifacts"`)
  and `:111` (`"almost never populated"`). Still true at HEAD; new here is the exact 11-site
  enumeration and the absence of any guard test.

### F-KBCTX-04 — Mutable artifacts serialise `kb_context_ref` into the envelope but not into `meta.json`, whose value overrides it on read (latent, intra-module)

- **Class:** none of O1–O8 — an intra-module robustness defect. The §1.3 distributivity test fails
  (one module, two write paths), so this is retained at reduced severity as a latent defect rather
  than presented as an ownership seam.
- **Severity:** Medium (impact 2 × drift 4 = 8) — downgraded from High 9 during verification
- **Concern:** which record is authoritative for a mutable artifact's KB provenance.
- **De-facto owners:** (one module only)
  - `src/film_pipeline/artifacts/store.py:251` — the mutable envelope does carry it — `"kb_context_ref=meta.kb_context_ref,"`
  - `src/film_pipeline/artifacts/store.py:279-289` — `_write_mutable_meta` builds `ArtifactCurrentMeta` **without** the field (`:288` `created_by=meta.created_by,` → `:289` `checksum=checksum,`)
  - `src/film_pipeline/artifacts/store.py:536-541` + `:553` — the read path overrides the envelope value with the meta value — `"\"kb_context_ref\": meta.get(\"kb_context_ref\"),"` then `"return record.model_copy(update=mutable_fields)"`
  - `src/film_pipeline/artifacts/store.py:184` — the versioned meta write **does** include it, so two write paths inside one module disagree
- **Why this is not O3 (§1.1/§1.3):** distributed ownership requires two or more *modules*; both
  writers are `artifacts/store.py`, which this audit's own Clean-concerns table records as the
  only module that writes these bytes. This is intra-module asymmetry with a latent failure, not
  an ownership seam.
- **Drift proof (latent — corrected from the first revision):** there is **no** observable
  divergence at HEAD. The only mutable kind is `generation_ledger`
  (`artifacts/registry.py:163`), and its sole writer passes no `kb_context_ref`
  (`generation/ledger.py:223-231`, `"created_by=\"generation-ledger-manager\","`) — the same site
  F-KBCTX-03 lists among its 11 omissions. Envelope and `meta.json` therefore both carry `None`
  and agree by accident. The first revision of this audit wrongly stated that the ledger writer
  "carries the column"; it does not.
  Mutation scenario: pass `kb_context_ref="kbctx:…"` at `generation/ledger.py:223`; the envelope
  records it (`:251`) while `meta.json` does not (`:279-289`), and `load_metadata` returns `None`
  because `mutable_fields` (`:536-541`) is applied last (`:547`/`:553`). No test fails:
  `tests/unit/artifacts/test_store_v2.py:116-126` exercises `store.save` (the versioned path)
  only, and no test round-trips a mutable artifact's KB ref.
- **Reproduce:**
  ```bash
  grep -n "kb_context_ref" src/film_pipeline/artifacts/store.py
  sed -n '279,290p' src/film_pipeline/artifacts/store.py
  grep -rn "mutable=True" --include=*.py src/
  sed -n '223,232p' src/film_pipeline/generation/ledger.py
  ```
- **Blast radius:** `artifacts/store.py` mutable path; `generation/ledger.py` (the only calling
  module). Latent: it becomes user-visible only once the ledger's KB ref is populated (i.e. once
  F-KBCTX-01 and F-KBCTX-03 are fixed), at which point the generation ledger — the
  cost/idempotency audit trail — would silently report no KB context.
- **Candidate owner module:** `artifacts` — both write paths must serialise the same provenance
  field set, and a derived record must not null out an immutable envelope field.
- **Extraction sketch:** make `ArtifactCurrentMeta` construction from `ArtifactMetadata` a single
  helper used by both `_save_locked` and `_write_mutable_meta`, and drop `kb_context_ref` from
  `mutable_fields` (`:536-541`) since it is immutable provenance. Guard test: save a mutable
  artifact whose metadata carries a KB ref, read it back, assert the ref is present (fails
  today).
- **Prior art:** new (the prior audits only note that the column is "often empty", not that the
  store's two write paths disagree).

### F-KBCTX-05 — `_last_kb_context_ref` is a node-local state key that is not a graph channel, so provenance is absent on saves that precede an agent run in their node

- **Class:** O5 (policy-by-branch) + O3 (split state authority)
- **Severity:** High (impact 3 × drift 4 = 12) — downgraded from Critical 16 during verification
- **Concern:** how the KB context id reaches the artifact-write path when that path runs before
  any agent run in the same node (or in a node that runs no agent at all).
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/_agent.py:120` — the only writer — `"state[\"_last_kb_context_ref\"] = kb.kb_context_id"`
  - `src/film_pipeline/graph/nodes/_agent_artifacts.py:105-107` — the only reader, defaulting silently — `"kb_context_ref if kb_context_ref is not None else state.get(\"_last_kb_context_ref\")"`
  - `src/film_pipeline/graph/orchestrator_state.py:93-165` — `ORCH_CHANNELS`, the declared list of
    keys that cross a node boundary — contains **no** KB row
  - `src/film_pipeline/graph/state_schema.py:102` — `"class StudioGraphState(TypedDict, total=False):"` — contains **no** `kb` key at all
- **Drift proof (existing divergence inside one node):** in `qc_node`
  (`graph/nodes/qc.py:33-44`) the matrix patch is saved at `:39`
  (`_emit_matrix_patch_from_findings` → `_save_artifact`, `:83`) *before* the only agent run at
  `:40` (`_synthesize_consensus_report` → `_run_agent`, `:97` → `_save_artifact`, `:109`). Both
  calls go through the same `_resolve_provenance`, so the patch at `:83` gets `None` and the
  consensus report at `:109` gets the `clip-validator` ref (reproduced during verification:
  `qc matrix_patch_qc kb_context_ref=None` vs
  `qc consensus_report kb_context_ref='kbctx:p1:qc:clip-validator:v1'`). Two further node files
  have saves with **zero** `_run_agent` calls: `generation_node` (`generation.py:105-114`, save 1
  / run 0) saves a `MatrixPatch` at `:93`, and `repair_phase_node` persists feedback at `:230`
  before re-running the phase node that would open a KB session at `:234`
  (`_repair_loop.py`, save 1 / run 0). The key is written into the node's local `deepcopy`ed dict
  and appears in no returned `updates` dict (`grep -rn "_last_kb_context_ref" src/` → the two
  sites above only). Mutation scenario: change the key name in `_agent.py:120`;
  `_agent_artifacts.py:106` silently returns `None` for every artifact and no test fails —
  `tests/unit/graph/test_services.py:53` injects the literal key into a hand-written state dict
  rather than exercising the node.
- **Reproduce:**
  ```bash
  grep -rn "_last_kb_context_ref" --include=*.py src/ tests/
  grep -n "kb" src/film_pipeline/graph/state_schema.py    # no output
  for f in src/film_pipeline/graph/nodes/*.py; do echo "$f save=$(grep -c '_save_artifact(' $f) run=$(grep -c '_run_agent(' $f)"; done
  ```
- **Blast radius:** all 19 `_save_artifact` sites reach this through the same silent default, but
  provenance is actually absent only for saves that precede any `_run_agent` in their node.
  **Corrected during verification:** `intake_node`'s three saves (`prep.py:117`, `:131`, `:175`)
  **do** carry provenance, because `prep.py:115` calls `_classify_film_idea` → `_run_agent`
  (`prep.py:58`) on `new_state` first (reproduced:
  `intake project_profile kb_context_ref='kbctx:p1:intake:intake-classifier-agent:v1'`, likewise
  for `project_constraints` and `scope_contract`). The first revision wrongly listed those three
  as never carrying provenance. What remains: `matrix_patch_generation`
  (`generation.py:93`), `matrix_patch_qc` (`qc.py:83`) and `repair_feedback_<phase>`
  (`_repair_loop.py:170`). User-visible: the column's meaning changes per artifact with no rule —
  same node, same helper, one save stamped and the next null.
- **Candidate owner module:** `kb-context` owns the *value*; `graph` state owns the *channel*.
  The fix is one explicit channel plus an explicit "no KB context" sentinel rather than a
  silent `None` default.
- **Extraction sketch:** either add `_last_kb_context_ref` to `ORCH_CHANNELS` as a real channel
  (so a run's KB ref travels with the run) or, better, pass the `KBContextPacket` explicitly into
  every `_save_artifact` call and make the state lookup fallback illegal. Guard test: run
  `qc_node`, `generation_node` and `repair_phase_node` against a wired services object and assert
  every artifact written in the node reports a non-null `kb_context_ref` (fails today for
  `matrix_patch_qc`, `matrix_patch_generation`, `repair_feedback_*`).
- **Prior art:** `documentation/reviews/arch-lens-dataflow.md:191` records the write
  (`"state[\"_last_kb_context_ref\"] mutated, :117"`) but not that the key is not a channel and
  therefore does not survive the boundary. New here.

### F-KBCTX-06 — A second, dead phase-context system duplicates the live one and its docstring describes behaviour that does not run (unwired dead policy)

- **Class:** unwired parallel policy with no consumer — *not* O6 lifecycle (nothing consumes its
  output, so there is no lifecycle divergence to observe)
- **Severity:** Medium (impact 2 × drift 3 = 6) — downgraded from High 12 during verification
- **Concern:** which module defines what context a phase's agent receives.
- **De-facto owners:**
  - `src/film_pipeline/graph/context_packets.py:128-136` — the dead registry — `"PHASE_BUILDERS: dict[str, Callable[..., str]] = {"`
  - `src/film_pipeline/graph/context_packets.py:4` — its (false) claim — `"phase's agent needs. Replaces loading ALL artifacts and truncating at 6000 chars."`
  - `src/film_pipeline/graph/nodes/_agent_prompt_context.py:116` — the only consumer, writing a key nobody reads — `"context_vars[\"scoped_context\"] = builder(state, services)"`
  - `src/film_pipeline/graph/nodes/_context.py:356` — the live assembly it claims to replace — `"context_vars[content_key] = _compact_upstream_content(state, services, project_id, ref)"`
- **Drift proof (existing divergence):** `grep -rn "scoped_context" src/ tests/` returns exactly
  one hit (`_agent_prompt_context.py:116`, the write); no prompt template under
  `agents/prompt_templates/` references it, so seven builders (`context_packets.py:34-124`) execute
  and their output is discarded. The live path meanwhile does exactly the thing the dead module's
  docstring says it replaced: `_compact_upstream_content` calls `compact_json_context(...)` with
  `DEFAULT_MAX_CONTEXT_CHARS = 6000` (`kb/compression.py:10`, consumed at `_context.py:12`).
  **Mutation scenario (corrected during verification):** the builders themselves *are* pinned —
  `tests/unit/graph/test_context_packets.py:40-183` holds seven content tests, e.g. `:123-155`
  (`test_shot_bible_context_summarizes_execution_brief_and_script`) asserts
  `"Execution brief - 120s, measured"`, `"act_1: 4 shots ([8, 10])"` and
  `"Script has 2 scenes across 3 acts"`, and `:196-202` pins the `PHASE_BUILDERS` map. The first
  revision's mutation ("change `build_shot_bible_context` to return `""` … no test fails") was
  therefore false. What is unguarded is the *wiring*: rename the `scoped_context` key at
  `_agent_prompt_context.py:116`, or delete `_attach_scoped_packet` entirely, and no test fails.
- **Reproduce:**
  ```bash
  grep -rn "scoped_context" src/ tests/
  grep -rn "PHASE_BUILDERS" src/ tests/
  ```
- **Blast radius:** `graph/context_packets.py`, `graph/nodes/_agent_prompt_context.py`. A
  maintainer editing phase context finds two candidate modules, only one of which has any effect;
  the refactor direction stated in the code is the opposite of the truth.
- **Candidate owner module:** delete `graph/context_packets.py`, or promote it to the single owner
  and delete `_inject_artifact_context`. The `kb-context` module should own whichever survives.
- **Extraction sketch:** decide the winner and remove the other, including
  `_attach_scoped_packet` and the `scoped_context` key. Guard test: a template-variable test that
  fails when `_augment_phase_context` writes a `context_vars` key that no registered template
  placeholder consumes (would fail today on `scoped_context`).
- **Prior art:** new.

### F-KBCTX-07 — The MCP bible tools are the only producer of the bible artifacts and bypass the prompt-runner, the KB, and every shared context policy

- **Class:** O5 (policy-by-branch) — model profile and context-size policy re-derived at each MCP call site
- **Severity:** Medium (impact 2 × drift 4 = 8) — downgraded from High 12 during verification
- **Concern:** how a bible artifact is produced, and which module owns its prompt context, model profile, and provenance.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/bibles/shot.py:182-184` — a raw adapter call with a local truncation — `"raw = runner.model_adapter.chat("` / `f"Script:\n{script_text[:6000]}\n\n"`
  - `src/film_pipeline/mcp/tools/bibles/_shared.py:104-106` — the same bypass for every bible, with a hardcoded profile — `"if runner.model_adapter is None:"` / `"raw = runner.model_adapter.chat(prompt, model=runner.model_router.resolve(\"creative_writer\"))"`
  - `src/film_pipeline/mcp/tools/bibles/character.py:39` — a second, different local truncation — `{script_text[:8000]}`
  - `src/film_pipeline/mcp/tools/bibles/shot.py:199` — the sole writer of `master_film_matrix` — `store, project_id, "master_film_matrix", ArtifactType.MASTER_FILM_MATRIX, matrix`
- **Drift proof (corrected — the first revision's two-producer premise was false):** 4 of the 5
  bible artifacts have **no** graph producer. `grep -rn "character_bible\|environment_bible\|camera_language_bible\|style_bible" src/film_pipeline/graph/`
  matches only `_generation_prompts.py:120,123` — **loads**, not saves; no graph node runs a bible
  agent (`grep -n "agent_id=" src/film_pipeline/graph/nodes/visual.py` →
  `reference-strategy-planner`, `structure-extractor-agent`, `shot-design-agent`,
  `provider-planning-agent`) and `graph/` never imports `mcp`. For the matrix the graph writes a
  **different artifact id** — `visual.py:447` `"ref = _save_artifact(new_state, shot_matrix,
  \"shot_matrix\", \"shot_bible\")"` (reproduced: `shot_bible shot_matrix type=shot_bible`) — while
  the MCP writes `master_film_matrix` (`shot.py:199`); that id split is tracked separately as
  F-KBCTX-11 and is not evidence of one artifact with two producers. What remains is a
  single-producer bypass: the MCP bible tools are the only path building these prompts, and they
  re-derive the model profile (the `"creative_writer"` literal) and the context budget (`[:8000]`
  vs `[:6000]`) locally. Mutation scenario: change the creative-writer profile mapping in
  `_AGENT_PROFILE_MAP` or `ModelRouter`; the MCP bibles keep `"creative_writer"` and `[:6000]`,
  and no test fails — the MCP bible suites mock `model_adapter.chat` directly rather than
  asserting which surface produced the artifact.
- **Reproduce:**
  ```bash
  grep -rn "model_adapter.chat(" src/film_pipeline/mcp/tools/bibles/
  grep -rn "character_bible\|environment_bible\|camera_language_bible\|style_bible" --include=*.py src/film_pipeline/graph/
  grep -rn "master_film_matrix" --include=*.py src/ | grep -v __pycache__
  ```
- **Blast radius:** `mcp/tools/bibles/**`. User-visible: the five bible artifacts are produced with
  a prompt context and model profile that no shared policy controls, and with `kb_context_ref`
  always null (F-KBCTX-03); a KB or prompt-template change reaches the graph path and misses this
  one.
- **Candidate owner module:** one `bible-generation` module owning prompt assembly, model-profile
  resolution, truncation and provenance for each bible, called by the MCP tools (and by graph
  nodes if they ever produce bibles).
- **Extraction sketch:** route the MCP bibles through shared assembly (`run_from_template`-style,
  one registered template per bible) so profile, budget and KB block come from one place; the MCP
  layer keeps only argument parsing and response shaping. Guard test: assert no module outside the
  owner resolves a model profile from a string literal, and that every bible artifact written
  carries a non-null `kb_context_ref` when a packet exists.
- **Prior art:** `documentation/audit-findings.md:25` notes creator tools bypassing the
  orchestrator generally; new here is that the bypass also skips the KB and the shared context
  policy, and that four bible ids have no graph producer at all.

### F-KBCTX-08 — The packet's content never reaches a prompt: the template path discards the `KBContextPacket`, and only its opaque id is rendered

- **Class:** O8 (missing contract) + O7 (leaked internals via a stringly-typed id)
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** what a KB context packet must deliver to a model prompt.
- **De-facto owners:**
  - `src/film_pipeline/agents/runner.py:400` + `:415` — the required critical-agent path takes the packet and ignores it — `"_kb_context: KBContextPacket,"` … `"rendered_text = template.render(**(context_vars or {}))"`
  - `src/film_pipeline/agents/runner.py:111-122` — the only renderer of packet *references*, reachable only from the generic path — `"if kb_context.authority_policy_refs:"`
  - `src/film_pipeline/agents/runner.py:86-100` + `:393` — the generic path that does use it — `"prompt = self.build_rctco(contract, kb_context, task)"`
  - `src/film_pipeline/graph/nodes/_agent_prompt_context.py:22` — what the live templates actually get — `"\"kb_refs\": kb.kb_context_id,"`
  - `src/film_pipeline/kb/packets.py:118` — the never-read content — `"payload=_build_payload_map(all_kept),"`; field declared at `schemas/kb.py:56-59`
- **Drift proof (existing divergence):** `_generate_model_output` uses `run_from_template` for
  every agent that has an implementation class (`_agent.py:140-162`) and `run()` only for those
  without (`:169`). The docstring at `runner.py:410-411` states the generic assembly is
  `"forbidden for critical-path agents"`, so the path that *does* render KB refs is reserved for
  the agents least likely to need them. `grep -rn "kb_context\.payload\|kb\.payload" src/`
  returns nothing, so `KBContextPacket.payload` has no reader; the field is written
  (`packets.py:118`), declared (`schemas/kb.py:56-59`) and never consumed. Ten
  templates render `{kb_refs}` (`agents/prompt_templates/defaults/spine.py:61,132,212,290,392`,
  `production.py:40,124,201,269,321`), i.e. an opaque id string. Mutation scenario: change
  `_build_payload_map` (`packets.py:47-53`) to return item summaries as bodies; nothing in any
  prompt changes and no test fails — `tests/unit/agents/test_runner.py:124`
  (`test_build_rctco_empty_kb_context`, asserting `"No KB context."`) covers only the generic
  path, and `tests/unit/kb/test_packets.py:68-78` asserts `payload` keys exist, never that any
  consumer reads them.
- **Reproduce:**
  ```bash
  grep -rn "_kb_context" src/film_pipeline/agents/runner.py
  grep -rn "kb_context\.payload\|kb\.payload" src/
  grep -rn "kb_refs" --include=*.py src/
  grep -rn "excluded_refs\|authority_policy_refs\|playbook_refs\|case_study_refs" --include=*.py src/
  ```
- **Blast radius:** `agents/runner.py`, `agents/prompt_templates/defaults/*`, all 20 MVP agents'
  prompts. User-visible: the KB — the entire governed-policy mechanism — contributes one id
  string to shipped prompts; canonical policies, playbooks, case studies, exclusions, and
  compression-aware payload never influence model output.
- **Candidate owner module:** `kb-context` owns the packet; `agents` owns rendering. The seam
  needs a typed renderer (`render_kb_block(packet) -> str`) that both `run()` and
  `run_from_template()` call, instead of `_kb_context_section` being private to one branch.
- **Extraction sketch:** inject the rendered KB block into `context_vars` (e.g.
  `context_vars["kb_context"]`) at `_build_template_context` (`_agent_prompt_context.py:17-54`)
  and let templates consume it; delete the unused `_kb_context` parameter or make it required for
  both entry points. Guard test: assert that a packet with a canonical policy produces that
  policy's summary text in the rendered prompt for a template-path agent (fails today).
- **Prior art:** new (the prior audit recommends *wiring* the builder, F-KBCTX-01; it does not
  observe that even a wired packet would not reach the prompt).

### F-KBCTX-09 — The KB root is resolved in three modules with divergent candidate rules

- **Class:** O1 (duplicated normative model) + O5 (policy-by-branch)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** where the KB manifest lives.
- **De-facto owners:**
  - `src/film_pipeline/kb/paths.py:10-16` — the intended owner, two candidates in priority order — `"Path(\"film-knowledge-base/manifest.yaml\"),"` / `"Path(\"film-knowledge-base/index/kb-manifest.yaml\"),"`
  - `src/film_pipeline/app/smoke.py:55` — a hardcoded single path — `"path = Path(\"film-knowledge-base/index/kb-manifest.yaml\")"`
  - `src/film_pipeline/app/bootstrap.py:42` — a hardcoded message that assumes the other rule — `"\"film-knowledge-base/index/kb-manifest.yaml not found. \""` (checked via `kb_manifest_path()` at `:39`)
- **Drift proof (existing divergence):** at HEAD only
  `film-knowledge-base/index/kb-manifest.yaml` exists (`ls film-knowledge-base/manifest.yaml`
  → *No such file or directory*), so all three agree by accident. But `kb_manifest_path()` would
  prefer a root `manifest.yaml` the moment an operator creates one, while `smoke.py` continues to
  read the `index/` file and bootstrap's message names a path that is no longer the one being
  checked. Mutation scenario: create `film-knowledge-base/manifest.yaml` with different items;
  `KBRetrieval` (via `mcp/tools/kb.py:23` and any wired builder) silently switches manifests,
  `check_kb_manifest` (`smoke.py:58`) keeps loading the old file, and no test fails — the smoke
  test asserts the same literal (`tests/unit/test_app_smoke.py:32`) and the app tests monkeypatch
  `kb_manifest_path` to a tmp file (`tests/unit/app/test_app_ops.py:173`) without touching
  `smoke.py`. All paths are CWD-relative `Path(...)` literals, so the resolution also varies with
  the process working directory.
- **Reproduce:**
  ```bash
  grep -rn "film-knowledge-base" --include=*.py src/
  ls film-knowledge-base/manifest.yaml   # absent at fb85baa
  ```
- **Blast radius:** `kb/paths.py`, `app/smoke.py`, `app/bootstrap.py`, `app/health.py:58` (uses
  the owner correctly). User-visible: doctor/smoke output can disagree with what the runtime
  actually loaded, and the failure is silent.
- **Candidate owner module:** `kb` (`paths.py`) — one resolver that all three call, with no
  second literal anywhere.
- **Extraction sketch:** make `kb_manifest_path()` accept an injected root, have `smoke.py` and
  `bootstrap.py` call it (bootstrap's message should render the resolved path), and add a guard
  test that fails when the literal `"film-knowledge-base/"` appears in `src/` outside
  `kb/paths.py`. Note (verifier): a naive guard on the bare substring `film-knowledge-base`
  false-positives on two docstrings — `agents/prompt_templates/registry.py:7` and
  `schemas/prompt.py:14` — so the guard must match the path literal, not the KB directory name.
- **Prior art:** new.

### F-KBCTX-10 — The packet's governance output has no consumer, and the MCP tool returns a truncated projection of the packet it just built

- **Class:** O8 (missing contract) — caveat: the typed seam already exists (`schemas/kb.py:36-59`);
  what is missing is a *reader*, not a type
- **Severity:** High (impact 3 × drift 3 = 9) — confirmed
- **Concern:** the contract between KB governance (conflicts, exclusions, examples) and its observers.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/kb.py:102-106` — the external surface returns 3 of 10 packet fields — `"return _ok("` / `"project_id=packet.project_id,"` / `"authority_policy_refs=packet.authority_policy_refs,"`
  - `src/film_pipeline/kb/packets.py:99-100` — conflict records created then converted away — `"conflicts = detector.detect_conflicts(all_kept)"` / `"_note_unresolved_conflicts(conflicts, all_excluded)"`
  - `src/film_pipeline/kb/packets.py:116` — examples always empty although retrieval can produce them — `"examples=[],"` vs `kb/retrieval.py:60-71` `"def examples("`
  - `src/film_pipeline/schemas/kb.py:55-59` — declared but unread fields — `"excluded_refs: list[KBExcludedRef] = Field(default_factory=list)"`
- **Drift proof (existing divergence):** `KBConflictRecord` is declared as a `MutableSchemaBase`
  (`schemas/kb.py:62`), i.e. a persistable record, and is constructed by `detect_conflicts`
  (`conflicts.py:41-47`) with `detected_at` timestamps, but `grep -rn "KBConflictRecord" src/`
  shows it is never persisted and never returned; `_note_unresolved_conflicts` flattens it into
  `KBExcludedRef` (`packets.py:39-44`) which, in turn, `grep -rn "excluded_refs" src/` shows has
  no reader. `KBRetrieval.examples()` (`retrieval.py:60`) has no caller in `src/` while the packet
  hardcodes `examples=[]`. Mutation scenario: make `resolve_authority` drop conflicts silently;
  the packet's `excluded_refs` shrinks and nothing fails — `tests/unit/kb/test_conflicts.py` tests
  the detector in isolation and `tests/e2e/test_scenario_08_kb_conflict.py:22` constructs a
  `KBConflictRecord` by hand rather than reading one back from storage or an MCP response.
  The drift is asymmetric (verifier note): `tests/unit/kb/test_packets.py:104-111`
  (`assert packet.examples == []`) actively *pins* the dead `examples` behaviour, so fixing that
  half breaks a test, while a silent change to the conflict/exclusion pipeline breaks nothing.
- **Reproduce:**
  ```bash
  grep -rn "KBConflictRecord" --include=*.py src/
  grep -rn "excluded_refs\|examples=" --include=*.py src/
  grep -rn "\.examples(" --include=*.py src/
  sed -n '102,106p' src/film_pipeline/mcp/tools/kb.py
  ```
- **Blast radius:** `kb/packets.py`, `kb/conflicts.py`, `mcp/tools/kb.py`, `schemas/kb.py`.
  User-visible: a KB curator cannot learn which items were excluded or why, nor which conflicts
  remain unresolved — the "governed" part of the context packet is write-only.
- **Candidate owner module:** `kb` — the packet is the contract; conflict/exclusion records need
  one declared sink (an artifact or a store) and one reader.
- **Extraction sketch:** define the packet's public projection once (all content fields or an
  explicitly documented subset) and have `kb_get_context_packet` return it; persist
  `KBConflictRecord`s or delete the type; either use `retrieval.examples()` or delete it.
  Guard test: the MCP response keys must equal the packet's declared content fields (fails
  today), and a conflict fixture must be observable through the MCP surface.
- **Prior art:** new.

---

## Added after verification

These three seams were identified by the verifier as missed in the first revision of this audit.
Each was independently re-verified at HEAD by this author before being recorded here.

### F-KBCTX-11 — One matrix payload has two registry identities, and the MCP consumers require the id the graph never writes

- **Class:** O4 (parallel registries)
- **Severity:** High (impact 3 × drift 4 = 12) — downgraded from Critical 16 during the second verification round (`reviews/verify-20.md`)
- **Concern:** which artifact id is the canonical identity of the MasterFilmMatrix payload.
- **De-facto owners:**
  - `src/film_pipeline/artifacts/registry.py:157` — the graph's id — `"\"shot_matrix\": _spec(\"shot_matrix\", renderer=rendering.render_shot_matrix),"` → kind `film.studio/shot-matrix` (`:119` `"return f\"film.studio/{artifact_id.replace('_', '-')}\""`)
  - `src/film_pipeline/artifacts/registry.py:192` — the MCP's id, **same renderer** — `"\"master_film_matrix\": _spec(\"master_film_matrix\", renderer=rendering.render_shot_matrix),"`
  - `src/film_pipeline/graph/nodes/visual.py:447` — the graph writer — `"ref = _save_artifact(new_state, shot_matrix, \"shot_matrix\", \"shot_bible\")"`
  - `src/film_pipeline/mcp/tools/bibles/shot.py:199` — the MCP writer of the other id — `store, project_id, "master_film_matrix", ArtifactType.MASTER_FILM_MATRIX, matrix`
  - `src/film_pipeline/mcp/tools/planning.py:108` — a consumer that requires the MCP id — `"version = max(1, store.latest_version(project_id, \"shot_bible\", \"master_film_matrix\"))"`, failing at `:230` — `"return _error(\"MasterFilmMatrix not found. Run generate_shot_bible first.\")"`
  - `src/film_pipeline/validation/validators/__init__.py:88` — a second declaration of the MCP id — `input_schema="master_film_matrix"` (descriptive only; see drift proof)
- **Drift proof (existing divergence):** the two registry rows are two identities for one payload —
  same renderer `rendering.render_shot_matrix`, distinct kind slugs — and the writer and reader
  disagree today: `visual.py:447` persists under `shot_matrix`, while `planning.py:108` looks up
  `master_film_matrix`; `_load_master_matrix` (`planning.py:101-115`) wraps the read in
  `"except FileNotFoundError:"` / `"return None"`, and `store.load` raises `FileNotFoundError` for
  an absent version (`store.py:543-545`), so the planning tool returns the hard error at `:230` for
  a matrix that exists under the other id. The `input_schema="master_film_matrix"` declaration
  (`validation/validators/__init__.py:88`) is not a second runtime failure: no module in `src/`
  *reads* `ValidatorRegistryEntry.input_schema`, so it is unenforced metadata that nevertheless
  names the same non-graph id — and the first revision's characterization of that grep was wrong:
  `grep -rn "input_schema" --include=*.py src/ | wc -l` returns **26**, not 3 (the field declaration
  at `src/film_pipeline/schemas/registries/validator_registry.py:28`, the two unrelated MCP *tool*
  schemas at `mcp/contract.py:111` / `mcp/_stdio_transport.py:39`, and 22 validator-registration
  sites that pass `input_schema=` in `validation/validators/__init__.py` and `validation/impl/*.py`).
  The first revision's mutation proof is **falsified**: changing `visual.py:447`'s id to
  `master_film_matrix` *does* fail — `tests/unit/graph/test_shot_bible_structure.py:180` loads the
  graph's artifact by hard-coded id
  (`**services.artifact_store.load("third-interval", FilmPhase("shot_bible"), "shot_matrix", 1)`),
  so the mutation raises `FileNotFoundError` and fails
  `test_five_scene_film_shot_matrix_conforms_to_three_act_brief` (`reviews/verify-20.md` §2.1). The
  finding therefore rests on the existing divergence alone. The fixture enumeration is corrected
  too: `artifact:shot_bible:shot_matrix:v1` also occurs at
  `tests/unit/graph/test_generation_node_ledger.py:53,130` and
  `tests/unit/graph/test_context_packets.py:174` (all hand-written refs), so the first revision's
  "every other occurrence" was not exhaustive. **Why impact is 3, not 4:** the graph's matrix
  content is correct; the failure is a cross-surface lookup refusal ("Run generate_shot_bible
  first." for a matrix that exists) that re-running the producer clears — recoverable
  internal/UX behavior, not a corrupted deliverable and not durable-data corruption. **Shared
  fix:** this finding and F-KBCTX-13 are the artifact-**id** and `artifact_type` halves of one
  `MasterFilmMatrix` identity decision — schedule them as one job, not two.
- **Reproduce:**
  ```bash
  sed -n '157p;192p' src/film_pipeline/artifacts/registry.py
  sed -n '447p' src/film_pipeline/graph/nodes/visual.py
  sed -n '108p;230p' src/film_pipeline/mcp/tools/planning.py
  grep -rn "master_film_matrix" --include=*.py src/film_pipeline/graph/   # no output
  grep -rn "input_schema" --include=*.py src/ | wc -l                     # 26
  sed -n '180p' tests/unit/graph/test_shot_bible_structure.py
  grep -rn "artifact:shot_bible:shot_matrix:v1" tests/ --include=*.py
  ```
- **Blast radius:** `artifacts/registry.py`, `graph/nodes/visual.py`,
  `mcp/tools/bibles/shot.py`, `mcp/tools/planning.py`, `validation/validators/__init__.py`.
  User-visible: after a graph-only run, MCP planning tells the operator
  "Run generate_shot_bible first." for a matrix that already exists, and a matrix produced through
  the MCP is invisible to every graph consumer that follows `shot_matrix_ref` — the two surfaces
  cannot see each other's matrix.
- **Candidate owner module:** `artifacts` (the registry) owns id identity; one id must be
  canonical for the `MasterFilmMatrix` payload, with the other either removed or registered as an
  alias that resolves to it.
- **Extraction sketch:** pick one artifact id, delete the other registry row, and make
  `ArtifactStore.load`/`latest_version` resolve a documented alias if backwards compatibility is
  needed; update `visual.py:447` or `planning.py:108` accordingly. Guard test: assert no two
  registry rows share a renderer, and that every `ArtifactType` member used by a consumer
  (`planning.py:108`, `validators/__init__.py:88`) is written by at least one producer in `src/`.
- **Prior art:** new (verifier-found; recorded here as a finding rather than an append.)

### F-KBCTX-12 — `kb_context_packet` is a registered artifact kind with no producer, so a persisted ref can never resolve

- **Class:** O4 (registries must agree with producers; nothing enforces it)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** whether the artifact kind a `kb_context_ref` names can actually exist.
- **De-facto owners:**
  - `src/film_pipeline/artifacts/registry.py:185` — the row, inside the default kind table — `"\"kb_context_packet\": _spec(\"kb_context_packet\"),"`
  - `src/film_pipeline/schemas/_base.py:66` — the declared type member — `"KB_CONTEXT_PACKET = \"kb_context_packet\""`
  - `src/film_pipeline/kb/packets.py:107-119` — the object that would be persisted, returned but never stored — `"return KBContextPacket("`
- **Drift proof (latent, structural):** `grep -rn "kb_context_packet" --include=*.py src/ tests/`
  returns exactly three things: the registry row (`registry.py:185`), the `ArtifactType` member
  (`schemas/_base.py:66`), and `tests/unit/test_schemas.py:645`
  (`test_kb_context_packet_excluded_refs`, which builds the *schema* object, not the registered
  kind). No `save`/`save_mutable` call anywhere produces one, and `KBContextPacket` is not even
  bound as the row's `payload_model` (`_spec` is called with no keyword arguments). Mutation
  scenario: fix F-KBCTX-01 so a real packet is built and stamped; the `kb_context_ref` still
  resolves to nothing, because nothing ever writes the kind it names. No test fails — no test
  round-trips a `kb_context_packet` through the store.
- **Reproduce:**
  ```bash
  grep -rn "kb_context_packet" --include=*.py src/ tests/
  grep -rn "KBContextPacket" --include=*.py src/ | grep -i "save"
  ```
- **Blast radius:** `artifacts/registry.py`, `schemas/_base.py`, `kb/packets.py`, and every
  provenance audit that follows a `kb_context_ref`. F-KBCTX-01 observed that graph artifacts
  "point at a packet that does not exist"; this finding names the missing producer and the orphan
  registry row behind it.
- **Candidate owner module:** `kb-context` (producer) with `artifacts` (the kind row) — either
  persist the packet the builder already returns, or delete both the row and the enum member.
- **Extraction sketch:** in the (fixed) packet-build path, `save()` the packet under
  `kb_context_packet` bound to `payload_model=KBContextPacket`, so `kb_context_ref` resolves; or
  remove the registry row and the `ArtifactType` member. Guard test: every `ArtifactType` member
  has at least one construction/write site in `src/` (fails today for `kb_context_packet`).
- **Prior art:** new (verifier-found; the prior audit noted the dangling ref but not the orphan
  kind).

### F-KBCTX-13 — `_ARTIFACT_TYPE_BY_CLASS` is a second normative type model that disagrees with the writers it infers for

- **Class:** O1 (duplicated normative model)
- **Severity:** High (impact 3 × drift 4 = 12) — confirmed with fix during the second verification round (`reviews/verify-20.md`)
- **Concern:** what `artifact_type` an artifact receives when the caller omits it.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/_context.py:300-312` — the inference map — `"_ARTIFACT_TYPE_BY_CLASS: dict[str, str] = {"`, with `:308` `"\"MasterFilmMatrix\": \"shot_bible\","`
  - `src/film_pipeline/graph/nodes/_context.py:315-321` — the fallback that hides the gap — `"return _ArtifactType(_ARTIFACT_TYPE_BY_CLASS.get(class_name, \"script\"))"` … `"except ValueError:"` / `"return _ArtifactType.SCRIPT"`
  - `src/film_pipeline/graph/nodes/visual.py:119` — a writer relying on inference, typed wrong — `"brief_ref = _save_artifact(new_state, brief, \"execution_brief\", \"shot_bible\")"` (no `artifact_type=`, so `ExecutionBrief` → the `"script"` default)
  - `src/film_pipeline/mcp/tools/bibles/shot.py:199` — the same payload typed explicitly, and differently — `store, project_id, "master_film_matrix", ArtifactType.MASTER_FILM_MATRIX, matrix`
- **Drift proof (existing divergence):** `MasterFilmMatrix` appears in the map only as
  `"shot_bible"` (`:308`), whereas the explicit writer uses `ArtifactType.MASTER_FILM_MATRIX`
  (`shot.py:199`), so one payload class can be persisted as `shot_bible` or `master_film_matrix`
  depending on which surface saved it. `ExecutionBrief` has no entry at all, so `visual.py:119`
  falls through to `"script"` — the map printed by the first `Reproduce` command below contains no
  `ExecutionBrief` key; the first revision's parenthetical runtime output
  (`shot_bible execution_brief type=script`) recorded no command and is dropped. The mismatch is
  externally visible, not internal:
  `artifact_type` is written into the envelope (`store.py:148`), rendered into `current.md`
  (`store.py:758` `"f\"- type: {meta.artifact_type.value}\","`) and returned by MCP listings
  (`mcp/tools/artifacts.py:40`, `mcp/tools/projects.py:260`). Mutation scenario: add a new payload
  class and a graph save that omits `artifact_type=`; it is silently typed `script` and no test
  fails — nothing asserts the inferred type for classes absent from this map, and the registry's
  `KindSpec` (`artifacts/registry.py:70-81`) carries no `artifact_type` field to check against
  (only `artifact_id`, `kind`, `schema_version`, `payload_model`, `mutable`, `renderer`).
  **Shared fix:** this is the `artifact_type` half of the same `MasterFilmMatrix` identity decision
  as F-KBCTX-11 (artifact **id**): both bindings belong in the registry, so schedule one job.
- **Reproduce:**
  ```bash
  sed -n '300,312p' src/film_pipeline/graph/nodes/_context.py
  grep -n "artifact_type" src/film_pipeline/graph/nodes/visual.py
  sed -n '148p;758p' src/film_pipeline/artifacts/store.py
  ```
- **Blast radius:** `graph/nodes/_context.py` and the 15 of 19 `_save_artifact` sites that omit
  `artifact_type` (four pass it explicitly: `generation.py:98`, `qc.py:88`,
  `_repair_loop.py:175`, `visual.py:546`). User-visible: `execution_brief` is listed as type
  `script`, and a `MasterFilmMatrix` payload reports `shot_bible` or `master_film_matrix`
  depending on its producer — type-based filtering and review surfaces see inconsistent metadata
  for the same content.
- **Candidate owner module:** `artifacts` (the registry already binds `payload_model` per kind) as
  the single class→type model, with `_ARTIFACT_TYPE_BY_CLASS` deleted.
- **Extraction sketch:** require `artifact_type` on `_save_artifact`, or derive it from the
  registry by binding each `KindSpec.payload_model` to its `ArtifactType`, and delete the map and
  its `"script"` fallback. Guard test: every `_save_artifact` call passes an explicit type, and the
  inferred type for each registered `payload_model` equals the registry's declared type.
- **Prior art:** new (verifier-found).

---

## Added post-verification (corrected by `reviews/verify-17.md`)

F-KBCTX-14 was opened by the adversarial coverage pass to close the A6 record gap recorded in
`01-ownership-map.md` §9 ("Compression / bounding", no finding id). Its anchors were re-read at
`fb85baa` by this author and then independently re-checked by `reviews/verify-17.md`, which returned
**CORRECTED**: the seam and every command reproduce, but the first revision's novelty claim was
false (audit 03 F-CFG-15 already owned the gate-and-MCP half) and its scope is reduced to the
producer budgets below.

### F-KBCTX-14 — The prompt-character budget is re-chosen independently by `kb`, `graph`, `mcp` and the retry ladder; no guard detects a changed cap

- **Class:** O5 (policy-by-branch) + O1 (the same budget constant is re-declared per module)
- **Severity:** High (impact 3 × drift 4 = 12) — retained after de-duplication: the producer budget still spans `kb` (`compression.py:10-11`), `graph` (six `_context.py` slices), `mcp` (three bible producers) and the retry ladder (`runner.py:240,281`), so the §1.3 multi-module test holds. The verifier's strict-de-duplication alternative (Medium 2×4 = 8, verifier §Severity) is noted and rejected: the producer concern is split from the gate, not eliminated.
- **Concern:** how many characters of an artifact may reach a model prompt.
- **De-facto owners:**
  - `src/film_pipeline/kb/compression.py:10` — the intended single artifact budget, consumed only by the graph — `"DEFAULT_MAX_CONTEXT_CHARS = 6000"`
  - `src/film_pipeline/kb/compression.py:11` + `:64-65` — a **floor** on that budget, not a second cap — recorded here only to keep the coverage pass's "256" out of the cap set — `"MIN_COMPRESSED_CONTEXT_CHARS = 256"` / `"return max(MIN_COMPRESSED_CONTEXT_CHARS, int(max_chars))"`
  - `src/film_pipeline/graph/nodes/_context.py:376` (budget source `:451-465`; env override `config/runtime_overrides.py:19`) — the one path that consults `kb` and the resolved config — `"return compact_json_context(data, max_chars=_artifact_context_max_chars(state))"`
  - `src/film_pipeline/graph/nodes/_context.py:110,189,215,217,241,243` — six ad-hoc slices that bypass that budget and write prompt text directly — `"f\"visual_language: {str(data.get('visual_language', ''))[:200]}\""` / `"dramatic_function = str(scene.get(\"dramatic_function\", \"\"))[:80]"` / `"lines.append(f\"  {key}: {val[:150]}\")"` / `"lines.append(f\"  {key}: {', '.join(str(x)[:60] for x in val[:3])}\")"` / `"text = \"\n\".join(str(w)[:200] for w in (warnings if isinstance(warnings, list) else []))"` / `"return text[:800] + \"...\""`
  - `src/film_pipeline/mcp/tools/bibles/character.py:39` and `environment.py:40` — a hardcoded budget that never consults `kb` or the resolved config *(first enumerated by audit 03 F-CFG-15; the producer half of that finding now rests here — see Prior art)* — `"{script_text[:8000]}"`
  - `src/film_pipeline/mcp/tools/bibles/shot.py:184` — a third number inside the same package *(same provenance as the pair above)* — `"f\"Script:\n{script_text[:6000]}\n\n\""`
  - `src/film_pipeline/providers/failure_classifier.py:214` and `src/film_pipeline/agents/runner.py:240,281` — a multiplicative shrink of the already-assembled prompt — `"def compress_prompt_for_retry(prompt_text: str, *, factor: float = 0.6) -> str:"` / `"compress_prompt_for_retry(rendered_prompt, factor=0.6)"` / `"compress_prompt_for_retry(rendered_prompt, factor=0.35)"`
- **Drift proof (existing divergence + mutation):** the same `script` artifact already reaches
  two prompts under independently chosen budgets and truncation *algorithms*. The graph path
  compacts upstream content through `compact_json_context` at the `kb` default (6000) or a
  resolved-config override (`_context.py:376`), keeping a JSON-aware head 2/3 + tail 1/3 plus an
  identifier header (`kb/compression.py:57-61`); the MCP bible path keeps a blunt first-8000-chars
  prefix (`character.py:39`, `environment.py:40`) and the matrix path a first-6000-chars prefix
  (`shot.py:184`), and neither consults `kb` nor `context.max_chars_per_artifact`. A maintainer
  raising the graph budget via `FILM_PIPELINE_MAX_CONTEXT_CHARS` therefore cannot raise the MCP
  bible budget, and vice versa. **Mutation scenario (silent failure):** change
  `character.py:39`'s `[:8000]` to `[:2000]` (or `DEFAULT_MAX_CONTEXT_CHARS` from 6000 to 12000);
  the affected prompt is silently shortened or lengthened. `compact_json_context` never raises —
  it clamps to ≥256 and always returns a string ≤ its limit (`compression.py:61`, `:65`) — and a
  blunt slice can never raise — so the run continues and the model answers from less (or more)
  context. No test fails: no test asserts any producer budget (the only cap literals in `tests/`
  are explicit `max_chars=1000`/`900` at `tests/unit/kb/test_compression.py:11,29`, a 9000-char
  fixture at `tests/unit/validation/test_impl_validators.py:456`, and `FILM_PIPELINE_MAX_CONTEXT_CHARS="8000"`
  at `tests/unit/test_config.py:152`), and the MCP bible suite asserts output truthiness only
  (`tests/unit/mcp/tools/test_bibles.py:246` `assert result[\"locked_prompt_block\"]`). The one
  guard that watches prompt size — `PromptReadinessValidator`
  (`validation/impl/prompt_readiness.py:15`, `:83`, blocking code `prompt_too_long`) — is a
  *ceiling* (>8000 only), is pinned by that single 9000-char fixture, and runs only over
  `prompt_package`/`execution_brief` artifacts on the graph QC path
  (`graph/nodes/qc.py:304-308`), never over the inline MCP bible prompts. That gate is audit 03
  **F-CFG-15**'s concern, not this finding's — the two cross-reference each other (see Prior art).
  A lowered cap can therefore never trip a guard: the failure mode is a truncated prompt, never an
  error.
  *Corrections to the coverage pass's cap list:* the three `agents/impl/*[:2000]` sites
  (`constitution_agent.py:67`, `development_agent.py:86`, `screenwriter_agent.py:62`) are
  `except ValidationError` **log** truncations of invalid model output, not prompt bounds, so
  `agents` does not independently choose prompt size through them; and 256 in
  `kb/compression.py:11` is a floor, not a competing cap. The pass also missed
  `_context.py:110`, `_context.py:243`, and the two retry factors at `runner.py:240,281`.
- **Reproduce:**
  ```bash
  grep -rn "DEFAULT_MAX_CONTEXT_CHARS = \|MIN_COMPRESSED_CONTEXT_CHARS = " src/film_pipeline/kb/compression.py
  grep -rn "\[:8000\]\|\[:6000\]\|\[:200\]\|\[:150\]\|\[:80\]\|\[:60\]\|\[:800\]" --include=*.py src/film_pipeline/mcp/tools/bibles/ src/film_pipeline/graph/nodes/_context.py
  grep -rn "def compress_prompt_for_retry\|compress_prompt_for_retry(rendered_prompt" --include=*.py src/film_pipeline/providers/failure_classifier.py src/film_pipeline/agents/runner.py
  grep -rn "MAX_PROMPT_LENGTH" --include=*.py src/film_pipeline/validation/impl/prompt_readiness.py
  ```
- **Blast radius:** `kb/compression.py`, `graph/nodes/_context.py`,
  `mcp/tools/bibles/{character,environment,shot}.py`, `agents/runner.py`,
  `providers/failure_classifier.py`, `config/runtime_overrides.py`. User-visible: one artifact
  reaches different prompts at different lengths and with different truncation algorithms, and no
  surface reports which budget applied. Prior art already records the quality consequence:
  `documentation/reviews/prep-production-quality-review.md:141-144`.
- **Candidate owner module:** `kb` — one `PromptBudget` value object in `kb/compression.py` that
  every prompt-assembly path consumes; `03-target-architecture.md:510` already lists `compress`
  in the `kb` public contract, and `01-ownership-map.md:231-232` nominates `kb` for this concern.
- **Extraction sketch:** move each literal into one `PromptBudget` (`artifact_body=6000`,
  `script_preview=8000`, retry factors, per-field slices) or delete the ad-hoc slices in favour
  of `compact_json_context`; thread the resolved config budget into the MCP bible tools, which
  today never see `resolved_config`. Guard test: assert no module outside `kb/compression.py`
  contains a `[:N]` prompt slice, and that one over-budget script produces the same emitted length
  through graph assembly (`_inject_artifact_context`) and MCP bible assembly (fails today:
  6000 ≠ 8000).
- **Prior art:** `docs/modular-architecture/audit/03-config-profile-and-defaults.md:759` (audit 03
  **F-CFG-15**) first named the three MCP bible slices (`character.py:39`, `environment.py:40`,
  `shot.py:184`), the readiness limit (`prompt_readiness.py:15,83`) and the 8000-vs-6000
  disagreement. The program-wide ownership split makes the two findings complementary rather than
  overlapping: **F-CFG-15 owns the readiness-gate policy and the `per_ten` spot-check; F-KBCTX-14
  owns the prompt-character budget across producers** — the MCP trio transfers here as the producer
  half, and F-CFG-15 keeps the gate. The retry-factor values are already prior art
  (`documentation/reviews/arch-lens-cognition.md:166-167`), and
  `failure_classifier.compress_prompt_for_retry` is declared single-owner with test pins in
  `docs/modular-architecture/audit/05-provider-runtime-and-health.md:1020-1023` (audit 05 §4.4) —
  this finding adds the per-branch values, not the function's ownership.
  `documentation/reviews/prep-production-quality-review.md:141-144` and
  `documentation/reviews/prep-production-implementation-plan.md:218-221` record the real quality
  consequence (compaction fidelity loss), and this audit's own prose at `:74-76` / `:727-729`
  anticipated a single `kb/compression.py` owner but filed it under F-KBCTX-06.
  **New here (novelty reduced after `reviews/verify-17.md`):** the `kb` budget as the intended
  single owner (`kb/compression.py:10-11`), its `FILM_PIPELINE_MAX_CONTEXT_CHARS` override
  (`config/runtime_overrides.py:19`), and the six unguarded ad-hoc `_context.py` slices
  (`:110,189,215,217,241,243`). *The first revision's claim that "no finding id existed" was
  false — F-CFG-15 already covered the gate-and-MCP half; only the A6 record gap in
  `01-ownership-map.md` was real.*
- **Provenance:** uncovered by the adversarial coverage pass (`reviews/adversarial-coverage.md` §H6); closes the A6 record gap recorded in `01-ownership-map.md` ("Compression / bounding", no finding id). The gate-and-MCP half was already recorded as audit 03 **F-CFG-15**, whose readiness-gate-ownership is complementary (cross-referenced above); this finding is the producer-budget half.

---

## Clean concerns (single-owner, already guarded)

| Concern | Owner | Guard / evidence |
|---|---|---|
| KB authority hierarchy and supersession ranking | `kb/conflicts.py:17-22` (`AUTHORITY_RANK`) | Single definition in `src/`: `grep -rn "AUTHORITY_RANK\|authority_rank" --include=*.py src/ | wc -l` = 5, all in `kb/conflicts.py`. Enforcement is local (`resolve_authority` `:77-110`, `resolve_superseded` `:51-75`). Guard test: `tests/unit/kb/test_conflicts.py`. No second implementation found in graph or agent code. |
| KB item metadata validation | `kb/manifest.py:22-32` (`from_yaml` constructs `KBItemMetadata` per row via `cls()` at `:28`) | Single parse/validate entry point; `grep -rn "KBManifest(" --include=*.py src/` returns nothing, so `from_yaml` is the only constructor. Guard test: `tests/unit/kb/test_manifest.py`. Consumers (`mcp/tools/kb.py:26`, `tests/e2e/conftest.py:101`) both call it. |
| Item activation filter (`status == "active"`) | `kb/manifest.py:57-58` (`active_only`) | The only status gate before retrieval (`retrieval.py:43`); no second status check in `src/` (`grep -rn "status == \"active\"" src/` → `manifest.py:58` only). Guard test: `tests/unit/kb/test_manifest.py`. |
| Artifact store as **the** writer of the persisted `kb_context_ref` column | `artifacts/store.py:157`, `:184`, `:251`, `:726`, `:747` | The store is the only module that writes these bytes; graph and MCP only supply `ArtifactMetadata`. Weakness: the column is optional and its default is null — recorded as F-KBCTX-03, not as a second writer. Guard test: `tests/unit/artifacts/test_store_v2.py:116-130`. |
| KB MCP tool registration | `mcp/tools/registry.py:289-292` | All four KB tools registered exactly once; `mcp/tools/__init__.py:88-91` re-exports the same four. No duplicate or shadow tool name found. Guard test: `tests/unit/mcp/tools/test_kb.py`. |

## Candidate module boundary

**`kb-context`** — owns "the governed KB slice for one agent task, and the provenance pointer to it".

- **Owns (N):** the `kbctx:` identifier grammar and its parser (F-KBCTX-02); the packet
  construction pipeline retrieval → authority resolution → exclusion → payload
  (`kb/packets.py`, `kb/retrieval.py`, `kb/conflicts.py`, minus F-KBCTX-10's dead output); the
  KB manifest location resolver (`kb/paths.py`, F-KBCTX-09).
- **Owns (I):** the single refusal path when no manifest exists (`mcp/tools/kb.py:36-41`,
  `services.py:119-134` currently duplicate the "no KB" branch), and the invariant that a
  persisted `kb_context_ref` resolves to a real packet.
- **Owns (R):** the KB provenance **value** — one constructor plus one renderer used by every
  prompt path (F-KBCTX-08) and every artifact writer (F-KBCTX-03/04/05).
- **Does not own:** artifact serialisation (`artifacts`), the graph state schema (`graph`),
  prompt templates (`agents`), MCP response envelopes (`mcp`), or context *size* policy, which
  should have one owner (`kb/compression.py`) with `_context.py`'s ad-hoc slices deleted
  (F-KBCTX-06).
- **Hardest dependency to break:** the graph state channel for the current run's KB ref
  (F-KBCTX-05) — either a real `ORCH_CHANNELS` row or an explicit argument threaded through
  `_save_artifact`; a silent `state.get(...)` fallback must not survive.
- **Deletion candidates once the boundary exists:** `graph/context_packets.py` +
  `_attach_scoped_packet` (F-KBCTX-06), `AgentRouteResult.kb_context_ref` +
  `_build_kb_context_ref` (F-KBCTX-02), `KBContextPacket.payload`/`excluded_refs` unless the
  MCP projection is widened (F-KBCTX-08/10), `KBRetrieval.examples` unless called (F-KBCTX-10),
  the `HandoffManager`/`PromptRunner.create_handoff` duplicates (unused by production), the
  duplicate matrix registry row (F-KBCTX-11), the `kb_context_packet` registry row +
  `ArtifactType` member unless a producer is added (F-KBCTX-12), and
  `_ARTIFACT_TYPE_BY_CLASS` with its `"script"` fallback (F-KBCTX-13).
- **Adjacent boundary (added after verification):** `artifacts/registry.py` must be the single
  owner of artifact-kind identity and of the payload-class → `ArtifactType` binding. Today
  `kb-context` mints `kb_context_ref` values whose target kind has no producer (F-KBCTX-12),
  and the graph infers types from a private map that disagrees with the registry and with the
  explicit writers (F-KBCTX-13). Whichever module owns the KB packet must also be able to
  persist it, which is a contract on `artifacts`, not a second registry inside `graph`.

## Unverified hypotheses and coverage gaps (not findings)

1. **`app/mock_responses.py` carries no synthetic KB data.** The cluster brief expected
   "synthetic KB data" there;
   `grep -in "kb\|knowledge\|playbook\|canonical" src/film_pipeline/app/mock_responses.py`
   returns nothing, and the file's own docstring describes only the demo film
   (`mock_responses.py:1-8`). The synthetic packet instead originates in the *code*
   (`graph/services.py:128-134`), which is F-KBCTX-01. No finding is drawn from the brief's
   premise.
2. **Runtime reachability of the post-production and checkpoint writers.** `post/*.py`,
   `mcp/tools/checkpoints.py`, `reference_generation/index_files.py` and `validation.py` are
   cited in F-KBCTX-03 as construction sites that omit the column; I verified the omission and
   the presence of a `store.save`/`save_mutable` call in each file, but I did not trace whether
   every one is reachable from a live entry point at HEAD. The omission itself is verified; the
   user-visible impact for each site is not independently measured.
3. **`tests/` guard coverage for the MCP bible provenance.** I read the MCP bible suites only by
   grep for `kb_context_ref` (zero hits) rather than in full, so I can state that no test
   *asserts* the column on MCP-written bibles, but I have not enumerated those tests' full
   subject matter.
