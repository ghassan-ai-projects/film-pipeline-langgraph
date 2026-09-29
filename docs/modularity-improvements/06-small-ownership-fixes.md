# 06 — Small ownership fixes

Independent, one-commit slices. Each was checked against the tree at `2450616`.
Do **6.9 first** — until it lands, no slice can be graded by the architecture gate.
The rest are ordered roughly by how likely the defect is to cause a silent wrong result.

## 6.1 `_ORCH_NS` is mirrored across packages with no guard

`governance/orchestrator_reads.py:19` and `orchestration/orchestrator_state.py:77` both
define `_ORCH_NS = "_orchestrator"`. The governance copy exists so the gate validators
can read orchestrator state "without an upward import edge". If the orchestration value
changes, `get_execution_brief()` silently returns `None` and the brief gate
(`governance/validators/brief.py`) sees no brief — the "one policy, N sites" shape, with no test tying the two.

**Fix:** keep one definition. `orchestration -> governance` is already an edge (13
imports), so `orchestrator_state` can import the constant from
`governance.orchestrator_reads`; no new edge, no cycle.
**Check:** `measure.py` "`_ORCH_NS` definitions" goes 2 -> 1.

## 6.2 The Gemini endpoint is defined three times, under three names

| Module | Name |
|---|---|
| `agents/transports/gemini.py:22` | `GEMINI_API_ROOT` |
| `providers/adapters/imagen4_gemini.py:21` | `GEMINI_API` |
| `providers/gemini_review_client.py:25` | `GEMINI_API_BASE` |

And `agents/transports/chat_completions.py` gets the OpenRouter base URL by importing
`OPENROUTER_API` from **`providers.adapters.seedance_openrouter`** — a text-LLM
transport depending on a *video* adapter module for a string.

**Fix:** one module in `providers` owns vendor endpoints (next to `credentials`, which
already owns vendor key lookup); all four sites import from it.
**Check:** `measure.py` "Gemini API base URL definitions" goes 3 -> 1.

## 6.3 The "vendor calls belong in `providers`" rule is applied once

`providers/gemini_review_client.py`'s docstring states the rule: talking to a concrete
provider API and resolving its credentials "is provider-adapter work … so it lives in
`providers`". The three text transports in `agents/transports/` (`gemini`, `zai`,
`chat_completions`) do exactly that — they import `providers.credentials.lookup` and
`providers.http_transport.post_json` — and stay in `agents`.

**Decide one way and record it.** Either move `agents/transports/` to
`providers/text/` (then `agents -> providers` shrinks to the transport protocol), or
state in `agents/transports/__init__.py` why text transports are an agent concern.
Not both rules at once.

## 6.4 A leftover compatibility shim with no importers

`generation/gemini_client.py` is a "compatibility alias" re-exporting
`providers.gemini_review_client`. Nothing in `src`, `tests`, or `scripts` imports it.
AGENTS.md says the shims were removed. **Delete it.**

The same class, smaller: the `nodes.approval` re-export of `_PHASE_NODES` /
`repair_phase_node` for "historical `graph.nodes.approval` paths" (see 05, Finding B).

## 6.5 Cost residue after the cost-removal round

Defined, never read:

- `studio/mock_responses.py:14` — `_SEEDANCE_RATE_USD_PER_SECOND = 0.18`
- `devharness/mock_human.py:23` — `spend_limit_usd: float = 5.0`
- `providers/health.py:20` — `credit_remaining_usd: float = -1.0`

Stale wording: `governance/validators/__init__.py:6` still says Gate B checks
"non-placeholder cost estimates"; `planning_gates.py:86` records that half was removed.

**Fix:** delete the three fields (check `extra="forbid"` models and persisted JSON for
`credit_remaining_usd` first — it may be serialised in health snapshots), fix the
docstring.

## 6.6 Three things called "validators"

| Path | What it is |
|---|---|
| `governance/validators/` | structural phase gates S/A/B/C |
| `validation/impl/` | the quality validators (script structure, continuity, …) |
| `validation/validators/` | a package whose only content is `MVP_VALIDATORS` in `__init__` |

**Fix:** rename `governance/validators` -> `governance/gates` (they are called gates
everywhere else, including their own docstring), and move `MVP_VALIDATORS` into
`validation/registry.py`, deleting the one-file package. The surface ratchet will
record both changes.

## 6.7 `filmspec` is described as pure vocabulary but carries behaviour and messages

`filmspec` holds `NO_ACTIVE_PROJECT = "No active project."` (used only by `mcp`) and
the text-only generation-request builders (used only by `mcp` and `operations`). A
user-facing error string is an `mcp` concern; the builders belong with generation
planning. These moved into `filmspec` to be shared by two callers; after doc 03 there
is one. Move them then, not before.

## 6.8 The AGENTS.md package table is missing three packages

`generation`, `constraints`, and `cli` exist under `src/film_pipeline/` and appear in
neither the AGENTS.md sub-package table nor `06-independent-review-and-decision.md`
§4's ownership map. An agent reading the canonical instructions cannot tell who owns
generation lifecycle. **Add the rows.** (`generation`: ledger, executor, prompt
construction, compositor, frame/sheet review; `constraints`: extraction of project
constraints from operator input; `cli`: headless driver and product gate.)

## 6.9 The Enola gate is declining, not passing — do this first

AGENTS.md makes Enola a required gate at exit 0. On clean HEAD (`2450616`):

```text
$ enola check --baseline=docs/modular-architecture/enola-out docs/modular-architecture/enola-config.yaml
DECLINED — refusing to grade: the baseline is not comparable to the current snapshot.
  Blocking: version_mismatch — 0.2.7-51-g72cd079 vs 0.4.25
            ignore_globs — the set of files parsed changed
exit 3
```

The pinned baseline (`enola-out/receipt.json`) was generated at `df97c47` on
`modular-app-4` by an older enola. Every slice recorded since then as "Enola exit 0"
should be re-checked: a `enola check ... | tail` reports `tail`'s exit status, not
Enola's (this review made that mistake once before re-running).

Separately, the config ignores `.uv-cache`, `.venv`, and the other tool caches but not
`.pre-commit-cache/` (gitignored). `--detail` output lists `.pre-commit-cache/…/pre_commit_hooks`
edges among the "new coupling" — vendored code in the fact set.

**Fix, one commit:** add `".pre-commit-cache/**"` to `ignore` (a scope correction of
the same kind as `.uv-cache`, not a threshold change); from **clean HEAD** run
`enola --generate`, `enola baseline clear`, `enola baseline pin` with the installed
version; confirm the new snapshot holds 0 facts for removed packages and that
`enola check` exits 0 on the committed tree. Record the enola version in the progress
ledger so the next version bump is recognised as the cause of a DECLINED.

**Guard worth adding:** a `make enola` target that runs the check without a pipe and
fails on any non-zero exit, so the gate cannot be read through `tail` again.

## 6.10 Four verified-dead functions (from Enola's advisory list)

Enola's `dead-code` explainer flagged these; each was checked by `grep` and is
referenced only by its own `__all__` entry, in neither `src` nor `tests`:

- `mcp/tools/helpers._active_project_state` — the helper `11` §5b recommended routing
  handlers through; the dispatch-level precondition made it unnecessary.
- `orchestration/orchestrator_state.has_execution_brief`
- `storage/_layout.project_relpaths`
- `studio/_operator_runtime.runtime_for`

**Delete them.** Enola reports "70 more" candidates; they are claims, not findings —
verify each the same way before deleting, and expect false positives for names reached
through registries, `getattr`, or LangGraph node strings.

## 6.11 Two import spellings for the core enums (low priority)

`schemas.base` re-exports nine `filmspec` names; 274 imports use the re-export and 15
use the owner. Both spellings resolve to the same object, so they cannot diverge —
duplication of convenience under `00` §1.3. **Do not sweep.** If anything, pick
`schemas.base` as the documented spelling for schema code and stop re-exporting from
anywhere else.
