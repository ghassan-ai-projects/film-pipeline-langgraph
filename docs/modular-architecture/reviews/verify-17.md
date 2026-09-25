# verify-17 — second-round verification of five post-verification findings (audits 06, 07, 09)

Scope: the five findings added to the audit corpus *after* the first verification round and not
seen by any prior verifier (bar A6):

| audit file | new id | claimed class | claimed severity |
|---|---|---|---|
| `audit/06-generation-runtime-and-ledger.md` | `F-GEN-17` | O1+O4+O5 | Critical (20) |
| `audit/06-generation-runtime-and-ledger.md` | `F-GEN-18` | O1+O4+O5 | High (12) |
| `audit/06-generation-runtime-and-ledger.md` | `F-GEN-19` | O1 | High (12) |
| `audit/07-artifact-refs-and-schemas.md` | `F-ARTIFACT-14` | O1 | High (12) |
| `audit/09-kb-context-and-provenance.md` | `F-KBCTX-14` | O5+O1 | High (12) |

## Method

For every finding I (1) re-derived each `path:line` anchor against the pinned snapshot and
classified it as *defining/enforcing* (rule §1.6.1 compliant) or non-resolving; (2) ran every
`Reproduce` command verbatim and recorded the real output (rule §1.6.7); (3) attacked the stated
*mechanism* with an independent probe, not a re-run of the finding's own command; (4) attacked
severity by re-deriving impact × drift against §1.5, treating "arithmetic wins over a band word"
as binding; (5) checked double-counting against the sibling findings named in the brief
(`F-GEN-03`, `F-GEN-06`, `F-GEN-12`, `F-CFG-13/14/15`, `F-ARTIFACT-01/02/08`, `F-KBCTX-06`) and
against every other audit file by grep. Nothing was written outside this file; `src/` was read
only. Bar A6 asks for adversarial verification, so where a finding survived I record what I
attacked and why it survived rather than restating it.

Revision and snapshot (rule §1.6.8):

```bash
cd ${REPO_ROOT}
git rev-parse HEAD
# -> fb85baa0e6b769b709791a96a89980089304bf13
mkdir -p /tmp/v17 && git archive fb85baa | tar -x -C /tmp/v17
diff -rq src /tmp/v17/src
# -> only "Only in src/film_pipeline/...: __pycache__" lines; every .py file identical
git status --porcelain
# -> (empty) at the start and at the end of this review
```

The snapshot and the working tree are byte-identical for every source file (only build
`__pycache__` directories differ), so the `src/` line numbers below are valid for both.

## Verdict summary

| finding | verdict | one-line basis |
|---|---|---|
| F-GEN-17 | **CONFIRMED** | Every anchor resolves; both Reproduce commands print the stated output; the executed board-build divergence (prompt-mapped roles vanish from the sheet and its manifest) reproduces exactly. 4×5=20 Critical holds. |
| F-GEN-18 | **CORRECTED** | All executed facts, the self-refutation and the dead-consumer proof hold, but the mutation's parenthetical "(the paid Gemini call is still made)" is backwards for a mistyped type, the first `Reproduce` output is pyc-polluted, and the impact-3 justification never cites the live `asset_type` consumers. Severity unchanged (3×4=12). |
| F-GEN-19 | **CORRECTED** | The duplication, the executed identity differential and the silent mutation all reproduce, but two cited test anchors are misattributed, "the only behavioural consumer" is understated, and the TEST-default policy has a third declaration the owner list omits. Drift is **5, not 4**, so the score is **15 not 12** (band High unchanged). Not a hypothesis: §1.6.3(b) admits a mutation scenario as a drift proof. |
| F-ARTIFACT-14 | **CORRECTED** | The 24/13 counts and all five executed asymmetries reproduce, but the pacing half is substantially audit 03 **F-CFG-14**'s (two of the three declaration sites + the `"measured"` divergence + the same pinning test), the phase half is an uncited extension of audit 01 **F-PHASE-02**, and the `Reproduce` block commands only one of the five asymmetries it asserts. Severity defensible (3×4=12) but the "schema half is new" claim is not. |
| F-KBCTX-14 | **CORRECTED** | Seam real and every command/output reproduces, but it is a partial double-count of audit 03 **F-CFG-15**: the same three MCP bible sites, the same 8000-vs-6000 disagreement and the same "each builder its own authority / nothing compares them" framing. Its "no finding id existed" is false. Must cite F-CFG-15 and reduce its novelty to the `kb` budget, the six `_context.py` slices and the retry factors. |

No finding was REJECTED. None failed its reproducibility bar outright. Two printed claims are
outright false (`F-GEN-19`'s two test attributions; `F-KBCTX-14`'s "no finding id existed") and
`F-GEN-18`'s mechanism parenthetical is backwards for the scenario it is attached to.

---

## 1. F-GEN-17 — CONFIRMED (Critical 20)

`audit/06-generation-runtime-and-ledger.md:958`.

### Anchors

Every anchor resolves. Verified line by line (working tree = snapshot):

```
generation/compositor/_layout.py:24   _CHAR_TILES: dict[str, tuple[int, int, int, int]] = {
generation/compositor/_layout.py:42   _CHAR_LABELS: dict[str, str] = {
generation/compositor/environment.py:27   _ENV_TILES: dict[str, tuple[int, int, int, int]] = {
generation/compositor/environment.py:116  for role, rect in _ENV_TILES.items():
generation/compositor/environment.py:128  _paste_environment_frame(canvas, frames.get(role), role, rect)
generation/compositor/extras.py:23    _EXPRESSION_TILES: dict[str, tuple[int, int, int, int]] = {
generation/prompt_builder.py:24       _CHARACTER_FRAME_ROLE_TEXT: dict[str, str] = {
generation/prompt_builder.py:40       _ENVIRONMENT_FRAME_ROLE_TEXT: dict[str, str] = {
generation/prompt_builder.py:157      def _build_environment_prompt(
generation/prompt_builder.py:169          angle_text = _frame_role_text(entry, _ENVIRONMENT_FRAME_ROLE_TEXT)
mcp/tools/reference_generation/entries.py:29  ANCHOR_PRIORITY = {"front-face": 0, "wide-establishing": 0}
mcp/tools/reference_generation/outcomes.py:55 is_anchor = str(raw.get("frame_role", "")).strip().lower() in (
mcp/tools/reference_generation/composites.py:76  role = str(entry.get("frame_role", "")).strip()
mcp/tools/reference_generation/composites.py:82  frames_by_subject.setdefault(subject_id, {})[role] = frame_path
agents/prompt_templates/defaults/production.py:63 '        "frame_role": "front-face",\n'
schemas/reference.py:53               frame_role: str = Field(
```

Two anchors attach a *function name* to what is the function's delegation line rather than its
`def` (`_reference_prompt` is defined at `entries.py:77`, cited as `:92` = `return
build_structured_prompt(`; `_build_environment_prompt` is defined at `prompt_builder.py:157`,
cited as `:169` = the `_frame_role_text(...)` call). Both cited lines are the *enforcing* lines of
the claim being made (the chain of delegation), which §1.6.1 explicitly permits, and both resolve
to the intended behaviour. I record it as a presentation nit, not a defect.

### Reproduce — output matches exactly

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
from film_pipeline.generation.compositor._layout import _CHAR_TILES
from film_pipeline.generation.compositor.environment import _ENV_TILES
from film_pipeline.generation.prompt_builder import _CHARACTER_FRAME_ROLE_TEXT, _ENVIRONMENT_FRAME_ROLE_TEXT
print('char', len(_CHAR_TILES), len(_CHARACTER_FRAME_ROLE_TEXT), set(_CHARACTER_FRAME_ROLE_TEXT)^set(_CHAR_TILES))
print('env ', len(_ENV_TILES), len(_ENVIRONMENT_FRAME_ROLE_TEXT), 'prompt-only', sorted(set(_ENVIRONMENT_FRAME_ROLE_TEXT)-set(_ENV_TILES)))
"
# real output:
# char 13 13 set()
# env  8 10 prompt-only ['alt-angle-entrance', 'lighting-overcast-morning']
```

The board-build probe (independent execution, `/tmp/h1probe`):

```bash
UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
import json; from pathlib import Path; from PIL import Image
from film_pipeline.generation.compositor import build_environment_board
r=Path('/tmp/h1probe'); r.mkdir(exist_ok=True)
for n,c in (('w',(200,30,30)),('e',(30,200,30)),('o',(30,30,200))): Image.new('RGB',(64,64),c).save(r/f'{n}.png')
build_environment_board('studio','Studio',{'wide-establishing':r/'w.png','alt-angle-entrance':r/'e.png','lighting-overcast-morning':r/'o.png'}, r/'b.png')
m=json.loads((r/'b.png.sheet.json').read_text())
print('tiles',[t['tile_name'] for t in m['tiles']],'placeholders',m['placeholder_tiles'])
"
# real output:
# tiles ['wide-establishing'] placeholders ['alt-angle-desk', 'alt-angle-corner', 'lighting-cool-night', 'lighting-golden-afternoon', 'detail-texture', 'detail-prop', 'color-palette']
```

Counts and the novelty greps:

```bash
grep -rln "_CHAR_TILES\|_ENV_TILES\|_EXPRESSION_TILES\|_CHARACTER_FRAME_ROLE_TEXT\|_ENVIRONMENT_FRAME_ROLE_TEXT\|ANCHOR_PRIORITY" src/film_pipeline --include=*.py | wc -l
# -> 6
grep -rn "_ENV_TILES\|_ENVIRONMENT_FRAME_ROLE_TEXT\|FRAME_ROLE" docs/modular-architecture/audit/ \
  --exclude=06-generation-runtime-and-ledger.md | wc -l
# -> 0
grep -rn "_ENV_TILES\|_CHAR_TILES\|_ENVIRONMENT_FRAME_ROLE_TEXT\|ANCHOR_PRIORITY" tests/ --include=*.py
# -> no matches (grep exit 1)
```

### Mechanism attack — the executed divergence survives

I tried five ways to break the claim and all failed:

1. **"Maybe something re-maps the unknown roles before the board build."** No. The live path is
   MCP `generate_reference_images` (`mcp/tools/reference_generation/tool.py:202`) →
   `_build_composites` → `_build_environment_boards` → `build_environment_board`.
   `_collect_subject_frames` keys frames by the raw `frame_role` string with no allow-list
   (`composites.py:76,82`), and `_build_environment_boards` passes that dict straight through.
2. **"Maybe the reviewer rejects the two prompt-mapped frames so they never reach the board."**
   No. `frame_reviewer.should_review_frame` sends `alt-angle-*` to a 3/10 spot check (`:66`) and
   returns `False` (skip) for every `lighting-*` role (`:64`), so those frames are stamped
   `generated`/`validated` and collected like any other.
3. **"Maybe the board build places them somewhere."** No — verified by execution above. The paste
   loop is `for role, rect in _ENV_TILES.items()` (`environment.py:116`) and `:128` is inside it.
4. **"Maybe the manifest at least records them."** No. `_write_sheet_manifest` builds both the
   tile list and the placeholder list from its `tiles` argument (`_layout.py:212`), and
   `build_environment_board` passes `_ENV_TILES` (`environment.py:134-141`). A role absent from
   `_ENV_TILES` is in neither list — confirmed by the probe's `['wide-establishing']` tiles and
   seven known-missing placeholders.
5. **"Maybe the vocabulary is owned by another finding."** No — the other-audit grep returns 0.
   The cited overlap with F-GEN-03 (`_generation_prompts.py:73` / `executor_prompts.py:99`,
   the `camera_profile → frame_role` conflation) is a *different* concern (prompt assembly) and is
   named in the finding's own prior art, so it is a cited overlap, not a hidden double-count.

### Severity

Impact 4: a paid frame with prompt prose (or any LLM-minted role) is silently absent from the
reference sheet a human approves, and is not even counted as a missing tile. Drift 5: no test
references any of the role registries (`tests/` grep above → no matches), so changing one table
alone cannot fail any test. 4×5 = 20, Critical. Arithmetic and band agree. **CONFIRMED.**

---

## 2. F-GEN-18 — CORRECTED (High 12)

`audit/06-generation-runtime-and-ledger.md:1008`.

### Reproduce — output matches (with one environmental caveat)

```bash
grep -rn '_PASS_THRESHOLD' src/film_pipeline/generation/
# real output (after any uv run has created __pycache__):
# src/film_pipeline/generation/frame_reviewer.py:43:_PASS_THRESHOLD = 28.0
# src/film_pipeline/generation/frame_reviewer.py:222:        passed=total >= _PASS_THRESHOLD,
# Binary file src/film_pipeline/generation/__pycache__/frame_reviewer.cpython-312.pyc matches
grep -rni '_pass_threshold' src/film_pipeline/generation/
# real output adds:
# src/film_pipeline/generation/sheet_reviewer.py:72:def _pass_threshold(max_score: int) -> float:
# src/film_pipeline/generation/sheet_reviewer.py:154:    threshold = _pass_threshold(max_score)
# src/film_pipeline/generation/sheet_reviewer.py:227:    threshold = _pass_threshold(max_score)
grep -rn "review_composite_sheet\|_validate_composite" src/film_pipeline
# real output (non-pyc): composites.py:105, :131, :225, :229, :232; delta_regenerator.py:14, :95;
# generation/__init__.py:26, :43; sheet_reviewer.py:79
grep -rn "regenerate_failing_tiles" src/
# -> delta_regenerator.py:59 (def) + generation/__init__.py:11 (import) + :41 (__all__) only
grep -rn "_RUBRICS\|character_identity_sheet\|environment_board" docs/modular-architecture/audit/ \
  --exclude=06-generation-runtime-and-ledger.md | wc -l
# -> 0
```

**Defect (minor, environmental):** the finding records the first command's output as
"`frame_reviewer.py:43,222` only". That is true at a pristine checkout, but once any test/`uv run`
has created `__pycache__`, `grep -rn` also prints a `Binary file ... matches` line. Audit 03's own
other contains use `--include=*.py`; the finding should too, so the printed output is
revision-independent (§1.6.7).

### Mechanism attack — what holds and what is wrong

Confirmed by reading and execution:

* `sheet_reviewer.py:101-103` really does return `_failed_result(..., "Unknown sheet type: …")`
  for an unknown key instead of raising.
* `_validate_composite` (`composites.py:225-237`) calls `review_composite_sheet(...)` and **drops
  the return value**, inside `except Exception: pass`. So a completed review's pass/fail never
  reaches anything: the manifest's own `validation_status`/`validation_score` fields
  (`schemas/reference.py:152-154`) stay at their defaults (`"pending"` / `0.0`).
* `regenerate_failing_tiles` (`delta_regenerator.py:59`) is the only consumer that reads a
  `SheetReviewResult`, and it has no production caller (grep above).
* `_build_scale_sheet` (`composites.py:180-195`) builds the scale sheet and never calls
  `_validate_composite`, so `_RUBRICS["scale_sheet"]` is unreachable from the pipeline.
* Threshold bands: the sheet reviewer's two scored fixtures are totals 41 (assert pass) and 23
  (assert fail), so any threshold in `(23, 41]` passes; `0.8*40=32` and `0.7*40=28` both qualify.
  The frame reviewer's fixtures are 34, 17 and 30, so its band is `(17, 30]`. Both as claimed.

**Defect (substantive):** the mutation's parenthetical is backwards. The finding says a mistyped
literal at `composites.py:105` means "composite validation silently stops **(the paid Gemini call
is still made)**", and the blast radius repeats "silently disables composite validation while
still paying for the review call". With an unknown `sheet_type`, `review_composite_sheet` returns
at `:101-103` *before* any API call, so the paid review is **skipped**, not paid for. The
"still paying" fact belongs to the *correctly-typed* path: there the review is bought and its
result is then thrown away. The two consequences are real but they are different, and as written
the sentence asserts the opposite of what the code does.

### Severity and self-refutation

The finding's internal H5 refutation is **correct**: the two bars grade different units (one frame
vs an assembled sheet), so they are not an executed divergence; and at HEAD the sheet bar gates
nothing because its only consumer is dead. That reasoning justifies 3, not 4, on impact, and I
could not raise it back to 4. Drift 4 is right: a moved `0.8` (or a renamed sheet type at
`composites.py:105`) fails no test — `tests/unit/mcp/tools/test_reference_generation.py:135` only
patches `review_composite_sheet` and never asserts its arguments or result. 3×4 = 12, High.

**Correction the authors should make:** the impact-3 case should name the *live* consumers of the
sibling `asset_type` vocabulary rather than resting on bareness: `entries.py:101-105` selects the
aspect ratio by substring (`"environment"` / `"style"` / `"camera"` / `"scale"` → 16:9 else 3:4)
and `frame_reviewer.py:91` keys the review policy on `asset_type in ("scale_sheet", "prop_sheet")`.
A mis-minted `asset_type` therefore silently changes the rendered aspect ratio and the paid-review
policy — that is the executed impact 3. Verdict **CORRECTED**; band High 12 unchanged.

---

## 3. F-GEN-19 — CORRECTED (drift 4→5, score 12→15, band High unchanged)

`audit/06-generation-runtime-and-ledger.md:1038`.

### Anchors and Reproduce — output matches exactly

```
graph/nodes/_generation_batch_planning.py:20  def _parse_generation_mode(mode_str: str) -> GenerationMode:
graph/nodes/_generation_batch_planning.py:24      mode = GenerationMode.TEST
graph/nodes/_generation_batch_planning.py:25      with contextlib.suppress(ValueError):
graph/nodes/_generation_batch_planning.py:26          mode = GenerationMode(mode_str)
graph/nodes/_generation_batch_planning.py:93      mode = _parse_generation_mode(str(req.get("mode", "test") or "test"))
graph/nodes/_generation_batch_planning.py:160             mode=_parse_generation_mode(mode_str),
mcp/tools/generation/planning.py:21           def _resolve_generation_mode(args: dict[str, object]) -> GenerationMode:
mcp/tools/generation/planning.py:25               mode_str = str(args.get("mode", "test"))
mcp/tools/generation/planning.py:26               mode = GenerationMode.TEST
mcp/tools/generation/planning.py:27-28            with contextlib.suppress(ValueError): mode = GenerationMode(mode_str)
mcp/tools/generation/planning.py:78               mode = _resolve_generation_mode(args)
mcp/tools/generation/planning.py:191                  "mode": row.mode.value,
schemas/_base.py:183                          class GenerationMode(StrEnum):
```

```bash
grep -rn "_parse_generation_mode\|_resolve_generation_mode" src/ docs/modular-architecture/audit/ \
  --include=*.py --include=*.md --exclude=06-generation-runtime-and-ledger.md
# -> 2 definitions + 3 call sites in src/ ; 0 hits in the other audit files   (matches the finding)
UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
from film_pipeline.graph.nodes._generation_batch_planning import _parse_generation_mode as g
from film_pipeline.mcp.tools.generation.planning import _resolve_generation_mode as m
print([(s, g(s).value, m({'mode': s}).value) for s in ('test','production','','prod','TEST')])
"
# real output, exactly as printed in the finding:
# [('test', 'test', 'test'), ('production', 'production', 'production'), ('', 'test', 'test'), ('prod', 'test', 'test'), ('TEST', 'test', 'test')]
grep -rn "_parse_generation_mode\|_resolve_generation_mode" tests/
# -> no matches (grep exit 1)
```

I extended the differential to the arg forms the finding claims (`{}`, `{"mode": None}`,
`{"mode": 0}`, `{"mode": ["test"]}`) — all resolve to `TEST` on both paths, so "behaviourally
identical today" is correct.

### Defects

1. **`tests/unit/test_schemas.py:430` is misattributed.** The finding says it "pins only the
   `GenerationLedgerRow` *default*". Line 430 is `assert r.mode == GenerationMode.TEST` inside
   `test_generation_request_idempotency_key_required`, where `r = GenerationRequest(...)` — it is
   the **`GenerationRequest`** default, not `GenerationLedgerRow`'s. The substantive point (it
   does not pin the resolver) stands.
2. **`tests/unit/generation/test_ledger.py:106` is misattributed.** The finding says it "pins a
   hand-set `mode=` on `update_row`". Lines 104-106 are `test_plan_batch_respects_mode`:
   `mgr.plan_batch("proj-10", ["S001"], "p", "m", mode=GenerationMode.PRODUCTION)` then
   `assert ledger.rows[0].mode == GenerationMode.PRODUCTION`. It is `plan_batch`, not `update_row`.
3. **"the only behavioural consumer of `mode` is `ledger.py:155`" is understated.** The promote
   gate at `ledger.py:155` (`row.mode == GenerationMode.TEST`) is the only *gating* consumer, but
   `_generation_batch_planning.py:95` keys the batch grouping on `str(mode.value)`, and
   `planning.py:191` / `executor.py:330` publish `row.mode.value` into graph/operator payloads. The
   finding itself cites `:95` two sentences later, so this is an internal inconsistency.
4. **The TEST fallback has a third declaration the owner list omits.**
   `schemas/generation.py:24` — `mode: GenerationMode = GenerationMode.TEST` on
   `GenerationRequest`. The "silent fallback to TEST" policy is therefore stated at three sites
   (the two resolvers plus the request schema default), which is O5 as much as O1. The class O1 is
   not wrong, but the owner list is incomplete.

### Severity — drift should be 5, not 4

The mutation is silent. I checked every place a test could notice:

* `grep -rn "\.mode\b\|mode ==\|\"mode\"\]" tests/unit/graph/` → no matches. The graph test
  `tests/unit/graph/test_generation_node_ledger.py` drives the graph copy with `"mode": "test"`
  (`:96`) but asserts only `estimated_cost_usd` (`:128`), never the mode.
* `tests/unit/mcp/tools/test_generation.py:593` plans through the MCP resolver with **no** mode
  and then *overwrites* the mode with `mgr.update_row(..., mode=GenerationMode.TEST)` (`:606-612`)
  before promoting — so flipping the resolver fallback is masked by the test itself.
* `tests/smoke/test_operator_workflow.py:194` plans with no mode and promotes, but asserts only
  `r["ok"] is True`, not `promoted`.

So no test can fail when either copy changes: drift 5, score 3×5 = **15** (High, 9–15). The finding
recorded 4 and 12. Per §1.5 ("a verifier who disagrees with a band changes the *axes*"), the axis
to change is drift; the band word stays High.

### Is F-GEN-19 a hypothesis under §1.6.6?

**No.** §1.6.3 (rule 3) admits either (a) an existing divergence *or* (b) a mutation scenario as a
valid drift proof, and this finding uses (b) explicitly. Rule 6 ("downgrade to an unverified
hypothesis") applies to a claim that cannot be verified at all — each copy's behaviour was
verified by reading both functions and by the executed differential. Being mutation-only is not a
defect under this program's bar.

### Double-count

None. F-ARTIFACT-14 owns the *schema declaration* half (`SpendRecord.mode: str` vs
`GenerationLedgerRow.mode`), which this finding cites and does not re-count; the resolver seam is
distinct and the symbols appear in no other audit file. It is also distinct from F-GEN-06
(`GenerationStatus`) and F-GEN-04 (row transition fields), both cited.

Verdict **CORRECTED**: substance and mutation-silence confirmed, two cited anchors wrong, drift
axis re-derived upward.

---

## 4. F-ARTIFACT-14 — CORRECTED (High 12 retained, novelty claim reduced)

`audit/07-artifact-refs-and-schemas.md:768`.

### Reproduce — matches, and I executed the four asymmetries the finding only asserts

```bash
grep -rnE "^    (pacing_style|film_type|phase|next_action|mode): " src/film_pipeline/schemas/ --include='*.py' | wc -l
# -> 24
grep -rnE "^    (pacing_style|film_type|phase|next_action|mode): str" src/film_pipeline/schemas/ --include='*.py' | wc -l
# -> 13
UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
from pydantic import ValidationError
from film_pipeline.schemas.constraints import ProjectConstraints
from film_pipeline.schemas.execution_brief import ExecutionBrief
from film_pipeline.graph.scope_contract import avg_shot_duration_for
for label, fn in [('ProjectConstraints', lambda: ProjectConstraints(project_id='p', pacing_style='measured')),
                  ('ExecutionBrief   ', lambda: ExecutionBrief(project_id='p', target_runtime_seconds=60, pacing_style='measured'))]:
    try: fn(); print(label, 'ACCEPTED')
    except ValidationError as e: print(label, 'REJECTED (%s)' % e.errors()[0]['type'])
print('avg_shot_duration_for(measured) =', avg_shot_duration_for('measured'), '(standard =', avg_shot_duration_for('standard'), ')')
"
# real output, exactly as printed in the finding:
# ProjectConstraints REJECTED (literal_error)
# ExecutionBrief    ACCEPTED
# avg_shot_duration_for(measured) = 6.5 (standard = 6.5 )
```

The four remaining asymmetries are asserted in the drift-proof prose but **not commanded in the
`Reproduce` block** (§1.6.4 wants reproducible counts/probes). I ran them; all four reproduce:

```
ProjectProfile      film_type=also_nonsense REJECTED (enum)
StoryScopeContract  film_type=also_nonsense ACCEPTED
ApprovalRecord      phase=bogus             REJECTED (enum)
MatrixPatch         phase=bogus             ACCEPTED
GenerationLedgerRow next_action=bogus       REJECTED (literal_error)
ResumeToken         next_action=bogus       ACCEPTED
GenerationLedgerRow mode=bogus              REJECTED (enum)
SpendRecord         mode=bogus              ACCEPTED
```

(Note: `ProjectProfile` needs a `ProjectIdentity`; `StoryScopeContract` needs
`target_runtime_seconds`, `avg_shot_duration_seconds`, `target_scene_count`, `min_scene_count`,
`target_shot_count`, `shots_per_scene_low/high`; `GenerationLedgerRow` needs `mode` because
`next_action` has a default and `mode` does not. An earlier attempt of mine got `REJECTED
(missing)` on several of these purely from under-specified constructors — the values above are
the correct ones, and they confirm the finding.)

### Double-count — the pacing half is largely F-CFG-14's

F-ARTIFACT-14's prior-art block claims: "audit/03 … F-CFG-14 … owns the *mapping-rule* half — the
two alias tables and the `ExecutionBrief` bridge … **this finding owns the *schema-declaration*
half** … The schema half is new; the rule half is not restated."

That split is not accurate. Audit 03 **F-CFG-14** (`03-config-profile-and-defaults.md:721`) lists
as its de-facto owners, verbatim:

* `schemas/constraints.py:61` — "the canonical vocabulary as a schema `Literal`", and
* `schemas/execution_brief.py:51-53` — "a fourth, unvalidated spelling of the same vocabulary
  (plain `str`, the values only in the description)",

and its extraction sketch says "**type `ExecutionBrief.pacing_style: PacingStyle`**" with
`schemas` as the candidate owner. So two of F-ARTIFACT-14's three pacing declaration sites, the
`schemas`-owner remedy for pacing, and the `"measured"` divergence (F-CFG-14 executes
`avg_shot_duration_for("slow cinema")`, and both findings cite the *same* pinning test
`tests/unit/agents/test_impl_agents.py:603`) are already F-CFG-14's. The only pacing site genuinely
new to F-ARTIFACT-14 is `schemas/scope_contract.py:23` (`StoryScopeContract.pacing_style`).

Likewise the phase half: `schemas/artifact.py:24 phase: str` is already owned by
**F-ARTIFACT-01** (F-ARTIFACT-14 says so), and audit 01's coverage table
(`01-phase-model-and-transitions.md:95`) explicitly records that "`FilmPhase` … is the only
canonical *type*; every other site uses raw strings (**F-PHASE-02**)". F-ARTIFACT-14 never cites
F-PHASE-02. Typing the eight `phase: str` fields as `FilmPhase` is still an un-owned *action*
(F-PHASE-02's remedy is `PHASE_DIR_MAP`-keying and a literal sweep, not field typing), so this is
an uncited extension, not a plain duplicate.

What is genuinely new and un-owned in F-ARTIFACT-14: the `film_type` asymmetry
(`constraints.py:57` / `project.py:36` closed vs `scope_contract.py:22` bare), the `next_action`
and `mode` asymmetries (`schemas/generation.py:43,73-80` vs `ResumeToken`; `budget.py:31` vs
`generation.py:24,57`), the `StoryScopeContract.pacing_style` site, the 24/13 quantification, and
the `schemas`-layer reflection guard test.

### Other checks

* The exclusions of same-name/different-domain fields (`role`, `status`, `outcome`, `severity`)
  are honest — I re-checked `severity` (`IssueSeverity` vs `failure.py` `severity: str`
  "blocking|non_blocking"), `status` (at least five distinct vocabularies) and `role`
  (`AgentRole` vs narrative character role).
* F-ARTIFACT-01/02/08 do not own any of the four new fields; F-ARTIFACT-02's
  `_ARTIFACT_TYPE_BY_CLASS` concern is orthogonal.

### Severity

The four un-owned fields carry real acceptance gaps at persistence boundaries
(`StoryScopeContract.film_type`, `MatrixPatch.phase`, `ResumeToken.next_action`,
`SpendRecord.mode`), so impact 3 is defensible and drift 4 holds (no test compares the
declarations; the mutation is silent). 3×4 = 12, High. But the finding should not claim the schema
half is new for pacing: it is an extension of F-CFG-14 for two of three sites, and of F-PHASE-02
for `phase`. **CORRECTED**, band High 12 unchanged (score would fall to Medium 8 if the pacing
axis were struck entirely and only the pacing evidence counted, so the citation fix matters).

---

## 5. F-KBCTX-14 — CORRECTED (High 12 retained only after citing F-CFG-15)

`audit/09-kb-context-and-provenance.md:716`.

### Anchors and Reproduce — output matches exactly

```bash
grep -rn "DEFAULT_MAX_CONTEXT_CHARS = \|MIN_COMPRESSED_CONTEXT_CHARS = " src/film_pipeline/kb/compression.py
# src/film_pipeline/kb/compression.py:10:DEFAULT_MAX_CONTEXT_CHARS = 6000
# src/film_pipeline/kb/compression.py:11:MIN_COMPRESSED_CONTEXT_CHARS = 256
grep -rn "\[:8000\]\|\[:6000\]\|\[:200\]\|\[:150\]\|\[:80\]\|\[:60\]\|\[:800\]" --include=*.py \
  src/film_pipeline/mcp/tools/bibles/ src/film_pipeline/graph/nodes/_context.py
# src/film_pipeline/mcp/tools/bibles/character.py:39:{script_text[:8000]}
# src/film_pipeline/mcp/tools/bibles/environment.py:40:{script_text[:8000]}
# src/film_pipeline/mcp/tools/bibles/shot.py:184:        f"Script:\n{script_text[:6000]}\n\n"
# src/film_pipeline/graph/nodes/_context.py:110, :189, :215, :217, :241, :243   (the six ad-hoc slices)
grep -rn "def compress_prompt_for_retry\|compress_prompt_for_retry(rendered_prompt" --include=*.py \
  src/film_pipeline/providers/failure_classifier.py src/film_pipeline/agents/runner.py
# failure_classifier.py:214  def compress_prompt_for_retry(prompt_text: str, *, factor: float = 0.6) -> str:
# agents/runner.py:240       rendered_prompt = compress_prompt_for_retry(rendered_prompt, factor=0.6)
# agents/runner.py:281       compressed = compress_prompt_for_retry(rendered_prompt, factor=0.35)
grep -rn "MAX_PROMPT_LENGTH" --include=*.py src/film_pipeline/validation/impl/prompt_readiness.py
# prompt_readiness.py:15:MAX_PROMPT_LENGTH: Final[int] = 8000  # characters
# prompt_readiness.py:83:    if len(rendered) <= MAX_PROMPT_LENGTH:
# prompt_readiness.py:90:                f"Prompt '{prompt_id}' is {len(rendered)} chars (> {MAX_PROMPT_LENGTH} limit)."
```

All six `_context.py` slice anchors, the env override (`config/runtime_overrides.py:19`), and the
resolved-budget function (`_context.py:451-465`) resolve; `kb/compression.py:57-61` really is the
JSON-aware head-2/3 + tail-1/3 compaction, and `:64-65` really is a `max(256, …)` floor. The two
struck corrections are right: the three `agents/impl/*[:2000]` sites are `except ValidationError`
log truncations of invalid model output, not prompt bounds, and `256` is a floor.

### The double-count: audit 03 F-CFG-15 already owns the MCP half

Audit 03 **F-CFG-15** (`03-config-profile-and-defaults.md:765`) is titled "The model-input size cap
is code-only policy and the gate already disagrees with the truncation site (8000 vs 6000)" and
lists as de-facto owners, verbatim:

* `validation/impl/prompt_readiness.py:15` `MAX_PROMPT_LENGTH: Final[int] = 8000`,
* `validation/impl/prompt_readiness.py:83` its only enforcement,
* `mcp/tools/bibles/character.py:39` `{script_text[:8000]}`,
* `mcp/tools/bibles/environment.py:40` the same truncation re-spelled,
* `mcp/tools/bibles/shot.py:184` "a third, *different* truncation" `{script_text[:6000]}`,
* `frame_reviewer.py:68,82,88` the paid-review sampling rate.

Its drift proof says: a 7,000-char script "passes readiness … and is truncated by 1,000 characters
with no error … The two `[:8000]` builders … happen to match the gate, which is exactly why the
6000 site stays invisible: **each builder is its own authority and nothing compares them**."

F-KBCTX-14 re-lists all three MCP bible sites, re-uses the 8000-vs-6000 disagreement, and frames
the same "no surface shares a budget / no guard" defect — without citing F-CFG-15 anywhere. Its
prior-art block goes further and states: "**New here:** none of the prior art frames the caps as
distributed ownership with no guard … and **no finding id existed**." The second clause is
demonstrably false: F-CFG-15 is a finding id whose concern *is* exactly that. So the finding's
novelty claim is refuted by an existing sibling finding, and its claim to close the
`01-ownership-map.md` "Compression / bounding — no finding id" gap is at best half true.

Independently, the retry-factor element is already recorded as prior art
(`documentation/reviews/arch-lens-cognition.md:166-167` names "compression factors 0.6/0.35 carried
across attempts, L240/L281"), which F-KBCTX-14 itself cites, and audit 05 §4.4
(`05-provider-runtime-and-health.md:1020-1023`) already declares
`failure_classifier.is_token_limit_exceeded`/`compress_prompt_for_retry` a single-owner, test-pinned
concern. That row is about the function's ownership, not the two per-branch factor values, so it is
an adjacency rather than a duplicate — but it belongs in the citation list.

### What is genuinely new

* `kb/compression.py:10` `DEFAULT_MAX_CONTEXT_CHARS = 6000` as the *intended* single budget,
  consumed only by the graph (`_context.py:12`), and overridable through
  `FILM_PIPELINE_MAX_CONTEXT_CHARS` → `("context", "max_chars_per_artifact")`
  (`config/runtime_overrides.py:19`) — none of which F-CFG-15 mentions.
* The six ad-hoc `_context.py` slices (`:110, :189, :215, :217, :241, :243`); the finding notes the
  coverage pass missed `:110` and `:243`.
* The graph-vs-MCP comparison *pair* (kb 6000 vs bible 8000) is different from F-CFG-15's
  gate-vs-builder pair (8000 vs 6000), even though it uses the same three MCP sites.

### Severity

Impact 3 (a silently shortened prompt loses context; nothing raises — the compaction clamps and a
blunt slice can never fail) and drift 4 (no test pins any producer budget; the mutation is silent —
verified: the only `max_chars` literals in `tests/` are explicit small values, the validator is
pinned by a single 9000-char fixture, and MCP bible tests assert truthiness only). 3×4 = 12, High.

**The band is retained only on the new axis.** If the parent applies strict de-duplication (F-CFG-15
owns the MCP trio, audit 05 owns the retry function, prior art owns the factors), what remains —
the `kb` budget plus six formatting slices in one module — is not a distributed-ownership seam in
the §1.3 sense, and the honest re-score is Medium 2×4 = 8. The correct resolution is the one the
program's own convention prescribes: keep F-KBCTX-14, cite F-CFG-15, and present the MCP trio and
the 8000-vs-6000 disagreement as F-CFG-15's evidence. Verdict **CORRECTED**.

---

## What the authors should fix

1. **`F-KBCTX-14` prior art (highest priority).** Delete the false "no finding id existed" and
   "none of the prior art frames the caps as distributed ownership with no guard" clauses. Cite
   audit 03 **F-CFG-15** for `character.py:39` / `environment.py:40` / `shot.py:184`,
   `prompt_readiness.py:15,83`, and the 8000-vs-6000 disagreement; cite audit 05 §4.4 and
   `arch-lens-cognition.md:166-167` for the retry ladder. Scope the novelty to the `kb` budget, the
   `FILM_PIPELINE_MAX_CONTEXT_CHARS` override, and the six `_context.py` slices. Either drop the
   three MCP sites from the de-facto-owner list or mark them "owned by F-CFG-15; restated here as
   context". If the parent instead wants each finding to own disjoint evidence, downgrade to
   Medium 8.
2. **`F-GEN-19` test attributions.** `tests/unit/test_schemas.py:430` pins the **`GenerationRequest`**
   default, not `GenerationLedgerRow`'s; `tests/unit/generation/test_ledger.py:106` is
   `test_plan_batch_respects_mode` asserting `plan_batch(..., mode=PRODUCTION)`, not an
   `update_row` call. Also add `schemas/generation.py:24` (`GenerationRequest.mode =
   GenerationMode.TEST`) to the owner list, change "the only behavioural consumer" to "the only
   *gating* consumer", and raise drift 4 → 5 (score 12 → 15). Keep it a finding: §1.6.3(b) accepts
   mutation-only proofs.
3. **`F-GEN-18` mutation parenthetical.** A mistyped sheet type returns
   `_failed_result` at `sheet_reviewer.py:101-103` *before* the paid call — so it skips the review,
   it does not pay for one. Move the "still pays" fact to the correctly-typed path whose result
   `_validate_composite` discards. Add `--include=*.py` to the first `Reproduce` command (its
   stated "43,222 only" output is pyc-dependent), and cite the live `asset_type` consumers
   (`entries.py:101-105` aspect ratio, `frame_reviewer.py:91` review policy) in the impact case.
4. **`F-ARTIFACT-14` ownership split.** Rewrite the prior-art split so it does not claim the
   schema-declaration half is new for pacing: F-CFG-14 already owns `constraints.py:61` and
   `execution_brief.py:51-53` plus the `schemas`-owner remedy, and both findings share the
   `test_impl_agents.py:603` pin. Cite audit 01 **F-PHASE-02** for the `phase` half. Add the four
   asserted-but-uncommanded asymmetry probes to the `Reproduce` block, with the required
   constructor fields.
5. **`F-GEN-17` presentation nit.** The chain labels `_reference_prompt` at `entries.py:92` and
   `_build_environment_prompt` at `prompt_builder.py:169`; those are the delegation lines
   (`def`s at `:77` and `:157`). Rule §1.6.1 permits enforcing lines, so this is optional, but
   labeling them as the call sites removes any ambiguity. No substantive change needed.

## What I attacked and what survived

* **F-GEN-17:** five refutation attempts (re-mapping, reviewer rejection, placement, manifest
  recording, cross-audit ownership) — all failed. The executed divergence is real; the frame
  disappears from both the board and its `.sheet.json`. Critical 20 stands.
* **F-GEN-18:** I tried to raise impact back to 4 by finding a live consumer of the sheet bar —
  there is none (`regenerate_failing_tiles` is uncalled; `_validate_composite` discards the
  result), so the finding's own downgrade to 3 is correct. I also verified every threshold fixture
  and both mutation bands.
* **F-GEN-19:** I tried to find a test that would fail under the mutation — the graph suite asserts
  no mode, the MCP promote test overwrites the mode, and the smoke test asserts only `ok`. The
  mutation is silent, which makes the finding *stronger* on drift, not weaker.
* **F-ARTIFACT-14:** I re-executed all five asymmetries and all four rejected constructors; every
  one reproduces. The weakness is citation, not fact.
* **F-KBCTX-14:** every command and anchor reproduces; the weakness is that a large part of its
  evidence is audit 03 F-CFG-15's, and its novelty sentence is false.

## Residual risk / open questions for the parent

* Whether F-CFG-15 and F-KBCTX-14 should be **merged** into one cross-audit "model-input budget"
  finding, or kept as siblings with an explicit ownership split. I recommend the split (they ask
  different questions: gate-vs-builder vs graph-vs-MCP), but the two prior-art blocks must agree.
* `F-ARTIFACT-14`'s severity is sensitive to whether the `phase`/`film_type`/`next_action`/`mode`
  acceptance gaps count as impact 3 without a demonstrated downstream wrong behavior. I kept 3
  because `StoryScopeContract.film_type` and `MatrixPatch.phase` are persisted fields that feed
  planning/routing and accept arbitrary strings; a stricter verifier could argue 2. The drift (4) is
  not in doubt.
* No finding in this batch needed a `REJECTED` verdict; the strongest single defect is
  F-KBCTX-14's false novelty claim, which is a citation error rather than a factual one.
