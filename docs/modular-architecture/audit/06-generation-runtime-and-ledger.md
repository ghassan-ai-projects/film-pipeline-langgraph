# Audit 06 — Generation runtime: job lifecycle, ledger, prompts, media/asset paths, dispatch

Audited at `modular-app` = `fb85baa` (`git rev-parse HEAD` →
`fb85baa0e6b769b709791a96a89980089304bf13`). Working tree clean at audit time.

Method: full reads of every file in the cluster, plus `grep` sweeps for the
state fields (`ledger`, `job_id`, `batch`, `take`, `sidecar`, `media`,
`prompt_ref`, `submit(`, `poll(`). Every anchor below was re-printed from the
file at HEAD immediately before this document was written. All counts are
reproducible with the commands shown.

**Headline correction to prior art.** `documentation/audit-findings.md:98`
claims *"`generation_node` never consults the generation ledger; ledger is only
used by MCP tools."* That is **false at HEAD** — the graph both reads and writes
the ledger (§1). The surviving, narrower problems are that the graph writes only
the *planning* half of the lifecycle and never dispatches (F-GEN-05), and that it
writes on a read path (F-GEN-13).

**Verification record (bar A6).** Independently verified in
`docs/modular-architecture/reviews/verify-06.md`: **11 of 13 findings CONFIRMED
as stated, 2 DOWNGRADED, 0 REJECTED.** Downgrades applied in this revision:

- **F-GEN-07** High (3×4=12) → **Medium (3×2=6)** — the drift proof was refuted
  (the named mutation fails `tests/unit/artifacts/test_state_persistence.py:321-369`);
  the duplication is real but is not a §1.3 silent-partial-edit seam. Prior-art
  line corrected `:83` → `:85`.
- **F-GEN-08** High (3×4=12) → **High (3×3=9)** — the mutation clause was refuted
  (`tests/unit/mcp/tools/test_reference_generation_helpers.py:58` fails on the
  named mutation); the *existing divergence* (reference assets never reach
  `AssetManifest`) holds. Proof reframed to the unpinned `composites.py` sites.

Nine author-fix disputes are resolved in place below — **all nine accepted, none
contested** (F-GEN-02 count → 3 hits; F-GEN-04 anchor → `dispatch.py:31-37`;
F-GEN-05 citation replaced with `schemas/matrix_patch.py:49` →
`artifacts/matrix_projection.py:45`; F-GEN-07 and F-GEN-08 proofs reframed and
downgraded above; F-GEN-10 count corrected; F-GEN-12 active-take clause made
name-dependent and the class changed to O1/O2; and the candidate-owner overlap
reconciled in "Candidate module boundary"). Two further changes come out of the
same review:

- **Three seams the verifier found that this audit had missed** are now findings
  **F-GEN-14** (provider-status vocabulary re-derived as raw literals),
  **F-GEN-15** (`scene_id` `"unassigned"` vs `""`), and **F-GEN-16** (compositor
  PNG writes bypass `ProjectStorage`). The verifier's fourth, minor item
  (`dispatch.py:140-142` borrowing `GenerationExecutor` only for
  `load_shot_rows`) is recorded as support inside F-GEN-01 rather than as its own
  finding. This document therefore carries **19 findings**; the "11 of 13"
  verdict applies to the pre-review set.
- **One correction runs the other way:** §F-GEN-10's duration-default count. The
  verifier said 8 while listing nine line numbers; the audit's original said 4.
  Re-running the command returns **9**, so the finding is scoped to all nine.
- **Findings after this revision:** **19** — Critical 5, High 9, Medium 5, Low 0
  (pre-revision 16 = Critical 4, High 7, Medium 5, Low 0). The three additions
  come from the adversarial coverage pass
  (`../reviews/adversarial-coverage.md` §H1/§H5/§H8) and have **not** been
  independently verified (bar A6 open) — no `Verification:` line below is
  implied for them.
- **Added post-verification (PENDING VERIFICATION):** F-GEN-17 — reference-sheet
  frame-role vocabulary ownerless across compositor/prompt/schema/reviewer/agent
  modules; a prompt-mapped role is silently dropped from the composited board (H1).
- **Added post-verification (PENDING VERIFICATION):** F-GEN-18 — two code-only
  reference acceptance bars and an ownerless sheet-type vocabulary, with the
  sheet-side bar dead at HEAD (H5).
- **Added post-verification (PENDING VERIFICATION):** F-GEN-19 — generation-mode
  resolution implemented twice, verbatim, both silently defaulting to `TEST`
  (H8).

---

## Coverage

| Scope | Verdict |
|---|---|
| `generation/ledger.py` (282) | read in full — owns ledger artifact CRUD + transitions |
| `generation/executor.py` (409) | read in full — owns batch lifecycle + prompt entry point |
| `generation/executor_prompts.py` (121) | read in full — second prompt resolver (F-GEN-03) |
| `generation/executor_delivery.py` (148) | read in full — sole media delivery + take/manifest writer; two `scene_id` spellings (F-GEN-15) |
| `generation/prompt_builder.py` (359) | read in full — shared prompt assembler (consumed by 3 callers) |
| `generation/frame_sidecar.py` (34) | read in full — `.meta.json` sidecar convention |
| `generation/__init__.py` (48) | read — façade; exports `GenerationLedgerManager`, `build_structured_prompt` |
| `generation/compositor/**` (703 across 5 files) | grep-swept + `extras.py:178-186`/`environment.py:128-136` read — no ledger or manifest writes; writes PNG via PIL **directly to disk** (F-GEN-16) + `.sheet.json` |
| `generation/{frame_reviewer,sheet_reviewer,frame_heuristics,delta_regenerator,gemini_client}.py` | grep-swept — no job-state or media-path writes |
| `graph/nodes/generation.py` (132) | read in full — ledger reader + matrix-patch writer (F-GEN-05, F-GEN-13) |
| `graph/nodes/visual.py` (632) | read in full — gen_planning node + cost-estimate artifact writer |
| `graph/nodes/_generation_batch_planning.py` (165) | read in full — graph-side ledger writer (F-GEN-04) |
| `graph/nodes/_generation_prompts.py` (178) | read in full — graph-side prompt resolver (F-GEN-03) |
| `graph/nodes/_visual_matrix_coverage.py` (149) | read in full — scene back-fill; no job-state ownership |
| `graph/nodes/_shared.py` (relevant) | read — `_apply_external_state`, `_generation_request_key` (F-GEN-11) |
| `graph/state_schema.py` (relevant) | read — `merge_generation_requests` (F-GEN-11) |
| `graph/orchestrator_validators/planning_gates.py` (relevant) | read — `validate_dispatch_readiness` |
| `mcp/tools/generation/**` (6 files) | all read — independent dispatch lifecycle (F-GEN-01, F-GEN-02, F-GEN-04) |
| `mcp/tools/reference_generation/**` (7 files) | all read — parallel job lifecycle + asset catalog (F-GEN-06, F-GEN-08); builds compositor output paths inline (F-GEN-16) |
| `mcp/tools/planning.py` (generation section) | read — a third plan/cost builder |
| `app/services/_generation_ops.py` (305) | read in full — operator-side executor driver + text-only copy (F-GEN-09) |
| `app/services/operator.py` (generation section) | read — thin delegates only |
| `artifacts/paths.py` (39) | read in full — dead media-path owner (F-GEN-07) |
| `artifacts/store.py`, `artifacts/project_storage.py`, `artifacts/manifest.py` | read (relevant sections) — asset write surface |
| `providers/base.py` + `mock_provider`, `veo_fast`, `imagen4_gemini`, `seedance_openrouter` (submit/poll/download) | read — provider-side job status enum; no ledger access. Its consumers re-derive the vocabulary as literals (F-GEN-14) |
| `providers/{registry,factory,health,credentials,failure_classifier,pricing}.py` | pricing read; others grep-swept — no ledger/media writes |
| Callers of `GenerationExecutor` outside the cluster (`app/`, `mcp/tools`) | audited — the graph never constructs it |

Not audited (other clusters): `cli/`, `config/`, `checkpoints/`, `post/`,
`review/`, `kb/`, `agents/`, `validation/`, profile files, test files as
subjects. Tests were read only as evidence of what is pinned.

---

## 1. Who consults and writes the ledger at HEAD

The prior claim that the graph ignores the ledger is false. Four graph sites
touch it:

- `src/film_pipeline/graph/nodes/_generation_batch_planning.py:137` —
  `mgr = GenerationLedgerManager(services.artifact_store)`
- `src/film_pipeline/graph/nodes/_generation_batch_planning.py:154` —
  `mgr.plan_batch(`
- `src/film_pipeline/graph/nodes/_generation_batch_planning.py:47` —
  `mgr.approve_spend(project_id, max_cost_usd=max_cost_usd)`
- `src/film_pipeline/graph/nodes/generation.py:43` —
  `mgr = GenerationLedgerManager(services.artifact_store)`

But the graph never submits to a provider — `grep -rn "GenerationExecutor"
src/film_pipeline/graph/` returns no matches. So the graph advances rows only to
`SUBMITTED` (via `approve_spend`) and then stops; the `RUNNING → COMPLETED →
delivered` half of the same state machine lives in two *other* modules
(`generation/executor.py` and `mcp/tools/generation/dispatch.py`).

The graph is also gated on `services`: with no services injected, no ledger is
written at all, pinned by `tests/unit/graph/test_generation_node_ledger.py:127`
(`test_generation_node_falls_back_without_services`).

---

## Findings

### F-GEN-01 — The MCP submit path sends `prompt_ref` (a reference string) to the provider instead of the resolved prompt
- **Class:** O6 (parallel lifecycle) + O8 (missing contract)
- **Severity:** Critical (impact 5 × drift 4 = 20)
- **Concern:** what prompt text a submitted generation job actually carries.
- **De-facto owners:**
  - `src/film_pipeline/generation/executor.py:177` — resolves the prompt, then uses it — `"prompt = resolve_shot_prompt(self._store, project_id, row.shot_id, shot_row, row.prompt_ref)"` and `:181` — `"prompt=prompt,"`
  - `src/film_pipeline/mcp/tools/generation/dispatch.py:77` — passes the ref verbatim — `"prompt=row.prompt_ref,"`
  - `src/film_pipeline/mcp/tools/generation/dispatch.py:81` — `"job = adapter.submit(payload, row.shot_id)"`
  - `src/film_pipeline/mcp/tools/generation/dispatch.py:140-142` — the MCP copy
    borrows the runtime *only* for a matrix read while re-implementing
    submit/poll — `"for shot in GenerationExecutor("` /
    `"_services(rt).artifact_store, rt.provider_adapters"` /
    `").load_shot_rows(project_id)"` (the verifier's missed-in-scope item 4;
    support for this finding, not a separate defect)
- **Drift proof (existing divergence):** the same ledger row submitted through
  the operator/GUI path (`app/services/_generation_ops.py:96` →
  `executor.start` → `executor.py:177`) sends the *assembled prompt text*; the
  same row submitted through the MCP tool
  (`mcp/tools/generation/dispatch.py:114` `start_generation_batch`) sends the
  *artifact reference string* (e.g. `prompt:<id>`). Both paths are live and
  registered (`mcp/tools/registry.py:258` registers `start_generation_batch`).
  `tests/unit/mcp/tools/test_generation.py:95-105` asserts only
  `successes[0]["provider_job_id"]`, never the payload — so the MCP side is
  pinned against nothing.
- **Reproduce:**
  ```bash
  grep -rn "build_payload" src/film_pipeline/generation/executor.py src/film_pipeline/mcp/tools/generation/dispatch.py
  grep -rn "prompt=prompt\|prompt=row.prompt_ref" src/film_pipeline
  ```
- **Blast radius:** `mcp/tools/generation/dispatch.py`, `generation/executor.py`,
  `providers/*`. User-visible consequence: identical ledger rows produce
  different provider payloads; the MCP path submits a non-prompt string, so the
  paid job generates against the wrong instruction (or fails), while the
  operator path works.
- **Candidate owner module:** `generation-runtime` — owns "given a ledger row,
  produce the provider payload"; both surfaces call it.
- **Extraction sketch:** move payload construction out of both surfaces into one
  `build_submission(store, project_id, row, shot_row) -> payload` on the runtime
  owner; `executor._dispatch_row` and `dispatch._submit_one_row` both call it.
  Guard test: submit the same row through both surfaces with a spy adapter and
  assert identical `build_payload` kwargs.
- **Prior art:** `documentation/audit-findings.md:99` — *"`start_generation_batch`
  passes `prompt_ref` (a reference string) as the prompt text to providers."*
  Still present at HEAD, unchanged; this audit adds the second (correct) site so
  the divergence is now provable inside the repo.

### F-GEN-02 — The MCP poll path marks a row COMPLETED without downloading the media or recording the manifest/take
- **Class:** O6 (parallel lifecycle)
- **Severity:** Critical (impact 5 × drift 4 = 20)
- **Concern:** the `RUNNING → COMPLETED` transition and its required side effects.
- **De-facto owners:**
  - `src/film_pipeline/generation/executor.py:293-301` — completing a row delivers first — `"output_refs=output_paths,"` / `"next_action=\"validate\","`, after `:275` — `"output_paths = deliver_completed_job("`
  - `src/film_pipeline/generation/executor_delivery.py:25` — the only delivery implementation — `"def deliver_completed_job("`
  - `src/film_pipeline/mcp/tools/generation/dispatch.py:239-245` — completes by writing status alone — `"status=new_status,"` / `"poll_count=polls,"`
- **Drift proof (existing divergence):** `deliver_completed_job` has exactly one
  **call** site in `src/` (`generation/executor.py:275`). Verified by
  `grep -rn "deliver_completed_job" src/film_pipeline` → **3 hits**: the
  definition (`executor_delivery.py:25`), the import (`executor.py:23`), and that
  single call (`executor.py:275`). The MCP path therefore leaves `output_refs` empty, writes
  no `take-NNN.json` sidecar (`executor_delivery.py:121`), and adds no
  `AssetEntry` to the manifest (`executor_delivery.py:106`) — while the ledger
  row reads `completed`, which is the value `executor.status_rows` surfaces to
  the operator as `"output": row.output_refs[0] if row.output_refs else ""`
  (`executor.py:334`). `tests/unit/mcp/tools/test_generation.py:451-484`
  (`test_resume_generation_polling_status_mapping`) only asserts
  `result["ok"] is True`; no test asserts delivery happened.
- **Reproduce:**
  ```bash
  grep -rn "deliver_completed_job" src/film_pipeline
  grep -rn "output_refs" src/film_pipeline
  ```
- **Blast radius:** `mcp/tools/generation/dispatch.py`, `generation/executor.py`,
  `artifacts/manifest.py`. User-visible consequence: a project driven from MCP
  reports completed generations whose clip files and manifest entries do not
  exist; QC/assembly/delivery read the manifest and see nothing.
- **Candidate owner module:** `generation-runtime` — owns the `COMPLETED`
  transition *and* its delivery obligation.
- **Extraction sketch:** make "record completion" a single runtime call that
  performs delivery then the ledger write; remove the COMPLETED *write* from the
  MCP module, leaving the status mapping as a pure classifier owned by one
  function (F-GEN-14). Guard test: stub an adapter whose poll
  returns `completed`, run each surface, assert the manifest gains one
  `generated_clip` entry and the row gains `output_refs`.
- **Prior art:** new (the prior audit's "*generation state can diverge between
  graph and ledger*" is the same family but names neither site).
- **Verification:** CONFIRMED by `reviews/verify-06.md`; the dispute ("2 hits" →
  **3**) is fixed above — the command returns definition
  `executor_delivery.py:25`, import `executor.py:23`, call `executor.py:275`, i.e.
  exactly one live call site.

### F-GEN-03 — Prompt assembly for a shot is implemented twice, with different fallback chains and different constitution sources
- **Class:** O1 (duplicated normative model) + O2 (duplicated invariant enforcement)
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** how a shot's prompt text is derived from the matrix, bibles, and constitution.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/_generation_prompts.py:64` — graph copy of the row→entry mapping — `"def _prompt_entry_from_row(row: dict[str, Any]) -> dict[str, Any]:"`, body `:68-76`
  - `src/film_pipeline/generation/executor_prompts.py:92` — executor copy — `"def _prompt_entry_from_shot_row(shot_row: dict[str, Any]) -> dict[str, Any]:"`, body `:96-103` (byte-identical key/value mapping)
  - `src/film_pipeline/graph/nodes/_generation_prompts.py:132` — RCTCO composition exists **only** on the graph side — `"def _compose_prompt_from_rctco(rctco: dict[str, Any]) -> str:"`, used at `:172`
  - `src/film_pipeline/generation/executor_prompts.py:50` — executor final fallback — `"return f\"Cinematic shot {shot_id} for project {project_id}.\""` vs `_generation_prompts.py:178` — `"return str(req.get(\"prompt\", \"\") or \"\")"`
  - `src/film_pipeline/graph/nodes/_generation_prompts.py:111-114` — constitution from the **state ref** — `"constitution_ref = str(state.get(\"constitution_ref\", \"\") or \"\")"` vs `executor_prompts.py:118-120` — constitution from the **latest artifact** — `"store, project_id, FilmPhase.CONSTITUTION, \"film_constitution\""`
- **Drift proof (existing divergence):** three concrete divergences for the same
  shot: (a) an entry whose only prompt is an `rctco` block yields the composed
  RCTCO text from the graph resolver (`_generation_prompts.py:170-172`) and the
  bare `"Cinematic shot …"` string from the executor resolver; (b) when the two
  resolvers disagree on the constitution source they assemble different blocks
  through the shared `build_structured_prompt`; (c) the operator-facing preview
  (`app/services/_generation_ops.py:137` → `executor.resolve_prompt`) can
  therefore show text that differs from the text the graph stamps at
  `_generation_batch_planning.py:73-74`. Tests exist per side
  (`tests/unit/generation/test_executor.py:302-318`,
  `tests/unit/graph/test_generation_node_ledger.py:109-115`) and none compares
  them.
- **Reproduce:**
  ```bash
  grep -rn "_prompt_entry_from_row\|_prompt_entry_from_shot_row" src/film_pipeline
  grep -rn "rctco" src/film_pipeline
  grep -rn "film_constitution" src/film_pipeline/generation src/film_pipeline/graph/nodes
  ```
- **Blast radius:** `graph/nodes/_generation_prompts.py`,
  `generation/executor_prompts.py`, `graph/nodes/_generation_batch_planning.py`,
  `app/services/_generation_ops.py`. User-visible consequence: the prompt a
  human approves in the preview is not provably the prompt that ships; RCTCO-only
  plans silently degrade to a placeholder on the submit path.
- **Candidate owner module:** `generation-runtime` — owns prompt resolution for
  both surfaces; `generation/prompt_builder.py` remains the shared assembler.
- **Extraction sketch:** keep `build_structured_prompt` as the block grammar;
  move `resolve_shot_prompt` + the row→entry mapping + RCTCO handling into one
  module that takes an explicit `constitution` and `character_bible` (injected,
  not loaded), so the graph passes refs and the executor passes latest; delete
  `_generation_prompts.py`'s assembly functions. Guard test: parameterized over
  a matrix row + reference index, assert both callers return the same string.
- **Prior art:** new.

### F-GEN-04 — The ledger row state machine has two writers with different transition rules for the same statuses
- **Class:** O3 (split state authority) + O6
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** which fields a ledger row transition must set.
- **De-facto owners:** `update_row` is called from **10 sites in 2 modules** —
  `grep -rn "update_row(" src/film_pipeline/generation/executor.py
  src/film_pipeline/mcp/tools/generation/dispatch.py` → `executor.py:196,257,293,399`
  and `dispatch.py:31,100,172,239,272,295`.
  - `src/film_pipeline/generation/executor.py:399-405` — failure sets a terminal action — `"status=GenerationStatus.FAILED,"` / `"next_action=\"wait_human\","`
  - `src/film_pipeline/mcp/tools/generation/dispatch.py:34-36` — failure sets neither — `"status=GenerationStatus.FAILED,"` / `"error_code=error_code,"` / `"blocking_reason=reason,"`
  - `src/film_pipeline/generation/executor.py:201` — submit time on dispatch — `"submitted_at=datetime.now(UTC),"` vs `src/film_pipeline/generation/ledger.py:255` — submit time on **spend approval** — `"submitted_at": now,`
  - `src/film_pipeline/generation/executor.py:260` — local poll counter — `"poll_count=row.poll_count + 1,"` vs `src/film_pipeline/mcp/tools/generation/dispatch.py:243` — provider's counter — `"poll_count=polls,"`
- **Drift proof (existing divergences):** the same ledger row ends in different
  shapes depending on which surface touched it:
  1. `next_action`: a FAILED row from the operator path is parked at
     `wait_human`; the same failure via MCP leaves `next_action` at the value
     `ledger.py:98` gave it, `submit` — the MCP failure call
     (`dispatch.py:31-37`) sets only `status`/`error_code`/`blocking_reason` and
     never touches `next_action`, i.e. the row still advertises itself as needing
     submission.
  2. `submitted_at`: on the operator path it is *overwritten* with the provider
     submit instant (`executor.py:201`), so the spend-approval instant written by
     `ledger.py:255` is lost; on the MCP path it stays at the spend-approval
     instant forever, because `_mark_row_running` (`dispatch.py:100-106`) omits
     it.
  3. `poll_count`: operator path counts local polls; MCP path overwrites with the
     adapter's own counter. A provider that does not increment `polls` (e.g.
     `providers/adapters/veo_fast.py:52-54` returns without touching `polls`)
     yields a permanently 0 `poll_count` through MCP and an incrementing one
     through the executor.
  No test asserts any of the three field values across surfaces:
  `tests/unit/mcp/tools/test_generation.py:451-484` checks only the returned
  status mapping.
- **Reproduce:**
  ```bash
  grep -rn "update_row(" src/film_pipeline/generation/executor.py src/film_pipeline/mcp/tools/generation/dispatch.py
  grep -rn "submitted_at\|poll_count" src/film_pipeline/generation src/film_pipeline/mcp/tools/generation
  ```
- **Blast radius:** `generation/ledger.py` (the data), `generation/executor.py`,
  `mcp/tools/generation/dispatch.py`, `app/services/_generation_ops.py`,
  `mcp/tools/generation/status.py`. User-visible consequence: `get_generation_status`
  and the operator workspace report different `submitted_at`, `poll_count`, and
  `next_action` for the same DB state; retry/repair logic keyed on `next_action`
  behaves differently per surface.
- **Candidate owner module:** `generation-runtime`'s ledger component (the module
  that owns the artifact — there is no peer `generation-ledger` module) exposes one
  transition API
  (`mark_submitted/mark_running/mark_completed/mark_failed/mark_cancelled`) that
  every writer must use.
- **Extraction sketch:** replace the free-form `update_row(**updates)` with named
  transition methods that fix each field's meaning; make `update_row` private.
  Guard test: a table-driven test calling each transition from each surface and
  asserting an identical row snapshot.
- **Prior art:** new.
- **Verification:** CONFIRMED (10 `update_row(` sites in exactly 2 modules; all
  three field divergences reproduced statically). The dispute over the weak anchor
  is fixed above: the MCP failure call spans `dispatch.py:31-37`, so the claim
  points at that span rather than at its closing `)`. Candidate owner renamed from
  `generation-ledger` to `generation-runtime`'s ledger component.

### F-GEN-05 — The graph marks shot-matrix rows `generated` at planning time and uses a generation id as the asset reference
- **Class:** O3 (split state authority)
- **Severity:** High (impact 4 × drift 3 = 12)
- **Concern:** which store owns "this shot has generated media".
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/generation.py:64` — matrix row status — `"set={\"status\": \"generated\"},"`
  - `src/film_pipeline/graph/nodes/generation.py:57-59` — the "asset ref" — `"req.get(\"asset_ref\") or req.get(\"output_ref\") or ledger_rows_by_shot.get(sid, \"\")"` where `ledger_rows_by_shot` maps `shot_id → generation_id` (`:44`)
  - `src/film_pipeline/generation/ledger.py:97` / `executor.py:299` — the other authority — `"status=GenerationStatus.PREPARED,"` then `"output_refs=output_paths,"`
- **Drift proof (existing divergence):** at the moment
  `_mark_matrix_rows_generated` runs, `_plan_generation_ledger` has only just
  created rows and approved spend (`_generation_batch_planning.py:154,164`), so
  the ledger says `submitted` with empty `output_refs` while the matrix says
  `generated` with `asset_refs` containing a **generation id** (`gen:…`, minted
  at `ledger.py:86`), not a media path. Nothing submits to a provider in the
  graph at all. Consumers reading the matrix
  (`schemas/matrix.py:75` — `"status: str = \"planned\""`) cannot distinguish
  this from a real delivery. The guard test
  `tests/unit/graph/test_generation_node_ledger.py:105-107` asserts only that a
  patch ref exists, not its content.
- **Reproduce:**
  ```bash
  grep -rn "status\": \"generated\"" src/film_pipeline/graph
  grep -rn "GenerationExecutor" src/film_pipeline/graph
  grep -rn "asset_refs" src/film_pipeline
  ```
- **Blast radius:** `graph/nodes/generation.py`, `schemas/matrix.py`,
  `schemas/matrix_patch.py`, `artifacts/matrix_projection.py` (the patch
  application path). User-visible consequence: the master matrix advertises generated
  assets that do not exist and points at non-path ids; downstream QC/validation
  that trusts row status sees false readiness.
- **Candidate owner module:** `generation-runtime` owns "shot X has media"
  (derived from `COMPLETED` + `output_refs`); the matrix patch should be emitted
  by the routine that completes the row, not by the planning node.
- **Extraction sketch:** delete `_mark_matrix_rows_generated` from the planning
  node; have the completion transition (F-GEN-02's owner) emit the matrix patch
  with `output_refs[0]`. Guard test: run the planning node, assert no matrix
  patch is emitted; run a completion, assert the patch carries the delivered path.
- **Prior art:** the prior audit only said `generation_node` was a shell
  (`documentation/audit-findings.md:59`); this specific mis-marking is new.
- **Verification note:** the patch is applied by `schemas/matrix_patch.py:49`
  (`def apply_to(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:`),
  reached through `artifacts/matrix_projection.py:45` —
  `"rows = patch.apply_to(rows)"` — a module imported **only** by
  `tests/unit/artifacts/test_matrix_projection.py:9` and by no `src/` module
  (`grep -rn "matrix_projection" src/` → no matches). An earlier draft of this
  finding cited `artifacts/store.py:823` as "normalizes `asset_refs`"; that line
  is the scene→markdown renderer — `'for key in ("characters", "asset_refs", "reference_refs", "validation_refs"):'`
  — which only reads `asset_refs` to emit markdown. Citation corrected.

### F-GEN-06 — Generation status is a 10-member enum whose writers use 6, beside a second untyped reference-generation status grammar
- **Class:** O1 (duplicated normative model)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** the vocabulary of "what state is this generation in".
- **De-facto owners:**
  - `src/film_pipeline/schemas/_base.py:168-180` — the normative enum — `"REQUIRES_HUMAN_REVIEW = \"requires_human_review\""` / `"BLOCKED_BUDGET = \"blocked_budget\""`
  - Reference-generation path writes raw strings into untyped dicts — `src/film_pipeline/mcp/tools/reference_generation/outcomes.py:66` `"raw[\"generation_status\"] = \"validated\""`, `:84` `"raw[\"generation_status\"] = \"needs_regeneration\""`, `:108` `"raw[\"generation_status\"] = \"generated\""`, `retry_loop.py:64` `"raw[\"generation_status\"] = \"failed\""`
  - Consumers re-derive the vocabulary as literals — `app/services/_generation_ops.py:181` `"counts = {\"prepared\": 0, \"submitted\": 0, \"running\": 0, \"completed\": 0, \"failed\": 0}"`, `mcp/tools/generation/planning.py:167` `"if r.status.value == \"submitted\""`, `mcp/tools/reference_generation/composites.py:73` `"if entry.get(\"generation_status\") not in (\"validated\", \"generated\"):"`
  - Terminal subset duplicated — `generation/ledger.py:126-131` and `mcp/tools/generation/status.py:47-52` both spell out `COMPLETED/FAILED/CANCELLED/TIMED_OUT`
- **Drift proof (existing + mutation):** (a) existing — the reference path emits
  `needs_regeneration`, which appears in **neither** `GenerationStatus` nor the
  `generation_status` field description at `schemas/reference.py:70-72`
  (`"'planned' | 'generated' | 'failed' | 'validated'."`); (b) mutation — rename
  `GenerationStatus.RUNNING`'s value in `_base.py:173`; mypy stays green,
  `_generation_ops.py:181-185` silently stops counting `running`, so
  `_generation_next_step` (`:196-200`) falls through to `"approve_phase"` on a
  batch that is still running. No test fails: `_count_rows_by_status` and
  `_generation_next_step` have no direct test, and the suite's only `next_step`
  assertion (`tests/unit/app/services/test_operator_service.py:624`) exercises
  the text-only workspace, which computes it inline at `_generation_ops.py:283`.
  (c) `grep -rn "REQUIRES_HUMAN_REVIEW\|BLOCKED_PROVIDER\|BLOCKED_BUDGET" src/`
  → only the three definition lines; nothing ever writes them.
- **Reproduce:**
  ```bash
  grep -rn "BLOCKED_BUDGET\|REQUIRES_HUMAN_REVIEW\|BLOCKED_PROVIDER" src/film_pipeline
  grep -rn "generation_status" src/film_pipeline/mcp/tools/reference_generation src/film_pipeline/schemas/reference.py
  grep -rn "GenerationStatus.TIMED_OUT" src/film_pipeline
  ```
- **Blast radius:** `schemas/_base.py`, `schemas/reference.py`,
  `mcp/tools/reference_generation/*`, `app/services/_generation_ops.py`,
  `mcp/tools/generation/status.py`. User-visible consequence: operator status
  counts and "next step" advice can be wrong; two asset pipelines cannot be
  queried with one status vocabulary.
- **Candidate owner module:** `generation-runtime` owns one status grammar for
  *all* generation kinds (clips and reference images), typed via `GenerationStatus`.
- **Extraction sketch:** extend/replace `GenerationStatus` with the reference
  vocabulary (or map reference states onto it explicitly), make
  `ReferenceIndexEntry.generation_status` that enum, and derive the terminal set
  once. Guard test: assert every status string emitted in `src/` is a member of
  the enum, and that the terminal set has exactly one definition.
- **Prior art:** `documentation/audit-findings.md:29` notes a "dead
  `NEEDS_REVISION` status" in validation — same failure mode in generation; this
  finding is new.

### F-GEN-07 — The canonical media-path helper is dead and import-banned, while `ProjectStorage.media_dir` re-implements the same convention
- **Class:** O1 (duplicated normative model)
- **Severity:** Medium (impact 3 × drift 2 = 6) — **downgraded from High (3×4=12) on independent verification**
- **Concern:** the module that owns `<project>/media/scenes/<scene>/<shot>`.
- **De-facto owners:**
  - `src/film_pipeline/artifacts/paths.py:3-5` — declares exclusive ownership — `"Every artifact path must flow through this module. No other module constructs"` / `"paths manually."`
  - `src/film_pipeline/artifacts/paths.py:37-39` — the declaration — `"def media_scene_dir(project_slug: str, scene_id: str, shot_id: str, root: Path) -> Path:"` / `"return project_dir(project_slug, root) / \"media\" / \"scenes\" / scene_id / shot_id"`
  - `src/film_pipeline/artifacts/project_storage.py:208-210` — the second declaration — `"self.project_dir(project_id) / _layout.MEDIA_DIRNAME / \"scenes\" / scene_id / shot_id"`
- **Drift proof (existing divergence, not silent):** `media_scene_dir` has **zero**
  production callers — `grep -rn "media_scene_dir" src/ tests/` returns only its
  definition and its re-export in `artifacts/__init__.py:20,47`; the sole media
  writer calls the other one (`generation/executor_delivery.py:55` —
  `"return ProjectStorage.for_root(root).media_dir(project_id, scene_id, shot_id)"`).
  The "canonical" helper is unreachable by design:
  `tests/unit/artifacts/test_storage_boundary.py:72-85`
  (`test_only_storage_imports_path_helpers`) *fails* if any module outside
  `artifacts/` imports `artifacts.paths`, and the gate test at `:144-159`
  requires `ProjectStorage.media_dir` to exist. So there are **2** production
  construction sites (one dead, one live) plus one delegated caller and one test
  hardcode — and the *live* one is pinned:
  `tests/unit/artifacts/test_state_persistence.py:321-369` hardcodes
  `tmp_path / "store/p1/media/scenes/SC_001/shot_0001"` (`:355`) and asserts the
  downloaded file and its `take-*.json` land there (`:356-357`) and that the
  manifest path starts with `media/scenes/` (`:369`). Mutating
  `project_storage.py:209` therefore **fails a test**; the verifier re-ran this
  under a patched `media_dir` and got FAILED.
  **Downgrade rationale:** mutating the dead `paths.py:39` alone is silent but
  produces no divergent behavior, so the §1.3 condition ("a partial edit can pass
  every existing test while producing divergent behavior") is **not** met. What
  survives is cleanliness debt: a dead, publicly exported helper that falsely
  claims to be the only legal path constructor.
- **Reproduce:**
  ```bash
  grep -rn "media_scene_dir" src/ tests/
  grep -rn '"media" / "scenes"\|MEDIA_DIRNAME / "scenes"' src/film_pipeline
  grep -rn 'media/scenes' tests/unit/artifacts/test_state_persistence.py
  ```
- **Blast radius:** `artifacts/paths.py` (the lie), `artifacts/project_storage.py`.
  User-visible consequence today: none — the live path is pinned. Future
  consequence: a contributor following `paths.py:3-5` writes a third media path,
  or deletes `media_scene_dir` believing it is load-bearing.
- **Candidate owner module:** `artifacts` storage core — keep exactly one media
  locator (`ProjectStorage.media_dir`) and delete the orphan helper.
- **Extraction sketch:** delete `media_scene_dir` from `paths.py` and its
  `__init__` export (or make it delegate to `ProjectStorage.for_root(root).media_dir`);
  drop the "Every artifact path must flow through this module" docstring claim or
  narrow it to the phase-directory helpers that are actually used. Guard test:
  assert `artifacts.paths` exposes no media-locator function (the existing
  `test_only_storage_imports_path_helpers` already bans outside importers).
- **Prior art:** `documentation/audit-findings.md:85` — *"Phase-to-directory
  mapping and safe-id logic are duplicated between `store.py` and `paths.py`"* —
  that specific duplication is now resolved (`store.py:78,357,495,501` all read
  `paths.PHASE_DIR_MAP`), but the **media**-path duplication remains, now without
  the silent-drift claim. (An earlier draft cited `:83`; corrected.)
- **Verification:** DOWNGRADED by `reviews/verify-06.md` — proof refuted, not a
  §1.3 seam. Accepted. This also disposes of the internal contradiction the
  verifier flagged: the earlier draft's "Clean concerns" row already cited
  `test_state_persistence.py:321-369` as pinning `media/scenes/`, which is exactly
  why the proposed mutation is test-caught rather than silent; the two statements
  are now consistent (that row pins the *live* path, `ProjectStorage.media_dir`).

### F-GEN-08 — Reference assets live in a second, parallel catalog with paths re-derived at six sites
- **Class:** O4 (parallel registries) + O1
- **Severity:** High (impact 3 × drift 3 = 9) — **downgraded from High (3×4=12) on independent verification**
- **Concern:** where a generated reference image (a media asset) is recorded and located.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/reference_generation/entries.py:72-74` — the helper — `"return project_root / \"references\" / f\"{subject_type}s\" / subject_id / \"master-frames\""`
  - `composites.py:101,120,173,192,212` — sibling directories re-derived inline — `"sheet_path = project_root / \"references\" / \"characters\" / subject_id / \"identity-sheet.png\""`, `"… / \"references\" / \"scale\" / \"scale-sheet.png\""`
  - `index_files.py:21` — a third inline base — `"idx_dir = project_root / \"references\" / \"index\""`
  - `artifacts/manifest.py:29-45` — the *other* asset catalog (`AssetManifest`), whose writers are only `executor_delivery.py:119`, `_text_only.py:97`, `_generation_ops.py:305`
  - `index_files.py:41,57` — the reference catalog — `"ProjectStorage.for_root(idx_dir).write_json_document("`
- **Drift proof (existing divergence):** the reference path never registers
  anything in `AssetManifest` — `grep -rn "write_manifest\|manifest.add_take"
  src/film_pipeline/mcp/tools/reference_generation` returns no matches — so
  every generated reference frame and composite sheet exists on disk and in
  `references/index/reference-index.json` (`index_files.py:25-43`) but not in the
  manifest that `mcp/tools/artifacts.py:190` and `app/services/_browse_ops.py:98`
  serve `take` numbers from. Nothing enforces agreement between the two
  catalogs; the manifest entries carry `sha256` while the reference index entries
  do not (`index_files.py:28-39`), so the two cannot even be reconciled by
  content. **Silent-drift sites (corrected):** the helper site is *pinned* —
  `tests/unit/mcp/tools/test_reference_generation_helpers.py:54-58` asserts
  `_reference_output_dir(...) == root/"references"/"characters"/"leo"/"master-frames"`,
  so the verifier's re-run of the earlier "change `entries.py:73` and no test
  fails" mutation **FAILED** that test. What remains unpinned is the **five
  inline `composites.py` sites** (`:101,120,173,192,212`) and `index_files.py:21`:
  no test in `tests/unit/mcp/tools/` asserts a composite sheet path, so a change
  to any of those six literals passes every test while producing sheets in a
  directory the frame collector at `composites.py:80`
  (`"frame_path = project_root / asset"`) no longer reads. Drift likelihood is
  therefore 3, not 4.
- **Reproduce:**
  ```bash
  grep -rn '"references"' src/film_pipeline
  grep -rn "write_manifest\|add_take" src/film_pipeline/mcp/tools/reference_generation
  grep -rn 'references' tests/unit/mcp/tools/test_reference_generation_helpers.py
  ```
- **Blast radius:** `mcp/tools/reference_generation/*`, `generation/compositor/*`,
  `artifacts/manifest.py`, `mcp/tools/artifacts.py`. User-visible consequence:
  two asset inventories that disagree; a project can pass delivery checks against
  the manifest while reference sheets are untracked, and take/browse UIs cannot
  see reference media.
- **Candidate owner module:** one reference-layout locator owned by `artifacts`
  (a second locator method on `ProjectStorage`, next to `media_dir` — the same
  owner as all other paths, not a new module); the *registration* half belongs to
  `generation-runtime` (see "Candidate module boundary").
- **Extraction sketch:** add one `reference_dir(project_id, kind, subject_id)`
  locator (beside `media_dir`) and one `register_asset(...)` writer into the
  manifest; make `_reference_output_dir`, `composites.py`, and `index_files.py`
  call them. Guard test: after a mock reference batch, assert every file under
  `references/` has a matching unique `AssetEntry`.
- **Prior art:** new.
- **Verification:** DOWNGRADED to 3×3=9 by `reviews/verify-06.md` — existing
  divergence holds, mutation clause refuted. Accepted; proof reframed.

### F-GEN-09 — The text-only generation policy is implemented twice, with the ledger bypassed in both
- **Class:** O6 (parallel lifecycle)
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** how a text-only project satisfies the generation gates.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/generation/_text_only.py:12` — predicate — `"def _is_text_only_policy(state: dict[str, Any]) -> bool:"` / `:13` `"return str(state.get(\"generation_policy\", \"\")).lower() == \"text_only\""`
  - `src/film_pipeline/app/services/_generation_ops.py:208` — the same predicate again — `"def _is_text_only_policy(state: dict[str, Any]) -> bool:"`
  - `_text_only.py:76-97` vs `_generation_ops.py:287-305` — two identical manifest writers — `"kind=\"text_only_delivery\","`
  - `_text_only.py:24-36` vs `_generation_ops.py:240-256` — two request-row builders writing `"generation_id": f"text-only-{project_id}-{shot_id}"`
- **Drift proof (existing + mutation):** both copies write the same
  `_text_only_generation_completed` flag (`_text_only.py:66`,
  `_generation_ops.py:234`) and complete the phase without ever creating a
  `GenerationLedgerRow`, so "this shot is generated" has two authorities (the
  ledger, and this flag plus `generation_requests`). Mutation scenario: change
  the manifest `kind` in one writer; the other keeps `text_only_delivery`, both
  tests pass (`tests/unit/mcp/tools/test_generation.py:683-710` covers the MCP
  copy; `tests/unit/app/services/test_operator_service.py:608-631` covers the
  operator copy — neither asserts the manifest entry), and the manifest entry's
  kind depends on which surface ran first.
- **Reproduce:**
  ```bash
  grep -rn "_is_text_only_policy\|text-only-delivery\|text_only_delivery" src/film_pipeline
  ```
- **Blast radius:** `mcp/tools/generation/_text_only.py`,
  `app/services/_generation_ops.py`, `artifacts/manifest.py`. User-visible
  consequence: divergent manifest metadata and a second, non-ledger "done" flag
  that generation status tooling cannot see.
- **Candidate owner module:** `generation-runtime` — one text-only policy path.
- **Extraction sketch:** delete the operator copy and have
  `_generation_ops.plan_generation` call the MCP/runtime text-only routine (or
  vice versa); the predicate moves next to the runtime. Guard test: assert the
  policy predicate has one definition and the manifest gains exactly one
  `text_only_delivery` entry regardless of entry surface.
- **Prior art:** new.

### F-GEN-10 — Two independent cost models are compared by the budget gate, and the shot-duration default is re-derived at nine sites
- **Class:** O4 (parallel registries) + O5 (policy-by-branch)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** what a batch is expected to cost, and the ceiling it is checked against.
- **De-facto owners:**
  - `src/film_pipeline/providers/pricing.py:1-3` — claims single authority — `"Single source of truth for provider pricing."` / `"generation-planning prompt read from here, so the cost the planner predicts"` / `"matches the cost the adapter actually charges."`
  - `src/film_pipeline/generation/ledger.py:99` + `:276` — the ledger's number — `"estimated_cost_usd=max(0.0, float((estimated_costs or {}).get(sid, 0.0))),"` / `"total_cost = sum(r.estimated_cost_usd for r in rows if r.status == GenerationStatus.SUBMITTED)"`
  - `src/film_pipeline/graph/nodes/_generation_batch_planning.py:42-45` — the ceiling comes from the **agent artifact** — `"raw_cost = ce_data.get(\"estimated_cost_usd\")"` / `"max_cost_usd = float(raw_cost) * 1.1"`
  - `src/film_pipeline/app/mock_responses.py:363` — the agent number is a literal — `"\"estimated_cost_usd\": 18.72,"`
  - Duration default re-derived at **9** sites — `grep -rn 'duration_seconds", 5' src/film_pipeline`
    returns: `generation/executor.py:116,178`;
    `graph/nodes/_generation_batch_planning.py:150`;
    `mcp/tools/generation/planning.py:97`;
    `mcp/tools/generation/dispatch.py:146`;
    `app/services/_generation_ops.py:136`; `agents/impl/shot_bible_agent.py:88`;
    `mcp/tools/planning.py:179,183`; plus **four** adapter signature defaults —
    `providers/base.py:58` (the `build_payload` contract,
    `"duration: float = 5.0,"`) and its three implementations
    `providers/mock_provider.py:70`, `providers/adapters/veo_fast.py:34`,
    `providers/adapters/seedance_openrouter.py:93`. Four of the nine grep sites are
    the cost/dispatch sites; the other five are display, planning, or extraction
    defaults.
- **Drift proof (mutation scenario):** change
  `PROVIDER_PRICING["seedance-openrouter"]["rate_usd"]` from `0.18` to `0.36`
  (`providers/pricing.py:39`). Every ledger row's `estimated_cost_usd` doubles, so
  `_raise_if_over_budget` (`ledger.py:277`) compares a doubled ledger sum against
  the *unchanged* ceiling derived from the agent-authored `cost_estimate`
  artifact — the batch flips from approved to `ValueError` with no plan change,
  and no test fails: `tests/unit/graph/test_generation_node_ledger.py:124`
  asserts the row cost (`== 1.44`) but no test asserts the ceiling, and the only
  budget tests (`tests/unit/generation/test_ledger.py:151-176`) set both the row
  cost and the ceiling by hand via `update_row`, so they cannot detect the two
  models drifting apart. Conversely,
  the `5`-second default can be changed at `executor.py:116` alone and the graph's
  ceiling math (`_generation_batch_planning.py:150`) keeps the old basis.
- **Reproduce:**
  ```bash
  grep -rn "estimate_cost_for_duration" src/film_pipeline
  grep -rn 'duration_seconds", 5' src/film_pipeline --include=*.py | grep -v __pycache__ | wc -l   # 9
  grep -rn "max_cost_usd = float(raw_cost)" src/film_pipeline
  ```
- **Blast radius:** `providers/pricing.py`, `generation/ledger.py`,
  `generation/executor.py`, `graph/nodes/_generation_batch_planning.py`,
  `mcp/tools/generation/{planning,dispatch}.py`, `mcp/tools/planning.py`.
  User-visible consequence: the spend gate can block a correctly-priced batch or
  wave through an underpriced one, depending on how an LLM-authored estimate
  compares to the catalog.
- **Candidate owner module:** `generation-runtime` owns cost estimation for a
  batch (one function over ledger rows, delegating the rate table to
  `providers/pricing.py`); the ceiling is a policy input, not a second computation.
- **Extraction sketch:** make the ceiling derive from the same
  `estimate_cost_for_duration` call that fills the rows (or store the basis in the
  cost artifact), and give the duration default one named constant. Guard test:
  assert `estimate_total_cost` equals the sum the ceiling was computed from for a
  fixed matrix, and that no literal `5` duration default exists outside the
  owning module.
- **Prior art:** `providers/pricing.py:1-6` records that prices *previously*
  diverged across three places; the surviving seam is between the catalog and the
  agent artifact, which that fix did not close. New as stated.
- **Verification:** CONFIRMED; the verifier flagged the duration-default count as
  understated. Corrected to the measured **9** — note the verifier's own report
  says 8 while listing nine line numbers, so this audit records the command's
  output, not either count. Reviewing it also surfaced that the signature-level
  default appears **four** times (the Protocol plus three implementations), not
  once as the verifier's note implied; that is now stated above.

### F-GEN-11 — `generation_requests` identity is defined by two different dedup keys
- **Class:** O1 (duplicated normative model) + O4
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** what identifies one generation request across graph state and MCP state.
- **De-facto owners:**
  - `src/film_pipeline/graph/state_schema.py:44` — the reducer's key — `"for key in (\"generation_request_id\", \"generation_id\", \"shot_id\"):"`
  - `src/film_pipeline/graph/nodes/_shared.py:163-164` — the replay key — `"\"\"\"Deduplication key identifying a generation request across MCP and graph state.\"\"\""` / `"return str(request.get(\"generation_request_id\", request.get(\"generation_id\", \"\")))"`
- **Drift proof (mutation scenario):** the two functions operate on the same
  list — `_apply_external_state` filters with the 2-key version
  (`_shared.py:182-188`), then LangGraph merges through the 3-key reducer. For a
  request carrying only `shot_id` (the shape the graph node consumes and that
  `tests/unit/graph/test_generation_node_ledger.py:91-99` builds), the reducer
  upserts it by `shot_id` while `_generation_request_key` returns `""` and either
  appends a duplicate or drops the request (when any existing request also lacks
  ids). `merge_generation_requests` has **no test at all**
  (`grep -rn "merge_generation_requests" tests/` → no matches) and
  `tests/unit/graph/test_real_human_gates.py:319-353` only exercises
  id-bearing requests, so the fallback disagreement is invisible.
- **Reproduce:**
  ```bash
  grep -rn "generation_request_id\", \"generation_id" src/film_pipeline/graph
  grep -rn "merge_generation_requests" src/film_pipeline tests/
  ```
- **Blast radius:** `graph/state_schema.py`, `graph/nodes/_shared.py`,
  `graph/nodes/approval.py:237`, `app/_resume.py`. User-visible consequence:
  duplicated or silently dropped generation requests in checkpointed state;
  `_plan_generation_ledger` could plan a shot twice or skip one after a resume.
- **Candidate owner module:** `generation-runtime` publishes the request identity
  function; both the reducer and the replay use it.
- **Extraction sketch:** export one `generation_request_key(request)` from the
  runtime/schema layer and have `state_schema.merge_generation_requests` and
  `_shared._apply_external_state` import it. Guard test: parameterized over
  id-bearing, `generation_id`-only, and `shot_id`-only requests, assert the
  reducer and replay agree on identity.
- **Prior art:** new.

### F-GEN-12 — "Which files count as generated media" is owned by a name denylist in the delivery module while the sidecar grammar is written elsewhere
- **Class:** O1 (three sidecar grammars) + O2 (duplicated produced-file predicate); the branch-policy aspect is O5. Earlier draft said O5 alone.
- **Severity:** High (impact 4 × drift 3 = 12)
- **Concern:** enumerating the produced media files of a completed job.
- **De-facto owners:**
  - `src/film_pipeline/generation/executor_delivery.py:65-71` — the denylist — `"and not path.name.endswith(\"_metadata.json\")"` / `"and not (path.name.startswith(\"take-\") and path.name.endswith(\".json\"))"`
  - `src/film_pipeline/generation/executor_delivery.py:132-148` — the filename→kind classifier whose fallthrough lets a non-media file become a clip — `"return \"generated_clip\""` (`:148`, reached for **any** unclassified file including `.json`)
  - `src/film_pipeline/generation/frame_sidecar.py:11-13` — sidecar grammar #2 — `"return Path(str(frame_path) + \".meta.json\")"`
  - `src/film_pipeline/generation/compositor/_layout.py:234` — grammar #3 — `"manifest_path = Path(str(sheet_path) + \".sheet.json\")"`
  - `src/film_pipeline/artifacts/manifest.py:41-44` — the consequence — `"if existing.shot_id == entry.shot_id and existing.kind == \"generated_clip\":"` / `"existing.active = False"`
- **Drift proof (mutation scenario):** add a `.json` companion to `download()`
  in one adapter (all six adapters write only `.mp4`/`.png` today — verified by
  `grep -rn "write_bytes\|path.write\|_write_" src/film_pipeline/providers`; the
  only `.json` written into a download dir is `mock_provider.py:167`'s
  `f"{job.shot_id}_metadata.json"`, the excluded case). The file is
  not `_metadata.json` and not `take-*.json`, so `_produced_files` returns it
  and `_asset_kind` falls through to `generated_clip`, so it is written into the
  manifest **and** the `take-NNN.json` sidecar as a phantom clip with
  `asset_id=f"{shot_id}:generated_clip:take{take}"` and a real `sha256` — i.e.
  the durable defect is a *phantom clip asset*, not necessarily a lost one.
  **Corrected clause:** an earlier draft claimed the sidecar always becomes the
  active take because "`.mp4` sorts before the `.json`". That holds only for
  underscore-style companions: measured with `sorted([Path('shot_0001.mp4'),
  Path('shot_0001_zz.json')])` → `['shot_0001.mp4', 'shot_0001_zz.json']`, so the
  phantom is appended last and `add_take` deactivates the real clip; but for a
  same-stem companion, `sorted([Path('shot_0001.mp4'), Path('shot_0001.json')])`
  → `['shot_0001.json', 'shot_0001.mp4']`, so the real clip is appended last and
  stays active. The phantom-clip pollution is unconditional; the
  active-take displacement is name-dependent.
  Nothing fails either way: `_asset_kind` and `_produced_files`
  have **no test at all** (`grep -rn "_asset_kind\|_produced_files" tests/` →
  no matches), and `add_take` is exercised only with hand-built entries
  (`tests/unit/artifacts/test_state_persistence.py:414-440`,
  `tests/unit/test_artifacts_manifest.py:41-59`). The producer and the denylist
  must be edited together, and a partial edit is silent — exactly the §1.3
  distributed-ownership condition.
- **Reproduce:**
  ```bash
  grep -rn "meta.json\|sheet.json\|take-0\|_metadata.json" src/film_pipeline
  grep -rn "def _asset_kind" -A 18 src/film_pipeline/generation/executor_delivery.py
  ```
- **Blast radius:** `generation/executor_delivery.py`, `generation/frame_sidecar.py`,
  `generation/compositor/_layout.py`, `providers/*`, `artifacts/manifest.py`.
  User-visible consequence: a non-media file can be recorded in a human-facing
  deliverable manifest as a phantom `generated_clip` (and, for underscore-style
  names, displace the real clip as the active take).
- **Candidate owner module:** `artifacts` owns the one sidecar-naming grammar,
  the media-file predicate, and the paths (F-GEN-16 assigns it the whole write
  surface); `generation-runtime` supplies only the decision of which files it
  recorded.
- **Extraction sketch:** introduce `SIDECAR_SUFFIXES`/`is_sidecar(name)` and
  `is_media_file(name)` in the owning module; `_produced_files` uses the
  predicate instead of a denylist, and every sidecar writer uses the grammar.
  Guard test: for each declared sidecar suffix, assert `_produced_files` excludes
  it and `add_take` keeps the real clip active.
- **Prior art:** new.
- **Verification:** CONFIRMED with one proof clause corrected by
  `reviews/verify-06.md`. The active-take displacement holds only for
  underscore-style names (`<shot>_x.json` sorts before `<shot>.mp4`); for a
  same-stem companion the opposite holds — measured
  `sorted(['shot_0001.mp4', 'shot_0001.json'])` → `['shot_0001.json',
  'shot_0001.mp4']`, so the real clip stays active. The unconditional defect, now
  the proof's core, is the phantom `generated_clip` entry. Class also changed from
  O5 alone to O1+O2 (branch-policy aspect O5), per the verifier.

### F-GEN-13 — The graph's ledger *read* path creates the ledger, bypassing the owner's documented `has_ledger` guard
- **Class:** O5 (policy-by-branch) + O7 (leaked internals)
- **Severity:** Medium (impact 2 × drift 3 = 6)
- **Concern:** whether a read of the generation ledger may write it.
- **De-facto owners:**
  - `src/film_pipeline/generation/executor.py:310-312` — the owner's rule — `"Read paths must check this first: the ledger manager's ``load``"` / `"persists a new empty ledger artifact when none exists, which would"` / `"turn every status refresh into an artifact write."`
  - `src/film_pipeline/generation/ledger.py:59-60` — the behaviour being guarded — `"except FileNotFoundError:"` / `"return self.create(project_id)"`
  - `src/film_pipeline/graph/nodes/generation.py:44` — the read that ignores the guard — `"return {row.shot_id: row.generation_id for row in mgr.load(project_id).rows}"`
  - `src/film_pipeline/graph/nodes/_generation_batch_planning.py:114` — a second unguarded `load` — `"mgr.load(project_id)  # ensures the ledger exists and rows are persisted"`
- **Drift proof (mutation scenario):** the guard exists only as a method on
  `GenerationExecutor` (`executor.py:307`) and is called only by
  `executor.status_rows`/`estimated_cost`/`dispatchable_requests`
  (`executor.py:322,342,352`). The graph read at `generation.py:44` calls
  `mgr.load` directly, so running the generation node on a project with
  `generation_requests` + `shot_matrix_ref` + services but no prior ledger
  **creates and persists** an empty `generation_ledger` artifact (and regenerates
  the artifact index) as a side effect of reading. Change
  `ledger.load()`'s missing-file branch (e.g. return an in-memory empty ledger)
  and the executor's behaviour changes while the graph's does not; no test fails
  (`tests/unit/graph/test_generation_node_ledger.py:127` covers only the
  *no-services* fallback, not the empty-ledger case).
- **Reproduce:**
  ```bash
  grep -rn "has_ledger" src/film_pipeline
  grep -rn "mgr.load(\|self._ledger.load(" src/film_pipeline
  ```
- **Blast radius:** `generation/ledger.py`, `generation/executor.py`,
  `graph/nodes/generation.py`, `artifacts/store.py` (artifact index churn).
  User-visible consequence: spurious ledger artifacts and index/revision churn
  from a read path; `has_ledger` reports true for a project that never planned.
- **Candidate owner module:** `generation-runtime`'s ledger component exposes
  `load_or_none` and `create`; only planning may call `create`.
- **Extraction sketch:** split `load` (never writes) from `ensure` (creates);
  update `plan_batch` to use `ensure`, graph/executor reads to use `load`.
  Guard test: assert reading a project with no ledger leaves the artifact
  directory unchanged.
- **Prior art:** corrects `documentation/audit-findings.md:98` — the graph *does*
  consult the ledger at HEAD; the surviving defect is the write-on-read, which is
  new.

---

### F-GEN-14 — Provider job status is re-derived as raw string literals by the executor while the MCP path parses the typed enum
- **Class:** O1 (duplicated normative model) + O8 (missing contract)
- **Severity:** Medium (impact 3 × drift 2 = 6)
- **Concern:** whether the provider→ledger status vocabulary has one owner.
- **De-facto owners:**
  - `src/film_pipeline/providers/base.py:15-22` — the normative model —
    `"class ProviderJobStatus(StrEnum):"` … `'COMPLETED = "completed"'` /
    `'FAILED = "failed"'` / `'CANCELLED = "cancelled"'`
  - `src/film_pipeline/generation/executor.py:245,247` — copy 1, raw literals —
    `'if job.status == "completed":'` / `'elif job.status == "failed":'`
  - `src/film_pipeline/mcp/tools/generation/dispatch.py:188` — copy 2, typed
    parse — `"job_status = ProviderJobStatus(provider_status)"`, with the
    incomplete mapping `"}.get(job_status, GenerationStatus.RUNNING)"` at `:196`
- **Drift proof (mutation scenario + already-divergent behaviour):** rename
  `ProviderJobStatus.COMPLETED`'s *value* at `providers/base.py:20`: the
  executor's comparison at `:245` stops matching, so `_complete_row` is never
  called and `poll_once` reports `completed == 0` while every row stays
  `RUNNING` — and the MCP parser at `:188` then raises `ValueError` and returns
  `GenerationStatus.RUNNING` at `:190`, i.e. the two copies agree on the wrong
  answer. Drift is 2 rather than higher only because the enum's own value *set*
  is pinned by `tests/unit/providers/test_provider_job_status.py:28-29`
  (`assert {status.value for status in ProviderJobStatus} == _CONSUMED_VOCABULARY`)
  and the executor branch indirectly by
  `tests/unit/generation/test_executor.py:215-232` (`test_poll_once_completes`:
  `assert result.completed == 2` / `assert all(r["status"] == "completed" for r in rows)`).
  Nothing pins either *consumer mapping*, and the two copies are already out of
  sync for `CANCELLED`: the member exists (`providers/base.py:22`) and adapters
  produce it (`providers/mock_provider.py:188`,
  `providers/adapters/seedance_openrouter.py:173`, asserted at
  `tests/unit/providers/test_mock_provider.py:104` and
  `tests/integration/providers/test_seedance_adapter.py:100`), yet the executor's
  chain at `:245,247` has no branch — a cancelled provider job is re-polled as
  if it were still running — and the MCP mapping falls through
  `.get(..., GenerationStatus.RUNNING)` at `:196`. A `GenerationStatus.CANCELLED`
  row is only ever written directly by the cancel tools (`dispatch.py:275,298`);
  no code path derives it from a cancelled *provider* job. Extending the enum
  (with its contract test) therefore requires editing two independent copies, and
  only the copy the author remembers changes.
- **Reproduce:**
  ```bash
  grep -rn 'job\.status == "' src/film_pipeline
  grep -rn "ProviderJobStatus" src/film_pipeline
  grep -rn "CANCELLED" src/film_pipeline
  ```
- **Blast radius:** `providers/base.py`, `generation/executor.py`,
  `mcp/tools/generation/dispatch.py`, `app/services/_generation_ops.py` (counts
  rows by raw status strings, F-GEN-09). User-visible consequence: a job the
  provider reports as `cancelled` is indistinguishable from one still running,
  so it is polled until the provider forgets it.
- **Candidate owner module:** `providers` keeps the vocabulary; `generation-runtime`
  owns the one mapping to `GenerationStatus`.
- **Extraction sketch:** move `_generation_status` onto the runtime's transition
  API and have `generation/executor.py` compare `job.status is
  ProviderJobStatus.COMPLETED`. Guard test: assert no `job.status == "<literal>"`
  comparison exists outside `providers/`, and that every `ProviderJobStatus`
  member has an explicit mapping entry (no `.get` fallback).
- **Prior art:** new — the verifier's missed-in-scope item 1. It also contradicts
  this audit's earlier "Clean concerns" row, which is corrected below.

---

### F-GEN-15 — Scene-less media is named `unassigned` on disk but recorded as `scene_id=""` in the sidecar and `AssetEntry`
- **Class:** O3 (split state authority) + O1 (duplicated normative model)
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** who owns a delivered asset's scene identity.
- **De-facto owners:**
  - `src/film_pipeline/generation/executor_delivery.py:44-46` — the path copy —
    `"return str(shot_row.get(\"scene_id\", \"\") or \"unassigned\")"`, whose
    result becomes a path segment in
    `src/film_pipeline/artifacts/project_storage.py:209-210`
    (`"_layout.MEDIA_DIRNAME / \"scenes\" / scene_id / shot_id"`)
  - `src/film_pipeline/generation/executor_delivery.py:97` — the sidecar copy —
    `'"scene_id": "" if scene_id == "unassigned" else scene_id,'`
  - `src/film_pipeline/generation/executor_delivery.py:111` — the manifest copy —
    `'scene_id="" if scene_id == "unassigned" else scene_id,'`
  - `src/film_pipeline/artifacts/manifest.py:56-57` — the consumer that can never
    match the directory — `"return [e for e in self.entries if e.scene_id == scene_id]"`
- **Drift proof (mutation scenario + already-divergent behaviour):** a shot row
  with no `scene_id` is delivered under
  `media/scenes/unassigned/<shot_id>/` (`executor_delivery.py:46` →
  `project_storage.py:206-212`), while the `AssetEntry` and the sidecar record
  `scene_id=""` (`:97`, `:111`). The same `(scene_id, shot_id)` pair therefore
  names two different locations depending on which copy is read: rebuilding the
  path from the entry yields `media/scenes//<shot_id>` (empty segment), not the
  directory that exists, and `AssetManifest.list_by_scene("unassigned")` returns
  `[]` while `list_by_scene("")` is not a spelling any caller would use. The two
  copies are also written in different languages — a path-presentation sentinel
  versus an empty string — so the translation clause
  `"" if scene_id == "unassigned" else scene_id` is duplicated at `:97` and
  `:111` and must be edited in lockstep with the path builder. Mutation: rename
  `_scene_id_of`'s sentinel to `"none"`; the directory name changes, both
  translation clauses silently keep writing `""`, and **no test fails** —
  `grep -rn "unassigned" tests/` returns **no matches**, and the pinned delivery
  path is the scene-ful one (`tests/unit/generation/test_executor.py:215-232`
  completes through `deliver_completed_job` with `SC_001`).
  Note the delivery module's own docstring at `:52-54` claims *"Path ownership
  belongs to the storage core; this only asks it where to put the media"* — yet
  the scene-id vocabulary it passes is exactly what names the directory.
- **Reproduce:**
  ```bash
  grep -rn "unassigned" src/film_pipeline tests
  grep -rn "scene_id" src/film_pipeline/generation/executor_delivery.py
  ```
- **Blast radius:** `generation/executor_delivery.py`,
  `artifacts/project_storage.py`, `artifacts/manifest.py`,
  `graph/nodes/generation.py` (asset_ref consumers), F-GEN-12's take selection.
  User-visible consequence: scene-less media exists on disk but is unreachable
  through the manifest's scene index; a GUI listing assets by scene shows it
  under no scene, and a path rebuilt from the entry does not resolve.
- **Candidate owner module:** `artifacts` owns the scene→directory convention and
  the `AssetEntry` model; `generation-runtime` supplies the shot's real scene id
  or an explicit "no scene" decision — never a path sentinel.
- **Extraction sketch:** delete the `"unassigned"` literal; have `_scene_id_of`
  return `""` and `ProjectStorage.media_dir` place scene-less media under one
  documented constant (`_layout.UNSCENED_DIRNAME`) **and** record that same
  constant in the entry — or make `scene_id` required on the shot row. Guard
  test: deliver a shot with no `scene_id`; assert `(entry.scene_id, entry.shot_id)`
  resolves back to `entry.path`, and that `list_by_scene` finds the entry under
  whatever spelling the directory uses.
- **Prior art:** new — the verifier's missed-in-scope item 2.

---

### F-GEN-16 — The compositor writes PNG content straight to disk, so `ProjectStorage` is not the only writer
- **Class:** O7 (leaked internals) + unenforced invariant
- **Severity:** Medium (impact 2 × drift 3 = 6)
- **Concern:** whether every write under a project root flows through `ProjectStorage`.
- **De-facto owners:**
  - `tests/unit/artifacts/test_storage_boundary.py:72-82` — the declared
    invariant — `'"""Project path helpers stay internal to the storage package."""'`
    / `'"These modules build project paths themselves: … Ask ProjectStorage for typed values instead."'`
    — but the check bans *importing* `artifacts.paths`, not writing files
  - `src/film_pipeline/generation/compositor/extras.py:181-185` — a bypassing
    write — `"def _save_sheet(canvas: Image.Image, output_path: Path)"` /
    `"output_path.parent.mkdir(parents=True, exist_ok=True)"` /
    `'canvas.save(output_path, "PNG")'`
  - `src/film_pipeline/generation/compositor/environment.py:132-133` — the same
    pair, inline — `"output_path.parent.mkdir(parents=True, exist_ok=True)"` /
    `'canvas.save(output_path, "PNG")'`
  - `src/film_pipeline/mcp/tools/reference_generation/composites.py:98,116,168,186,209`
    — the callers that build `output_path` inline and hand it down
- **Drift proof (mutation scenario):** the storage core owns the media write
  surface and states its contract — `project_storage.py:206-212` creates the
  directory, `:215` is `'"""Write a media sidecar next to its binary, atomically."""'`
  — and `test_storage_boundary.py` is the guard. But `_outside_storage()`
  (`:45-50`) only inspects *imported modules* and three layout constants
  (`:84-95`), so a module that *receives* a `Path` from its caller and calls
  `Path.mkdir` + `Image.save` is compliant by the letter of the test while
  violating its intent. Change the storage core's reference-layout convention:
  the compositor's callers keep passing the old paths, nothing under
  `artifacts/` observes the write, and **no test fails** — no test asserts that
  the set of files written under a project root was produced by
  `ProjectStorage`. The divergence is also semantic: storage's writers are
  atomic, the compositor's PNG writes truncate in place, so an interrupted
  render leaves a partial PNG where the storage contract promises an atomic one.
- **Reproduce:**
  ```bash
  grep -rn "canvas.save\|\.parent.mkdir" src/film_pipeline
  grep -rn "_outside_storage\|artifacts.paths" tests/unit/artifacts/test_storage_boundary.py
  ```
- **Blast radius:** `generation/compositor/{extras,environment,identity,_layout}.py`,
  `mcp/tools/reference_generation/composites.py`, `artifacts/project_storage.py`,
  `artifacts/paths.py` (the dead `media_scene_dir`, F-GEN-07). User-visible
  consequence: partially written sheets on interrupt, and a second, invisible
  write surface that a future storage migration will miss.
- **Candidate owner module:** `artifacts` owns every byte written under a project
  root; the compositor should return an in-memory image and the reference tool
  should call `ProjectStorage`.
- **Extraction sketch:** add `ProjectStorage.write_png(relpath, image)` (temp
  file + `os.replace`) and have `_save_sheet`/the environment board return the
  canvas; guard test monkeypatches the `ProjectStorage` write methods and
  asserts rendering a sheet calls one, plus a sweep asserting no `Image.save` /
  `Path.write_bytes` under a project root outside `artifacts/`.
- **Prior art:** new — the verifier's missed-in-scope item 3.

---

### F-GEN-17 — The reference-sheet frame-role vocabulary has no owner, and a role the prompt builder has mapped prose for cannot be placed by the compositor
- **Class:** O1 (duplicated normative model) + O4 (parallel registries) + O5 (policy-by-prefix)
- **Severity:** Critical (impact 4 × drift 5 = 20)
- **Concern:** what a frame role *is*, which roles a reference sheet contains, and what happens to a role the minting LLM emits that the compositor does not know.
- **De-facto owners:**
  - `src/film_pipeline/generation/compositor/_layout.py:24` — the 13 character roles the identity sheet can place — `"_CHAR_TILES: dict[str, tuple[int, int, int, int]] = {"` (`:25-38`; the same 13 keys at `_CHAR_LABELS`, `:42`)
  - `src/film_pipeline/generation/compositor/environment.py:27` — the **8** environment roles the board can place — `"_ENV_TILES: dict[str, tuple[int, int, int, int]] = {"` (`:28-35`; the same 8 at `_ENV_LABELS`, `:38`)
  - `src/film_pipeline/generation/prompt_builder.py:24` — 13 character prompt blocks — `"_CHARACTER_FRAME_ROLE_TEXT: dict[str, str] = {"`
  - `src/film_pipeline/generation/prompt_builder.py:40` — **10** environment prompt blocks — `"_ENVIRONMENT_FRAME_ROLE_TEXT: dict[str, str] = {"`, read by `_frame_role_text` (`:340`), which falls back to `frame_role.replace("-", " ").title()` (`:345`) for any other role
  - `src/film_pipeline/mcp/tools/reference_generation/entries.py:29` — the anchor-role set, copy 1 — `"ANCHOR_PRIORITY = {\"front-face\": 0, \"wide-establishing\": 0}"`
  - `src/film_pipeline/mcp/tools/reference_generation/outcomes.py:55` — the anchor-role set, copy 2 — `"is_anchor = str(raw.get(\"frame_role\", \"\")).strip().lower() in ("` / `:56-57` — `"\"front-face\","` / `"\"wide-establishing\","`
  - `src/film_pipeline/generation/frame_reviewer.py:64` — the role partition re-derived from string prefixes — `"if frame_role in (\"wide-establishing\",) or frame_role.startswith(\"lighting-\"):"` (also `:66` `"alt-angle-"`, `:70`/`:73` `"detail-"`, `:81`, `:85` `"expression-"`)
  - `src/film_pipeline/generation/compositor/extras.py:23` — a third 4-key tile registry (expression sheet) — `"_EXPRESSION_TILES: dict[str, tuple[int, int, int, int]] = {"`
  - `src/film_pipeline/schemas/reference.py:53` — the type is free text — `"frame_role: str = Field("` / `:55` — `"description=\"e.g. 'front-face', '3-4-left', 'wide-establishing', 'detail-texture'.\","`
  - `src/film_pipeline/graph/nodes/_generation_prompts.py:73` — a *different* vocabulary mapped onto this one — `"\"frame_role\": str(row.get(\"camera_profile\", \"\") or \"\"),"`; the same conflation at `src/film_pipeline/generation/executor_prompts.py:99`
  - `src/film_pipeline/agents/prompt_templates/defaults/production.py:63` — the only role example the minting LLM sees — `"'        \"frame_role\": \"front-face\",\\n'"`
- **Drift proof (existing divergence, executed):** `_CHARACTER_FRAME_ROLE_TEXT` and `_CHAR_TILES` are exactly equal (13/13, symmetric difference `set()`), but `_ENVIRONMENT_FRAME_ROLE_TEXT` has **10** keys against `_ENV_TILES`' **8**, and the two extra roles — `alt-angle-entrance`, `lighting-overcast-morning` — are prompt-only. That is not a paper set difference: `_reference_prompt` (`mcp/tools/reference_generation/entries.py:92`) → `build_structured_prompt` → `_build_environment_prompt` (`prompt_builder.py:169`) → `_frame_role_text` returns the *mapped* prose for both roles (executed: `"View from the entrance."` and `"Overcast morning: soft diffuse light"`), the frame is generated and paid for, `_collect_subject_frames` keys it by that role (`composites.py:76,82`), and `build_environment_board` then iterates only `_ENV_TILES` (`environment.py:116`) — so the frame is never pasted (`:128` is reached only for known roles) and `_write_sheet_manifest` records it neither as a tile nor as a placeholder, because both lists are built from `_ENV_TILES` (`_layout.py:212`). Executing the board build with all three roles yields `tiles=['wide-establishing']` and placeholders only for the seven *known* missing tiles; the two prompt-mapped roles appear nowhere. A role no table knows (`alt-angle-window`) gets the title-cased fallback prompt and is dropped identically. No test can fail on any of this: `grep -rn "_ENV_TILES\|_CHAR_TILES\|_ENVIRONMENT_FRAME_ROLE_TEXT\|ANCHOR_PRIORITY" tests/` returns **no matches**, and `tests/unit/generation/test_sheet_manifest.py:38-48` asserts only that one known role maps to one tile.
- **Reproduce:**
  ```bash
  UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
  from film_pipeline.generation.compositor._layout import _CHAR_TILES
  from film_pipeline.generation.compositor.environment import _ENV_TILES
  from film_pipeline.generation.prompt_builder import _CHARACTER_FRAME_ROLE_TEXT, _ENVIRONMENT_FRAME_ROLE_TEXT
  print('char', len(_CHAR_TILES), len(_CHARACTER_FRAME_ROLE_TEXT), set(_CHARACTER_FRAME_ROLE_TEXT)^set(_CHAR_TILES))
  print('env ', len(_ENV_TILES), len(_ENVIRONMENT_FRAME_ROLE_TEXT), 'prompt-only', sorted(set(_ENVIRONMENT_FRAME_ROLE_TEXT)-set(_ENV_TILES)))
  "
  # -> char 13 13 set()
  # -> env  8 10 prompt-only ['alt-angle-entrance', 'lighting-overcast-morning']
  UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
  import json; from pathlib import Path; from PIL import Image
  from film_pipeline.generation.compositor import build_environment_board
  r=Path('/tmp/h1probe'); r.mkdir(exist_ok=True)
  for n,c in (('w',(200,30,30)),('e',(30,200,30)),('o',(30,30,200))): Image.new('RGB',(64,64),c).save(r/f'{n}.png')
  build_environment_board('studio','Studio',{'wide-establishing':r/'w.png','alt-angle-entrance':r/'e.png','lighting-overcast-morning':r/'o.png'}, r/'b.png')
  m=json.loads((r/'b.png.sheet.json').read_text())
  print('tiles',[t['tile_name'] for t in m['tiles']],'placeholders',m['placeholder_tiles'])
  "
  # -> tiles ['wide-establishing'] placeholders ['alt-angle-desk','alt-angle-corner','lighting-cool-night','lighting-golden-afternoon','detail-texture','detail-prop','color-palette']
  grep -rln "_CHAR_TILES\|_ENV_TILES\|_EXPRESSION_TILES\|_CHARACTER_FRAME_ROLE_TEXT\|_ENVIRONMENT_FRAME_ROLE_TEXT\|ANCHOR_PRIORITY" src/film_pipeline --include=*.py | wc -l   # -> 6 modules reference a named role registry
  grep -rn "_ENV_TILES\|_ENVIRONMENT_FRAME_ROLE_TEXT\|FRAME_ROLE" docs/modular-architecture/audit/ \
    --exclude=06-generation-runtime-and-ledger.md | wc -l   # -> 0 (no *other* audit owns the vocabulary)
  ```
- **Blast radius:** `generation/prompt_builder.py`, `generation/compositor/{_layout,identity,environment,extras}.py`, `mcp/tools/reference_generation/{composites,entries,outcomes,retry_loop}.py`, `generation/frame_reviewer.py`, `generation/delta_regenerator.py` (`_find_entry_by_role` matches on the same string, `:114`), `schemas/reference.py`, `agents/prompt_templates/defaults/production.py`. User-visible consequence: the composited sheet is the reference artifact a human approves; a paid frame whose role has prompt prose (or any LLM-invented role) is silently absent from that sheet and from its `.sheet.json`, and is not even counted as a missing tile, so nothing downstream can tell it was ever planned.
- **Candidate owner module:** `generation-runtime` (reference-sheet component) owns one frame-role registry — `{role → prompt text, tile, label, anchor?}` — with the compositor, prompt builder, reviewer, and anchor policy as consumers.
- **Extraction sketch:** one `FrameRole` registry/enum keyed by the union of roles, each entry carrying its prompt text and (optionally) a tile rect; `_frame_role_text` and the tile dicts read it; both sheet builders must render an unknown role as an explicit placeholder or raise, never drop it; `ANCHOR_PRIORITY` and the inline anchor tuple become a `frame_role.is_anchor` property. Guard test: parameterized over every registry key, assert a tile exists (or a placeholder is recorded) and that the prompt table and tile table have identical key sets.
- **Prior art:** new. No *other* audit file contains the vocabulary (`grep -rn "_ENV_TILES\|_ENVIRONMENT_FRAME_ROLE_TEXT\|FRAME_ROLE" docs/modular-architecture/audit/ --exclude=06-generation-runtime-and-ledger.md` → 0) and `documentation/audit-findings.md` has no `frame_role`/compositor entry. Overlaps audit 04's prompt-template anchor (`production.py:63`) and audit 07's `schemas/reference.py` scope, but neither has a finding for it; not double-counted in this file — F-GEN-03 covers prompt *assembly*, F-GEN-12 covers *sidecar* grammar, neither covers the role registry.
- **Provenance:** uncovered by the adversarial coverage pass (`../reviews/adversarial-coverage.md` §H1); added post-verification.

---

### F-GEN-18 — Two code-only acceptance bars for reference artifacts, and the sheet-type vocabulary that selects one of them has no owner
- **Class:** O1 (duplicated normative model) + O4 (parallel registries) + O5 (policy re-derived at two sites)
- **Severity:** High (impact 3 × drift 4 = 12) — see the refutation inside the drift proof: the reviewer's H5 implies two live authorities for one question; at HEAD the sheet-side bar gates nothing, so impact is 3, not 4. Still High because the registry is unguarded.
- **Concern:** what score accepts a generated reference artifact, and which sheet type selects which rubric.
- **De-facto owners:**
  - `src/film_pipeline/generation/frame_reviewer.py:43` — per-frame bar, absolute — `"_PASS_THRESHOLD = 28.0"` (28/40 = 70%), applied at `:222` — `"passed=total >= _PASS_THRESHOLD,"` and restated in the rubric text at `:41` — `"Threshold: 28/40 (70%).\"\"\""`
  - `src/film_pipeline/generation/sheet_reviewer.py:72` — per-sheet bar, fraction — `"def _pass_threshold(max_score: int) -> float:"` / `:73` — `"return max_score * 0.8"` (80%), applied at `:227` — `"threshold = _pass_threshold(max_score)"`
  - `src/film_pipeline/generation/sheet_reviewer.py:40` — the sheet-type registry — `"_RUBRICS: dict[str, tuple[dict[str, tuple[int, str]], int]] = {"` with exactly `character_identity_sheet`, `environment_board`, `scale_sheet` (`:41,51,61`); an unknown key returns a *failed result*, not an error — `:101-103` — `"rubric_data = _RUBRICS.get(sheet_type)"` / `"if rubric_data is None:"` / `"return _failed_result(subject_id, sheet_type, f\"Unknown sheet type: {sheet_type}\")"`
  - `src/film_pipeline/generation/sheet_reviewer.py:81` — the selection key is free text — `"sheet_type: str,"`; the manifest model re-declares it — `src/film_pipeline/schemas/reference.py:152` — `"sheet_type: str"`; the entry model re-declares the sibling vocabulary — `schemas/reference.py:38` — `"asset_type: str = Field(description=\"e.g. 'character_identity_sheet'.\")"`
  - `src/film_pipeline/mcp/tools/reference_generation/composites.py:105` — call-site spelling 1 — `"_validate_composite(sheet_path, \"character_identity_sheet\", subject_id)"`; `:131` — spelling 2 — `"_validate_composite(sheet_path, \"environment_board\", subject_id)"` (the reviewer's `:101,120,225` are the sheet *paths* and the helper definition, not the type spellings — corrected)
  - `src/film_pipeline/generation/compositor/identity.py:69` / `environment.py:137` — the manifest spellings — `"\"character_identity_sheet\","` / `"\"environment_board\","`
  - `src/film_pipeline/agents/impl/visual_dev_agent.py:107` — the third minting site — `"asset_type=str(entry.get(\"asset_type\", \"character_identity_sheet\")),"` (reviewer cited `:105` — corrected; `production.py:56` and `app/mock_responses.py:318` spell the same literal)
- **Drift proof (mutation scenarios, silent):** (a) *the bar is unpinned across the band its fixtures straddle.* `tests/unit/generation/test_sheet_reviewer.py` has exactly two scored fixtures — total **41** (`test_passing_character_sheet`, asserts passed) and **23** (`test_failing_environment_board`, asserts failed) — so **any** threshold in `(23, 41]` passes the suite: change `sheet_reviewer.py:73` from `0.8` (32) to `0.7` (28, i.e. the frame bar) and no test fails. The frame side is pinned only within `(17, 30]` by the same construction (fixtures 34/17/30). The *agreement* between the two bars is asserted nowhere, and audit 03's reproduce command is structurally blind to the second: `grep -rn '_PASS_THRESHOLD' src/film_pipeline/generation/` (`03-config-profile-and-defaults.md:761`) is case-sensitive and returns only `frame_reviewer.py:43,222`. (b) *the type is the load-bearing half.* Change the literal at `composites.py:105` (or `:131`) to a name absent from `_RUBRICS`: `review_composite_sheet` returns `_failed_result(..., "Unknown sheet type: …")` instead of raising (`:101-103`), and its only production caller discards the return value — `composites.py:232-237` calls it inside `try: … except Exception: pass` — so composite validation silently stops. The two cases are opposite and must stay distinct: an **unknown** type returns at `:103`, *before* `_encode_sheet_image`/`call_gemini` (`:108,115`), so the mistyped path **skips** the paid review entirely; the **correctly-typed** path is the one that still pays for a review whose verdict `_validate_composite` then discards. No test fails: `tests/unit/mcp/tools/test_reference_generation.py:135` patches `review_composite_sheet` and never asserts its arguments or result. That the vocabulary is live rather than decorative is visible in two non-dead consumers: `asset_type` selects the generated aspect ratio at `entries.py:101-105` — `"asset_type = str(entry.get(\"asset_type\", \"\"))"` / `"if \"environment\" in asset_type or subject_type == \"environment\":"` / `"if \"style\" in asset_type or \"camera\" in asset_type or \"scale\" in asset_type:"` — so a frame's `asset_type` decides `16:9` versus `3:4` at submit time; and it selects the review policy at `frame_reviewer.py:91` — `"if asset_type in (\"scale_sheet\", \"prop_sheet\"):"`. **Refutation inside H5:** the reviewer's headline framing — two pass bars for "did this reference image pass?" — is only half true. The bars grade different units (a single frame vs an assembled sheet), so they are not an *executed* divergence; and at HEAD the sheet bar gates nothing, because the only consumer of a `SheetReviewResult`, `regenerate_failing_tiles` (`delta_regenerator.py:59`), has **no production caller** (`grep -rn "regenerate_failing_tiles" src/` → definition + the `generation/__init__.py:11` re-export only), while the per-frame bar *is* live (`retry_loop.py:157` drives retry control; `outcomes.py:206-212` stamps the entry). What survives H5 is the ownerless vocabulary plus a dead-but-exported 80% policy — hence impact 3. The reviewer also cited the type spellings at `composites.py:101,120,225` and `visual_dev_agent.py:105`; both anchors are corrected above.
- **Reproduce:**
  ```bash
  grep -rn '_PASS_THRESHOLD' src/film_pipeline/generation/ --include='*.py'            # audit 03's command -> frame_reviewer.py:43,222 only
  grep -rni '_pass_threshold' src/film_pipeline/generation/ --include='*.py'           # -> adds sheet_reviewer.py:72,154,227
  grep -rn "review_composite_sheet\|_validate_composite" src/film_pipeline --include='*.py'
  grep -rn "regenerate_failing_tiles" src/ --include='*.py'
  grep -rn "_RUBRICS\|character_identity_sheet\|environment_board" docs/modular-architecture/audit/ \
    --exclude=06-generation-runtime-and-ledger.md | wc -l   # -> 0 (no other audit owns the sheet-type vocabulary)
  ```
- **Blast radius:** `generation/{frame_reviewer,sheet_reviewer,delta_regenerator}.py`, `generation/compositor/{identity,environment,extras}.py`, `mcp/tools/reference_generation/composites.py`, `schemas/reference.py`, `agents/impl/visual_dev_agent.py` and `agents/prompt_templates/defaults/production.py` (both mint `asset_type`), plus audit 03 §4's numeric table. User-visible consequence: the reference acceptance policy is a code-only number that can move with no test noticing; a renamed or mistyped sheet type silently disables composite validation (skipping its paid call), while a correctly-typed sheet still pays for a review whose result is thrown away; and `_RUBRICS["scale_sheet"]` is unreachable from the pipeline because `_build_scale_sheet` (`composites.py:180-195`) builds the sheet and never calls `_validate_composite`.
- **Candidate owner module:** `generation-runtime` owns one `ReferenceReviewPolicy` (sheet-type enum + one pass fraction, or two explicitly named, deliberately different fractions) consumed by both reviewers; `artifacts` owns the manifest's `sheet_type` spelling, as it does every other persisted representation.
- **Extraction sketch:** give the sheet types an enum (`ReferenceSheetType`) and key `_RUBRICS` by it; type `CompositeSheetManifest.sheet_type`, `ReferenceIndexEntry.asset_type`, and `review_composite_sheet`'s parameter with it; read both reviewers' bars from one declared policy value (or assert them distinct on purpose); make the sheet/delta review result either consumed or deleted rather than silently discarded. Guard test: assert every sheet-type literal in `src/` is a member of the enum and a `_RUBRICS` key; assert the two reviewers' bars are equal to one declared fraction or explicitly asserted different; assert `_validate_composite` surfaces an unknown type instead of swallowing a failed result.
- **Prior art:** audit 03 **F-CFG-13** (`03-config-profile-and-defaults.md:680`; table row `:761`) already records the per-frame 70% bar as a hardcoded numeric default with no profile key — this finding does **not** re-count that row. What is new: the **second** (80%) bar its command cannot see, the ownerless sheet-type vocabulary, and the discarded sheet-review result. `documentation/reviews/hardcoded-values-inventory.md:220` lists only the Gemini `maxOutputTokens`, not the thresholds.
- **Provenance:** uncovered by the adversarial coverage pass (`../reviews/adversarial-coverage.md` §H5); added post-verification.

---

### F-GEN-19 — Generation-mode resolution is implemented twice, verbatim, and both copies silently fall back to `TEST`
- **Class:** O1 (duplicated normative model)
- **Severity:** High (impact 3 × drift 5 = 15) — drift raised 4 → 5 on independent verification: no test can fail when either fallback changes (see the drift proof's test inventory).
- **Concern:** which `GenerationMode` a generation request is planned under, and what an absent or unrecognised mode means.
- **De-facto owners:**
  - `src/film_pipeline/graph/nodes/_generation_batch_planning.py:24` — copy 1, string in — `"mode = GenerationMode.TEST"` / `:25-26` — `"with contextlib.suppress(ValueError):"` / `"mode = GenerationMode(mode_str)"`; callers `:93` (batch grouping key) and `:160` (`plan_batch`)
  - `src/film_pipeline/mcp/tools/generation/planning.py:25` — copy 2, args dict in, same core — `"mode_str = str(args.get(\"mode\", \"test\"))"` / `:26` — `"mode = GenerationMode.TEST"` / `:27-28`; caller `:78`
  - `src/film_pipeline/schemas/_base.py:183` — the vocabulary both copies parse — `"class GenerationMode(StrEnum):"` (`:186-189` `MOCK`/`TEST`/`PREVIEW`/`PRODUCTION`)
  - `src/film_pipeline/schemas/generation.py:24` — a **third** `TEST` default, on the request model both resolvers feed — `"mode: GenerationMode = GenerationMode.TEST"` (the second declaration is `ledger.plan_batch`'s signature default, `generation/ledger.py:72`)
  - the mode string round-trips back into graph-visible state — `src/film_pipeline/mcp/tools/generation/planning.py:191` — `"\"mode\": row.mode.value,"`
- **Drift proof (mutation scenario; the two copies are behaviourally identical today).** I ran the differential over `test/production/mock/preview/""/"TEST"/" production "/"prod"/"quality"` and over arg forms `{}`, `{"mode": None}`, `{"mode": 0}`, `{"mode": ["test"]}`: every corresponding input yields the **same** member, with the same silent `TEST` fallback — no default-string, stripping, or casing difference exists (the only difference is the wrapper: copy 2 does its own `args.get`, copy 1 receives a pre-stringified value, and the graph caller's extra `or "test"` at `:93` changes the *string* but never the resolved member). So there is no existing divergence; the proof is the mutation. **This is a finding, not a hypothesis:** §1.6.3(b) admits a mutation scenario as a drift proof, and both copies were verified by execution (the differential below, plus the byte-identical bodies) — it must not be re-litigated into the "Unverified hypotheses" section. Change the fallback at `planning.py:26` `GenerationMode.TEST` → `GenerationMode.PRODUCTION` (or the default string at `:25` `"test"` → `"production"`): the MCP path then plans absent/invalid modes as `PRODUCTION` while the graph keeps `TEST` at `_generation_batch_planning.py:24`, and **no test fails** — no test names either symbol (`grep -rn "_parse_generation_mode\|_resolve_generation_mode" tests/` → no matches), every test that calls `plan_generation_batch` omits `mode` or passes the valid string `"test"` (so `GenerationMode("test")` succeeds and the fallback branch is never exercised), and no test asserts a resolved mode anywhere: `tests/unit/test_schemas.py:430` (`assert r.mode == GenerationMode.TEST`) pins the **`GenerationRequest`** schema default built at `:421-429`, not a resolver or a ledger row; `tests/unit/generation/test_ledger.py:101-106` (`test_plan_batch_respects_mode`) calls `plan_batch(..., mode=GenerationMode.PRODUCTION)` with the enum **already resolved** and asserts the row stored it, bypassing both resolvers; `tests/unit/graph/test_generation_node_ledger.py:96` feeds the valid string `"test"` and asserts no mode at all; `tests/unit/mcp/tools/test_generation.py:593` (`test_promote_test_to_production_with_shot_ids_filter`) calls `plan_generation_batch` **without** `mode` and then overwrites every row's mode (`update_row(..., mode=GenerationMode.TEST)`, `:611`) before promoting, so it cannot observe what the resolver produced; and the smoke path that does pass `mode="test"` asserts only `result["ok"] is True` (`tests/smoke/test_manual_4min_mock_short.py:75`). Drift is therefore **5**, not 4: no test can fail when either copy changes. The consequence is reachable: the mode value is published from the ledger into graph state (`planning.py:191`), `_group_requests_by_batch` keys batches on `str(mode.value)` (`_generation_batch_planning.py:95`), and `promote_to_production` gates on `row.mode == GenerationMode.TEST` (`generation/ledger.py:155`) — so the same request planned from MCP and from the graph can land in a different batch and be differently eligible for promotion. **Correction to H8:** the reviewer says "GenerationMode decides dry-run versus real provider spend". It does not at HEAD: the submit path selects its adapter by `row.provider` (`mcp/tools/generation/dispatch.py:69` — `"adapter = rt.get_provider(row.provider)"`) and neither `build_payload` call site reads `mode`; the only *gating* consumer of `mode` is `ledger.py:155` (the batch-grouping key at `_generation_batch_planning.py:95` is a second, non-gating behavioural use). Impact is therefore 3 (wrong internal behaviour, recoverable), not 5.
- **Reproduce:**
  ```bash
  grep -rn "_parse_generation_mode\|_resolve_generation_mode" src/ docs/modular-architecture/audit/ \
    --include=*.py --include=*.md --exclude=06-generation-runtime-and-ledger.md
  # -> 2 definitions + 3 call sites in src/; 0 hits in the *other* audit files
  UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
  from film_pipeline.graph.nodes._generation_batch_planning import _parse_generation_mode as g
  from film_pipeline.mcp.tools.generation.planning import _resolve_generation_mode as m
  print([(s, g(s).value, m({'mode': s}).value) for s in ('test','production','','prod','TEST')])
  "
  # -> [('test','test','test'),('production','production','production'),('','test','test'),('prod','test','test'),('TEST','test','test')]
  ```
- **Blast radius:** `graph/nodes/_generation_batch_planning.py`, `mcp/tools/generation/planning.py`, `generation/ledger.py`, `schemas/_base.py`, `mcp/tools/generation/promote.py`. User-visible consequence: which mode a batch is recorded under depends on the entry surface; `promote_test_to_production` eligibility and the graph's batch grouping follow the surface, and an unrecognised mode string is silently treated as `TEST` with no warning on either path.
- **Candidate owner module:** `generation-runtime` (or `schemas`, where the enum already lives) owns one `resolve_generation_mode(raw: object) -> GenerationMode` with one documented fallback; both callers import it.
- **Extraction sketch:** export one resolver next to `GenerationMode` that takes an arbitrary value, applies `str(...)` plus the `or "test"` normalisation once, and documents `TEST` as the only fallback; delete both private copies and have `_group_requests_by_batch` and `plan_generation_batch` call it. Guard test: parameterized over absent/`None`/blank/valid/invalid values, assert both call paths resolve to the same member and that the fallback is `TEST`.
- **Prior art:** audit 07 **F-ARTIFACT-14** (`07-artifact-refs-and-schemas.md:768`) already records the *schema-layer* half of this vocabulary — `GenerationLedgerRow.mode` closed (`schemas/generation.py:24,57`) vs `SpendRecord.mode: str` bare (`schemas/budget.py:31`) — and nominates `schemas/_base.py` as the one owner; this finding does **not** re-count that row. What is new here is the **string→enum resolution** seam: two private parsers with the same silent `TEST` fallback, one in `graph` and one in `mcp`, which F-ARTIFACT-14 does not reach — the resolver *symbols* appear in no other audit file (`grep -rn "_parse_generation_mode\|_resolve_generation_mode" docs/modular-architecture/audit/ --exclude=06-generation-runtime-and-ledger.md` → 0). Distinct from F-GEN-06 (the `GenerationStatus` vocabulary) and F-GEN-04 (row transition fields).
- **Provenance:** uncovered by the adversarial coverage pass (`../reviews/adversarial-coverage.md` §H8); added post-verification.

---

## Unverified hypotheses (explicitly not findings)

- Whether the Seedance/Veo paid adapters are reachable under a real (non-mock)
  profile, i.e. whether F-GEN-01 costs money in practice. Profile resolution is
  outside this cluster; the adapter code path exists (`providers/adapters/
  seedance_openrouter.py:110-129` submit) but I did not verify a live profile binds
  it.
- Whether any *future* provider adapter writes a `.json` into `output_dir`; F-GEN-12
  is proven only as a mutation scenario because all six adapters at HEAD write
  `.mp4`/`.png` (or the excluded `_metadata.json`).
- Whether `AssetEntry` manifests are ever reconciled against the filesystem by a
  validator; not searched (validation cluster).

---

## Job-state authority map

Fields are from `src/film_pipeline/schemas/generation.py:43-74`
(`GenerationLedgerRow`). "Writers" are exact call sites at HEAD.

| State field | Writers (`file:line`) | Single / distributed |
|---|---|---|
| `status` | `ledger.py:254` (PREPARED→SUBMITTED); `executor.py:200` (→RUNNING); `executor.py:296` (→COMPLETED); `executor.py:402` (→FAILED); `dispatch.py:34` (→FAILED); `dispatch.py:104` (→RUNNING); `dispatch.py:242` (→ mapped status); `dispatch.py:275,298` (→CANCELLED) | **Distributed** — 2 modules, 8 sites, divergent rules (F-GEN-04); the provider→status *mapping* feeding these sites is itself duplicated and incomplete (F-GEN-14) |
| `provider_job_id` | `executor.py:199`; `dispatch.py:103` | Distributed (2 sites, same value, no divergence found) |
| `submitted_at` | `ledger.py:255` (spend approval); `executor.py:201` (provider submit). Not written by `dispatch._mark_row_running` | **Distributed — contested meaning** (F-GEN-04) |
| `last_polled_at` | `executor.py:261`; `executor.py:298`; `dispatch.py:244` | Distributed (consistent semantics) |
| `poll_count` | `executor.py:260`, `executor.py:297` (local +1); `dispatch.py:243` (provider-reported) | **Distributed — contested meaning** (F-GEN-04) |
| `estimated_cost_usd` | `ledger.py:99` (only site, from `pricing.estimate_cost_for_duration`) | Single writer, but the *ceiling* compared against it comes from a different model (`_generation_batch_planning.py:42-45`) → O4 (F-GEN-10) |
| `actual_cost_usd` | **none** — `grep -rn "actual_cost_usd" src/` → only `schemas/generation.py:68` | Never written (dead field) |
| `output_refs` | `executor.py:299` only | Single writer — but `dispatch.py:242` sets COMPLETED without it (F-GEN-02) |
| `error_code` / `blocking_reason` | `executor.py:403-404`; `dispatch.py:35-36`; `dispatch.py:175-176` | Distributed (3 sites, consistent field names) |
| `next_action` | `ledger.py:98` (`submit`), `ledger.py:256` (`poll`), `ledger.py:165` (`stop`); `executor.py:202` (`poll`), `executor.py:300` (`validate`), `executor.py:405` (`wait_human`); `dispatch.py:105` (`poll`), `dispatch.py:276,299` (`stop`). Not set on MCP failure | **Distributed — divergent** (F-GEN-04) |
| `mode` | `ledger.py:92` (plan); `ledger.py:164` (TEST→PRODUCTION) | Single module |
| `prompt_ref`, `reference_refs` | `ledger.py:95-96` (plan only) | Single writer |
| `resume_token` | **none** — `grep -rn "resume_token" src/` → only `schemas/generation.py:71` | Never written (dead field) |
| Ledger *rows* as a whole | `plan_batch` called from `executor.py:120`, `_generation_batch_planning.py:154`, `mcp/tools/generation/planning.py:101`; `approve_spend` from `executor.py:139`, `_generation_batch_planning.py:47`, `mcp/tools/generation/planning.py:163` | Distributed (3 callers each; idempotent by `shot_id` only) |

Parallel state that shadows the ledger (same logical facts, different storage):

| Logical state | Ledger representation | Shadow representation | Split? |
|---|---|---|---|
| Shot has media | `status=COMPLETED` + `output_refs` (`executor.py:296-299`) | shot-matrix row `status="generated"` + `asset_refs` holding a `generation_id` (`graph/nodes/generation.py:57-65`) | **Yes** (F-GEN-05) |
| Reference frame generated | *(no ledger row at all)* | reference index `asset_path` + `generation_status` (`outcomes.py:66-108`); not in `AssetManifest` | **Yes** (F-GEN-06, F-GEN-08) |
| All generation done (text-only) | *(no ledger row)* | `_text_only_generation_completed` flag + `generation_requests` (`_text_only.py:66`, `_generation_ops.py:234`) | **Yes** (F-GEN-09) |
| Batch grouping | *(no batch id anywhere)* | `(provider, model, mode, prompt_ref)` tuple computed at `_generation_batch_planning.py:95` and never persisted | No persisted owner — gap, not a seam |
| Spend ceiling | `sum(row.estimated_cost_usd)` (`ledger.py:276`) | agent `cost_estimate` artifact (`_generation_batch_planning.py:42`) | **Yes** (F-GEN-10) |
| Asset catalog | — | `AssetManifest` (`manifest.py:29`) vs `references/index/reference-index.json` (`index_files.py:41`) | **Yes** (F-GEN-08) |
| A delivered asset's scene identity | *(no ledger field)* | path segment `"unassigned"` (`executor_delivery.py:46` → `project_storage.py:210`) vs `AssetEntry.scene_id=""` (`executor_delivery.py:111`) | **Yes** (F-GEN-15) |

Two further seams are *not* ledger-field splits, so they are not rows above: the
provider-job-status vocabulary is re-derived as raw string literals by the
executor's read path (F-GEN-14), and the compositor writes media bytes without
`ProjectStorage` (F-GEN-16) — the latter is why the *byte-write* surface has two
owners even though the `AssetManifest` column here has one.

---

## Clean concerns (single-owner, guarded)

| Concern | Owner | Guard / evidence |
|---|---|---|
| Ledger persistence mechanics (one revision-counted mutable file, one `ArtifactMetadata`) | `generation/ledger.py:221-234` | `ledger.py:234` is the **only** `save_mutable` call in all of `src/` (`grep -rn "save_mutable" src/` → storage's definition/docstrings + this call); `LEDGER_ARTIFACT_ID` appears only in `ledger.py` |
| Plan idempotency + duplicate-submit prevention | `generation/ledger.py:80-84` (`existing = {r.shot_id …}`), `:249-258` (`only PREPARED rows move`) | `tests/unit/mcp/tools/test_generation.py:108-121` (`test_start_generation_batch_skips_already_submitted`) pins the no-op |
| Budget refusal semantics (`max_cost_usd < 0` = no limit; reject without persisting) | `generation/ledger.py:264-282` | `tests/unit/generation/test_ledger.py:151-176` (`test_approve_spend_budget_gate_rejects`, `…_passes`) covers the raise and the pass; `tests/unit/mcp/tools/test_generation.py:250-255` covers the MCP surface; the "untouched ledger on rejection" property follows from raising before `_persist` (`ledger.py:118-120`) |
| where take numbers come from (`max(existing take)+1`) | `generation/executor_delivery.py:124-129` | single implementation; `tests/unit/artifacts/test_state_persistence.py:321-369` asserts `take-*.json` and `media/scenes/` paths — the *scene* segment of that path is the split in F-GEN-15 |
| one-active-clip-per-shot invariant | `artifacts/manifest.py:35-45` (`add_take`) | enforced in the model, not at call sites |
| prompt *block grammar* (negatives, frame-role text, block order) | `generation/prompt_builder.py` | one definition; all three resolvers call `build_structured_prompt` (`executor_prompts.py:83-89`, `_generation_prompts.py:104-129`, `reference_generation/entries.py:90-97`) |
| provider job status *vocabulary* inside `providers/` | `providers/base.py:15-22` (`ProviderJobStatus`) + adapters | one enum, pinned by `tests/unit/providers/test_provider_job_status.py:28-29`; adapters are its only *writers* — but this row is scoped to the enum: the mapping into `GenerationStatus` is duplicated outside `providers/` and already incomplete (F-GEN-14) |
| compositor sheet *rendering* + `.sheet.json` manifest naming | `generation/compositor/_layout.py:197-237` | one naming rule within the module; **not clean on the write surface** — the PNG bytes themselves bypass `ProjectStorage` (F-GEN-16) |
| `artifacts.paths.PHASE_DIR_MAP` as phase-directory authority | `artifacts/paths.py:14-26`, consumed by `artifacts/store.py:78,357,495,501` and `artifacts/project_storage.py:136` | `tests/unit/artifacts/test_storage_boundary.py:55-85` bans other importers; no second copy exists |

---

## Candidate module boundary

**Ownership split.** Three concerns that individual findings nominated loosely are
assigned exactly once here — this resolves the verifier's dispute that "three of
the audit's own candidate owners disagree about who owns media layout and the
manifest write":

| Concern | Single owner | Everyone else |
|---|---|---|
| Ledger *row* state (`GenerationLedgerRow` fields, transitions, the `generation_ledger` artifact) | `generation-runtime`'s ledger component | reads through it; never calls `update_row` |
| Path conventions (`media/scenes/…`, `references/…`), atomic byte writes, and the `AssetManifest`/`AssetEntry` model — including the `scene_id` spelling | `artifacts` (`ProjectStorage`, `manifest.py`) | asks for paths and calls the writers |
| Provider payload shape (`build_payload`/submit/poll) and the provider-status vocabulary | `providers` | passes decisions in and maps status out through the runtime's one mapping |

There is **no peer `generation-ledger` module**: the ledger is a component
*inside* `generation-runtime`, so the two earlier nominations (F-GEN-04, F-GEN-13)
are corrected to say so. `generation-runtime` decides *which* prompt, refs,
duration, and *which* entries; it does not own paths, bytes, the manifest model,
or payload shape.

**`generation-runtime`** — the single owner of a generation job's lifecycle, its
prompt, and its delivered-media *decisions*, for every surface (graph,
operator/GUI, MCP, reference-image path).

- **Responsibility (one sentence):** given a project and a planned request,
  advance one generation job from `PREPARED` to a delivered media asset with a
  manifest entry, or to a terminal failure with a stated reason — and be the only
  writer of the *ledger row* state.
- **Non-goals:** does not choose provider pricing (reads
  `providers/pricing.py`); does not render prompts from scratch (calls
  `generation/prompt_builder.py`); does not own path conventions, byte writes, or
  the `AssetManifest`/`AssetEntry` model (calls `artifacts`); does not define
  provider payload shape or the provider-status vocabulary (calls `providers`);
  does not own the shot matrix (emits a patch); does not run MCP transport or the
  LangGraph graph.
- **Normative model (N):** `GenerationLedgerRow` + one status grammar covering
  clips *and* reference images (F-GEN-06); one transition API
  (`mark_submitted/mark_running/mark_completed/mark_failed/mark_cancelled`) that
  fixes each field's meaning (F-GEN-04); one `generation_request_key` (F-GEN-11);
  one provider-status→`GenerationStatus` mapping (F-GEN-14).
- **Invariant enforcement (I):** duplicate-submit prevention (already in
  `ledger.plan_batch`/`approve_spend` — keep); "COMPLETED implies delivered"
  (new — F-GEN-02); one prompt per row computed by one resolver (F-GEN-03); the
  budget gate compares like-for-like numbers (F-GEN-10); a scene-less asset's
  recorded `scene_id` and its directory agree (F-GEN-15).
- **Representation authority (R):** the `generation_ledger` artifact and the
  shot-matrix generation patch — **not** the media bytes or the `AssetManifest`,
  which stay with `artifacts`. `mcp/tools/generation/*`,
  `app/services/_generation_ops.py`, and
  `graph/nodes/{generation,_generation_batch_planning}.py` become consumers.
- **Consumers / deleted specialists:** `executor_prompts.py` and
  `graph/nodes/_generation_prompts.py` collapse into one resolver;
  `_text_only.py`'s duplicate side is deleted; `_asset_kind`/`_produced_files`
  and `generation/frame_sidecar.py` collapse into `artifacts`' one sidecar/media
  grammar (F-GEN-12, F-GEN-16) that the runtime consumes;
  `mcp/tools/reference_generation/outcomes.py` and `retry_loop.py` report through
  the runtime's completion transition instead of writing a private status string.
- **Guard tests that fail if ownership regresses:**
  1. *single-writer*: a spy `ArtifactStore` asserts only the runtime's ledger
     component calls `save_mutable` for generation state, and that only
     `artifacts` writes bytes under a project root (pins F-GEN-16).
  2. *cross-surface equivalence*: the same ledger row submitted/polled through
     every surface yields identical provider payloads, row snapshots, and
     manifest deltas (pins F-GEN-01, F-GEN-02, F-GEN-04).
  3. *prompt agreement*: preview text == stamped `resolved_prompt` == submitted
     prompt for a fixture corpus including an RCTCO-only entry (pins F-GEN-03).
  4. *status vocabulary*: every status string written in `src/` is a
     `GenerationStatus` member; the terminal set has one definition; every
     `ProviderJobStatus` member has an explicit mapping entry with no `.get`
     fallback (pins F-GEN-06, F-GEN-14).
  5. *path single-source*: no module outside the storage core assembles
     `media/scenes` or `references/…`, and no module outside `artifacts` writes
     bytes under a project root (pins F-GEN-07, F-GEN-08, F-GEN-16).
  6. *asset identity round-trip*: for every `AssetEntry`, `(scene_id, shot_id)`
     resolves back to `path`, including the scene-less case (pins F-GEN-15).
