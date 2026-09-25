# Adversarial coverage review — attacking bar A1

**Role:** adversarial coverage reviewer. This file is an attack on the deliverable
`docs/modular-architecture/`, not part of the audited set. It tries to falsify the
claim that the 14 audits found **every** instance of distributed ownership.

**Revision measured.** Source at `fb85baa` (`modular-app`, `git rev-parse HEAD`).
Audit text at the revision whose hashes are in §7; `docs/` is gitignored and was
being edited by other agents *during* this review (ownership map mtime 15:21,
`reviews/` 15:27–15:36), so every hole below was re-verified against the audit files
at the moment of writing and every hole's symbol is confirmed absent from the
current text. `git status --porcelain` is empty (docs is ignored).

---

## 1. Method

### 1.1 What I inventoried, and how

I did not trust grep. I wrote two AST passes over **all 281 `.py` files** under
`src/film_pipeline/` (`/tmp/inv.py`, `/tmp/inv2.py`; logic summarised in §7.2). The
passes extract, at module, class and function scope:

| Kind | What it captures | Rows |
|---|---|---|
| `ENUM` | every `Enum`/`StrEnum` class and its members | 23 |
| `LITERAL` | every `Literal[...]` field/param/return annotation | 7 fields (11 subscripts) |
| `VOCAB` / `VOCAB2` | module/class-level list/tuple/set of ≥2 string literals; tuple-of-tuples keyed by a string | 33 + 7 |
| `DICTREG` / `LISTDICT` | dict literal with ≥2 string keys (registries/tables); list-of-dicts registries | 76 + 1 |
| `REGISTRY_CALL` | registry object built by a constructor call | 19 |
| `PATHLIT` | string constants that are paths, roots, filenames, URL bases or `dir`/`root` named | 27 |
| `NUMCONST` | module-class-function-level numeric constants | 109 |
| `STATEKEY` | every `state[k]`, `state.get/pop/setdefault(k)` read/write/update | 424 uses / **79 distinct keys** |
| `CROSSIMPORT` | every `film_pipeline.<pkg>` import across package boundaries | 442 sites / **53 distinct package→package edges** |

Raw rows: **1,168**. After dropping counters, Pydantic defaults and other
non-policy numerics, the curated normative inventory is **671 rows** (23 enums,
7 literals, 117 vocab/registries, 27 path literals, 73 numeric policy constants,
424 state-key uses = 79 distinct keys).

Commands:

```bash
cd ${REPO_ROOT}
UV_CACHE_DIR="$PWD/.uv-cache" uv run python /tmp/inv2.py    # writes /tmp/inventory2.json
```

### 1.2 How I tested coverage

1. **Textual coverage.** For every curated item I searched its symbol name, its
   defining file, and its first literal values across all 14 audit files plus
   `01`–`05` and `reviews/` (`/tmp/cover.py`, `/tmp/tally.py`). 576/671 are named
   somewhere; **95 have zero textual mention**.
2. **Manual probes of the requested hole shapes** — package→audit map, clean-concern
   counterexamples, "acknowledged in prose but no finding id", numeric policy,
   `Literal`→plain-`str`, declared-vs-used state keys, non-Python surface — and
   hand-reading of every symbol reported below.
3. **Re-running the audits' own §1 reproduce commands** to test whether coverage
   sections are decorative.

### 1.3 Limits of this attack

- Text search proves *mention*, not that the concern was analysed. I hand-read each
  reported hole; the automated "covered" verdict is optimistic and produced two
  false positives (`_REVIEW_CAPABILITIES` and `_PACING_ALIASES` scored covered
  because their values are common English words — see H3/H4).
- This is an ownership-seam review. A defect with one owner (dead code, a stub) is
  reported only when it is a *second authority* for a normative model.

---

## 2. Tally

| Measure | Count |
|---|---|
| Source files AST-parsed | 281 |
| Raw inventory rows | 1,168 |
| Curated normative items | 671 |
| Named somewhere in the deliverable | 576 |
| Zero textual mention | **95** |
| — of which **verified holes with anchor + reproduce** | **18 rows / 9 concerns** |
| — of which benign, single-owner, fixture or logging constants (read, no seam) | 30 |
| — of which single-owner vocabularies in a file the owning audit read in full (no seam found) | 20 |
| — of which state keys of declared channels / artifact payloads, covered under another name | 27 |
| Verified holes the automated text test *falsely* scored covered | 2 concerns |
| Deliverable-integrity defects (counts / missing finding id / missing class) | 3 |
| **Total real gaps reported (H1–H13)** | **13** |
| Hypotheses only (no counterexample produced) | 3 |

---

## 3. The holes

### H1 — The reference-sheet **frame-role vocabulary** is owned by six modules, and the environment role set already diverges (O1 + O4 + O5)

**Anchors**

| Anchor | What it defines |
|---|---|
| `src/film_pipeline/generation/compositor/_layout.py:24` | `_CHAR_TILES` — 13 character frame roles → tile rectangles |
| `src/film_pipeline/generation/compositor/_layout.py:42` | `_CHAR_LABELS` — the same 13 keys → display labels |
| `src/film_pipeline/generation/compositor/environment.py:27` | `_ENV_TILES` — **8** environment roles → rectangles |
| `src/film_pipeline/generation/compositor/environment.py:38` | `_ENV_LABELS` — the same 8 keys |
| `src/film_pipeline/generation/compositor/extras.py:23` | `_EXPRESSION_TILES` — 4 roles |
| `src/film_pipeline/generation/prompt_builder.py:24` | `_CHARACTER_FRAME_ROLE_TEXT` — 13 prompt texts |
| `src/film_pipeline/generation/prompt_builder.py:40` | `_ENVIRONMENT_FRAME_ROLE_TEXT` — **10** prompt texts |
| `src/film_pipeline/mcp/tools/reference_generation/entries.py:29` | `ANCHOR_PRIORITY = {"front-face": 0, "wide-establishing": 0}` |
| `src/film_pipeline/mcp/tools/reference_generation/outcomes.py:55-58` | the same two anchor roles as an inline tuple, deciding drift policy |
| `src/film_pipeline/generation/frame_reviewer.py:59-88` | role-prefix policy: `lighting-`, `alt-angle-`, `detail-`, `expression-`, `front-face`, `color-palette` |
| `src/film_pipeline/graph/nodes/_generation_prompts.py:73` | `"frame_role": str(row.get("camera_profile", ""))` — maps a *different* vocabulary onto this one |
| `src/film_pipeline/generation/executor_prompts.py:99` | the same `camera_profile` → `frame_role` conflation |
| `src/film_pipeline/schemas/reference.py:53` | `frame_role: str` — free text, docstring lists four example values |
| `src/film_pipeline/agents/prompt_templates/defaults/production.py:63` | the LLM template that mints roles, showing only `"front-face"` |

**Why it is a hole.** The set of frame roles is a normative representation: it
decides which tiles a delivered character/environment sheet contains, how each
tile's prompt is built, which frame is the drift anchor, and which frames get paid
spot-check review. Six modules re-spell it and nothing validates agreement. The
divergence is *already executed*: `_ENVIRONMENT_FRAME_ROLE_TEXT` contains
`alt-angle-entrance` and `lighting-overcast-morning`, which `_ENV_TILES` cannot
place — the compositor silently drops them from the board. The source of roles is an
LLM that only ever sees one example (`production.py:63`), so a role the model invents
lands in some tables and not others. O-class: **O1** (duplicated normative model),
**O4** (parallel registries), **O5** (`frame_reviewer` re-derives the role partition
from string prefixes).

**Reproduce**

```bash
cd ${REPO_ROOT}
UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
from film_pipeline.generation.compositor._layout import _CHAR_TILES
from film_pipeline.generation.compositor.environment import _ENV_TILES
from film_pipeline.generation.prompt_builder import _CHARACTER_FRAME_ROLE_TEXT, _ENVIRONMENT_FRAME_ROLE_TEXT
print('char', len(_CHAR_TILES), len(_CHARACTER_FRAME_ROLE_TEXT), set(_CHARACTER_FRAME_ROLE_TEXT)^set(_CHAR_TILES))
print('env ', len(_ENV_TILES), len(_ENVIRONMENT_FRAME_ROLE_TEXT), 'prompt-only', sorted(set(_ENVIRONMENT_FRAME_ROLE_TEXT)-set(_ENV_TILES)))
"
# -> char 13 13 set()
# -> env  8 10 prompt-only ['alt-angle-entrance', 'lighting-overcast-morning']
grep -rn "front-face\|FRAME_ROLE\|_ENV_TILES" docs/modular-architecture/audit/ | wc -l   # -> 0
```

**Which audit should have owned it.** Audit 06 declares `generation/compositor/**`
and `mcp/tools/reference_generation/**` in scope but its coverage row dismisses the
compositor as "grep-swept … no ledger or manifest writes". That is the miss: the
compositor's *normative surface* is its tile/role vocabulary, not its writes. Audit
04 owns the prompt-template anchor (`production.py:63`) and audit 07 owns
`schemas/reference.py:53`.

---

### H2 — Provider polling policy is declared in four keys and only one is read; nothing enforces a wait budget (O5 + O8)

**Anchors**

- `src/film_pipeline/providers/adapters/seedance_openrouter.py:28` —
  `POLLING_CONFIG = {"initial_delay_seconds": 20, "poll_interval_seconds": 30, "max_wait_seconds": 1800, "backoff_multiplier": 1.2}`
- `src/film_pipeline/providers/adapters/seedance_openrouter.py:49` — stored on the instance
- `src/film_pipeline/providers/adapters/seedance_openrouter.py:122` — the **only** read: `time.sleep(self.polling_config["initial_delay_seconds"])`
- `src/film_pipeline/generation/executor.py:207-300` — the poll loop advances `poll_count` with no deadline
- `src/film_pipeline/mcp/tools/generation/dispatch.py:199-250` — the MCP poll loop, likewise unbounded

**Why it is a hole.** `poll_interval_seconds`, `max_wait_seconds` and
`backoff_multiplier` are dead normative policy: a provider timeout budget that no
code applies and no profile declares (`grep -rin "max_wait\|poll_interval\|backoff"
profiles/` → 0). A job whose provider never completes polls forever on the MCP path.
This is exactly the "retry/timeout/number a gate or loop depends on" class: audit 05's
coverage table notes four `poll(` call sites and three retry policies as *prose*, but
no finding owns the numbers. O-class: **O5** (policy re-derived at call sites,
here re-derived as "absent"), **O8** (no contract for the loop's budget).

**Reproduce**

```bash
cd ${REPO_ROOT}
grep -rn "polling_config\|max_wait_seconds\|poll_interval_seconds\|backoff_multiplier" src/ tests/ --include=*.py
# -> 4 hits in seedance_openrouter.py (3 declaration + 1 initial_delay read) + 0 consumers
grep -rin "max_wait\|poll_interval\|backoff" profiles/ ; echo "profiles: $?"
```

**Which audit should have owned it.** Audit 05 (`providers/**`), the only audit that
declares the adapter in scope.

---

### H3 — The pacing vocabulary is a `Literal` in `schemas`, plain `str` constants in `graph`, and two alias tables that already disagree (O1 + O4)

**Anchors**

- `src/film_pipeline/schemas/constraints.py:61` —
  `pacing_style: Literal["slow_cinema", "standard", "dynamic"] | None`
- `src/film_pipeline/graph/scope_contract.py:17-19` — the same three values re-declared as
  plain `str` constants `SLOW_CINEMA`, `STANDARD`, `DYNAMIC`
- `src/film_pipeline/graph/scope_contract.py:33` — `_PACING_ALIASES`, 10 source keys → 3 canonical
- `src/film_pipeline/constraints/_keywords.py:46` — `_PACING_KEYWORDS`, a **second** alias table, also 10 source keys
- `src/film_pipeline/constraints/_keywords.py:60` — `_PACING_PREFERENCE` scan order
- `src/film_pipeline/schemas/execution_brief.py:51-55` — a fourth spelling: `pacing_style: str = Field(default="standard", description="Pacing style: 'slow_cinema', 'standard', 'dynamic'.")`

**Why it is a hole.** This is the classic shape the brief asks for: a schema `Literal`
re-spelled as a plain `str` comparison/constant elsewhere, plus parallel registries.
The two alias tables are the enforcement of "profile/user pacing string → canonical
pacing" and they cover **different, partly disjoint** source vocabularies:

```bash
cd ${REPO_ROOT}
UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
from film_pipeline.graph.scope_contract import normalize_pacing, _PACING_ALIASES
from film_pipeline.constraints._keywords import _PACING_KEYWORDS
print('constraints-only:', sorted(set(_PACING_KEYWORDS)-set(_PACING_ALIASES)))
print('scope-only      :', sorted(set(_PACING_ALIASES)-set(_PACING_KEYWORDS)))
print('slow cinema ->', _PACING_KEYWORDS.get('slow cinema'), 'vs', normalize_pacing('slow cinema','narrative'))
"
# constraints-only: ['moderate', 'slow', 'slow cinema']
# scope-only      : ['character_driven', 'irregular', 'narrative']
# slow cinema -> slow_cinema vs standard          <-- executed divergence
```

`_PACING_KEYWORDS` lacks `irregular`/`character_driven`/`narrative`, which the
shipped profiles actually use (`profiles/film-type.experimental.yaml:4`,
`film-type.narrative.yaml:4`); `_PACING_ALIASES` lacks `slow cinema`/`slow`/`moderate`,
which user prose produces. A partial edit to either table passes CI.

**Which audit should have owned it.** Audit 03 already touched this file and marked
prior-art item A2 ("`pacing` dead / vocabulary mismatch") **FIXED** on the strength of
`scope_contract.py:33-46` — without noticing the second table in `constraints`. Audit
12 read `constraints/_keywords.py` "in full" and claims the package **SINGLE (clean)**
(`01-ownership-map.md` §16), which this contradicts. Owner: audit 03 (config/vocabulary)
with audit 12 as the contradicted clean claim.

---

### H4 — The agent capability-classification sets in `graph` share zero tokens with the roster the agents package declares (O4)

**Anchors**

- `src/film_pipeline/graph/_agent_routing.py:31` — `_REVIEW_CAPABILITIES = {"review", "validation", "qc", "inspecting"}`
- `src/film_pipeline/graph/_agent_routing.py:32` — `_REPAIR_CAPABILITIES = {"repair", "revision", "replan", "correcting"}`
- `src/film_pipeline/agents/mvp/__init__.py:15` — `MVP_AGENTS`, the roster whose `capabilities=[...]` these sets are meant to classify
- `src/film_pipeline/graph/_agent_routing.py:57-59`, `:175-177` — the sets decide which routing branch runs

**Why it is a hole.** The sets and the roster are two registries that must agree about
what a "review capability" is called. They agree on **nothing**:

```bash
cd ${REPO_ROOT}
UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
from film_pipeline.agents.mvp import MVP_AGENTS
from film_pipeline.graph._agent_routing import _REVIEW_CAPABILITIES,_REPAIR_CAPABILITIES
caps=set().union(*[set(a.capabilities) for a in MVP_AGENTS])
print('roster caps', len(caps), '| routing tokens not in any agent:',
      sorted((_REVIEW_CAPABILITIES|_REPAIR_CAPABILITIES)-caps))
"
# roster caps 30 | routing tokens not in any agent:
# ['correcting','inspecting','qc','repair','replan','review','revision','validation']
grep -rn "preferred_capability=" src/ --include=*.py | grep -v _agent_routing.py   # -> 0 production callers
```

All 8 tokens are declared by no agent, and no production caller ever passes
`preferred_capability`, so the entire capability branch is dead policy that a future
caller will trust. The reverse is also true: 30 declared capabilities are never
classified. O-class: **O4** (parallel registries, no agreement check), **O5** (routing
policy by hardcoded membership).

**Which audit should have owned it.** Audit 04 (agent registry/roster agreement). Its
F-AGENT-03/10/12 cover KB-domain, output-artifact and model-profile agreement but not
the capability vocabulary; the string `_REVIEW_CAPABILITIES` appears in **zero** audit
files.

---

### H5 — Two pass bars for "did this reference image pass?" and a sheet-type vocabulary with no owner (O1 + O4)

**Anchors**

- `src/film_pipeline/generation/frame_reviewer.py:43` — `_PASS_THRESHOLD = 28.0` (28/40 = **70%**)
- `src/film_pipeline/generation/frame_reviewer.py:35` — `_PER_FRAME_RUBRIC` hardcodes "Threshold: 28/40 (70%)"
- `src/film_pipeline/generation/sheet_reviewer.py:72` — `def _pass_threshold(max_score): return max_score * 0.8` (**80%**)
- `src/film_pipeline/generation/sheet_reviewer.py:40` — `_RUBRICS` keyed by `character_identity_sheet`, `environment_board`, `scale_sheet`
- `src/film_pipeline/mcp/tools/reference_generation/composites.py:101,120,225` — the sheet-type strings are re-spelled at the call sites
- `src/film_pipeline/agents/impl/visual_dev_agent.py:105` — `asset_type` defaults to `"character_identity_sheet"`, a third spelling site

**Why it is a hole.** "What score passes a reference review" has two authorities with
different numbers (70% vs 80%) and two different rubric grammars, across the
per-frame and per-sheet reviewers, both reachable from the MCP reference-generation
lifecycle (`composites.py:225` → `review_composite_sheet`; `retry_loop.py:116` →
`review_frame`). Audit 03 §4 lists the 70% bar and records its reproduce as
`grep -rn '_PASS_THRESHOLD' src/film_pipeline/generation/` — a command narrowed to one
symbol, so it structurally cannot see `_pass_threshold`. O-class: **O1**, **O4**.

**Reproduce**

```bash
cd ${REPO_ROOT}
grep -rn "_PASS_THRESHOLD\|_pass_threshold" src/film_pipeline/generation/
sed -n '72,73p' src/film_pipeline/generation/sheet_reviewer.py
grep -rn "_RUBRICS\|character_identity_sheet\|environment_board" docs/modular-architecture/audit/ | wc -l   # -> 0
```

**Which audit should have owned it.** Audit 06 (`generation/**`), with audit 03 as the
owner of the numeric-defaults table that cites only half of the pair.

---

### H6 — KB compression/bounding is acknowledged with evidence but has **no finding id and no reproduce command** (bar A6)

**Anchors**

- `docs/modular-architecture/01-ownership-map.md:203` — the row
  `| Compression / bounding | no single owner (3 sites + ad-hoc slices) | **DISTRIBUTED** | (recorded in audit 09) |`
  — a DISTRIBUTED status with **no `F-…` id** in the Findings column.
- `src/film_pipeline/kb/compression.py:10-11` — `DEFAULT_MAX_CONTEXT_CHARS = 6000`, `MIN_COMPRESSED_CONTEXT_CHARS = 256`
- `src/film_pipeline/kb/compression.py:25` — `compact_json_context(..., max_chars=DEFAULT_MAX_CONTEXT_CHARS)`
- `src/film_pipeline/graph/nodes/_context.py:189,215,217,241` — independent slices `[:80]`, `[:150]`, `[:60]`, `[:200]`
- `src/film_pipeline/agents/impl/constitution_agent.py:67`, `development_agent.py:86`, `screenwriter_agent.py:62` — `[:2000]` each
- `src/film_pipeline/mcp/tools/bibles/character.py:39`, `environment.py:40` — `script_text[:8000]`; `shot.py:184` — `script_text[:6000]`
- `src/film_pipeline/providers/failure_classifier.py:214` — `compress_prompt_for_retry(..., factor=0.6)`
- `docs/modular-architecture/audit/09-kb-context-and-provenance.md:74-76` — the prose that analyses it (with a good anchor list) but does not promote it to a numbered finding

**Why it is a hole (bar A6, not the taxonomy).** §1.6.3 requires every finding to carry a
drift proof *and* a reproduce command; §1.6.6 requires unverifiable claims to move to a
labelled hypothesis section. This concern is analysed in prose, given a DISTRIBUTED
status in the authoritative ownership map, and never given a finding record — so the
163/173 finding counts cannot include it, and no verifier checked it. The taxonomy does
apply: the same "how many characters of an artifact reach a prompt" policy is
re-implemented in `kb`, `graph`, `agents` and `mcp` with four different numbers
(256/6000/2000/8000) and ad-hoc slices. O-class: **O5**.

**Reproduce**

```bash
cd ${REPO_ROOT}
grep -n "recorded in audit 09" docs/modular-architecture/01-ownership-map.md
grep -n "Compression / bounding" docs/modular-architecture/audit/09-kb-context-and-provenance.md
grep -rn "\[:8000\]\|\[:6000\]\|\[:2000\]" src/film_pipeline --include=*.py
```

**Which audit should have owned it.** Audit 09 — it already has the evidence; it needs
an `F-KBCTX-NN` block.

---

### H7 — The numeric-policy inventory is partial: retries, sampling rates, list caps, prompt caps and post timings are unaudited (O5)

Audit 03 §4 is the program's only numeric-policy inventory. It covers the famous
values (shot duration 5, runtime fallback 300, capability `max_duration_seconds`,
validator bands, 512px resolution, tolerances, stall rounds). It does not cover:

| Anchor | Value | Why it is policy |
|---|---|---|
| `src/film_pipeline/validation/impl/prompt_readiness.py:15` | `MAX_PROMPT_LENGTH = 8000`, enforced at `:83,:90` | a gate threshold; a prompt above it fails readiness |
| `src/film_pipeline/mcp/tools/bibles/character.py:39`, `environment.py:40` / `shot.py:184` | `[:8000]` / `[:6000]` | the same "max prompt size" concern, re-chosen at three call sites |
| `src/film_pipeline/mcp/tools/checkpoints.py:21` | `_RECENT_CHECKPOINT_LIMIT = 20` | list cap |
| `src/film_pipeline/post/audio_design_agent.py:10-12` | 30.0 / 25.0 / 5.0 | the post-production timeline model |
| `src/film_pipeline/generation/frame_reviewer.py:48,66,82,89` | `per_ten=3/3/5` | the paid-review sampling rate — a cost policy |
| `src/film_pipeline/agents/runner.py:299,320,338` and `mcp/tools/reference_generation/retry_loop.py:214` | 3-attempt ladders | two independent retry counts |
| `src/film_pipeline/app/logging_setup.py:22-23` | 1,000,000 / 5 | log rotation |
| `src/film_pipeline/providers/mock_image_provider.py:16` | `_MOCK_SIZE = 1024` | doubles influence test outcomes |

**Why it is a hole.** Each is a number a gate or loop depends on; several are the same
concern expressed twice (8000 in a validator and 8000/6000 in MCP prompts). The audits
never claim to have found *all* numeric duplication, but bar A1 claims every source
package is mapped to a concern, and "the numeric policy surface" is a concern that
audit 03 declares as its §4 and leaves half-enumerated. O-class: **O5**.

**Reproduce**

```bash
cd ${REPO_ROOT}
grep -rn "MAX_PROMPT_LENGTH\|_RECENT_CHECKPOINT_LIMIT\|_SCENE_SPACING_SECONDS\|per_ten=\|\[:8000\]\|\[:6000\]" src/film_pipeline --include=*.py
grep -c "MAX_PROMPT_LENGTH\|_RECENT_CHECKPOINT_LIMIT\|per_ten\|_SCENE_SPACING" docs/modular-architecture/audit/03-config-profile-and-defaults.md
# -> 0
```

**Which audit should have owned it.** Audit 03 §4 (extend the table) with audit 08
(prompt-readiness gate) for `MAX_PROMPT_LENGTH`.

---

### H8 — Generation-mode resolution is implemented twice, once in `graph` and once in `mcp` (O1)

**Anchors**

- `src/film_pipeline/graph/nodes/_generation_batch_planning.py:20-27` —
  `def _parse_generation_mode(mode_str): mode = GenerationMode.TEST; with suppress(ValueError): mode = GenerationMode(mode_str); return mode`
- `src/film_pipeline/mcp/tools/generation/planning.py:21-28` —
  `def _resolve_generation_mode(args): mode_str = str(args.get("mode", "test")); mode = GenerationMode.TEST; …`

**Why it is a hole.** Two byte-equivalent policy implementations for "which
`GenerationMode` does this request run under", with the same silent fallback to
`TEST`. `GenerationMode` decides dry-run versus real provider spend, so a partial edit
(default one to `PRODUCTION`, or make one raise) changes spend behaviour on one path
only. No audit file contains either symbol or the mode vocabulary. O-class: **O1**.

**Reproduce**

```bash
grep -rn "_parse_generation_mode\|_resolve_generation_mode" src/ docs/modular-architecture/audit/ --include=*.py --include=*.md
```

**Which audit should have owned it.** Audit 06 (generation runtime) and audit 11/05
(MCP generation lifecycle).

---

### H9 — `_pending_row_updates` is a second, undeclared state key, and the app/MCP path discards the matrix patch (O3 + O8)

**Anchors**

- `src/film_pipeline/graph/nodes/qc.py:421` — `pending = state.setdefault("_pending_row_updates", [])`
- `src/film_pipeline/graph/nodes/qc.py:70` — `pending_updates = state.pop("_pending_row_updates", [])`, consumed by `_emit_matrix_patch_from_findings`
- `src/film_pipeline/graph/nodes/qc.py:39` — only `qc_node` calls `_emit_matrix_patch_from_findings`
- `src/film_pipeline/app/_graph_exec.py:336-337` — the app path clears the key then calls `_run_validators(working)`, and never consumes it
- `src/film_pipeline/graph/state_schema.py:102-215` and `graph/orchestrator_state.py:93-165` — neither declares the key

**Why it is a hole.** Audit 02's writer law enumerates exactly these keys and misses
this one (`grep -rn _pending_row_updates docs/modular-architecture/audit/ → 0`). F-VR-03
(08:471) covers the *side-effect* half ("missing matrix patches exactly when a human
has requested a fix") but not the state-authority half: a key that crosses the
`qc_node` boundary and is absent from both the TypedDict and `ORCH_CHANNELS`, so the
F-OST-01 parity sweep cannot see it. O-class: **O3**, **O8** (private key tuple /
untyped sidecar).

**Reproduce**

```bash
cd ${REPO_ROOT}
grep -rn "_pending_row_updates" src/ --include=*.py
grep -rn "_pending_row_updates" docs/modular-architecture/audit/ | wc -l    # -> 0
UV_CACHE_DIR="$PWD/.uv-cache" uv run python /tmp/channels.py                 # lists it as USED but NOT declared
```

**Which audit should have owned it.** Audit 02 (channel law), with audit 08 already
holding the side-effect half.

---

### H10 — `schemas/execution_brief.py` re-spells the pacing vocabulary and is named nowhere in the deliverable (O1)

**Anchor:** `src/film_pipeline/schemas/execution_brief.py:51` —
`pacing_style: str = Field(default="standard", description="Pacing style: 'slow_cinema', 'standard', 'dynamic'.")`

**Why it is a hole.** A fourth authority for the pacing vocabulary (see H3), in a file
that no audit file names (`execution_brief` appears 5× in the corpus, but never this
path/field; the audit 07 schemas table lists `artifact.py`, `_base.py`,
`runtime_state.py`, `__init__.py` and the registries). `ExecutionBrief` is the
structural brief that `OrchChannelSpec` says "must reach live state", so its fields are
normative. O-class: **O1**.

**Reproduce**

```bash
grep -rn "pacing_style" src/film_pipeline/schemas/ docs/modular-architecture/audit/ | head
```

**Which audit should have owned it.** Audit 07 (`schemas/**`) with audit 12 (scope
contract / constraints).

---

### H11 — The ownership map's own counts are not reproducible, and its §16 coverage ledger is stale (bar A2 §1.6.4)

**Anchors**

- `docs/modular-architecture/01-ownership-map.md:13-30` — claims **173 live findings,
  38 Critical / 88 High / 47 Medium / 0 Low**, and class distribution **O1 57, O5 33,
  O8 32, O3 29, O6 24, O4 24, O2 23, O7 13**, with stated recount commands.
- Reproducing those exact commands at this revision gives:

```bash
cd ${REPO_ROOT}/docs/modular-architecture
grep -h '^- \*\*Severity:\*\*' audit/*.md | wc -l                                  # -> 173   (matches)
grep -h '^- \*\*Severity:\*\*' audit/*.md | sed -E 's/^- \*\*Severity:\*\* *\**([A-Za-z]+).*/\1/' | sort | uniq -c
# -> 38 Critical / 86 High / 49 Medium          (map says 88 / 47)
grep -h '^- \*\*Class:\*\*' audit/*.md | grep -oE 'O[1-8]' | sort | uniq -c
# -> O1 60, O2 23, O3 31, O4 26, O5 35, O6 24, O7 15, O8 36   (map says 57/23/29/24/33/24/13/32)
```

- `docs/modular-architecture/01-ownership-map.md:294-317` (§16 ledger) still carries the
  **pre-verification** per-package counts: `agents` 10 (actual 12),
  `artifacts` 9 (13), `generation` 13 (16), `graph` 10+16+11 (11+17+15), `kb` 10 (13),
  `mcp` 12 (15), `providers` 7 (8), `testing` 8 (10 live), `validation` 11 (15).

**Why it is a hole.** §1.6.4: "Counts must be mechanically reproducible." The class
breakdown and the bar-A1 coverage ledger are not. This is a *measurement about the
audit set itself*, so it belongs in this review, not in an ownership finding.

**Which audit should have owned it.** The orchestrator/`01` synthesis (its own
preamble already documents the fix-loop churn but the commands it prints do not
reproduce the numbers it prints, and §16 was not regenerated).

---

### H12 — `documentation/` is declared out of scope, but `AGENTS.md` makes the blueprint the source of truth, and it drifts from the code

**Anchors**

- `AGENTS.md:9` — "The architectural source of truth is `documentation/architecture-blueprint.md`."
- `documentation/architecture-blueprint.md:1570` and `:1655` — the documented graph-state
  value is `"current_phase": "visual_development"`
- `src/film_pipeline/schemas/_base.py:77-90` — `FilmPhase.VISUAL_DEV = "visual_dev"`

**Why it is a hole (bounded).** `01-ownership-map.md` §16 openly declares this gap
("`documentation/` was used as prior art, not audited"), so this is a *named* gap, not
a hidden one — but it is 62 Markdown files / **15,350 lines**, and the one sample I
checked produces a state value the current schema rejects:

```bash
cd ${REPO_ROOT}
UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "
from film_pipeline.schemas._base import FilmPhase
try: FilmPhase('visual_development')
except ValueError as e: print('REJECTED:', str(e)[:60])"
# -> REJECTED: 'visual_development' is not a valid FilmPhase
```

**Which audit should have owned it.** None, by the declared A1 scope; this is a
program-level scope decision that should be stated as a residual risk rather than
absorbed into "used as prior art".

---

### H13 — `scripts/` is 1,678 lines of phase-hardcoding, sampled not audited

**Anchors**

- `docs/modular-architecture/audit/11-mcp-surface-safety-and-entrypoints.md:103` — only
  two scripts are in scope, as evidence for F-MCP-02.
- `scripts/e2e-real-auto-approve.py:113`, `scripts/test-full-pipeline-direct.py:59` —
  hardcoded partial phase lists (audit 01 §1 notes these).

**Why it is a hole (bounded).** `scripts/*.py` totals 1,678 lines and contains **50**
phase-name literals (`grep -cE '"(intake|…|delivery)"' scripts/*.py`), plus a live
confirmation-gate bypass (F-MCP-02 already records the bypass). The phase lists are
normative-looking duplication that no finding numbers. `01-ownership-map.md:314`
honestly marks it "(unverified) partially audited — flagged".

**Reproduce**

```bash
cd ${REPO_ROOT}
wc -l scripts/*.py | tail -1
grep -cE '"(intake|constitution|development|script|visual_dev|shot_bible|gen_planning|generation|qc|post|delivery)"' scripts/*.py | awk -F: '{s+=$2} END{print s}'
```

**Which audit should have owned it.** Audit 11 (scripts) with audit 01 for the phase
vocabulary.

---

### Hypotheses (no counterexample produced — explicitly **not** holes)

- **Y1** `constraints/_keywords._GENRE_KEYWORDS` / `_TONE_KEYWORDS` /
  `_VISUAL_STYLE_KEYWORDS` (single file, read in full by audit 12) may duplicate the
  vocabulary the prompt templates ask the model to emit. I found no second table in
  `src/`, only prose in templates, so no drift proof exists.
- **Y2** `generation/sheet_reviewer._RUBRICS["scale_sheet"]` is unreachable: only
  `character_identity_sheet` and `environment_board` are passed to
  `review_composite_sheet` (`composites.py:105,131`). That is a dead-code/incompleteness
  observation, not distributed ownership, and I did not trace every composite builder.
- **Y3** The Z.AI endpoint pair (`agents/model_adapter.py:40-41`) is declared once in
  `src/`; F-PROV-08 covers the Gemini triple but not Z.AI. I found no second `src/`
  declaration, so no O1 seam is demonstrated.

---

## 4. Blunt verdict on A1 coverage

**Package/file coverage: substantially real, not decorative.** All **17/17** source
packages are named by at least one audit's §1; **276/281** source files are named by
basename, and the remaining 5 (`impl/{character,constitution,environment,style}_bible_agent.py`,
`impl/visual_dev_agent.py`) fall inside audit 04's declared brace-glob, so there is no
orphan file and no "nobody's cluster" package. I re-ran the audits' own reproduce
commands and they match: audit 01's phase sweeps return exactly `entries=129 files=16`
and `359`; audit 14's `grep -rl schemas._base … | grep -vc '^src/film_pipeline/schemas/'`
returns exactly `72`; audit 06's `grep -rn GenerationExecutor src/film_pipeline/graph/`
returns `0`; audit 12's `ProjectConstraints(` count returns the number it states. The
173 live finding blocks all carry Class, Severity, a drift proof and a reproduce step
(`F-CFG-02` embeds its reproduce snippet inline in the drift proof rather than in a
dedicated field; only the withdrawn `F-TEST-02` heading lacks the block entirely). The
coverage sections are work, not decoration.

**Concern coverage: not complete, with named gaps.** Of **671** curated normative
items, **95 (14%)** are never mentioned anywhere in the deliverable; of those, **18
rows covering 9 distinct concerns** are verified ownership holes with anchors and
reproduce commands, and **2 more seams** (H3 pacing aliases, H4 capability sets) were
falsely scored "covered" by the text test. The pattern is systematic: the audits
enumerate *symbols they grepped for* and dismiss whole sub-packages as "grep-swept"
(audit 06 on `compositor/**`) or dismiss prose as an inventory (audit 03 §4, audit 05's
`retry`/`poll(` rows, audit 09's compression paragraph). The result is that
**vocabulary-shaped seams inside in-scope packages** — the frame-role set (H1), the
pacing alias tables (H3/H10), the capability sets (H4), the sheet-type/rubric pair
(H5), the generation-mode pair (H8) — are the systematic blind spot, because a
file-level or line-level grep does not reveal that two tables must agree.

**Quantified A1 gaps**

| Gap | Count |
|---|---|
| Source packages with no audit §1 mention | 0 / 17 |
| Source files with no literal-path or basename mention | 5 / 281, all inside a declared brace-glob |
| Curated normative items never mentioned in the deliverable | 95 / 671 |
| Verified ownership holes with anchors and reproduce commands | 13 (H1–H13) |
| Concerns whose DISTRIBUTED status has no finding id (bar A6) | 1 (compression, §9) |
| Finding blocks whose `Class` field names **no** O-class (bar A4) | 2 — `F-KBCTX-04` ("none of O1–O8") and `F-KBCTX-06` ("*not* O6 lifecycle"). Both give a reason, but A4 requires an O-class and neither is demoted into the hypothesis section |
| Finding blocks with no dedicated `**Reproduce:**` field | 1 live (`F-CFG-02` — it embeds the command inline in its drift proof, so the finding is verifiable but not machine-collectable) |
| Ownership-map summary numbers not reproducible with its own commands | 2 of 3 (severity breakdown, class distribution) |
| §16 coverage-ledger rows with stale finding counts | 9 of 21 |

**One-sentence verdict.** Bar A1 holds at package and file granularity and the greps
were genuinely run — this is not a fabricated audit — but it fails at **concern**
granularity: at least **13 ownership seams with concrete anchors and reproduce
commands**, concentrated in vocabularies/registries/numeric policies that no grep for
a *symbol* would surface, were never audited, so the deliverable's claim to have found
*every* instance of distributed ownership does not hold.

---

## 5. Things I checked and found genuinely complete (so this is a measurement, not a complaint)

- `--cov-fail-under=90` is real and enforced via `pyproject.toml:80` even though the
  `Makefile` `test-cov` target does not repeat it.
- Audit 01's two scope-wide phase sweeps reproduce byte-for-byte (`entries=129 files=16`; `359`).
- Audit 14's `schemas._base` count reproduces exactly (`72` non-schema importers / `109` total).
- Audit 06's claim that the graph never constructs `GenerationExecutor` reproduces (`0` hits).
- Audit 03 §4's numeric commands reproduce, and its documented prior-art citation drift is correct.
- Storage layout/root/atomic-write ownership is genuinely single-owner in `artifacts`
  (`_layout.py` literals have no second definition outside `artifacts/`; the guard
  `tests/unit/artifacts/test_storage_boundary.py` exists).
- KB conflict detection is genuinely single-owner (`AUTHORITY_RANK` in
  `kb/conflicts.py:17` has no second definition in `src/`).
- The 173 live finding blocks all carry Class + Severity + drift proof + a reproduce
  step; 171 of 173 name an actual O-class (`F-KBCTX-04` and `F-KBCTX-06` explain why
  they do not) and only the withdrawn `F-TEST-02` is structurally incomplete.
- `scripts/` really is developer tooling, not a shipped entry point (the `Makefile`
  never invokes it in `ci-check`), so its exclusion from A1 as an *entry point* is
  defensible; only its duplicated phase vocabulary is a gap.

### Things I could not verify

- I did not run the test suite (a deliberate constraint); all "no test fails" statements
  here are inherited, not re-executed. The audit program itself records that several
  subagents did not run it either (`reviews/program-process-record.md`, sandbox note).
- Three hypotheses in §3 remain hypotheses because I could not construct an anchor.

---

## 6. Appendix — exact commands used

```bash
cd ${REPO_ROOT}

# 1. inventory (AST over 281 files)
UV_CACHE_DIR="$PWD/.uv-cache" uv run python /tmp/inv2.py            # 1,168 rows -> /tmp/inventory2.json

# 2. textual coverage of every inventory item against the deliverable
UV_CACHE_DIR="$PWD/.uv-cache" uv run python /tmp/cover.py           # 95 curated zero-mention
UV_CACHE_DIR="$PWD/.uv-cache" uv run python /tmp/tally.py           # curated tally

# 3. declared-vs-used state channels
UV_CACHE_DIR="$PWD/.uv-cache" uv run python /tmp/channels.py

# 4. enum members re-spelled as raw strings outside their defining module
UV_CACHE_DIR="$PWD/.uv-cache" uv run python /tmp/enumreuse.py       # (inline in §1.1 of the session log)

# 5. audit-set self-counts
cd docs/modular-architecture
grep -h '^### F-' audit/*.md | wc -l
grep -h '^- \*\*Severity:\*\*' audit/*.md | sed -E 's/^- \*\*Severity:\*\* *\**([A-Za-z]+).*/\1/' | sort | uniq -c
grep -h '^- \*\*Class:\*\*' audit/*.md | grep -oE 'O[1-8]' | sort | uniq -c
```

### Revision hashes (audit text at time of writing)

```
01-ownership-map.md        d59b931bcb217825024192133a419e8ef2d66dfeac7f0722ce0fd20093669f96
00-methodology…           6fc1ec700e9b8c068e701cf51c610e087439ad13ee34bfec734194054facb703
audit/01-phase-model…     75547299df2c90919c3a00d826e257fa879226824d045b2889222d606533c815
audit/02-orchestration…   5c9a9182171f6932cfbdc94e01fb9ae4b9940605766a3e6bb5bc580946bf70d4
audit/03-config…          866a75711b25af41b91c0dd11c12280e0253e14bacb472318e0ca6e551562bce
audit/04-agent…           cd88545d37a09181e8853d07e1421184691aca72e142f2cba13ed43cc52bc251
audit/05-provider…        8351740c4b16e4f24467d9ec0c9bd7c0b8245c97d4682e4e440a8f5ac5668079
audit/06-generation…      1fcff1e5c53a581bebbd0f659af4076c78dbc912e9ee6c79960f8900027f69d0
audit/07-artifact…        a184d57295c8aca8ce241fbbe9bae11d4aeae50ff27cf117748c2822c935f07f
audit/08-validation…      f5142f98b55ed9a56183b5b41df6ecac9b0e1f3d733c95fa4cde405df715e94e
audit/09-kb-context…      d77d871e8342ef4056fe6eb6bcc81c1afe3c25394bf70f65c9edcf5f5e114c28
audit/10-checkpoints…     a0d39525a8d4afdaa3d3b0851bd1b73b807fb3c3523cd0f8f63e892297a48aca
audit/11-mcp…             3cf4f35732914a81650bf84f7606f993e9ea7c768bf9758d13e71b6d1a9d4ec7
audit/12-post…            81e07510e9a55f2b537a1ca416ae51f5ead7af366e0df1d330ca40fd00504bbc
audit/13-test-doubles…    1b6d4e8443030916c31af0c2f6d916c620b96fc9eba009c89748cef0ebcb756e
audit/14-module…          6bc51d6392e4ff11395e203b7db572944512f9d7479b90b82b2f07e8e01a1f01
```
