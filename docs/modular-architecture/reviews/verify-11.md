# verify-11 — adversarial verification of `audit/11-mcp-surface-safety-and-entrypoints.md`

Verifier: independent agent (did not write the audit). Repo
`${REPO_ROOT}`, branch `modular-app`, commit
`fb85baa` (clean worktree; every anchor below read with `git show HEAD:<path>`).
Method: methodology §1.4/§1.5/§1.6 and bar A6. No repo file was modified.

Machine facts re-measured at HEAD:

```
$ .venv/bin/python -c "... make_registry() ..."
tools 77   confirm 10   mutates 32   checkpoint 1
input_schema non-empty 0   output_schema non-empty 0   idempotency_key_field set 0
$ grep -c mutates=True|confirm=True|checkpoint=True registry.py   # 32 10 1
$ grep -rn "MCPErrorCode\." src/film_pipeline/mcp/tools/          # (empty)
$ grep -rn "raise MCPError" src/film_pipeline/mcp/tools/          # (empty)
$ grep -rn "_live_validator_specs" src/ tests/                    # validation.py only
$ grep -rn "_auto_register_from_runtime" tests/                   # (empty)
$ grep -rn "_save_visual_dev_candidate" tests/                    # (empty)
$ grep -rn "CameraBibleAgent" src/film_pipeline/graph/            # (empty)
$ grep -rn "OperatorService(" src/                                # planning.py:140 only
$ grep -rn "_STALE_ISSUE_CODES\|_STALE_REQUEST_CODES" tests/      # (empty)
```

## Verdict table

| finding | verdict | one-line reason |
|---|---|---|
| F-MCP-01 | CONFIRMED | both gates (`server.py:187`, `checkpoints.py:249/294`) and the lying docstring (`_profile_change.py:101` vs body 98‑145) verified; caveat: the handler copy is unreachable via `server.call`, and its "not enforced at all" wording is false for the canonical path |
| F-MCP-02 | CONFIRMED | all four invocation paths verified, and the bypass is **live**: scripts call confirm-gated tools with no `confirmed` and no handler self-check |
| F-MCP-03 | CONFIRMED | 0/77 non-empty `input_schema`; `_tool_contract` (registry.py:110‑117) never passes schema; transport publishes `{}` |
| F-MCP-04 | CONFIRMED (score 20→16) | two tables real and validator membership genuinely duplicated; drift 5→4 because `test_qc_validator_dispatch.py:75‑107` pins the phase sets; mutation anchor `qc.py:364` is the wrong line |
| F-MCP-05 | **DOWNGRADED → High (12)** | duplication real, but the cited *existing* divergence (`prompt_payload` shapes) is **refuted**; only the provider-default divergence (D7) survives |
| F-MCP-06 | **DOWNGRADED → Medium (8)** | facts real but entirely latent (no production caller of operator mutators, no delete tool); O3 label wrong (single writer, not 2+) |
| F-MCP-07 | CONFIRMED | server registry is populated **only** by the lazy fallback in production; no agreement test; reproduce command verified |
| F-MCP-08 | CONFIRMED | `envelope.py:28` declared, never read/written anywhere in `src/` |
| F-MCP-09 | CONFIRMED | entry points re-derive flag policy; `cli.run.main` never validates; anchor `langgraph.json:3` should be `:4`; duplicate of F-CFG-08/F-CRP-09 with a third candidate owner |
| F-MCP-10 | CONFIRMED | zero handler-side codes; only a synthetic handler test; correction: the transport then erases the typed code too |
| F-MCP-11 | CONFIRMED | `resolve_provider_block` (registry.py:332‑338, providers.py:32) ungated, verified; O5 label weak, and "4 stub tools mutates/confirm" is factually wrong |
| F-MCP-12 | CONFIRMED | bible/planning/graph versioning duplication verified; O7 sub-label unsupported; a third `next_version` copy (`shot.py:71`) uncited |

Counts: 10 CONFIRMED, 2 DOWNGRADED, 0 REJECTED, 0 unverifiable.

---

## Expanded non-CONFIRMED rows

### F-MCP-05 — DOWNGRADED to High (impact 3 × drift 4 = 12); severity was Critical (16)

**Claim under test.** "The two text-only implementations write different `prompt_payload`
shapes — MCP `{"text_only": True, "shot_id": shot_id}` (`_text_only.py:53`), operator
`{"text_only": True}` with `shot_id` only on the row (`_generation_ops.py:240-243`)."

**Counter-evidence (refuted).** The operator path builds exactly the MCP shape:

- `_text_only.py:16-36,51-58` — per-shot row payload
  `{"text_only": True, "shot_id": shot_id}`; fallback row `{"text_only": True}`.
- `_generation_ops.py:240-256` — `payload = {"text_only": True}` then
  `if shot_id != "all": payload["shot_id"] = shot_id`. Per-shot → same payload as MCP;
  the `"all"` fallback → `{"text_only": True}`, again the same.

The rest of the row dict (`generation_request_id`, `generation_id`, `mode`, `provider`,
`model`, `prompt_ref`, `reference_refs`, `status`) is field-for-field identical
(`_text_only.py:24-36` vs `_generation_ops.py:244-256`), as is the shot-id extraction
(`_text_only.py:48` vs `_generation_ops.py:203-205`) and the stale-issue filter
(`_text_only.py:63-73` vs `_generation_ops.py:170-177`). At HEAD the two writers produce
**byte-identical `generation_requests` and manifest entries**; there is no existing
divergence here. The audit's own D8 "two copies of the stale-issue code set" is correct,
but its drift proof's headline divergence is wrong.

**What survives.** (a) Real duplication: two near-identical `_complete_text_only_generation`
implementations, two duplicate constants, and `grep -rn "_STALE_ISSUE_CODES\|_STALE_REQUEST_CODES" tests/`
is empty → the mutation scenario is valid. (b) D7 is a genuine **existing** divergence:
`planning.py:75-76` hard-codes `mock-video-provider`/`mock-fast` while the operator uses
`runtime.default_video_provider()` (`_generation_ops.py:61`), which returns
`seedance-openrouter`/`veo-fast` in real mode (`app/_provider_seeds.py:68-80`) — an MCP
caller omitting provider/model in real mode plans against a provider that does not exist
in that runtime (recoverable: submit fails), not a wrong human deliverable.

**Recomputed severity.** impact 3 (wrong internal behaviour, recoverable; no current
divergence in stored rows) × drift 4 (duplicated constant untested) = **12 High**.
Correction required: replace the prompt_payload sentence with D7/D8 evidence.

### F-MCP-06 — DOWNGRADED to Medium (impact 2 × drift 4 = 8); severity was High (12)

**Facts verified.** `operator.py:322` calls `self.runtime.approve_phase()` with no
`confirmed` parameter (D1); `operator.py:330-342` same for revision (D2);
`operator.py:354-360` → `_generation_ops.py:70-86` → `executor.approve_spend` with no
confirmation (D3). `_populate_project_state` (`projects.py:96-124`) sets exactly the keys
the audit lists and does **not** set `project_kind`; `operator.py:125` is the only writer
in `src/`; `safety.py:131-132` returns `True` for `""`/`"test"`. All confirmed.

**Why the impact is lower than 3.**

- Every unconfirmed operator mutator is unreachable from production: the only
  `OperatorService(...)` construction in `src/` is
  `mcp/tools/generation/planning.py:140` (`preview_generation_prompts`), which touches
  none of them. The divergence cannot reach a human deliverable or corrupt data at HEAD.
- The `project_kind` path-dependence is likewise unreachable from the product boundary:
  no MCP tool exposes deletion (`grep -rn "delete_project" src/` → `runtime.py`,
  `safety.py` only), and `runtime.delete_project` is invoked only from tests. The audit
  acknowledges both latencies in its own blast radius ("Latent at HEAD"), which is
  inconsistent with impact 3.

**Class dispute.** The block is labelled `O6 + O3`, but §1.4 O3 requires "state … written
by **2+** modules with no single writer". `project_kind` has exactly one writer; the
defect is a *missing* writer in the second creation path, i.e. O6 (parallel lifecycle) or
O5, not O3.

**Recomputed severity.** impact 2 (dead path; recoverable if ever wired) × drift 4 = **8
Medium**. Correction required: drop O3, justify the latency explicitly in the severity line.

---

## Missed in scope (own evidence)

1. **The transport erases `MCPErrorCode`, so the code is machine-readable nowhere.**
   `mcp/server.py:188-199` builds `MCPError(code=MCPErrorCode.CONFIRMATION_REQUIRED)`, but
   `mcp/_stdio_transport.py:62-65` maps every failure to `_jsonrpc_error(request_id,
   -32000, message)` — the typed code is dropped before it leaves the process. A JSON-RPC
   client sees code `-32000` for `UNKNOWN_TOOL`, `CONFIRMATION_REQUIRED`, and
   `BUDGET_EXCEEDED` alike. F-MCP-10's closing claim ("machine-readable only for transport
   errors") is therefore backwards, and F-MCP-01's premise that the server emits a
   machine-readable refusal does not hold over the wire. New O8 seam: transport/contract.
2. **`ToolContract.idempotency_key_field` is dead normative state** — `contract.py:57`
   declares it, `registry.py:110-117` never sets it (measured: 0/77 populated),
   `contract.py:110` echoes it in the catalog, nothing reads it. Same O1 class as
   F-MCP-08, and §2's "Single for flags" row wrongly presents the whole flag set as healthy.
3. **`MCPServer.active_project_id` is a write-only second "active project".** Written at
   `server.py:121,157,230-231`; no reader exists in `src/` (only tests assert it), while
   `StudioRuntime.active_project_id` (`runtime.py:44,207,211-213`) is the state the tools
   actually read (`helpers.py:45-52`). O3/O1 split state with no consumer.
4. **Actor attribution is never populated and never consumed.** `server.call` accepts
   `actor_id`/`actor_type` (`server.py:51-58`) and stores them on the envelope
   (`envelope.py:29-30`), but the only transport calls `server.call(tool_name, arguments)`
   with no actor (`_stdio_transport.py:61`), and no handler reads `_envelope.actor_id`.
   Every MCP mutation is therefore attributed to `None`/"human" by construction — a
   safety/audit seam adjacent to D5 and §2's "actor_id/actor_type carried on the envelope".
5. **F-MCP-11's ungated-mutation set is incomplete.** `set_active_project` is registered
   `mutates=True` with no `confirm` (`registry.py:143`) and repoints the process-global
   active project that every subsequent mutating tool acts on — a comparable
   safety-relevant ungated mutation not cited. (Measured: `set_active_project`
   mutates=True, confirm=False; `create_film_project` likewise.)
6. **F-MCP-12 cites two of three `next_version` copies.** The reproduce grep
   `grep -rn "next_version = (" src/film_pipeline/mcp/` returns **three** sites —
   `bibles/_shared.py:124`, `bibles/shot.py:71`, `planning.py:74` — the audit names two.
   Cosmetic, but the §1.6.4 count is incomplete.

## Disputes requiring the author to fix

1. **F-MCP-09 duplicates F-CFG-08 and F-CRP-09, with three different candidate owners.**
   `audit/03-config-profile-and-defaults.md:373-400` (F-CFG-08) already reports the
   `FILM_PIPELINE_NO_PERSIST` re-derivation across the same six modules and nominates
   `app/_persistence`; `audit/10-checkpoints-and-runtime-persistence.md:817-850` nominates
   a new `runtime_persistence` with `resolve_persistence()`. F-MCP-09 nominates extended
   `app.bootstrap` and cites none of them (its "Prior art" is the unrelated
   `audit-findings.md:146`). One concern, three owners — this is the most serious
   program-level defect in the file.
2. **Candidate-owner collision on env access.** Extended `app.bootstrap`'s guard
   ("no module other than `app/_persistence.py` reads `FILM_PIPELINE_PERSIST_STATE`/
   `FILM_PIPELINE_NO_PERSIST`") conflicts with `config`'s invariant 5
   (`audit/03:722-760`: "`FILM_PIPELINE_*` configuration variables are read in exactly one
   module", with a new `config.environment` accessor replacing `app/_persistence.py:41`).
   Both cannot be the single raw-env reader; the split of mechanism (`config.environment`)
   vs policy (`_persistence`) must be stated in both files. `mcp.policy` itself is
   coherent and collision-free (`01-ownership-map.md:227` already endorses it).
3. **`langgraph.json:3` anchor is wrong** — line 3 is `"graphs": {`; the quoted entry is at
   `langgraph.json:4`. §1.6.1 requires the anchored line, not the enclosing block.
4. **F-MCP-04's mutation site is wrong** — `qc.py:364` is the `gen_planning` arm; the
   `shot_bible` validator membership lives in `_run_continuity_validators`
   (`qc.py:311-328`). Also, `tests/unit/graph/test_qc_validator_dispatch.py:75-107` pins
   the phase sets, so only the validator-class version of the mutation is silent; drift is
   4, not 5 (score 16, still Critical).
5. **F-MCP-01 overstates two things** — (a) `checkpoints.py:249-301` is unreachable through
   `MCPServer.call` (the gate at `server.py:64-66` returns before `_dispatch_handler` at
   :67), so the two contracts only diverge on the F-MCP-02 bypass paths; (b)
   `approve_profile_change`'s confirmation **is** enforced at the product boundary
   (`registry.py:348-354` + `server.py:187`), so "not enforced by the tool at all" is false
   — the docstring is imprecise about the enforcing layer, not documenting an absent gate.
6. **F-MCP-11's "4 tools … registered `mutates=True`/`confirm=True`" is wrong** — measured:
   `plan_coverage_group` mutates/no-confirm, `list_coverage_groups` and
   `inspect_coverage_group` read-only, `approve_coverage_generation` mutates+confirm.
   Only two of the four stubs are mutating. The O5 label is also weak for a *missing*
   classification (O8 is closer); the substance (ungated `resolve_provider_block`) stands.
7. **F-MCP-12's `O7` sub-label is unsupported** — both writers use the `ArtifactStore`
   public API (`_shared.py:138` → `store.save`, `graph/nodes/visual.py:52` →
   `_save_artifact`); neither reaches into the
   other's private state. O6 (+O1 for duplicated version arithmetic) is the correct class.
8. **F-MCP-09's test-evidence sentence is misleading** — `grep -rn "use_persistent_runtime"
   tests/` is indeed `test_logging_setup.py` only, but `tests/unit/test_entrypoints.py:12-39`
   exists and pins the CLI `persist_enabled=True` literal and the MCP
   `configure_logging(root)` call. The drift proof still holds (a new `_persistence` flag
   fails nothing), but the file must cite this test, since it actively pins the *divergent*
   CLI derivation and would have to change with any fix.

## Overall verdict

**Bar A6 not met as written**: F-MCP-05's headline drift proof is false and F-MCP-06 is
over-severity; the remaining ten findings are CONFIRMED (two with score/anchor
corrections), the core F-MCP-02 safety bypass and F-MCP-03 empty-schema defect are
mechanically proven, and the file additionally misses five adjacent MCP-surface seams —
fix the eight disputes above and it passes.
