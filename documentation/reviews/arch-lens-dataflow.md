# LENS-DATAFLOW — State Management & Data Flow Review

Repo: `/Users/ghassan/my-projects/film-pipeline-langgraph` @ `arch-improvement-review`, HEAD `e811d1d`. Read-only review; single output (this file).
Scope: LangGraph pipeline state & data flow only. All line numbers verified against HEAD.

---

## F-1 — The side-channel propagation allowlist is a fixed key list; 9 of 10 orchestrator channels are not covered by it (heading count critic-corrected from "10 of 11"), and no invariant fails when a new one is added

**SEVERITY: HIGH** (this is the D-009 bug class, still open generically)

**EVIDENCE**
- `src/film_pipeline/graph/orchestrator_state.py:22-63` defines **10 channel keys**: `_orchestrator__candidate_refs` (:26), `__approved_refs` (:30), `__active_review_cycles` (:34), `__pending_revisions` (:38), `__routing_decisions` (:42), `__convergence` (:46), `__failure_decisions` (:50), `__provider_health_snapshot` (:54), `__budget_snapshot` (:58), `__execution_brief` (:63).
- `_propagate_side_effects` (`graph/nodes/_agent_handoff.py:62-79`) copies exactly: 3 hand-written decision keys (`_routing_decisions`, `_repair_feedback`, `_validation_reports`, :18-22), the candidate-ref map (:25-37), and sliced `issues`/`validation_report_refs` (:40-59). Of the orchestrator namespace it copies **only `_orchestrator__candidate_refs`**.
- Everything else reaches graph state only when a node *manually* returns the key in its updates dict: `_repair_loop.py:70,78,220` hand-carries `_orchestrator__convergence`; `approval.py:293` hand-carries `_orchestrator__pending_revisions`; `approval.py:267` returns `_orchestrator__approved_refs`.
- The schema declares all 10 channels (`state_schema.py:188-197`) but a schema entry does not propagate anything — the comment at `state_schema.py:122-123` even admits this for scalar settings ("without schema entries the graph silently drops them").
- Guardrail status: the only regression tests are D-009's, which hardcode `candidate_refs` (`tests/unit/graph/test_candidate_ref_propagation.py:48-103`). **No test fails when a new channel is added and not propagated.**

Per-channel production write map (grep-verified):

| Channel | Production writer | Survives node boundary? |
|---|---|---|
| `candidate_refs` | `_save_artifact` → `_publish_candidate_ref` (`nodes/_agent_artifacts.py:43-48`) | Yes — via propagate |
| `approved_refs` | `approve_phase_node` (`nodes/approval.py:260-261`) | Yes — returned explicitly |
| `pending_revisions` | `request_revision_node` (`approval.py:279`) | Yes — returned explicitly |
| `convergence` | repair `_start_round` (`_repair_loop.py:69-73`) | Yes — deep-copied + returned by hand |
| `execution_brief` | `_ensure_execution_brief` (`nodes/visual.py:99`) | **No — see F-2** |
| `active_review_cycles` | none (tests only) | n/a |
| `_orchestrator__routing_decisions` | none (tests only; distinct from bare `_routing_decisions`) | n/a |
| `failure_decisions` | none (tests only) | n/a — feeds dead router rules (F-6) |
| `provider_health_snapshot` | none (tests only) | n/a — feeds dead router rules (F-6) |
| `budget_snapshot` (orch) | none (tests only) | n/a — feeds dead router rules (F-6) |

Also note `ensure_orchestrator_state` (`orchestrator_state.py:415-435`) initializes 9 domains but omits `_EXECUTION_BRIEF` — the registry drift already exists inside the module itself.

**FAILURE SCENARIO** (realized twice already): an agent writes a new domain into the node's deep-copied working state; `_propagate_side_effects` doesn't know the key; LangGraph merges a partial update without it; the channel is permanently empty in checkpointed state while every unit test of the helper module passes green.

**TARGET DESIGN** — a single registry as the *only* place channels are named:
```python
# orchestrator_state.py
@dataclass(frozen=True)
class OrchChannel:
    key: str
    policy: Literal["always_copy", "delta_vs_original", "explicit_return"]
ORCH_CHANNELS: tuple[OrchChannel, ...] = (
    OrchChannel(CANDIDATE_REFS, "always_copy"),
    OrchChannel(CONVERGENCE, "delta_vs_original"), ...
)
```
`_propagate_side_effects` iterates `ORCH_CHANNELS`; `set_candidate_ref` & co. take the key from the registry. Two tests enforce the invariant:
1. *Schema↔registry parity*: iterate `StudioGraphState.__annotations__` (and `__required_keys__`), assert every `_orchestrator__*` (and every underscore side-channel) appears in `ORCH_CHANNELS` — fails at import/collect time when someone adds a channel.
2. *Propagation contract*: parametrized over the registry — mutate each channel in a fake working state, call `_propagate_side_effects(source, dest, original)`, assert the policy holds. Adding channel #12 with no registry entry now breaks test 1, not production.
The same registry should absorb the three hand-written keys in `_copy_decision_channels` so there is exactly one key list in the codebase (today: `_agent_handoff.py:20`, plus ad-hoc lists at `nodes/qc.py:33`, `visual.py:166`, `generation.py:139`, `_repair_loop.py:220`).

**MIGRATION**: introduce registry + parity test first (pure refactor, behavior identical); then move the fixed key lists onto it; then fix F-2 as the first consumer.
**EFFORT: S** · **RISK: low** — mechanical, fully test-covered.

---

## F-2 — Live instance of the drop class: `_orchestrator__execution_brief` never reaches graph state, masked by a store fallback pinned to version 1

**SEVERITY: MEDIUM-HIGH**

**EVIDENCE**
- `visual.py:79-110` `_ensure_execution_brief` runs the structure-extractor agent, then `set_execution_brief(new_state, brief)` (:99) writes `_orchestrator__execution_brief` into the node's **private deepcopy**.
- `shot_bible_node` collects updates via `_collect_updates(..., ("shot_matrix_ref", "execution_brief_ref"))` (`visual.py:151-166`) — scalar refs only — and `_propagate_side_effects` has no entry for `_orchestrator__execution_brief` (`_agent_handoff.py:62-79`). Net: the cached brief is discarded at the node boundary on every run.
- Consumers only work because `load_execution_brief` falls back to the artifact store (`orchestrator_validators/brief.py:43-46`) — and that fallback hardcodes **version 1**: `store.load(project_id, FilmPhase.SHOT_BIBLE, "execution_brief", 1)` (`brief.py:35`).

**FAILURE SCENARIO**: any future change that makes the brief re-extractable (e.g., revision requests a different structure) produces `execution_brief v2` on disk while every cross-node consumer keeps validating against v1 from the store fallback — silent structural-gate divergence. Today the early-return at `visual.py:84` hides this because v1's existence blocks re-extraction entirely (the brief is de-facto immutable, which nothing documents or enforces).

**TARGET DESIGN**: either register the channel in F-1's registry (`policy="always_copy"`) so the cache actually persists, or delete the state-cache branch and make the store loader resolve latest-version via `next_version(...) - 1` (as `subgraphs/qc.py:185` already does). Pick one source of truth; the current design pays for both and gets neither.

**MIGRATION**: registry route is one line after F-1; add a test asserting the brief survives `constitution_node`→`shot_bible_node` boundary merge semantics.
**EFFORT: S** · **RISK: low**.

---

## F-3 — Three disconnected notions of "approved": store status lifecycle is dead code, scalar refs track candidates, and promotion is promote-all

**SEVERITY: HIGH** (correctness of the human-gate contract)

**EVIDENCE**
- `ArtifactStore.approve()` / `.supersede()` (`artifacts/store.py:100-132`) have **zero production callers** (repo-wide grep). Every artifact ever saved stays `status=CANDIDATE` in its metadata sidecar forever, including after human approval.
- `approve_phase_node` promotes refs only in orchestrator state maps: deep-copies the `_orchestrator__*` slice (`approval.py:58-66`), then promotes **all** candidate families unconditionally (`approval.py:260-261`) — not just the phase under review.
- Downstream consumers never consult `resolve_artifact()` (the designed approved→candidate resolution order, `orchestrator_state.py:97-111` — grep shows no production caller) nor `approved_refs` for content. They read the scalar `*_ref` keys via `_UPSTREAM_CONTENT_SOURCES` (`nodes/_context.py:331-340`), and those scalars are set unconditionally at save time (`prep.py:209` for constitution_ref) — i.e., they always point at the **latest candidate**, approval or not.
- The human gate payload shows `artifact_refs` (append-only all-versions list, `approval.py:125`), never the candidate/approved maps being promoted on their behalf.
- `consistency.check_staleness` compares `built_from` against `approved_refs` (`consistency.py:84-86`) — informational only ("Non-blocking until Phase 6", :3).

**FAILURE SCENARIO**: script v2 is produced by a repair; `script_ref` flips to v2 immediately; the human rejects the gate; meanwhile any downstream context injection or QC load can consume v2 content that was never approved. Conversely, approving one phase silently grants `APPROVED`-map status to stale candidates of unrelated families. Rollback/audit tooling reading store statuses sees "everything is a candidate".

**TARGET DESIGN**: one promotion path. `approve_phase_node` should call `store.approve(...)` for exactly the families whose candidates the gate reviewed (derive from the gate payload's ref list ∩ latest candidates), emit `supersede` for prior versions, and consumers should resolve through `resolve_artifact(state, family)` instead of raw scalars. Scalar refs remain "latest written"; approved map remains "last human-blessed"; the two may differ *visibly*, enforced by the consistency checker being allowed to block.

**MIGRATION**: (1) wire `store.approve` into `approve_phase_node` behind existing gate flow + test asserting sidecar status transitions; (2) switch `_UPSTREAM_CONTENT_SOURCES` reads to `resolve_artifact` per family; (3) narrow promote-all to gate-scoped families.
**EFFORT: M** · **RISK: medium** — touches approval semantics; needs e2e gate test before flip.

---

## F-4 — Two live QC implementations with material drift; normal flow uses the Send subgraph, repair replay uses the sequential node

**SEVERITY: HIGH**

**EVIDENCE (why both exist)**: `graph.py:119` binds the graph node `qc_node` to `build_qc_subgraph()` — the parallel path owns the normal flow. But `repair_phase_node` re-runs phases by direct function invocation through `_PHASE_NODES`, which maps `"qc"` to the sequential `qc_node` (`_repair_loop.py:47`, registry at :38-50); the manual advance fallback uses the same registry (`app/_graph_exec.py:336-344`). A compiled Send subgraph cannot be called as a plain function on a state dict, so repair needed something callable — hence the sequential copy survived.

**Drift inventory (both files read in full):**

| Dimension | Sequential `nodes/qc.py` | Parallel `subgraphs/qc.py` |
|---|---|---|
| Artifact resolution | Pinned versions parsed from `state["artifact_refs"]`, tried against a fixed phase list (`:158-181`) | Ignores refs entirely; scans **all** `FilmPhase` values for latest-on-disk via `next_version()-1` (`:182-198`) |
| Validator coverage | Phase-keyed runners incl. delivery validator (`_VALIDATOR_RUNNERS :381-388`, `{delivery}` at :387) | Fixed 6 workers, **no delivery worker** (`:45-52, :205-212`) |
| Side effects | Emits `MatrixPatch` artifact + `qc_patch_ref` (`:71-95`); consensus via clip-validator agent (`:98-115`) and `ConsensusBuilder` when ≥2 reports (`:184-203`) | None — reduce only translates findings→issues (`:244-272`) |
| Validator wiring | `template_registry` + `pass_state_as_context=True` for script validators (`:291-300`) | Suppresses `set_services` errors; never passes templates or state context (`:139-148, :95`) |
| Failure visibility | Exceptions swallowed per-validator (`:267-274`) | Skips/failures recorded as status reports (`:55-65`) — better |
| Report flow | Appends into carried `_validation_reports` (`:406-413`) | Reduce **replaces** `_validation_reports` wholesale with QC-only reports (`:261`) |

Issue-id scheme (`val:{validator_id}:{code}`) is consistent across both (`nodes/qc.py:426-434` vs `subgraphs/qc.py:232-240`) — the one place they agree by construction.

**FAILURE SCENARIO**: generation fails QC; human requests revision; repair replays qc sequentially; the sequential path validates **pinned older versions** (or misses artifacts whose phase isn't in its load list) while first-pass validated latest-on-disk; matrix patches and consensus artifacts appear only on the repair path. Pass/fail decisions differ depending on which entry point ran — unreproducible QC verdicts.

**RECOMMENDATION — unify, don't isolate.** Extract one pure core, e.g. `graph/qc_core.py`: `run_validator_set(services, project_id, artifact_resolver, validators) -> list[ValidatorReport]` where `artifact_resolver` is injected (ref-pinned for repair fidelity, latest-scan if that's the intended semantic — decide once). Thin adapters: (a) Send fan-out worker bodies and (b) the sequential loop both call the core; reduce_qc_reports keeps issue translation. This deletes the duplicated instantiation/wiring maps (`cls_map` vs direct imports), equalizes coverage, and lets repair produce the same patch/consensus side effects (or deliberately none, documented).
**MIGRATION**: core extraction first with both paths delegating (behavior-preserving, golden-test report output per path), then reconcile resolver semantics + add the missing delivery worker to fan-out.
**EFFORT: M** · **RISK: medium** — QC verdicts change on the repair path by design; cover with contract tests comparing both adapters' outputs on a fixture project.

---

## F-5 — Resume validity: bare-except fallback bypasses the human gate; the staleness quartet has zero direct tests; external-state replay covers exactly one key

**SEVERITY: HIGH**

**EVIDENCE**
- Resume payload carries only `generation_requests` (+ synthesized `remove_issue_codes`) across the checkpoint boundary (`app/_resume.py:81-107`). The module docstring states the general problem ("MCP tools mutate the active project state after a graph checkpoint was created") but the implementation replays a single key — mutations to `issues`, ref scalars, or orchestrator channels made between interrupt and resume are lost.
- Post-resume progress is a heuristic: `_approval_made_progress` counts *any* blocking issue present as "progress" (`_resume.py:23-27`), and otherwise compares `PHASE_ORDER` indices (:28-33).
- `_resume_after_approval` wraps the graph invoke in `except Exception:` → manual `advance_to_next_phase` (`app/_graph_exec.py:181-183`). Any bug — KeyError, provider adapter crash, serialization failure — silently converts "resume the gated graph" into "run the next phase node directly", skipping gate semantics entirely.
- Manual advance merges node results by hand-emulating reducers (`run_phase_node`, `_graph_exec.py:336-372`): a hardcoded reducer dict for 4 channels + special-casing 2 more. This is a **third** site defining merge semantics (after LangGraph reducers and `_propagate_side_effects`); it already lacks the `_qc_reports`/`_qc_raw_reports` add-channels (`state_schema.py:208-210`), so a future manual-advance QC would replace instead of append.
- Test coverage: only `_build_resume_payload` is tested (`tests/unit/graph/test_real_human_gates.py:356-368`). `_approval_made_progress`, `_has_stale_generation_request_blocker`, `_preserve_external_generation_requests`, `_strip_stale_generation_request_blockers` — the fleet-flagged quartet — have **no direct tests**. Checkpoint unit tests (`tests/unit/checkpoints/test_checkpoints.py`) cover git backend/manager/snapshot/invalidation CRUD only, none of resume validity.
- Write-only "crash recovery": `.graph_state.json` (`_graph_exec.py:135-143`) and the per-step `CheckpointState` artifacts (`:91-118`, saved on **every** graph step) have no reader anywhere in `src/` (grep-verified) — unbounded version growth with zero consumer. Restore-side, invalid checkpoint metadata rows are silently skipped (`app/_persistence.py`, `restore_checkpoints` `continue` on `ValueError`).

**FRAGILITY SUMMARY**: resume validity = (phase index advanced?) OR (blocking issues?) OR (no exception → else bypass gates). Each clause is individually reasonable; composed, they mean the gate guarantee rests on an untested heuristic guarded by a catch-all.

**TARGET DESIGN**
1. Replace the bare except with a narrow `(FileNotFoundError, json.JSONDecodeError)`-style "no checkpoint" condition; anything else propagates (fail loud) or routes to an explicit degraded-mode flag recorded in audit.
2. Generalize `_external_state` replay from one key to a small allowlist (issues, ref scalars, candidate_refs) built by the same registry as F-1 — MCP mutation replay stops being per-key whack-a-mole.
3. Table-driven unit tests for the quartet (phase regress/stall/blocking-issue matrix) + one integration test: interrupt → external mutation → resume → assert merged state.
4. Either consume or stop writing `.graph_state.json` / per-step `CheckpointState` (keep git-tag checkpoints, which rollback actually uses).

**EFFORT: S–M** · **RISK: low-medium** — narrowing the except may surface latent resume bugs; that is the point.

---

## F-6 — Seven router rules read channels that production never writes: decision logic that cannot fire

**SEVERITY: MEDIUM** (dead logic masquerading as safety)

**EVIDENCE**
- `_action_routing.py` gates routing on: `has_blocking_failure` (:212, reads `_orchestrator__failure_decisions`), `get_blocked_providers` (:227, :329, reads `_orchestrator__provider_health_snapshot`), `is_budget_blocked` (:239, reads `_orchestrator__budget_snapshot`), `has_pending_revision` (:301).
- Grep-verified: the writers of those three channels (`orchestrator_state.py:280-282, :304-308, :347-361`) are called **only from tests** (`tests/unit/graph/test_orchestrator_state.py`, `test_graph.py`, e2e). No node, MCP tool, or runtime path records failure decisions, provider health, or budget snapshots into these channels. The blueprint mandates them (`documentation/architecture-blueprint.md` §Core State Domains, budget/provider-health sections ~line 685-727).
- Same for `start_review_cycle`/`advance_review_round`/`close_review_cycle` (`orchestrator_state.py:126-157`) and `record_routing_decision` (:205-225) — test-only, so `_orchestrator__active_review_cycles` and `_orchestrator__routing_decisions` are permanently empty in real runs.

**FAILURE SCENARIO**: an operator trusts "provider-blocked work continues elsewhere" routing (blueprint promise); in production the rule never fires because the snapshot channel is empty — blocked-provider generations proceed and fail at the provider instead. Reviews of `compute_actions` overstate the system's actual safety behavior.

**TARGET DESIGN**: either wire the writers (generation/post nodes record failure decisions + provider health via the F-1 registry with `policy="always_copy"`; budget snapshot updated where spend is computed) or delete the channels + rules until a phase needs them (AGENTS.md: no scaffolding without concrete need). Recommendation: wire `failure_decisions` + `provider_health_snapshot` (they back blueprint-mandated pause behavior); delete `active_review_cycles` and the duplicate-namespaced `_orchestrator__routing_decisions` (confusingly shadowed by bare `_routing_decisions`, which IS live — `state_schema.py:192` vs `:200`).

**EFFORT: M** (wire) / **S** (delete) · **RISK: low**.

---

## F-7 — Deepcopy-everything node convention: 22 sites, one canonical pattern, dual role as diff-base and mutation-masker

**SEVERITY: MEDIUM**

**EVIDENCE (quantified)**
- Pattern `new_state = deepcopy(state)` ×**10** node entries: `prep.py:107,189,222,271`, `visual.py:28,151,274`, `generation.py:106`, `qc.py:37`, `wrapup.py:20`. Word-count of `deepcopy` across `graph/nodes/**` + `subgraphs/**`: **22** (incl. `approval.py:63` orchestrator-slice copy, `_repair_loop.py:70,78` convergence copies, `subgraphs/qc.py:193` per-artifact copy).
- Why it exists: agents mutate state in place (`BaseAgent.run(state, kb, task, model_output)`, `_agent.py:170-181`; `_record_handoff` appends to `state["_routing_decisions"]`, `_agent_handoff.py:131-149`), so nodes clone, mutate the clone, then reconstruct partial updates by diffing clone-vs-original (`_collect_updates` variants at `nodes/qc.py:50-68`, `visual.py:60-76`, inline in `generation.py:124-141`; `_is_new_ref`/`_is_new_issue` at `_shared.py:196-210`). Returning full state is forbidden because reducer channels would double-append (`graph.py:183-187`, `approval.py:243-248` comments).
- Perf signal (structural, UNCERTAIN magnitude — not profiled): each node deep-copies the entire accumulated state — `generation_requests` (full prompt payloads, enriched in place per `state_schema.py:32-64` docstring), `issues`, `_validation_reports`, all orchestrator maps — O(nodes × |state|) per super-step, multiplied by repair rounds; the QC fan-out additionally ships `dict(state)` per Send worker ×6 (`subgraphs/qc.py:217`) and deep-copies each loaded artifact (`:193`); MemorySaver checkpoints duplicate again per step. For a 90s film with hundreds of shots this is the pipeline's most predictable CPU/GC tax.
- Masking effect (the deeper cost): any stray mutation inside an agent or helper silently vanishes unless a hand-curated list (`F-1`) or `ref_keys` tuple happens to include the key; conversely nodes reason over a private snapshot that diverges from real thread state mid-node, so "reads" inside a node can disagree with what the next node sees. Both directions hide bugs instead of raising.

**Is explicit immutable state feasible?** Yes, staged — the TypedDict discipline already exists (`state_schema.py`) but is unenforced:
1. **S**: keep deepcopy at the node boundary but hand agents a read-only view (`types.MappingProxyType` over the frozen snapshot, or pydantic frozen model per domain) so accidental agent mutation raises immediately instead of vanishing. Agent contracts return `(outputs, artifacts)`; nodes assemble updates explicitly. This kills the diff-by-hand for agent-produced values.
2. **M**: replace per-node hand-diffs with one generic `diff_updates(original, working)` deep-compare utility (single implementation of what 3 variants do today); delete the per-node `ref_keys` tuples (a new key class of omission disappears).
3. **L**: full frozen-state (pydantic frozen / TypedDict-with-reducers-only) — feasible only after every `impl.run` signature stops taking mutable state; do last, and only if profiling shows the copies matter.

**RISK**: step 1 changes every agent's view type — mechanical but broad; gate with existing unit suite + mypy strict.
**EFFORT: S/M/L per stage**.

---

## F-8 — Artifact end-to-end trace: `film_constitution` (every copy/transformation named)

Producer → consumer, with divergence points marked (†):

1. `constitution_node` clones: `new_state = deepcopy(state)` (`prep.py:189`). **Copy #1** (whole state).
2. Lifecycle `_run_agent` (`_agent.py:184-235`): route → KB packet (`state["_last_kb_context_ref"]` mutated, :117) → prompt template context (**Copy #2**: state fields copied into `context_vars`, `_build_template_context`/`_populate_state_fields`) → model output dict → `impl.run(new_state, kb, task, model_output)` returns pydantic `FilmConstitution` under `result["constitution"]`.
3. `_save_artifact` (`_agent_artifacts.py:107-146`): provenance captured (`built_from` = scalar-ref dependency map, `_context.py:274-289`); `next_version` **scans disk** for max version+1 (`store.py:69-90`); `store.save` serializes **twice** (`model_dump(mode="json")` payload + `model_dump_json` string, `store.py:44-45`) and writes **5 files**: `versions/vN.json`, `current.json`, 2 meta sidecars, rendered `.md` (`store.py:175-188`). Ref string minted: `artifact:film_constitution:vN` (`_agent_artifacts.py:142`).
4. Candidate publication mutates the clone: `_publish_candidate_ref` → `set_candidate_ref` (`_agent_artifacts.py:43-48`). †
5. Node update assembly: `updates["constitution_ref"]=ref` (scalar, `prep.py:209`), `updates["artifact_refs"]=[ref]`, then `_propagate_side_effects(new_state, updates, state)` copies the candidate-ref map **by reference** from the clone (`_agent_handoff.py:37` — safe today only because the clone is private; becomes shared-mutation if F-7 stage 3 removes deepcopy). †
6. LangGraph merge: scalar = last-write-wins; `artifact_refs` = `merge_unique`; `_orchestrator__candidate_refs` = whole-map replace (default reducer). Thread checkpointed (MemorySaver unless `FILM_PIPELINE_PERSIST_STATE`, `graph.py:50-56`).
7. Gate: `after_phase` → consistency check → `await_approval` `interrupt()`; the human sees `artifact_refs` (all versions ever), **not** the map that will be promoted (`approval.py:121-130`). †
8. Promotion: `Command(resume={"action":"approve"})` → `approve_phase_node`: slice-deepcopy (#3) of `_orchestrator__*`, promote-**all** candidates into `approved_refs`, return full map (`approval.py:58-66, 253-268`). Store sidecar untouched — stays `CANDIDATE` forever (F-3). †
9. Consumer: downstream prompt context loads via **scalar** `constitution_ref` → `store.load(project_id, "constitution", id, pinned_version)` compacted to char budget (`_context.py:331-381`). Staleness checker separately diffs `built_from` vs `approved_refs` (`consistency.py:65-86`) — informational.

**Silent-divergence points (†)**: (a) scalar ref = latest candidate regardless of gate outcome — consumers read unapproved content; (b) promote-all blurs which version humans blessed; (c) store status never leaves CANDIDATE; (d) QC-subgraph consumers bypass refs entirely and read latest-on-disk (`subgraphs/qc.py:184-198`); (e) execution-brief variant pins v1 (F-2). Four sources claim to answer "which constitution is canonical"; they agree only when nothing ever gets revised.

Shot-level trace adds: shot_matrix save → `_VALIDATOR_ARTIFACTS` latest-scan reads in QC (may read unreviewed vN+1) → `_pending_row_updates` → MatrixPatch artifact (`nodes/qc.py:71-95`) — patch exists only on the sequential path (F-4).

---

## F-9 — Side-effect choke point: is `_propagate_side_effects` the right seam?

**Answer: it is the right *place* (node-boundary projection) but the wrong *mechanism* (hand-maintained allowlist).** Evidence-backed comparison:

| Option | Verdict |
|---|---|
| Status quo: fixed allowlist | Proven failure mode (D-009; F-2 live). Every new channel requires remembering N edit sites (propagate list, ref_keys tuples, repair-loop setdefault, run_phase_node special cases). Reject. |
| `Command(update=...)` returns | Relocates the enumeration problem into every node; adds LangGraph coupling to node signatures. Does not fix "forgot to emit". Reject as primary fix. |
| Per-channel custom reducers for orch maps | Solves *concurrent merge* correctness (relevant once fan-outs write shared maps) but not emission omissions. Adopt selectively later (e.g., candidate_refs upsert-by-family reducer mirrors `merge_generation_requests`). |
| Generic boundary diff (`diff_updates(original, working)`) | Honest generalization of what nodes hand-roll; removes the allowlist class entirely. Cost ≈ existing deepcopy walk. Risks: re-emitting large unchanged nested values — mitigate with shallow-unchanged pruning + value-type policy. Adopt at F-7 stage 2. |
| Registry + `__members__`-style iteration + parity test (F-1) | Cheapest durable guardrail; keeps current architecture. **Adopt now.** |
| Immutable snapshots, agents return deltas (F-7 stage 1→3) | Eliminates the choke point's reason to exist. Long-term target. |

Sequence: registry (S) → generic diff (M) → immutable boundary (L, optional).

---

## Top-3 priorities

1. **F-1 — Channel registry + schema-parity test** (S, low risk): structurally closes the silent-drop bug class D-009 exposed; prerequisite for fixing F-2 cleanly and for any future channel (failure decisions, provider health) being wired safely.
2. **F-5 — Resume gate integrity**: narrow the `except Exception` fallback at `_graph_exec.py:181-183` and add table-driven tests for the untested staleness quartet (`_resume.py:17-78`). Smallest change that restores a hard safety property (gates cannot be bypassed by an exception).
3. **F-4 — Unify QC on one validator-execution core** (M): today repair verdicts are computed from different artifact resolutions, different wiring, and different side effects than first-pass verdicts — QC results are not reproducible across the two paths that both run in production.

*(Honorable mention: F-3's dead store-status lifecycle — promote-all + never-approved sidecars will bite the moment rollback or audit tooling trusts `meta.status`.)*

**UNCERTAIN marks**: F-7 perf magnitude (structural argument only, no profile run — review was read-only); exact behavior of LangGraph subgraph channel projection for `_qc_raw_reports` accumulation across repeated invocations within one thread (inferred from reducer semantics, not executed); whether any out-of-tree consumer reads `.graph_state.json` (no reader in `src/`, grep-verified).
