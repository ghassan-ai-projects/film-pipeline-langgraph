# verify-16 — second-round adversarial verification of five post-verification findings

**Role:** independent adversarial verifier (bar A6), second round. Not an author of any audit,
and not the author of the coverage pass or of the round-1 verification files.
**Scope:** the five findings added to four audit files *after* their first-round verification:

| audit file | finding | claimed class | claimed severity |
|---|---|---|---|
| `docs/modular-architecture/audit/02-orchestration-state-and-routing.md` | `F-OST-18` | O8 + O3 | High (3 × 5 = 15) |
| `docs/modular-architecture/audit/03-config-profile-and-defaults.md` | `F-CFG-14` | O1 | High (3 × 4 = 12) |
| `docs/modular-architecture/audit/03-config-profile-and-defaults.md` | `F-CFG-15` | O5 | High (impact 3 × drift 4 = 12) |
| `docs/modular-architecture/audit/04-agent-registry-and-prompts.md` | `F-AGENT-13` | O4 + O5 | High (2 × 5 = 10) |
| `docs/modular-architecture/audit/05-provider-runtime-and-health.md` | `F-PROV-09` | O5 + O8 | High (3 × 5 = 15) |

**Verdicts:** `CONFIRMED` · `CONFIRMED-WITH-FIX` · `CORRECTED` · `STRENGTHENED` · `DOWNGRADED` ·
`REJECTED`. Exactly one per finding.

**Outcome in one line:** no finding is rejected and none changes band, but **four of the five
carry a printed defect that must be fixed**, and **two of them (`F-CFG-14`, `F-CFG-15`) are
double-counts of findings that already exist in sibling audit files (07 and 09) and are not
cross-referenced**. `F-PROV-09` is substantively confirmed (§1.6.3 clears) with one
unreproducible test count.

No audit file was modified. Every correction below is reported here, not applied.

---

## 0. Method and revision pinning

**Pristine snapshot** (per §1.6.5/§1.6.8 — every `src/` anchor was re-derived here, never from
the live tree, which is byte-identical but also carries `__pycache__`/`tests/logs`):

```bash
mkdir -p /tmp/v16 && git archive fb85baa | tar -x -C /tmp/v16
```

**Revision:**

```bash
$ git rev-parse HEAD
fb85baa0e6b769b709791a96a89980089304bf13
```

`/tmp/v16` contains the tracked tree only (`AGENTS.md documentation film-knowledge-base
langgraph.json LICENSE Makefile mcp-arch.yaml profiles pyproject.toml README.md scripts src tests
uv.lock`) — so `docs/` (gitignored, `.gitignore:2`) exists only in the live workspace. Audit-doc
greps were therefore run in the live workspace; every `src/`/`tests/` claim was re-derived in
`/tmp/v16`.

**Severity rubric applied (§1.5, lines 71–78):** impact 5 = wrong behaviour reaches a human
deliverable/corrupts durable data, 3 = wrong internal behaviour, recoverable, 1 = cosmetic;
drift 5 = no test can fail when one site changes, 1 = a test already pins it;
score = impact × drift; Critical ≥ 16, High 9–15, Medium 4–8, Low 1–3.

**Drift-proof bar (§1.6.3, lines 99–102):** a finding must state either **(a)** an *existing*
divergence between two owners with both sites cited, or **(b)** a mutation scenario — "change X at
`A:l`; `B:l` keeps the old value and no test fails because Z".

**Attacks run per finding:** (1) every anchor re-derived at `fb85baa`; (2) every `Reproduce`
command re-run verbatim (fences de-indented per §1.6.7) with its real output recorded; (3) a
mechanism attack specific to the finding; (4) an impact/drift re-score; (5) a double-count sweep
against every other finding id in the program; (6) a prior-art sweep against
`documentation/audit-findings.md`, `documentation/reviews/*.md`, `docs/clean-code-refactor/*.md`
and the sibling audit files.

**Mutations** were run in throwaway copies (`cp -R /tmp/v16 /tmp/mut13`, `/tmp/mut15`) with
`PYTHONPATH=<copy>/src` (verified to win over the editable install: the imported module file
resolved to the copy). The live repository was never touched.

---

## 1. `F-OST-18` (audit 02) — `CONFIRMED-WITH-FIX`

**Title:** the QC validator→matrix-patch handoff is an undeclared, untyped key on the state dict,
and the app's `run_validation` fills it with no consumer.

### 1.1 Anchors — all resolve at `fb85baa`

| anchor | quote / fact | verdict |
|---|---|---|
| `graph/nodes/qc.py:421` | `pending: list[Any] = state.setdefault("_pending_row_updates", [])` (inside `_track_matrix_row_updates`, def `:417`) | resolves |
| `graph/nodes/qc.py:70` | `pending_updates = state.pop("_pending_row_updates", [])` (inside `_emit_matrix_patch_from_findings`, def `:68`) | resolves |
| `graph/nodes/qc.py:39` | `_emit_matrix_patch_from_findings(new_state)` inside `qc_node` (def `:33`); order `_run_validators(new_state)` `:38` → pop `:39` → `_synthesize_consensus_report` → `_collect_updates` | resolves |
| `app/_graph_exec.py:336-337` | `working.pop("_pending_row_updates", None)` then `_run_validators(working)` | resolves |
| `app/_graph_exec.py:340-344` | writeback only `issues`, `_validation_reports`, `consensus_report_ref`; `qc_patch_ref` never set; `working` discarded | resolves |
| `graph/state_schema.py:102` | `class StudioGraphState(TypedDict, total=False):` (the only `TypedDict` in `graph/`) | resolves |
| `graph/orchestrator_state.py:93-165` | `ORCH_CHANNELS` has no row for the key | resolves |
| `tests/unit/graph/test_channel_registry.py:292-293` | `return frozenset(spec.key for spec in ORCH_CHANNELS) \| _EXTRA_SWEEP_KEYS`; `_EXTRA_SWEEP_KEYS` `:35-37` = `{"artifact_refs","generation_requests","_qc_reports","_qc_raw_reports"}` | resolves |
| `tests/unit/graph/test_channel_registry.py:254-272`, `:273-288` | the sweep inspects only `state.update({...})` and subscript `Assign`/`AnnAssign`/`AugAssign` — **not** `setdefault`/`pop` | resolves |

`_run_validators` (`qc.py:115-137`) → `_append_validator_report` (`:386-403`) → `_track_matrix_row_updates`
(`:417-421`); `_VALIDATOR_RUNNERS` (`:361-368`) includes phase sets `{"script","qc"}`,
`{"visual_dev","qc"}`, `{"gen_planning","qc"}`, `{"shot_bible","qc"}`, `{"post","assembly","qc"}`,
`{"delivery"}`. The dispatch `app/_graph_exec.py:337` and `qc_node` both call the same
`_run_validators`, so the "identical dispatch" claim holds.

### 1.2 `Reproduce` — real output (all three commands)

```
$ grep -rn "_pending_row_updates" src/ tests/ --include=*.py
src/film_pipeline/app/_graph_exec.py:336:    working.pop("_pending_row_updates", None)
src/film_pipeline/graph/nodes/qc.py:70:    pending_updates = state.pop("_pending_row_updates", [])
src/film_pipeline/graph/nodes/qc.py:421:    pending: list[Any] = state.setdefault("_pending_row_updates", [])
exit=0
$ grep -rn "_pending_row_updates\|qc_patch_ref\|_emit_matrix_patch_from_findings" tests/ --include=*.py; echo "tests exit=$?"
tests exit=1
$ # AST probe (verbatim from the finding)
qc_node      : ['_emit_matrix_patch_from_findings', '_run_validators']
run_validation: ['_run_validators']
declared in schema/registry: False False
```

Matches the printed block exactly ("exactly three sites", `tests exit=1`, the asymmetric call sets,
the two `False` declarations). A mechanism probe driving both paths with a real
`MatrixRowUpdate` confirmed the asymmetry end to end: the app path carries `issues` (1) and
`_validation_reports` (1) and `consensus_report_ref` back but leaves
`_pending_row_updates`/`qc_patch_ref` absent, while the sequential path saves a `matrix_patch_qc`
artifact and sets `qc_patch_ref`; the buffer is still gone in both.

### 1.3 Mechanism attack

- **Is the app-path drop reachable?** The drop is real and unconditional on that path
  (`working.pop(...)` at `:336` runs *before* the dispatch at `:337` that fills the buffer — so
  the discard is not the pop but the fact that `working` is never copied back for that key; a
  round-1 note that described the pop as "pops and discards it" mis-describes the order, and the
  finding's own wording, "the buffer dies with the local `working` copy", is the accurate one).
  From **production**, however, the path has no caller: `StudioRuntime.run_validation`
  (`app/runtime.py:234-236`) ← `OperatorService.run_validation` (`app/services/operator.py:310-315`) ←
  **tests only** (`tests/unit/app/services/test_operator_service.py:505,517`); `OperatorService`
  is instantiated in `src/` only at `mcp/tools/generation/planning.py:140` for an unrelated method
  (`preview_generation_prompts`). The MCP `run_validation`
  (`mcp/tools/validation.py:280`) is a third implementation that never calls `_run_validators`.
- **Defect 1 (prior-art count, §1.6.4/§1.6.7).** The finding prints: *"The key is named in **zero**
  audit files (`grep -rn _pending_row_updates docs/modular-architecture/audit/` → 0)."* Re-run, the
  command prints **11 hits**, all in this finding's own file:

  ```
  $ grep -rn _pending_row_updates docs/modular-architecture/audit/ | wc -l
        11
  $ grep -rn _pending_row_updates docs/modular-architecture/audit/ --exclude=02-orchestration-state-and-routing.md; echo "exit=$?"
  exit=1
  ```

  The intended claim is true but the printed evidence is self-refuting. Fix: add
  `--exclude=02-orchestration-state-and-routing.md` (→ 0 hits), or write "zero *other* audit
  files".
- **Defect 2 (blast radius over-reach).** The printed blast radius names *"the operator dashboard
  (`src/film_pipeline/app/services/operator.py:310-315`)"*. There is no dashboard, TUI or
  `InProcessStudioGateway` anywhere in the tracked tree, and `OperatorService.run_validation` has
  zero non-test callers (above). "Reached from `StudioRuntime.run_validation`" is correct;
  "operator dashboard" is unsupported and should be deleted — it also inflates the reachability
  story that the finding is otherwise careful about (it correctly narrows H9's "app/MCP path" to
  the app path).
- **Both round-1 refutations checked.** H9's "app/MCP path" label: the finding's narrowing is
  correct (MCP never fills the key). V15's compression of the app path: looser than the finding's
  own text, as noted above.

### 1.4 Severity

Claimed **High (3 × 5 = 15)**. Drift 5 is exactly §1.5's definition: `tests/` names none of the
three symbols, the writer sweep is structurally blind (both to the `setdefault` form *and* to the
key's absence from `_sweep_scope()`), and the mutation (rename the literal at `:421`, or delete
the `:39` call) is silent. Impact 3 is defensible: the public runtime API returns a state that is
internally wrong but recoverable, and because `issues` are still carried back the blocking gate
still fires — so it is not a 4. **My score: 3 × 5 = 15, High, confirmed.** One inconsistency to
record rather than to punish: `F-AGENT-13` scored an unreachable branch at impact 2 on the
grounds "no caller ⇒ no deliverable impact", and this app path likewise has no non-test caller.
The findings should state the reconciliation explicitly (here the O8 *missing contract* is
present-tense even though the drop is dormant; there the branch is merely dormant). Scored at
impact 2 it would be 10, still High.

### 1.5 Drift proof (§1.6.3)

Clears on **(a)**: two owners of one dispatch — `qc_node` (`qc.py:39`, persists a
`matrix_patch_qc` artifact and `qc_patch_ref`) and `run_validation`
(`app/_graph_exec.py:337`, same dispatch, no consumer, no patch) — both cited with a reproduced
asymmetry, plus **(b)** a silent mutation. This is the strongest drift proof among the five.

### 1.6 Double-count and prior art

- **Not a double-count.** `F-VR-13` (`audit/08-validation-and-review.md:1073-1116`, High 12) owns
  the *declared* `consensus_report_ref`/`qc_patch_ref` fields missing from `ORCH_CHANNELS`;
  `F-OST-18` owns the *undeclared, untyped* `_pending_row_updates`. Different keys, different
  invariant (handoff contract vs entry-path equivalence), and the finding explicitly defers to
  `F-VR-03`. Verified: the two keys are declared in `graph/state_schema.py:157,167` while
  `_pending_row_updates` is in no schema (`AST probe: False False`).
- **Prior art** `documentation/reviews/arch-lens-dataflow.md:202` does name `_pending_row_updates`
  (whole-tree grep: the only hit outside `src/` and this finding), and `docs/.../01-ownership-map.md:106`
  rows it. Novelty of the eight other claims stands.

**Verdict: `CONFIRMED-WITH-FIX`** — substance, mechanism and score stand; two printed claims
(the `grep … → 0` and "operator dashboard") must be corrected.

---

## 2. `F-CFG-14` (audit 03) — `CORRECTED`

**Title:** the pacing vocabulary is re-declared in four places, and the two mapping tables already
disagree.

### 2.1 Anchors — all resolve

`schemas/constraints.py:61` (`Literal[...]`), `graph/scope_contract.py:17-19` (comment + `SLOW_CINEMA`/
`STANDARD`/`DYNAMIC`), `graph/scope_contract.py:33-46` (`_PACING_ALIASES`), `constraints/_keywords.py:46-57`
(`_PACING_KEYWORDS`), `schemas/execution_brief.py:51` (the citation `51-53` overshoots; `:53` is
blank), `agents/impl/structure_extractor_agent.py:59`, `graph/orchestrator_validators/brief.py:113`
plus the tolerance gate at `:120-125`, and the two pinning tests
(`tests/unit/constraints/test_extractor.py:52-54`, `tests/unit/graph/test_scope_contract.py:30`,
`tests/unit/agents/test_impl_agents.py:603` `assert brief.pacing_style == "measured"`). All resolve.

### 2.2 `Reproduce` — real output (exact match)

```
constraints-only: ['moderate', 'slow', 'slow cinema']
scope-only: ['character_driven', 'irregular', 'narrative']
slow cinema -> slow_cinema vs standard | avg_shot 6.5
```

### 2.3 Mechanism attack — the headline premise does **not** survive

The Concern states: *"the two lookup tables that implement it return different canonical values
for the same input."* Probed directly:

```
common keys: ['action', 'contemplative', 'dynamic', 'fast', 'meditative', 'slow_cinema', 'standard']
value conflicts on common keys: {}
```

Seven shared keys, **zero conflicts**. The only asymmetric inputs are keys present in exactly one
table, and for those `normalize_pacing` applies a *documented, test-pinned* unknown-key fallback
(`tests/unit/graph/test_scope_contract.py:30`: `normalize_pacing("nonsense", "also_nonsense") ==
"standard"`). The two tables are not two implementations of one function over one input alphabet;
they are two different vocabularies feeding two different entry points:

- `_PACING_KEYWORDS` → only `constraints/extractor._extract_pacing` (`:236`) — free prose → canonical;
- `_PACING_ALIASES` → only `scope_contract.py:64` (via `derive_scope_contract` `:86`) and `:125`
  (`avg_shot_duration_for`) — profile/film-type vocabulary → canonical.

No production path composes them: `normalize_pacing` has exactly one production caller
(`derive_scope_contract`), fed by `pacing_from_config(state.get("resolved_config"))` =
`profiles/film-type.*.yaml` values (`meditative`, `character_driven`, `irregular`), all of which
are `_PACING_ALIASES` keys. So `avg_shot_duration_for("slow cinema") == 6.5` is real arithmetic
but **not a reachable production harm arising from the table asymmetry**. The reachable harm runs
through the unvalidated `ExecutionBrief.pacing_style: str` bridge (`structure_extractor_agent.py:59`
→ `brief.py:113` → `avg_shot_duration_for`'s silent `STANDARD` default), which is the subject of
another finding (§2.4).

Two further printed defects:

- **Count.** The title/Concern say "four places"; the De-facto owners list prints **five**
  bullets; the Prior-art paragraph counts four only by dropping the `_PACING_ALIASES` row. Either
  way the seam is larger than stated: `schemas/scope_contract.py:23` is a **second** bare-`str`
  `pacing_style` declaration that the finding never cites (already noted by a round-1 adversary).
- The executed divergence is real but is *asymmetric coverage*, not *disagreement*; the sentence
  should say so.

### 2.4 Double-count — this is `F-ARTIFACT-14`'s harm chain

`audit/07-artifact-refs-and-schemas.md:794-846` (`F-ARTIFACT-14`, same class O1, same severity
High 3 × 4 = 12) already owns the identical harm chain with the identical anchors:
`schemas/constraints.py:61`, `schemas/execution_brief.py:51`, **`schemas/scope_contract.py:23`**,
`structure_extractor_agent.py:59`, `brief.py:113`, `scope_contract.py:125-126`, the executed
`avg_shot_duration_for("measured") == 6.5 == avg_shot_duration_for("standard")`, the pinning test
`test_impl_agents.py:603`, and a mutation scenario on the same `Literal`. `F-CFG-14` neither cites
it nor defers to it; its Prior-art block claims "no existing finding or verdict is modified here"
while reproducing that finding's mechanism.

The program's own map treats them as one concern with two ids —
`docs/modular-architecture/01-ownership-map.md:128` lists `F-CFG-14, F-ARTIFACT-14` on the pacing
row, and `:163` lists `F-KBCTX-14, F-CFG-15` on the prompt-budget row — but that co-listing makes
the cross-reference *more* necessary, not less: as written, the same harm is scored at High 12
twice.

### 2.5 Severity

Claimed High (3 × 4 = 12). As co-owner of the shared harm, 12 is arithmetically consistent and I
would not change the band. But the part of the finding that is **unique to audit 03** — duplicated
alias rows in two tables (`action`, `contemplative`, `fast`, `meditative` appear in both with
identical values), asymmetric key coverage, and no test that compares them — is latent
(impact 2: no production composition, no currently wrong value) with drift 4 (no guard: adding a
key to either table alone passes CI). **Unique remainder: 2 × 4 = 8, Medium.** I keep the finding
at High 12 only for the harm it shares with `F-ARTIFACT-14`, counted once.

**Verdict: `CORRECTED`** — the printed mechanism ("different canonical values for the same input")
is refuted; the count contradicts the finding's own anchor list; `schemas/scope_contract.py:23`
is missing; and the harm must be cross-referenced to `F-ARTIFACT-14` (or the two merged).

---

## 3. `F-CFG-15` (audit 03) — `CORRECTED`

**Title:** the model-input size cap is code-only policy and the gate already disagrees with the
truncation site (8000 vs 6000).

### 3.1 Anchors — all resolve

`validation/impl/prompt_readiness.py:15` (`MAX_PROMPT_LENGTH: Final[int] = 8000`), `:83`
(`if len(rendered) <= MAX_PROMPT_LENGTH:`), `:90`; `mcp/tools/bibles/character.py:39`
(`{script_text[:8000]}`); `mcp/tools/bibles/environment.py:40` (same); `mcp/tools/bibles/shot.py:184`
(`script_text[:6000]`); `generation/frame_reviewer.py:68,82,88` (`per_ten=3,3,5`). All resolve.

### 3.2 `Reproduce` — real output

The three commands reproduce as printed — 14 grep lines, `gate limit 8000 | admits a 7000-char
script: True`, and `0` from the tabular `grep -c` (exit 1). One small defect: the printed output
fence stops after the `gate limit …` line and **omits** the `0` that the third command prints
(the third command's own inline comment does say "→ 0").

### 3.3 Mechanism attack — the headline divergence is a category error

**(a) The gate and the slice do not govern one decision.** `_flag_overlong_prompt` measures
`len(entry["rendered_prompt"])` (`:195`) over `prompt_package`/`execution_brief` artifacts; it
never reads `script_text`. Executed:

```
artifact with a 7000-char script_text and no entries -> blocking: []
prompt_package entry with a 7000-char rendered_prompt -> blocking: []
prompt_package entry with an 8001-char rendered_prompt -> blocking: ['prompt_too_long']
```

The MCP bible builders never build a `prompt_package`: `shot.py:182` calls
`runner.model_adapter.chat(...)` directly with `script_text[:6000]`. So a 7,000-character script
is not "admitted by the gate" — the gate never sees it. Worse, `8000` is a *whole-rendered-prompt*
ceiling (template + constitution + constraints + script), while `6000` is *one section's* slice;
they are different dimensions, and "make them agree" is not the fix.

**Double-count — this ground is `F-KBCTX-14`'s.** `audit/09-kb-context-and-provenance.md:716-790`
(`F-KBCTX-14`, High 3 × 4 = 12) already owns: the three slice sites (`character.py:39`,
`environment.py:40`, `shot.py:184`), `MAX_PROMPT_LENGTH` (`:747-749`, and its own reproduce at
`:764`), the `6000 ≠ 8000` divergence (`:780-781`), the same test/absence-of-test argument
(`:742-746`), and — decisively — the correct statement that the gate *"runs only over
`prompt_package`/`execution_brief` artifacts on the graph QC path … never over the inline MCP
bible prompts. A lowered cap can therefore never trip a guard"* (`:749-752`). That sentence is
the opposite of `F-CFG-15`'s framing. `01-ownership-map.md:163` co-lists `F-KBCTX-14, F-CFG-15`.
`F-CFG-15`'s prior-art block greps only `documentation/…` and this audit file and so never sees
its sibling audit; its grep *does* reproduce 0 hits, so the defect is scope, not accuracy — and
unlike `F-PROV-09`, it does not sweep "every other audit file".

**(b) The `per_ten` half survives, and is stronger than printed.** `grep -rn "per_ten\|_spot_check"
tests/` returns 0 hits. Mutating `frame_reviewer.py:68` `per_ten=3` → `4` in a pristine copy
leaves `tests/unit/generation/test_frame_reviewer.py` green (11 passed) **and the whole unit suite
green**:

```
$ sed -i '' '68s/per_ten=3/per_ten=4/' /tmp/mut15/src/film_pipeline/generation/frame_reviewer.py
$ cd /tmp/mut15 && PYTHONPATH=/tmp/mut15/src … -m pytest tests/unit -o addopts="" -q
1866 passed, 3 skipped, 1 warning in 23.42s
```

New evidence (not in any audit): `_spot_check` samples with `hash(frame_role + str(frame_index))`
(`:50`), and CPython salts `str` hashing per process — so the paid-review decision is **not
reproducible across runs**. Three fresh interpreters, same six alt-angle frames:

```
run [False, False, False, True, False, False]
run [False, False, True, False, False, False]
run [False, False, False, False, True, True]
```

That belongs in the surviving finding (or a new one): sampling rate *and* its outcome are
unpinned and nondeterministic, so even the same frame flips between reviewed and not.

### 3.4 Severity

Claimed High (3 × 4 = 12). The claimed score is attached to the prompt-size half, which is
`F-KBCTX-14`'s (12 there, once). The audit-03-specific remainder is the paid-review sampling
policy: **impact 2** (a cost/QC-sampling knob; it does not corrupt a deliverable) × **drift 5**
(verified: no test can fail — the entire unit suite is green under mutation, and no test names
`per_ten`) = **10, High**. Band unchanged; the score and the subject must be rewritten. Note also
that the bolted-on `per_ten` policy is *not* the title's "model-input size cap" — the finding
conflates two unrelated policies to reach its site count.

**Verdict: `CORRECTED`** — the headline divergence is a category error and a duplicate of
`F-KBCTX-14` (delete it and cross-cite); the surviving half must be re-titled, re-scored 10, and
extended with the nondeterminism evidence.

---

## 4. `F-AGENT-13` (audit 04) — `CORRECTED`

**Title:** the router's capability-classification sets share zero tokens with the roster, and the
only argument that reads them is supplied by no caller in `src/` or `tests/`.

### 4.1 Anchors and `Reproduce` — everything reproduced exactly

`graph/_agent_routing.py:31,32,57,59,175,177`; `agents/mvp/__init__.py:15,20`;
`graph/nodes/_agent.py:86,91,193`; `agents/registry.py:43`;
`tests/unit/graph/test_create_path_routing.py:63`; `tests/unit/graph/test_services.py:126` — all
resolve with the quoted text.

```
$ # reproduce 1
roster caps 30 | routing tokens 8 | intersection []
routing tokens in no agent: ['correcting', 'inspecting', 'qc', 'repair', 'replan', 'review', 'revision', 'validation']
$ grep -rn "preferred_capability=" src/ tests/ --include=*.py | grep -v _agent_routing.py || echo "no caller passes preferred_capability"
no caller passes preferred_capability
$ grep -rn "task_type=" src/film_pipeline/graph/nodes/ --include=*.py
src/film_pipeline/graph/nodes/_agent.py:89:        task_type=task_type,
```

Exactly the printed output. Corroborated independently: `preferred_capability` appears on **11
lines, all inside `_agent_routing.py`**; `_run_agent(` has **11** production call sites
(`wrapup.py:24`, `qc.py:97`, `prep.py:58,195,226,275`, `approval.py:34`, `visual.py:39,105,426,600`),
none passing `task_type`; the only `task_type=` in `src/` is the forwarding site `_agent.py:89`.
`tests/integration/test_dynamic_routing.py` exercises `compute_actions`/`after_phase` and never
`route_agent` — so prior-art Finding 8's "execute only from `test_dynamic_routing.py`" is indeed
stale. The mutation was re-run independently in a pristine copy:

```
$ # _REVIEW_CAPABILITIES = {"no_such_capability"}; _REPAIR_CAPABILITIES = {"also_fake"}
$ cd /tmp/mut13 && PYTHONPATH=/tmp/mut13/src … -m pytest tests/unit -o addopts="" -q
1866 passed, 3 skipped, 1 warning in 59.94s
```

— the claimed `1866 passed, 3 skipped` is exact.

### 4.2 Mechanism attack — the blast-radius consequence is refuted

The Blast radius claims: *"A future caller that sets `preferred_capability="review"` … receives the
phase's **creator** agent with `routing_reason="create path for phase '…' — using default agent"` …
because `_capability_route` returns `None` for every routing token and `route_agent` falls through
(`:184-186`)."* This is **false**. Executed against the real `MVP_AGENTS` registry:

```
phase default for script: screenwriter-agent
preferred_capability='review'       -> clip-validator           fallback=False reason="review path for phase 'script'"
preferred_capability='repair'       -> failure-handling-agent   fallback=False reason="repair path for phase 'script' after validation failure"
preferred_capability='qc'           -> clip-validator           fallback=False reason="review path for phase 'script'"
preferred_capability='validation'   -> clip-validator           fallback=False reason="review path for phase 'script'"
preferred_capability='arbitration'  -> orchestrator-agent       fallback=False reason="selected by capability 'arbitration' for phase 'script'"
```

`_normalized_task_type` (`:55-61`) converts every one of the eight routing tokens into
`task_type="review"/"repair"` **before** `:175-177`, so those tokens never reach `_capability_route`;
a genuine roster capability (`arbitration`) does reach it and selects by capability. The eight
tokens are therefore a redundant *synonym* layer, not a broken one, and the
`preferred_capability in …` disjuncts at `:175,:177` are decision-dead (short-circuited by the
rewrite at `:170`). The paragraph also contradicts itself, saying "User-visible: **none today** —
that is the defect" and then asserting a concrete wrong behaviour. (A quirk the finding misses:
`preferred_capability` silently *overrides* an explicit `task_type` — `task_type="repair"` +
`preferred_capability="review"` yields the review path.)

### 4.3 Severity

Claimed High (2 × 5 = 10): *"the branch is unreachable today (no deliverable impact → impact 2)"*.
That reasoning survives — and the corrected mechanism makes it *more* justified, since even a
future caller passing `"review"` gets the reviewer. Drift 5 is confirmed by the silent mutation
and the zero callers. **My score: 2 × 5 = 10, High, confirmed.**

### 4.4 Drift proof, double-count, prior art

- §1.6.3 clears on both limbs: **(a)** an existing, measured divergence (30 declared capabilities
  vs 8 routing tokens, intersection empty — reproduced) with both sides cited, and **(b)** the
  silent mutation.
- **Not a double-count**: `F-AGENT-02` (output artifacts), `F-AGENT-03` (KB domains/output
  artifacts), `F-AGENT-10` (reverse roster guard) do not mention either capability set; the set
  names appear in no other finding.
- Prior art `documentation/reviews/arch-lens-flexibility.md:121` (extension-cost row 4) and
  `:88-97` (Finding 8) verified present and accurately characterised. Minor: Finding 8 says "all
  **12** production `_run_agent` call sites"; the true count is **11** — the finding silently uses
  11 without noting the prior-art correction.

**Verdict: `CORRECTED`** — every count and the mutation reproduce exactly, but the blast-radius
consequence is wrong and must be rewritten (the correct residual harm is the parallel vocabulary,
the decision-dead disjuncts, and the `task_type` override — not a silent creator fallback).

---

## 5. `F-PROV-09` (audit 05) — `CONFIRMED-WITH-FIX`

**Title:** the provider wait budget is declared in four keys, only one is read, and neither poll
path enforces a deadline.

### 5.1 Anchors — all resolve

`providers/adapters/seedance_openrouter.py:28-33` (`POLLING_CONFIG`, keys `:29-32`);
`:122` `time.sleep(self.polling_config["initial_delay_seconds"])` (inside `submit`, under the
comment `# Respect initial delay`); `:128` `job.status = ProviderJobStatus.COMPLETED`;
`generation/executor.py:239` `job = adapter.poll(job)`; `:260` `poll_count=row.poll_count + 1,`;
`mcp/tools/generation/dispatch.py:170` `result = adapter.poll(job)`; `:243` `poll_count=polls,`;
`providers/base.py:71` `def poll(self, job: ProviderJob) -> ProviderJob:`. `ProviderJob`
(`base.py:26-36`) carries no deadline and no `submitted_at`, so "the contract both sites obey"
is accurate; the ledger row *does* have `submitted_at` (`schemas/generation.py:64`, written
`generation/ledger.py:255`), so the extraction sketch is grounded.

### 5.2 `Reproduce` — real output (exact)

```
$ grep -rn "polling_config\|max_wait_seconds\|poll_interval_seconds\|backoff_multiplier\|initial_delay_seconds" src/ tests/ --include=*.py
… seedance_openrouter.py:29, :30, :31, :32, :45, :49, :122   →  7 hits
$ grep -rin "max_wait\|poll_interval\|backoff" profiles/ ; echo "profiles: $?"
profiles: 1
$ # AST probe
declared ['backoff_multiplier', 'initial_delay_seconds', 'max_wait_seconds', 'poll_interval_seconds']
read ['initial_delay_seconds']
dead ['backoff_multiplier', 'max_wait_seconds', 'poll_interval_seconds']
```

The "7 hits" annotation is exact (4 declaration keys + ctor `:45` + copy `:49` + read `:122`),
`profiles: 1`, and the declared/read/dead lists match character for character. The finding's
self-correction of H2 is also exact: H2's own pattern (without `initial_delay_seconds`) returns
**6** hits, none of which is the `initial_delay` read (`:122` matches only via the
`polling_config` substring). H2's two over-claims are correctly narrowed (`resume_generation_polling`,
`dispatch.py:199-251`, contains no loop or sleep; `_poll_row` is likewise single-shot, so the
unboundedness is the absence of budget state across repeated callers).

### 5.3 Mechanism attack

`POLLING_CONFIG` has exactly four keys; the only read anywhere in `src/` or `tests/` is
`initial_delay_seconds`, and it is a sleep inside `submit`, not a poll cadence. Both poll sites
invoke `adapter.poll(job)` with no delay and no cap, each advancing a counter
(`executor.py:260`, `dispatch.py:243`), and all three real adapters complete on the first poll —
which the finding states, and uses to keep the claim latent rather than claiming a live hang.
The declared-vs-enforced divergence is real and well evidenced.

### 5.4 Severity

Claimed High (3 × 5 = 15). Drift 5 is exactly §1.5: `grep` over `tests/` is empty, the three dead
keys have no readers (AST-verified), and the mutation (`max_wait_seconds: 1800` → `60`) is
undetectable. Impact 3 ("wrong internal behaviour, recoverable") is defensible because the O8 half
— a `poll` contract and a `ProviderJob` that cannot express a deadline — is present-tense, even
though the reachable-now consequence is inert configuration. A stricter "reachable today" reading
gives impact 2 → 10, still High. **My score: 3 × 5 = 15, High, confirmed**, with the note that it
sits at the generous end of the band and the finding should say explicitly which half carries the 3.

### 5.5 Drift proof (§1.6.3)

**Clears.** On **(a)**: an existing divergence between the declaration site
(`seedance_openrouter.py:28-33`, promising a 30 s interval, 1.2× backoff and an 1800 s cap) and the
two enforcement sites (`executor.py:239`, `dispatch.py:170`, enforcing none of them) — both sides
cited and reproduced. On **(b)**: the mutation is silent. One honest caveat to record: the (b)
mutation is a *dead-value* mutation (no second site keeps an old value), which is weaker than
§1.6.3(b)'s two-site template — the (a) divergence is what carries the proof, and it is precisely
why drift is 5 rather than `F-PROV-06`'s 4.

### 5.6 Double-count and prior art

- **Not a double-count.** `F-PROV-06` (audit 05, High 12) owns the status→`GenerationStatus`
  mapping and mentions `poll_count` "forever" at `:641` only inside a *status-literal* mutation;
  `F-GEN-04` (audit 06, Critical 16) owns the ledger row transition rules and lists
  `executor.py:260` vs `dispatch.py:243` as two writers. `F-PROV-09` shares those two anchors for a
  different invariant (the wait budget) and explicitly defers ("audit/06's F-GEN-04 owns the
  *meaning* of `poll_count`, not any deadline"). The deferral is correct.
- **Prior art verified as "new":** `grep -rn "POLLING_CONFIG\|max_wait_seconds\|poll_interval_seconds\|backoff_multiplier"`
  over `documentation/`, `docs/clean-code-refactor/` and every other `docs/modular-architecture/audit/*.md`
  returns 0. The characterisations of `documentation/audit-findings.md:101`,
  `arch-lens-flexibility.md:109`, `arch-lens-observability.md:100-105`,
  `arch-lens-boundaries.md:135` and this audit's `§Grep` table at `:96` all check out.
- **Defect (§1.6.4/§1.6.7): the printed count "252 provider/generation/MCP tests pass unchanged"
  is unreproducible and has no command.** Re-run over exactly those three directories:

  ```
  $ pytest tests/unit/providers tests/unit/generation tests/unit/mcp -o addopts="" -q
  501 passed, 1 warning
  ```

  No natural scoping I could construct yields 252: providers 98, generation 113, `providers +
  generation` 211, `+ integration` 523, `-k "provider or generation"` 377, `-k "provider or
  generation or mcp"` 644. Fix: attach the exact command and the real number, or delete the count
  — the conclusion (nothing pins the three keys) is already proven by the empty `tests/` grep and
  the silent mutation.

**Verdict: `CONFIRMED-WITH-FIX`** — substance, anchors, reproduce output, prior-art novelty and the
§1.6.3 drift proof all stand; the unreproducible test count must be corrected.

---

## 6. Summary

| finding | verdict | claimed score | my score | band change | must-fix |
|---|---|---|---|---|---|
| `F-OST-18` (02) | `CONFIRMED-WITH-FIX` | 3 × 5 = 15 High | **15 High** | none | prior-art `grep … → 0` is 11 hits (add `--exclude=02-…`); delete "operator dashboard" |
| `F-CFG-14` (03) | `CORRECTED` | 3 × 4 = 12 High | **12 High** co-owned; **8 Medium** unique | none | delete "different canonical values for the same input"; fix five-vs-four; add `schemas/scope_contract.py:23`; cross-cite `F-ARTIFACT-14` |
| `F-CFG-15` (03) | `CORRECTED` | 3 × 4 = 12 High | **10 High** (surviving half) | none | delete the 8000-vs-6000 gate divergence (it is `F-KBCTX-14`'s and is a category error); re-title/re-score around `per_ten`; add the hash nondeterminism |
| `F-AGENT-13` (04) | `CORRECTED` | 2 × 5 = 10 High | **10 High** | none | rewrite the blast radius — `preferred_capability="review"` routes to a reviewer, not the creator |
| `F-PROV-09` (05) | `CONFIRMED-WITH-FIX` | 3 × 5 = 15 High | **15 High** | none | the "252 tests" count is unreproducible (real: 501) — attach a command or delete it |

**Are any of the five a double-count?** Yes, two:

- `F-CFG-14` restates the harm of **`F-ARTIFACT-14`** (audit 07, High 12) with the same anchors,
  the same pinning test and the same mutation. The unique audit-03 content is the alias-table
  asymmetry (Medium 8).
- `F-CFG-15` restates the ground of **`F-KBCTX-14`** (audit 09, High 12) — same three slice sites,
  same `MAX_PROMPT_LENGTH`, same 6000 ≠ 8000 point — and its headline framing is contradicted by
  `F-KBCTX-14`'s own, correct sentence that the readiness gate never runs over the inline MCP
  bible prompts. The unique audit-03 content is the `per_ten` sampling policy (High 10 on drift 5).

`F-OST-18`, `F-AGENT-13` and `F-PROV-09` are **not** double-counts (`F-VR-13`, `F-AGENT-02/03/10`
and `F-PROV-06`/`F-GEN-04` own adjacent but distinct invariants; each finding defers where it
should, except that `F-CFG-14`/`F-CFG-15` fail to defer at all).

**Did `F-CFG-14`'s framing survive the "two tables should agree" attack?** **No.** The two tables
share seven keys with zero value conflicts; the asymmetric keys are handled by a documented,
test-pinned fallback; and no production path composes the tables. The real reachable harm is the
unvalidated `ExecutionBrief.pacing_style` bridge, which audit 07 already owns.

**Does `F-PROV-09`'s drift proof clear §1.6.3?** **Yes** — on limb (a), the declaration
(`seedance_openrouter.py:28-33`) versus the two enforcement sites (`executor.py:239`,
`dispatch.py:170`) that enforce nothing, both cited; the (b) mutation is silent but is a
dead-value mutation rather than the two-site template, and the finding says as much by scoring
drift 5. The only defect is the unreproducible test count.

**At least one correction per audit file:** audit 02 ✔ (`F-OST-18`, two printed defects), audit 03
✔ (`F-CFG-14`, `F-CFG-15`), audit 04 ✔ (`F-AGENT-13`), audit 05 ✔ (`F-PROV-09`).

---

## 7. What the authors should fix

1. **`F-OST-18` (02).** Replace `grep -rn _pending_row_updates docs/modular-architecture/audit/`
   with a command that excludes the finding's own file (`--exclude=02-orchestration-state-and-routing.md`,
   real output exit 1), or rewrite the claim as "zero *other* audit files". Delete "the operator
   dashboard" from the blast radius: no such surface exists in the tree and
   `OperatorService.run_validation` (`app/services/operator.py:310-315`) has only test callers —
   say instead that the app path is reachable from `StudioRuntime.run_validation` and currently
   only exercised by `tests/unit/app/services/test_operator_service.py:505,517`. Add one sentence
   reconciling impact 3 here with `F-AGENT-13`'s "unreachable ⇒ impact 2" ruling.
2. **`F-CFG-14` (03).** Delete "the two lookup tables … return different canonical values for the
   same input"; replace with "the two tables have different, partly disjoint key alphabets and
   four rows are duplicated verbatim (`action`, `contemplative`, `fast`, `meditative`), with no
   test that compares them". Make the count consistent (the owner list has five entries) and add
   `schemas/scope_contract.py:23`. Cross-cite `F-ARTIFACT-14` for the `ExecutionBrief`→`brief.py:113`
   harm, or merge the two findings and score the shared harm once at 12 (the unique audit-03 half
   is Medium 8).
3. **`F-CFG-15` (03).** Delete the (a) divergence paragraph and the "8000 vs 6000" title claim:
   the readiness gate reads `rendered_prompt` on `prompt_package`/`execution_brief` artifacts and
   never sees `script_text`, and `F-KBCTX-14` (audit 09) already owns the slice sites, the limit
   and the tests. Re-title around the surviving, reproduced half — the `per_ten` sampling policy
   in `generation/frame_reviewer.py:68,82,88` — re-score it 2 × 5 = 10, and add the new evidence
   that `_spot_check`'s use of the salted built-in `hash` makes the review decision differ between
   processes for the same frame and index. Also print the third command's `0` in the output fence.
4. **`F-AGENT-13` (04).** Rewrite the blast radius. `preferred_capability="review"`/`"qc"`/
   `"validation"` reaches the review path (`clip-validator`) and `"repair"` the operator path
   (`failure-handling-agent`) because `_normalized_task_type` (`:55-61`) rewrites `task_type`
   before `:175-177`; only non-routing (roster) capabilities reach `_capability_route`, and they
   resolve. The real residual harms are: the 8-token synonym vocabulary parallel to the 30
   registry capabilities with no register-time check; the decision-dead `preferred_capability in …`
   disjuncts at `:175,:177`; and `preferred_capability` silently overriding an explicit
   `task_type`. Also note that prior-art Finding 8's "12 production `_run_agent` call sites" is
   actually 11.
5. **`F-PROV-09` (05).** Delete or substantiate "the 252 provider/generation/MCP tests pass
   unchanged": `pytest tests/unit/providers tests/unit/generation tests/unit/mcp` gives
   **501 passed** at `fb85baa`, and no other scoping I tried gives 252. The point it supports is
   already carried by the empty `tests/` grep and the silent mutation. Everything else in the
   finding reproduces exactly — keep it.
6. **Process.** The register should forbid a post-verification addition whose prior-art block does
   not sweep the sibling audit files (`F-CFG-14`/`F-CFG-15` both fail this while `F-PROV-09`
   passes it), and `01-ownership-map.md` rows that carry two ids for one concern should require a
   reciprocal cross-reference in both findings.

---

## Appendix A — raw evidence log

All commands run from `${REPO_ROOT}` unless noted;
`src/`-anchored checks were re-derived against `/tmp/v16` (identical content). Raw output:

```
########## F-OST-18 ##########
--- CMD1 grep src/tests ---
src/film_pipeline/app/_graph_exec.py:336:    working.pop("_pending_row_updates", None)
src/film_pipeline/graph/nodes/qc.py:70:    pending_updates = state.pop("_pending_row_updates", [])
src/film_pipeline/graph/nodes/qc.py:421:    pending: list[Any] = state.setdefault("_pending_row_updates", [])
exit=0
--- CMD2 grep tests ---
tests exit=1
--- CMD3 AST probe ---
qc_node      : ['_emit_matrix_patch_from_findings', '_run_validators']
run_validation: ['_run_validators']
declared in schema/registry: False False
--- V: prior-art grep as printed in F-OST-18 ---
docs/modular-architecture/audit/02-orchestration-state-and-routing.md:42:  undeclared, untyped key on the state dict (`_pending_row_updates`), and the app's on-demand `run_validation` fills
… (11 lines, all in the finding's own file) …
printed-claim exit should be 0 and print 0 hits:
      11
--- V: excluding the finding's own file ---
exit=1

########## F-CFG-14 ##########
constraints-only: ['moderate', 'slow', 'slow cinema']
scope-only: ['character_driven', 'irregular', 'narrative']
slow cinema -> slow_cinema vs standard | avg_shot 6.5
--- V: shared-key conflict probe ---
common keys: ['action', 'contemplative', 'dynamic', 'fast', 'meditative', 'slow_cinema', 'standard']
value conflicts on common keys: {}
  raw='character_driven' K=None            normalize='standard'
  raw='irregular'        K=None            normalize='standard'
  raw='narrative'        K=None            normalize='standard'
  raw='moderate'         K='standard'      normalize='standard'
  raw='slow'             K='slow_cinema'   normalize='standard'
  raw='slow cinema'      K='slow_cinema'   normalize='standard'
  raw='meditative'       K='slow_cinema'   normalize='slow_cinema'
  raw='measured'         K=None            normalize='standard'
  raw=''                 K=None            normalize='standard'

########## F-CFG-15 ##########
src/film_pipeline/post/audio_design_agent.py:10:_SCENE_SPACING_SECONDS = 30.0
src/film_pipeline/post/audio_design_agent.py:46:                    start_seconds=i * _SCENE_SPACING_SECONDS,
src/film_pipeline/post/audio_design_agent.py:71:                start_seconds=i * _SCENE_SPACING_SECONDS,
src/film_pipeline/mcp/tools/bibles/character.py:39:{script_text[:8000]}
src/film_pipeline/mcp/tools/bibles/environment.py:40:{script_text[:8000]}
src/film_pipeline/mcp/tools/bibles/shot.py:184:        f"Script:\n{script_text[:6000]}\n\n"
src/film_pipeline/mcp/tools/checkpoints.py:21:_RECENT_CHECKPOINT_LIMIT = 20
src/film_pipeline/mcp/tools/checkpoints.py:82:    return cps[-_RECENT_CHECKPOINT_LIMIT:]
src/film_pipeline/validation/impl/prompt_readiness.py:15:MAX_PROMPT_LENGTH: Final[int] = 8000  # characters
src/film_pipeline/validation/impl/prompt_readiness.py:83:    if len(rendered) <= MAX_PROMPT_LENGTH:
src/film_pipeline/validation/impl/prompt_readiness.py:90:                f"Prompt '{prompt_id}' is {len(rendered)} chars (> {MAX_PROMPT_LENGTH} limit)."
src/film_pipeline/generation/frame_reviewer.py:68:            return _spot_check(frame_role, frame_index, per_ten=3)
src/film_pipeline/generation/frame_reviewer.py:82:        return _spot_check(frame_role, frame_index, per_ten=3)
src/film_pipeline/generation/frame_reviewer.py:88:        return _spot_check(frame_role, frame_index, per_ten=5)
grep exit=0
gate limit 8000 | admits a 7000-char script: True
0
grep -c exit=1
--- V: gate input is rendered_prompt, not script_text ---
artifact with a 7000-char script_text and no entries -> blocking: []
prompt_package entry with a 7000-char rendered_prompt -> blocking: []
prompt_package entry with an 8001-char rendered_prompt -> blocking: ['prompt_too_long']
--- V: bibles never build a prompt_package ---
src/film_pipeline/mcp/tools/bibles/shot.py:182:    raw = runner.model_adapter.chat(
--- V: nondeterministic spot-check across processes ---
run [False, False, False, True, False, False]
run [False, False, True, False, False, False]
run [False, False, False, False, True, True]

########## F-AGENT-13 ##########
roster caps 30 | routing tokens 8 | intersection []
routing tokens in no agent: ['correcting', 'inspecting', 'qc', 'repair', 'replan', 'review', 'revision', 'validation']
no caller passes preferred_capability
src/film_pipeline/graph/nodes/_agent.py:89:        task_type=task_type,
--- V: preferred_capability routing outcome (refutes Blast radius) ---
phase default for script: screenwriter-agent
preferred_capability='review'       -> clip-validator           fallback=False reason="review path for phase 'script'"
preferred_capability='repair'       -> failure-handling-agent   fallback=False reason="repair path for phase 'script' after validation failure"
preferred_capability='qc'           -> clip-validator           fallback=False reason="review path for phase 'script'"
preferred_capability='validation'   -> clip-validator           fallback=False reason="review path for phase 'script'"
preferred_capability='arbitration'  -> orchestrator-agent       fallback=False reason="selected by capability 'arbitration' for phase 'script'"

########## F-PROV-09 ##########
src/film_pipeline/providers/adapters/seedance_openrouter.py:29:    "initial_delay_seconds": 20,
src/film_pipeline/providers/adapters/seedance_openrouter.py:30:    "poll_interval_seconds": 30,
src/film_pipeline/providers/adapters/seedance_openrouter.py:31:    "max_wait_seconds": 1800,
src/film_pipeline/providers/adapters/seedance_openrouter.py:32:    "backoff_multiplier": 1.2,
src/film_pipeline/providers/adapters/seedance_openrouter.py:45:        polling_config: dict[str, float] | None = None,
src/film_pipeline/providers/adapters/seedance_openrouter.py:49:        self.polling_config = polling_config or dict(POLLING_CONFIG)
src/film_pipeline/providers/adapters/seedance_openrouter.py:122:        time.sleep(self.polling_config["initial_delay_seconds"])
hits=7
profiles: 1
declared ['backoff_multiplier', 'initial_delay_seconds', 'max_wait_seconds', 'poll_interval_seconds']
read ['initial_delay_seconds']
dead ['backoff_multiplier', 'max_wait_seconds', 'poll_interval_seconds']
--- V: H2's own pattern (no initial_delay) ---
       6
--- V: the printed 252 count ---
501 passed, 1 warning in 8.77s
```

## Appendix B — mutation runs

```bash
# F-AGENT-13: replace both routing sets with fake tokens in a pristine copy
cp -R /tmp/v16 /tmp/mut13
sed -i '' 's/_REVIEW_CAPABILITIES = {"review", "validation", "qc", "inspecting"}/_REVIEW_CAPABILITIES = {"no_such_capability"}/; \
           s/_REPAIR_CAPABILITIES = {"repair", "revision", "replan", "correcting"}/_REPAIR_CAPABILITIES = {"also_fake"}/' \
    /tmp/mut13/src/film_pipeline/graph/_agent_routing.py
cd /tmp/mut13 && PYTHONPATH=/tmp/mut13/src <venv>/bin/python -m pytest tests/unit -o addopts="" -q
# → 1866 passed, 3 skipped, 1 warning in 59.94s   (exit 0)

# F-CFG-15: change the alt-angle sampling rate only
cp -R /tmp/v16 /tmp/mut15
sed -i '' '68s/per_ten=3/per_ten=4/' /tmp/mut15/src/film_pipeline/generation/frame_reviewer.py
cd /tmp/mut15 && PYTHONPATH=/tmp/mut15/src <venv>/bin/python -m pytest tests/unit/generation/test_frame_reviewer.py -o addopts="" -q
# → 11 passed in 1.86s                             (exit 0)
cd /tmp/mut15 && PYTHONPATH=/tmp/mut15/src <venv>/bin/python -m pytest tests/unit -o addopts="" -q
# → 1866 passed, 3 skipped, 1 warning in 23.42s    (exit 0)

# Import resolution check (PYTHONPATH wins over the editable install)
cd /tmp/mut13 && PYTHONPATH=/tmp/mut13/src <venv>/bin/python -c "import film_pipeline.graph._agent_routing as m; print(m.__file__)"
# → /tmp/mut13/src/film_pipeline/graph/_agent_routing.py
```

## Appendix C — hygiene

- Only `docs/modular-architecture/reviews/verify-16.md` was written; `docs/` is gitignored
  (`.gitignore:2`), and `git status --porcelain` was empty before and after.
- No `git checkout`/`clean`/`stash`/`commit`/`push` was run. No `make ci-check` was run.
  Scratch lived in `/tmp` only.
- Pinned revision verified at the start: `git rev-parse HEAD` =
  `fb85baa0e6b769b709791a96a89980089304bf13`.
