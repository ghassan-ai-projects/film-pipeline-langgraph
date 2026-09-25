# 02 — Consolidated Duplication Ledger

> **Review status (2026-09-25): unreconciled historical ledger.** This file maps
> 178 live findings and explicitly defers 11 later additions. Subsequent
> `verify-15`–`verify-20` verdicts are not fully applied. In particular,
> `verify-19` **rejects** `F-ARTIFACT-13`, which this ledger still counts under
> L-18. Do not use its 58-concern total, severity ranking, or verification
> labels as a current execution priority. See [06](06-independent-review-and-decision.md).

Status: **synthesis of the 14 cluster audits under bar A8, reconciled against all
14 completed independent verifications.** This is the one deduplicated, ranked,
evidence-anchored list of ownership seams for `film-pipeline-langgraph` at
baseline `fb85baa` (`modular-app`).

Sources consolidated, and nothing else:

| Source | Role here |
|---|---|
| `00-methodology-and-quality-bar.md` | normative definitions, O1–O8, severity rubric §1.5, evidence rules §1.6, **bar A8** |
| `01-ownership-map.md` | concern-centric ownership map this ledger must stay consistent with |
| `reconciliation-notes.md` | cross-source corrections, **R1 artifact-kind counts** (applied in L-18) |
| `audit/01..14-*.md` | **178 live findings + 1 withdrawn hypothesis** mapped in this revision (189 on disk — see the revision note), deduplicated here by **concern**, not by finding id |
| `reviews/verify-01..09,11..14.md` | independent per-finding verdicts; supersede audit claims (reconciliation R4) |
| `reviews/orchestrator-verification-notes.md` | the orchestrator's own reproductions (V1–V10); source of the L-02/L-14/L-48 corrections below |
| `reviews/program-process-record.md` | the fix-loop record (which audits were corrected, what was withdrawn/added) |
| `enola-architecture-facts.md` | machine-measured coupling (5 cycles, fan-in/out, exported surface) |

Baseline: `fb85baa0e6b769b709791a96a89980089304bf13`, clean tree. `make ci-check`
verified green at this commit (2003 passed / 8 skipped, 91.58 % coverage).

**Scope of this file.** One entry per ownership *concern*. A concern reported by
two or three clusters of findings is merged into a single entry with all
constituent finding ids listed; severity is the concern's worst case under §1.5
(impact × drift), **after** any verifier severity correction. The appendix maps
every finding in the mapped scope to its entry, so no finding is dropped and none is
counted twice; findings that landed after this revision's measurement are named under
"Deferred to the second sync" rather than silently omitted. One withdrawn hypothesis
is quarantined in §(d) and is **not** a concern.

> **Revision note — sync 2 (audit 10 fix loop).** This revision is synced against
> **`audit/10-checkpoints-and-runtime-persistence.md` at its post-verification revision**
> (now **16 findings**, `F-CRP-01`…`F-CRP-16`, with the five verifier missed seams
> `F-CRP-12`…`F-CRP-16` promoted to full findings) and against `reviews/verify-10.md`,
> which landed after revision 1 and makes all 14 verifier files complete. Totals in this
> revision: **178 live findings + 1 withdrawn** (the 173 of revision 1 plus the five
> audit-10 additions), **40 Critical / 91 High / 46 Medium / 1 Low** at finding level
> (restated after the §1.5 band corrections — see the band-check output below; the
> pre-correction reading was 39/88/50/1),
> **147 verified** and **31 unverified** (the 26 of revision 1 plus `F-CRP-12`…`F-CRP-16`).
> Audit 10 is the only finding set re-mapped here; every other audit's mapping is unchanged.
> Because the remaining coverage-closure seams are still landing in the other audits
> (**11 further live findings were already on disk, in audits 02/03/04/05/06/07/09/14, at the
> measurement moment**), a **second sync will follow**. Those findings are named under
> "Deferred to the second sync" in the appendix and are deliberately **not** mapped here.

**Severity bands are a function of the score — `00-methodology-and-quality-bar.md` §1.5,
normative.** The band is derived from the score, never the reverse: `Critical ≥ 16`,
`High 9–15`, `Medium 4–8`, `Low 1–3`, where `score = impact × drift`. A verifier who
disagrees with a band must change the *axes*; a recorded band that contradicts its own
recorded score is a self-contradiction, not a judgement call. This rule was made normative
in round 3, after a mechanical sweep of all 189 findings found **five** such
self-contradictions — every one a verifier band word disagreeing with its own recomputed
score: `F-CRP-05` (Medium, 3×3=9 → High), `F-CRP-13` (High, 4×4=16 → **Critical**),
`F-BOUNDARY-02`, `F-BOUNDARY-03` and `F-BOUNDARY-06` (each Medium, 3×3=9 → High). Where
this ledger's band differs from an audit's band *word*, it is applying this rule and says
so inline (`L-43`, `L-48`, `L-54`); it is not expressing a preference. The audit authors
have since corrected all five. That the same relabelling error was made independently by
several agents is the argument for checking the corpus with an invariant rather than by
review — the command and its current output are stated below.

**Verification legend (R4).** Verdicts are taken verbatim from
`reviews/verify-NN.md`; the files use this vocabulary:

| Verdict | Meaning here |
|---|---|
| `CONFIRMED` | verifier reproduced the finding; evidence and severity stand |
| `CONFIRMED-WITH-FIX` | substance confirmed, specific anchor/count/drift clause must be corrected |
| `CORRECTED` | substance stands but the printed numbers/mechanism were wrong (may be worse or milder) |
| `STRENGTHENED` | verifier found the divergence is broader than the audit claimed |
| `DOWNGRADED` | severity, scope or drift proof reduced; entry severity reflects the downgrade |
| `WITHDRAWN` | finding removed from the live set for lack of a valid §1.6.3 drift proof |
| `PENDING VERIFICATION` | no verifier file covers the finding, or it was added/revised after its audit was verified (the 31 findings listed in the verification section) |

## Verification outcomes

**Fourteen verifier files exist at HEAD — `verify-01`…`verify-14`, complete.**
`verify-10.md` landed after this ledger's first revision; audit 10 is now
independently verified and the four checkpoint concerns (`L-11`, `L-21`, `L-22`,
`L-42`) are no longer pending. Aggregate:

- **147 findings independently verified** across all 14 verifications: the 136
  finding-verdicts of audits 01–09 and 11–14 at their original finding sets, plus
  audit 10's 11 (verify-10 landed last). The remaining **31 live findings are the
  post-verification additions** made during the fix loops, which by construction
  have no verifier verdict and are listed explicitly below.
- **Zero findings REJECTED.** No verifier overturned a finding outright. One
  finding, `F-TEST-02`, was **downgraded twice and then WITHDRAWN** by its own
  author during the fix loop (`audit/13` header, `reviews/verify-13.md` §F-TEST-02),
  and is quarantined in §(d).
- **~20 severity downgrades**: `F-OST-02` (15→12), `F-CFG-01` (16→12),
  `F-CFG-02` (25→16), `F-AGENT-02` (20→15), `F-GEN-07` (12→6), `F-GEN-08` (12→9),
  `F-KBCTX-04` (9→8), `F-KBCTX-05` (16→12), `F-KBCTX-06` (12→6),
  `F-KBCTX-07` (12→8), `F-MCP-05` (16→12), `F-MCP-06` (12→8), `F-POST-06` (12→8),
  `F-CRP-05` (12→9), `F-CRP-10` (12→6),
  `F-ARTIFACT-03` (12→8), `F-ARTIFACT-07` (16→12), `F-ARTIFACT-08` (12→8),
  `F-ARTIFACT-09` (9→6), `F-VR-05` (16→12), `F-TEST-01` (15→12),
  `F-TEST-02` (10→4→withdrawn).
- **Two severity upgrades**: `F-ARTIFACT-05` (12→**16 Critical**) and
  `F-ARTIFACT-01` (corrected upward within the Medium band, 6→8).
- **One STRENGTHENED**: `F-CFG-03` (verifier found an existing divergence the
  audit missed).
- **~6 class corrections**: `F-ARTIFACT-06` O3→O2/O5, `F-ARTIFACT-07` O3→O6/O2,
  `F-KBCTX-06` O6→dead policy, `F-MCP-06` O3 label dropped, `F-VR-11`
  Low→**Medium** under §1.5, plus the `F-PHASE-10` scope reduction
  ("three tables" → two).
- **5 CONFIRMED-WITH-FIX** (`F-OST-01/07/08/11/16`) all in audit 02.
- **31 live findings remain unverified**: the findings added *after* their audit
  was verified, during the fix loop. Audit 10's 11 *original* findings are **not** in
  this set — `verify-10` verified them (11 CONFIRMED, 0 rejected, 2 with severity
  recomputed) — but the five seams audit 10's own fix loop then promoted
  (`F-CRP-12`…`F-CRP-16`) **are**, because no verifier has seen them.
  Measured by absence from the corresponding `verify-NN.md` (any mention counts as
  coverage): `F-AGENT-11/12`; `F-PHASE-11`; `F-OST-17`; `F-PROV-08`;
  `F-GEN-14/15/16`; `F-ARTIFACT-10/11/12/13`; `F-VR-12/13/14/15`;
  `F-KBCTX-11/12/13`; `F-MCP-13/14/15`; `F-BUD-06`; `F-TEST-09/10/11`;
  `F-CRP-12/13/14/15/16`. The audit files flag most of these "(added after
  verification)"; `F-PROV-08`, `F-VR-12/13/14/15`, `F-ARTIFACT-10` and the five
  `F-CRP-12`…`F-CRP-16` are later revisions of the same fix loop. None carries a
  verifier verdict, so every one is **PENDING VERIFICATION**.
- **Finding counts moved during the fix loop, and were still moving while this ledger was written.**
  `orchestrator-verification-notes.md` V5 recorded **163 live findings (38 Critical, 83 High, 41
  Medium, 1 Low)**; revision 1 of this ledger then measured 173. **This revision's mapped total is
  178 live findings (40 Critical, 91 High, 46 Medium, 1 Low)** — revision 1's 173 plus audit 10's
  five new findings `F-CRP-12`…`F-CRP-16`, with the four `Medium → High` and one
  `High → Critical` §1.5 band corrections applied (the pre-correction reading, which is what
  `orchestrator-verification-notes.md` V10 recorded, was 39/88/50/1).

  **The mapped scope is not the whole corpus.** At this revision's measurement moment
  (**2026-09-25T14:07Z**, restated after the band corrections) the on-disk corpus had already
  grown to **189 live findings (41 Critical, 101 High, 46 Medium, 1 Low)**: the audits are
  being edited by other agents
  *while this file is being written*, and a further **11 coverage-closure findings** had landed
  in audits 02, 03, 04, 05, 06, 07, 09 and 14 on top of the audit-10 delta. Those 11 belong to
  the **second sync**, are named in the appendix under "Deferred to the second sync", and are
  deliberately not mapped to concerns here. The arithmetic reconciles exactly:
  `178 mapped + 11 deferred = 189 on disk`.

  Reproduce the mapped scope from the file itself: `grep -c '^### F-' audit/*.md` minus the two
  `F-TEST-02` withdrawal stubs gives 189 live *headers*; subtract the 11 named deferred ids to
  get 178. `grep -h '^- \*\*Severity:\*\*' audit/*.md | wc -l` gives **189** for the whole corpus
  and **178** for the mapped scope. This ledger carries **178/178 + 1 withdrawn of the mapped
  scope**, with the 11-deferred delta stated rather than hidden.

  Because the audit files are edited concurrently with this synthesis, the finding-level numbers
  above are a **snapshot at 2026-09-25T14:07Z**; the concern-level structure (58 entries) is
  invariant to additions, since a new finding joins an existing concern rather than creating one.
  Where a later audit revision adds a finding this ledger does not yet list, the entry's
  `Consolidates` line is the authority to re-check, not the count.
- **Verifiers surfaced ~30 seams the audits had missed** (V6), of which the 31
  post-verification additions above are the ones promoted to findings — the five
  `F-CRP-12`…`F-CRP-16` are the audit-10 batch of them. A ninth note
  (V9) then corrected this program's own evidence: the orphaned `test_guard_canary`
  bytecode is ours, not a historical loss — see `L-47`'s anti-rot paragraph.

Verification files consulted: `reviews/verify-01.md`, `reviews/verify-02.md`,
`reviews/verify-03.md`, `reviews/verify-04.md`, `reviews/verify-05.md`,
`reviews/verify-06.md`, `reviews/verify-07.md`, `reviews/verify-08.md`,
`reviews/verify-09.md`, `reviews/verify-10.md`, `reviews/verify-11.md`,
`reviews/verify-12.md`, `reviews/verify-13.md`, `reviews/verify-14.md`, plus the
orchestrator's own `reviews/orchestrator-verification-notes.md` (V1–V10).

**Mechanical band check — run this, do not trust the words.** Because the band is a pure
function of the score (§1.5 above), the corpus can be checked as an invariant:

```bash
UV_CACHE_DIR=$PWD/.uv-cache uv run python - <<'PY'
import pathlib, re
band = lambda s: 'Critical' if s >= 16 else 'High' if s >= 9 else 'Medium' if s >= 4 else 'Low'
bad = []; n = 0
for f in sorted(pathlib.Path('docs/modular-architecture/audit').glob('*.md')):
    cur = None
    for l in f.read_text().splitlines():
        if l.startswith('### F-'):
            m = re.match(r'### (F-[A-Z]+-\d+)', l)
            cur = None if ('withdrawn' in l.lower() or not m) else m.group(1)
        elif cur and l.startswith('- **Severity:**'):
            b = l.split('**Severity:**', 1)[1]
            w = re.search(r'\b(critical|high|medium|low)\b', b, re.I)
            s = re.search(r'=\s*(\d+)', b); n += 1
            if w and s and w.group(1).capitalize() != band(int(s.group(1))):
                bad.append((cur, w.group(1).capitalize(), int(s.group(1)), band(int(s.group(1)))))
            cur = None
print(f"parsed={n} violations={len(bad)}")
for v in bad: print("  %-16s recorded=%-9s score=%-3d correct=%s" % v)
PY
```

**Current output (measured `2026-09-25T14:07Z`): `parsed=189 violations=0`** — the round-3
five have all been corrected by their authors; `F-CRP-13` was the last, re-stated
`High → Critical` in `audit/10` with the reason given as §1.5 itself. The residual is
therefore **zero**, and this ledger knowingly leaves none outstanding. The count is a
timestamp, not a fact: while this revision was being written the residual moved
**5 → 3 → 0** within a few minutes as the audit files were edited. The four
`Medium → High` corrections and the one `High → Critical` correction have already moved
the finding-level severity mix, which is restated below at the same instant.

**Anti-pattern noted (V6), and it is evidence for this program's thesis.** The
threshold count `24 / 20` was duplicated across three synthesis/audit files at
once and was wrong in the same direction in all three, while a fourth file
(`audit/03` §2) had already corrected it. The AST ground truth for the corrected
figure is **23 `ValidatorThresholds(...)` constructions — 22 with literal values
and 1 bare default** — where the `22` is the literal count and the `18` is the
number sharing the majority triple `(85, 75, 75)` (the other five being
3×(80,70,70) and 1×(90,80,80)); the `24` originally came from a `grep` that also
matched the class definition and its `Field` declarations. A number with three owners
and no guard drifted exactly the way the phase, budget and validator vocabularies
drift — a documentation-scale rehearsal of the failure this ledger exists to
retire.

---

## Executive table

Severity is the entry-level worst case **after** verifier correction; a
downgraded constituent is noted in the entry. `Verified?` is the entry's
aggregate status.

| Id | Title | Severity | O-class | Candidate owner | Verified? |
|---|---|---|---|---|---|
| L-01 | Budget state, caps, refusal gates and spend recording | Critical (5×5=25) | O3+O2+O5 | `budget` | CONFIRMED (F-BUD-06 pending) |
| L-02 | Agent→model-profile map is duplicated and already divergent | Critical (4×5=20; was 25) | O1+O5+**O4** | `agents.registry` | DOWNGRADED (F-CFG-02 25→16) |
| L-03 | Agent execution lifecycle: graph `PromptRunner` vs MCP bible path | Critical (5×5=25) | O6+O1+O5 | `agents.registry` | CONFIRMED (F-KBCTX-07 ↓; F-AGENT-11 pending) |
| L-04 | Post-production models, `AssemblyAgent` and `assembly_manifest` | Critical (5×5=25) | O6+O1+O3 | `post-production` | CONFIRMED |
| L-05 | "Delivery complete" and the delivery-manifest seam | Critical (5×5=25) | O2+O8 | `delivery` | CONFIRMED (F-POST-06 ↓) |
| L-06 | Phase advancement / successor, app path skips provider gate | Critical (5×4=20) | O6+O1 | `phase-model` | CONFIRMED |
| L-07 | Agent declared contract vs registered implementation | Critical (5×5=25) | O1+O8+O4 | `agents.registry` | MIXED (F-AGENT-02 ↓ 20→15) |
| L-08 | Generation job lifecycle: submit → poll → complete | Critical (5×4=20) | O6+O8+O1 | `generation-runtime` | CONFIRMED (F-MCP-05 ↓) |
| L-09 | Provider health has four representations; routing reads the dormant one | Critical (4×5=20) | O3+O4 | `provider-health` | CONFIRMED (F-TEST-10 pending) |
| L-10 | Consensus construction and consensus report state | Critical (4×5=20) | O8+O3+O5 | `validation/consensus.py` | CONFIRMED (F-VR-05 ↓ 16→12; F-VR-13 pending) |
| L-11 | Run / runtime / storage / checkpoint roots resolved five ways | **Critical (5×5=25; was 20)** | O5+O3+O7 | `runtime_persistence` | CONFIRMED (verify-10); **`F-CRP-12` post-verification, pending** — corpus-maximum score |
| L-12 | MCP tool invocation lifecycle and the `app` ↔ `mcp` cycle | Critical (5×4=20) | O6+O8 | `mcp.dispatch` / `module-law` | CONFIRMED |
| L-13 | Validator registry and phase→validator dispatch | Critical (4×4=16) | O4+O3+O1 | `validation/registry.py` | MIXED (F-CFG-03 ↑, F-PHASE-10 ↓ scope, F-MCP-04 ↓ 20→16; F-VR-14/15 pending) |
| L-14 | Score→status thresholds; `NEEDS_REVISION` unreachable | Critical (4×5=20) | O1 | `validation/thresholds.py` | CONFIRMED / CORRECTED (F-CFG-04 worse, numbers fixed) |
| L-15 | Phase vocabulary, order and phase-keyed policy literals | Critical (4×4=16) | O1+O3+O4 | `phase-model` | CONFIRMED (F-PHASE-11 pending) |
| L-16 | Generation ledger state machine and generation-status grammar | Critical (4×4=16) | O3+O6+O1 | `generation-ledger` | CONFIRMED (F-ARTIFACT-07 ↓ 16→12) |
| L-17 | Two live QC lifecycles (subgraph vs sequential node) | Critical (4×4=16) | O6+O2 | `validation/runtime.py` | CONFIRMED |
| L-18 | Artifact kind ↔ `ArtifactType` vocabulary (R1-corrected) | Critical (4×4=16) | O1+O4+O2 | `artifacts.contract` | MIXED (F-ARTIFACT-08/09 ↓; F-ARTIFACT-11/13, F-VR-12, KBCTX-11/12/13 pending) |
| L-19 | KB packet construction and delivery to prompts | Critical (4×4=16) | O6+O3+O8 | `kb-context` | CONFIRMED (F-KBCTX-06 ↓) |
| L-20 | KB provenance: `kb_context_ref` stamping and `kbctx:` id grammar | Critical (4×4=16) | O3+O8+O1 | `kb-context` + `artifacts` | CONFIRMED (F-KBCTX-04/05 ↓) |
| L-21 | Checkpoint metadata registries and `artifact_versions` | Critical (4×4=16) | O3+O8 | `runtime_persistence.checkpoints` | CONFIRMED (verify-10; F-CRP-15 pending) |
| L-22 | Resume seam and duplicate resume implementations | Critical (4×4=16) | O8+O6 | `graph.resume_protocol` | CONFIRMED (verify-10; F-CRP-16 pending) |
| L-23 | MCP tool argument contracts are declared and never populated | Critical (4×4=16) | O8 | `mcp.contracts` | CONFIRMED |
| L-24 | Model-profile defaults declared in YAML and in code | **High (3×4=12; was Critical 16)** | O1 | `config` | **DOWNGRADED (F-CFG-01 16→12)** |
| L-25 | Provider-lineup parsing understands one of two profile shapes | Critical (4×4=16) | O1 | `config` | CONFIRMED |
| L-26 | "Stalled phase" has two representations and three thresholds | **High (3×4=12; was 15)** | O3+O5 | `graph/orchestrator_state.py` | **DOWNGRADED (F-OST-02 15→12)** |
| L-27 | Failure decisions and provider failure classification | High (3×5=15) | O8+O2+O5 | `provider-failure` + `graph` | CONFIRMED |
| L-28 | Provider registry and catalog/capabilities | High (3×5=15) | O4+O8+O1+O5 | `provider-registry` | CONFIRMED (F-PROV-08 pending) |
| L-29 | Credential resolution policy re-derived at 14 sites | High (3×5=15) | O2+O5 | `provider-credentials` | CONFIRMED (with corrections) |
| L-30 | Agent naming drifts into the KB manifest/defaults | High (3×5=15) | O4 | `agents.registry` | CONFIRMED |
| L-31 | Gate decision and the human-gate review package | High (3×5=15) | O5+O6+O8 | `validation/gate_policy.py` | CONFIRMED (F-VR-09 drift falsified) |
| L-32 | Number-word and scene-count grammar defined twice | High (3×5=15) | O1 | `constraints` | CONFIRMED |
| L-33 | Test doubles: canned payloads and mock provider entries | **High (3×4=12; was 15)** | O8+O1 | `testing.doubles` | **DOWNGRADED (F-TEST-01 15→12; F-TEST-02 withdrawn)** |
| L-34 | Phase→approval-gate map and gate mode | High (3×4=12) | O1+O2+O4+O5 | `phase-model` | CONFIRMED (F-OST-04 severity disputed ↑) |
| L-35 | `issues` contract, blocking predicate and approve veto | High (4×3=12) | O8+O2 | `graph/orchestrator_state.py` | CONFIRMED |
| L-36 | `app` re-implements the graph's channel reducers | High (3×4=12) | O4+O6 | `graph/state_schema.py` | CONFIRMED-WITH-FIX |
| L-37 | Prompt registry keyed from two id spaces | High (3×4=12) | O4 | `agents.prompt_templates` | CONFIRMED |
| L-38 | Artifact version / `schema_version` / status law | **Critical (4×4=16; was High 12)** | O5+O1+O2+O3 | `artifacts.contract` | CONFIRMED (F-ARTIFACT-05 ↑ 12→16; F-ARTIFACT-03 ↓; F-ARTIFACT-10/12 pending) |
| L-39 | Media paths, reference-asset catalog and generated-media policy | High (4×3=12) | O1+O4+O5 | `artifacts` / `generation-runtime` | MIXED (F-GEN-07 ↓ 12→6, F-GEN-08 ↓ 12→9; F-GEN-15/16 pending) |
| L-40 | Generation-request identity and stale-code sets | High (3×4=12) | O1+O4 | `generation-runtime` | MIXED (F-GEN-11 CONFIRMED; F-CRP-10 ↓ 12→6) |
| L-41 | Cost model: pricing table vs planner artifact ceiling | High (3×4=12) | O4+O5+O1 | `generation-runtime` | CONFIRMED (F-PROV-07 ↓ in part) |
| L-42 | Checkpoint history: rollback record, invalidation, audit, discovered projects | High (3×4=12) | O3+O1+O4+O6 | `runtime_persistence.rollback` | CONFIRMED (verify-10; F-CRP-14 pending) |
| L-43 | Persistence flags and entry-point bootstrap | **Critical (4×4=16; was High 12)** | O5+O3 | `runtime_persistence.policy` | MIXED (F-CFG-08/MCP-09/F-CRP-09 CONFIRMED; **F-CRP-13 post-verification, pending**) |
| L-44 | MCP confirmation enforcement and dangerous-mutation policy | High (3×4=12) | O2+O5 | `mcp.policy` | CONFIRMED |
| L-45 | `OperatorService` vs MCP and the two project registries | High (3×4=12) | O6+O3+O4 | `mcp.policy` / `ProjectCatalog` | MIXED (F-MCP-06 ↓ 12→8; F-MCP-14 pending) |
| L-46 | Profile-stack keys, writers and `resolved_review_strategy` | High (4×3=12) | O1+O3+O8 | `config` | CONFIRMED |
| L-47 | Test harness: store factory, fixtures, git double, separation guard, protocols | High (3×4=12) | O2+O1+O5+O8 | `testing.harness` | CONFIRMED (F-TEST-09/11 pending) |
| L-48 | Module dependency law, enforcement and private reach-ins | High (3×4=12) | O7+O8+O5 | `module-law` | CONFIRMED/CORRECTED (`verify-14`) |
| L-49 | Router action vocabulary vs the edge transition table | High (3×3=9) | O8 | `phase-model` | CONFIRMED (mutation clause false) |
| L-50 | Orchestrator key grammar and `_orchestrator__` literals | High (3×3=9) | O1+O7 | `graph/orchestrator_state.py` | CONFIRMED-WITH-FIX |
| L-51 | Four prompt renderers and two JSON-recovery strategies | High (3×3=9) | O2 | `agents.prompt_templates` | CONFIRMED (dispute) |
| L-52 | MCP error taxonomy bypassed; dead contract state | High (3×4=12) | O1+O8 | `mcp.contracts` | CONFIRMED (F-MCP-13/15 pending) |
| L-53 | `profiles/` location and hardcoded numeric defaults | High (3×3=9) | O7+O8+O5 | `config` | CONFIRMED |
| L-54 | `film_pipeline.testing` ships and is a cross-domain consumer | High (3×3=9) | O8+O7 | `testing` (contract) | CONFIRMED (`verify-14`) |
| L-55 | `next_action` → operator prose and routing-decision channels | Medium (2×4=8) | O5+O1+O3 | `graph/router.py` | CONFIRMED / CONFIRMED-WITH-FIX |
| L-56 | Ledger read path creates the ledger (write-on-read) | Medium (2×3=6) | O5+O7 | `generation-ledger` | CONFIRMED |
| L-57 | Ref-string formatter duplicated | Medium (2×4=8; was 6) | O1 | `artifacts.contract` | CONFIRMED (corrected upward) |
| L-58 | "Requires human review" derived twice | Medium (2×3=6) | O1 | `validation/thresholds.py` | CONFIRMED (mislabeled Low) |

Totals: **58 canonical entries** consolidating **178 live findings + 1 withdrawn
hypothesis** (plus the 11 deferred to the second sync, named in the appendix).
26 Critical, 28 High, 4 Medium, 0 Low at entry level. 47 entries are
**defects** (owners already disagree and behaviour is wrong today); 11 are **drift
risk** (owners agree today, nothing prevents divergence). **31 live findings remain
unverified** (26 added or revised post-verification, plus audit 10's five
post-verification additions `F-CRP-12`…`F-CRP-16`; audit 10's original 11 are
verified).

**Entry bands were re-counted, not assumed: 26 Critical / 28 High / 4 Medium / 0 Low**
(the four Medium entries are `L-55`, `L-56`, `L-57`, `L-58`). `L-54` is **already** High —
revision 1 recorded it that way under this same §1.5 rule — so the `F-BOUNDARY-06`
correction changes no entry band and no total; it only removes a self-contradiction at the
finding level. Four band changes now stand. From verification: **L-24 fell from Critical to High**
(`F-CFG-01` downgraded 16→12) and **L-38 rose from High to Critical**
(`F-ARTIFACT-05` upgraded 12→16). From the audit-10 sync: **L-11 rose from 20 to
Critical 25** — `F-CRP-12` is the highest-scoring finding this ledger carries, at the
corpus maximum of 5×5=25 (it ties `F-AGENT-04`, `F-BUD-01`, `F-POST-01`, `F-POST-02`
and `F-POST-04`, which are the corpus's other 25s) — and **L-43 rose from High to
Critical 16** (`F-CRP-13`, 4×4=16; see the band-convention note in that entry).
Four entries had their headline severity *lowered* by a downgrade (L-02, L-24, L-26,
L-33); each states the reason inline.

---

## Ranked ledger

**How to read the evidence in an entry (bar A2/A5).** Each entry below is a *consolidation*, not a
new finding: its **Consolidates** line names the audit findings it merges, and those findings carry
the anchors and reproduce commands that establish every number quoted here. Where an entry states a
count or an exclusivity ("eight gate sites", "zero production callers", "no test compares the two")
without an inline `path:line` or command, the evidence of record is the cited finding — one hop
away, in `audit/<NN>-*.md`. `reviews/anchor-check-02.md` §"UNANCHORED-CLAIM flags" lists the 32 such
lines explicitly so a reader can go straight to the finding that owns the number; that list is the
residual, and it is deliberate rather than hidden.

Two anchors in this file are worth the extra hop because they are the ones that are easiest to
mis-read: `mcp/tools/registry.py` and `mcp/tools/validation.py` both have a sibling `registry.py` /
`validation.py` elsewhere in `src/`, so a bare filename resolves to the wrong file. All bare
filenames in the ranked ledger were swept and corrected in revision 3
(`reviews/anchor-check-02.md`; 375 anchors resolved, 10 defects fixed).

### L-01 — Budget state, caps, refusal gates and spend recording
- **O-class:** O3 (split state authority) + O2 (duplicated invariant enforcement) + O5 (policy-by-branch).
- **Severity:** Critical (impact 5 × drift 5 = 25).
- **Verification:** CONFIRMED. `F-BUD-01`, `F-BUD-02`, `F-BUD-03`, `F-BUD-04` (verify-12: CONFIRMED ×4), `F-CFG-06` (verify-03: CONFIRMED), `F-OST-12` (verify-02: CONFIRMED); `F-BUD-06` is a post-verification addition → PENDING/UNVERIFIED.
- **Consolidates:** `F-BUD-01`, `F-BUD-02`, `F-BUD-03`, `F-BUD-04`, `F-BUD-06` (audit 12); `F-CFG-06` (audit 03); `F-OST-12` (audit 02).
- **What is wrong:** "What is the budget and may this spend proceed?" has no owner. Four-plus caps are derived independently (planning artifact, constraint extraction, config context, profile, plus the `context_packets` `budget_snapshot` key the owner never writes), the refusal rule is re-instated at eight gate sites of which only the ledger's `_raise_if_over_budget` can actually refuse, the graph gate always passes a ceiling derived from the planner's own estimate, and no spend is ever recorded so `remaining_usd` always equals the cap. The orchestrator's namespaced budget channel is written by `update_budget_snapshot` while the prompt reader consumes the un-namespaced key, so the planner is told "Budget cap: $0".
- **De-facto owners (strongest anchor):** `src/film_pipeline/mcp/tools/planning.py:33` — `budget = BudgetState(`; also `constraints/extractor.py:286-293`, `graph/nodes/_context.py:422-427`, `generation/ledger.py:264-277`, `graph/orchestrator_state.py:59`, `graph/context_packets.py:121`.
- **Drift proof (existing divergence):** set the cap to 100 via MCP and state "budget of $50" in the idea — the artifact says 100, `ProjectConstraints.budget_cap_usd` says 50.0, the prompt variable says whatever the profile holds, and the graph gate passes no ceiling, so the operator can authorise spend the project's own constraint forbids. (verify-12 reproduced the G1-only refusal and the inert graph gate.)
- **Candidate owner module:** `budget` — one `BudgetState` document, one `authorize_spend(project_id, batch)` and one `record_spend(...)`.
- **Guard test:** for every phase and every `(cap, spent)` pair, `authorize_spend` agrees with the ledger gate and the prompt block, and `record_spend` makes `remaining_usd = cap - spent` observable through `mcp/tools/planning.py:55`.

### L-02 — Agent→model-profile map is duplicated and already divergent
- **O-class:** O1 (duplicated normative model) + O5 (policy re-derived per call site) + **O4 (parallel registry, different cardinality)** — per `orchestrator-verification-notes.md` V2.
- **Severity:** Critical (impact 4 × drift 5 = 20). **Lowered from 25** because verify-03 corrected `F-CFG-02` from 25 to 16 (drift 5→4); the entry maximum is now `F-AGENT-01` at 20.
- **Verification:** MIXED. `F-CFG-02` CORRECTED (verify-03: CONFIRMED, score 25→16); `F-AGENT-01` CONFIRMED (verify-04); `F-AGENT-12` post-verification → PENDING/UNVERIFIED. The V2 reproduction below is the orchestrator's own.
- **Consolidates:** `F-CFG-02` (audit 03); `F-AGENT-01`, `F-AGENT-12` (audit 04).
- **What is wrong:** The declared agent contract carries `default_model_profile`, but the runtime ignores it and reads a hand-maintained `_AGENT_PROFILE_MAP` that is a *parallel registry of different cardinality*. The map has **21 rows**, and the orchestrator's V8 measurement decomposes them exhaustively: **11** name a registered `MVP_AGENTS` agent, **2** name a registered validator (`scene-continuity-validator`, `full-movie-flow-validator`), and **8 name nothing in either registry** — `character-dossier-agent`, `config-inference-agent`, `continuity-ledger-agent`, `environment-bible-agent`, `generation-scheduler-agent`, `kb-curator-agent`, `prompt-composition-agent`, `visual-dev-agent`; **5 of those 8 have zero references anywhere else in `src/`**. So **10 of 21 rows are not derivable from any registry** (2 validator rows + 8 phantom rows), and of the 11 agent rows that *are* legitimate, **2 carry the wrong value**: `intake-classifier-agent` declares `creative_writer` (`agents/mvp/__init__.py:40`) but runs `operations_triage`, and `structure-extractor-agent` declares `schema_enforcer` (`:96`) but runs `strict_validator`. The map is therefore not derivable from the roster by any mapping.
- **Cross-reference, not duplication.** Audit 04's `F-AGENT-12` (also folded into this entry) covers the 2 validator rows: they contradict both the validator roster and the validator implementations — `model_profile="multimodal_reviewer"` in the registry (`validation/validators/__init__.py:131`, `:151`) versus `strict_validator` in the map. V8 verified both citations and confirmed the reproduce command. That is the same seam seen from the validator side; it is stated once here and owned once by `agents.registry`.
- **Worse: the test suite actively locks in the wrong values.** `tests/unit/graph/test_agent_profile_routing.py:21` asserts `_AGENT_PROFILE_MAP["structure-extractor-agent"] == "strict_validator"` and `:25` asserts `_AGENT_PROFILE_MAP["intake-classifier-agent"] == "operations_triage"` — both pinning the divergent values as expected. Only `:35-40` is a value-blind membership check. Any fix must therefore change the tests as well.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/nodes/_context.py:27` — `_AGENT_PROFILE_MAP` definition (21 rows, of which 10 are unbacked); also `agents/mvp/__init__.py:40`, `:96`; `validation/validators/__init__.py:131`, `:151`.
- **Drift proof (existing divergence, reproduced by V2 and V8):** V8's `uv run python` import of the real objects printed `21 / 11 / 2 / 8` with the eight unbacked ids; V2 reproduced the two wrong agent rows. The real routing test file is `tests/unit/agents/model_routing/test_routing.py` (142 lines) and it does **not** compare the map with the roster, so changing `mvp/__init__.py:40` leaves the run on `_context.py:44` and every test green.
- **Candidate owner module:** `agents.registry` — one `AgentDescriptor.default_model_profile`, with the map strictly derived from (or deleted in favour of) it, and validator ids kept out of the agent map.
- **Guard test:** `for a in MVP_AGENTS: assert _AGENT_PROFILE_MAP[a.agent_id] == a.default_model_profile` — fails today on 2 rows; plus `set(_AGENT_PROFILE_MAP) == {a.agent_id for a in MVP_AGENTS}` (fails today on 10 extra keys) and `set(_AGENT_PROFILE_MAP.values()) ⊆ ModelRouter().list_profiles()`.

### L-03 — Agent execution lifecycle: graph `PromptRunner` vs MCP bible path
- **O-class:** O6 (parallel lifecycle) + O1 (duplicated contracts/prompts) + O5.
- **Severity:** Critical (impact 5 × drift 5 = 25).
- **Verification:** MIXED. `F-AGENT-04` CONFIRMED (verify-04: "pre-existing defect verified"); `F-KBCTX-07` **DOWNGRADED** to Medium 8 (verify-09); `F-MCP-12` CONFIRMED (verify-11); `F-AGENT-11` post-verification → PENDING/UNVERIFIED.
- **Consolidates:** `F-AGENT-04`, `F-AGENT-11` (audit 04); `F-KBCTX-07` (audit 09); `F-MCP-12` (audit 11).
- **What is wrong:** The graph runs agents through `PromptRunner` with a shared prompt registry, model router and mock policy; the MCP bible/assembly tools build their own contracts, call `model_adapter.chat` with an inline prompt and save artifacts with their own versioning. The MCP path calls `ModelRouter.resolve()`, which does not exist, and treats `chat()`'s `str` return as a mapping, so the real-model bible path cannot work (verify-04 confirmed 5 MCP bible tools raise `AttributeError`). Four MCP-only bible agents are invisible to the roster, and per-agent prompt policy is additionally re-derived by hardcoded identity branches in `_agent_prompt_context.py`.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/nodes/_agent.py:144` — `template = prompt_registry.get_required(agent_id)`; also `graph/nodes/_agent_artifacts.py`, `mcp/tools/bibles/_shared.py:101-107`, `mcp/tools/bibles/camera.py:64`, `graph/nodes/_agent_prompt_context.py:94`.
- **Drift proof (existing divergence + live defect):** `ModelRouter` has no `resolve` method (`agents/model_routing/__init__.py` exports `select`/`resolve_or_raise`), so `bibles/_shared.py:106` raises `AttributeError`; verify-04 confirms the real runtime wires `ModelAdapter` and no test in `tests/unit/mcp/` exercises real mode.
- **Candidate owner module:** `agents.registry` (+`agents.prompt_templates`) — one descriptor per agent consumed by nodes and tools; MCP tools route through it.
- **Guard test:** the same bible agent driven through the graph node and through the MCP tool produces byte-identical artifact envelopes and model calls; assert no MCP module imports `ModelAdapter.chat` directly and no `if agent_id == ...` branch exists outside the descriptor.

### L-04 — Post-production models, `AssemblyAgent` and `assembly_manifest`
- **O-class:** O6 (parallel lifecycle) + O1 (duplicated normative model) + O3 (split state authority).
- **Severity:** Critical (impact 5 × drift 5 = 25).
- **Verification:** CONFIRMED. verify-12: `F-POST-01`, `F-POST-03`, `F-POST-05` all CONFIRMED (only the "share no field" sentence of F-POST-01 is overstated).
- **Consolidates:** `F-POST-01`, `F-POST-03`, `F-POST-05` (audit 12).
- **What is wrong:** `AssemblyAgent` exists twice (graph-side and MCP-side) with disjoint output fields and two invocation lifecycles; every post-production model is defined twice, once as a `post/` dataclass and once as a `schemas/` Pydantic model, sharing zero fields for `AudioPlan`/`TransitionPlan`; and the artifact id `assembly_manifest` (phase `post`) has two writers whose schemas are incompatible (`transitions: list[TransitionPlan]` with `cut_id` vs `transitions: list[dict[str,str]]` with no `cut_id`). Consumers therefore read different payloads for the same durable artifact id.
- **De-facto owners (strongest anchor):** `src/film_pipeline/post/assembly_agent.py:37` — `@dataclass` (MCP-side `AssemblyManifest`); also `agents/impl/assembly_agent.py:17`, `graph/nodes/wrapup.py:30-32`, `artifacts/registry.py:186`.
- **Drift proof (existing divergence, executed):** `AssemblyManifest` fields = `audio_plan, color_plan, cut_id, delivery_mode, duration_total_seconds`; `AssemblyPlanArtifact` fields = `clip_count, clips, notes, plan_id, total_duration_seconds` — only the artifact name is shared (verify-12 reproduced the field split).
- **Candidate owner module:** `post-production` — one assembly model and one writer used by the graph node and the MCP tool.
- **Guard test:** duplicate-normative-model test asserting one class per post model name under `src/`, plus a single-writer test asserting only one code path saves `assembly_manifest`.

### L-05 — "Delivery complete" and the delivery-manifest seam
- **O-class:** O2 (duplicated invariant enforcement) + O8 (missing contract).
- **Severity:** Critical (impact 5 × drift 5 = 25).
- **Verification:** MIXED. `F-POST-04` CONFIRMED (verify-12, reproduced verbatim); `F-POST-06` **DOWNGRADED** to Medium 8 (owner B has zero production callers); `F-POST-07` CONFIRMED.
- **Consolidates:** `F-POST-04`, `F-POST-06`, `F-POST-07` (audit 12).
- **What is wrong:** Two owners disagree about what makes a delivery package complete: `post/delivery_packaging_agent` declares completeness and the validator it also runs blocks the very same package (executed: `is_complete = True` alongside a `blocked` validator with five `missing_required_asset` findings). Three independent assembly validators return different issues for the same object, and the delivery-manifest seam uses two artifact ids (`delivery_manifest` probed by QC vs `delivery_package` written by post), so the `DeliveryCompletenessValidator` has nothing to read at phase `delivery`.
- **De-facto owners (strongest anchor):** `src/film_pipeline/post/delivery_packaging_agent.py:11` — `_COMPLETION_REQUIREMENTS: tuple[tuple[str, str], ...] = (`; also `validation/impl/delivery_completeness.py:15-22`, `post/validators.py:16-25`, `graph/nodes/qc.py:356`.
- **Drift proof (existing divergence, executed):** the same `AssemblyPlan` yields `['Clip count mismatch.']` from owner A and `[]` from owner B; QC probing `delivery_manifest` finds no writer because the only writer produces `delivery_package` (verify-12 reproduced `is_complete=True` vs `blocked/0.0` with 5 blocking issues).
- **Candidate owner module:** `delivery` — one declarative required-artifact set, one assembly rule function, one manifest id + schema.
- **Guard test:** for one fixture package, `delivery_packaging_agent.is_complete(...)` and the delivery validator agree, and every artifact id probed by QC is an id some module writes.

### L-06 — Phase advancement / successor, app path skips the provider gate
- **O-class:** O6 (parallel lifecycle) + O1 (duplicated normative model).
- **Severity:** Critical (impact 5 × drift 4 = 20).
- **Verification:** CONFIRMED. verify-01: `F-PHASE-01` CONFIRMED (divergence reproduced; Critical ≥16 holds), `F-PHASE-04` CONFIRMED.
- **Consolidates:** `F-PHASE-01`, `F-PHASE-04` (audit 01).
- **What is wrong:** The rule "which phase runs next after approval" has two live implementations. The graph refuses to enter `generation` while providers are blocked; the app/MCP `approve_phase` path indexes `PHASE_ORDER` with no provider check. The successor function itself is also written twice (`PHASE_ORDER` indexing in `_advance_result` vs the hand-written `_NEXT_PHASE_AFTER_APPROVAL` table), so a human approval while a provider is blocked can launch the paid generation phase, and the approval and non-approval routes through the graph can disagree about the next phase.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/_action_routing.py:325` — `def _advance_result(state: dict[str, Any], phase: str, result: RouterResult) -> RouterResult:`; also `app/_graph_exec.py:425-445`, `graph/edges.py:40-54`.
- **Drift proof (existing divergence, executed):** verify-01 re-ran the reproduction: with `current_phase="gen_planning"`, `approved=True`, provider `seedance` blocked — graph returns `continue_unrelated_work`, app returns `generation`; `tests/unit/app/test_resume_integrity.py:91-100` never inspects the target phase.
- **Candidate owner module:** `phase-model` — one `successor(phase, *, blocked_providers)` returning the `RouterResult`, consumed by both paths.
- **Guard test:** for every phase × blocked-provider state, the app advance result equals `compute_actions().next_action`; for every `PHASE_ORDER[i]`, `_NEXT_PHASE_AFTER_APPROVAL` maps to `PHASE_ORDER[i+1]`.

### L-07 — Agent declared contract vs registered implementation
- **O-class:** O1 (duplicated normative model) + O8 (missing contract) + O4 (parallel registries).
- **Severity:** Critical (impact 5 × drift 5 = 25). The entry maximum is `F-POST-02` (verify-12 CONFIRMED at 25); the entry is unchanged despite `F-AGENT-02` being downgraded.
- **Verification:** MIXED. `F-AGENT-02` **DOWNGRADED** Critical 20 → High 15 (verify-04: broken Reproduce block, declared field has zero production readers); `F-AGENT-03`, `F-AGENT-10` CONFIRMED (verify-04); `F-POST-02` CONFIRMED 25 (verify-12).
- **Consolidates:** `F-AGENT-02`, `F-AGENT-03`, `F-AGENT-10` (audit 04); `F-POST-02` (audit 12).
- **What is wrong:** The registry's declared role and `output_artifacts` do not match what the implementation returns: of 11 agents only one matches exactly, three overlap partially and the rest disagree; `known_kb_domains`/`known_output_artifacts` guards are dead in production and would reject 7 of 11 agents if enabled; the class roster has 12 keys against 11 declared agents (an unreachable `visual-dev-agent`) and `_AGENT_PROFILE_MAP` has 21 keys, 10 of which name no registered contract; and the id `failure-handling-agent` is claimed by multiple registries that disagree about whether it is an assembly agent, the graph's `AssemblyAgent` or a `FailureDecision` producer.
- **De-facto owners (strongest anchor):** `src/film_pipeline/agents/mvp/__init__.py:162` — `output_artifacts=["failure_decision"],`; also `agents/impl/registry.py:26-29`, `agents/registry.py:118-122`, `agents/impl/assembly_agent.py:64`.
- **Drift proof (existing divergence, executed):** `FailureDecision` (`schemas/failure.py:17`) is never constructed in `src/` while `failure-handling-agent` is mapped to `AssemblyAgent`, which returns `{"assembly_manifest": manifest}`; the roster returns `{"status": "agent_not_found"}` for the extra class id (verify-12 reproduced the mismap and the never-produced `failure_decision`).
- **Candidate owner module:** `agents.registry` — one descriptor table (`agent_id`, class, contract, `produces`) plus a reverse-direction guard test.
- **Guard test:** `for a in AGENTS: assert a.produces in get_agent(a.agent_id).execute(...)`; every `applies_to_agents`/`output_artifacts` token is a registered id; `set(AGENT_CLASS_BY_ID) == set(MVP_AGENTS)`.

### L-08 — Generation job lifecycle: submit → poll → complete
- **O-class:** O6 (parallel lifecycle) + O8 (missing contract) + O1.
- **Severity:** Critical (impact 5 × drift 4 = 20).
- **Verification:** MIXED. `F-GEN-01`, `F-GEN-02`, `F-GEN-03`, `F-GEN-09` CONFIRMED (verify-06); `F-MCP-05` **DOWNGRADED** Critical 16 → High 12 (verify-11: the cited `prompt_payload` divergence was refuted, only the provider-default divergence survives).
- **Consolidates:** `F-GEN-01`, `F-GEN-02`, `F-GEN-03`, `F-GEN-09` (audit 06); `F-MCP-05` (audit 11).
- **What is wrong:** The same generation row is driven by two lifecycles. The operator/GUI path submits the assembled prompt text through `GenerationExecutor`; the MCP path submits `prompt_ref` (a reference string) where prompt text is expected, and its poll path marks the row `COMPLETED` without downloading media or recording a manifest/take, so `output_refs` stays empty. Prompt assembly itself has two implementations with different fallback chains and constitution sources, and the text-only policy is implemented twice.
- **De-facto owners (strongest anchor):** `src/film_pipeline/generation/executor.py:177` — `prompt = resolve_shot_prompt(self._store, project_id, row.shot_id, shot_row, row.prompt...`; also `mcp/tools/generation/dispatch.py:114`, `generation/executor.py:293-301`, `graph/nodes/_generation_prompts.py:64`.
- **Drift proof (existing divergence):** verify-06 re-ran the spy adapter: the operator path sends resolved text, the MCP path sends `"prompt:pkg-42"` verbatim; `deliver_completed_job` has exactly one caller (`executor.py:275`), and `dispatch.py:239-245` writes status/poll fields only — no `output_refs`, no manifest/take.
- **Candidate owner module:** `generation-runtime` — one `plan → approve → start → poll` façade used by both surfaces; one prompt resolver.
- **Guard test:** drive the same row through both surfaces with a spy adapter and assert identical provider payloads, on-disk media, ledger rows and `generation_requests`.

### L-09 — Provider health has four representations; routing reads the dormant one
- **O-class:** O3 (split state authority) + O4 (parallel registries).
- **Severity:** Critical (impact 4 × drift 5 = 20).
- **Verification:** CONFIRMED. verify-05: `F-PROV-01` CONFIRMED (all 6 anchors resolve, 4 representations/3 writers/0 producers re-executed, CWD divergence reproduced); `F-OST-13` CONFIRMED (verify-02); `F-TEST-10` post-verification → PENDING/UNVERIFIED.
- **Consolidates:** `F-PROV-01` (audit 05); `F-OST-13` (audit 02); `F-TEST-10` (audit 13).
- **What is wrong:** Provider health is stored as a runtime dict, a `providers/health.py` tracker, a `schemas/provider_health.py` model and a checkpointed orchestrator snapshot, and the same runtime field holds two incompatible value types depending on writer. The graph router reads `ostate.get_blocked_providers`, whose only writer `update_provider_health` has zero production callers; operator surfaces read `rt.provider_health`. The same real-mode runtime reports four *healthy* providers from the repo root and four *unconfigured* providers from `/tmp` with an identical environment, and in neither case can routing see the result.
- **De-facto owners (strongest anchor):** `src/film_pipeline/app/runtime.py:51` — `provider_health: dict[str, Any] = field(default_factory=dict)`; also `app/runtime.py:386-387`, `graph/orchestrator_state.py:55`, `providers/health.py`, `schemas/provider_health.py`.
- **Drift proof (existing divergence, executed):** verify-05 reproduced the CWD divergence verbatim; freeze a provider via `rt.set_provider_health(...)` — `compute_actions` still sees the dormant snapshot and permits the blocked provider's phase.
- **Candidate owner module:** `provider-health` — one typed health record with one writer, exported to the orchestrator state.
- **Guard test:** after seeding the runtime, `set(rt.provider_adapters) == set(rt.provider_health)` and a blocked provider makes `compute_actions` refuse generation; every value written to `provider_health` is one declared type.

### L-10 — Consensus construction and consensus report state
- **O-class:** O8 (missing contract) + O3 (split state authority) + O5.
- **Severity:** Critical (impact 4 × drift 5 = 20). The entry maximum is `F-VR-04` at 20; `F-VR-05` was recomputed to High 12.
- **Verification:** MIXED. `F-VR-04` CONFIRMED (verify-08: dict input → `AttributeError`, swallowed); `F-VR-05` CONFIRMED evidence but **severity recomputed 16 → 12** (writer A can never succeed, so the live race is latent); `F-OST-06` CONFIRMED (verify-02: no writer anywhere in `src/`). `F-VR-13` is post-verification → PENDING/UNVERIFIED.
- **Consolidates:** `F-VR-04`, `F-VR-05`, `F-VR-13` (audit 08); `F-OST-06` (audit 02).
- **What is wrong:** `ConsensusBuilder` receives serialized dicts from the QC node and does attribute access on them; the resulting `AttributeError` is swallowed, so algorithmic consensus never runs. Two writers then compete for `consensus_report_ref` in one node run (the LLM synthesis overwrites the algorithmic one — though writer A cannot succeed today), while the router reads a `consensus_report` state key that no production code writes and the schema does not declare — making the router's `BLOCKED`-consensus branch dead. **The refs themselves then cross the node boundary through a private policy.** `F-VR-13`: `qc.py:29-30` declares `_QC_REF_KEYS: tuple[str, ...] = ("consensus_report_ref", "qc_patch_ref")` and passes it as the whole boundary rule at `:42`, applied by hand in a loop at `:61-64` with a non-constant subscript — so the two ref keys are copied into the state update through a module-private tuple that `ORCH_CHANNELS` does not own, that the registry parity test cannot see, and that the AST write-detector misses; `_agent_handoff.py:9-12` states the opposite ownership claim.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/nodes/qc.py:392` — `reports = state.setdefault("_validation_reports", [])`; also `graph/nodes/qc.py:166-182`, `validation/consensus.py:66-71`, `graph/_action_routing.py:108-115`.
- **Drift proof (existing divergence, executable):** verify-08 re-ran `/tmp/vr04.py`: dict input → `AttributeError: 'dict' object has no attribute 'validator_id'` swallowed at `nodes/qc.py:176-177`; `grep -rn '"consensus_report":' src` finds only the agent's result key.
- **Candidate owner module:** `validation/consensus.py` — owns `ConsensusReport` construction and the one ref writer; the router reads the ref, not a phantom key.
- **Guard test:** after a QC run, `consensus_report_ref` resolves to a real artifact and a `BLOCKED` consensus makes `compute_actions` return `handle_blockers`.

### L-11 — Run / runtime / storage / checkpoint roots resolved five ways (plus one import-time writer)
- **O-class:** O5 (policy-by-branch) + O3 (split state authority over "where state lives") + O7 (`F-CRP-12` only: an import-time side effect reaching another module's root).
- **Severity:** **Critical (impact 5 × drift 5 = 25)** — **raised from 20** by `F-CRP-12`, which is the highest-scoring finding this ledger carries (it ties the corpus maximum, 5×5=25).
- **Verification:** MIXED. verify-10: `F-CRP-01` CONFIRMED (with a framing dispute — see below); `F-CRP-12` is audit 10's **post-verification** addition (verifier missed-seam M1, promoted to a finding and re-run by the audit's author) → **PENDING/UNVERIFIED**.
- **Consolidates:** `F-CRP-01`, `F-CRP-12` (audit 10).
- **What is wrong:** "Where does a run's state live?" is answered five times: `src/film_pipeline/artifacts/storage.py:79` nests the run root under the storage root, `cli/driver.py:69` makes the store root a subdirectory of the run root, `app/runtime.py:75-77` makes the store root the runtime root, `graph/graph.py:46` derives the checkpointer dir from `runtime_root` else the storage root, and `app/_persistence.py:41-42` derives the runtime root from a different env var. The answers do not coincide.
- **`F-CRP-12` — the import-time writer (the reason this entry is now 25).** A **bare `import film_pipeline.graph.graph`** runs the module-level `graph: CompiledStateGraph = build_graph()` at `src/film_pipeline/graph/graph.py:201`, which reaches `_default_checkpointer(runtime_root=None)` at `:181`; with `FILM_PIPELINE_PERSIST_STATE=1` and `FILM_PIPELINE_NO_PERSIST` unset, `:43-46` derives the checkpoint dir from `default_checkpoints_root()`, which is `resolve_storage_root() / "checkpoints"` (`artifacts/storage.py:74`) — **inside the storage root** — and `:49` then runs `checkpoint_dir.mkdir(parents=True, exist_ok=True)`. No runtime, no CLI and no MCP server is involved. That leaves the storage root non-empty but unmarked, so the app's own subsequent `ensure_storage_root` refuses it (`artifacts/storage.py:160-164` raises `StorageRootError` naming a marker the operator never removed). The root *resolver* is already single-owned and guarded (audit 03); what is unowned is the **composition** of roots — and here the composition happens at import time, in a module `langgraph.json:4` names as the graph target.
- **De-facto owners (strongest anchor):** `src/film_pipeline/artifacts/storage.py:79` — `return resolve_storage_root() / "runs" / "default"`; also `graph/graph.py:201` (`F-CRP-12`'s import-time build), `graph/graph.py:49` (the `mkdir`), `artifacts/storage.py:74` (the derived root), `cli/driver.py:69`, `app/runtime.py:75-77`, `graph/graph.py:46`.
- **Drift proof (existing divergence, executed by the author).** `F-CRP-01`: after a CLI run the storage root contains `['runs']` with no valid marker, and the app then fails to open it (`StorageRootError`); the CLI help text at `cli/run.py:114` is already wrong and `tests/unit/cli/test_help_snapshot.py:55` pins the wrong text. `F-CRP-12` (reproduced end to end, Appendix A.9 of `audit/10`): with a fresh `FILM_PIPELINE_STORAGE_ROOT` and `PERSIST_STATE=1`, `import film_pipeline.graph.graph` leaves `children of storage root: ['checkpoints']` and the app then reports `StorageRootError: Refusing to use <tmp>/storage …`. Drift 5 because the failure is invisible to the suite: `tests/conftest.py:98` sets `FILM_PIPELINE_NO_PERSIST=1` session-wide, so every test that imports the module takes the `MemorySaver` branch at `graph/graph.py:43-44` and never reaches `:49`; the bug needs a fresh process with `PERSIST_STATE=1`, which no test creates.
- **Candidate owner module:** `runtime_persistence` — one `RootLayout` value object (`storage_root`, `runtime_root`, `checkpoint_root`, `run_root`) resolved once, and the module-level graph instance moved behind a lazy accessor so importing the module has no durable side effect.
- **Guard test:** build a CLI run and an app runtime from one env and assert `RootLayout` equality and that the storage root still opens; **plus** (`F-CRP-12`) import `film_pipeline.graph.graph` in a fresh process with `PERSIST_STATE=1` and a fresh storage root, then assert `resolve_storage_root()` still opens and has no `checkpoints/` child.

### L-12 — MCP tool invocation lifecycle and the `app` ↔ `mcp` cycle
- **O-class:** O6 (parallel lifecycle) + O8 (missing contract) + cycle.
- **Severity:** Critical (impact 5 × drift 4 = 20).
- **Verification:** CONFIRMED. verify-11: `F-MCP-02` CONFIRMED and the bypass is **live** (scripts call confirm-gated tools with no `confirmed`). verify-14: `F-BOUNDARY-03` CONFIRMED at package granularity, scope materially understated (cycle C2 is 7 modules, `enola-architecture-facts.md:56`).
- **Consolidates:** `F-MCP-02` (audit 11); `F-BOUNDARY-03` (audit 14).
- **What is wrong:** Tool invocation is implemented four times (stdio transport, CLI driver, two scripts), and only the stdio transport applies the confirmation gate and project resolution, so `confirm=True` on a destructive tool is advisory on every other entry point. Structurally the same boundary is a real import cycle: `app.product_gate` imports `mcp.contract` while `mcp/server.py` imports `app.runtime`/`app.bootstrap`/`app._persistence`, held together only by function-body imports. Enola (module granularity) reports the cycle as `app → app/services → mcp → mcp/tools → mcp/tools/bibles → mcp/tools/generation → mcp/tools/reference_generation → app` (7 members), so the audit's 2-package view and its proposed split do not by themselves break the actual cycle.
- **De-facto owners (strongest anchor):** `src/film_pipeline/mcp/_stdio_transport.py:61` — `tool_response = await server.call(tool_name, arguments)`; also `cli/driver.py:199-206`, `scripts/*`, `app/product_gate.py:17`, `mcp/server.py:164,241,248`.
- **Drift proof (existing divergence / cycle):** verify-11 confirmed the four paths and that scripts invoke confirm-gated tools unconfirmed; the cycle is invisible to mypy/pytest because the imports are lazy.
- **Candidate owner module:** `mcp.dispatch` — one `invoke_tool(name, args, *, actor)`; and `module-law` for the `app`↔`mcp` direction.
- **Guard test:** a boundary test asserting `mcp` never imports `app` at module scope (and vice versa) plus an invocation test that each of the four entry points refuses an unconfirmed destructive tool; add the enola intent declaration so the cycle is graded.

### L-13 — Validator registry and phase→validator dispatch
- **O-class:** O4 (parallel registries) + O3 + O1.
- **Severity:** Critical (impact 4 × drift 4 = 16). `F-CFG-03` was STRENGTHENED to 16; `F-MCP-04` was corrected 20→16, so the entry maximum is 16.
- **Verification:** MIXED. `F-VR-01` CONFIRMED (verify-08: `scene-writing-validator DIFFERS ['blocking_conditions']`, `delivery-completeness-validator ABSENT`); `F-VR-07`, `F-VR-08` CONFIRMED (verify-08); `F-CFG-03` **STRENGTHENED** (verify-03 found an existing divergence the audit missed); `F-AGENT-08` CONFIRMED (verify-04); `F-PHASE-10` **DOWNGRADED** in scope (verify-01: two phase→validator tables, not three; severity unchanged Medium 6); `F-MCP-04` CONFIRMED with score corrected 20→16 (verify-11); `F-VR-14`, `F-VR-15` are post-verification → PENDING/UNVERIFIED.
- **Consolidates:** `F-VR-01`, `F-VR-07`, `F-VR-08`, `F-VR-14`, `F-VR-15` (audit 08); `F-CFG-03` (audit 03); `F-AGENT-08` (audit 04); `F-PHASE-10` (audit 01); `F-MCP-04` (audit 11).
- **What is wrong:** Validator identity is declared in `validation/validators/__init__.py` (15 entries, never executed) and re-declared per class in `validation/impl/*` (executed); six ids are declared twice with different conditions (`scene-writing-validator` blocking list differs), one validator has an impl but no roster row, and the runtime `ValidatorRegistry` is never populated. Dispatch is then split across several tables (`graph/nodes/qc._VALIDATOR_RUNNERS`, `graph/subgraphs/qc._VALIDATOR_MAP` + `_WORKER_NODES`, `graph/subgraphs/qc._ARTIFACT_ROUTING`, `mcp/tools/validation._live_validator_specs`), and the delivery validator is absent from both QC paths. `blocking_conditions`/`warning_conditions` are inert, so "which finding blocks" is re-derived inline in every validator. **The MCP dispatch surface is narrower than its own spec in two ways.** `F-VR-15`: `_live_validator_specs` declares six phase arms (`src/film_pipeline/mcp/tools/validation.py:138-157`) but the *registered* mutating tool `run_validation` (`src/film_pipeline/mcp/tools/registry.py:240`) dispatches only `visual_dev` and `script` (`src/film_pipeline/mcp/tools/validation.py:297-306`), and answers every other declared phase with `_ok(message="No validators found for this phase.")` — a success-shaped refusal, so four of six declared phases are unreachable through the registered path and the failure is reported as success. `F-VR-14`: the tool writes an undeclared `validation_refs` project-state key (`src/film_pipeline/mcp/tools/validation.py:274-276`) while the schema's `validation_report_refs` channel (`state_schema.py:173`), its `ORCH_CHANNELS` row (`orchestrator_state.py:163`) and its documentation (`_agent_handoff.py:31`) all describe a channel that **no code writes**.
- **De-facto owners (strongest anchor):** `src/film_pipeline/validation/validators/__init__.py:40` — `blocking_conditions=["missing_scene_intent", "no_conflict"],`; also `validation/impl/script_structure.py:139`, `graph/nodes/qc.py:361-368`, `graph/subgraphs/qc.py:45-52,210-217`, `mcp/tools/validation.py:123-158`.
- **Drift proof (existing divergence):** verify-08 reproduced the registry disagreement; `grep -rn "blocking_conditions\|warning_conditions" src` = 46 hits, 0 read sites; verify-11 notes `test_qc_validator_dispatch.py:75-107` already pins the phase sets (hence drift 4, not 5).
- **Candidate owner module:** `validation/registry.py` (identity + entry lists) and `validation/dispatch.py` (`PHASE_VALIDATORS: dict[FilmPhase, tuple[ValidatorId, ...]]`), consumed by both QC paths.
- **Guard test:** registry-agreement test over all entries; for every `FilmPhase`, the subgraph worker set, the sequential runners and the MCP specs are equal; every `blocking_conditions` token is produced by the validator that declares it.

### L-14 — Score→status thresholds; `NEEDS_REVISION` unreachable
- **O-class:** O1 (duplicated normative model).
- **Severity:** Critical (impact 4 × drift 5 = 20). `F-VR-11` is correctly Medium 6 but does not raise the entry.
- **Verification:** CORRECTED / CONFIRMED. verify-08: `F-VR-02` CONFIRMED with correction required (the empty band reproduces for explicit thresholds, but the §2.4 absolute "not reachable end-to-end" verdict is false because the LLM path can mint `needs_revision`); `F-CFG-04` **CORRECTED** (verify-03: the band is zero-width for **22 of 22** explicit literals, not "20 of 24" — the divergence is worse but narrower than stated, because the class default band is *not* empty); `F-VR-11` CONFIRMED with severity mislabeled (verify-08 confirms 6 = Medium under §1.5).
- **Consolidates:** `F-VR-02` (audit 08); `F-CFG-04` (audit 03); `F-VR-11` (audit 08).
- **Counts (orchestrator V1, AST-verified):** 23 `ValidatorThresholds(...)` constructions repo-wide — **22 with literal thresholds** and **1 bare default** at `validation/thresholds.py:21` (`t = thresholds or ValidatorThresholds()`). Of the 22 literals: **18×(85,75,75)**, **3×(80,70,70)**, **1×(90,80,80)**; `block_below == review_at` in **22 of 22**. The earlier "24/20" figures came from `grep` matching the class definition and `Field` declaration lines in addition to call sites.
- **What is wrong:** The score→status grammar exists as a class default (85/75/65) and as 22 explicit call-site literals, and **every one of the 22 literals uses `block_below == review_at`**. Because `score_to_status` evaluates `pass_at → review_at → block_below` in order, the literal path's `[block_below, review_at)` band is empty, so every explicitly-thresholded validator skips `NEEDS_REVISION` entirely; a score of 70 against an 85/75/75 entry becomes `BLOCKED`, not the revision status the four-status contract promises. The unreachability is a property of the *literals*, not of the class: the bare default (85/75/65, and the same values in the Pydantic field defaults at `schemas/registries/validator_registry.py:17-19`) does leave a live `[65,75)` band, so a validator that omits `thresholds=` can still emit the status. The prior defect "`score_to_status` ignores `review_at`" is fixed, but the conclusion survives through the empty band for all 22 registered literal entries.
- **De-facto owners (strongest anchor):** `src/film_pipeline/validation/thresholds.py:25` — `if score >= t.review_at:`; also `schemas/registries/validator_registry.py:17-19`, `validation/validators/__init__.py:19`.
- **Drift proof (existing divergence, with behavioural consequence):** verify-08 re-ran `/tmp/vr02.py` → `[]` (no score emits `NEEDS_REVISION` through the declared band); with `pass_at=85, review_at=75, block_below=75`, `score_to_status(70)` returns `BLOCKED`; no test covers a registered entry.
- **Candidate owner module:** `validation/thresholds.py` — one `ValidatorThresholds` vocabulary, all literals replaced by references.
- **Guard test:** for every registered validator entry there exists a score that emits each of the four statuses (`PASS`, `PASS_WITH_NOTES`, `NEEDS_REVISION`, `BLOCKED`).

### L-15 — Phase vocabulary, order and phase-keyed policy literals
- **O-class:** O1 (duplicated normative model) + O3 + O4.
- **Severity:** Critical (impact 4 × drift 4 = 16).
- **Verification:** CONFIRMED. verify-01: all ten audit-01 findings CONFIRMED (`F-PHASE-02` mutation → `"wrap"` reproduced; `F-PHASE-09` "zero test references" is stronger than claimed); verify-02: `F-OST-15` CONFIRMED.
- **Consolidates:** `F-PHASE-02`, `F-PHASE-05`, `F-PHASE-08`, `F-PHASE-09`, `F-PHASE-11` (audit 01); `F-OST-15` (audit 02).
- **What is wrong:** The 11-phase vocabulary and its order are defined independently in eleven places across eight modules (`FilmPhase`, `PHASE_ORDER`, `_PHASE_TO_NODE`, `APPROVAL_GATES`, `_APPROVAL_DESTINATIONS`, `_PHASE_NODES`, `_NEXT_PHASE_AFTER_APPROVAL`, `PHASE_DIR_MAP`, `_PHASE_KEYWORDS`, `_PHASE_DEFAULT_AGENTS`, phase-class sets), and `PHASE_DIR_MAP` insertion order is a second ordering authority that feeds `current_phase` through project discovery. Phase-keyed policies live outside the vocabulary (rollback regeneration, constraint keywords, per-phase budget caps, required context), and two partial registries (`_PHASE_DEFAULT_AGENTS` 9/11, `PHASE_BUILDERS` 7/11) fall back silently for the phases they omit. Values agree at HEAD, but only by convention.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/_action_routing.py:18` — `PHASE_ORDER = [`; also `artifacts/paths.py:14`, `schemas/_base.py:77`, `graph/graph.py:55,85`, `graph/edges.py:40`, `graph/_agent_routing.py:35`, `constraints/_keywords.py:153`.
- **Drift proof (mutation scenario):** verify-01 reproduced "add a 12th phase to `FilmPhase` and `PHASE_DIR_MAP` only" → `_advance_result` computes `idx = -1` and returns `"wrap"`, ending the run early; no test references `PHASE_DIR_MAP` or `FilmPhase` membership.
- **Candidate owner module:** `phase-model` — one ordered `PHASE_ORDER: tuple[FilmPhase, ...]`; every other table becomes a derived view or a declared partial index.
- **Guard test:** `set(PHASE_DIR_MAP) == set(PHASE_ORDER) == set(FilmPhase)`, `list(PHASE_DIR_MAP) == [p.value for p in PHASE_ORDER]`, every partial registry key is a `FilmPhase` and intentional omissions are named, plus an AST test banning new line-initial phase-literal blocks outside the owner.

### L-16 — Generation ledger state machine and generation-status grammar
- **O-class:** O3 (split state authority) + O6 + O1.
- **Severity:** Critical (impact 4 × drift 4 = 16). `F-ARTIFACT-07` was downgraded 16→12; the entry maximum is `F-GEN-04` at 16.
- **Verification:** MIXED. `F-GEN-04`, `F-GEN-05`, `F-GEN-06` CONFIRMED (verify-06); `F-ARTIFACT-07` **DOWNGRADED** Critical 16 → High 12 (verify-07: original drift proof falsified; the reproduced COMPLETED→RUNNING proof replaces it); `F-PROV-06` CONFIRMED (verify-05).
- **Consolidates:** `F-GEN-04`, `F-GEN-05`, `F-GEN-06`, `F-GEN-14` (audit 06); `F-ARTIFACT-07` (audit 07); `F-PROV-06` (audit 05).
- **What is wrong:** The ledger row state machine has two writers with different transition rules: a row that fails on the operator path is parked at `wait_human`, the same failure via MCP leaves `next_action` at `submit`. `update_row` accepts an arbitrary status and enforces no transition (verify-07 reproduced COMPLETED→RUNNING), the graph marks shot-matrix rows `generated` at planning time while the ledger still says `SUBMITTED` with empty `output_refs`, and the 10-member `GenerationStatus` enum is written from only 6 members beside a second untyped reference-generation status (`needs_regeneration` appears in neither).
- **De-facto owners (strongest anchor):** `src/film_pipeline/generation/executor.py:399` — `self._ledger.update_row(`; also `generation/ledger.py:211-216`, `graph/nodes/generation.py:64`, `schemas/_base.py:168-180`, `mcp/tools/generation/dispatch.py:182-196`.
- **Drift proof (existing divergence):** verify-07 reproduced COMPLETED→RUNNING as an illegal transition that persists and changes cost computation; verify-06 found 10 `update_row(` sites in exactly 2 modules with three field divergences.
- **Candidate owner module:** `generation-ledger` — one transition API; `generation-runtime` owns one status grammar for both surfaces.
- **Guard test:** exhaustive `(from, to)` transition-matrix test, and a test asserting every status string emitted in `src/` is a member of `GenerationStatus`.

### L-17 — Two live QC lifecycles (subgraph vs sequential node)
- **O-class:** O6 (parallel lifecycle) + O2.
- **Severity:** Critical (impact 4 × drift 4 = 16).
- **Verification:** CONFIRMED. verify-08: `F-VR-03` CONFIRMED (dispute over mutation strength, not substance); verify-02: `F-OST-07` CONFIRMED-WITH-FIX (two anchors do not resolve).
- **Consolidates:** `F-VR-03` (audit 08); `F-OST-07` (audit 02).
- **What is wrong:** The forward graph runs QC through the compiled parallel subgraph while the repair/app paths run the sequential `qc_node`; the two write different state (`_qc_reports`/`_qc_raw_reports` vs `consensus_report_ref`/`qc_patch_ref`), cover different validator sets, and translate findings→issues with two separate severity mappings. A repair triggered from a QC failure therefore exercises a different QC implementation than the forward pass.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/graph.py:115` — `builder.add_node("qc_node", build_qc_subgraph())  # Phase 7: parallel subgraph`; also `graph/nodes/_repair_loop.py:47,234`, `graph/subgraphs/qc.py:68-73`, `graph/nodes/qc.py:91-182`.
- **Drift proof (existing divergence):** verify-08 verified both lifecycles and all live call sites (`graph.py:115` vs `_repair_loop.py:47`/`_graph_exec.py:337,452`); change a severity mapping in one translation — the other path keeps its own, and no test asserts both entry points produce the same issues for the same reports.
- **Candidate owner module:** `validation/runtime.py` — one pure QC core invoked by both callers.
- **Guard test:** run both entry paths over the same fixture and assert equal issues, equal side effects and equal state keys.

### L-18 — Artifact kind ↔ `ArtifactType` vocabulary (R1-corrected)
- **O-class:** O1 (duplicated normative model) + O4 (parallel registries) + O2.
- **Severity:** Critical (impact 4 × drift 4 = 16). `F-ARTIFACT-08` and `-09` were downgraded, but `F-ARTIFACT-02` (CONFIRMED) and the post-verification `F-KBCTX-11` (16) keep the entry Critical.
- **Verification:** MIXED. verify-07: `F-ARTIFACT-02` CONFIRMED (one sub-claim false — the persisted-data divergence stands); `F-ARTIFACT-08` **DOWNGRADED** 12→8; `F-ARTIFACT-09` **DOWNGRADED** 9→6. verify-09 has no coverage of the newer ids; `F-ARTIFACT-11`, `F-ARTIFACT-13`, `F-VR-12` and `F-KBCTX-11/12/13` are post-verification → PENDING/UNVERIFIED.
- **Consolidates:** `F-ARTIFACT-02`, `F-ARTIFACT-08`, `F-ARTIFACT-09`, `F-ARTIFACT-11`, `F-ARTIFACT-13` (audit 07); `F-VR-12` (audit 08); `F-KBCTX-11`, `F-KBCTX-12`, `F-KBCTX-13` (audit 09).
- **What is wrong:** Three vocabularies describe artifact identity: the 47-id kind registry, the 45-member `ArtifactType` enum, and `graph/nodes/_context._ARTIFACT_TYPE_BY_CLASS`, whose class map contains values `ArtifactType` rejects and whose fallback silently writes `SCRIPT`. Data is already wrong today: `consensus_report` and `cost_estimate` written through the graph path persist `artifact_type: script`. `F-VR-12` is the executed instance of exactly that coercion: `qc.py:83-89` passes `artifact_type="consensus_report"` for a `MatrixPatch` and `qc.py:109` relies on class-name inference for the report, while `_agent_artifacts.py:35-39` catches the resulting `ValueError` and substitutes `SCRIPT` — so a matrix patch is stamped a consensus report and a consensus report is stamped a script. The same conflation gives one matrix payload two registry identities, leaves `kb_context_packet` a registered kind with no producer, and makes `_ARTIFACT_TYPE_BY_CLASS` a second normative type model. On read, `KindNotRegisteredError` is enforced on write but a fabricated spec is returned for unknown kinds, so the catalog can drift silently. **Two further vocabularies belong to the same concern.** `F-ARTIFACT-11`: `AssetEntry.kind` (`artifacts/manifest.py:21`) is a fourth, free-form `str` whose only vocabulary is a trailing comment, written by `generation/executor_delivery._asset_kind` (`:132-148`) and consumed by three equality checks in the same file — and it **already drifts**: the manifest comment and the classifier say `generated_clip`/`reference_sheet`/`last_frame`/`mid_frame`/`audio_stem`, while `ArtifactType` spells the same concept `clip` (`schemas/_base.py:58`), so a clip is two different strings depending on which layer names it. `F-ARTIFACT-13`: `_UPSTREAM_CONTENT_SOURCES` (`graph/nodes/_context.py:329-338`) is a fifth table — a ref-key→phase map with 8 phase names as tuple values, hard-coding both the phase and the content key per ref, cross-checked against neither `FilmPhase` nor `PHASE_DIR_MAP`.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/nodes/_context.py:300` — `_ARTIFACT_TYPE_BY_CLASS: dict[str, str] = {`; also `schemas/_base.py:27-74`, `artifacts/registry.py:131-194` (`:157` shot-matrix id, `:185` `kb_context_packet`), `artifacts/manifest.py:21,41,43,49`, `generation/executor_delivery.py:132-148`, `graph/nodes/_context.py:329-338`, `schemas/_base.py:58`.
- **Drift proof (existing divergence, verified mechanically):** verify-07 confirmed the persisted-type divergence; `cost_estimate_bom` and `consensus_report` raise `ValueError` in `ArtifactType`, so `_infer_artifact_type` returns `SCRIPT` and the wrong type is persisted into the immutable envelope (`artifacts/store.py:148`) and surfaced by `mcp/tools/artifacts.py:40`.
- **R1 correction (applied).** `reconciliation-notes.md` R1 measured the ground truth with the repo venv: **47 registry ids vs 45 `ArtifactType` values, 39 shared; 8 registry-only ids** (`consensus_report`, `cost_estimate`, `execution_brief`, `project_profile`, `scope_contract`, `shot_matrix`, `story_bible`, `subtitles`) and **6 enum-only values**, of which **3 are reachable through registry prefixes** (`checkpoint_`, `invalidation_report_`, `rollback_record_`) and **3 have no registry entry at all** (`clip`, `last_frame`, `mid_frame`). verify-07's D8 adds the comparison basis: exact ids only is 47/45; including the 8 prefix kinds is 54/45 (registry-only 12). The audit's original "8-id / 3-id mismatch" understated the enum-only side; `design/proposal-A`'s "12 unregistered" compared `_by_kind` slugs against snake_case enum values and is methodologically wrong.
- **Candidate owner module:** `artifacts.contract` — one `type_for(artifact_id, obj)` backed by the kind registry, with missing values added to `ArtifactType` or an explicit refusal instead of a silent `SCRIPT`.
- **Guard test:** registry-agreement invariant — for every registry kind a type resolves or the kind is on an explicit dict-payload allow-list; no map value is rejected by `ArtifactType`; reading an unregistered kind raises rather than fabricating a spec; every registered kind has a producer.

### L-19 — KB packet construction and delivery to prompts
- **O-class:** O6 (parallel lifecycle) + O3 + O8.
- **Severity:** Critical (impact 4 × drift 4 = 16). `F-KBCTX-06` was downgraded to Medium 6; the entry maximum is `F-KBCTX-01`/`-08` at 16.
- **Verification:** MIXED. verify-09: `F-KBCTX-01` CONFIRMED (16), `F-KBCTX-08` CONFIRMED (16), `F-KBCTX-10` CONFIRMED (9), `F-KBCTX-06` **DOWNGRADED** to Medium 6 (dead parallel policy, not a lifecycle).
- **Consolidates:** `F-KBCTX-01`, `F-KBCTX-06`, `F-KBCTX-08`, `F-KBCTX-10` (audit 09).
- **What is wrong:** `KBContextPacketBuilder` is never wired into production — both `GraphServices` factories omit `kb_builder`, so every graph run takes a synthetic packet with empty policy/playbook refs, while the MCP `kb` tool builds a real one; the template path that critical-path agents use accepts the packet and discards it, rendering only its opaque id, so packet content never reaches a prompt. A second, dead phase-context system (`graph/context_packets.py`) executes seven builders whose output is written to a key no template reads, and the packet's governance/conflict output has no consumer.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/services.py:119` — `if self.kb_builder is not None:`; also `graph/services.py:128-134`, `agents/runner.py:400,415`, `graph/context_packets.py:128-136`, `mcp/tools/kb.py:95`.
- **Drift proof (existing divergence):** verify-09 CONFIRMED the builder is unwired and reproduced the packet-never-read path; the graph and MCP paths produce packets with different content for the same phase and agent, and `grep -rn "scoped_context" src/ tests/` shows the only writer's output is never read.
- **Candidate owner module:** `kb-context` — one builder wired into both `GraphServices` factories; the packet is the contract and rendering is `agents`' job.
- **Guard test:** `for_mock_runtime(...)` and `for_real_runtime(...)` both build a packet with non-empty refs; a packet with a canonical policy produces that policy text in the rendered prompt; a template-variable test rejects keys no template reads.

### L-20 — KB provenance: `kb_context_ref` stamping and `kbctx:` id grammar
- **O-class:** O3 (split state authority) + O8 + O1.
- **Severity:** Critical (impact 4 × drift 4 = 16). `F-KBCTX-04` and `-05` were downgraded; the entry maximum is `F-KBCTX-03` at 16.
- **Verification:** MIXED. verify-09: `F-KBCTX-03` CONFIRMED (16 — 11 write paths drop the column), `F-KBCTX-02` CONFIRMED (12), `F-KBCTX-09` CONFIRMED (8); `F-KBCTX-04` **DOWNGRADED** to Medium 8 (latent intra-module asymmetry, not an existing divergence) and `F-KBCTX-05` **DOWNGRADED** to High 12 (blast radius overstated).
- **Consolidates:** `F-KBCTX-02`, `F-KBCTX-03`, `F-KBCTX-04`, `F-KBCTX-05`, `F-KBCTX-09` (audit 09).
- **What is wrong:** Provenance is stamped by exactly one artifact-write path (`graph/nodes/_agent_artifacts.py`), and 11 other write paths — including every MCP bible tool — construct metadata with `kb_context_ref=None`. Mutable artifacts carry the value in the envelope but delete it from `meta.json`, and reads prefer the deleted copy, so provenance disappears on read. The value itself is a node-local key that is not a graph channel. Three incompatible `kbctx:` minters (project+agent+random, project+phase+agent+constant, agent+domains) mean a ref cannot be parsed back to packet coordinates, and the KB root is resolved by three modules with divergent candidate rules.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/nodes/_agent_artifacts.py:86` — `kb_context_ref=provenance.kb_context_ref,`; also `kb/packets.py:108`, `graph/services.py:129`, `graph/_agent_routing.py:196-201`, `artifacts/store.py:279-289,536-553`, `kb/paths.py:10-16`.
- **Drift proof (existing divergence):** verify-09 CONFIRMED the 11-path drop; in `qc_node` the matrix patch is saved before the only agent run, and a mutable artifact saved with a ref reads back with `kb_context_ref: null` — though verify-09 correctly reframes the mutable case as latent.
- **Candidate owner module:** `kb-context` owns the value and one `KBContextId.for_packet(...)`; `artifacts` owns the provenance column and must serialise it in both envelope and `meta.json`.
- **Guard test:** `parse(ref)` round-trips for every producer and exactly one module mints `kbctx:`; a mutable save→read preserves the ref; a `_save_artifact` call without a resolvable ref raises rather than writing `None`.

### L-21 — Checkpoint metadata registries and `artifact_versions`
- **O-class:** O3 (split state authority) + O8.
- **Severity:** Critical (impact 4 × drift 4 = 16).
- **Verification:** MIXED. verify-10: `F-CRP-02` and `F-CRP-04` independently reproduced (the verifier corrected `F-CRP-04`'s Appendix A.6, which was not executable as written because it omitted the `_ORCH_NS` prefix at `graph/orchestrator_state.py:27`); `F-CRP-15` is audit 10's **post-verification** addition (verifier missed-seam M4) → **PENDING/UNVERIFIED**.
- **Consolidates:** `F-CRP-02`, `F-CRP-04`, `F-CRP-15` (audit 10).
- **What is wrong:** Checkpoint metadata lives in two in-memory registries; rollback validates against one and executes against the other, so clearing the state-side registry makes rollback fail while the manager still has the record. `CheckpointMetadata.artifact_versions` has two writers with different rules: the MCP `create_checkpoint` path leaves the map empty, so `get_invalidation_report` always returns `will_invalidate == []` for MCP-created checkpoints while the auto path populates it. **`F-CRP-15` shows the defect has a second half on the read side:** even a correctly derived map would be invisible, because the summary projection `_checkpoint_summary` (`mcp/tools/checkpoints.py:85-93`) hand-lists its keys and omits `artifact_versions`, and `list_checkpoints` (`:102`) and the single-checkpoint view (`:132`) return only that summary. The factory *can* carry the field (`app/runtime.py:253`) and `app/_graph_exec.py:102-103` is the only derivation, so the record can be right while the projection makes the empty map look like a property of the record. Adding `"artifact_versions": cp.artifact_versions` to the summary fails no test — nothing asserts the summary's key set.
- **De-facto owners (strongest anchor):** `src/film_pipeline/app/_persistence.py:145` — `manager.checkpoints[meta.checkpoint_id] = meta`; also `app/_persistence.py:236`, `mcp/tools/checkpoints.py:85-93` (`F-CRP-15`'s key-omitting `_checkpoint_summary`), `mcp/tools/checkpoints.py:102,132`, `app/runtime.py:253`, `app/_graph_exec.py:102-103`.
- **Drift proof (existing divergence, reproduced by the author):** after `create_checkpoint` through MCP, `checkpoint.artifact_versions = {}` and the invalidation report is empty; the auto path is pinned to a non-empty map by `tests/unit/app/test_runtime.py:35` (the assertion; `:37` is a comment).
- **Candidate owner module:** `runtime_persistence.checkpoints` — one registry and one checkpoint factory used by both creation paths.
- **Guard test:** restart → rollback succeeds; `len(rt.checkpoints) == len(manager.checkpoints)` after every restore; MCP create → `get_invalidation_report` is non-empty for a project with candidate refs.

### L-22 — Resume seam and duplicate resume implementations
- **O-class:** O8 (missing contract) + O6.
- **Severity:** Critical (impact 4 × drift 4 = 16).
- **Verification:** MIXED (verify-10: `F-CRP-03` CONFIRMED; **`F-CRP-05` DOWNGRADED High→Medium (3×3=9)** because the drifted lifecycle it names is dead code with no caller); `F-CRP-16` is audit 10's **post-verification** addition (verifier missed-seam M5) → **PENDING/UNVERIFIED**.
- **Consolidates:** `F-CRP-03`, `F-CRP-05`, `F-CRP-16` (audit 10).
- **What is wrong:** The resume seam between `app/_resume.py` and the graph is stringly typed: the producer and the consumer spell the payload keys themselves, with no shared type, so a one-sided rename silently leaves stale generation blockers in state and the resume falls through to manual phase advancement. Separately, `checkpoints/resume.py` (`ResumeManager`/`ResumeSnapshot`) and `checkpoints/branches.py` (`BranchManager`) are dead parallel implementations with no production consumer, while the crash-recovery snapshot is written and never read. **`F-CRP-16` extends the same seam to the revision path:** `request_revision`'s no-interrupt fallback sets two raw private keys — `_revision_note` and `_resume_to_repair` (`app/_graph_exec.py:381-393`) — though both are declared schema fields (`graph/state_schema.py:203-204`), and the production consumer `graph/nodes/_repair_loop.py:198` (also read for routing at `graph/graph.py:193`) is reached by **no test**: the only test of this recovery replaces the whole node (`tests/unit/app/test_resume_integrity.py:202` `monkeypatch.setattr(graph_module, "repair_phase_node", fake_repair)`) and asserts only the input dict keys, so deleting the consumer leaves the suite green. Impact is Low (§1.5 cosmetic/internal) because the failure is a last-resort path that is audited as `resume_failed` and re-raised, but it is the same untyped-payload contract the entry is about, now with a silent-failure mutation.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/nodes/_shared.py:190` — `remove_codes = external_state.get("remove_issue_codes")`; also `app/_resume.py`, `checkpoints/resume.py`, `checkpoints/branches.py`, `app/_graph_exec.py:381-393` (`F-CRP-16`'s producer), `graph/nodes/_repair_loop.py:198` (its unobserved consumer), `graph/state_schema.py:203-204`.
- **Drift proof (mutation scenario):** change the consumer literal at `graph/nodes/_shared.py:190` — stale blockers are never dropped, resumes fall through `app/_graph_exec.py:232` into manual advancement, and no test fails.
- **Candidate owner module:** `graph.resume_protocol` (or a typed `ResumePayload` in `app`) — one shared type both ends import.
- **Guard test:** a round-trip test that builds the payload through the producer and consumes it through the graph, asserting stale codes were removed; delete or wire the dead resume/branch modules (bar B9).

### L-23 — MCP tool argument contracts are declared and never populated
- **O-class:** O8 (missing contract).
- **Severity:** Critical (impact 4 × drift 4 = 16).
- **Verification:** CONFIRMED. verify-11: `F-MCP-03` CONFIRMED (0/77 non-empty `input_schema`; transport publishes `{}`).
- **Consolidates:** `F-MCP-03` (audit 11).
- **What is wrong:** `ToolContract` declares `input_schema`/`output_schema`, but `_tool_contract` never passes them; the catalog and the transport therefore advertise `inputSchema: {}` for all 77 tools while each handler re-parses raw dicts by hand. A required argument or a type change cannot be expressed, and no test can observe the contract.
- **De-facto owners (strongest anchor):** `src/film_pipeline/mcp/contract.py:52` — `input_schema: dict[str, Any] = field(default_factory=dict)`; also `mcp/tools/registry.py:110-117`, `mcp/_stdio_transport.py:39`, `mcp/tools/helpers.py:76-98`.
- **Drift proof (mutation scenario):** make `confirmed` mandatory for a tool — the advertised schema stays `{}`, so no client or test sees the change; `grep -rn "input_schema" src/film_pipeline/mcp/` matches only the declaration and the echo (verify-11 confirmed 0/77).
- **Candidate owner module:** `mcp.contracts` — one Pydantic argument model per tool, with the JSON Schema derived and validated before the confirmation gate.
- **Guard test:** every registered tool has a non-empty derived `input_schema`, `server.call` rejects missing/extra arguments against it, and `set(catalog schemas) == set(argument models)`.

### L-24 — Model-profile defaults declared in YAML and in code
- **O-class:** O1 (duplicated normative model).
- **Severity:** **High (impact 3 × drift 4 = 12)** — **lowered from Critical (4×4=16)** by verify-03's downgrade of `F-CFG-01`.
- **Verification:** **DOWNGRADED.** verify-03: the duplicate map is byte-identical, but the claimed consequence ("stale fallback live in every `ModelRouter()` path") is false — the YAML reaches the router through `resolved_config["model_profiles"]` overrides; severity recomputed to High 12.
- **Consolidates:** `F-CFG-01` (audit 03).
- **What is wrong:** `profiles/base.studio.yaml` and `agents/model_routing._FALLBACK_PROFILES` declare the same eight model profiles and are byte-identical today, but `ModelRouter` is constructed by `GraphServices` with no profiles and falls back to the code copy. The duplication is real drift risk; the verifier's correction is that the YAML is *not* dead in every path — some callers do receive it through overrides — so the impact is a latent divergence, not a live defect.
- **De-facto owners (strongest anchor):** `profiles/base.studio.yaml:43` — `model_profiles:`; also `agents/model_routing/__init__.py` (`_FALLBACK_PROFILES`), `graph/services.py`.
- **Drift proof (mutation scenario):** change `base.studio.yaml:45` `primary: deepseek/deepseek-chat` to a new model — `_FALLBACK_PROFILES` keeps the old value and callers that construct `ModelRouter()` directly keep using it; no test fails because the two are byte-identical today.
- **Candidate owner module:** `config` — owns the name→params vocabulary; `agents.model_routing` becomes a pure consumer that requires resolved profiles.
- **Guard test:** `ModelRouter.profiles` is a required constructor argument and a test asserts the resolved profile set equals the YAML's for every construction path.

### L-25 — Provider-lineup parsing understands one of two profile shapes
- **O-class:** O1 (duplicated normative model).
- **Severity:** Critical (impact 4 × drift 4 = 16).
- **Verification:** CONFIRMED. verify-03 reproduced the two-shape divergence exactly (`[] []` vs blocking conflict; the resolver sees both mock providers).
- **Consolidates:** `F-CFG-05` (audit 03).
- **What is wrong:** `config/validator.py` reads `providers.order`, but the mock and local-real profiles declare providers under `providers.video[].provider_id` with no `order` key, so the festival/quality conflict check silently finds no conflict against an all-mock stack — the exact combination it exists to reject.
- **De-facto owners (strongest anchor):** `src/film_pipeline/config/validator.py:26` — `provider_order: list[str] = (resolved.get("providers", {}) or {}).get("order", [])`; also `config/resolver.py`, `profiles/mock-demo.yaml:15-21`, `profiles/local-real-provider.yaml:16-22`.
- **Drift proof (existing divergence, executed):** verify-03 reproduced it — resolving a festival stack against the all-mock profile yields no conflict; the check only fires for the `order` shape.
- **Candidate owner module:** `config` — one provider-lineup normalizer consumed by the conflict check and the preferred-provider resolver.
- **Guard test:** a `.env`-free temp CWD with a festival stack + all-mock profile produces a blocking conflict; every known profile shape normalizes to the same lineup.

### L-26 — "Stalled phase" has two representations and three thresholds
- **O-class:** O3 (split state authority) + O5.
- **Severity:** **High (impact 3 × drift 4 = 12)** — **lowered from 15** by verify-02's downgrade of `F-OST-02` (the false drift proof removed the "no test executes it" claim).
- **Verification:** **DOWNGRADED.** verify-02: the divergence is real, but the stated drift proof is false — `ORCHESTRATOR_STALLED` *is* asserted at `test_real_human_gates.py:140,148`; severity recomputed 15→12.
- **Consolidates:** `F-OST-02` (audit 02).
- **What is wrong:** A stalled phase is represented as `_stalled_phase` in the routing layer and as a repair-loop round count, with thresholds 5 (default), 3 (repair call) and the approval-edge default. The router can declare a stall and write a blocking issue while the repair loop keeps re-running the phase, or vice versa; the two thresholds already disagree at HEAD.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/orchestrator_state.py:362` — `def is_stalled(state: dict[str, Any], phase: str, *, max_rounds: int = 5) -> bool:`; also `graph/edges.py:97-130`, `graph/nodes/_repair_loop.py:70-78`.
- **Drift proof (existing divergence):** changing the default from 5 to 2 changes the router's stall decision while `_start_round` keeps `max_rounds=3`; the two call sites already use 5 and 3.
- **Candidate owner module:** `graph/orchestrator_state.py` — one convergence/stall state and one cap.
- **Guard test:** delete `_stalled_phase` in favour of one `mark_stalled` call and assert the router and repair loop agree on the stall predicate for a table of round counts.

### L-27 — Failure decisions and provider failure classification
- **O-class:** O8 (missing contract) + O2 + O5.
- **Severity:** High (impact 3 × drift 5 = 15).
- **Verification:** CONFIRMED. verify-05: `F-PROV-02` CONFIRMED (0 src callers, 5 vocabularies, High 15 recomputes); verify-02: `F-OST-14` CONFIRMED (typed producer unused; only invocation is `wrapup.py:26`).
- **Consolidates:** `F-OST-14` (audit 02); `F-PROV-02` (audit 05).
- **What is wrong:** `FailureClassifier` has zero production callers while five ad-hoc error-code vocabularies re-implement it, so the provider layer never produces the classified failure the orchestrator expects. On the state side, `FailureDecision` is never constructed and `add_failure_decision` is never called, leaving the router's `escalate_to_failure_handler` rule unreachable, while the failure-handling agent's declared `failure_decision` output is dropped at `wrapup.py`.
- **De-facto owners (strongest anchor):** `src/film_pipeline/providers/failure_classifier.py:135` — `class FailureClassifier:`; also `graph/orchestrator_state.py:382-384`, `graph/nodes/wrapup.py:30-35`, `generation/ledger.py`, `agents/runner.py:17-20`.
- **Drift proof (existing gap + mutation):** verify-05 confirmed `grep -rn "FailureClassifier" src/` returns only its own module, so the classifier can be deleted with no test failure; the failure-handling agent's output never enters state.
- **Candidate owner module:** `provider-failure` owns the error-code vocabulary and classification; `graph/orchestrator_state.py` owns the typed `FailureDecision` channel.
- **Guard test:** drive a mocked 429 through `GenerationExecutor.start()` and assert the health record moves to `BLOCKED_QUOTA`; assert a produced `FailureDecision` reaches the orchestrator channel and makes rule 2 fire.

### L-28 — Provider registry and catalog/capabilities
- **O-class:** O4 (parallel registries) + O8 + O1 + O5.
- **Severity:** High (impact 3 × drift 5 = 15).
- **Verification:** CONFIRMED. verify-05: both `F-PROV-03` and `F-PROV-05` CONFIRMED (the `zai` reproduction prints the claimed output; the capability table has 0 readers and `_FALLBACK_PROFILES` == `base.studio.yaml:43-85`). `F-PROV-08` is post-verification → PENDING/UNVERIFIED.
- **Consolidates:** `F-PROV-03`, `F-PROV-05`, `F-PROV-08` (audit 05).
- **What is wrong:** Two same-named `ProviderRegistry` classes exist and neither is the production one; the real registry is `StudioRuntime.provider_adapters`, which silently overwrites on duplicate registration and can list an id that is registered-but-not-resolvable. The provider catalog and capabilities are re-declared in five modules (factory defaults, pricing, credentials, profiles, seeds), and `ProviderCapabilities` is written but never read, so "no provider capability enforcement before submission" persists. `F-PROV-08` extends the same concern to the *endpoint* each client actually talks to: the Gemini base URL is declared three times in three layers — `providers/adapters/imagen4_gemini.py:21` (`GEMINI_API`), `generation/gemini_client.py:13` (`GEMINI_API_BASE`) and a bare inline literal at `agents/model_adapter.py:296` — while `providers/adapters/seedance_openrouter.py:27` declares its equivalent exactly once, so the repo demonstrates both arrangements and nothing pins either. Changing one of the three leaves the other two pointing at the old host with no test failing.
- **De-facto owners (strongest anchor):** `src/film_pipeline/providers/registry.py:11` — `class ProviderRegistry:`; also `app/runtime.py:372`, `providers/factory.py:47-56`, `app/_provider_seeds.py:74`.
- **Drift proof (existing divergence, executed):** verify-05 reproduced the `zai` registered-but-unresolvable divergence; changing `factory._default_models` at `factory.py:49` leaves `_provider_seeds.default_video_provider` and the profile files on their old values and no test fails.
- **Candidate owner module:** `provider-registry` — one declarative table (id, type, defaults, capabilities) with one duplicate policy and one unknown-id error.
- **Guard test:** `set(rt.provider_adapters) == set(rt.provider_health)` after seeding; duplicate registration raises; every id in credentials/seeds/profiles resolves or the profile is rejected.

### L-29 — Credential resolution policy re-derived at 14 sites
- **O-class:** O2 (duplicated invariant enforcement) + O5.
- **Severity:** High (impact 3 × drift 5 = 15).
- **Verification:** CONFIRMED with corrections. verify-05: 14-call-site grep and rotation divergence reproduce; the audit's "never asserts a policy at the adapter layer" claim is false (tests do assert it) — see `verify-05.md` §F-PROV-04.
- **Consolidates:** `F-PROV-04` (audit 05); `F-CFG-11` (audit 03, CONFIRMED by verify-03).
- **What is wrong:** The id→env-var map, `.env` fallback, CWD-relative lookup and caching policy are re-derived at 14 call sites, re-keyed through unrelated provider ids, and differ in freshness: two adapters in the same process resolve the same class of credential with opposite semantics (one keeps the key captured at construction, one re-reads). Provider credentials also fall back to `./.env` while config knobs do not, so two resolution policies coexist.
- **De-facto owners (strongest anchor):** `src/film_pipeline/providers/credentials.py:28` — `def lookup(provider_id: str) -> str | None:`; also `providers/credentials.py:46-52`, `config/resolver.py:46`, `runtime_overrides.py:38`.
- **Drift proof (existing divergence, executed):** verify-05 reproduced it — rotating the key mid-process yields `seedance sees: <old>` and `veo sees: <new>` in the same run.
- **Candidate owner module:** `provider-credentials` — one `env_var_for(provider_id)`, one `EnvironmentSource` (`env → .env`), one freshness rule.
- **Guard test:** rotate a key between two lookups and assert both adapters observe the new value; a `.env` in a temp CWD is honoured for both credentials and config knobs.

### L-30 — Agent naming drifts into the KB manifest/defaults
- **O-class:** O4 (parallel registries that must agree).
- **Severity:** High (impact 3 × drift 5 = 15).
- **Verification:** CONFIRMED. verify-04 reproduced the counts (`4 11 4 5`; `orchestrator` 5 vs `orchestrator-agent` 4; generation-only 7) with one wrong anchor (`:30`).
- **Consolidates:** `F-AGENT-09` (audit 04).
- **What is wrong:** The canonical generation-planning agent is `provider-planning-agent`, but the KB manifest tags generation items with `generation-agent`/`provider-agent`, ids no source declares. Agents whose names do not match a manifest token silently receive no KB items instead of failing, so KB starvation is invisible.
- **De-facto owners (strongest anchor):** `src/film_pipeline/kb/retrieval.py:51` — `if agent_id is not None:`; also `agents/mvp/__init__.py:129`, `film-knowledge-base/index/kb-manifest.yaml`.
- **Drift proof (existing divergence, measured):** verify-04 reproduced the unmatched-token counts; no test asserts the intersection of `applies_to_agents` tokens with registered agent ids is empty.
- **Candidate owner module:** `agents.registry` exports the canonical id set; `kb` validates `applies_to_agents` at manifest load.
- **Guard test:** every non-`all` token in every manifest entry is a registered agent id, and an unknown token fails manifest load.

### L-31 — Gate decision and the human-gate review package
- **O-class:** O5 (policy-by-branch) + O6 + O8.
- **Severity:** High (impact 3 × drift 5 = 15).
- **Verification:** CONFIRMED, with a falsified sub-proof. verify-08: `F-VR-06` CONFIRMED (count disputed — seven sites, not six), `F-VR-10` CONFIRMED; `F-VR-09` CONFIRMED evidence but the "fails loudly on the MCP path" drift proof is **falsified** (the error is swallowed). Severity kept at 15 because the enforcement-copy divergence and zero-construction records are reproduced.
- **Consolidates:** `F-VR-06`, `F-VR-09`, `F-VR-10` (audit 08); `F-OST-17` (audit 02).
- **What is wrong:** The approve-vs-request-revision decision is re-derived at seven sites including a test that replicates the production logic, so changing the predicate changes only the enforcement site and leaves the advisory payload, headless path and router with the old rule. The typed `ReviewPackage` exists only on the MCP path; the LangGraph human gate renders an ad-hoc dict. The gate action vocabulary bypasses its own `ApprovalAction` schema (`approve_phase`/`revise` accepted but undeclared; `reject` declared but unhandled), and `ApprovalRecord`/`RevisionRequest` have zero constructions.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/nodes/approval.py:249` — `# ── Guard: reject approval when structural issues exist ──────────`; also `graph/nodes/approval.py:113-115,133-190,221-224`, `review/generator.py:65-80`, `schemas/approval.py:12`.
- **Drift proof (mutation scenario):** make `_count_blocking_issues` treat `"info"` as blocking — the payload, headless path and router keep the old test, and `tests/unit/graph/test_real_human_gates.py:153-174` (the replica) still passes.
- **Candidate owner module:** `validation/gate_policy.py` (decision) and `review/generator.py` (representation); `schemas/approval.py` owns the action vocabulary.
- **Guard test:** `available_gate_actions(issues)` equals the allowed set for the real state; the graph human gate builds a `ReviewPackage`; every `ApprovalAction` member has a handler and every accepted resume token is a member.

### L-32 — Number-word and scene-count grammar defined twice
- **O-class:** O1 (duplicated normative model).
- **Severity:** High (impact 3 × drift 5 = 15).
- **Verification:** CONFIRMED. verify-12: tables are byte-identical today, grammars duplicate, no test binds them; parity/equality reproduction passes.
- **Consolidates:** `F-BUD-05` (audit 12).
- **What is wrong:** The number-word vocabulary and scene-count extraction grammar are defined byte-identically in `constraints/_keywords.py` and `graph/nodes/_shared.py` (plus grammar variants in `constraints/extractor.py`). The constraint extractor and the graph's target-scene-count helper therefore recognise different inputs despite describing the same rule.
- **De-facto owners (strongest anchor):** `src/film_pipeline/constraints/_keywords.py:13` — `_NUMBER_WORDS: dict[str, int] = {`; also `graph/nodes/_shared.py:29-82`, `constraints/extractor.py:167-185`.
- **Drift proof (mutation scenario):** add `"thirty": 30` to `constraints/_keywords.py:33` only — `_extract_target_scene_count({"idea": "thirty scenes"})` returns `None` while `extract_constraints(...)` finds 30, and no test compares them.
- **Candidate owner module:** `constraints` — the numeric vocabulary and scene-count grammar.
- **Guard test:** duplicate-normative-model test asserting one `_NUMBER_WORDS` under `src/`, and a table test that both entry points return the same scene count for the same prose.

### L-33 — Test doubles: canned payloads and mock provider entries
- **O-class:** O8 (missing contract) + O1.
- **Severity:** **High (impact 3 × drift 4 = 12)** — **lowered from 15** by verify-13's downgrade of `F-TEST-01` (15→12).
- **Verification:** **DOWNGRADED.** verify-13: `F-TEST-01` DOWNGRADED High 15 → High 12; `F-TEST-07` CONFIRMED High 10 (with a reproduced undercount). **`F-TEST-02` was WITHDRAWN** in the fix loop and is excluded from this entry and from the live set — see §(d).
- **Consolidates:** `F-TEST-01`, `F-TEST-07` (audit 13). **Not** `F-TEST-02` (withdrawn).
- **What is wrong:** Canned agent payloads live in the production composition package (`app/mock_responses.py`), are bound to no output schema, and at least one already contradicts the prompt template (`treatment-agent` omits the `development` wrapper the template mandates, surviving only through a silent fallback in `DevelopmentAgent.execute`). Mock-provider registry entries are hand-built in four places and already disagree on capabilities for the same `provider_id`.
- **De-facto owners (strongest anchor):** `src/film_pipeline/app/mock_responses.py:97` — `def default_mock_responses() -> dict[str, dict[str, Any]]:`; also `providers/factory.py:96-103`, `tests/e2e/conftest.py:69-81`, `tests/unit/providers/test_mock_provider.py:27-35`.
- **Drift proof (existing divergence):** verify-13 reproduced the template/canned mismatch and the capability disagreement (`supports_audio=False, supports_seed=False` in the factory vs both true in `test_mock_provider.py:31-34`).
- **Candidate owner module:** `testing.doubles` — one normative owner of canned payloads, with provider entries derived from the real factory.
- **Guard test:** every canned payload validates against the artifact schema named by its template's `output_schema_ref`; `build_provider_adapter("mock-video-provider").capabilities` equals the entry tests use.

### L-34 — Phase→approval-gate map and gate mode
- **O-class:** O1 + O2 + O4 + O5.
- **Severity:** High (impact 3 × drift 4 = 12).
- **Verification:** CONFIRMED. verify-01: `F-PHASE-03`, `F-PHASE-07` CONFIRMED; verify-02: `F-OST-04`, `F-OST-10` CONFIRMED (verify-02 disputes `F-OST-04`'s severity *upward* to ≥12, matching `F-PHASE-03`, so the entry stays 12).
- **Consolidates:** `F-PHASE-03`, `F-PHASE-07` (audit 01); `F-OST-04`, `F-OST-10` (audit 02).
- **What is wrong:** The phase→gate map exists as `APPROVAL_GATES`, as eleven per-node `gate=` literals and as a hand-inlined copy in the QC subgraph; all eleven values agree today but nothing pins the agreement, so the router and the interrupt payload can disagree about which gate is showing. Gate mode (human vs auto/headless) is likewise derived twice from the same config key by two predicates that no test compares.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/_action_routing.py:49` — `APPROVAL_GATES = {`; also `graph/nodes/_shared.py:147-158`, `graph/subgraphs/qc.py:263-271`, `graph/edges.py:18-24`, `graph/nodes/_shared.py:132-143`.
- **Drift proof (mutation scenario):** verify-01 confirmed all eleven values agree and no test compares them; renaming `APPROVAL_GATES["shot_bible"]` without touching `visual.py:472` makes the MCP review package report the new gate while the interrupt payload keeps `"shot_bible"`.
- **Candidate owner module:** `phase-model` owns the gate map and the gate-mode predicate; `_phase_gate_updates` is the only writer of `human_approval_phase`.
- **Guard test:** for every phase, `_phase_gate_updates(...)["human_approval_phase"] == APPROVAL_GATES[phase]`; `_is_auto_mode(state) == (not _require_human_approval(state))` parameterised over both entry points.

### L-35 — `issues` contract, blocking predicate and approve veto
- **O-class:** O8 (missing contract) + O2.
- **Severity:** High (impact 4 × drift 3 = 12).
- **Verification:** CONFIRMED. verify-02: `F-OST-03` CONFIRMED (18-site predicate count reproduces, `IssueRecord` unused), `F-OST-05` CONFIRMED (four veto sites, two scopes, anchors exact).
- **Consolidates:** `F-OST-03`, `F-OST-05` (audit 02).
- **What is wrong:** The `issues` channel has no typed contract and the blocking predicate is re-derived at 18 sites, including both canonical blocker views. The "cannot approve with blocking issues" veto is implemented four times with two scopes: a blocking issue already in state is invisible to the prep auto-approval guard (which filters to new issues) but vetoes `approve_phase_node` and fires the router's `handle_blockers`.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/nodes/approval.py:250` — `if _count_blocking_issues(state):`; also `schemas/issue.py:12-22`, `graph/_action_routing.py:92,256`, `graph/nodes/prep.py:333`.
- **Drift proof (existing divergence in rule coverage):** change `_action_routing._is_blocking_issue` to also accept `severity == "fail"` — `router.py:64` and `approval.py:55` keep the old test, `compute_actions` stops blocking, and the prep guard already scopes differently.
- **Candidate owner module:** `graph/orchestrator_state.py`/`schemas/issue.py` — one `Issue` model and one `is_blocking(issue)` predicate, plus one `may_approve(state) -> (bool, reason)`.
- **Guard test:** parametrised over states containing pre-existing, fresh and non-blocking issues, all four veto sites return the same decision.

### L-36 — `app` re-implements the graph's channel reducers
- **O-class:** O4 (parallel registries) + O6.
- **Severity:** High (impact 3 × drift 4 = 12).
- **Verification:** CONFIRMED-WITH-FIX. verify-02: reducer duplication is real, but the stale-report asymmetry in the drift proof is overstated and one clause is vacuous.
- **Consolidates:** `F-OST-08` (audit 02).
- **What is wrong:** `app._graph_exec.run_phase_node` re-implements the compiled graph's channel merge rules: `_validation_reports` is last-write-wins in the schema but union-merged on the manual path, so a stale `BLOCKED` report from an earlier QC run survives on the repair path and `_most_severe_report` keeps treating the phase as blocked.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/state_schema.py:171` — `artifact_refs: Annotated[list[str], merge_unique]`; also `app/_graph_exec.py:481`, `graph/_action_routing.py:118-131`.
- **Drift proof (existing divergence):** run the same node update through `run_phase_node` and a compiled graph step — the manual path retains the old report, the compiled path replaces it, and no test compares the two.
- **Candidate owner module:** `graph/state_schema.py` — export the reducer map (`REDUCERS`) and have `_graph_exec` consume it.
- **Guard test:** the same node update applied through both paths yields equal channel contents.

### L-37 — Prompt registry keyed from two id spaces
- **O-class:** O4 (parallel registries must agree).
- **Severity:** High (impact 3 × drift 4 = 12).
- **Verification:** CONFIRMED. verify-04 reproduced `tpl-only = delivery-completeness-validator` and 9 registry-only ids; `template_id` is never a lookup key and `llm_enabled=True` on one impl.
- **Consolidates:** `F-AGENT-05` (audit 04).
- **What is wrong:** One prompt registry is keyed from two id spaces (agent ids and validator ids). `MVP_VALIDATORS` has 15 rows but only 6 have templates, and the `llm_enabled` gate makes 6 of the 7 validator templates unreachable; `delivery-completeness-validator` has a template and an impl but no roster row. Nothing asserts coverage, so a validator can silently ship without a prompt.
- **De-facto owners (strongest anchor):** `src/film_pipeline/agents/prompt_templates/registry.py:69` — `def get(self, agent_id: str) -> PromptTemplate | None:`; also `validation/validators/__init__.py:11-167`.
- **Drift proof (existing divergence):** adding an `llm_enabled` validator with no template produces a silent generic fallback rather than a load-time error; verify-04 reproduced the id-space split.
- **Candidate owner module:** `agents.prompt_templates` — one registry with a declared `TemplateKey` id space and a coverage invariant.
- **Guard test:** every `MVP_VALIDATORS` id with an `llm_enabled` impl has a template; every template name resolves to exactly one registered id.

### L-38 — Artifact version / `schema_version` / status law
- **O-class:** O5 + O1 + O2 + O3.
- **Severity:** **Critical (impact 4 × drift 4 = 16)** — **raised from High 12** because verify-07 recomputed `F-ARTIFACT-05` *upward* to 16 Critical.
- **Verification:** MIXED/UPGRADED. verify-07: `F-ARTIFACT-05` CONFIRMED with severity recomputed upward 12 → **16 Critical**; `F-ARTIFACT-04` CONFIRMED (12 High holds); `F-ARTIFACT-06` CONFIRMED (9, class corrected O3→O2/O5); `F-ARTIFACT-03` **DOWNGRADED** to Medium 8. `F-ARTIFACT-10` and `F-ARTIFACT-12` are post-verification → PENDING/UNVERIFIED.
- **Consolidates:** `F-ARTIFACT-03`, `F-ARTIFACT-04`, `F-ARTIFACT-05`, `F-ARTIFACT-06`, `F-ARTIFACT-10`, `F-ARTIFACT-12` (audit 07).
- **What is wrong:** The store owns version numbering, yet 5 sites hardcode `version=1` and 4 re-derive "latest + 1" from `meta.json`; all are discarded, so a change to honour the caller's field would reset post/validation artifacts to v1. `schema_version` is overloaded across eight axes, three inside the artifact path, and two are written but never validated on read. `SchemaTooNewError` and checksum enforcement are path-dependent (the mutable read path, `load_metadata` and `list_artifacts` bypass the checked reader). Artifact status has two writers with different side effects: `save_mutable` cannot express `APPROVED`, pre-approved saves bypass the deliverable side effect, and `REJECTED`/`ARCHIVED` are unreachable. **The read side is asymmetric in two further ways.** `F-ARTIFACT-10`: the two QC artifact-resolution paths disagree on *which version* is validated — the same artifact identity resolves to different versions depending on which path asks. `F-ARTIFACT-12`: `validate_artifact_id` is called at exactly two sites, both **write-side** (`artifacts/store.py:120`, `:217`), while the read paths `store.py:435`/`:456` build a filesystem path directly from a raw `artifact_id` that arrives unvalidated from `mcp/tools/artifacts.py:57,75` — the charset rule is enforced on the way in and not on the way out.
- **De-facto owners (strongest anchor):** `src/film_pipeline/artifacts/store.py:501` — `phase_order = {name: index for index, name in enumerate(paths.PHASE_DIR_MAP)}`; also `artifacts/store.py:177,251,279-289,558-591`, `artifacts/_layout.py:52-53`, `artifacts/registry.py:162-164`.
- **Drift proof (mutation scenario + asymmetry):** verify-07 confirmed the mutable envelope is read with no `SchemaTooNewError` when the kind's `schema_version` is bumped; the version-law mutation (honour `meta.version`) would reset five sites to v1 and overwrite prior versions.
- **Candidate owner module:** `artifacts.contract` — one `(artifact_id, obj) → version/status/schema-check` law; `save_candidate(...)` fills version/status so callers never compute them.
- **Guard test:** transition-matrix test over every `(from, to)` status pair; "approved implies deliverable" across all writers; a table asserting each kind's `schema_version` is validated on every read path.

### L-39 — Media paths, reference-asset catalog and generated-media policy
- **O-class:** O1 + O4 + O5.
- **Severity:** High (impact 4 × drift 3 = 12). `F-GEN-07` and `-08` were downgraded; `F-GEN-12` (CONFIRMED at 12) keeps the entry at 12.
- **Verification:** MIXED. verify-06: `F-GEN-12` CONFIRMED (denylist/sidecar grammar duplicated 3×; `_asset_kind` returns `generated_clip` for any unknown suffix); `F-GEN-07` **DOWNGRADED** to Medium 6 (drift proof refuted — the named mutation fails a test) and `F-GEN-08` **DOWNGRADED** to High 9 (mutation clause refuted). `F-GEN-15` and `F-GEN-16` are post-verification → PENDING/UNVERIFIED.
- **Consolidates:** `F-GEN-07`, `F-GEN-08`, `F-GEN-12`, `F-GEN-15`, `F-GEN-16` (audit 06).
- **What is wrong:** The canonical `media_scene_dir` helper is dead and import-banned while `ProjectStorage.media_dir` re-implements the convention; reference assets live in a parallel catalog whose paths are re-derived at six sites and never registered in `AssetManifest`; and "which files count as generated media" is decided by a filename denylist in the delivery module while the sidecar grammar is written elsewhere, so any new `.json` companion becomes a generated clip. **Two further copies of the media-writing policy belong here.** `F-GEN-15`: scene-less media is named `unassigned` on disk (the path segment written by `executor_delivery.py:44-46` through `project_storage.py:209-210`) but recorded as `scene_id=""` in the sidecar (`:97`) and in the `AssetEntry` manifest (`:111`) — one asset, two identities, so a scene-less asset cannot be found by the name it is filed under. `F-GEN-16`: the declared invariant that `ProjectStorage` is the only writer under a project root holds only for *imports* of `artifacts.paths`, not for writes — the compositor writes PNG bytes straight to disk via `canvas.save(output_path, "PNG")` in `generation/compositor/extras.py:181-185` (and again in `environment.py:132-133`) with its own `mkdir`, so the storage boundary test cannot see it.
- **De-facto owners (strongest anchor):** `src/film_pipeline/generation/executor_delivery.py:55` — `return ProjectStorage.for_root(root).media_dir(project_id, scene_id, shot_id)`; also `artifacts/paths.py:3-5`, `mcp/tools/reference_generation/entries.py:72-74`, `generation/executor_delivery.py:65-71,132-148`, `generation/frame_sidecar.py:11-13`.
- **Drift proof (existing divergence + mutation):** the reference path never registers anything in `AssetManifest` (verify-06 confirmed the existing divergence), so generated reference frames exist on disk but not in the manifest; adding a `.json` companion in one adapter's `download()` makes `_asset_kind` classify it `generated_clip` and no test covers the function.
- **Candidate owner module:** `artifacts` owns one media/sidecar grammar; `generation-runtime` owns the asset inventory.
- **Guard test:** after a mock reference batch every file under the media root is registered in `AssetManifest`; for each declared sidecar suffix, `_produced_files` excludes it.

### L-40 — Generation-request identity and stale-code sets
- **O-class:** O1 (duplicated normative model) + O4.
- **Severity:** High (impact 3 × drift 4 = 12).
- **Verification:** MIXED. verify-06: `F-GEN-11` CONFIRMED (id-bearing state + `shot_id`-only incoming → 2 entries for one shot; both sides id-less → request silently dropped); `F-CRP-10` is audit 10 → **CONFIRMED by `verify-10`**.
- **Consolidates:** `F-GEN-11` (audit 06); `F-CRP-10` (audit 10).
- **What is wrong:** `generation_requests` identity is defined by two dedup keys: the LangGraph reducer matches on `("generation_request_id", "generation_id", "shot_id")` while `_apply_external_state` uses a two-key version, so a request carrying only `shot_id` is filtered one way and merged another. Separately, the stale generation-request code set is defined three times and emitted a fourth.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/state_schema.py:44` — `for key in ("generation_request_id", "generation_id", "shot_id"):`; also `graph/nodes/_shared.py:163-188`, `mcp/tools/generation/_text_only.py:9`, `app/_resume.py:14`.
- **Drift proof (mutation scenario + reproduced divergence):** verify-06 reproduced the duplicate-entry and dropped-request cases; mutating the stale-code set in one module leaves the other consumers on the old set and no test fails.
- **Candidate owner module:** `generation-runtime` publishes the request identity and the stale-code set; both consumers import them.
- **Guard test:** parameterised over every subset of the three id keys, filter and reducer agree; mutating one stale-code set fails a test asserting the three consumers share one constant.

### L-41 — Cost model: pricing table vs planner artifact ceiling
- **O-class:** O4 (parallel registries) + O5 + O1.
- **Severity:** High (impact 3 × drift 4 = 12).
- **Verification:** MIXED. verify-06: `F-GEN-10` CONFIRMED (rate change 0.18→0.36 doubles every ledger estimate while the ceiling artifact is unchanged); verify-05: `F-PROV-07` **DOWNGRADED in part** (rate duplicate and "unpinned" are true; the O3 quota clause is out of taxonomy and the severity label needed correction).
- **Consolidates:** `F-GEN-10` (audit 06); `F-PROV-07` (audit 05).
- **What is wrong:** Two independent cost models meet at the budget gate: the ledger estimates from `providers/pricing.py` while the graph's ceiling comes from the planner's `cost_estimate` artifact, with the shot-duration default re-derived at four (verify-06 says more) sites. The mock planner response still advertises the old rate, and the provider cost/quota fields are written by three modules with an unpinned duplicate rate literal.
- **De-facto owners (strongest anchor):** `src/film_pipeline/providers/pricing.py:36` — `PROVIDER_PRICING: dict[str, _PricingEntry] = {`; also `generation/ledger.py:99,276`, `graph/nodes/_generation_batch_planning.py:42-45`, `app/mock_responses.py`.
- **Drift proof (mutation scenario, reproduced):** verify-06 changed the rate 0.18→0.36 and observed ledger estimates double while the agent-artifact ceiling is unchanged, so the gate comparison is meaningless.
- **Candidate owner module:** `generation-runtime` owns cost estimation for a batch and one duration constant; `providers/pricing.py` remains the rate authority.
- **Guard test:** mock response costs equal `pricing` costs; the ledger gate and the planner ceiling are computed from the same estimator for a fixture batch.

### L-42 — Checkpoint history: rollback record, invalidation, audit, discovered projects
- **O-class:** O3 + O1 + O4 + O6.
- **Severity:** High (impact 3 × drift 4 = 12).
- **Verification:** CONFIRMED (verify-10: `F-CRP-06/07/08/11` all reproduced); `F-CRP-14` is audit 10's **post-verification** addition (verifier missed-seam M3, promoted to a finding and re-run by the audit's author) → **PENDING/UNVERIFIED**. (`F-CRP-10`, which the verifier downgraded to Medium 3×2=6, is consolidated in `L-40`.)
- **Consolidates:** `F-CRP-06`, `F-CRP-07`, `F-CRP-08`, `F-CRP-11`, `F-CRP-14` (audit 10).
- **What is wrong:** `RollbackRecord` has two authorities that emit different `rollback_id` grammars and different `invalidation_report_ref` values, with no audit event. Invalidation depends on a hand-maintained `DEPENDENCY_GRAPH` rather than the real artifact parentage recorded by the graph, so adding an artifact family under-reports invalidation. Artifact-only ("discovered") projects are adopted and get a checkpoint manager but never restore their checkpoint log, and the project-deletion audit event never reaches disk because persistence is keyed on live registry membership. **`F-CRP-14` is the destructive-operation arm of the same split:** `SafetyService.persist_root()` (`app/safety.py:25-32`) derives the trash base from `resolve_storage_root().resolve().parent` instead of the runtime root actually in use, and `app/safety.py:111` builds `trash_root` from it — so deleting a project created under an explicit `FILM_PIPELINE_RUNTIME_ROOT` archives it into a *different tree* from the one it lived in, which then feeds the same audit/rollback history this entry owns.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/nodes/wrapup.py:30` — `manifest = result.get("assembly_manifest")` (the graph path that records parentage); also `checkpoints/rollback.py`, `schemas/checkpoint.py:60`, `app/runtime.py:173`, `app/_persistence.py`, `app/safety.py:25-32` (`F-CRP-14`'s `persist_root`), `app/safety.py:111`.
- **Drift proof (existing divergence, reproduced by the author):** an archived project's audit log contains only `['create_project']` while the in-memory trail is `['create_project', 'delete_project']`; a discovered project shows `manager registered` but `rt.checkpoints size: 0`. `F-CRP-14` (reproduced end to end, Appendix A.11 of `audit/10`): a project created under an explicit runtime root and then deleted with `force=True` is archived under `resolve_storage_root().resolve().parent / "trash"`, a different tree from `rt.runtime_root` — the deletion archive and the runtime disagree about which root they are operating on, so the rollback/audit history this entry owns can be split across two roots.
- **Candidate owner module:** `runtime_persistence.rollback` (one factory and one audit event) and `artifacts.provenance` (dependency model derived from recorded parentage).
- **Guard test:** after `rollback_to_checkpoint`, exactly one `RollbackRecord` with a real invalidation ref exists and the audit log contains the rollback; adopting a discovered project restores its checkpoint log; create → delete with `force=True` writes both audit events; **plus** (`F-CRP-14`) deletion under an explicit `RUNTIME_ROOT` archives inside that root, not under the storage root's parent.

### L-43 — Persistence flags and entry-point bootstrap
- **O-class:** O5 (one policy decision re-derived at N call sites) + O3 (`F-CRP-13` only: split authority over "may I write durably?").
- **Severity:** **Critical (impact 4 × drift 4 = 16)** — raised from High 12 by `F-CRP-13`. **The band follows from the score by rule, not by preference:** `00-methodology-and-quality-bar.md` §1.5 makes the band a function of the score (`Critical ≥ 16`) and provides that arithmetic wins over a band word. The verifier recorded **High** beside its own recomputed 4×4=16 — one of the five self-contradictions §1.5's round-3 amendment forbids, and precisely the defect class this ledger audits. `audit/10` has since re-stated `F-CRP-13` to Critical citing §1.5 itself, so audit and ledger now agree.
- **Verification:** MIXED. verify-03: `F-CFG-08` CONFIRMED (exactly 7 read sites in 6 modules; conjunction-vs-lone-flag divergence verified); verify-11: `F-MCP-09` CONFIRMED (`cli.run.main` never validates; duplicate of F-CFG-08/F-CRP-09 with a third candidate owner); `F-CRP-09` **CONFIRMED by `verify-10`**; `F-CRP-13` is audit 10's **post-verification** addition (verifier missed-seam M2, promoted to a finding and re-run by the audit's author) → **PENDING/UNVERIFIED**.
- **Consolidates:** `F-CFG-08` (audit 03); `F-CRP-09`, `F-CRP-13` (audit 10); `F-MCP-09` (audit 11).
- **What is wrong:** "Is persistence enabled?" has six readers and two formulas: `app/_persistence.py:51-53` requires `PERSIST_STATE` and not `NO_PERSIST`, `graph/graph.py:43` applies the same conjunction, but `graph/services.py:31,48`, `logging_setup.py:80`, `mcp/server.py:243` and `cli/run.py:226` test `NO_PERSIST` alone. The three entry points (CLI, MCP, `langgraph.json`) each re-derive bootstrap, logging and persistence, and `cli.run.main` never validates the environment. **`F-CRP-13` shows the policy is also *bypassed*, not merely duplicated:** `app/runtime.py:59-63` tests `FILM_PIPELINE_RUNTIME_ROOT` **before** the `elif use_persistent_runtime():` gate, and `:75-77` then builds the services with `artifacts_root=self.runtime_root`, so a runtime whose own policy reports "not persistent" still opens a real on-disk root — `artifacts/storage.py:116-126` writes the durable `storage.json` marker into it and `app/_persistence.py:259-265` funnels `project.json` there. Measured (Appendix A.10): `use_persistent_runtime() = False` while `runtime_root` is a real path, the store root *is* that path, and both the durable project record and the storage marker are written. The storage plan's own bar — "non-persistent invocations never write home or CWD" (`documentation/storage-upgrade-plan.md:297`) — is violated by design, and the §2.1 derivation table has no column for the combination because the branch is about a *root*, not the policy boolean.
- **De-facto owners (strongest anchor):** `src/film_pipeline/app/_persistence.py:51` — `return bool(os.getenv("FILM_PIPELINE_PERSIST_STATE")) and not bool(`; also `app/runtime.py:59-63` (`F-CRP-13`'s pre-gate env branch), `app/runtime.py:75-77`, `cli/run.py:226`, `mcp/server.py:243-244`, `graph/services.py:31,48`, `graph/graph.py:43`.
- **Drift proof (existing divergence):** verify-03 confirmed the conjunction-vs-lone-flag split; with both flags unset, `app/_persistence`/graph report disabled while `cli/run.py:226` reports `persist_enabled=True`. `F-CRP-13` (reproduced end to end, Appendix A.10 of `audit/10`): with `RUNTIME_ROOT` set and the policy reporting *not persistent*, `durable project.json written? = True` and `durable storage marker? = True`. Drift 4 because no test covers the combination — `tests/unit/artifacts/test_storage_guards.py:63` deletes `PERSIST_STATE` but not `RUNTIME_ROOT`, and `tests/unit/app/test_logging_setup.py:148-171` pins both flags but not the root branch.
- **Candidate owner module:** `runtime_persistence.policy` (one `use_persistent_runtime`) and `app.bootstrap` — one `bootstrap(role) -> Runtime` used by all entry points.
- **Guard test:** parametrised over all four flag combinations, every entry point reports the same persistence decision; the string `FILM_PIPELINE_NO_PERSIST` occurs only in the owner module; **plus** (`F-CRP-13`) `RUNTIME_ROOT` set with `PERSIST_STATE` unset ⇒ the resolved policy's mode is not `DURABLE` and no `storage.json`/`project.json` appears under that root (or the explicit promotion contract, if promotion is chosen instead of fail-closed).

### L-44 — MCP confirmation enforcement and dangerous-mutation policy
- **O-class:** O2 + O5.
- **Severity:** High (impact 3 × drift 4 = 12).
- **Verification:** CONFIRMED. verify-11: `F-MCP-01` CONFIRMED (both gates and the lying docstring verified; the handler copy is unreachable via `server.call` and the "not enforced at all" wording is false for the canonical path), `F-MCP-11` CONFIRMED (`resolve_provider_block` ungated).
- **Consolidates:** `F-MCP-01`, `F-MCP-11` (audit 11).
- **What is wrong:** Confirmation is enforced at two sites with two response contracts: `server.py` returns a failed `MCPResponse` with `CONFIRMATION_REQUIRED`, while `mcp/tools/checkpoints.py` returns `{"ok": False, ...}` inside a successful response, and one tool documents enforcement it does not implement. "Which mutations are dangerous" has no owner: `resolve_provider_block` clears a provider block (safety-relevant state) with no gate while comparable state changes are gated by a per-tool `confirm=True` literal.
- **De-facto owners (strongest anchor):** `src/film_pipeline/mcp/server.py:187` — `if registration.contract.requires_confirmation and not arguments.get("confirmed"):`; also `mcp/tools/checkpoints.py:249-254`, `mcp/tools/_profile_change.py:101`, `mcp/tools/registry.py:163-179,332-338`.
- **Drift proof (existing divergence):** verify-11 confirmed both gates and the divergence; calling the checkpoint handler directly with `{}` returns an untyped refusal inside a success response while the server path returns a coded failure; adding `confirm=True` to `resolve_provider_block` changes nothing else.
- **Candidate owner module:** `mcp.policy` — one `authorize(registration, arguments) -> MCPError | None`, and a `Danger` classification derived from behaviour rather than a literal.
- **Guard test:** for the 10 confirm-gated tools, calling each handler directly with `{}` yields a `CONFIRMATION_REQUIRED`-coded refusal in exactly one shape; every tool whose handler clears a safety block is classified `danger`.

### L-45 — `OperatorService` vs MCP and the two project registries
- **O-class:** O6 + O3 + O4.
- **Severity:** High (impact 3 × drift 4 = 12). `F-MCP-06` was downgraded 12→8 as latent; `F-MCP-07` (CONFIRMED at 12) keeps the entry at 12.
- **Verification:** MIXED. verify-11: `F-MCP-07` CONFIRMED (the server registry is populated **only** by the lazy fallback; no agreement test); `F-MCP-06` **DOWNGRADED** to Medium 8 (facts real but entirely latent; O3 label dropped because it is a single writer); `F-MCP-14` post-verification → PENDING/UNVERIFIED.
- **Consolidates:** `F-MCP-06`, `F-MCP-07`, `F-MCP-14` (audit 11).
- **What is wrong:** `OperatorService` is a full second lifecycle that bypasses the confirmation policy the MCP registry declares (approval, revision and real-money spend approval all proceed without `confirmed`) and is the only writer of `project_kind`, so `can_delete_project` returns True for an MCP-created project and False for an operator-created one — deletion safety is path-dependent. Separately, two project registries (MCP envelope registry and `StudioRuntime.projects`) must agree but are reconciled only lazily by an auto-register fallback, and `MCPServer.active_project_id` is a write-only shadow of the runtime's active project.
- **De-facto owners (strongest anchor):** `src/film_pipeline/app/services/operator.py:318` — `def approve_phase(self, project_id: str | None = None) -> MutationResult:`; also `mcp/tools/registry.py:169`, `app/services/operator.py:125`, `app/safety.py:131-132`, `mcp/server.py:44,142-177`.
- **Drift proof (existing divergence):** verify-11 confirmed the server registry is populated only by the lazy fallback and that no agreement test exists; the same project is deletable when created via MCP (`project_kind=""`) and protected when created via the operator (`"production"`).
- **Candidate owner module:** `mcp.policy` (confirmation classification) + one `ProjectCatalog` in `app` that always writes `project_kind` and is read by `mcp`.
- **Guard test:** create a project through each path and assert equal states for safety-relevant keys; after any create, `set(server.projects) == set(rt.projects)` with no fallback needed.

### L-46 — Profile-stack keys, writers and `resolved_review_strategy`
- **O-class:** O1 + O3 + O8.
- **Severity:** High (impact 4 × drift 3 = 12).
- **Verification:** CONFIRMED. verify-03: all three findings CONFIRMED (`F-CFG-07` mutation mechanics verified, `F-CFG-09` three writers verified, `F-CFG-10` exactly three occurrences and no production writer).
- **Consolidates:** `F-CFG-07`, `F-CFG-09`, `F-CFG-10` (audit 03).
- **What is wrong:** The profile-stack key set is defined three times (resolver mapping, merge order, `_PROFILE_STACK_KEYS`), so a new slot accepted by `propose_profile_change` is silently ignored by `resolve_project_config`. `profile_stack` has three writers that disagree about the environment override (the operator path re-derives the quality slot from resolved config; the MCP path re-derives it differently). `resolved_review_strategy` is read by agent routing but written by nothing and has no profile key.
- **De-facto owners (strongest anchor):** `src/film_pipeline/app/services/operator.py:143` — `state["profile_stack"] = profile_stack`; also `config/profile_resolver.py:34-40,51-68`, `mcp/tools/projects.py:107-113`, `graph/_agent_routing.py:204-211`, `schemas/project.py:62`.
- **Drift proof (existing divergence + mutation):** verify-03 verified the three writers and that `projects.py:107-113` applies an env correction while `operator.py:143` does not; adding a sixth slot to `_profile_change.py:36-42` is accepted and stored but ignored by resolution.
- **Candidate owner module:** `config` — one `PROFILE_STACK_SLOTS` ordered tuple with the mapping, merge order and keys derived from it, plus a single `apply_env_overrides_to_stack()`; `resolved_review_strategy` gets a writer or is deleted.
- **Guard test:** pushing a slot through `propose_profile_change` changes the resolved stack; both entry points produce an identical `profile_stack` for one env; the key read at `_agent_routing.py:208` is written by some module.

### L-47 — Test harness: store factory, fixtures, git double, separation guard, protocols
- **O-class:** O2 + O1 + O5 + O8.
- **Severity:** High (impact 3 × drift 4 = 12).
- **Verification:** MIXED. verify-13: `F-TEST-03` CONFIRMED (12), `F-TEST-04` CONFIRMED (10), `F-TEST-05` CONFIRMED (6), `F-TEST-06` CONFIRMED (12), `F-TEST-08` CONFIRMED (8); `F-TEST-09` and `F-TEST-11` are post-verification → PENDING/UNVERIFIED.
- **Consolidates:** `F-TEST-03`, `F-TEST-04`, `F-TEST-05`, `F-TEST-06`, `F-TEST-08`, `F-TEST-09`, `F-TEST-11` (audit 13). (`F-TEST-10` is consolidated in L-09; `F-TEST-02` is withdrawn.)
- **What is wrong:** `make_store`/`sandbox_store_root` is bypassed by 64 direct `ArtifactStore(root=...)` constructions that silently stamp the production profile while the sandbox marker they write is read by nothing. Fixture construction is re-implemented per tier and the e2e fixture bypasses the production composition root it is supposed to stand in for, while "how a test supplies the runtime to MCP tools" has no owner. The session-wide `InMemoryGitBackend` replaces the only writer of checkpoint state with no parity test against `GitBackend`, and the e2e tier can still build a real backend. The production-separation invariant is enforced in three places with different scopes, and the primary guard has no test and compares path→size only. `GraphServices` seams have no protocol; two same-named `FakeArtifactStore` classes already disagree on constructor and method set.
- **De-facto owners (strongest anchor):** `tests/conftest.py:75` — `from film_pipeline.testing.in_memory_git import InMemoryGitBackend`; also `tests/conftest.py:51,78,121-125`, `testing/storage.py:17`, `artifacts/store.py:60-61`, `tests/e2e/conftest.py:135,155-156`, `graph/services.py:62-63`.
- **Drift proof (existing divergence):** verify-13 confirmed `grep -rn "InMemoryGitBackend" src tests` matches only its module and the conftest install — no test constructs it; deleting the separation guard leaves the suite green; the two fakes expose `load_ref` vs `list_artifacts`.
- **Anti-rot evidence — corrected (`orchestrator-verification-notes.md` V9).** This ledger does **not** claim that the orphaned `tests/unit/__pycache__/test_guard_canary.cpython-312-pytest-9.1.1.pyc` proves "a guard canary was silently deleted in this repo". That reading is wrong and V9 retracts it: the file was created **2026-09-25 12:41**, inside this program's own session, by our enforcement-prototype subagent, and `git log --all -- '*test_guard_canary*'` is empty because it was never tracked (`__pycache__/` is gitignored at `.gitignore:5`). The measured replacement, **independently re-derived here and matching V9 exactly**: an orphaned-bytecode sweep (a `.pyc` whose source no longer exists) finds **18** files under `tests/` — **10** removed by the traceable TUI refactor `37e9c65` (`refactor(tui): remove TUI package, tests, entry point, and textual dependency`: the five `tests/e2e/test_tui_*.py` sources plus `tests/integration/cli/conftest.py`), **6** tracked helpers that moved or were renamed (`tests/unit/graph/_helpers.py`, `tests/unit/mcp/tools/test_helpers.py`, `tests/unit/generation/_helpers.py`, …), **1** never tracked (`tests/unit/artifacts/test_migration.py`), and our own prototype canary. Nothing cleans them and nothing enumerates the test set as data, so a guard file's disappearance leaves no trace. That is the verified motivation for a guard *registry* (a set that fails when a guard family disappears), and it is stronger than the retracted claim — one stale bytecode file would have been trivia; eighteen with three distinct causes is evidence of a missing inventory.
- **Candidate owner module:** `testing.harness` + `testing.doubles.git` + `testing.protocols` — one store factory, one runtime factory, one backend parity suite, one separation guard with a self-test, and declared `Protocol`s for `GraphServices`.
- **Guard test:** no `tests/**` module constructs `ArtifactStore` directly; the git parity suite runs both backends through one contract fixture; a deliberately same-size write trips the separation guard; both fakes satisfy the declared protocol.

### L-48 — Module dependency law, enforcement and private reach-ins
- **O-class:** O7 (leaked internals) + O8 (missing contract) + O5.
- **Severity:** High (impact 3 × drift 4 = 12) — **corrected** by verify-14; the audit printed High beside `4 × 4 = 16`, which §1.5 makes Critical.
- **Verification:** CONFIRMED/CORRECTED (`reviews/verify-14.md`, plus the orchestrator's V3/V4 measurements). `F-BOUNDARY-01` **CONFIRMED (substance)** with corrections (the "8 forbidden edges" list is the union of three targeted greps, not a count; severity recomputed High 3×4=12); `F-BOUNDARY-02` **DOWNGRADED** (O1 rejected; façade incompleteness is the real divergence; Medium 3×3=9); `F-BOUNDARY-04` **CONFIRMED (core)**, severity recomputed High 3×4=12; `F-BOUNDARY-05` **CONFIRMED (offenders real)** but the stated `Reproduce` command is broken and two `app→graph` private-symbol sites are missing — High 12 once corrected.
- **Consolidates:** `F-BOUNDARY-01`, `F-BOUNDARY-02`, `F-BOUNDARY-04`, `F-BOUNDARY-05` (audit 14).
- **What is wrong (edge count, re-measured).** The `AGENTS.md:51` domain-isolation law is prose only. The audit listed **eight** example domain→domain edges (`agents→providers`, `config→providers`, `generation→providers`, `generation→artifacts`, `post→validation`, `testing→artifacts`, `testing→checkpoints`, `testing→providers`), but that list is a union of three targeted greps and is not the count. An AST sweep performed for this ledger finds **53 distinct cross-package import edges** in `src/film_pipeline/`, of which **32 have a source outside `graph`/`mcp`** (the two packages the law exempts), **21 survive removing `schemas` as a target**, and **17 survive removing `artifacts` too** — so even a domain-isolation rule with a `schemas`/`artifacts` allowance has at least 17 violations. The `AGENTS.md` prose also says "12 packages" when 17 exist. Enforcement is two bespoke per-package AST suites, so adding a forbidden import elsewhere fails nothing.
- **What is wrong (private reach-ins, re-measured).** The `schemas.__init__` façade is incomplete — `TRANSITION_TYPES` and `LEGACY_TRANSITION_ALIASES` are importable only from the private `schemas._base`. Measured: **107 reach-in sites**, of which **106 import `schemas._base`** and **1 imports `app._persistence`** (`mcp/server.py:248`); they live in **73 distinct files, every one of them outside `schemas/`**. Separately, **3 sites import a private *symbol* across a package boundary**: `config/profile_resolver.py:204 → providers.credentials._env_var_for`, and `app/_graph_exec.py:319 → graph.nodes._run_validators` / `:449 → graph.nodes.approval._PHASE_NODES` (the last two found by the verifier). `schemas` is imported via `ImportFrom` **322** times in total — **252 cross-package and 70 intra-package** — which is the blast radius any façade change is exposed to.
- **De-facto owners (strongest anchor):** `src/film_pipeline/agents/runner.py:17` — `from film_pipeline.providers.failure_classifier import (`; also `schemas/_base.py`, `schemas/__init__.py:25-28`, `tests/unit/artifacts/test_storage_boundary.py:1`, `tests/unit/graph/test_startup_boundaries.py:1`.
- **Drift proof (existing divergence / mutation):** verify-14 independently confirmed the façade incompleteness (`TRANSITION_TYPES`, `LEGACY_TRANSITION_ALIASES` absent from `schemas/__init__.py`); adding `from film_pipeline.validation.impl.assembly import AssemblyValidator` to `post/subtitle_agent.py` fails nothing, and with 17 non-exempt domain→domain edges already present the law's own subject matter is unenforced. The exact permitted-edge matrix is **undefined pending `03-target-architecture.md`**, so this entry asserts the *absence of an enforcement point* rather than a specific allowed set.
- **Candidate owner module:** `module-law` — one declarative edge matrix + one guard suite (no runtime import target); `schemas/__init__.py` becomes the complete public contract.
- **Guard test:** one edge-matrix test covering all 17 packages; an AST test that every cross-package private import is either promoted or failing; a façade-completeness test that every name outsiders import from `schemas._base` is bound in `schemas/__init__`.

### L-49 — Router action vocabulary vs the edge transition table
- **O-class:** O8 (missing contract between two registries).
- **Severity:** High (impact 3 × drift 3 = 9).
- **Verification:** CONFIRMED. verify-01 reproduced the existing gap (`after_phase` → `consistency_check`) but found the mutation clause false (changing the literal at `_action_routing.py:221` does affect tests).
- **Consolidates:** `F-PHASE-06` (audit 01).
- **What is wrong:** The router emits `escalate_to_failure_handler`, but neither `_HUMAN_GATE_ACTIONS` nor `_REPAIR_ACTIONS` declares it and no graph node handles it; `after_phase` routes it through the catch-all fallback to `consistency_check`, silently converting a failure escalation into a human gate. Coverage is by fallback, not declaration.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/_action_routing.py:220` — `eligible=["escalate_to_failure_handler", "escalate_to_human"],`; also `graph/edges.py:29-37,86-87`, `graph/graph.py:102-125`.
- **Drift proof (existing gap, reproduced):** verify-01 confirmed `after_phase` converts the escalation to `consistency_check`; a new declarative action string added to the router is absorbed by the same fallback until a graph node exists.
- **Candidate owner module:** `phase-model` — one declared `ACTION → destination` table covering every action `compute_actions` can emit.
- **Guard test:** the set of `next_action` literals emitted by `_action_routing.py` is a subset of the edge table's declared actions (not the fallback).

### L-50 — Orchestrator key grammar and `_orchestrator__` literals
- **O-class:** O1 (duplicated normative model) + O7 (leaked internals).
- **Severity:** High (impact 3 × drift 3 = 9).
- **Verification:** CONFIRMED-WITH-FIX. verify-02: `F-OST-01` drift proof valid but "eleven keys" is 10; `F-OST-11` mutation valid but a claimed grep is false.
- **Consolidates:** `F-OST-01`, `F-OST-11` (audit 02).
- **What is wrong:** The orchestrator channel-key set is defined twice (a constants tuple and the `TypedDict`), and parity is checked in one direction only, so a new domain can be added to the owner without a schema row or vice versa (verify-02 confirmed LangGraph silently drops the un-declared key). The `_orchestrator__` prefix grammar is re-derived by three consumer modules and by tests, because the owner publishes no accessor — the private key spelling has become the public contract.
- **De-facto owners (strongest anchor):** `src/film_pipeline/graph/orchestrator_state.py:23` — `_ORCH_NS = "_orchestrator"`; also `graph/orchestrator_state.py:43-59`, `tests/unit/graph/test_real_human_gates.py:128`, `tests/integration/test_dynamic_routing.py:195`.
- **Drift proof (mutation scenario):** adding a domain constant plus an `ORCH_CHANNELS` row passes both existing parity tests because each checks only one direction, and the `TypedDict` stays stale.
- **Candidate owner module:** `graph/orchestrator_state.py` — one registry row set and published key accessors; literals stay private.
- **Guard test:** `test_orchestrator_key_sets_are_identical` (both directions); the string `_orchestrator__` occurs only in the owner module and its accessors.

### L-51 — Four prompt renderers and two JSON-recovery strategies
- **O-class:** O2 (duplicated invariant enforcement).
- **Severity:** High (impact 3 × drift 3 = 9).
- **Verification:** CONFIRMED (dispute). verify-04: four divergent renderers and the dead `prompt_runner.build` branch hold, but drift-proof item 3 is false — `schemas/prompt.py` *is* referenced by tests; `F-AGENT-07` CONFIRMED.
- **Consolidates:** `F-AGENT-06`, `F-AGENT-07` (audit 04).
- **What is wrong:** Four RCTCO renderers emit the same framework with different section labels, orders and substitution mechanisms (`replace` vs `format_map`), one of which is a dead runner branch; the live validator renderer duplicates the template renderer. Model-output JSON recovery is implemented twice with different strategy sets: the agent extractor has a bracketed-array strategy the validator path lacks, and the validator tries fence spellings the extractor does not.
- **De-facto owners (strongest anchor):** `src/film_pipeline/agents/runner.py:43` — `self.rendered = "\n\n".join(`; also `schemas/prompt.py` (`RCTCOPrompt.render`), `validation/base.py:231-234`, `agents/_json_extraction.py:15-86`.
- **Drift proof (existing divergence):** verify-04 verified the 4-strategy vs 3-strategy vs 1-unwrap divergence; the same model output recovers under `_json_extraction` and raises `ValueError` under `_parse_validation_response`.
- **Candidate owner module:** `agents.prompt_templates` — one `render()`/section grammar and one JSON-recovery function with an injectable strategy list.
- **Guard test:** golden-text test comparing all call sites' rendered prompts; a table-driven test asserting every recovery strategy is reachable from both the agent and validator paths.

### L-52 — MCP error taxonomy bypassed; dead contract state
- **O-class:** O1 + O8.
- **Severity:** High (impact 3 × drift 4 = 12). Raised to 12 by the post-verification `F-MCP-13` (12); verify-11 confirmed `F-MCP-10` at 9 and `F-MCP-08` at 8.
- **Verification:** MIXED. verify-11: `F-MCP-08` CONFIRMED (`envelope.py:28` declared, never read/written), `F-MCP-10` CONFIRMED (zero handler-side codes); `F-MCP-13`, `F-MCP-15` post-verification → PENDING/UNVERIFIED.
- **Consolidates:** `F-MCP-08`, `F-MCP-10`, `F-MCP-13`, `F-MCP-15` (audit 11).
- **What is wrong:** `MCPErrorCode` is defined but no tool handler raises or uses it — handlers return `{"ok": False, "error": message}` and clients keying on `error.code` cannot distinguish failure classes; the only transport then flattens the typed code away again and adds no actor attribution. `RequestEnvelope.requires_confirmation` and `ToolContract.idempotency_key_field` are dead declared-but-unenforced contract state, so a reader who trusts them looks for behaviour that does not exist.
- **De-facto owners (strongest anchor):** `src/film_pipeline/mcp/errors.py:15` — `VALIDATION_ERROR = "validation_error"`; also `mcp/tools/helpers.py:33-35`, `mcp/server.py:216-223`, `mcp/envelope.py:28`, `mcp/contract.py:57`, `mcp/_stdio_transport.py:62-65`.
- **Drift proof (mutation scenario):** verify-11 added no handler-side code usage — `grep -rn "MCPErrorCode\." src/film_pipeline/mcp/tools/` is empty, so a new code cannot be used by a handler.
- **Candidate owner module:** `mcp.contracts` — `_error` builds a typed `MCPError` with a required code; delete the dead envelope/contract fields.
- **Guard test:** no handler returns `{"ok": False}` without a code; the transport propagates the typed code; `requires_confirmation`/`idempotency_key_field` each appear in exactly one enforcing module.

### L-53 — `profiles/` location and hardcoded numeric defaults
- **O-class:** O7 + O8 + O5.
- **Severity:** High (impact 3 × drift 3 = 9).
- **Verification:** CONFIRMED. verify-03: `F-CFG-12` (both `Path("profiles")` sites and all 5 submodule imports reproduce) and `F-CFG-13` (`"duration_seconds", 5` returns exactly the 9 cited sites) both CONFIRMED.
- **Consolidates:** `F-CFG-12`, `F-CFG-13` (audit 03).
- **What is wrong:** The `profiles/` corpus root is resolved relative to the process CWD in two modules that never consult each other, with different error messages for the same missing corpus, and `config`'s public API omits its own resolver. Hardcoded numeric defaults duplicate profile values: deadness is codified in `KNOWN_DEAD_GROUPS` (`generation.duration_seconds`, `search_api`, `review.strategy`, …) and the previous "300" runtime fallback is now three sites — worse than the prior record.
- **De-facto owners (strongest anchor):** `src/film_pipeline/config/loader.py:30` — `profiles_dir: Path = Path("profiles")`; also `app/bootstrap.py:34`, `profiles/base.studio.yaml:89`, `agents/impl/intake_agent.py:79`, `agents/impl/structure_extractor_agent.py:16`, `graph/nodes/_context.py:70`.
- **Drift proof (mutation scenario):** verify-03 confirmed the 9 `duration_seconds` readers; setting `generation.duration_seconds: 12` in a quality profile leaves the effective default at 5 and no test fails.
- **Candidate owner module:** `config` — owns the corpus root (absolute, overridable) and the numeric defaults; runtime modules take resolved values.
- **Guard test:** running any entry point from a subdirectory resolves the same corpus and error; for each profile numeric key either a test proves it reaches its consumer or it is deleted.

### L-54 — `film_pipeline.testing` ships and is a cross-domain consumer
- **O-class:** O8 (missing contract) + O7.
- **Severity:** High (impact 3 × drift 3 = 9). **The band follows from the score by rule (`00` §1.5):** `High` is 9–15, so a 3×3=9 finding is High. Both the audit and `verify-14` recorded **Medium** here — a verifier band word contradicting its own recomputed score, one of the five self-contradictions §1.5's round-3 amendment forbids. This ledger recorded High from revision 1 for that reason, and the audit has since re-stated `F-BOUNDARY-06` to High, so all three now agree. The episode is the case for the mechanical band check above: two agents independently making the same relabelling error is invisible to review and visible to an invariant.
- **Verification:** CONFIRMED (`reviews/verify-14.md`), with two citation corrections (the coverage `omit` list has two entries; the referenced `04-extraction-roadmap.md` does not exist).
- **Consolidates:** `F-BOUNDARY-06` (audit 14).
- **What is wrong:** The `testing` package is inside the shipped wheel (`packages = ["src/film_pipeline"]`), is the only `src` package excluded from coverage (along with `mcp/tools/__init__.py`), and imports three domains (`artifacts`, `checkpoints`, `providers`), so test doubles are part of the production artifact and their contracts are unowned.
- **De-facto owners (strongest anchor):** `src/film_pipeline/testing/storage.py:11` — `from film_pipeline.artifacts.storage import PROFILE_SANDBOX, init_storage_root`; also `testing/in_memory_git.py:29`, `testing/scenarios.py:5`, `pyproject.toml:59,95-98`.
- **Drift proof (existing divergence):** `tests/unit/graph/test_startup_boundaries.py` exists because `testing` once leaked into production startup; the guard covers `graph` only, so a new `app`→`testing` import is unguarded (verify-14 confirmed the counts and anchors).
- **Candidate owner module:** keep one `testing` package but give it a declared contract (or move it out of the wheel) — decision deferred to `03`.
- **Guard test:** no production package imports `testing` (extend the startup-boundary suite to all packages); the shipped wheel contains no `testing` module.

### L-55 — `next_action` → operator prose and routing-decision channels
- **O-class:** O5 (policy-by-branch) + O1 + O3.
- **Severity:** Medium (impact 2 × drift 4 = 8).
- **Verification:** CONFIRMED. verify-02: `F-OST-09` CONFIRMED (both renderers present, `operator._recommendation` has no test); `F-OST-16` CONFIRMED-WITH-FIX (channel split reproduced, one wrong file anchor).
- **Consolidates:** `F-OST-09`, `F-OST-16` (audit 02).
- **What is wrong:** `next_action` → human prose is re-derived in two modules: the operator recommendation collapses `wait_for_human` and `present_review_package` into one string and has no branch for `revise`, while the MCP renderer distinguishes them and adds two more actions; a new action produces generic text on one surface. Routing decisions are recorded in two channels and the operator-facing readers use the empty one, so `route_reason` is always blank on the dashboard.
- **De-facto owners (strongest anchor):** `src/film_pipeline/mcp/tools/review.py:120` — `def _build_orchestrator_recommendation(state: dict[str, Any], router_result: Any) -> str:`; also `app/services/operator.py` (`_recommendation`), `graph/orchestrator_state.py:43,330-338`.
- **Drift proof (existing divergence, visible without a test):** verify-02 reproduced the channel split and `None []`; a handoff record in `{"_routing_decisions": [...]}` leaves `get_latest_routing_decision` returning `None` because it reads `_orchestrator__routing_decisions`.
- **Candidate owner module:** `graph/router.py` — publish `describe_action(next_action) -> str`; `graph/orchestrator_state.py` — one routing-decision channel.
- **Guard test:** iterating the action vocabulary, every surface yields non-generic text; a handoff record makes `get_orchestrator_summary()["route_reason"]` non-empty.

### L-56 — Ledger read path creates the ledger (write-on-read)
- **O-class:** O5 (policy-by-branch) + O7.
- **Severity:** Medium (impact 2 × drift 3 = 6).
- **Verification:** CONFIRMED. verify-06: `ledger.load` creates+persists on `FileNotFoundError` (`ledger.py:59-60`); the graph read path calls it unguarded (`generation.py:44`); `has_ledger` is used only by the executor.
- **Consolidates:** `F-GEN-13` (audit 06).
- **What is wrong:** The generation executor documents `has_ledger` as a precondition for read paths, but the graph's read at `graph/nodes/generation.py:44` calls `mgr.load`, which persists a new empty ledger artifact when none exists. Reading a project's generation status therefore mutates durable storage and creates an authoritative-looking empty ledger.
- **De-facto owners (strongest anchor):** `src/film_pipeline/generation/executor.py:310` — `Read paths must check this first: the ledger manager's ``load``; also `generation/ledger.py:59-60`, `graph/nodes/generation.py:44`.
- **Drift proof (mutation scenario):** running the generation node on a project with no ledger leaves a new ledger artifact on disk; no test asserts the directory is unchanged (verify-06 confirmed).
- **Candidate owner module:** `generation-ledger` exposes `load_or_none` and `ensure`; only planning may call `ensure`.
- **Guard test:** reading a project with no ledger leaves the artifact directory unchanged.

### L-57 — Ref-string formatter duplicated
- **O-class:** O1 (duplicated normative model).
- **Severity:** Medium (impact 2 × drift 4 = 8) — **raised from 6** by verify-07's "corrected upward within the same band".
- **Verification:** CONFIRMED with correction. verify-07: `F-ARTIFACT-01` CONFIRMED, severity corrected upward within the Medium band; dispute D1 requires deleting the claim that `tests/unit/review/test_diff.py:20-33` shows `from_string` accepting ids the writer rejects. *(Anchor corrected by `reviews/anchor-check-02.md`: `from_string` appears nowhere in `tests/unit/review/test_diff.py`; the real reference-parsing tests are `tests/unit/artifacts/test_refs.py:12,33`. The claim is deleted, so the citation is retained only as a record of what was withdrawn.)*
- **Consolidates:** `F-ARTIFACT-01` (audit 07).
- **What is wrong:** `ArtifactRef.from_string` is the single parser (10 call sites), but the string form is written in two places: the canonical `ArtifactRef.to_string` and `review/diff._id_stem`'s `artifact:<phase>:<id>` stems, with two wrapper re-declarations. The id charset is enforced only on write.
- **De-facto owners (strongest anchor):** `src/film_pipeline/schemas/artifact.py:28` — `return f"artifact:{self.phase}:{self.artifact_id}:v{self.version}"`; also `review/diff.py:70`, `tests/unit/review/test_diff.py:10-19`.
- **Drift proof (mutation scenario):** verify-07 confirmed the duplication; changing the segment scheme in `ArtifactRef.to_string` changes every ref written by `store.save` while `review/diff.py` keeps emitting the old stem.
- **Candidate owner module:** `artifacts.contract` — one ref format/parse/stem implementation; delete the wrappers.
- **Guard test:** `ArtifactRef.from_string(r).stem()` equals the version-stripped form for a table of refs; a duplicate-normative test greps for a second `f"artifact:` literal.

### L-58 — "Requires human review" derived twice
- **O-class:** O1 (duplicated normative model).
- **Severity:** Medium (impact 2 × drift 3 = 6). The audit printed **Low**; verify-08 confirmed `2×3=6` is **Medium** under §1.5 (4–8), so this is a rubric correction.
- **Verification:** CONFIRMED with severity correction. verify-08: `F-VR-11` seam real; severity mislabeled Low.
- **Consolidates:** `F-VR-11` (audit 08).
- **What is wrong:** `ValidationReport.requires_human_review` is derived inline in `validation/base.py` and again as an exported helper in `validation/thresholds.py`; neither the report field nor the helper predicates have a consumer, so the two rules can diverge unnoticed.
- **De-facto owners (strongest anchor):** `src/film_pipeline/validation/base.py:286` — `requires_human_review=status`; also `validation/thresholds.py:32-40`.
- **Drift proof (mutation scenario):** change `thresholds.needs_human_review` to include `PASS_WITH_NOTES` — `base.py:286-290` keeps the old rule and nothing consumes the field.
- **Candidate owner module:** `validation/thresholds.py` — owns both the mapping and the predicates.
- **Guard test:** `report.requires_human_review == needs_human_review(report.score, entry.thresholds)`.

---

## Category separation

### (a) Defects — owners already disagree and behaviour is wrong today (47)

These are bugs, not refactor targets. Each cites its executed/observed divergence in
the entry above; a verifier `CONFIRMED` or reproduced it unless noted.

`L-01` (caps and gates disagree; no spend recorded) · `L-02` (wrong model runs for 2 agents) ·
`L-03` (MCP real-model path raises `AttributeError`; two lifecycles) · `L-04` (`assembly_manifest`
written with incompatible schemas) · `L-05` (complete package blocked by its own validator; delivery
validator has no artifact) · `L-06` (approval launches paid generation while a provider is blocked) ·
`L-07` (declared outputs ≠ implementation; 7 of 11 agents would fail their own guards) ·
`L-08` (MCP submit sends `prompt_ref`; MCP poll completes without media) ·
`L-09` (routing reads a snapshot nothing writes) · `L-10` (consensus never runs; phantom route key; QC refs cross the boundary via a private tuple) ·
`L-11` (CLI poisons the shared storage root; a bare `import film_pipeline.graph.graph` does too, at import time, and then bricks the root) · `L-12` (destructive tools ungated outside stdio) ·
`L-13` (declared vs executed validator contracts differ; delivery validator missing from QC; 4 of 6 declared MCP phases unreachable and reported as success) ·
`L-14` (`NEEDS_REVISION` unreachable for all 22 explicit literals; score 70 → `BLOCKED`) · `L-16` (illegal ledger transitions
persist; matrix says generated before media exists) · `L-17` (two QC implementations with different
coverage) · `L-18` (`artifact_type: script` persisted for `consensus_report`/`cost_estimate`; a `MatrixPatch` declared a consensus report; `AssetEntry.kind` spells `clip` as `generated_clip`) ·
`L-19` (production KB packet is synthetic; content never rendered) · `L-20` (provenance null on 11
write paths; mutable read drops it) · `L-21` (rollback validates and executes against different
registries) · `L-23` (all 77 tools advertise `inputSchema: {}`) · `L-25` (festival/free conflict
undetected for all-mock stack) · `L-26` (stall thresholds 5 vs 3 already disagree) ·
`L-27` (classifier dead; failure escalation unreachable) · `L-28` (duplicate registration silently
overwrites; capability enforcement absent; Gemini base URL declared in three layers) · `L-29` (two adapters disagree on credential freshness) ·
`L-30` (manifest agent ids match no registered agent) · `L-31` (multiple gate-decision copies; gate
vocabulary bypasses its schema) · `L-33` (canned payload contradicts the template; mock entries
disagree) · `L-35` (approve veto scopes already differ) · `L-36` (stale BLOCKED report survives the
manual path) · `L-37` (6 of 7 validator templates unreachable) · `L-38` (version/schema/status law
bypassed on several paths) · `L-39` (reference assets unregistered; `.json` companion classified as
media; scene-less asset filed as `unassigned` but recorded `scene_id=""`; compositor writes PNGs
outside `ProjectStorage`) · `L-41` (mock price stale vs pricing table) · `L-42` (delete audit event never persisted;
discovered project never restores; deletion archives cross-root) · `L-43` (six persistence readers, two
formulas; `RUNTIME_ROOT` bypasses the policy gate so a "non-persistent" runtime writes durably) · `L-44`
(two confirmation contracts; provider-block clearing ungated) · `L-45` (deletability path-dependent;
two project registries) · `L-46` (three `profile_stack` writers disagree) · `L-47` (production
profile stamped by 64 test sites; two fakes disagree) · `L-48` (17+ non-exempt domain→domain edges; façade incomplete; 107 private
reach-in sites) · `L-49` (`escalate_to_failure_handler` silently becomes a human gate) ·
`L-51` (four prompt grammars; divergent JSON recovery) · `L-52` (handler failures outside the error
taxonomy) · `L-53` (dead profile values codified; `300` now 3 sites) · `L-55` (dashboard action text
wrong; `route_reason` always blank).

### (b) Drift risk — owners agree today, nothing prevents divergence (11)

`L-15` (11 phase definitions agree by convention; mutation ends the run early) ·
`L-22` (resume payload keyed by string literals at both ends; one-sided rename silent) ·
`L-24` (YAML and code model profiles byte-identical; verify-03 confirms the YAML reaches some
callers, so the risk is latent rather than live) ·
`L-32` (number-word tables byte-identical; adding a word splits them) ·
`L-34` (all 11 gate values agree; nothing compares the three copies) ·
`L-40` (dedup keys and stale-code sets differ in shape but agree on current data) ·
`L-50` (orchestrator key sets agree; parity is one-directional) ·
`L-54` (`testing` contract gap; guarded today only for `graph` startup) ·
`L-56` (write-on-read is latent until a no-ledger project is read) ·
`L-57` (ref formatter duplicates the canonical form but agrees on current refs) ·
`L-58` (review predicate duplicates but has no consumer).

### (c) Previously-recorded `documentation/audit-findings.md` findings now FIXED at HEAD

Listed so this ledger does not over-claim. "FIXED" means the specific behaviour
the prior audit recorded is not reproducible at `fb85baa`; several leave a
*residual* seam that this ledger still carries.

| Prior `documentation/audit-findings.md` item | Status at HEAD | Evidence | Residual in this ledger |
|---|---|---|---|
| `:40` `requires_confirmation` declared but never enforced | **FIXED** | `mcp/server.py:187` enforces the gate; verified by `tests/unit/test_mcp.py:282-289` | enforcement is split across two sites → `L-44` |
| `:54` `after_phase()` / `compute_actions()` unwired | **FIXED** | `graph/edges.py:15,64` imports and calls `compute_actions`; router is live | action vocabulary gap → `L-49` |
| `:56` all `subgraphs/*.py` are one-line stubs | **FIXED** | `graph/graph.py:115` compiles `build_qc_subgraph()`; `graph/subgraphs/qc.py` is a real graph | parallel QC lifecycle → `L-17` |
| `:59` `generation_node`/`post_node`/`delivery_node` empty shells | **FIXED** | `graph/nodes/generation.py:44` reads the generation ledger | ledger state machine → `L-16` |
| `:82` `ArtifactStore.save_dict()` allows raw dicts across the boundary | **FIXED** | `grep -rn "save_dict" src/` → 0 hits | — |
| `:83` `save()` always writes `CANDIDATE`; no `approve`/`supersede` | **FIXED** | `artifacts/store.py:558-591` persists status transitions (audit 07:398) | pre-approved saves still bypass the deliverable side effect → `L-38` |
| `:85` phase-to-directory mapping duplicated between `store.py` and `paths.py` | **FIXED** | `store` now uses `paths.PHASE_DIR_MAP` (audit 07:176) | order authority still split → `L-15` |
| `:96` `score_to_status` ignores `review_at`, `NEEDS_REVISION` unreachable | **FIXED (mechanism)** | `validation/thresholds.py:25` now reads `review_at` (audit 08:340) | unreachable through the empty band instead → `L-14` |
| `:98` `generation_node` never consults the ledger; ledger MCP-only | **FIXED** | graph reads the ledger (audit 06:630); operator path uses `GenerationExecutor` (audit 11:231) | write-on-read → `L-56`; two lifecycles → `L-08` |
| `:116` checkpoint metadata in-memory only | **PARTIALLY FIXED** | JSONL append exists at `app/_persistence.py:236` (audit 10:359) | two-registry split → `L-21` |
| `:117` rollback without confirmation | **FIXED** | `mcp/tools/checkpoints.py:249-254` (audit 10:442, 539) | rollback record/audit split → `L-42` |
| `:129` `runtime.approve_phase` catches `Exception`, falls back to manual advance | **NARROWED** | `app/_graph_exec.py:216-229` re-raises; fallback gated on an empty snapshot (audit 10:490) | stalled trigger still advances manually → `L-22` |
| `:127`/`:31` TUI bypasses MCP via `InProcessStudioGateway`/`OperatorService` | **FIXED by removal** | no `tui` package under `src/film_pipeline/`; `git grep InProcessStudioGateway HEAD` → empty (audit 11:128-130) | latent `OperatorService` seam → `L-45` |
| `:130` dead code `_load_graph_state`, `_approve_current_phase` | **FIXED** | `grep -rn "_load_graph_state\|_approve_current_phase" src/` → 0 hits | dead `checkpoints/resume.py` is new → `L-22` |
| `:139`/`:15` coverage 87.43 %, below the 90 % gate | **FIXED** | baseline `make ci-check` green at 91.58 % (`01-ownership-map.md:9-11`) | — |
| `:146` `Makefile` `ci-check` omits `typecheck` | **FIXED** | `Makefile:108` runs `format-check lint typecheck test-cov build product-gate` | — |
| `:45` `version=1` hardcoded in bible/planning save paths | **PARTIALLY FIXED** | bible/planning use `_latest_artifact_version()+1`; five hardcoded sites remain (audit 07:264) | → `L-38` |

**Still open from `documentation/audit-findings.md` (do not read the table above as a
blanket "audit is resolved"):** `:41` rollback restore (`L-42`), `:42` assembly no-op
stubs (`mcp/tools/assembly.py:13-50` still `_stub`, carried under `L-05`/`L-45`),
`:43` bible tools bypassing the graph (`L-03`), `:68` registry coverage and semantic
mismaps (`L-07`), `:71` no `REVIEWER`-role agent (`L-07`), `:72` `_AGENT_PROFILE_MAP`
hardcoded (`L-02`), `:73` `BaseAgent.run` ignores `prepare`'s output (`L-07`),
`:74` `ModelRouter.resolve()` does not exist (`L-03`), `:97` `ValidatorRegistry` unwired
(`L-13`), `:114` `ProjectConfig` schema unused (`L-46`), `:128` `OperatorService` reaches
into runtime internals (`L-45`).

### (d) Withdrawn findings — must not be treated as live concerns (1)

Quarantined per §1.6.6 and the fix-loop record; the audit file preserves the id and
its reasoning under "Withdrawn findings / unverified hypotheses".

| Withdrawn id | Audit | Why it was withdrawn | Ledger treatment |
|---|---|---|---|
| `F-TEST-02` — "Three independent 'mock model response' sources; the shipped one is dead-wired" | `audit/13-test-doubles-and-harness.md` (header + §Withdrawn) | The original drift proof was a false equivalence (`clip-validator` is an agent id, not in `MVP_VALIDATORS`) and the replacement fallback-duplication proof was disproved because both fallbacks are test-pinned (`reviews/verify-13.md` §F-TEST-02) | **Excluded from every entry and from all counts.** The live mock-source concern is carried by `F-TEST-07` inside `L-33`; `L-33`'s severity was reduced to 12 accordingly. |

---

## Appendix — finding-to-entry coverage map (178 live + 1 withdrawn)

Every finding **in the mapped scope** appears exactly once, except the withdrawn
`F-TEST-02`, which appears only in §(d). Counts below are the mapped-scope snapshot at
**2026-09-25T13:57:06Z** (per-file header count, `grep -c '^### F-'` minus the two
`F-TEST-02` stubs in the same file, minus the 11 findings listed under "Deferred to the
second sync" below). The on-disk corpus was already **189 live findings** at that moment;
the difference is exactly the 11 deferred ids.

| Audit | Live findings | Entry assignment |
|---|---|---|
| 01 phase-model | 11 | `01→L-06`, `02→L-15`, `03→L-34`, `04→L-06`, `05→L-15`, `06→L-49`, `07→L-34`, `08→L-15`, `09→L-15`, `10→L-13`, `11→L-15` *(post-verification, unverified)* |
| 02 orchestration-state | 17 | `01→L-50`, `02→L-26`, `03→L-35`, `04→L-34`, `05→L-35`, `06→L-10`, `07→L-17`, `08→L-36`, `09→L-55`, `10→L-34`, `11→L-50`, `12→L-01`, `13→L-09`, `14→L-27`, `15→L-15`, `16→L-55`, `17→L-31` *(post-verification, unverified)* |
| 03 config-profile | 13 | `01→L-24`, `02→L-02`, `03→L-13`, `04→L-14`, `05→L-25`, `06→L-01`, `07→L-46`, `08→L-43`, `09→L-46`, `10→L-46`, `11→L-29`, `12→L-53`, `13→L-53` |
| 04 agent-registry | 12 | `01→L-02`, `02→L-07`, `03→L-07`, `04→L-03`, `05→L-37`, `06→L-51`, `07→L-51`, `08→L-13`, `09→L-30`, `10→L-07`, `11→L-03` *(post-verification, unverified)*, `12→L-02` *(post-verification, unverified)* |
| 05 provider-runtime | 8 | `01→L-09`, `02→L-27`, `03→L-28`, `04→L-29`, `05→L-28`, `06→L-16`, `07→L-41`, `08→L-28` *(post-verification, unverified)* |
| 06 generation | 16 | `01→L-08`, `02→L-08`, `03→L-08`, `04→L-16`, `05→L-16`, `06→L-16`, `07→L-39`, `08→L-39`, `09→L-08`, `10→L-41`, `11→L-40`, `12→L-39`, `13→L-56`, `14→L-16` *(post-verification, unverified)*, `15→L-39` *(post-verification, unverified)*, `16→L-39` *(post-verification, unverified)* |
| 07 artifact-refs | 13 | `01→L-57`, `02→L-18`, `03→L-38`, `04→L-38`, `05→L-38`, `06→L-38`, `07→L-16`, `08→L-18`, `09→L-18`, `10→L-38` *(post-verification, unverified)*, `11→L-18` *(post-verification, unverified)*, `12→L-38` *(post-verification, unverified)*, `13→L-18` *(post-verification, unverified)* |
| 08 validation-review | 15 | `01→L-13`, `02→L-14`, `03→L-17`, `04→L-10`, `05→L-10`, `06→L-31`, `07→L-13`, `08→L-13`, `09→L-31`, `10→L-31`, `11→L-58`, `12→L-18` *(post-verification, unverified)*, `13→L-10` *(post-verification, unverified)*, `14→L-13` *(post-verification, unverified)*, `15→L-13` *(post-verification, unverified)* |
| 09 kb-context | 13 | `01→L-19`, `02→L-20`, `03→L-20`, `04→L-20`, `05→L-20`, `06→L-19`, `07→L-03`, `08→L-19`, `09→L-20`, `10→L-19`, `11→L-18` *(post-verification, unverified)*, `12→L-18` *(post-verification, unverified)*, `13→L-18` *(post-verification, unverified)* |
| 10 checkpoints | 16 | `01→L-11`, `02→L-21`, `03→L-22`, `04→L-21`, `05→L-22`, `06→L-42`, `07→L-42`, `08→L-42`, `09→L-43`, `10→L-40`, `11→L-42` — the original 11, **all VERIFIED by `verify-10`** (11 CONFIRMED, 0 rejected; F-CRP-05 12→9 and F-CRP-10 12→6 downgraded); plus `12→L-11` *(post-verification, unverified — Critical 5×5=25)*, `13→L-43` *(post-verification, unverified)*, `14→L-42` *(post-verification, unverified)*, `15→L-21` *(post-verification, unverified)*, `16→L-22` *(post-verification, unverified)* — the verifier's missed seams M1–M5, promoted to full findings by audit 10's own fix loop. |
| 11 mcp-surface | 15 | `01→L-44`, `02→L-12`, `03→L-23`, `04→L-13`, `05→L-08`, `06→L-45`, `07→L-45`, `08→L-52`, `09→L-43`, `10→L-52`, `11→L-44`, `12→L-03`, `13→L-52` *(post-verification, unverified)*, `14→L-45` *(post-verification, unverified)*, `15→L-52` *(post-verification, unverified)* |
| 12 post-budget | 13 | `01→L-04`, `02→L-07`, `03→L-04`, `04→L-05`, `05→L-04`, `06→L-05`, `07→L-05`, `BUD-01→L-01`, `BUD-02→L-01`, `BUD-03→L-01`, `BUD-04→L-01`, `BUD-05→L-32`, `BUD-06→L-01` *(post-verification, unverified)* |
| 13 test-doubles | **10 live + 1 withdrawn** | `01→L-33`, `03→L-47`, `04→L-47`, `05→L-47`, `06→L-47`, `07→L-33`, `08→L-47`, `09→L-47` *(post-verification, unverified)*, `10→L-09` *(post-verification, unverified)*, `11→L-47` *(post-verification, unverified)*; **`02→§(d) withdrawn** |
| 14 module-boundaries | 6 | `01→L-48`, `02→L-48`, `03→L-12`, `04→L-48`, `05→L-48`, `06→L-54` |
| **Total (mapped scope)** | **178 live + 1 withdrawn** | |

**Verification coverage of the appendix:** **147 of the 178** mapped live findings
carry a verdict from `reviews/verify-NN.md` (the 136 of audits 01–09 and 11–14, plus
audit 10's original 11 now that `verify-10` exists); **31** are post-verification
additions flagged unverified above. That is `147 + 31 = 178`, so every mapped finding
is accounted for exactly once, and no finding is counted twice.

### Deferred to the second sync (11 live findings, not mapped here)

These were already on disk at the measurement moment and belong to the **second sync**;
they are deliberately **not** assigned to concerns in this revision (no placeholder
entries, per the sync brief). They are listed so the count reconciles —
`178 mapped + 11 deferred = 189 on disk`:

| Finding | Audit | Note |
|---|---|---|
| `F-OST-18` | 02 orchestration-state | coverage-closure addition |
| `F-CFG-14`, `F-CFG-15` | 03 config-profile | coverage-closure additions |
| `F-AGENT-13` | 04 agent-registry | coverage-closure addition |
| `F-PROV-09` | 05 provider-runtime | coverage-closure addition |
| `F-GEN-17`, `F-GEN-18`, `F-GEN-19` | 06 generation | coverage-closure additions |
| `F-ARTIFACT-14` | 07 artifact-refs | coverage-closure addition |
| `F-KBCTX-14` | 09 kb-context | coverage-closure addition |
| `F-BOUNDARY-07` | 14 module-boundaries | coverage-closure addition |

**Measured corroboration (enola, `fb85baa`).** `L-48` is corroborated by
`schemas` fan-in 509 and the manual count of 322 (the doc's 323 is a docstring hit,
per `verify-14.md:33-43`); `L-13`/`L-17` by `mcp/tools` fan-out 104 as the widest
consumer; `L-12` by cycle C2 (7 modules); `L-17`/`L-50` by cycle C3; `L-35` by
`graph/orchestrator_state`'s 38/38 exported surface (no encapsulation boundary).
Cycles C1/C4/C5 are cheap façade re-export cycles and are covered by `L-48`'s
façade-completeness guard. Layer enforcement is measurable as **0 violations
because no layers are declared** — the gap `L-48` exists to close.

---

### What this ledger says in one line

178 mapped live findings collapse to **58 ownership concerns**; **47 are already
wrong at HEAD** and must be fixed as defects, **11 are latency** that only a guard
test can retire. Fourteen independent verifications covered 147 findings with
**zero rejections**, downgrading ~20 severities and falsifying several drift
proofs; one hypothesis (`F-TEST-02`) was withdrawn and is quarantined; the 31 live
findings added *after* their audit was verified remain **PENDING VERIFICATION** and
are marked as such rather than taken on their author's word — audit 10's original
11 left that set when `verify-10` landed, but the five seams audit 10's own fix loop
then promoted (`F-CRP-12`…`F-CRP-16`) joined it. A further **11 coverage-closure
findings** were already on disk in other audits and are deferred to the second sync,
named in the appendix and counted in the corpus total rather than silently dropped.
