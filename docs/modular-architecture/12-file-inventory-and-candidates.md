# 12 — File inventory and relocation candidates (name-first triage)

Date: 2026-09-26. Revision: `17dcca1` (after the AGENTS.md gate update). Method:
every `.py` file under `src/film_pipeline/` was listed with its line count and its
public symbols; the **name alone** decided the first cut. Content was read only
for files whose name did not settle the question — a generic name
(`helpers`, `_shared`, `services`, `state`, `base`, `registry`), a name that
disagrees with its location, or a name suggesting a different module already
owns the concern.

This follows §3 of `11-what-to-do-next.md`: measure, pick the narrowest falsifiable
slice, let the tests enumerate the rest.

## 1. Triage rule

For each file, the name was asked three questions in order:

1. **Does the name state one concern?** (`model_adapter`, `frame_heuristics`,
   `budget` — yes. `helpers`, `_shared`, `services` — no.)
2. **Does the name match the module it lives in?** A file named for a concern
   that another module already owns is a relocation candidate regardless of size.
3. **Does the name reveal duplicated ownership?** Two files whose names describe
   the same concern (`impl/registry.py` vs `registry.py`,
   `model_adapter.py` vs `providers/`) mark a seam.

A file is **in place** when the answer to (1) is yes and to (2) and (3) is no.
Everything else is a candidate.

## 2. The census

299 `.py` files, 41,920 lines under `src/film_pipeline/`.

### 2.1 In place — settled by name, no content read (the large majority)

Names that state one concern and match their module. Representative, not
exhaustive; the whole `schemas/` tree (40 files, one record definition per file),
`filmspec/`, `budget/`, `projects/`, `post/`, `kb/`, `storage/` (except `store.py`
below), and the `_keyword`/`_quality`/`defaults` prompt files are all in this
class.

| Area | Files | Why the name settles it |
|---|---:|---|
| `schemas/**` | 40 | One Pydantic record per file, named for the record. §5 of `07` measured near-zero internal coupling; splitting would move imports and remove no coupling. |
| `filmspec/__init__.py` | 1 | Pure vocabulary; already one module. |
| `agents/impl/*_agent.py` | 15 | One agent class per file, named for the agent. |
| `agents/prompt_templates/defaults/*` | 5 | One template family per file (`spine`, `production`, `validators`). |
| `providers/adapters/*` | 4 | One provider per file, named for the provider. |
| `validation/impl/*` | 8 | One validator per file, named for the validator. |
| `orchestration/nodes/*.py` | 8 | Named per phase node; §3 of `07` measured the node set as genuinely cohesive. |
| `mcp/tools/<domain>/` | 26 | Already decomposed by domain. |
| `checkpoints/`, `config/`, `constraints/`, `generation/`, `governance/`, `kb/`, `operations/`, `post/`, `projects/`, `budget/`, `devharness/`, `studio/` | 120 | Concern-stating names matching their module. |

### 2.2 Generic names — content read, verdict unchanged

These were read because the name does not state a concern. All are **in place**;
the generic name is a house convention (`_shared` = private sibling helpers
within one domain), not a misplacement.

| File | LOC | Verdict |
|---|---:|---|
| `orchestration/nodes/_shared.py` | 176 | In place — graph-node helpers consumed by the node set. |
| `orchestration/nodes/_context.py` | 462 | In place — **but has findings** (F-AGENT-01/05: `_AGENT_PROFILE_MAP`, `_get_template_registry`). Surface problem, not a move. |
| `orchestration/services.py` | 157 | In place — `GraphServices` is the node dependency bundle. 19 fan-in. |
| `mcp/tools/helpers.py` | 268 | In place — after `ee465cc` it is the single active-project helper. |
| `mcp/tools/bibles/_shared.py` | 149 | In place by location — **but an F-AGENT-04 owner** (see §3.2). |
| `governance/validators/_shared.py` | 66 | In place. |
| `agents/impl/_model_output.py` | 41 | In place — shared parsing for the bible agents (audit `04` §5 calls it clean). |
| `agents/prompt_templates/defaults/_quality.py` | 26 | In place. |
| `orchestration/nodes/_*.py` (10 private helpers) | ~1,100 | In place — each is a named sub-concern of one node family. |
| `mcp/tools/reference_generation/*.py` (7) | ~1,000 | In place — already a decomposed sub-domain. |
| `cli/io.py`, `cli/driver.py` | 325 | In place — CLI input and headless driver are separate concerns. |
| `operations/models.py`, `operations/ports.py`, `operations/errors.py` | ~460 | In place — view models, ports, and errors are three concerns. |

### 2.3 Candidates — 14 files

Ordered by value per unit of risk. Sources: `07` §§2,4,7; audit `04` findings
F-AGENT-01…13; audit `14` (module boundaries).

| # | Candidate | LOC at `17dcca1` | Finding | Verdict |
|---|---|---:|---|---|
| **C-01** | `agents/model_adapter.py` | 383 → **290** | `07` §4 | **DONE** (`f55a23a`) — split into `agents/transports/{gemini,zai,chat_completions}.py`; dispatch pinned by a test. |
| **C-02** | `agents/impl/registry.py` | 36 | F-AGENT-02/06/10 | **DONE** (`9b0cfc0`) — collapsed into `agents/registry.py`; the roster now carries `produces`, so every row matches what its `execute()` returns (11 rows then, 15 after C-07). |
| **C-03** | `agents/model_routing/__init__.py` | 161 | F-AGENT-01, F-CFG-01 | **Open** — `_FALLBACK_PROFILES` is byte-identical to `profiles/base.studio.yaml`'s `model_profiles` (measured: same 8 keys, same values). A pure duplicate; delete it and read the profile file. |
| **C-04** | `agents/mvp/__init__.py` | 170 | F-AGENT-01/02/03/10 | **DONE** (`dda3afb`) — relocated to `agents/roster.py`, which is what it is. That file is now 266 lines, having gained the four bible rows. |
| **C-05** | `agents/runner.py` | 471 → **447** | F-AGENT-06/07 | **Open** — `RCTCOPrompt` remains renderer 1 of 4 (F-AGENT-06). The 24-line drop is C-06 deleting `create_handoff` from the same file. |
| **C-06** | `agents/handoff.py` | 51 | F-AGENT-02 | **DONE** (`12263f8`) — deleted with `PromptRunner.create_handoff`; both unreachable. |
| **C-07** | `mcp/tools/bibles/*` (7) | 1,181 → **840** | F-AGENT-04 (**Critical**) | **DONE** (`7d27083`, `42f8d7a`, `39cb402`) — one agent path. The `model_router.resolve` and `isinstance(raw, dict)` defects are gone; real-model mode verified working. (765 after `39cb402`; 840 after the review fixes added identity stamping and message handling.) |
| **C-08** | `agents/impl/*_bible_agent.py` (4) | 330 | F-AGENT-04 | **DONE** with C-07 — the four are on the roster with classes, templates, and mocks. |
| **C-09** | `studio/runtime.py` | 461 | `07` §2, F-RUNTIME-01 | **Open** — `11` §3 deliberately defers it until consumers move. |
| **C-10** | `storage/store.py` | 832 | `07` §7 | **Do not split the class.** 15 public / 21 private methods, one concern. |
| **C-11** | `schemas/registries/agent_registry.py` | 28 | F-AGENT-06/10 | **DONE** (`911ff4f`) — deleted; a guard pins the single registration model. |
| **C-12** | `studio/mock_responses.py` | 435 → **532** | F-AGENT-04 | **DONE** with C-07 — it is now the only mock authority; the five per-tool copies are gone, and the four bible payloads moved in. |
| **C-13** | `orchestration/orchestrator_state.py` | 551 → **648** | `07` §3, §6.4 | **DONE** (`860e041`) — declared surface added; three real leaks found and closed. The growth is the `__all__` block and the two accessors the guards required. |
| **C-14** | `schemas/registries/*` (4) | ~140 | F-AGENT-08 | **Open** — parallel registries that nothing forces to agree. |

LOC is stated as `before` or `before → after` per row. The first number is the
`17dcca1` measurement the triage was made from; a row with an arrow has been
re-measured at HEAD. Rows whose file did not change show one number.

### Status after this round

Closed: C-01, C-02, C-04, C-06, C-07, C-08, C-11, C-12, C-13 — nine of fourteen.
Open: C-03 (a verified exact duplicate), C-05, C-09 (deferred by `11` §3),
C-14. C-10 is a recorded "do not split".

### 2.4 Explicitly not candidates

- `orchestration/` as a whole — `07` §3 measured 43 node-to-node edges dominated
  by shared infrastructure, not pairwise dependency. Splitting by phase yields
  subpackages that all import the shared trio.
- `schemas/` layout — `07` §5: 30 of 32 non-`base` internal edges originate in
  `__init__.py`. Grouping adds a directory level and changes every import path
  while removing no coupling.
- `ArtifactStore` — see C-10.

## 3. The two concerns named in the request

### 3.1 `MVP`

Measured, not assumed:

| Fact | Value |
|---|---|
| `agents/mvp/` | one `__init__.py`, 170 lines, all data |
| Its content | `MVP_AGENTS: list[AgentRegistration]` — 11 rows |
| Production consumers | 2 (`orchestration/services.py:41`, `studio/smoke.py:25`) |
| Test consumers | 11 lines across `test_registry.py`, `test_mvp_invariants.py` |

So "MVP" is **not a module** — it is a roster constant sitting in a package that
implies more. The real seam it hides is F-AGENT-02: the roster's declared
`output_artifacts` disagree with what the bound implementation returns for 10 of
11 agents, and the field has **zero** production readers, so nothing catches it.

### 3.2 `model_adapter`

Measured:

| Fact | Value |
|---|---|
| `agents/model_adapter.py` | 383 lines, `ModelAdapter` 264 of them |
| Provider-specific methods | 6 across 3 transports (`_gemini_api_key`/`_call_gemini_api`/`_gemini_url`, `_zai_api_key`/`_zai_base_url`/`_zai_request`) |
| Transport already extracted | yes — `providers/http_transport.post_json` |
| Remaining concern | request shaping, key resolution, payload/response mapping |
| Consumers | `agents/runner.py`, `orchestration/services.py`, 2 MCP bible modules, `validation/base.py` (annotations), tests |

`07` §4 calls this "the highest-confidence split in this document". The target
architecture (`03` §3.10) already names it: `model_adapter.py:36` should drop the
concrete-adapter import.

## 4. What this document does not establish

- The 2.1 table is a **name-based triage**, not a read of those files. A file
  whose name is accurate can still hold a seam; this census cannot see that, and
  does not claim to.
- The candidate order is by value per unit of risk as `07` assessed it, not by a
  fresh measurement of effort.
- No candidate here has been re-verified against the source at `17dcca1` beyond
  the content actually read for §2.2 and §3. Audit `04`'s findings were taken as
  prior art; its anchors were recorded at `fb85baa` and line numbers drift.
