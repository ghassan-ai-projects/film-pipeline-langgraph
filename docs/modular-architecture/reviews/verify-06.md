# Verification — Audit 06 (generation runtime and ledger)

Verifier: independent adversarial pass (not the author). Repo `modular-app` @
`fb85baa0e6b769b709791a96a89980089304bf13`; working tree clean, so all reads are
HEAD reads. Method: every `path:line` re-printed via `git show HEAD:<path>`;
high-stakes claims re-run mechanically with `.venv/bin/python` + throwaway
scripts under `/tmp/ver06/` (no repo file touched). Bar A6 applies.

## Verdict table

| finding | verdict | one-line reason |
|---|---|---|
| F-GEN-01 | CONFIRMED | Spy adapter re-run: operator path sends resolved text, MCP path sends `"prompt:pkg-42"` verbatim; all anchors exact. |
| F-GEN-02 | CONFIRMED | `deliver_completed_job` has exactly one caller (`executor.py:275`); `dispatch.py:239-245` writes status/poll fields only, no `output_refs`, no manifest/take. |
| F-GEN-03 | CONFIRMED | Both `_prompt_entry_*` maps are the same 6-key mapping; RCTCO branch exists only in `_generation_prompts.py`; constitution ref vs latest artifact verified. |
| F-GEN-04 | CONFIRMED | 10 `update_row(` sites in exactly 2 modules; all three field divergences (`next_action`, `submitted_at`, `poll_count`) reproduced statically; `veo_fast.poll` does not touch `polls`. |
| F-GEN-05 | CONFIRMED | `generation.py:64` sets `generated` at planning time while the ledger row is `SUBMITTED` with empty `output_refs`; asset ref is the `gen:` id. One bad citation (see disputes). |
| F-GEN-06 | CONFIRMED | Enum has exactly 10 members; row writers use exactly 6 (`prepared/submitted/running/completed/failed/cancelled`); `TIMED_OUT`/3 blocked members are read-only. |
| F-GEN-07 | **DOWNGRADED** | Drift proof refuted: the named mutation fails `tests/unit/artifacts/test_state_persistence.py:321-369` (re-run, FAILED). Duplication is real but not a §1.3 silent-partial-edit seam. |
| F-GEN-08 | **DOWNGRADED** (12→9) | Existing divergence (reference assets never reach `AssetManifest`) holds; the mutation clause is refuted — `test_reference_generation_helpers.py:58` fails when `entries.py:73` is mutated (re-run, FAILED). |
| F-GEN-09 | CONFIRMED | Predicate, request-row builder, and manifest writer each duplicated byte-for-byte; both set `_text_only_generation_completed`; neither writes a ledger row. |
| F-GEN-10 | CONFIRMED | Rate change 0.18→0.36 doubles every ledger `estimated_cost_usd` (1.44→2.88) while the ceiling artifact is unchanged; duration-default count is understated (see disputes). |
| F-GEN-11 | CONFIRMED | Reproduced: id-bearing state + `shot_id`-only incoming → 2 entries for one shot; both sides id-less → incoming request silently dropped. |
| F-GEN-12 | CONFIRMED | Denylist/sidecar grammar duplicated 3×; `_asset_kind` returns `generated_clip` for any unknown suffix incl. `.json`; no test covers either function. One proof clause wrong (see disputes). |
| F-GEN-13 | CONFIRMED | `ledger.load` creates+persists on `FileNotFoundError` (`ledger.py:59-60`); graph read path calls it unguarded (`generation.py:44`); `has_ledger` used only by the executor. |

## Non-CONFIRMED rows — counter-evidence and recomputed severity

### F-GEN-07 — DOWNGRADED: High (3×4=12) → **Medium (3×2=6)**

Counter-evidence (mechanical). The drift proof says mutating
`artifacts/project_storage.py:209` to drop the `"scenes"` segment is silent
("no caller notices … nothing failing"). It is not: the sole live caller
`generation/executor_delivery.py:55` writes through `media_dir`, and
`tests/unit/artifacts/test_state_persistence.py:321-369` hardcodes
`tmp_path / "store/p1/media/scenes/SC_001/shot_0001"` then asserts the
downloaded file exists there. Re-run with a pytest plugin that monkeypatches
`ProjectStorage.media_dir` to the mutated shape:

```
PYTHONPATH=/tmp/ver06 .venv/bin/python -m pytest \
  tests/unit/artifacts/test_state_persistence.py -k delivery_lands -p mut_media -q
→ FAILED tests/unit/artifacts/test_state_persistence.py::TestMediaLayout::test_delivery_lands_in_media_with_sidecar_and_relative_manifest
```

The audit itself cites that same test (line 690, "Clean concerns") as pinning
`media/scenes/` paths — an internal contradiction. Mutating the *dead*
`paths.py:39` alone is indeed silent, but produces no divergent behavior, so the
§1.3 condition ("a partial edit can pass every existing test while producing
divergent behavior") is not met. Remaining content: one dead, publicly exported
helper (`artifacts/paths.py:37-39`, re-exported `artifacts/__init__.py:20,47`)
next to the live `ProjectStorage.media_dir` — real, but cleanliness, not a
silent drift seam. Recommend reclassifying as O1/Low-Medium, or deleting the
helper. Production media-path construction sites: **2** (paths.py:39 dead,
project_storage.py:209 live), plus one delegated caller (`executor_delivery.py:55`)
and one test hardcode (`test_state_persistence.py:355`).

### F-GEN-08 — DOWNGRADED: High (3×4=12) → **High (3×3=9)**

Counter-evidence (mechanical). The drift proof's named mutation ("change the
directory in `entries.py:73` … and no test fails") is refuted by the very test
it cites. `tests/unit/mcp/tools/test_reference_generation_helpers.py:54-58`
asserts `_reference_output_dir(...) == root/"references"/"characters"/"leo"/"master-frames"`.
Re-run with a plugin that mutates the helper's directory:

```
PYTHONPATH=/tmp/ver06 .venv/bin/python -m pytest \
  tests/unit/mcp/tools/test_reference_generation_helpers.py -k output_dir -p mut_ref -q
→ FAILED ...::test_reference_output_dir_for_character   (line 58 AssertionError)
```

So drift likelihood is 3, not 4: the helper site is pinned, the five
`composites.py` inline sites are not (no composites tests exist). The finding
itself survives on the *existing-divergence* limb of §1.6.3, which I verified:
`grep -rn "write_manifest\|add_take" src/film_pipeline/mcp/tools/reference_generation`
→ no matches, so reference frames/sheets exist on disk and in
`references/index/reference-index.json` but never in `AssetManifest`. Score 9
(High, bottom of band).

## Missed in scope

1. **Provider-status vocabulary duplicated as raw string literals** (not in any
   finding; conflicts with the audit's "Clean concerns" row "provider-side job
   status curve … one enum"). `generation/executor.py:245` `if job.status ==
   "completed":` / `:247` `elif job.status == "failed":` re-derive
   `providers/base.py:15-22` (`class ProviderJobStatus(StrEnum)`) as literals,
   while `mcp/tools/generation/dispatch.py:188` parses it as a typed enum
   (`ProviderJobStatus(provider_status)`). Mutation: rename
   `ProviderJobStatus.COMPLETED`'s *value*; the executor's completion branch
   silently stops matching and completed jobs stay `RUNNING` forever (caught
   today only indirectly by `tests/unit/generation/test_executor.py:215,231`).
   O1/O8; Low–Medium given the indirect test pin.
2. **Two different `scene_id` defaults for the same media.** `executor_delivery.py:46`
   returns `"unassigned"` (so `ProjectStorage.media_dir` creates
   `media/scenes/unassigned/<shot>/`, `project_storage.py:209`), but
   `executor_delivery.py:97` and `:111` record `scene_id` as `""` in the sidecar
   and the `AssetEntry`. `AssetManifest.list_by_scene` (`artifacts/manifest.py:56-57`)
   can therefore match neither `""` nor `"unassigned"` for that media, and the
   path cannot be rebuilt from `(scene_id, shot_id)`. No test exercises a
   scene-less shot: every `deliver_completed_job` test passes `{"scene_id": "SC_001"}`.
   O1/O5.
3. **Media writes bypass the declared single writer.** `ProjectStorage` is
   asserted (by `tests/unit/artifacts/test_storage_boundary.py:144-159`) to be
   the only writer, but the compositor writes image content straight to disk:
   `generation/compositor/extras.py:183-184`
   (`output_path.parent.mkdir(...)`; `canvas.save(output_path, "PNG")`) and
   `generation/compositor/environment.py:133`. The storage-boundary tests only
   ban *imports* of `artifacts.paths`/`_layout`, so this write surface is
   unenforced. In scope for `generation-runtime`/`artifacts` reconciliation.
4. Minor: `mcp/tools/generation/dispatch.py:139-143` constructs a
   `GenerationExecutor` only to borrow `load_shot_rows`, then re-implements
   submit/poll itself (O7 support for F-GEN-01/02, not named by the audit).

## Disputes requiring the author to fix

1. **F-GEN-05 citation error.** `artifacts/store.py:823` is cited as
   "(normalizes `asset_refs`)". Line 823 is `for key in ("characters",
   "asset_refs", "reference_refs", "validation_refs"):` inside the scene→markdown
   renderer (`_markdown_value`); it *reads* `asset_refs` to emit markdown and
   normalizes nothing. It is the only occurrence of `asset_refs` in `store.py`.
   Replace with the real patch-application site (`schemas/matrix_patch.py:49`
   `def apply_to(...)`, reached via `artifacts/matrix_projection.py:45`
   `rows = patch.apply_to(rows)` — itself currently uncalled in `src/`) or drop
   the claim.
2. **F-GEN-07 drift proof + prior-art line.** Proof refuted (see above); also
   "`documentation/audit-findings.md:83`" is off by two — the quoted line is
   `documentation/audit-findings.md:85`.
3. **F-GEN-08 drift proof.** Drop "no test fails": the cited
   `test_reference_generation_helpers.py:58` fails on the named mutation.
   Reframe the silent side as the five unpinned `composites.py` inline paths.
4. **F-GEN-10 duration count.** "re-derived at four sites" does not survive its
   own reproduce command: `grep -rn 'duration_seconds", 5' src/film_pipeline`
   returns **8** sites (`executor.py:116,178`;
   `_generation_batch_planning.py:150`;
   `mcp/tools/generation/planning.py:97`; `mcp/tools/generation/dispatch.py:146`;
   `app/services/_generation_ops.py:136`; `agents/impl/shot_bible_agent.py:88`;
   `mcp/tools/planning.py:179,183`), plus `providers/base.py:58` = `5.0`.
   State 8 (or scope the claim to the four cost/dispatch sites).
5. **F-GEN-12 proof clause.** "`.mp4` sorts before the `.json`, so the sidecar
   becomes the active take" is only true for underscore-style names
   (`<shot>_x.json`). For same-stem companions the opposite holds — measured:
   `_produced_files` on `{shot_0001.mp4, shot_0001.json}` returns
   `['shot_0001.json', 'shot_0001.mp4']` and the **real clip** stays active.
   The durable defect that always holds is that `_asset_kind` classifies the
   `.json` as `generated_clip` and it is written into the manifest/sidecar as a
   phantom clip. Fix the proof; keep the finding. Also note the O-class is
   arguably O1/O2 (three sidecar grammars, duplicated produced-file predicate)
   rather than O5.
6. **F-GEN-02 count.** "`grep -rn deliver_completed_job src/film_pipeline` → 2
   hits" — the command returns 3 (import `executor.py:23`, definition
   `executor_delivery.py:25`, call `executor.py:275`). One call site, three
   hits; quote the output as-is.
7. **F-GEN-04 weak anchor.** `dispatch.py:37` is cited for "leaves `next_action`
   at `submit`"; line 37 is the closing `)` of the `update_row` call (the call
   spans 31-37). Point at `dispatch.py:31-37` or the field's absence in it.
8. **Candidate-owner overlap to reconcile.**
   `generation-runtime` is nominated 9 times and `generation-ledger` twice
   (F-GEN-04, F-GEN-13) for the same row-state concern — pick one module graph
   node, not two. F-GEN-01/02 make `generation-runtime` construct the provider
   payload (`providers` owns `build_payload`/submit/poll) and write the
   `AssetManifest` (`artifacts` owns the model + atomic write); F-GEN-08 also
   puts a reference-layout helper "beside" ProjectStorage while F-GEN-07/12
   assign media layout to `artifacts`. Net: three of the audit's own candidate
   owners disagree about who owns media layout and the manifest write. The
   runtime's contract should be *which* prompt/refs/duration and *which* entries,
   with `providers` owning payload shape and `artifacts` owning paths + writes.

## Overall verdict

**11 of 13 findings CONFIRMED as stated; F-GEN-07 downgraded to Medium (proof
refuted, not a §1.3 seam) and F-GEN-08 downgraded to High-9 (proof clause
refuted); the program is blocked on the nine disputes above, all of which are
proof/citation fixes rather than new investigation.**
