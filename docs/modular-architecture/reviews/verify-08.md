# verify-08 — adversarial verification of `audit/08-validation-and-review.md`

- **Verifier:** independent agent (did not write the audit), bar A6.
- **Repo:** `${REPO_ROOT}`, branch `modular-app`, HEAD
  `fb85baa0e6b769b709791a96a89980089304bf13`; `git status --porcelain` empty.
- **Method:** every `path:line` in the audit re-resolved at HEAD (187 distinct anchors, 0 out of
  range); 101 audit quotes checked byte-wise at their cited lines (100 verbatim; the 1 exception is
  the `orchestrator_state.py:156-159` quote-join, see disputes). Drift proofs re-run with throwaway
  scripts (`/tmp/anchors.py`, `/tmp/quotes.py`, `/tmp/vr01.py`, `/tmp/vr02.py`, `/tmp/vr04.py`,
  `/tmp/sweep.py`) using `.venv/bin/python`. No repo file other than this one was written.

## Verdict table

| finding | verdict | one-line reason |
|---|---|---|
| F-VR-01 | CONFIRMED | `/tmp/vr01.py` reproduces exactly: `scene-writing-validator DIFFERS ['blocking_conditions']`, `delivery-completeness-validator ABSENT`, other five `AGREES`; no test imports both populations |
| F-VR-02 | CONFIRMED — **correction required** | empty `[block_below, review_at)` band and dead rule-6 tier reproduce (`/tmp/vr02.py` → `[]`), but the §2.4 absolute verdict is false: the LLM path *can* mint `needs_revision` (see expanded) |
| F-VR-03 | CONFIRMED — dispute | both lifecycles and all live call sites verified (`graph.py:115` vs `_repair_loop.py:47`/`_graph_exec.py:337,452`); mutation claim understated by `test_qc_validator_dispatch.py` (see disputes) |
| F-VR-04 | CONFIRMED | `/tmp/vr04.py`: dict input → `AttributeError: 'dict' object has no attribute 'validator_id'`, swallowed at `nodes/qc.py:176-177`; 0 tests touch the helper |
| F-VR-05 | CONFIRMED — **severity recomputed** | two writers + unwritten router key verified, but writer A can never succeed (F-VR-04), so the live race is latent → **High 3×4=12**, not Critical 16 |
| F-VR-06 | CONFIRMED — count dispute | test-side replica at `test_real_human_gates.py:153-174` confirmed; "six sites" is wrong — the finding enumerates seven |
| F-VR-07 | CONFIRMED — nuance | four tables verified and delivery absent from both QC paths; "MCP table runs delivery" holds only via the read-side fallback, not the registered `run_validation` tool |
| F-VR-08 | CONFIRMED | `grep -rn "blocking_conditions\|warning_conditions" src` = 46 hits, 0 read sites; mutation is silent |
| F-VR-09 | CONFIRMED — **drift proof falsified** | typed package has one construction site, but the claimed "fails loudly" on the MCP path is false — it is swallowed (see expanded) |
| F-VR-10 | CONFIRMED | `ApprovalRecord`/`RevisionRequest` have 0 constructions (def + 2 exports only); `"approve_phase"`/`"revise"` accepted but absent from `ApprovalAction`; `"reject"` unhandled |
| F-VR-11 | CONFIRMED — **severity mislabeled** | seam real, but `2×3=6` is **Medium** under §1.5 (4–8), not Low |

**Totals: 7 CONFIRMED, 4 CONFIRMED-with-correction, 0 REJECTED.** 187 anchors + 101 quotes + 3
reproduce scripts; every reproduce block the audit printed produced the documented output.

## Expanded rows (corrections and recomputed severity)

### F-VR-02 — validator claim stands; the §2.4 "not reachable end-to-end" verdict does not

Counter-evidence (`grep -rn "NEEDS_REVISION" --include=*.py src`, 11 hits, all opened):

- `src/film_pipeline/agents/impl/qc_synthesis_agent.py:66` —
  `consensus_status=ValidationStatus(str(data.get("consensus_status", "pass")))` and `:56`
  `status=ValidationStatus(str(r.get("status", "pass")))`. `"needs_revision"` is a valid
  `ValidationStatus`, so a model output selecting it **mints** `NEEDS_REVISION` on a live path
  (`_synthesize_consensus_report` → `_run_agent("clip-validator")`, `graph/nodes/qc.py:97-112`).
- That report is persisted as a first-class artifact (`nodes/qc.py:109`) and the artifact type is
  registered with a renderer that prints the status verbatim:
  `artifacts/registry.py:171-174` → `artifacts/rendering.py:164-170`
  (`for key in ("consensus_status", ...)`). So `needs_revision` **can reach a human-viewable
  artifact**; it simply never reaches the router.
- `consensus.py:92-93` and `:98` are pass-throughs gated on an input status/`ERROR` that no validator
  can emit, so they are not independent producers — the audit is right there.
- `_action_routing.py:287` is read-side.

The audit's own §2.4 sentence acknowledges the `qc_synthesis_agent.py:66` producer but dismisses it
with "never read back into the router key". That is true for routing and false for observability.
Separately, "Repairable findings route to repair behavior is unmet" is overstated: a repairable
score now lands in `BLOCKED` (entry `block_below == review_at`) and rule 6 still returns
`handle_blockers` with `eligible=["repair", ...]` (`_action_routing.py:283-286`), so repair is
reached; what is dead is the `revise` tier and the `needs_revision` label.

**Required fix:** retitle the §2.4 verdict to "no validator can emit `NEEDS_REVISION`, and the
router's consensus/`revise` tier is dead" and drop "not reachable end-to-end". Impact 4 × drift 5 =
20 (Critical) is otherwise defensible and is left unchanged.

### F-VR-05 — CONFIRMED evidence, severity recomputed Critical 16 → High 12

- Two writers verified: `graph/nodes/qc.py:180-182` (algorithmic) and `:107-111` (LLM agent).
- Router reader verified: `_action_routing.py:110` reads `state["consensus_report"]`;
  `grep -rn consensus_report src/film_pipeline/graph/orchestrator_state.py` → 0 rows, and the key is
  not in `StudioGraphState`; only `consensus_report_ref` is (`state_schema.py:157`).
- **Counter:** writer A cannot succeed at HEAD — `ConsensusBuilder().build(reports, ...)` always raises
  on the dict payload (F-VR-04, reproduced), so `consensus_report_ref` is written by writer B alone.
  The "last writer wins / human sees whichever ran last" consequence is therefore latent, not live.
  The live defect is the unwritten reader key (impact 3: wrong internal routing, recoverable), with
  drift 4 (no test can fail; `test_router_validation_status.py:77-80` hand-injects the key).
  Recomputed **3×4=12 = High**. If the author intends severity to cover the post-F-VR-04 world, say
  so explicitly; §1.5 grades HEAD.

### F-VR-09 — drift proof counter-evidence (`fails loudly` is false)

`src/film_pipeline/mcp/tools/review.py:44-59`:

```
    try:
        generator = ReviewPackageGenerator()
        pkg = generator.build(
        ...
    except Exception:
        return None
```

and the only caller degrades silently:

```
    pkg = _build_review_package(...)
    if pkg is None:
        # Fallback to simple artifact list if generator fails
        return _ok(artifacts=artifact_list, phase=phase)
```

`mcp/tools/review.py:103-106`. A new required `ReviewPackage` field therefore does **not** "fail
loudly" on the MCP path; the typed package is silently replaced by a bare artifact list. The
underlying seam (graph gate shows an ad-hoc dict, typed `ReviewPackage` has exactly one construction
site) is CONFIRMED and the severity Medium 2×4=8 stands, but the drift proof as written is wrong: the
MCP surface degrades quietly too, so the real drift is *both* representations silently collapsing,
not one failing loudly. (The separate F-VR-06 drift proof is unaffected — `review/actions.py:49-55`
still advertises `approve_phase` for the predicate mutation described there.)

### F-VR-11 — severity mislabeled (§1.5 arithmetic)

Audit: "Low (impact 2 × drift 3 = 6)". §1.5: High 9–15, Medium 4–8, Low 1–3. `6` is **Medium**.
The evidence is otherwise CONFIRMED: `base.py:286-290` writes `requires_human_review`,
`thresholds.py:37-40` duplicates the predicate, `schemas/validation.py:45` declares the field, and the
only callers of `is_blocking`/`needs_human_review` are `tests/unit/validation/test_thresholds.py`
and the `validation/__init__.py:12-16` re-export. **Recomputed: Medium (2×3=6).**

## Missed in scope (new seams, same cluster)

**M1 — `consensus_report_ref`/`qc_patch_ref` bypass the channel registry via a private key list (O5-ish).**
`graph/nodes/qc.py:30` declares `_QC_REF_KEYS: tuple[str, ...] = ("consensus_report_ref", "qc_patch_ref")`
and `:42,61-64` copies them into the node update by hand. Both keys are in `StudioGraphState`
(`state_schema.py:157,167`), yet neither is in `ORCH_CHANNELS` (`orchestrator_state.py:93-165`) nor in
the parity test's sweep scope (`test_channel_registry.py:35-37`,
`{"artifact_refs","generation_requests","_qc_reports","_qc_raw_reports"}`). Reproduced with
`/tmp/sweep.py`:

```
'consensus_report_ref': in ORCH_CHANNELS=False in sweep_scope=False in GraphState=True
'qc_patch_ref':         in ORCH_CHANNELS=False in sweep_scope=False in GraphState=True
```

This directly contradicts `_agent_handoff.py:9-12` ("Which keys cross the node boundary … is owned by
`ORCH_CHANNELS`. This module contributes no key names of its own") and `test_channel_registry.py:200-205`
("No hidden local key lists"). It is the *registration half* of the `consensus_report_ref` concern
that F-VR-05 owns, so it belongs in this audit (or as a blocking cross-reference to the graph-state
cluster). The AST writer sweep cannot see it either: `_collect_updates` writes `updates[key]` (a Name
subscript, not a Constant), so the guard is structurally blind to this shape.

**M2 — `validation_refs` vs `validation_report_refs`: split authority, and the registered channel has no writer (O3).**
`mcp/tools/validation.py:275` — `active.setdefault("validation_refs", []).extend(saved_refs)`.
`validation_refs` is **not** in `StudioGraphState`; the registered append-only channel is
`validation_report_refs` (`state_schema.py:173`, `orchestrator_state.py:163`), and
`grep -rn "validation_report_refs" src/film_pipeline/graph/` finds **no writer** (only the schema,
the channel row, the handoff docstring, and the `_graph_exec.py:470` reducer map). The audit's own
§4.3 even lists `validation_refs` as owned state but files no finding for it.

**M3 — consensus artifacts are silently persisted with `artifact_type = script` (O1/O8).**
`graph/nodes/qc.py:88` passes `artifact_type="consensus_report"` when saving a **`MatrixPatch`**.
`"consensus_report"` is not an `ArtifactType` member (`schemas/_base.py:27-75`), so
`_agent_artifacts.py:36-39` swallows the `ValueError` and returns `ArtifactType.SCRIPT`. Verified by
direct call: `MatrixPatch + artifact_type=consensus_report -> script`, and
`_infer_artifact_type(ConsensusReport()) -> script` because `_context.py:310` maps
`"ConsensusReport" -> "consensus_report"` — again not an enum member. Consequence: the registered
`consensus_report` artifact spec/renderer (`artifacts/registry.py:171-174`) can never fire, and both
the QC matrix patch and the consensus report are stored mislabeled as scripts. The audit read
`nodes/qc.py` in full and cited `:68-92` in F-VR-03, but filed nothing.

**M4 — `run_validation` cannot reach the phases its own dispatch table declares (O4/O5).**
`mcp/tools/validation.py:297-306` dispatches only `visual_dev` and `script`; every other phase returns
`"No validators found for this phase."` Yet `_live_validator_specs` (`:123-158`) declares arms for
`gen_planning`, `shot_bible`, `post/assembly`, and `delivery`, and `run_validation` is the *registered
mutating tool* (`mcp/tools/registry.py:240`). Those arms are reachable only through
`get_validation_report`'s live fallback (`:345`). This weakens F-VR-07's claim that delivery runs
through the MCP table.

**M5 — a covering test for the sequential dispatch table was omitted from scope.**
`tests/unit/graph/test_qc_validator_dispatch.py` (107 lines) imports `graph.nodes.qc` and pins
`_VALIDATOR_RUNNERS` per phase, including the id `"qc-covers-upstream-but-not-delivery"` (`:85-90`).
It is absent from the audit's §1.1 test table and from F-VR-03/F-VR-07's "no test fails" reasoning;
it codifies the very coverage delta the findings report.

## Disputes requiring the author to fix

1. **§1.2 counts are not reproducible (§1.6.4).** `grep -rn "NEEDS_REVISION" --include=*.py src`
   returns **11**, not 13, and they are **not** "all read-side": `thresholds.py:28`,
   `consensus.py:93`, `consensus.py:98` *produce* the status.
   `grep -rn '"blocking"' --include=*.py src` returns **59**, not 27. `ValidatorRegistryEntry(`
   returns 23 (the 23rd is `class ValidatorRegistryEntry(SchemaBase):`; 22 literals is right).
   `review_at` across `*.py .` is 26, not "22 + schema default" (the read site `thresholds.py:25` and
   2 test tuples are also hits). Fix the comments or the commands — not the repo.
2. **F-VR-02 §2.4 verdict** must drop the absolute "not reachable end-to-end" claim (see expanded).
3. **F-VR-09 drift proof** must drop "fails loudly" (see expanded).
4. **F-VR-11 severity** must read Medium (2×3=6), not Low.
5. **F-VR-05 severity** should be recomputed to High (3×4=12) or the impact-4 rationale stated for a
   dead writer.
6. **F-VR-06 count**: the title/concern/§4.1 say "six sites/derivations"; the owner list enumerates
   seven (three inside `approval.py` alone: `:113-119`, `:221-224`, `:249-251`). Pick one number.
7. **F-VR-07**: qualify the "delivery validator runs at the `delivery` phase through the MCP table"
   sentence — that is true only for `get_validation_report`, not for `run_validation` (M4).
8. **F-VR-03/F-VR-07**: soften "no test fails" — `test_qc_validator_dispatch.py` pins the sequential
   table, so a partial edit to that table is caught; what stays unguarded is cross-path agreement.
9. **Evidence formatting**: the `orchestrator_state.py:156-159` quote drops the literal quotes around
   `"_validation_reports"` (§1.6.2 requires verbatim). Trivial, but §1.6.2 is non-negotiable.
10. **Double-counting check**: F-VR-03 and F-VR-07 share the same subgraph-vs-sequential evidence and
    nominate near-identical owners (`validation/runtime.py` vs `validation/dispatch.py`). Keep both
    only if the reconciliation explicitly says which invariants each kills; otherwise merge.

## Overall verdict

**Substantively sound and unusually well-anchored: 0 of 11 findings rejected, every reproduce block
reproduces, and the two highest-stakes claims (empty `NEEDS_REVISION` band; consensus never built)
are literally true — but four rows need correction (one overstated absolute, one false drift proof,
one severity mislabel, one miscount) and the audit missed five seams in its own cluster, the sharpest
being the silently-swallowed `artifact_type="consensus_report"` → `script` coercion at
`graph/nodes/qc.py:88` and the unregistered `consensus_report_ref`/`qc_patch_ref` boundary keys at
`graph/nodes/qc.py:30`.**
