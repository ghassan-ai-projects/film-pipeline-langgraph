# Anchor check 02 — mechanical sweep of `02-duplication-ledger.md`

Revision audited (frozen): `docs/modular-architecture/02-duplication-ledger.md`, **1005 lines**,
**157466 bytes**, mtime **2026-09-25T15:25:14**, SHA-256
`7975d3aa5b1cd76c9a589ff0fea5dce4abf9b88fb8da897ace72996558eaaf61`. The ledger was under
concurrent edit for the first ~20 minutes of this run (883 → 979 → 991 → 996 → 1005 lines,
five hashes observed); every number below is measured against the frozen hash above, and all
findings are keyed by concern id as well as line number so they survive any further shift.

## Method

A Python sweep read the ledger, tracked the current `### L-NN` entry, and extracted every
`<path>:<line>` / `<path>:<start>-<end>` / `<path>:<a>,<b>` token matching
`[A-Za-z0-9_][A-Za-z0-9_./*-]*\.(py|md|yaml|yml|toml|json|cfg|txt|sh|sql|jsonl|ini):[0-9][0-9,\-]*`,
plus the ledger's path-elided continuation form `` `:NN` `` (bound to the nearest preceding path
token in the same backtick span, or, for the appendix table, to `documentation/audit-findings.md`
declared in the table header), for **375 anchors total** (345 `path:line`/`path:range` anchors in the
ranked ledger plus 30 appendix `:NN` refs). Path normalisation: an exact repo-root match wins; otherwise
the path is resolved as a `/`-suffix against the file index, preferring unique matches, then matches
under `src/film_pipeline/`, then (for bare filenames like `approval.py`, `base.py`, `registry.py`,
`operator.py`, `envelope.py`, `generation.py`, `qc.py`, `validation.py`) a candidate whose directory
matches a directory already resolved earlier in the same entry — the "audit's cited package" rule.
Ambiguities are listed in their own section below. For the identifier check, the backticked fragment
adjacent to the anchor in the `— \`code\``, `(\`code\`)`, `→ \`code\`` or verb+code form was taken as
the claim; its whitespace-normalised text (ellipsis-truncated), or failing that its key symbol
(function/class name, call target, assignment LHS, longest identifier), was searched in the cited line
or cited range (**RESOLVES**), then in the ±3-line window (**NEARBY**); on failure the whole file was
searched for the correct line (**WRONG-LINE**). Anchors with no adjacent quote were checked for
existence and range only (**existence-only RESOLVES**, 273 of them) and additionally spot-checked
against the entry's subject matter. `MISSING-FILE` = path did not resolve; `OUT-OF-RANGE` = resolved
file shorter than the cited line. Verdicts that the script's quote test could not decide (bare-filename
collisions, mutation-site anchors, retraction citations, comment-banner anchors) were adjudicated by
hand against the target file, and those adjudications are reported explicitly.

## Global tally

| Metric | Count |
|---|---|
| Total anchors extracted | **375** |
| RESOLVES | **365** (92 quote-checked, 273 existence-only) |
| NEARBY (±1–3 lines) | **1** |
| WRONG-LINE | **6** |
| MISSING-FILE | **2** |
| OUT-OF-RANGE | **1** |
| Non-RESOLVES subtotal | **10** (2.7 %) |
| UNANCHORED-CLAIM flags (separate from the anchor tally) | **32** |

Concern entries with at least one non-RESOLVES anchor: **5 of 58** (`L-13`, `L-21`, `L-28`,
`L-53`, `L-57`), plus the appendix `(c)` table. **53 of 58 entries are fully clean.**

## Non-RESOLVES anchors, by concern

### L-13 — Validator registry and phase→validator dispatch (ledger line 345; 3 of 13 anchors defective)

All three are on the single long "What is wrong" line and all three are bare-filename / path-elision
failures.

| Ledger line | Anchor as written | Verdict | Correction |
|---|---|---|---|
| 345 | `validation.py:138-157` | **OUT-OF-RANGE** | Intended file is `src/film_pipeline/mcp/tools/validation.py:138-157` (the `_PhaseSpec` arms; `_live_validator_specs` starts at `:123`). The bare name also matches `src/film_pipeline/schemas/validation.py` (76 lines) and `docs/modular-architecture/design/prototype-enforcement/arch-backup/validation.py`; shortest-suffix resolution lands on the 76-line schema file, which has no line 138. Spell the `mcp/tools/` path. |
| 345 | `registry.py:297-306` | **WRONG-LINE** | As written this elides onto the preceding `registry.py:240` → `src/film_pipeline/mcp/tools/registry.py:297-306`, which is checkpoint-tool registration (`get_checkpoint` … `rollback_artifact`), not the `run_validation` dispatch the text describes. The claimed dispatch (`visual_dev` / `script`) is at `src/film_pipeline/mcp/tools/validation.py:297-306`. |
| 345 | `registry.py:274-276` | **WRONG-LINE** | Same elision; `src/film_pipeline/mcp/tools/registry.py:274-276` is the `cancel_generation_request` registration. The claimed `validation_refs` write is `active.setdefault("validation_refs", []).extend(saved_refs)` at `src/film_pipeline/mcp/tools/validation.py:274-276`. |

Note: `registry.py:240` on the same line is correct (`src/film_pipeline/mcp/tools/registry.py:240` =
`_register(registry, "run_validation", …)`); it is listed under bare-filename ambiguities, not as a defect.
Also verified on that line: `state_schema.py:173` → `src/film_pipeline/graph/state_schema.py:173`
(`validation_report_refs`), `orchestrator_state.py:163` → the `"validation_report_refs"` `OrchChannelSpec`,
and `_agent_handoff.py:31` → `src/film_pipeline/graph/nodes/_agent_handoff.py:31` (docstring naming the channel).

### L-21 — Checkpoint metadata registries (ledger line 437; 1 of 4 anchors)

| Ledger line | Anchor as written | Verdict | Correction |
|---|---|---|---|
| 437 | `tests/unit/app/test_runtime.py:37` | **NEARBY** | The cited line is the comment `# The state snapshot was written and carries the step state.` The assertion that pins the non-empty map is two lines up, `tests/unit/app/test_runtime.py:35`: `assert cp.artifact_versions.get("script") == "artifact:script:v1"`. Correct anchor: `:35` (line 37 is the snapshot/state comment). |

### L-28 — Provider registry and catalog/capabilities (ledger line 513; 1 of 10 anchors)

| Ledger line | Anchor as written | Verdict | Correction |
|---|---|---|---|
| 513 | `providers/_provider_seeds.py:74` | **MISSING-FILE** | No file under `src/film_pipeline/providers/`. The module lives at `src/film_pipeline/app/_provider_seeds.py`, and line 74 is `("seedance-openrouter", "bytedance/seedance-2.0"),` inside `default_video_provider`. Correct anchor: `src/film_pipeline/app/_provider_seeds.py:74`. |

### L-53 — `profiles/` location and hardcoded numeric defaults (ledger line 790; 1 of 6 anchors)

| Ledger line | Anchor as written | Verdict | Correction |
|---|---|---|---|
| 790 | `config/bootstrap.py:34` | **MISSING-FILE** | No `src/film_pipeline/config/bootstrap.py`. The profiles-directory check is `src/film_pipeline/app/bootstrap.py:34` (`return ["profiles/ directory not found. Create it with at least one profile YAML."]` in `_missing_profiles_dir_issues`). Correct anchor: `src/film_pipeline/app/bootstrap.py:34`. |

### L-57 — Ref-string formatter duplicated (ledger line 831; 1 of 4 anchors)

| Ledger line | Anchor as written | Verdict | Correction |
|---|---|---|---|
| 831 | `tests/unit/review/test_diff.py:20-33` | **WRONG-LINE** | `from_string` occurs nowhere in that file (whole-file search: 0 hits); lines 20-33 are `TestArtifactDiff.test_empty` / `test_with_changes`, and the file only exercises `_id_stem` and `ArtifactDiff`. The `ArtifactRef` round-trip tests are `tests/unit/artifacts/test_refs.py:12` (`ArtifactRef.from_string("artifact:script:script:v3")`) and `:33` (`from_string(bad)` in the rejects case). Because the ledger sentence is itself a retraction ("dispute D1 requires deleting the claim that …"), the cleanest fix is to delete the line anchor; if a citation is kept, use `tests/unit/artifacts/test_refs.py:12,33`. |

### Appendix — Category separation `(c)`, evidence column (ledger lines 925–927; 3 of 31 refs)

These `:NN` refs are bound by the table header to `documentation/audit-findings.md` (176 lines).

| Ledger line | Anchor as written | Verdict | Correction |
|---|---|---|---|
| 925 | `:117` "checkpoint metadata in-memory only" | **WRONG-LINE** | `documentation/audit-findings.md:117` is "`rollback_to_checkpoint` executes immediately without enforcing confirmation." The claimed item ("Checkpoint metadata is in-memory only; `CheckpointManager` never persists it.") is at `:116`. So `:117` → `:116`. |
| 926 | `:118` "rollback without confirmation" | **WRONG-LINE** | `:118` is "`BranchManager` creates a git branch but does not root it at the checkpoint commit…". The claimed rollback-without-confirmation line is `:117`, one line above the current citation. So `:118` → `:117` (the `:117`/`:118` rows are shifted by one). |
| 927 | `:124` "`runtime.approve_phase` catches `Exception`, falls back to manual advance" | **WRONG-LINE** | `:124` is blank. The claimed bullet is at `documentation/audit-findings.md:129`. So `:124` → `:129`. |

All other 28 appendix refs (table rows and the "Still open" paragraph) match their
`audit-findings.md` lines verbatim, including `:40`, `:54`, `:56`, `:59`, `:82`, `:83`, `:85`, `:96`,
`:98`, `:127`/`:31`, `:130`, `:139`/`:15`, `:146`, `:45`, and `:41`, `:42`, `:43`, `:68`, `:71`,
`:72`, `:73`, `:74`, `:97`, `:114`, `:128`.

## Bare-filename / resolution notes (not counted as defects)

These anchors contain the identifier at the intended line once the correct same-package file is
chosen, but the ledger's short form is ambiguous and naive resolution goes elsewhere. They are
quality risks for a reader or tooling, not wrong citations.

| Concern | Anchor as written | Resolves to (correct) | Rival / hazard |
|---|---|---|---|
| L-10 | `qc.py:29-30`, `:42`, `:61-64` | `src/film_pipeline/graph/nodes/qc.py` | vs `graph/subgraphs/qc.py`; verified literals: `_QC_REF_KEYS` at `:30`, `_collect_updates(..., _QC_REF_KEYS)` at `:42`, the copy loop at `:61-64`. |
| L-13 | `registry.py:240` | `src/film_pipeline/mcp/tools/registry.py:240` | 6 files named `registry.py`; shortest-suffix picks `agents/registry.py` (132 lines) → false OUT-OF-RANGE. |
| L-35 | `approval.py:55` | `src/film_pipeline/graph/nodes/approval.py:55` (`severity == "blocking"` test) | vs `schemas/approval.py:55` (`)`). |
| L-46 | `operator.py:143` | `src/film_pipeline/app/services/operator.py:143` (`state["profile_stack"] = profile_stack`) | vs `mcp/tools/operator.py` (65 lines) → false OUT-OF-RANGE. |
| L-52 | `envelope.py:28` | `src/film_pipeline/mcp/envelope.py:28` (`requires_confirmation: bool = False`) | vs `artifacts/envelope.py` (no such field). |
| L-56 | `generation.py:44` | `src/film_pipeline/graph/nodes/generation.py:44` (`mgr.load(...)`) | vs `schemas/generation.py:44` (unrelated, but in range, so the sweep cannot reject it). |
| L-58 | `base.py:286-290` | `src/film_pipeline/validation/base.py:286-290` (`requires_human_review=status in (NEEDS_REVISION, BLOCKED,)`) | vs `agents/base.py` (60 lines) and `providers/base.py`; shortest-suffix → false OUT-OF-RANGE. Note `L-58` also writes `validation/thresholds.py` as owner, which is the intended package. |
| L-13 | `validation.py:138-157` | `src/film_pipeline/mcp/tools/validation.py:138-157` | counted as a defect above (resolves to the 76-line schema file). |

## Borderline anchors adjudicated as RESOLVES (checked adversarially, not defects)

- `L-31` `graph/nodes/approval.py:249` — the cited line is the comment banner `# ── Guard: reject approval when structural issues exist ──`, but the ledger quotes exactly that comment; the guard body `if _count_blocking_issues(state):` is at `:250`, and the same entry cites `:250` correctly (line 591). RESOLVES.
- `L-38` `artifacts/_layout.py:52-53` — cited without an adjacent quote; the range is the comment block explaining the layout key, and the named constants `JSONL_STORAGE_VERSION` / `JSONL_STORAGE_VERSION_KEY` are at `:54-55`. Existence-only RESOLVES; a reader wanting the identifiers should be sent to `:54-55`.
- `L-18` `artifacts/manifest.py:132-148` — the sweep flagged it OUT-OF-RANGE only because it bound the elided `:132-148` to the nearest *path-like* span. The elision actually follows `generation/executor_delivery._asset_kind`, and `src/film_pipeline/generation/executor_delivery.py:132-148` is exactly `_asset_kind`. RESOLVES with correct binding.
- `L-38` `artifacts/store.py:120`, `:217`, `store.py:435`, `:456` — the sweep's WRONG-LINE verdicts were claim mis-picks (it read the following `:NN` continuation as the claim). Verified literals: `validate_artifact_id(meta.artifact_id)` at `:120` and `:217`; `path = self._version_path(...)` at `:435` and `:456`. RESOLVES.
- `L-32` `constraints/_keywords.py:33` — `_NUMBER_WORDS` is declared at `:13` and the cited `:33` is its last entry `"twenty": 20,` (dict closes at `:34`); adding `"thirty": 30` at `:33` is the correct mutation insertion point. RESOLVES (mutation-site anchor).
- `L-28` `factory.py:49` — line 49 is `"seedance-openrouter": ["bytedance/seedance-2.0"],`, the value inside `_default_models` (defined at `:47`, ends `:56`). The anchor is inside the claimed function body. RESOLVES (mutation-target literal), though `_default_models` itself is declared at `:47`.
- `L-02` `agents/mvp/__init__.py:40` / `:96` and `validation/validators/__init__.py:131` / `:151` — literal values verified (`creative_writer`, `schema_enforcer`, and `model_profile="multimodal_reviewer"` at both 131 and 151). RESOLVES.
- `L-03` `mcp/tools/bibles/_shared.py:106` — line 106 literally contains `runner.model_router.resolve("creative_writer")`; "raises `AttributeError`" is the runtime consequence of `ModelRouter` lacking `resolve`, not source text on the line. RESOLVES.
- `L-14` `schemas/registries/validator_registry.py:17-19` — the three `Field(default=…)` lines are 85/75/65; the `[65,75)` band statement is derived from them. RESOLVES.
- `L-18` `artifacts/registry.py:131-194` with `:157` (shot-matrix id) and `:185` (`kb_context_packet`) — all three verified literally. RESOLVES.
- `L-28` `profiles/base.studio.yaml:43-85` — `:43` is `model_profiles:` and `:85` is the last line of the block (`temperature: 0.1`); `generation:` starts at `:87`. RESOLVES.

## UNANCHORED-CLAIM flags (32)

Bullets asserting a count of code artifacts or an exclusivity ("only", "no test", "never", "zero")
that carry **no `path:line` anchor and no reproduce command** on the same line. As briefed, the truth
of these claims was not checked — they are flagged because bar A2/A5 requires an anchor or a
reproduce command for every measurable claim. Lines are from the frozen revision.

| Concern | Ledger line | Quantified assertion |
|---|---|---|
| L-01 | 211 | "the refusal rule is re-instated at eight gate sites" |
| L-04 | 246 | "two writers whose schemas are incompatible" |
| L-06 | 268 | "two live implementations" |
| L-07 | 279 | "the class roster has 12 keys against 11 declared agents" |
| L-08 | 290 | "Prompt assembly itself has two implementations" |
| L-09 | 301 | "two incompatible value types depending on writer" |
| L-12 | 334 | "Tool invocation is implemented four times" |
| L-15 | 368 | "defined independently in eleven places across eight modules" |
| L-19 | 413 | "seven builders whose output is written to a key" |
| L-20 | 424 | "every one of one artifact-write path … and 11 other write paths" |
| L-21 | 435 | "Checkpoint metadata lives in two in-memory registries" |
| L-23 | 457 | "no test can observe the contract" |
| L-26 | 490 | "two thresholds already disagree" / "thresholds 5, 3 and the approval-edge default" |
| L-26 | 492 | "the two call sites already use 5 and 3" |
| L-27 | 501 | "`FailureClassifier` has zero production callers" |
| L-29 | 523 | "re-derived at 14 call sites" |
| L-31 | 545 | "re-derived at seven sites" |
| L-33 | 567 | "hand-built in four places" |
| L-34 | 578 | "eleven per-node `gate=` literals" |
| L-35 | 589 | "blocking predicate is re-derived at 18 sites" / "veto implemented four times" |
| L-36 | 602 | "no test compares the two" |
| L-40 | 637 | "stale generation-request code set is defined three times and emitted a fourth" |
| L-42 | 666 | "never persisted" (audit event) |
| L-44 | 688 | "Confirmation is enforced at two sites with two response contracts" |
| L-46 | 710 | "profile-stack key set is defined three times" |
| L-47 | 721 | "Fixture construction is re-implemented per tier" / "64 direct `ArtifactStore(root=...)`" |
| L-50 | 758 | "each checks only one direction" |
| L-52 | 778 | "the only transport then flattens the typed code away" |
| L-53 | 789 | "resolved relative to the process CWD in two modules" |
| L-54 | 800 | "imports three domains" |
| L-55 | 811 | "re-derived in two modules" |
| L-57 | 833 | "the single parser (10 call sites)" |

Excluded as a false positive: ledger line 724 (L-47 "Anti-rot evidence") matched only on a 7-hex-digit
commit id, which is itself evidence, not an unanchored claim.

## Worst offenders

1. **`L-13` (ledger line 345) — worst entry: 3 of its 13 anchors are defective (23 %), all on one
   line.** Two path-elided `:NN` continuations point into `mcp/tools/registry.py` while the claimed
   code is in `mcp/tools/validation.py`, and one bare `validation.py` resolves to the wrong module
   entirely. The line also mixes four different files through elision, which is what produced the
   failures.
2. **Appendix `(c)` table — 3 of 31 `audit-findings.md` line refs wrong (10 %).** `:117`/`:118` are a
   one-line shift (checkpoint-metadata row and rollback row swapped) and `:124` misses by five lines
   (blank line vs the `approve_phase` bullet at `:129`).
3. **`L-28` and `L-53` — one MISSING-FILE each.** Both cite a module path that no longer exists
   because the file is under `app/`: `providers/_provider_seeds.py` → `app/_provider_seeds.py`, and
   `config/bootstrap.py` → `app/bootstrap.py`. These are the only two hard-broken paths in the file.
4. **`L-57`** cites `tests/unit/review/test_diff.py:20-33` for a `from_string` behaviour, but
   `from_string` appears nowhere in that file; the real tests are `tests/unit/artifacts/test_refs.py:12,33`.
5. **`L-21`** points at a comment (`test_runtime.py:37`) instead of the assertion that proves its claim
   (`:35`); off by 2, hence NEARBY.

No defects were found in the other 53 concern entries. In particular, every primary "strongest anchor"
quote (the `— \`code\`` form) in those entries matched its cited line character-for-character after
whitespace normalisation.

## Commands run (reproducible)

```bash
# revision pin
stat -f '%Sm %z' -t '%Y-%m-%dT%H:%M:%S' docs/modular-architecture/02-duplication-ledger.md
wc -l docs/modular-architecture/02-duplication-ledger.md
shasum -a 256 docs/modular-architecture/02-duplication-ledger.md

# anchor extraction + existence/range/identifier verification (script written to /tmp, not the repo)
UV_CACHE_DIR="$PWD/.uv-cache" uv run python /tmp/anchor_check3.py      # -> /tmp/anchors3.json (345 ranked-ledger anchors)
#   regex: [A-Za-z0-9_][A-Za-z0-9_./*-]*\.(py|md|yaml|yml|toml|json|cfg|txt|sh|sql|jsonl|ini):[0-9][0-9,\-]*
#   plus path-elided `:NN` spans; suffix resolution with entry-scoped directory hints;
#   exact normalised quote (else key symbol) over cited range -> ±3 lines -> whole file.

# unanchored measurable-claim scan (no path:line and no grep/python/make/verify-N on the line)
UV_CACHE_DIR="$PWD/.uv-cache" uv run python /tmp/unanchored2.py        # -> 32 flags after one false-positive exclusion

# spot adjudication of every script non-RESOLVES and the appendix refs
sed -n '345p;437p;513p;790p;831p;925,927p' docs/modular-architecture/02-duplication-ledger.md
sed -n '29,33p' src/film_pipeline/mcp/tools/validation.py
sed -n '238,242p;272,278p;295,308p' src/film_pipeline/mcp/tools/registry.py
sed -n '120p;217p;435p;456p' src/film_pipeline/artifacts/store.py
sed -n '33,36p' tests/unit/app/test_runtime.py
sed -n '1,40p' tests/unit/review/test_diff.py
grep -rn "from_string" tests/
sed -n '116p;117p;124p;129p' documentation/audit-findings.md
sed -n '40p;54p;56p;59p;82p;83p;85p;96p;98p;127p;130p;139p;146p;45p' documentation/audit-findings.md

git status --porcelain
```

`git status --porcelain` is **empty** (verified after writing this file; the only file created is
this report under the gitignored `docs/` tree). No files under `src/`, `tests/`, or the repo root
were modified; no `git checkout`, `git clean`, `git stash`, or write command against a tracked file
was run; `make ci-check` was not run. Python was invoked only through
`UV_CACHE_DIR="$PWD/.uv-cache" uv run python`.
