# verify-18 — bar A6 closure for eight post-verification findings

- **Target:** the eight `PENDING VERIFICATION` findings that were added *after* their
  audit's verification pass and that no verifier has ever re-checked:
  `F-PHASE-11` (audit 01), `F-OST-17` (audit 02), `F-AGENT-11` / `F-AGENT-12`
  (audit 04), `F-PROV-08` (audit 05), `F-GEN-14` / `F-GEN-15` / `F-GEN-16` (audit 06).
  Their newer siblings (`F-OST-18`, `F-AGENT-13`, `F-PROV-09`,
  `F-GEN-17/18/19`) are out of scope and were **not** read as findings.
- **Repo / commit:** `${REPO_ROOT}`, branch
  `modular-app`. `git rev-parse HEAD` at verification time:
  `fb85baa0e6b769b709791a96a89980089304bf13` (`fb85baa`), working tree clean at start.
- **Snapshot (pristine, used for all `src/`, `tests/` and YAML reads):**
  ```
  mkdir -p /tmp/v18 && git archive fb85baa | tar -x -C /tmp/v18
  ```
  `.venv` was symlinked into `/tmp/v18` so the findings' verbatim
  `.venv/bin/python` commands run unchanged, and `diff -rq` confirmed the snapshot's
  `src/` is byte-identical to the repo working tree except `__pycache__`.
  Mutation experiments were run in throwaway copies `/tmp/v18m` under the workspace
  `.venv` with `PYTHONPATH=/tmp/v18m/src` (the editable install otherwise resolves to
  the repo tree — verified: `import film_pipeline` from `/tmp/v18m` without
  `PYTHONPATH` prints the repo path).
- **Verifier:** independent adversarial pass; did not write any of the eight blocks,
  the audit files, or the earlier `verify-*.md` files. Bar read in full:
  `00-methodology-and-quality-bar.md` §1.3–§1.7, §2 (A2/A3/A4/A6/A7), §1.5 rubric.
- **Method:** every `path:line` re-printed from `/tmp/v18`; every `Reproduce`
  command re-run verbatim with its real output recorded; every drift proof attacked,
  and each finding whose proof claims "no test fails" was re-checked by actually
  applying the named mutation to a pristine copy and running the suite. Baseline on
  the unmutated copy:
  ```
  cd /tmp/v18m && PYTHONPATH=/tmp/v18m/src .venv/bin/python -m pytest tests/unit \
    -o addopts="-n auto -q --import-mode=importlib --strict-markers"
  → 1866 passed, 3 skipped, 10 warnings in 17.58s
  ```
- **Severity:** re-scored independently with §1.5 (impact 1–5 × drift 1–5;
  Critical ≥16, High 9–15, Medium 4–8, Low 1–3).

---

## Verdict table

| finding | verdict | severity as written | severity re-scored | one-line reason |
|---|---|---|---|---|
| F-PHASE-11 | **CONFIRMED-WITH-FIX** | Medium (2×4=8) | Medium (2×4=8) | Drift proof and mutation reproduce; **"the only reader" is false** — `kb/retrieval.py:49` re-implements the same filter (missing O2/site). |
| F-OST-17 | **CONFIRMED-WITH-FIX** | Medium (2×3=6) | Medium (2×3=6) | All anchors and both reproduce commands exact; **prior art claim is false** — `documentation/reviews/arch-lens-dataflow.md` F-1/F-6 already records the dead review-cycle channel. |
| F-AGENT-11 | **CONFIRMED** | High (2×5=10) | High (2×5=10) | All anchors exact; both branches disabled → 1866 passed, 3 skipped; no test references the module. |
| F-AGENT-12 | **CONFIRMED-WITH-FIX** | High (3×4=12) | High (3×5=15) | Divergence and silent mutation reproduce; drift is 5, not 4, and the block overlaps F-AGENT-08/F-AGENT-10 owners. |
| F-PROV-08 | **CONFIRMED-WITH-FIX** | High (3×5=15) | High (3×5=15) | Triplication and unpinned endpoints reproduce; **prior art claim is false** (B-F3 / arch-lens-boundaries) and the cited `audit/14:96` anchor does not resolve to that claim. |
| F-GEN-14 | **STRENGTHENED** | Medium (3×2=6) | **High (3×5=15)** | CANCELLED divergence is real; the consumer mapping is completely unpinned (inverting it fails nothing), so drift is 5, not 2. The named enum-rename mutation is *not* silent — it fails tests. |
| F-GEN-15 | **CONFIRMED-WITH-FIX** | High (3×3=9) | High (3×3=9) | Divergence and silent sentinel mutation reproduce; the drift proof's rebuilt path form is wrong (`Path` elides the empty segment). |
| F-GEN-16 | **CONFIRMED-WITH-FIX** | Medium (2×3=6) | Medium (2×3=6) | Write-surface bypass real and silent (renaming all five sheet outputs → 48 passed); **all five `composites.py` anchors point at import lines, not the path-building lines**, the identifier is `sheet_path` not `output_path`, and `O7 + unenforced invariant` is not a valid §1.4 class. |

Counts: **1 CONFIRMED, 6 CONFIRMED-WITH-FIX, 1 STRENGTHENED, 0 DOWNGRADED, 0 REJECTED.**

---

## F-PHASE-11 — KB keys items by unvalidated free-string phase names

**Anchors.** All three resolve at `fb85baa`; the YAML list is exact.

| anchor | actual line in `/tmp/v18` | verdict |
|---|---|---|
| `schemas/kb.py:25` | `applies_to_phases: list[str] = Field(default_factory=list)` | exact |
| `kb/manifest.py:40-45` | `def by_phase(...)` … `if "all" in i.applies_to_phases or phase in i.applies_to_phases` | exact |
| `kb-manifest.yaml:13,29,45,61,77,93,111,127,143,161,177,193` | 12 `applies_to_phases:` lines, exactly those line numbers; `:111` `[visual_dev, gen_planning]`, `:93` `[qc, post]` | exact |
| `tests/unit/kb/test_manifest.py:48-55` | `test_by_phase_all_match` … `assert len(items) >= 8` | exact |
| block text: `kb/manifest.py:40-45` is **"the only reader"** | **FALSE** — `src/film_pipeline/kb/retrieval.py:49` contains the byte-identical predicate inside `KBRetrieval.search` | **defect** |

```
$ sed -n '48,52p' src/film_pipeline/kb/retrieval.py
        if phase is not None:
            items = [
                i for i in items if "all" in i.applies_to_phases or phase in i.applies_to_phases
            ]
```

**Reproduce (verbatim, run in `/tmp/v18`).**
```
$ grep -h "applies_to_phases" film-knowledge-base/index/kb-manifest.yaml | grep -oE '\[[^]]*\]' | tr -d '[]' | tr ',' '\n' | tr -d ' ' | sort -u
all
gen_planning
generation
post
qc
visual_dev

$ grep -c "applies_to_phases" film-knowledge-base/index/kb-manifest.yaml
12

$ grep -rn "applies_to_phases\|by_phase" src/film_pipeline tests/ --include='*.py'
src/film_pipeline/kb/manifest.py:40:    def by_phase(self, phase: str) -> list[KBItemMetadata]:
src/film_pipeline/kb/manifest.py:44:            if "all" in i.applies_to_phases or phase in i.applies_to_phases
src/film_pipeline/kb/retrieval.py:49:                i for i in items if "all" in i.applies_to_phases or phase in i.applies_to_phases
src/film_pipeline/mcp/tools/kb.py:52:                    "phases": i.applies_to_phases,
src/film_pipeline/mcp/tools/kb.py:79:            applies_to_phases=item.applies_to_phases,
src/film_pipeline/schemas/kb.py:25:    applies_to_phases: list[str] = Field(default_factory=list)
tests/unit/kb/test_manifest.py:48:    def test_by_phase_all_match(self, manifest: KBManifest) -> None:
tests/unit/kb/test_manifest.py:50:        items = manifest.by_phase("generation")
tests/unit/test_schemas.py:639:        applies_to_phases=["all"],

$ .venv/bin/python -c "import sys;sys.path.insert(0,'src');from film_pipeline.schemas._base import FilmPhase;print([t for t in ('gen_planning','generation','post','qc','visual_dev') if t not in [x.value for x in FilmPhase]])"
[]
```
The first command prints exactly the claimed token set. The third command's own output
surfaces the second reader the block does not cite.

**Drift-proof attack.** The stated mutation was applied to the pristine copy and the
whole unit suite run:
```
$ sed -i '' 's/\[visual_dev, gen_planning\]/[visualdev, gen_planning]/' film-knowledge-base/index/kb-manifest.yaml
$ grep -n visualdev film-knowledge-base/index/kb-manifest.yaml
111:    applies_to_phases: [visualdev, gen_planning]
$ PYTHONPATH=/tmp/v18m/src .venv/bin/python -m pytest tests/unit \
    -o addopts="-n auto -q --import-mode=importlib --strict-markers"
→ 1866 passed, 3 skipped
```
Silent, as claimed. The finding's account of the guard (`>= 8` cardinality bound that a
typo cannot break) is accurate. Two sharpenings: (i) the same typo also silently
shrinks `KBRetrieval.search(phase=...)`, so the seam has **two** independent consumers;
(ii) a mutation of the *reader* predicate does fail `test_by_phase_all_match`, which is
why drift 4 (not 5) is defensible. I keep drift 4.

**Severity verdict.** **Medium (impact 2 × drift 4 = 8) — unchanged.** Impact 2 is right
(the leak is latent; every token is currently valid). If the reader-side cardinality
pin is discounted, drift is 5 and the score is 10 (High); I do not move it, because the
reader is weakly pinned and the defect is a missing contract on the data side.

**Class / prior art / double-count.** Class `O8 + O4` is right but incomplete: the
duplicated filter at `kb/retrieval.py:49` is `O2` (duplicated invariant enforcement) and
should be named. Prior art `new` is **verified**: `grep -rl "applies_to_phases\|by_phase"
documentation/ docs/clean-code-refactor/` returns nothing. Double-count: `F-PHASE-02`'s
"Also phase-keyed but not line-initial (lower bound only, M2)" paragraph already lists
`schemas/kb.py:25`/`kb/manifest.py:44`/manifest YAML, and the ownership-map row
(audit 01 line 433) counts the KB registry inside F-PHASE-02's inventory. F-PHASE-11 is a
carve-out of F-PHASE-02's partial-index evidence, not an independent owner set — the two
blocks should state that relationship in opposite directions (F-PHASE-02 does; the
F-PHASE-11 block should cite F-PHASE-02 rather than read as a new discovery).

---

## F-OST-17 — Review-cycle channel has no production writer

**Anchors.** Every anchor resolves exactly. Measured from `/tmp/v18`:

| anchor | actual |
|---|---|
| `orchestrator_state.py:35` | `_ACTIVE_REVIEW_CYCLES = f"{_ORCH_NS}__active_review_cycles"` |
| `:105-109` | the `OrchChannelSpec(_ACTIVE_REVIEW_CYCLES, "explicit", "review-cycle writers return cycles in updates")` row (spec at 104-108; 109 opens the next spec) |
| `:228-243` | `def start_review_cycle(...)` … `state.setdefault(_ACTIVE_REVIEW_CYCLES, []).append(cycle)` at `:242` / `return cycle` |
| `:246-252` / `:255-260` | `advance_review_round` / `close_review_cycle` |
| `:523` | `state.setdefault(_ACTIVE_REVIEW_CYCLES, [])` |
| `state_schema.py:190` | `_orchestrator__active_review_cycles: list[dict[str, Any]]` |
| `mcp/tools/state.py:40` | `review_cycle = ostate.get_active_review_cycle(state, str(state.get("current_phase", "")))` |
| `:55` | `active_review_cycle=review_cycle,` |

The secondary contract-break claim is confirmed by the same read: the registered
propagation is `"explicit"` ("writers return cycles in updates") while
`start_review_cycle` returns the bare `cycle` dict after an in-place `append`.

**Reproduce (verbatim).**
```
$ grep -rn "start_review_cycle\|advance_review_round\|close_review_cycle" src/ --include=*.py
src/film_pipeline/graph/orchestrator_state.py:228:def start_review_cycle(
src/film_pipeline/graph/orchestrator_state.py:246:def advance_review_round(state: dict[str, Any], phase: str) -> dict[str, Any] | None:
src/film_pipeline/graph/orchestrator_state.py:255:def close_review_cycle(state: dict[str, Any], phase: str, *, status: str = "completed") -> None:

$ .venv/bin/python -c "
from film_pipeline.graph import orchestrator_state as o
s = {'current_phase': 'script'}
o.ensure_orchestrator_state(s)
print(o.get_active_review_cycle(s, 'script'))"
None
```
Both print exactly what the block says ("the second command prints `None`; the first
shows no production caller"). The claim that the only other hits are
`tests/unit/graph/test_orchestrator_state.py:62-91` is confirmed:
```
$ grep -rn "start_review_cycle\|advance_review_round\|close_review_cycle\|active_review_cycle" tests/ --include=*.py
tests/unit/graph/test_orchestrator_state.py:64:    cycle = ostate.start_review_cycle(state, "script", strategy="parallel_independent")
tests/unit/graph/test_orchestrator_state.py:71:def test_advance_review_round_increments() -> None:
tests/unit/graph/test_orchestrator_state.py:73:    ostate.start_review_cycle(state, "script")
tests/unit/graph/test_orchestrator_state.py:74:    ostate.advance_review_round(state, "script")
tests/unit/graph/test_orchestrator_state.py:75:    cycle = ostate.get_active_review_cycle(state, "script")
tests/unit/graph/test_orchestrator_state.py:80:def test_close_review_cycle() -> None:
tests/unit/graph/test_orchestrator_state.py:82:    ostate.start_review_cycle(state, "script")
tests/unit/graph/test_orchestrator_state.py:83:    ostate.close_review_cycle(state, "script", status="completed")
tests/unit/graph/test_orchestrator_state.py:84:    cycle = ostate.get_active_review_cycle(state, "script")
tests/unit/graph/test_orchestrator_state.py:89:def test_get_active_review_cycle_none_for_unknown_phase() -> None:
tests/unit/graph/test_orchestrator_state.py:91:    assert ostate.get_active_review_cycle(state, "qc") is None
tests/integration/test_dynamic_routing.py:118:        "_orchestrator__active_review_cycles": [],
```

**Drift-proof attack.** The proof is the existing-divergence limb (§1.6.3a), and it
holds: nothing in `src/` appends to the channel outside the test-only API, the MCP
summary is the only live reader, and the field is always `None`. I additionally tested
the claim that "wiring a writer (or deleting the channel) cannot fail a test today" by
deleting the reader field:
```
$ sed -i '' '/^        active_review_cycle=review_cycle,$/d' src/film_pipeline/mcp/tools/state.py
$ PYTHONPATH=/tmp/v18m/src .venv/bin/python -m pytest tests/unit \
    -o addopts="-n auto -q --import-mode=importlib --strict-markers"
→ 1866 passed, 3 skipped
```
A one-sided change on the MCP side is fully silent. The owner API itself *is* pinned
(`test_orchestrator_state.py:62-91`), so a one-sided change on the owner side is not
fully silent. Drift 3 (partial pinning) is defensible; a strict reading of §1.5 could
argue 4 (score 8, still Medium) or 5 (score 10, High). I keep 3/6 because one side is
pinned, but flag the band sensitivity.

**Severity verdict.** **Medium (impact 2 × drift 3 = 6) — unchanged.** Impact 2 is right:
the surface is always `None`; nothing durable or deliverable is corrupted.

**Class / prior art / double-count.** Class `O3 + O8` is defensible and matches the
program's accepted precedent (`F-OST-16` was CONFIRMED with the same "dead channel +
live reader" structure in `verify-02.md`). Structurally this is also *incompleteness*
(§1.3 excludes unfinished features from distributed ownership); it survives only because
the program has already accepted that shape. **Prior art is wrong as written:** the
block says "new — this channel is not covered by any prior review
(`documentation/reviews/*` records the routing-decision, failure, budget and provider
writers, but not the review-cycle API)". In fact
`documentation/reviews/arch-lens-dataflow.md` records it twice:
```
$ grep -n "active_review_cycle\|start_review_cycle" documentation/reviews/arch-lens-dataflow.md
28:| `active_review_cycles` | none (tests only) | n/a |          # F-1 per-channel write map
156:... Same for `start_review_cycle`/`advance_review_round`/`close_review_cycle`
    (`orchestrator_state.py:126-157`) and `record_routing_decision` ... — test-only, so
    `_orchestrator__active_review_cycles` and `_orchestrator__routing_decisions` are
    permanently empty in real runs.
160:... delete `active_review_cycles` and the duplicate-namespaced
    `_orchestrator__routing_decisions` ...
```
`documentation/reviews/arch-review-critic.md:111` also groups the dead channels. The
honest A7 statement is: *prior art records the dead channel and the wire-or-delete
decision; new here is the live MCP reader that publishes the always-`None` field.*
Double-count: `F-OST-16` (routing decisions) and `F-OST-17` (review cycles) describe
different channels/owners, so this is a sibling, not a duplicate; but F-OST-17 should
name F-OST-16 and arch-lens-dataflow F-6 as the same seam class rather than presenting
itself as new.

---

## F-AGENT-11 — Per-agent prompt policy re-derived by identity branches

**Anchors.** All resolve exactly.

| anchor | actual line in `/tmp/v18` |
|---|---|
| `_agent_prompt_context.py:94` | `if agent_id == "orchestrator-agent":` (followed by `context_vars.update(_build_phase_context(state))`) |
| `:148` | `if agent_id == "structure-extractor-agent" and context_vars.get("script_content"):` (followed by `_set_script_scene_count(context_vars)`) |
| `:136-149` | `def _augment_phase_context(...)` — hardcodes both branches |
| `_agent.py:146,150` | `context_vars = _build_template_context(state, kb)` / `_augment_phase_context(context_vars, state, services, phase, agent_id)` |
| `spine.py:12-15,40,59` | `def _structure_extractor()` / `agent_id="structure-extractor-agent",` / `"   - The script has {script_scene_count} scenes; the total must be "` / `"Script scene count: {script_scene_count}\n"` |

No bare-basename or cluster-relative paths in this block.

**Reproduce (verbatim).**
```
$ grep -rn -e "_maybe_add_orchestrator_context" -e "_set_script_scene_count" src/ tests/ --include=*.py
src/film_pipeline/graph/nodes/_agent_prompt_context.py:88:def _maybe_add_orchestrator_context(
src/film_pipeline/graph/nodes/_agent_prompt_context.py:126:def _set_script_scene_count(context_vars: dict[str, str]) -> None:
src/film_pipeline/graph/nodes/_agent_prompt_context.py:145:    _maybe_add_orchestrator_context(context_vars, state, agent_id)
src/film_pipeline/graph/nodes/_agent_prompt_context.py:149:        _set_script_scene_count(context_vars)

$ grep -rn -e "_agent_prompt_context" -e "_maybe_add_orchestrator_context" tests/ --include=*.py
(no output; exit 1)
```
The drift proof's grep returns nothing, as claimed ("the module is not referenced by any
test"). The `Reproduce` bullet itself prints the four `src/` sites and no expected
output; that is acceptable but weaker than the other blocks — it should carry the
`# no test hits` annotation the drift proof relies on.

**Drift-proof attack.** The named mutation was applied to the pristine copy:
```
$ sed -i '' 's/    if agent_id == "orchestrator-agent":/    if False:  # MUTATION/' src/film_pipeline/graph/nodes/_agent_prompt_context.py
$ sed -i '' 's/    if agent_id == "structure-extractor-agent" and context_vars.get("script_content"):/    if False:  # MUTATION/' .../_agent_prompt_context.py
$ PYTHONPATH=/tmp/v18m/src .venv/bin/python -m pytest tests/unit \
    -o addopts="-n auto -q --import-mode=importlib --strict-markers"
→ 1866 passed, 3 skipped
```
Silent, exactly as claimed. The upstream concern is also real: `spine.py:40,59` renders
`{script_scene_count}`, and only the `agent_id == "structure-extractor-agent"` branch at
`:148` supplies it; no descriptor field records the requirement.

**Severity verdict.** **High (impact 2 × drift 5 = 10) — unchanged.** Impact 2 is right
(prompt-quality degradation, no error, recoverable); drift 5 is exactly demonstrated.

**Class / prior art / double-count.** Class `O5` is correct. Prior art "none found" is
acceptable for this seam, with one qualification: `documentation/reviews/hardcoded-values-inventory.md:209`
already names `graph/nodes/_agent_prompt_context.py:51-53`, but for the pricing prompt
block, not the identity branches — the block should say "the file is cited elsewhere for
a different concern; this seam is new". No double-count with the other seven:
F-AGENT-10 (`_AGENT_PROFILE_MAP` orphans), F-AGENT-12 (profile values) and F-AGENT-13
(capability sets) all concern different mechanisms.

---

## F-AGENT-12 — `_AGENT_PROFILE_MAP` validator rows contradict the validator roster

**Anchors.** All resolve exactly.

| anchor | actual line in `/tmp/v18` |
|---|---|
| `graph/nodes/_context.py:41` | `"scene-continuity-validator": "strict_validator",` |
| `:42` | `"full-movie-flow-validator": "strict_validator",` |
| `validation/validators/__init__.py:131` | `model_profile="multimodal_reviewer",` (scene-continuity row) |
| `:151` | `model_profile="multimodal_reviewer",` (full-movie-flow row) |
| `validation/impl/scene_continuity.py:217` | `model_profile="multimodal_reviewer",` |
| `validation/base.py:122-125` | `profile = self.entry.model_profile` … `model = self._router.resolve_or_raise(profile)` |

The "one of which — `full-movie-flow-validator` — has neither an impl entry nor a prompt
template" claim is confirmed: the reproduce grep below returns no impl/template hit for
that id.

**Reproduce (verbatim).**
```
$ grep -rn "scene-continuity-validator\|full-movie-flow-validator" src/ --include=*.py
src/film_pipeline/graph/nodes/_context.py:41:    "scene-continuity-validator": "strict_validator",
src/film_pipeline/graph/nodes/_context.py:42:    "full-movie-flow-validator": "strict_validator",
src/film_pipeline/agents/mvp/__init__.py:5:scene-continuity-validator, full-movie-flow-validator, kb-curator) are kept out
src/film_pipeline/agents/prompt_templates/defaults/validators.py:218:        agent_id="scene-continuity-validator",
src/film_pipeline/validation/impl/scene_continuity.py:208:    Matches the ``scene-continuity-validator`` contract.
src/film_pipeline/validation/impl/scene_continuity.py:213:            validator_id="scene-continuity-validator",
src/film_pipeline/validation/validators/__init__.py:127:        validator_id="scene-continuity-validator",
src/film_pipeline/validation/validators/__init__.py:147:        validator_id="full-movie-flow-validator",

$ .venv/bin/python -c "from film_pipeline.graph.nodes._context import _AGENT_PROFILE_MAP as M; from film_pipeline.validation.validators import MVP_VALIDATORS; v={e.validator_id:e.model_profile for e in MVP_VALIDATORS}; print({k:(M[k],v[k]) for k in set(M)&set(v)})"
{'full-movie-flow-validator': ('strict_validator', 'multimodal_reviewer'), 'scene-continuity-validator': ('strict_validator', 'multimodal_reviewer')}
```
The second command prints the claimed dictionary **exactly**. "2 of 2 rows disagree" is
correct.

**Drift-proof attack.** Both stated sites were mutated:
```
$ sed -i '' 's/    "scene-continuity-validator": "strict_validator",/    "scene-continuity-validator": "text_validator",  # MUTATION/' src/film_pipeline/graph/nodes/_context.py
$ sed -i '' 's/    "full-movie-flow-validator": "strict_validator",/    "full-movie-flow-validator": "text_validator",  # MUTATION/' .../_context.py
$ PYTHONPATH=/tmp/v18m/src .venv/bin/python -m pytest tests/unit \
    -o addopts="-n auto -q --import-mode=importlib --strict-markers"
→ 1866 passed, 3 skipped
```
Silent. The block's own count is therefore too generous: the only pinning test,
`tests/unit/graph/test_agent_profile_routing.py:11-40`, asserts `clip-validator` and
`structure-extractor-agent` are `strict_validator` and that every `MVP_AGENTS` id has a
key — it does not assert either validator row, and no test asserts the roster's
`model_profile` for these ids either. With one-sided edits on *both* sides silent, the
agreement is unpinned: drift is **5**, not 4.

**Severity verdict.** **High, corrected (impact 3 × drift 5 = 15; was 12).** Band
unchanged. Impact 3 is defensible as written (the map row is the current lie; populating
the registry per F-AGENT-08 would flip the validators' profile with nothing failing), and
impact 2 would still score 10 (High).

**Class / prior art / double-count.** Class `O1 + O3` is right. Prior art
`documentation/reviews/arch-lens-flexibility.md:16` is cited correctly — that row does
name "three parallel per-agent tables (contract list, class dict, profile map)".
**Partial double-count:** the *concern line* "Which model profile a validator actually
runs with" is already the stated concern of `F-AGENT-08` ("validator contracts live in
three places … thresholds, scopes, and model profiles"), whose existing divergence is the
same shape (impl entry vs roster row) for the same two tables; and the two rows are
already cited as orphan rows by `F-AGENT-10` (`_context.py:35-51`, 10 orphan profile
keys). F-AGENT-12's genuinely new contribution is the **third** authority
(`_AGENT_PROFILE_MAP`) and the concrete value divergence on it. It should be presented as
an extension that cross-references F-AGENT-08 and F-AGENT-10 and shares their guard
(`impl.entry == registry_row`), not as an independent finding.

---

## F-PROV-08 — Provider endpoints have no owner (Gemini base URL declared three times)

**Anchors.** All source anchors resolve exactly; the prior-art anchor does not.

| anchor | actual line in `/tmp/v18` |
|---|---|
| `providers/adapters/imagen4_gemini.py:21` | `GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models"` |
| `generation/gemini_client.py:13` | `GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"` |
| `agents/model_adapter.py:296` | `            "https://generativelanguage.googleapis.com/v1beta/models/"` |
| `providers/adapters/seedance_openrouter.py:27` | `OPENROUTER_API = "https://openrouter.ai/api/v1"` |
| `agents/model_adapter.py:36` | `from film_pipeline.providers.adapters.seedance_openrouter import OPENROUTER_API` (used at `:141`) |
| extraction sketch: `_gemini_url` at `model_adapter.py:291` | `def _gemini_url(self, model: str) -> str:` is at `:291`; the literal is `:296` | exact |
| prior art: `audit/14-module-boundaries-and-import-law.md:96` records the adjacent `config → providers` private-symbol import | **line 96 is** `not in A1's list, but \`AGENTS.md:9\` makes it authoritative, so it needs an explicit` — a coverage-closure paragraph. The claim is recorded at `audit/14:307`/`:559` (F-BOUNDARY-05), not `:96`. | **anchor defect** |

**Reproduce (verbatim).**
```
$ grep -rn "generativelanguage\|GEMINI_API" src/ --include=*.py
src/film_pipeline/providers/adapters/imagen4_gemini.py:21:GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models"
src/film_pipeline/providers/adapters/imagen4_gemini.py:57:            f"{GEMINI_API}/{model}:predict",
src/film_pipeline/agents/model_adapter.py:296:            "https://generativelanguage.googleapis.com/v1beta/models/"
src/film_pipeline/generation/gemini_client.py:13:GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
src/film_pipeline/generation/gemini_client.py:30:    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={key}"

$ grep -rn "OPENROUTER_API\b" src/ --include=*.py
src/film_pipeline/providers/adapters/seedance_openrouter.py:27:OPENROUTER_API = "https://openrouter.ai/api/v1"
src/film_pipeline/providers/adapters/seedance_openrouter.py:66:        url = f"{OPENROUTER_API}{path}"
src/film_pipeline/agents/model_adapter.py:36:from film_pipeline.providers.adapters.seedance_openrouter import OPENROUTER_API
src/film_pipeline/agents/model_adapter.py:141:            f"{OPENROUTER_API}/chat/completions",

$ grep -rn "generativelanguage\|GEMINI_API\|OPENROUTER_API\b" tests/ --include=*.py
(no output; exit 1)
```
All three statements hold: three Gemini declaration sites in three sub-packages, one of
them an inline literal with a trailing slash; `OPENROUTER_API` declared once and imported
across the `agents → providers.adapters` boundary; no test references any endpoint.

**Drift-proof attack.** The proof is "no test fails when an endpoint is changed,
duplicated a fourth time, or pointed at a host that no other copy uses". The third
reproduce command (`exit 1`, empty) demonstrates the missing pin mechanically, so the
mutation is trivially silent — no further mutation was needed. The "trailing slash"
asymmetry is real but is *not* itself a behavioural divergence today (both forms build
the same URL), so the §1.6.3 proof rests on the unpinned-triplication limb, not on an
existing behavioural divergence. That is acceptable under §1.6.3(b) but should be phrased
as such.

**Severity verdict.** **High (impact 3 × drift 5 = 15) — unchanged as a band.** Drift 5 is
demonstrated. Impact 3 ("recoverable wrong internal behavior") is defensible, though the
prior art rated the OpenRouter edge "medium" / B-F3 "Low-Med"; if a reviewer scored
impact 2 the result is 10, still High. I keep 15.

**Class / prior art / double-count.** Class `O1 + O7` is correct. **Prior art is wrong:**
the block claims the `agents → providers.adapters` public-constant import is not recorded
and is "New". It is recorded, with the same target design:
```
$ sed -n '104,106p' documentation/architecture-review.md
| B-F2 | `config → providers`: ... importing the **private** `_env_var_for` | Medium | S |
| B-F3 | `agents/model_adapter.py:31` imports `OPENROUTER_API` from concrete adapter `seedance_openrouter.py` — generic chat transport coupled to one media adapter's constant | Low-Med | S |
$ sed -n '70,71p' documentation/reviews/arch-lens-boundaries.md
- `agents/model_adapter.py:31`: `from film_pipeline.providers.adapters.seedance_openrouter import OPENROUTER_API` (used at line 98: ...) — a generic chat adapter importing a constant owned by one specific media-provider adapter.
```
`documentation/reviews/arch-review-critic.md:113` also cites "(e) `OPENROUTER_API`
relocation [B-F3]". The honest A7 statement is: *`B-F3`/arch-lens-boundaries already
record the agents→providers OpenRouter leak; the genuinely new content is the Gemini
triplication across three layers, which no prior doc mentions* (`grep -rl
"generativelanguage\|GEMINI_API" documentation/ docs/clean-code-refactor/` → empty).
Double-count: none among the eight.

---

## F-GEN-14 — Provider job status re-derived as raw literals

**Anchors.** All resolve exactly.

| anchor | actual line in `/tmp/v18` |
|---|---|
| `providers/base.py:15-22` | `class ProviderJobStatus(StrEnum):` … `COMPLETED = "completed"` / `FAILED = "failed"` / `CANCELLED = "cancelled"` |
| `generation/executor.py:245,247` | `if job.status == "completed":` / `elif job.status == "failed":` |
| `mcp/tools/generation/dispatch.py:188` | `job_status = ProviderJobStatus(provider_status)` |
| `:196` | `}.get(job_status, GenerationStatus.RUNNING)` |
| `providers/mock_provider.py:188` / `seedance_openrouter.py:173` | `job.status = ProviderJobStatus.CANCELLED` |
| `dispatch.py:275,298` | `status=GenerationStatus.CANCELLED,` |

**Reproduce (verbatim).**
```
$ grep -rn 'job\.status == "' src/film_pipeline
src/film_pipeline/generation/executor.py:245:        if job.status == "completed":
src/film_pipeline/generation/executor.py:247:        elif job.status == "failed":

$ grep -rn "ProviderJobStatus" src/film_pipeline
src/film_pipeline/providers/mock_provider.py:15:    ProviderJobStatus,
src/film_pipeline/providers/mock_provider.py:108:            job.status = ProviderJobStatus.FAILED
src/film_pipeline/providers/mock_provider.py:113:            job.status = ProviderJobStatus.COMPLETED
src/film_pipeline/providers/mock_provider.py:115:            job.status = ProviderJobStatus.PROCESSING
src/film_pipeline/providers/mock_provider.py:188:        job.status = ProviderJobStatus.CANCELLED
src/film_pipeline/providers/adapters/imagen4_gemini.py:16:    ProviderJobStatus,
src/film_pipeline/providers/adapters/imagen4_gemini.py:115:            status=ProviderJobStatus.SUBMITTED,
src/film_pipeline/providers/adapters/imagen4_gemini.py:124:        job.status = ProviderJobStatus.COMPLETED
src/film_pipeline/providers/adapters/veo_fast.py:16:    ProviderJobStatus,
src/film_pipeline/providers/adapters/veo_fast.py:49:            status=ProviderJobStatus.SUBMITTED,
src/film_pipeline/providers/adapters/veo_fast.py:53:        job.status = ProviderJobStatus.COMPLETED
src/film_pipeline/providers/adapters/seedance_openrouter.py:22:    ProviderJobStatus,
src/film_pipeline/providers/adapters/seedance_openrouter.py:119:            status=ProviderJobStatus.SUBMITTED,
src/film_pipeline/providers/adapters/seedance_openrouter.py:128:        job.status = ProviderJobStatus.COMPLETED
src/film_pipeline/providers/adapters/seedance_openrouter.py:173:            job.status = ProviderJobStatus.CANCELLED
src/film_pipeline/providers/mock_image_provider.py:12:    ProviderJobStatus,
src/film_pipeline/providers/mock_image_provider.py:69:            status=ProviderJobStatus.COMPLETED,
src/film_pipeline/providers/mock_image_provider.py:73:        job.status = ProviderJobStatus.COMPLETED
src/film_pipeline/providers/base.py:15:class ProviderJobStatus(StrEnum):
src/film_pipeline/providers/base.py:33:    status: ProviderJobStatus = ProviderJobStatus.SUBMITTED
src/film_pipeline/mcp/tools/generation/dispatch.py:184:    from film_pipeline.providers.base import ProviderJobStatus
src/film_pipeline/mcp/tools/generation/dispatch.py:188:        job_status = ProviderJobStatus(provider_status)
src/film_pipeline/mcp/tools/generation/dispatch.py:192:        ProviderJobStatus.COMPLETED: GenerationStatus.COMPLETED,
src/film_pipeline/mcp/tools/generation/dispatch.py:193:        ProviderJobStatus.FAILED: GenerationStatus.FAILED,
src/film_pipeline/mcp/tools/generation/dispatch.py:194:        ProviderJobStatus.SUBMITTED: GenerationStatus.SUBMITTED,
src/film_pipeline/mcp/tools/generation/dispatch.py:195:        ProviderJobStatus.PROCESSING: GenerationStatus.RUNNING,
src/film_pipeline/mcp/tools/generation/dispatch.py:212:    from film_pipeline.providers.base import ProviderJob, ProviderJobStatus
src/film_pipeline/mcp/tools/generation/dispatch.py:230:        status=ProviderJobStatus.SUBMITTED,
src/film_pipeline/mcp/tools/generation/dispatch.py:284:    from film_pipeline.providers.base import ProviderJob, ProviderJobStatus
src/film_pipeline/mcp/tools/generation/dispatch.py:291:        status=ProviderJobStatus.SUBMITTED,
src/film_pipeline/generation/executor.py:32:    ProviderJobStatus,
src/film_pipeline/generation/executor.py:235:            status=ProviderJobStatus.SUBMITTED,

$ grep -rn "CANCELLED" src/film_pipeline
src/film_pipeline/providers/mock_provider.py:188:        job.status = ProviderJobStatus.CANCELLED
src/film_pipeline/providers/adapters/seedance_openrouter.py:173:            job.status = ProviderJobStatus.CANCELLED
src/film_pipeline/providers/base.py:22:    CANCELLED = "cancelled"
src/film_pipeline/mcp/tools/generation/dispatch.py:275:            status=GenerationStatus.CANCELLED,
src/film_pipeline/mcp/tools/generation/dispatch.py:298:            status=GenerationStatus.CANCELLED,
src/film_pipeline/mcp/tools/generation/status.py:50:        GenerationStatus.CANCELLED,
src/film_pipeline/schemas/_base.py:176:    CANCELLED = "cancelled"
Binary file src/film_pipeline/schemas/__pycache__/_base.cpython-312.pyc matches
src/film_pipeline/generation/ledger.py:129:            GenerationStatus.CANCELLED,
src/film_pipeline/generation/executor.py:356:            if row.status in {GenerationStatus.CANCELLED}:
```
The `CANCELLED` divergence is exactly as described: adapters produce it, the executor's
chain at `:245,247` has no branch (a cancelled job falls to the `else` at `:255` →
`result.running += 1` and a poll-count bump), and the MCP mapping has no entry for it.

**Drift-proof attack.** Two separate mutations were run because the block's proof has two
limbs and only one of them is silent.

*(a) The named enum-rename mutation is NOT silent.*
```
$ sed -i '' 's/    COMPLETED = "completed"/    COMPLETED = "done"/' src/film_pipeline/providers/base.py
$ PYTHONPATH=/tmp/v18m/src .venv/bin/python -m pytest tests/unit/providers/test_provider_job_status.py -o addopts="-q --import-mode=importlib --strict-markers"
FAILED tests/unit/providers/test_provider_job_status.py::test_provider_job_status_covers_produced_vocabulary
1 failed, 3 passed

$ PYTHONPATH=/tmp/v18m/src .venv/bin/python -m pytest tests/unit/generation/test_executor.py -o addopts="-q --import-mode=importlib --strict-markers"
FAILED tests/unit/generation/test_executor.py::TestGenerationExecutor::test_poll_once_completes
E   assert 0 == 2   # GenerationStepResult(processed=2, completed=0, failed=0, running=2)
1 failed, 19 passed
```
So the block's drift-2 rationale is honest (the naming assumption in §1.6.3(b), "the
failure is silent", is not met by this limb) — the proof survives only on the
`CANCELLED` existing-divergence limb. The block should say so explicitly.

*(b) The consumer mapping is completely unpinned.* Inverting the `PROCESSING` mapping —
i.e. exactly the "partial edit to one copy that the author forgets" the finding warns
about — fails nothing:
```
$ sed -i '' 's/        ProviderJobStatus.PROCESSING: GenerationStatus.RUNNING,/        ProviderJobStatus.PROCESSING: GenerationStatus.COMPLETED,  # MUTATION/' src/film_pipeline/mcp/tools/generation/dispatch.py
$ PYTHONPATH=/tmp/v18m/src .venv/bin/python -m pytest tests/unit/mcp/tools/test_generation.py tests/unit/generation -o addopts="-q --import-mode=importlib --strict-markers"
154 passed in 3.17s
```
No test pins the mapping dict at `dispatch.py:191-196`, and no test pins the
`CANCELLED → running` behaviour either (`grep -rn '"cancelled"\|CANCELLED' tests/` shows
only the provider-side assertions and the *tool-level* cancel results, never the mapping).

**Severity verdict.** **STRENGTHENED: Medium (3×2=6) → High (3×5=15).** The concern is the
agreement between the executor's literals and the MCP mapping. Since the mapping side is
completely unpinned and already divergent for `CANCELLED`, §1.5 gives drift 5 ("no test
can fail when one site changes"), not 2. The block's drift-2 reflects only the enum-value
limb, which is a *different* concern (the enum's own vocabulary, pinned by
`test_provider_job_status.py:28-29`) and does not pin the two-copy agreement. Impact 3
(wrong internal state, recoverable; cancelled jobs polled as running) holds.

**Class / prior art / double-count.** Class `O1 + O8` is correct. **Prior art is wrong:**
the block says "new — the verifier's missed-in-scope item 1", but
`documentation/reviews/arch-lens-flexibility.md:124` already records this exact pair
(line numbers then 234/238) and rates it "LOW — cosmetic; a serialization contract test
already pins the vocab":
```
$ sed -n '124p' documentation/reviews/arch-lens-flexibility.md
| 7 | Provider status comparisons | enum vs string-literal style mix |
`generation/executor.py:234,238` compare `job.status == "completed"` (works via StrEnum
equality) | LOW | cosmetic; a serialization contract test already pins the vocab
(`tests/unit/providers/test_provider_job_status.py:22-29`). |
```
The honest A7 statement is: *prior art records the literal-vs-enum style mix and calls it
cosmetic; new here is the second consumer (`dispatch.py:188-196`), the already-divergent
`CANCELLED` case, and the refutation of the "cosmetic" rating.* Double-count: none of the
other seven; `F-GEN-09` (raw status strings in `_generation_ops.py`) is cited in the blast
radius and is a distinct owner.

---

## F-GEN-15 — `unassigned` on disk vs `scene_id=""` in the sidecar/entry

**Anchors.** All resolve exactly.

| anchor | actual line in `/tmp/v18` |
|---|---|
| `executor_delivery.py:44-46` | `def _scene_id_of(...)` / docstring / `return str(shot_row.get("scene_id", "") or "unassigned")` |
| `project_storage.py:209-210` | the expression is on **`:209`** (`... / _layout.MEDIA_DIRNAME / "scenes" / scene_id / shot_id`); `:210` is `)` | range padded by one but the quote is verbatim at `:209` |
| `:206-212` (drift proof) | `def media_dir(...)` … `return directory` | exact |
| `executor_delivery.py:97` | `"scene_id": "" if scene_id == "unassigned" else scene_id,` | exact |
| `:111` | `scene_id="" if scene_id == "unassigned" else scene_id,` | exact |
| `artifacts/manifest.py:56-57` | `def list_by_scene(...)` / `return [e for e in self.entries if e.scene_id == scene_id]` | exact |

**Reproduce (verbatim).**
```
$ grep -rn "unassigned" src/film_pipeline tests
src/film_pipeline/generation/executor_delivery.py:45:    """Scene a shot belongs to, or the ``unassigned`` placeholder."""
src/film_pipeline/generation/executor_delivery.py:46:    return str(shot_row.get("scene_id", "") or "unassigned")
src/film_pipeline/generation/executor_delivery.py:97:        "scene_id": "" if scene_id == "unassigned" else scene_id,
src/film_pipeline/generation/executor_delivery.py:111:                scene_id="" if scene_id == "unassigned" else scene_id,

$ grep -rn "unassigned" tests/
(no output; exit 1)

$ grep -rn "scene_id" src/film_pipeline/generation/executor_delivery.py
(10 lines: 34,35,39,44,46,49,55,84,97,111)
```
`grep -rn "unassigned" tests/` returns no matches, exactly as claimed.

**Drift-proof attack.** The named mutation was applied to the pristine copy:
```
$ sed -i '' 's/or "unassigned"/or "none"/; s/== "unassigned"/== "none"/g' src/film_pipeline/generation/executor_delivery.py
$ PYTHONPATH=/tmp/v18m/src .venv/bin/python -m pytest tests/unit \
    -o addopts="-n auto -q --import-mode=importlib --strict-markers"
→ 1866 passed, 3 skipped
```
Silent, as claimed. The scene-ful path *is* pinned
(`tests/unit/artifacts/test_state_persistence.py:351-369` drives `deliver_completed_job`
with `SC_001` and asserts the `media/scenes/SC_001/...` location), which is why drift 3
is defensible rather than 5.

One **factual defect in the drift proof's illustration**: the block says "rebuilding the
path from the entry yields `media/scenes//<shot_id>` (empty segment)". `pathlib` *elides*
empty components, so the rebuilt path is `media/scenes/<shot_id>`:
```
$ .venv/bin/python -c "from pathlib import Path; print(Path('/root/proj')/'media'/'scenes'/''/'shot_0001')"
/root/proj/media/scenes/shot_0001
```
The conclusion (it does not resolve to the directory that exists) still holds; the stated
form does not.

**Severity verdict.** **High (impact 3 × drift 3 = 9) — unchanged.** Impact 3 is right
(scene-less media exists on disk but is unreachable via the manifest scene index); drift 3
is right because the scene-ful delivery path is pinned while the scene-less branch is not.

**Class / prior art / double-count.** Class `O3 + O1` is correct. Prior art `new` is
**verified**: `grep -rl "unassigned" documentation/ docs/clean-code-refactor/` returns
nothing. Double-count: none among the eight — `F-GEN-12` (denylist/sidecar grammar) and
`F-GEN-07` (dead `media_scene_dir` helper) are different seams; the block correctly points
at F-GEN-12 for the take-selection interaction.

---

## F-GEN-16 — Compositor writes PNG bytes straight to disk

**Anchors.** The two code anchors resolve; **all five `composites.py` anchors do not
describe the lines they point at**, and the identifier named in the block does not exist.

| anchor | actual line in `/tmp/v18` | verdict |
|---|---|---|
| `tests/unit/artifacts/test_storage_boundary.py:72-82` | `def test_only_storage_imports_path_helpers` … `)`, with `"""Project path helpers stay internal to the storage package."""` at `:73` and `"These modules build project paths themselves: … Ask ProjectStorage for typed values instead."` at `:80-81` | exact |
| `_outside_storage()` "(`:45-50`)" | `def _outside_storage()` at `:45`, body to `:50` | exact |
| "three layout constants (`:84-95`)" | `test_no_layout_constants_leak_outside_storage` at `:84`; the constants at `:89-92` | acceptable |
| `generation/compositor/extras.py:181-185` | `def _save_sheet(...)` / docstring / `output_path.parent.mkdir(parents=True, exist_ok=True)` / `canvas.save(output_path, "PNG")` / `return output_path` | exact |
| `generation/compositor/environment.py:132-133` | `output_path.parent.mkdir(parents=True, exist_ok=True)` / `canvas.save(output_path, "PNG")` | exact |
| `mcp/tools/reference_generation/composites.py:98,116,168,186,209` — described as "the callers that **build `output_path` inline** and hand it down" | all five are the `from film_pipeline.generation.compositor import build_*` **import lines**: `:98` import, `:101` `sheet_path = project_root / "references" / "characters" / subject_id / "identity-sheet.png"`; `:116` import, `:119-120` environment board path; `:168` import, `:172-174` expression sheet path; `:186` import, `:192` scale sheet path; `:209` import, `:212` style board path. **`grep -n "output_path" composites.py` exits 1** — the variable is `sheet_path`. | **5 anchor defects + wrong identifier** |

```
$ grep -n "output_path" src/film_pipeline/mcp/tools/reference_generation/composites.py
(no output; exit 1)
$ grep -n "import build_" src/film_pipeline/mcp/tools/reference_generation/composites.py
98:    from film_pipeline.generation.compositor import build_character_identity_sheet
116:    from film_pipeline.generation.compositor import build_environment_board
168:    from film_pipeline.generation.compositor import build_expression_sheet
186:    from film_pipeline.generation.compositor import build_scale_sheet
209:    from film_pipeline.generation.compositor import build_style_board
$ grep -n 'png"' src/film_pipeline/mcp/tools/reference_generation/composites.py
101:        sheet_path = project_root / "references" / "characters" / subject_id / "identity-sheet.png"
120:            project_root / "references" / "environments" / subject_id / "environment-board.png"
173:                project_root / "references" / "characters" / subject_id / "expression-sheet.png"
192:        sheet_path = project_root / "references" / "scale" / "scale-sheet.png"
212:        sheet_path = project_root / "references" / "style" / "style-board.png"
```
For comparison, `extras.py`/`environment.py` really do use the parameter name
`output_path`, so the block appears to have carried that name over to `composites.py`
without reading it. This is a straightforward A2 defect.

**Reproduce (verbatim).**
```
$ grep -rn "canvas.save\|\.parent.mkdir" src/film_pipeline
src/film_pipeline/artifacts/store.py:102:        lock_path.parent.mkdir(parents=True, exist_ok=True)
src/film_pipeline/artifacts/_layout.py:148:    path.parent.mkdir(parents=True, exist_ok=True)
src/film_pipeline/artifacts/serialization.py:87:    path.parent.mkdir(parents=True, exist_ok=True)
src/film_pipeline/testing/in_memory_git.py:124:            target.parent.mkdir(parents=True, exist_ok=True)
src/film_pipeline/generation/compositor/extras.py:183:    output_path.parent.mkdir(parents=True, exist_ok=True)
src/film_pipeline/generation/compositor/extras.py:184:    canvas.save(output_path, "PNG")
src/film_pipeline/generation/compositor/environment.py:132:    output_path.parent.mkdir(parents=True, exist_ok=True)
src/film_pipeline/generation/compositor/environment.py:133:    canvas.save(output_path, "PNG")

$ grep -rn "_outside_storage\|artifacts.paths" tests/unit/artifacts/test_storage_boundary.py
45:def _outside_storage() -> list[Path]:
60:            for path in _outside_storage()
76:            for path in _outside_storage()
77:            if any(module.endswith("artifacts.paths") for module in _imported_modules(path))
84:    def test_no_layout_constants_leak_outside_storage(self) -> None:
87:        for path in _outside_storage():
```
The reproduce output supports the finding: two live compositor write sites bypass
`ProjectStorage`, and the boundary test only inspects imported modules/constants.

**Drift-proof attack.** The block's stated mutation ("change the storage core's
*reference-layout convention*; the compositor's callers keep passing the old paths") is
**ill-defined**: `artifacts/` owns no reference-layout convention at all —
`grep -rn "references" src/film_pipeline/artifacts/*.py` returns only a docstring in
`manifest.py:1`, and the reference paths are assembled in
`mcp/tools/reference_generation/composites.py` itself. There is no second storage-side
site for the compositor's paths to drift from, so that mutation cannot be performed as
written. The proof survives on the other limb: the declared invariant
(`test_storage_boundary.py`'s `TestProjectStorageIsTheOnlyWriter`, also stated in
`documentation/artifact-store.md:30,52-55,62`) is violated by two live writers.
I confirmed the silence of the write surface directly:
```
$ sed -i '' 's/"identity-sheet.png"/"identity-sheet-MUT.png"/; s/"environment-board.png"/"environment-board-MUT.png"/; s/"expression-sheet.png"/"expression-sheet-MUT.png"/; s/"scale-sheet.png"/"scale-sheet-MUT.png"/; s/"style-board.png"/"style-board-MUT.png"/' src/film_pipeline/mcp/tools/reference_generation/composites.py
$ PYTHONPATH=/tmp/v18m/src .venv/bin/python -m pytest tests/unit/mcp/tools/test_reference_generation.py tests/unit/generation/test_compositor.py tests/unit/generation/test_compositor_templates.py tests/unit/generation/test_sheet_manifest.py -o addopts="-q --import-mode=importlib --strict-markers"
48 passed in 2.38s
```
Renaming **all five** composited sheet outputs fails nothing; no test exercises
`composites.py` at all, so the whole write surface it owns is unpinned (`verify-06.md`
reached the same conclusion for the reference-path helpers: "no composites tests exist").

**Severity verdict.** **Medium (impact 2 × drift 3 = 6) — unchanged.** Impact 2 is right
(a regenerable render artifact; the atomicity difference is a real but recoverable
divergence). Drift 3 is defensible: the compositor's own functions are tested (with
caller-supplied tmp paths) and `_save_sheet`'s existence would change if its signature
changed, but the path construction and the storage invariant are unpinned.

**Class / prior art / double-count.** Class as written — **"O7 (leaked internals) +
unenforced invariant"** — is invalid under §1.4/§1.7: "unenforced invariant" is not one
of O1–O8, and O7 ("a module reaches into another's private state") does not fit — the
compositor does not touch `artifacts/` internals, it simply writes its own files. The
correct class is **O3 (split state authority: media bytes under a project root have two
writers and no single one)**. Prior art: the block says "new — the verifier's
missed-in-scope item 3", but the invariant it is measured against is documented prior art
and should be cited: `documentation/artifact-store.md:30` ("ProjectStorage: THE gateway
every consumer uses"), `:52-55` ("They never assemble `media/scenes/...` themselves and
never import a relpath constant"), `:62` ("every byte goes through `ProjectStorage`") and
`:64-66` (naming `test_storage_boundary.py` as the enforcement). Double-count: none among
the eight; the blast-radius citation of `F-GEN-07` (the dead `media_scene_dir` helper) is
accurate and distinct.

---

## What the authors should fix

Ordered by consequence. Items 1–2 change a band or an A7 claim; the rest are A2/A4
corrections.

1. **F-GEN-14 — severity must rise to High (3×5=15).** The consumer mapping
   (`dispatch.py:191-196`) and the `CANCELLED` treatment are unpinned (mutation of the
   mapping: 154 passed). Rewrite drift as 5 and move the block out of Medium. Also
   restate the drift proof: the named enum-rename mutation is **caught**
   (`test_provider_job_status.py` FAILED, `test_executor.py::test_poll_once_completes`
   FAILED), so the §1.6.3 proof must rest solely on the existing `CANCELLED` divergence.
   Add prior art: `documentation/reviews/arch-lens-flexibility.md:124` (row 7, rated LOW).

2. **F-PROV-08 — prior-art line is false and one anchor is wrong.** Cite
   `documentation/architecture-review.md:106` (B-F3) and
   `documentation/reviews/arch-lens-boundaries.md:70-86` (which already record the
   `agents → providers.adapters` `OPENROUTER_API` leak and the same target design), and
   scope "new" to the Gemini triplication. Replace the `audit/14:96` prior-art anchor with
   `audit/14:307` (or `:559`, F-BOUNDARY-05).

3. **F-OST-17 — prior-art line is false.** Cite
   `documentation/reviews/arch-lens-dataflow.md` F-1 (`:28`) and F-6 (`:156,160`), which
   already record the dead review-cycle channel and the wire-or-delete recommendation, and
   state the genuinely new content (the live MCP reader at `mcp/tools/state.py:40,55`).

4. **F-GEN-16 — fix all five `composites.py` anchors and the class.** The anchors must
   point at the path-building lines (`:101`, `:119-120`, `:172-174`, `:192`, `:212`, or
   the surrounding function definitions at `:96/:110/:166/:180/:203`), not the
   `import build_*` lines at `:98/:116/:168/:186/:209`; the identifier is `sheet_path`,
   not `output_path`. Reclassify to `O3`, and cite `documentation/artifact-store.md`
   as the prior art for the invariant. Replace the ill-defined "storage reference-layout
   convention" mutation with the verified one (renaming all five sheet outputs → 48
   passed; no `composites.py` test exists).

5. **F-PHASE-11 — "the only reader" is false.** Add `kb/retrieval.py:49` (same predicate,
   second consumer) to the de-facto owners, add `O2` to the class, and note that the same
   typo silently shrinks `KBRetrieval.search(phase=...)`. Add a cross-reference to
   `F-PHASE-02`, which already lists the KB registry in its partial-index inventory.

6. **F-AGENT-12 — drift is 5, not 4 (score 15), and the block overlaps two verified
   findings.** The mutation of both map rows fails nothing, and no test asserts the
   roster's `model_profile` for either id, so the agreement is unpinned. Cross-reference
   `F-AGENT-08` (whose concern line already includes validator `model_profile` and whose
   divergence is the same shape) and `F-AGENT-10` (which already cites these two rows as
   orphan profile keys); share F-AGENT-08's `impl.entry == registry_row` guard instead of
   proposing a parallel one.

7. **F-GEN-15 — correct the rebuilt-path illustration.** `pathlib` elides the empty
   component: rebuilding from `scene_id=""` yields `media/scenes/<shot_id>`, not
   `media/scenes//<shot_id>`. The conclusion is unchanged.

8. **F-OST-17 — add the reader to the owner list for completeness.**
   `get_active_review_cycle`'s body (`orchestrator_state.py:218-225`) is the actual live
   reader behind `mcp/tools/state.py:40`; the block cites the MCP call but not the owner
   function it calls.

9. **F-AGENT-11 — add the expected output to `Reproduce`.** It currently prints four
   `src/` lines and no annotation; add `# no test hits` (or a second command) so the
   "module is not referenced by any test" claim is reproducible from the block alone.

10. **All eight — no finding needs rejecting or moving to §1.6.6.** Every claim is
    mechanically reproducible at `fb85baa`; the defects are anchors, counts, prior-art
    citations, class labels and severity arithmetic, not unverifiable substance.
