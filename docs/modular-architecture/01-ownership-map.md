# 01 — Current-State Ownership Map

> **Review status (2026-09-25): historical snapshot.** The audit corpus grew after
> this map's last measurement. Use [06](06-independent-review-and-decision.md)
> for the current decision, and verify each finding against source and its latest
> `verify-*` verdict before acting on it. The totals below describe the map's
> recorded revision, not the current verified corpus.

Synthesis of the 14 cluster audits in `audit/` into one concern-by-concern map of
**who currently owns what**. Severity, drift proofs and evidence live in
`02-duplication-ledger.md` and the underlying audit files; this document answers
only: *for each concern, is ownership single or distributed, and who are the
de-facto owners?*

Baseline: `fb85baa` (`modular-app`). `make ci-check` verified green at this
commit (2003 passed / 8 skipped, 91.58 % coverage, build + product gate OK) using
`UV_CACHE_DIR=$PWD/.uv-cache`.

### Corpus totals — measured, not asserted (bar A2 §1.6.4)

The corpus number has **one owner**: `02-duplication-ledger.md` §"Verification
outcomes". This map restates it only because bar A1 requires a coverage ledger, and
it restates it *with the command that produces it*. Both commands below were run at
this revision; run them and you get these numbers, or the line is wrong and must be
corrected.

```bash
cd docs/modular-architecture
grep -h '^- \*\*Severity:\*\*' audit/*.md | wc -l                       # 178
grep -h '^- \*\*Severity:\*\*' audit/*.md \
  | sed -E 's/^- \*\*Severity:\*\* *\**([A-Za-z]+).*/\1/' | sort | uniq -c
                                                                        # 39 Critical / 88 High / 50 Medium / 1 Low
grep -h '^- \*\*Class:\*\*' audit/*.md | grep -oE 'O[1-8]' | sort | uniq -c
                                                                        # O1 60 / O2 23 / O3 31 / O4 26 / O5 38 / O6 25 / O7 16 / O8 38
```

At this revision: **178 live findings — 39 Critical, 88 High, 50 Medium, 1 Low.**
Class distribution with the canonical command above (a Class bullet naming two
classes counts once per class, so these sum to more than 178): O1 duplicated
normative model 60, O5 policy-by-branch 38, O8 missing contract 38, O3 split state
authority 31, O4 parallel registries 26, O6 parallel lifecycle 25, O2 duplicated
invariant enforcement 23, O7 leaked internals 16.

Two counting conventions are load-bearing and are stated so the number is not
re-derivable three ways:

- **A withdrawn finding is not a live finding.** `F-TEST-02` keeps its heading in
  `audit/13` but carries no `- **Severity:**` bullet, so the grep above excludes it.
- **This map does not own a second class count.** An earlier revision printed a
  different class distribution (O1 57 / O5 33 / O8 32 / …) because it was measured
  over the ledger's *consolidated concerns* rather than over the audits' Class
  bullets. That variant is withdrawn: the ledger's per-concern class is a synthesis
  choice, the audit's Class bullet is evidence, and only the latter has a reproduce
  command. `reviews/adversarial-coverage.md` §H11 found the mismatch; this is the fix.

History of the corpus, for the reader who meets an older number: 148 (pre-verification)
→ 163 (V5) → 173 (after the per-audit verification fix loops) → **178** (after the
audit-10 fix loop promoted the verifier's five missed seams to findings
`F-CRP-12`…`F-CRP-16`). See `reviews/orchestrator-verification-notes.md` V5/V9 and
the per-audit table in `README.md`.

The concern-level rows below were unaffected by the additions: every added finding
folds into a concern already mapped here.

## How to read the status column

| Status | Meaning |
|---|---|
| **SINGLE** | One module satisfies normative model + invariant enforcement + representation authority. |
| **DISTRIBUTED** | Two or more modules independently satisfy part of N/I/R; a partial change can pass CI. |
| **DIVERGENT** | Distributed **and** the owners already disagree at HEAD (an executed, reproducible divergence — not a mutation scenario). |
| **CLEAN** | Audited and found single-owner; no finding raised. |

---

## 1. Phase model and lifecycle

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| Phase vocabulary and order (11 phases) | `schemas/_base.FilmPhase`; `graph/_action_routing.PHASE_ORDER`; `graph/graph._PHASE_TO_NODE`; `graph/nodes/_repair_loop._PHASE_NODES`; `graph/_action_routing.APPROVAL_GATES`; `graph/graph._APPROVAL_DESTINATIONS`; `artifacts/paths.PHASE_DIR_MAP`; `constraints/_keywords._PHASE_KEYWORDS`; `graph/_agent_routing._PHASE_DEFAULT_AGENTS`; 2 phase-class sets | **DISTRIBUTED** — 11 independent definitions in 8 modules; keys agree today, nothing tests it | F-PHASE-02, F-PHASE-05 |
| Phase → approval gate | `APPROVAL_GATES` **and** 11 per-node `gate=` literals **and** an inline copy in `graph/subgraphs/qc.py` | **DISTRIBUTED** | F-PHASE-03 |
| Phase advancement (approve → next phase) | `graph/_action_routing.compute_actions` vs `app/_graph_exec.advance_to_next_phase` | **DIVERGENT** — app/MCP path skips the provider-blocked-generation gate; reachable from MCP `approve_phase` | F-PHASE-01 |
| Successor-phase function | two implementations inside `graph` | **DISTRIBUTED** | F-PHASE-04 |
| Router action vocabulary ↔ graph edge table | router emits `escalate_to_failure_handler`; no edge table declares it (routed by fallback only) | **DISTRIBUTED** | F-PHASE-06 |
| Phase-keyed policy literals outside the vocabulary (rollback regeneration, constraint extraction) | `checkpoints/rollback.py`, `constraints/*`, others | **DISTRIBUTED** | F-PHASE-09 |
| Partial phase registries | `context_packets.PHASE_BUILDERS` (7 of 11), others — silent fallback | **DISTRIBUTED** | F-PHASE-08 |
| Gate mode (human vs auto/headless) | re-derived in `graph` and `app` from `resolved_config` | **DISTRIBUTED** | F-PHASE-07, F-OST-10 |
| Phase → validator dispatch | 3–4 tables: `graph/nodes/qc._VALIDATOR_RUNNERS`, `graph/subgraphs/qc._VALIDATOR_MAP`, `mcp/tools/validation`, `mcp/tools/validation.py` | **DISTRIBUTED** | F-PHASE-10, F-VR-07, F-MCP-04 |

**Candidate owner:** one `phase-model` catalog owning the vocabulary, order,
directory names, successor, gate membership, and the action↔edge correspondence;
everything else imports it.

## 2. Orchestration state and routing

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| Orchestrator channel-key set | constants tuple vs `TypedDict`; parity one-directional | **DISTRIBUTED** | F-OST-01 |
| `issues` channel contract + blocking predicate | no typed contract; predicate re-derived at 18 sites | **DISTRIBUTED** | F-OST-03 |
| "Cannot approve with blocking issues" veto | 4 implementations, 2 different scopes | **DISTRIBUTED** | F-OST-05 |
| "Stalled phase" | 2 representations, 3 thresholds | **DISTRIBUTED** | F-OST-02 |
| Consensus report as a routing input | router reads `state["consensus_report"]`, which **no production writer produces** and the schema does not declare | **DIVERGENT** | F-OST-06, F-VR-05 |
| QC lifecycle | subgraph (compiled graph) vs sequential node (repair loop, app) | **DIVERGENT** | F-OST-07, F-VR-03, F-MCP-04 |
| Graph channel reducers | `app._graph_exec.run_phase_node` re-implements and diverges | **DISTRIBUTED** | F-OST-08 |
| Provider health (routing input) | 4 representations, 3 writers; the checkpointed one has **no producer** | **DIVERGENT** | F-OST-13, F-PROV-01 |
| Budget state (routing input) | 2 state keys; prompt reader uses the unwritten one | **DISTRIBUTED** | F-OST-12, F-BUD-01/04 |
| Failure decisions | typed producer, untyped dict channel, no bridge; `FailureDecision` never constructed | **DIVERGENT** | F-OST-14, F-POST-02, F-PROV-02 |
| `next_action` → operator prose | re-derived in 2 modules | **DISTRIBUTED** | F-OST-09 |
| Orchestrator key literals / `_orchestrator__` prefix grammar | re-derived by 3 constructors | **DISTRIBUTED** | F-OST-11 |
| Gate label (human gate name) | 2 independent maps | **DISTRIBUTED** | F-OST-04 |
| Phase-keyed registries (7) | no agreement check | **DISTRIBUTED** | F-OST-15 |
| QC validator → matrix-patch handoff | undeclared, untyped `_pending_row_updates` key: written and popped inside one `qc_node` call, dropped on the app path, in no schema/registry | **DISTRIBUTED** — missing contract; no test names the key | F-OST-18 |

**Candidate owner:** an `orchestration` module that owns the state model
(channels, types, reducers) and the routing policy; state writers become
read-only consumers.

## 3. Configuration, profiles, defaults

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| Agent → model-profile map | `graph/nodes/_context._AGENT_PROFILE_MAP` vs `agents/mvp/__init__.py` | **DIVERGENT** — 2 agents differ; the test encodes the wrong values | F-CFG-02, F-AGENT-01 |
| Model-profile defaults | `profiles/base.studio.yaml` vs `agents/model_routing._FALLBACK_PROFILES` (byte-identical today); `GraphServices` builds `ModelRouter()` with no profiles | **DIVERGENT (latent)** — editing the YAML changes nothing | F-CFG-01 |
| Validator registries | `validation/validators/__init__.py` (15, unused) vs per-class entries in `validation/impl/*` (executed) | **DIVERGENT** — `scene-writing-validator` conditions differ; one validator impl-only | F-CFG-03, F-VR-01, F-AGENT-08 |
| Score → status band grammar | class default 85/75/65 vs 22 call-site literals (18 at 85/75/75, 3 at 80/70/70, 1 at 90/80/80), all 22 with `block_below == review_at`; `[block_below, review_at)` empty → `NEEDS_REVISION` unreachable | **DIVERGENT** | F-CFG-04, F-VR-02 |
| Provider-lineup parsing | `config/validator.py` understands 1 of 2 profile shapes | **DIVERGENT** — an all-mock stack yields no blocking conflict | F-CFG-05 |
| Budget cap | 4 spellings; profile cap never reaches `BudgetState` | **DISTRIBUTED** | F-CFG-06, F-BUD-01 |
| Profile-stack key set | defined 3 times; 3 writers disagree on env override | **DISTRIBUTED** | F-CFG-07, F-CFG-09 |
| `resolved_review_strategy` | read from resolved config, no writer, no profile key | **DIVERGENT** | F-CFG-10 |
| Provider credential resolution policy | CWD-relative; 14 call sites; re-keyed per provider | **DIVERGENT** | F-PROV-04, F-CFG-11 |
| `profiles/` location | resolved twice from the process CWD | **DISTRIBUTED** | F-CFG-12 |
| `FILM_PIPELINE_NO_PERSIST` | 7 readers across 6 modules | **DISTRIBUTED** | F-CFG-08, F-CRP-09 |
| Hardcoded numeric defaults duplicating profile values | multiple sites; prior-art "300" fallback now 3 sites (worse) | **DISTRIBUTED** | F-CFG-13 |
| Pacing vocabulary and its two alias tables | `schemas/constraints.pacing_style` (`Literal`), plain `str` consts in `graph/scope_contract.py`, `_PACING_ALIASES` vs `constraints/_keywords._PACING_KEYWORDS` (partly disjoint), unvalidated `schemas/execution_brief.pacing_style` | **DIVERGENT** — `"slow cinema"` maps to `slow_cinema` in one table and `standard` in the other | F-CFG-14, F-ARTIFACT-14 |

**Candidate owner:** `config` owns resolution order, profile loading/merging,
defaults, and the env-var contract; runtime modules receive resolved values, not
raw environment.

## 4. Agents, prompts, registries

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| Agent roster | `agents/mvp/__init__.py`, `agents/impl/registry.py`, `agents/registry.py`, `schemas/registries/agent_registry.py`, prompt registry, `_PHASE_DEFAULT_AGENTS`, `_AGENT_PROFILE_MAP` | **DIVERGENT** — orphan ids, a duplicate schema, no reverse roster guard | F-AGENT-10, F-AGENT-03 |
| Role / output-artifact contract per agent | declared contract vs registered implementation | **DIVERGENT** | F-AGENT-02 |
| `failure-handling-agent` identity | 5 registries disagree about what it is | **DIVERGENT** | F-POST-02 |
| Prompt registry | keyed from two different id spaces; 6 of 7 validator templates unused | **DISTRIBUTED** | F-AGENT-05 |
| Prompt rendering | 4 renderers; live validator renderer duplicates the template renderer | **DISTRIBUTED** | F-AGENT-06 |
| Agent execution lifecycle | graph `PromptRunner` path vs MCP bible path (locally built contracts, inline prompts) | **DIVERGENT** | F-AGENT-04, F-KBCTX-07, F-MCP-12 |
| Agent naming → KB manifest/defaults | drift silently starves agents of KB items | **DISTRIBUTED** | F-AGENT-09 |
| Validator contracts | 3 places; runtime `ValidatorRegistry` never populated | **DISTRIBUTED** | F-AGENT-08, F-VR-01 |
| Agent KB-context id | built in `graph/_agent_routing`, read nowhere; 3 id grammars | **DIVERGENT** | F-KBCTX-02, F-KBCTX-05 |
| Agent capability vocabulary | `graph/_agent_routing._REVIEW_CAPABILITIES`/`_REPAIR_CAPABILITIES` (8 tokens) vs the 30 capabilities `agents/mvp` declares: **zero** intersection; the argument that reads them is passed by no caller in `src/` or `tests/` | **DISTRIBUTED** — dead policy a future caller would trust | F-AGENT-13 |

**Candidate owner:** an `agents` module owning the roster/contract, prompt
registry, and the single execution lifecycle; MCP must route through it.

## 5. Providers, credentials, cost inputs

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| Provider health state | runtime dict, `providers/health.py`, `schemas/provider_health.py`, `graph/orchestrator_state.update_provider_health` (dormant) | **DIVERGENT** — routing reads the dormant one | F-PROV-01, F-OST-13 |
| Provider registry | 2 same-named classes, neither production; real one is `StudioRuntime.provider_adapters` with silent overwrite | **DIVERGENT** | F-PROV-03 |
| Failure classification | `providers/failure_classifier.py` has **zero** production callers; 5 ad-hoc code vocabularies | **DIVERGENT** | F-PROV-02 |
| Credential access policy | 14 call sites; CWD-relative; per-provider re-key; caching differs | **DIVERGENT** | F-PROV-04 |
| Provider catalog / capabilities | re-declared in 5 modules; `ProviderCapabilities` written, never read | **DISTRIBUTED** | F-PROV-05 |
| Provider job status → generation status | mapped twice (enum vs raw literal) | **DISTRIBUTED** | F-PROV-06, F-GEN-04 |
| Provider poll wait budget | `POLLING_CONFIG` declares 4 keys; 3 have zero readers everywhere; neither poll path enforces a deadline | **DISTRIBUTED** — declared policy, no authority | F-PROV-09 |
| Prompt-character budget | `kb` 6000 floor/cap, `mcp` 8000/8000/6000 blunt slices, `graph` ad-hoc `[:80]`…`[:800]`, retry factors 0.6/0.35, gate 8000 vs truncation 6000 | **DIVERGENT** — the gate admits what the truncator cuts | F-KBCTX-14, F-CFG-15 |

**Candidate owner:** `providers` owns the catalog, credentials, health, failure
classification, and the job-status mapping.

## 6. Generation runtime

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| MCP submit payload | `prompt_ref` (a reference string) passed where prompt text is expected | **DIVERGENT (defect)** | F-GEN-01 |
| MCP poll lifecycle | marks row COMPLETED without downloading media or recording the manifest | **DIVERGENT (defect)** | F-GEN-02 |
| Prompt assembly for a shot | graph path vs generation/MCP path, different fallbacks | **DIVERGENT** | F-GEN-03 |
| Ledger row state machine | 2 writers with different transition rules | **DIVERGENT** | F-GEN-04, F-ARTIFACT-07 |
| Media path construction | canonical helper dead + import-banned; `ProjectStorage.media_dir` plus 6 re-derivations | **DISTRIBUTED** | F-GEN-07, F-GEN-08 |
| Reference-asset catalog | a second, parallel catalog | **DISTRIBUTED** | F-GEN-08 |
| Cost model | 2 independent models compared by the budget gate; shot-duration default re-derived | **DISTRIBUTED** | F-GEN-10, F-BUD-01/03 |
| Generation-request identity | 2 dedup keys | **DISTRIBUTED** | F-GEN-11, F-CRP-10 |
| "Which files count as generated media" | name denylist in delivery vs other rules | **DISTRIBUTED** | F-GEN-12 |
| Shot-matrix row state | graph marks rows `generated` at planning time | **DIVERGENT** | F-GEN-05 |
| Generation status enum coverage | 10 members, writers use 6; a second untyped reference-generation status | **DISTRIBUTED** | F-GEN-06 |

**Candidate owner:** `generation` owns job lifecycle, ledger state machine,
prompt resolution, and media naming.

## 7. Artifacts: refs, kinds, versions, status

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| Ref grammar | one parser (`ArtifactRef.from_string`, 10 call sites) but a **second formatter** (`review/diff._id_stem`) and charset/family rules split into the registry | **DISTRIBUTED** | F-ARTIFACT-01 |
| Artifact kind → type | `artifacts/registry.py` (47 ids) vs `schemas._base.ArtifactType` (45) vs `graph/nodes/_context._ARTIFACT_TYPE_BY_CLASS` (silent fallback to `script`; 2 entries are values the enum rejects) | **DIVERGENT** — 8 registry-only / 6 enum-only; data already written with `artifact_type=script` | F-ARTIFACT-02, F-ARTIFACT-08 |
| Version on write | store owns numbering, but 5 sites hardcode `version=1` and 4 re-derive "latest+1"; all discarded | **DISTRIBUTED** | F-ARTIFACT-03 |
| `schema_version` semantics | overloaded across 8 axes | **DISTRIBUTED** | F-ARTIFACT-04 |
| Schema-too-new / checksum enforcement | only `_read_checked_envelope`; mutable/metadata/list paths bypass | **DISTRIBUTED (gap)** | F-ARTIFACT-05 |
| Artifact status lifecycle | store owns it, but `save_mutable` cannot express APPROVED, `save()` pre-approves, `REJECTED`/`ARCHIVED` unreachable | **DISTRIBUTED** | F-ARTIFACT-06 |
| Kind catalog on read | `KindNotRegisteredError` on write, fabricated spec on read | **DIVERGENT** | F-ARTIFACT-09 |
| Closed-vocabulary schema fields | one field is a `Literal`/`StrEnum` in one model and a bare `str` in a sibling model: `pacing_style`, `film_type`, `phase`, `next_action`, `mode` (5 fields, 24 declarations) | **DISTRIBUTED** — validated at one declaration, accepts anything at the other | F-ARTIFACT-14 |
| Layout, root, atomic writes, paths | `artifacts` (`ProjectStorage`) | **SINGLE** — guarded by `tests/unit/artifacts/test_storage_boundary.py` | — |

**Candidate owner:** `artifacts.contract` for kind/ref/version/status
derivation — *enforcement and derivation only*; the storage owner keeps layout,
root, atomic writes and the catalog (see `reconciliation-notes.md` R3).

## 8. Validation and review

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| Validator registration | 4 definition paths (2 dead); `register_validator` does not exist | **DISTRIBUTED** | F-VR-01, F-CFG-03, F-AGENT-08 |
| Score → status, `NEEDS_REVISION` | thresholds collapse the review band in every entry (22/22 literals have `block_below == review_at`), so **no validator can produce it** and the router's `revise` tier is dead; the QC synthesis agent *can* mint it from LLM JSON and it is rendered to a human-viewable artifact, so it is not unreachable end-to-end — just unreachable by the validation contract | **DIVERGENT** | F-VR-02, F-CFG-04 |
| QC lifecycle | forward graph uses the subgraph; repair/app paths use the sequential node, with different validator sets and side effects | **DIVERGENT** | F-VR-03, F-OST-07 |
| Consensus | `ConsensusBuilder` receives serialized dicts; `AttributeError` swallowed → algorithmic consensus never runs | **DIVERGENT (defect)** | F-VR-04 |
| Consensus state ref | 2 writers in one node run | **DISTRIBUTED** | F-VR-05, F-OST-06 |
| Approve-vs-revise gate decision | 6 sites, including a test that replicates the policy | **DISTRIBUTED** | F-VR-06 |
| Phase → validator dispatch | 4 tables, no agreement proof | **DISTRIBUTED** | F-VR-07, F-PHASE-10, F-MCP-04 |
| Finding severity / blocking rules | `blocking_conditions`/`warning_conditions` inert; rules re-derived inline | **DIVERGENT** | F-VR-08 |
| Review package | typed only on the MCP path; the LangGraph path produces a different shape | **DISTRIBUTED** | F-VR-09, F-VR-11 |
| Gate action vocabulary | bypasses its own typed contract | **DISTRIBUTED** | F-VR-10 |
| Multi-model review | `review/` package | **SINGLE** (no finding) | — |

**Candidate owner:** `validation` owns the registry, thresholds/status law,
dispatch, and consensus; `governance` (proposed) owns the gate decision.

## 9. Knowledge base and provenance

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| KB context packet in production | `KBContextPacketBuilder` never wired; graph uses a synthetic empty packet | **DIVERGENT (defect)** | F-KBCTX-01, F-KBCTX-08 |
| Context-building system | 4: `kb.packets` (unwired), `graph/context_packets.py` (dead), `graph/nodes/_context.py` (live), MCP bibles (hand-rolled) | **DISTRIBUTED** | F-KBCTX-06, F-KBCTX-07 |
| `kb_context_ref` provenance | 1 of 12 artifact-write paths sets it; mutable write drops it from `meta.json`; node-local state key not a channel | **DIVERGENT** | F-KBCTX-03, F-KBCTX-04, F-KBCTX-05 |
| `kbctx:` id grammar | 3 incompatible minters | **DISTRIBUTED** | F-KBCTX-02 |
| KB root | resolved in 3 modules | **DISTRIBUTED** | F-KBCTX-09 |
| Packet governance output | no consumer | **DISTRIBUTED** | F-KBCTX-10 |
| Conflict detection | `kb/conflicts.py` | **SINGLE** — clean | — |
| Compression / bounding | no single owner (3 sites + ad-hoc slices) | **DISTRIBUTED** | F-KBCTX-14 |

**Candidate owner:** `kb` owns retrieval, packets, compression, conflicts, ids,
and KB provenance stamping.

## 10. Checkpoints, resume, runtime persistence

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| Run / runtime / storage / checkpoint roots | 5 independent resolution paths that do not coincide | **DIVERGENT** | F-CRP-01 |
| Checkpoint metadata registry | 2 in-memory registries; rollback validates against one | **DISTRIBUTED** | F-CRP-02 |
| Resume seam (app ↔ graph) | stringly typed, no shared contract | **DISTRIBUTED** | F-CRP-03 |
| `CheckpointMetadata.artifact_versions` | 2 writers, different rules | **DISTRIBUTED** | F-CRP-04 |
| Resume implementation | 2 plus a write-only crash-recovery snapshot | **DISTRIBUTED** | F-CRP-05 |
| Rollback record | 2 authorities, no audit event | **DISTRIBUTED** | F-CRP-06 |
| Invalidation dependency model | hand-maintained map vs real artifact parentage | **DIVERGENT** | F-CRP-07 |
| Discovered (artifact-only) projects | get a checkpoint manager but never restore | **DISTRIBUTED** | F-CRP-08 |
| "Persistence enabled?" | 6 sites, 2 formulas | **DISTRIBUTED** | F-CRP-09, F-CFG-08 |
| Stale generation-request code set | 3 definitions + 1 emission | **DISTRIBUTED** | F-CRP-10, F-GEN-11 |

**Candidate owner:** `projects` (project catalog + runtime persistence policy) and
`checkpoints` (checkpoint/rollback/resume state).

## 11. MCP surface, safety, entry points

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| Tool invocation lifecycle | 4 implementations; only the stdio transport applies the confirmation gate | **DIVERGENT** | F-MCP-02 |
| Tool argument contracts | declared and never populated; every tool advertises `inputSchema: {}` | **DIVERGENT (defect)** | F-MCP-03 |
| Confirmation enforcement | `server.py` vs `checkpoints.py`, divergent response contracts; one tool documents a check it never performs | **DISTRIBUTED** | F-MCP-01 |
| `OperatorService` vs MCP | parallel lifecycle; mutations bypass confirmation (incl. a real-money spend path); `project_kind` set in one place makes deletion safety path-dependent | **DIVERGENT** | F-MCP-04/05/06 |
| Project registry | 2 registries, no agreement check | **DISTRIBUTED** | F-MCP-07 |
| Dangerous-mutation policy | no owner; provider-blocked vs other guards | **DISTRIBUTED** | F-MCP-11 |
| Entry-point bootstrap | 3 mains + `langgraph.json` each re-derive bootstrap/persistence; `cli.run.main` never validates env | **DISTRIBUTED** | F-MCP-09 |
| Error taxonomy | tool failures bypass `MCPErrorCode` | **DISTRIBUTED** | F-MCP-10 |
| Contract flags | registration is the single source of truth (`registry.py` only) | **SINGLE** — clean | — |
| Agent/artifact creation outside the graph | bible/assembly/reference tools instantiate agents and version artifacts | **DIVERGENT** | F-MCP-12, F-AGENT-04 |

**Candidate owner:** `mcp.policy` (contract + one `authorize` gate + typed errors
+ argument models) and one `bootstrap(role)` in `app`.

## 12. Post-production, delivery, constraints, budget

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| `AssemblyAgent` | two classes with disjoint output contracts and two invocation lifecycles | **DIVERGENT** | F-POST-01, F-POST-03 |
| "What makes delivery complete" | `post/delivery_packaging_agent` vs `validation/impl/delivery_completeness` — **already disagree** on the same package | **DIVERGENT** | F-POST-04 |
| `assembly_manifest` (phase post) | 2 writers, incompatible schemas | **DIVERGENT** | F-POST-05 |
| Assembly validators | 3 independent validators, divergent rules | **DIVERGENT** | F-POST-06 |
| Delivery manifest seam | 2 ids, 2 field grammars, no in-graph producer | **DIVERGENT** | F-POST-07 |
| Budget state | 4 caps, 7 representations, 6 writer modules, no single state | **DIVERGENT** | F-BUD-01/02/04, F-CFG-06 |
| Spend recording | none: `spent_usd` always 0, `SpendRecord`/`actual_cost_usd` zero writers | **DIVERGENT (defect)** | F-BUD-03 |
| Budget refusal | 8 gate sites; only 1 can refuse; graph gate always passes a ceiling; MCP/operator default to no cap; router gate inert | **DIVERGENT** | F-BUD-02 |
| Number-word / scene-count grammar | duplicated byte-identically | **DISTRIBUTED** | F-BUD-05 |
| Constraint extraction | `constraints/extractor.py`, one call site | **SINGLE** — clean, guarded | — |

**Candidate owner:** `post` owns the post/delivery lifecycle and models;
`governance` owns the budget law.

## 13. Test doubles and harness

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| Canned agent payloads | `app/mock_responses.py` (production package), unbound to output schemas; 2 of 11 already contradict the prompt templates | **DIVERGENT** | F-TEST-01 |
| Mock model responses | 3 sources; the shipped `MockModelAdapter` is dead-wired | **DISTRIBUTED** | F-TEST-02 |
| Mock providers | 2 shipped classes (one contract) + ≥3 test-local doubles that bypass it; registry entries hand-built in 4 places and already divergent | **DIVERGENT** | F-TEST-07 |
| Checkpoint git double | session-wide replacement with no parity test; silently no-ops missing paths | **DIVERGENT** | F-TEST-03 |
| Sandbox storage helper | bypassed by 64 direct `ArtifactStore` constructions; marker profile read by nothing | **DIVERGENT** | F-TEST-04 |
| Fixture construction | re-implemented per tier; integration has no conftest | **DISTRIBUTED** | F-TEST-05 |
| Production-separation guard | 3 overlapping enforcers; the snapshot guard has no test, watches 3 fixed roots, compares size only | **DISTRIBUTED** | F-TEST-06 |
| `GraphServices` seams | no protocol; 2 `FakeArtifactStore`s already disagree | **DISTRIBUTED** | F-TEST-08 |

**Candidate owner:** `devharness` (one test-double package with declared
contracts), or keep `testing` and give it a contract (decision in `03`).

## 14. Module boundaries and the import law

| Concern | De-facto owners | Status | Findings |
|---|---|---|---|
| Dependency law | `AGENTS.md:51` prose only; **8** domain→domain edges violate it by AST sweep (7 of them are reachable from the audit's three targeted greps — the eighth, `generation→artifacts`, is real at 7 statements and was outside the generation grep's pattern, per `reviews/adversarial-evidence.md` §3.1), but the law never defines "domain module" so the count is undefined (32 edges at package granularity with `graph`/`mcp` excluded, 21 with `schemas` as target removed, 17 with `artifacts` also removed — see `reviews/orchestrator-verification-notes.md` V3); says "12 packages" when 17 exist | **DISTRIBUTED (unenforced)** | F-BOUNDARY-01 |
| `schemas` public surface | `schemas/__init__.py` façade exists, but 72 non-schema files import the private `schemas._base` | **DISTRIBUTED** | F-BOUNDARY-02 |
| Boundary enforcement | 2 bespoke AST test files (`artifacts`, `graph`); no global law, no linter | **DISTRIBUTED** | F-BOUNDARY-04 |
| Cross-package private access | `schemas._base` (107 sites across 72 non-schema files), `mcp/server.py:248 → app._persistence`, `config/profile_resolver.py:204 → providers` private symbol, plus 3 private-**symbol** sites | **DISTRIBUTED** | F-BOUNDARY-05 |
| `scripts/` operator tooling | outside all four CI gates (ruff `pyproject.toml:127`, mypy `Makefile:42`, pytest `testpaths`, coverage); 9 files / 1,678 lines re-spelling the phase (50 lines / 53 occurrences), artifact-id, MCP-tool and agent-id vocabularies; 4 of the offenders already import `FilmPhase` | **DISTRIBUTED (unguarded)** | F-BOUNDARY-07 |
| `documentation/` as source of truth | `AGENTS.md:1` makes `documentation/architecture-blueprint.md` authoritative; it prints `"current_phase": "visual_development"` at `:1570`/`:1655` where `FilmPhase` has only `visual_dev` | **scope decision, not a finding** — documentation ships no code, so the drift cannot silently fail shipped behaviour; recorded with anchors | — |
| `app` ↔ `mcp` direction | import cycle (7 modules at sub-package granularity) | **DIVERGENT (cycle)** | F-BOUNDARY-03 |
| `testing` package placement | ships in the wheel, excluded from coverage, imports 3 domains | **DISTRIBUTED** | F-BOUNDARY-06 |

**Candidate owner:** a `module-law` declaration + one guard suite (no runtime
import target).

---

## 15. The five dependency cycles (enola, exact at HEAD)

| # | Cycle | Severity of the seam |
|---|---|---|
| C1 | `agents/prompt_templates` ↔ `agents/prompt_templates/defaults` | façade re-export; cheap |
| C2 | `app` ↔ `mcp` (+5 sub-modules, 7 members) | design-level; blocks hard modularity |
| C3 | `graph` ↔ `graph/nodes` ↔ `graph/orchestrator_validators` ↔ `graph/subgraphs` | intra-package; structure-level |
| C4 | `providers` ↔ `providers/adapters` | façade re-export; cheap |
| C5 | `schemas` ↔ `schemas/registries` | façade re-export; cheap |

## 16. Coverage ledger (bar A1) — measured

Bar A1 requires every source package and entry point to be mapped to at least one
concern and explicitly marked. The previous revision of this table was
**hand-maintained and stale** — a mix of aggregate finding counts and bare id lists
(`9`, `16+10+12+8`, `(F-MCP-02/09)`) that no command could reproduce; the adversarial
coverage pass caught it (`reviews/adversarial-coverage.md` §H11). It is replaced with
a measured column.

**Reproduce (per package, the number of finding blocks that name it):**

```bash
cd docs/modular-architecture
for p in agents app artifacts checkpoints cli config constraints generation graph \
         kb mcp post providers review schemas testing validation; do
  printf '%-14s %s\n' "$p" "$(awk -v pkg="$p/" '
    /^### F-[A-Z]+-[0-9]+/ { if (b && h) n++; b=1; h=0; next }
    b && index($0, pkg) { h=1 }
    END { if (b && h) n++; print n+0 }' audit/*.md)"
done
```

This is deliberately a plain substring match on `` `<package>/` `` inside a finding
block, so there is exactly one way to read it. At this revision
(`grep -h '^### F-' audit/*.md | wc -l` → **180** blocks = 178 live findings + the
two `F-TEST-02` withdrawal stubs):

| Package | Finding blocks naming `` `<pkg>/` `` | Audited in | Ownership status |
|---|---|---|---|
| `graph` | 119 | 01, 02, 08, 10 | DISTRIBUTED |
| `mcp` | 111 | 11, 04, 08 | DISTRIBUTED |
| `app` | 99 | 02, 10, 11, 13 | DISTRIBUTED |
| `schemas` | 59 | 03, 07, 14 | DISTRIBUTED (as vocabulary source) |
| `artifacts` | 56 | 07, 06, 09 | SINGLE for storage, DISTRIBUTED for the contract |
| `generation` | 53 | 06, 05, 12 | DISTRIBUTED |
| `agents` | 46 | 04, 03, 09, 12 | DISTRIBUTED |
| `validation` | 36 | 08, 03, 11 | DISTRIBUTED |
| `config` | 27 | 03 | DISTRIBUTED |
| `providers` | 26 | 05 | DISTRIBUTED |
| `post` | 22 | 12 | DISTRIBUTED |
| `cli` | 21 | 11 | DISTRIBUTED |
| `checkpoints` | 18 | 10 | DISTRIBUTED |
| `testing` | 17 | 13, 14 | DISTRIBUTED |
| `kb` | 16 | 09 | DISTRIBUTED |
| `constraints` | 10 | 12, 03 | **SINGLE** for extraction; pacing vocabulary DISTRIBUTED (H3) |
| `review` | 10 | 08 | SINGLE (thin) |

A low count is not a coverage failure and a high count is not a quality signal: the
column answers only "was this package reached by at least one finding", which is what
bar A1 asks. `review` and `constraints` are low because they are genuinely thin
surfaces with few owners, not because they were skipped.

Entry points and non-package surfaces:

| Surface | Audited in | Ownership status |
|---|---|---|
| `cli.run:main` | 11 | DISTRIBUTED (F-MCP-02/09) |
| `mcp.server:main` | 11 | DISTRIBUTED |
| `app.product_gate:main` | 11 | DISTRIBUTED |
| `langgraph.json → graph/graph.py:graph` | 11, 10 | **DISTRIBUTED and import-poisoning** (F-CRP-12) |
| `profiles/` | 03 | DISTRIBUTED (F-CFG-01/05/12) |
| `scripts/` | 14 | see §16.1 — sampled, classified, one finding |
| `tests/` | 13, 14 | DISTRIBUTED |
| `documentation/` | — | see §16.2 — declared prior art, not audited; drift recorded |

### 16.1 `scripts/` — scope decision (bar A1)

`scripts/` is **not** a product module: 9 Python files / 1,678 lines of operator
tooling, imported by nothing under `src/`. It was sampled by audit 11 and audited to
justify the scope call by audit 14 (`audit/14-module-boundaries-and-import-law.md`
§"A1 coverage closure"). Residual risk, stated rather than hidden: hardcoded phase
vocabulary in `scripts/` drifts silently from `schemas/_base.FilmPhase` and no guard
covers it. See audit 14 for the measured inventory and whether it was promoted.

### 16.2 `documentation/` — scope decision (bar A1)

`documentation/` was **used as prior art, never audited as source**. That is
defensible for an ownership audit — it ships no code — but it is not harmless:
`AGENTS.md` makes `documentation/architecture-blueprint.md` the architectural source
of truth, and it already drifts from the code (it prints
`"current_phase": "visual_development"` where `FilmPhase` has only `visual_dev`).
Recorded, with anchors, in audit 14 §"A1 coverage closure", not silently omitted.

**Other gaps, stated honestly:** `film-knowledge-base/` and `profiles/` content
beyond the config audit were out of scope; `docs/` (this program's own output) is
audited by the adversarial passes, not by the cluster audits.

## 17. Clean concerns (single-owner, verified)

| Concern | Owner | Guard |
|---|---|---|
| Storage layout, roots, atomic writes, path helpers | `artifacts` / `ProjectStorage` | `tests/unit/artifacts/test_storage_boundary.py` |
| Graph must not import `testing`/`app` | `graph` | `tests/unit/graph/test_startup_boundaries.py` |
| Constraint extraction | `constraints` | recorded in audit 12 |
| Multi-model review package shape | `review` | recorded in audit 08 |
| KB conflict detection | `kb/conflicts.py` | recorded in audit 09 |
| MCP contract flags (registration is the only builder) | `mcp/tools/registry.py` | `contract.py` duplicate-name rejection |
| Filename sanitization / ref grammar parse | `schemas/artifact.ArtifactRef` | single parser; formatter is the leak |

## 18. Prior-art status

Reconciled in the audits: `documentation/audit-findings.md` items are mostly
still present at HEAD (e.g. provider health ad-hoc dict, no capability
enforcement, KB builder unwired, `NEEDS_REVISION` unreachable); the
`hardcoded-values-inventory.md` re-check found 6 fixed, 13 present, 1 **worse**
(the `300` runtime fallback is now 3 sites), and 5 citations drifted. Details in
`audit/03` §5 and each audit's "Prior art" field.

---

### What this map says in one paragraph

The repository has **one properly owned subsystem (`artifacts` storage, guarded),
two clean leaf concerns (constraints, KB conflicts), and roughly 25 distributed
concerns** clustered into seven ownership domains that recur across clusters:
phase/lifecycle, orchestration state, configuration/profiles, registries
(agent/validator/provider/kind), generation job lifecycle, budget/spend,
persistence/roots, and test doubles. The recurring mechanism is the same
everywhere: a *canonical type or registry exists*, but callers re-derive its
content from string literals or a second table, so the canonical definition has
no authority. That is the thing the target architecture must fix, and it is why
the enforcement layer matters more than moving files.
