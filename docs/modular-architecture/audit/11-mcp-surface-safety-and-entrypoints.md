# 11 — MCP Surface, Safety Policy, and Entry Points

Status: **audit artifact**, conforms to `docs/modular-architecture/00-methodology-and-quality-bar.md`
(quality bar A). Cluster: MCP tool contracts, confirmation/mutation/checkpoint policy,
argument contracts, safety guards, and entry-point wiring.

**Audited commit:** `fb85baa0e6b769b709791a96a89980089304bf13` (branch `modular-app`,
merge of the storage upgrade — the recorded baseline of §5 of the methodology).

**Working-tree caveat (recorded, not folded into findings).** During this audit the
worktree contained *uncommitted* work by another agent: `src/film_pipeline/architecture.py`
and `tests/architecture/` are untracked, and 17 package `__init__.py` files are modified
(`git status --porcelain`). None of those paths exist at HEAD:

```
$ git cat-file -e HEAD:src/film_pipeline/architecture.py
fatal: path 'src/film_pipeline/architecture.py' exists on disk, but not in 'HEAD'
$ git cat-file -e HEAD:tests/architecture/_harness.py
fatal: path 'tests/architecture/_harness.py' exists on disk, but not in 'HEAD'
```

Every anchor below is verified against the HEAD blob (`git show HEAD:<path>`), and the
substantive files read here are unmodified in the worktree (only `__init__.py` files and
the two untracked trees differ). The in-flight `architecture.py` declarations are cited
only in "Prior art / precedent", never as enforcement that exists at HEAD.

**Verification status.** This file was independently verified against the same commit
(`docs/modular-architecture/reviews/verify-11.md`): **10 CONFIRMED, 2 DOWNGRADED, 0 REJECTED**. Applied here:
F-MCP-05 downgraded Critical→High and F-MCP-06 High→Medium (recomputed in place);
F-MCP-04's score corrected 20→16 and its mutation anchor fixed; the disputes in
`docs/modular-architecture/reviews/verify-11.md` §"Disputes" folded in (F-MCP-01 wording, F-MCP-09 anchors/collision,
F-MCP-11 stub counts, F-MCP-12 class/count); and the five adjacent MCP-surface seams the
first pass missed are now recorded (four consolidated into the new §4.1 findings
F-MCP-13…F-MCP-15, and the ungated `set_active_project` folded into F-MCP-11).

**Post-verification correction (round 3).** A later adversarial evidence replay
(`docs/modular-architecture/reviews/adversarial-evidence.md`) surfaced a second
`project_kind` writer that the verification pass had missed. **F-MCP-06's class is
therefore corrected from O6-only back to O3 + O6** at the same arithmetic
(2 × 4 = 8, Medium); its one-writer premise is formally withdrawn in that finding. No
other finding's class, severity, drift proof or verdict was changed.

Measured registry facts at HEAD (separately re-measured mechanically with `make_registry()`):
**77 tools, 10 `confirm=True`, 32 `mutates=True`, 1 `checkpoint=True`, 0/77 non-empty
`input_schema`, 0/77 non-empty `output_schema`, 0/77 `idempotency_key_field` populated.**

---

## 1. Coverage

All MCP-surface modules at HEAD, with verdict. "Contract flags" means the
`mutates_state` / `requires_confirmation` / `creates_checkpoint` triple.

### 1.1 Core surface (`src/film_pipeline/mcp/`)

| Module | Lines | Verdict |
|---|---|---|
| `mcp/contract.py` | 127 | **has findings** (F-MCP-03, F-MCP-08, F-MCP-15): owns `ToolContract` (45‑57) and `ToolRegistry.register` (80‑83); `input_schema`/`output_schema` declared (52‑53) and never populated; `idempotency_key_field` (57) declared and never set. Single source of truth for the *populated* contract flags. |
| `mcp/errors.py` | 54 | **has findings** (F-MCP-10, F-MCP-13): `MCPErrorCode` (9‑22) is the only typed taxonomy; 77 handlers never use it and the transport discards it. |
| `mcp/envelope.py` | 48 | **has findings** (F-MCP-08, F-MCP-13): `RequestEnvelope.requires_confirmation` (28) is dead duplicate normative state; `actor_id`/`actor_type` (29‑30) are never populated by the only transport. |
| `mcp/resolution.py` | 113 | **has findings** (F-MCP-07): `ProjectRegistry` is a second project registry, independent of `StudioRuntime.projects`. |
| `mcp/server.py` | 270 | **has findings** (F-MCP-01, F-MCP-02, F-MCP-07, F-MCP-09, F-MCP-14): single dispatch + confirmation gate; `main()` (234‑257) re-derives bootstrap/persistence; `active_project_id` (44) is a write-only second active-project state. |
| `mcp/_stdio_transport.py` | 167 | **has findings** (F-MCP-02, F-MCP-03, F-MCP-13): canonical invocation path `server.call` (61) — but calls it with no actor; emits `inputSchema` from the empty contract (35‑42); flattens every typed error to `-32000` (62‑65). |
| `mcp/__init__.py` | 42 (@HEAD) | clean facade (re-exports), no policy. |

### 1.2 Tool modules (`mcp/tools/`)

| Module | Lines | Verdict |
|---|---|---|
| `tools/registry.py` | 387 | **has findings** (all contract findings): the sole registrar — 77 `_register(...)` calls, 32 `mutates=True`, 10 `confirm=True`, 1 `checkpoint=True`. No tool module constructs a contract. |
| `tools/helpers.py` | 223 | **has findings** (F-MCP-03): `_ok`/`_error` untyped dict responses (28‑35) and ad-hoc arg coercion `_coerce_runtime_arg` (76‑98). |
| `tools/projects.py` | 295 | **has findings** (F-MCP-03, F-MCP-06): `create_film_project` (152) re-parses `args` and never sets `project_kind` (96‑124). |
| `tools/review.py` | 165 | **has findings** (F-MCP-06): `approve_phase` (146), `request_revision` (155) call the runtime directly; confirmation comes only from the registry/server. |
| `tools/checkpoints.py` | 331 | **has findings** (F-MCP-01): rollback handlers *re-enforce* `confirmed` (249‑254, 294‑301) with a different response shape. |
| `tools/_profile_change.py` | 473 | **has findings** (F-MCP-01): docstring at 101 claims `confirmed=True` is required; the body never reads it. |
| `tools/validation.py` | 374 | **has findings** (F-MCP-04): own `_live_validator_specs` phase→validator table (123‑158), plus hard-coded `version=1` report save (191). |
| `tools/generation/planning.py` | 203 | **has findings** (F-MCP-05): hard-coded provider/model defaults (75‑76); delegates `preview_generation_prompts` to `OperatorService` (140). |
| `tools/generation/_text_only.py` | 119 | **has findings** (F-MCP-05): second text-only policy implementation (12‑13, 100‑119). |
| `tools/generation/dispatch.py` | 305 | **has findings** (F-MCP-05): reads text-only policy (125); direct ledger writes, bypassing `GenerationExecutor`. |
| `tools/generation/status.py` | 67 | clean reads over `GenerationLedgerManager`. |
| `tools/generation/promote.py` | 35 | **has findings** (F-MCP-06-adjacent): mutates ledger mode with `confirm=True` in registry (285) but no handler check; relies on server gate. |
| `tools/generation/__init__.py` | 42 | clean facade. |
| `tools/bibles/_shared.py` | 149 | **has findings** (F-MCP-12): own artifact versioning + prompt-runner call (101‑107, 110‑139). |
| `tools/bibles/camera.py` | 124 | **has findings** (F-MCP-12): instantiates `CameraBibleAgent` (64‑78), writes `visual_dev` artifact (84‑99). |
| `tools/bibles/character.py` | 258 | **has findings** (F-MCP-12): instantiates `CharacterBibleAgent` (163). |
| `tools/bibles/environment.py` | 239 | **has findings** (F-MCP-12): instantiates `EnvironmentBibleAgent` (142). |
| `tools/bibles/shot.py` | 250 | **has findings** (F-MCP-12): instantiates `ShotBibleAgent` (13, 132). |
| `tools/bibles/style.py` | 123 | **has findings** (F-MCP-12): instantiates `StyleBibleAgent` (59). |
| `tools/bibles/__init__.py` | 22 | clean facade. |
| `tools/reference_generation/tool.py` | 213 | **has findings** (F-MCP-12-adjacent): writes/rewrites the reference index directly (50‑61); selects provider adapter directly (`src/film_pipeline/mcp/tools/reference_generation/index_files.py:62‑67`). |
| `tools/reference_generation/{composites,context,entries,index_files,outcomes,retry_loop}.py` | 239/149/111/123/218/226 | helper modules, no contract/confirmation policy of their own; must not become a fourth policy owner. |
| `tools/assembly.py` | 76 | **has findings** (F-MCP-11, F-MCP-12): all 4 coverage tools are `_stub` no-ops, but only 2 are mutating — `plan_coverage_group` (`mutates=True`, no confirm) and `approve_coverage_generation` (`mutates=True` + `confirm=True`) at `src/film_pipeline/mcp/tools/registry.py:358-370`; `list_coverage_groups`/`inspect_coverage_group` are read-only. `assemble_review_cut` instantiates `AssemblyAgent` (37‑46). |
| `tools/planning.py` | 250 | **has findings** (F-MCP-12-adjacent): own `_save_gen_planning_candidate`/`_register_active_artifact_ref` write path (60‑99), independent of `_shared`'s copy. |
| `tools/artifacts.py` | 196 | clean reads; `version=`/`phase=` re-parsed per tool (57‑73). |
| `tools/state.py` | 90 | clean: `get_blockers` (76‑90) delegates to `graph.router.get_blockers_for_state`. |
| `tools/kb.py` | 116 | clean reads. `kb_search` accepts `query` but ignores it (30, 43‑45). |
| `tools/audit.py` | 75 | clean reads; `explain_kb_context` is a static string (71‑75). |
| `tools/config.py` | 102 | clean reads; re-exports `_profile_change` tools. |
| `tools/providers.py` | 53 | **has findings** (F-MCP-11): `resolve_provider_block` clears a block with no confirmation (27‑33). |
| `tools/operator.py` | 65 | **has findings** (F-MCP-06-adjacent): duplicates `OperatorService.add_operator_comment`/`list_operator_comments` (10, 53) with a different validation path (`source` default `"mcp"` vs `"operator"`). |
| `tools/intake.py` | 79 | **has findings** (F-MCP-06-adjacent): `approve_intake` (67) and `submit_idea` (25) re-implement `OperatorService.approve_phase`/`submit_idea` sequencing. |

### 1.3 Entry points and build surface

| Entry | Verdict |
|---|---|
| `cli/run.py:main` (208) + `cli/driver.py` | **has findings** (F-MCP-02, F-MCP-09): no `validate_environment`; `_call_tool` (199‑206) bypasses `MCPServer.call`. |
| `mcp/server.py:main` (234) | **has findings** (F-MCP-09). |
| `app/product_gate.py:main` (139) | **has findings** (F-MCP-10): consumes `make_registry()` and inspects handler source for `"_stub("` (130‑136) — a string-matching policy over the tool surface. |
| `langgraph.json` | **has findings** (F-MCP-09): a 4th entry (`./src/film_pipeline/graph/graph.py:graph`) that never builds `MCPServer` or runs bootstrap. |
| `app/bootstrap.py`, `app/runtime.py`, `app/_persistence.py`, `app/logging_setup.py`, `app/health.py`, `app/smoke.py` | **has findings** (F-MCP-09); `app/safety.py` is clean single-owner (see §5). |
| `scripts/*.py` | **has findings** (F-MCP-02): 2 scripts re-implement direct tool invocation; `scripts/test-full-pipeline.py` is the only script that drives the real stdio transport. |
| `Makefile` | clean: `run-mcp*` targets go through `python -m film_pipeline.mcp.server` (only canonical stdio path); `product-gate` runs `app.product_gate`. |

Counts (mechanically reproducible):

```
$ grep -c "mutates=True" src/film_pipeline/mcp/tools/registry.py   # 32
$ grep -c "confirm=True"  src/film_pipeline/mcp/tools/registry.py   # 10
$ grep -c "checkpoint=True" src/film_pipeline/mcp/tools/registry.py # 1
$ .venv/bin/python -c "from film_pipeline.mcp.contract import make_registry; r=make_registry(); \
  print(len(r.all_names()), sum(1 for n in r.all_names() if r.get(n).contract.requires_confirmation))"
# 77 10
```

---

## 2. Contract authority table

| Policy / concern | Defining site (N) | Enforcing site(s) (I) | Single / distributed |
|---|---|---|---|
| Tool identity + flags (`name`, `description`, `group`, `mutates_state`, `requires_confirmation`, `creates_checkpoint`, `idempotency_key_field`) | `src/film_pipeline/mcp/contract.py:45-57` — the dataclass; `src/film_pipeline/mcp/tools/registry.py:101-117` — `_tool_contract` builds every instance | `src/film_pipeline/mcp/tools/registry.py:137-384` (77 `_register` calls); `src/film_pipeline/mcp/server.py:120,156` (mutates ⇒ set active project); `src/film_pipeline/mcp/server.py:187` (confirm) | **Single for the enforced flags.** `grep -rn "ToolContract" src/` matches only `mcp/contract.py`, `mcp/tools/registry.py`, `mcp/__init__.py`. **One flag is dead:** `idempotency_key_field` is declared and echoed in the catalog (`src/film_pipeline/mcp/contract.py:110`) but set by no tool (0/77) and read by nothing — F-MCP-15. |
| Confirmation requirement (which tools) | `src/film_pipeline/mcp/tools/registry.py:151,169,178,254,285,306,314,354,369,383` — 10 `confirm=True` sites | `src/film_pipeline/mcp/server.py:187-199` **and** `src/film_pipeline/mcp/tools/checkpoints.py:249-254,294-301` | **Distributed (O2).** Two enforcing sites, divergent response contract. |
| Checkpoint-creation policy | `src/film_pipeline/mcp/tools/registry.py:170` — `checkpoint=True` is set only for `approve_phase` | nothing reads `creates_checkpoint` except the catalog (`src/film_pipeline/mcp/contract.py:109`); `grep -rn "creates_checkpoint" src/` shows dataclass + catalog only | **Declared, not enforced anywhere.** |
| Mutation ⇒ active-project selection | `mcp/tools/registry.py` `mutates=True` (32 tools) | `src/film_pipeline/mcp/server.py:120-121`, `src/film_pipeline/mcp/server.py:156-157` | Single (`server.py`). |
| Argument contract / JSON schema | `src/film_pipeline/mcp/contract.py:52-53` — `input_schema`/`output_schema` fields | **none** — `_tool_contract` (`src/film_pipeline/mcp/tools/registry.py:110-117`) never passes them; catalog emits `{}` (`src/film_pipeline/mcp/contract.py:111-112`); transport advertises `inputSchema: {}` (`src/film_pipeline/mcp/_stdio_transport.py:39`) | **Missing (O8).** Required args re-parsed per handler, e.g. `src/film_pipeline/mcp/tools/helpers.py:76-98`, `src/film_pipeline/mcp/tools/projects.py:159-161`. |
| Error-code taxonomy | `src/film_pipeline/mcp/errors.py:9-22` — `MCPErrorCode` | `mcp/server.py` only (UNKNOWN_TOOL, AMBIGUOUS_PROJECT, UNKNOWN_PROJECT, CONFIRMATION_REQUIRED, INTERNAL_ERROR). `grep -rn "MCPErrorCode\." src/` matches only `mcp/server.py`, `mcp/__init__.py`, `mcp/errors.py`; handlers return `_error(...)` dicts (`src/film_pipeline/mcp/tools/helpers.py:33-35`) | **Distributed (O8).** Tools are outside the taxonomy. |
| Error representation over the wire | `src/film_pipeline/mcp/errors.py:9-22` — the `MCPError.code` value | `src/film_pipeline/mcp/_stdio_transport.py:62-65` maps every failed call to JSON-RPC `-32000` + `message`; the typed code is never serialized | **Erased (O8).** `-32000` is indistinguishable across `UNKNOWN_TOOL` / `CONFIRMATION_REQUIRED` / `BUDGET_EXCEEDED` — F-MCP-13. |
| Active-project state | `src/film_pipeline/app/runtime.py:207-213` — `StudioRuntime.active_project_id` (read by every tool via `src/film_pipeline/mcp/tools/helpers.py:38-52`) | `src/film_pipeline/mcp/server.py:121,157,230-231` writes `MCPServer.active_project_id`, which no `src/` reader consumes | **Split (O3/O1).** A second, write-only active-project slot — F-MCP-14. |
| Project-reference resolution | `src/film_pipeline/mcp/resolution.py:45-113` — `ProjectRegistry.resolve_or_raise` | `src/film_pipeline/mcp/server.py:101-122` (canonical) + `src/film_pipeline/mcp/server.py:142-177` (fallback into `StudioRuntime.projects`) | **Distributed (O4).** Two registries, reconciled lazily. |
| Destructive-delete safety | `src/film_pipeline/app/safety.py:58-132` — `is_safe_to_delete`, `can_delete_project` | `src/film_pipeline/app/runtime.py:150,161-169` (`delete_project`) — and **no MCP tool exposes delete** (`grep -rn "delete_project" src/` → runtime + safety only) | Single owner, **unreachable from the product boundary**. |
| "This mutation is dangerous" classification | **no defining site** | only per-tool `confirm=True` literals (registry) | **Missing (O5).** `resolve_provider_block` mutates safety-relevant state with no gate (`src/film_pipeline/mcp/tools/providers.py:27-33`). |
| Runtime persistence enablement | `src/film_pipeline/app/_persistence.py:45-53` — `use_persistent_runtime`, `configured_runtime_root` | `src/film_pipeline/app/runtime.py:61`, `src/film_pipeline/app/logging_setup.py:80-81`, `src/film_pipeline/graph/graph.py:43`, `src/film_pipeline/graph/services.py:31,48`, `src/film_pipeline/mcp/server.py:243-244`, `src/film_pipeline/cli/run.py:226` | **Distributed (O5).** Entry points read/set the env flags directly. |

---

## 3. OperatorService vs MCP divergence table

Scope note (verified): at HEAD the **only production caller of `OperatorService`** is
`src/film_pipeline/mcp/tools/generation/planning.py:140`. The prior audit's `InProcessStudioGateway`/TUI
consumer does not exist at HEAD (`git ls-tree HEAD src/film_pipeline/` lists no `tui`;
`git grep InProcessStudioGateway HEAD -- src/ tests/` is empty). `OperatorService` is
nonetheless a full second lifecycle with 37 tests in
`tests/unit/app/services/test_operator_service.py`.

| # | Concern | MCP path (canonical) | `OperatorService` path | Divergence |
|---|---|---|---|---|
| D1 | Phase approval confirmation | `src/film_pipeline/mcp/tools/registry.py:163-171` `confirm=True`; enforcement `src/film_pipeline/mcp/server.py:187` | `src/film_pipeline/app/services/operator.py:318-328` — `self.runtime.approve_phase()` at 322, **no `confirmed` parameter** | Operator can approve a gate that the product boundary refuses without confirmation. |
| D2 | Revision confirmation | `src/film_pipeline/mcp/tools/registry.py:172-179` `confirm=True` | `src/film_pipeline/app/services/operator.py:330-342` — no `confirmed` parameter | Same. |
| D3 | Spend approval confirmation | `src/film_pipeline/mcp/tools/registry.py:248-255` `confirm=True` | `src/film_pipeline/app/services/operator.py:354-360` → `src/film_pipeline/app/services/_generation_ops.py:70-86` `executor.approve_spend(...)` | Real-money approval with no confirmation gate. |
| D4 | Project kind (feeds delete safety) | `src/film_pipeline/mcp/tools/projects.py:152-203`; `_populate_project_state` (`96-124`) sets `runtime_mode`, `profile_stack`, `server_mode`, `resolved_config`, `resolved_config_sources`, `config_conflicts`, `generation_policy`, `target_runtime_seconds` — **no `project_kind`** | **Two writers with different rules.** `src/film_pipeline/app/services/operator.py:119-127`: `state["project_kind"] = normalize_project_kind(request.project_kind)` (caller-validated, default `"production"`, `src/film_pipeline/app/services/models.py:19`); `src/film_pipeline/app/services/_project_discovery.py:55`: `state["project_kind"] = project_kind_for_name(project_id)` (folder-name heuristic, `:68-71`), reached from `src/film_pipeline/app/services/operator.py:438` `_require_project` → `load_discovered_project` | `can_delete_project` (`src/film_pipeline/app/safety.py:131-132`) reads the raw key and returns True for kind `""`/`"test"`: the *same* project is deletable when created via MCP (no key at all) and protected when created via the operator, and the two operator-side writers can classify the same folder differently. |
| D5 | Project resolution / actor | envelope (`src/film_pipeline/mcp/server.py:55-59`, `resolution.py`) resolves `project_ref`; `actor_id`/`actor_type` carried on the envelope | `src/film_pipeline/app/services/operator.py:427-441` `_state_for_project` / `_require_project`: explicit id or process-global `runtime.get_active()` | No envelope, no actor attribution on operator mutations. |
| D6 | Response representation | `_ok(...)`/`_error(...)` dicts (`src/film_pipeline/mcp/tools/helpers.py:28-35`) | frozen dataclasses (`MutationResult`, `DashboardSummary`, … `src/film_pipeline/app/services/models.py:9-174`) | Two output contracts for the same use cases. |
| D7 | Generation planning defaults | `src/film_pipeline/mcp/tools/generation/planning.py:75-76`: `args.get("provider", "mock-video-provider")`, `args.get("model", "mock-fast")` | `src/film_pipeline/app/services/_generation_ops.py:61`: `svc.runtime.default_video_provider()` | Identical request can plan different providers. |
| D8 | Text-only generation policy | `src/film_pipeline/mcp/tools/generation/_text_only.py:12-13`, `100-119` | `src/film_pipeline/app/services/_generation_ops.py:20`, `208-209`, `212-237` | Two implementations of the same policy + two copies of the stale-issue code set. |
| D9 | On-demand validation | `src/film_pipeline/mcp/tools/validation.py:280-308` + `_live_validator_specs` (`123-158`) | `src/film_pipeline/app/services/operator.py:310-316` → `runtime.run_validation` → `src/film_pipeline/graph/nodes/qc.py:115` / `_VALIDATOR_RUNNERS` (`361-368`) | Two dispatch tables (also F-MCP-04). |
| D10 | Comment source tag | `src/film_pipeline/mcp/tools/operator.py:21`: `source = str(args.get("source", "mcp"))` | `src/film_pipeline/app/services/_browse_ops.py:39`: `request.source.strip() or "operator"` | Same stored record, different provenance value. |

---

## 4. Findings

### F-MCP-01 — Confirmation is enforced at two sites with two different contracts, and one tool documents enforcement it does not implement
- **Class:** O2
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** Which module decides that a tool call is refused without `confirmed` — and what the refusal looks like.
- **De-facto owners:**
  - `src/film_pipeline/mcp/server.py:187` — the single dispatch gate, emitting a typed error — `"if registration.contract.requires_confirmation and not arguments.get(\"confirmed\"):"`
  - `src/film_pipeline/mcp/server.py:192` — the typed code — `"code=MCPErrorCode.CONFIRMATION_REQUIRED,"`
  - `src/film_pipeline/mcp/tools/checkpoints.py:249` — second enforcement inside the handler — `"confirmed = bool(args.get(\"confirmed\"))"`
  - `src/film_pipeline/mcp/tools/checkpoints.py:251` — different, untyped refusal — `"return _error("`
  - `src/film_pipeline/mcp/tools/_profile_change.py:101` — a documented but absent enforcement — ``"Requires ``confirmed=True``. Bumps ``profile_version``, re-resolves the"``
- **Drift proof:** existing divergence. For the same semantic condition, `server.py` returns `MCPResponse(success=False, error=MCPError(...CONFIRMATION_REQUIRED))`, while `src/film_pipeline/mcp/tools/checkpoints.py:251-254` returns `{"ok": False, "error": "Rollback requires confirmation…"}` inside a *successful* `MCPResponse`. **Reachability caveat (added after verification):** the canonical path never sees the handler copy — `src/film_pipeline/mcp/server.py:64-66` returns the refusal before `_dispatch_handler` at `:67` — so the two contracts diverge only on the F-MCP-02 bypass paths (CLI driver and scripts), where the handler copy is the *only* gate and it returns a different shape. Mutation scenario: change the server message/code at `src/film_pipeline/mcp/server.py:192-196`; `src/film_pipeline/mcp/tools/checkpoints.py:251` keeps the old wording and `tests/unit/mcp/tools/test_checkpoints.py:122-142` (which calls the handler directly) still passes, while `tests/unit/test_mcp.py:282-289` (server-level) exercises only the server copy. `grep -rn "MCPErrorCode\." src/film_pipeline/mcp/tools/` returns nothing.
- **Reproduce:** `grep -rn "confirmed" src/film_pipeline/mcp/ ; grep -rn "MCPErrorCode\." src/film_pipeline/mcp/tools/`
- **Blast radius:** `mcp/server.py`, `mcp/tools/checkpoints.py`, `mcp/tools/_profile_change.py`; an agent that calls rollback directly (all non-transport paths, F-MCP-02) gets an untyped `ok:false` instead of a machine-readable code. **Corrected after verification:** `approve_profile_change`'s confirmation *is* enforced at the product boundary (`src/film_pipeline/mcp/tools/registry.py:348-354` `confirm=True` + `src/film_pipeline/mcp/server.py:187`); `src/film_pipeline/mcp/tools/_profile_change.py:101` is imprecise about *which layer* enforces it (its body does not), not a tool whose gate the boundary lacks.
- **Candidate owner module:** `mcp.policy` — single `authorize(registration, arguments) -> MCPError | None`.
- **Extraction sketch:** move both checks into one `authorize()` invoked by `server.call` and by every direct-invocation helper; delete `src/film_pipeline/mcp/tools/checkpoints.py:249-301` re-checks; make the error code the only refusal shape. Guard test: for the 10 confirm-gated tool names, call each handler directly with `{}` and assert a `CONFIRMATION_REQUIRED`-coded refusal.
- **Prior art:** `documentation/audit-findings.md:40` claimed `requires_confirmation` was *never* enforced; at HEAD `src/film_pipeline/mcp/server.py:187` enforces it — new is that enforcement is now split across two sites (the second reachable only off the canonical path) and one docstring misstates which layer enforces it.

### F-MCP-02 — Tool invocation has four implementations; only the stdio transport applies the confirmation gate and project resolution
- **Class:** O6
- **Severity:** Critical (impact 5 × drift 4 = 20)
- **Concern:** The single path from "tool name + arguments" to a handler invocation, with its safety middleware.
- **De-facto owners:**
  - `src/film_pipeline/mcp/_stdio_transport.py:61` — canonical: `"tool_response = await server.call(tool_name, arguments)"`
  - `src/film_pipeline/cli/driver.py:199-206` — bypass — `"mod = importlib.import_module(\"film_pipeline.mcp.tools\")"` … `"result: dict[str, Any] = await handler(dict(args))"`
  - `scripts/test_real_mcp_operator.py:36-46` — bypass — `"handler = getattr(mod, tool_name, None)"` … `"return await handler(dict(args))"`
  - `scripts/e2e-real-auto-approve.py:37-51` — bypass — `"handler = getattr(mod, tool_name, None)"` … `"result = await handler(dict(args))"`
  - `scripts/test_real_mcp_operator.py:205` — **live bypass, confirm-gated tool with no `confirmed`** — `"r = invoke_tool(rt, \"approve_intake\")"`
  - `scripts/e2e-real-auto-approve.py:134,153,154` — **live bypass** — `"r = invoke_tool(rt, \"approve_phase\")"` / `"invoke_tool(rt, \"request_revision\")"` / `"r = invoke_tool(rt, \"approve_phase\")"`
- **Drift proof:** existing divergence, **and the bypass is live, not merely structural** (added after verification). `src/film_pipeline/mcp/server.py:64` calls `_check_confirmation`; `src/film_pipeline/cli/driver.py:199-206` and both scripts never construct an `MCPServer`, so `src/film_pipeline/mcp/server.py:187` never runs. `git grep -n "_check_confirmation" HEAD -- src/` matches only `mcp/server.py`. The scripts then exercise confirm-gated tools through that hole: `approve_intake` (`src/film_pipeline/mcp/tools/registry.py:151` `confirm=True`, and it is the only gate between intake and the pipeline), `approve_phase` (`src/film_pipeline/mcp/tools/registry.py:163-171`), and `request_revision` (`src/film_pipeline/mcp/tools/registry.py:172-179`) are each invoked with no `confirmed` argument — and no handler self-checks, so the calls *succeed*. Handler-side `confirmed` reads exist nowhere but `src/film_pipeline/mcp/tools/checkpoints.py:249,294`; `git grep -n "confirmed" HEAD -- src/film_pipeline/mcp/tools/` otherwise matches only the `src/film_pipeline/mcp/tools/_profile_change.py:101` docstring. Mutation scenario: add `confirm=True` to a new destructive tool in `registry.py`; the driver/scripts invoke the handler by name and the new gate is silently skipped — `tests/` exercises the scripts out-of-band and `cli/driver.py` has no test that asserts a confirmation refusal.
- **Reproduce:** `grep -rn "import_module(\"film_pipeline.mcp.tools\")" src/ scripts/ ; grep -rn "invoke_tool(rt, \"approve_intake\"\|invoke_tool(rt, \"approve_phase\"\|invoke_tool(rt, \"request_revision\"" scripts/`
- **Blast radius:** `cli/driver.py`, `scripts/*`, plus any future embedder; the headless and real-provider scripts can mutate/spend without the product boundary's gate.
- **Candidate owner module:** `mcp.dispatch` — one `invoke_tool(name, args, *, actor) -> MCPResponse` used by transport, CLI driver, and scripts.
- **Extraction sketch:** replace the three `importlib + getattr + handler(...)` copies with one call into `MCPServer.call` (or a shared `invoke_tool`); `cli/driver.py` keeps its explicit `confirmed=True` for its auto-approval role. Guard test: assert no module outside `mcp/` imports `film_pipeline.mcp.tools` handlers by `getattr`.
- **Prior art:** new (prior audit noted the TUI bypass; that consumer is gone and the bypass now lives in the CLI driver and scripts).

### F-MCP-03 — Tool argument contracts are declared and never populated: every tool advertises `inputSchema: {}` and re-parses raw dicts
- **Class:** O8
- **Severity:** Critical (impact 4 × drift 4 = 16)
- **Concern:** The typed argument contract of each tool (required fields, types, and the `confirmed` flag an LLM caller must send).
- **De-facto owners:**
  - `src/film_pipeline/mcp/contract.py:52-53` — declared fields — `"input_schema: dict[str, Any] = field(default_factory=dict)"` / `"output_schema: dict[str, Any] = field(default_factory=dict)"`
  - `src/film_pipeline/mcp/tools/registry.py:110-117` — the sole constructor never sets them — `"return ToolContract("` … `"requires_confirmation=confirm,"` (no `input_schema=`)
  - `src/film_pipeline/mcp/_stdio_transport.py:39` — what the product boundary actually publishes — `"\"inputSchema\": item[\"input_schema\"],"`
  - `src/film_pipeline/mcp/tools/helpers.py:82-98` — per-tool ad-hoc parsing — `"raw_seconds = args.get(\"target_runtime_seconds\")"` … `"minutes = float(str(raw_minutes))"`
  - `src/film_pipeline/mcp/tools/projects.py:159-161` — a required field validated nowhere but here — `"project_id = str(args.get(\"project_id\", \"\"))"`
- **Drift proof:** existing divergence and a dead declaration. `grep -rn "input_schema" src/film_pipeline/mcp/` matches the dataclass, the catalog echo, and the transport — never a producer. Mutation scenario: make `confirmed` mandatory for a tool, or add a required argument; the catalog output is byte-identical (`{}`), so no test fails and the caller has no way to learn the field. Concretely, the 10 confirm-gated tools are undiscoverable: a caller reading `tools/list` sees no `confirmed` parameter and only learns of it from an error string (`src/film_pipeline/mcp/server.py:195`).
- **Reproduce:** `grep -rn "input_schema\|output_schema" src/film_pipeline/mcp/`
- **Blast radius:** `mcp/contract.py`, `mcp/tools/registry.py`, `mcp/_stdio_transport.py`, and all 77 handlers; the MCP product boundary is untyped to its only client (an LLM).
- **Candidate owner module:** `mcp.contracts` — one table of per-tool Pydantic argument models + derived JSON Schema, shared by registration, catalog, and validation.
- **Extraction sketch:** define `ToolArgs(BaseModel)` per tool; `_register` accepts `args_model=` and derives `input_schema=model.model_json_schema()`; `server.call` validates before `_check_confirmation`; handlers consume the validated model rather than `args.get`. Guard test: assert every registered tool has a non-empty `input_schema` whose properties include `confirmed` iff `requires_confirmation`.
- **Prior art:** `documentation/audit-findings.md:46` ("Tool descriptions are auto-generated and useless to LLM callers", `src/film_pipeline/mcp/tools/registry.py:112` `description=f"MCP tool: {name}"`); the schema gap is new.

### F-MCP-04 — Two independent phase→validator dispatch tables govern the same validation decision
- **Class:** O2
- **Severity:** Critical (impact 4 × drift 4 = 16; score corrected from 20 after verification)
- **Concern:** Which validators run for a given film phase and in what order.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/validation.py:123-158` — MCP table `_live_validator_specs` — `"phases=(\"script\",),"` … `"validators=_delivery_validators,"`
  - `src/film_pipeline/graph/nodes/qc.py:361-368` — graph table `_VALIDATOR_RUNNERS` — `"({\"script\", \"qc\"}, _run_script_validators),"` … `"({\"delivery\"}, _run_delivery_validators),"`
  - `src/film_pipeline/graph/nodes/qc.py:115` — the graph consumer `_run_validators`, reached by `src/film_pipeline/app/_graph_exec.py:319,337` under `OperatorService.run_validation`
  - `src/film_pipeline/graph/nodes/qc.py:311-328` — the *validator membership* for `shot_bible` (`_run_continuity_validators`), dispatched by the `shot_bible` arm at `src/film_pipeline/graph/nodes/qc.py:365`
- **Drift proof:** mutation scenario with silent failure. Add a validator to the `shot_bible` set by editing the membership arm `_run_continuity_validators` (`src/film_pipeline/graph/nodes/qc.py:311-328`); `src/film_pipeline/mcp/tools/validation.py:143-147` keeps the old set, so the operator's on-demand `run_validation` report and the QC gate disagree, and no test fails — `tests/unit/graph/test_qc_validator_dispatch.py:75-107` **does** pin the phase→runner sets (so a phase-set edit is caught; drift on that axis was 5, measured 4), but it does not compare validator *membership* against the MCP table, and `tests/unit/mcp/tools/test_validation.py` exercises only the MCP table's own behavior (e.g. `test_run_validation_script_phase_success` at line 61). **Anchor corrected after verification:** the earlier draft cited `src/film_pipeline/graph/nodes/qc.py:364`, which is the `gen_planning`/prompt arm; the `shot_bible` arm is `src/film_pipeline/graph/nodes/qc.py:365` and its membership lives in `_run_continuity_validators`. `grep -rn "_live_validator_specs" tests/ src/` matches only `mcp/tools/validation.py`.
- **Reproduce:** `grep -rn "_VALIDATOR_RUNNERS\|_live_validator_specs" src/ tests/`
- **Blast radius:** `mcp/tools/validation.py`, `graph/nodes/qc.py`, `graph/nodes/__init__.py`; a human reviewer sees one set of blocking issues on demand and a different set at the gate.
- **Candidate owner module:** `validation.dispatch` — one phase→validator table consumed by both the QC node and the `run_validation` tool.
- **Extraction sketch:** move `_VALIDATOR_RUNNERS`/`_live_validator_specs` into one registry keyed by `FilmPhase`; `mcp/tools/validation.py` and `graph/nodes/qc.py` both read it. Guard test: one test that asserts the two consumers yield the same validator-id set for every phase.
- **Prior art:** new.

### F-MCP-05 — The generation lifecycle is implemented twice with divergent policy and provider defaults
- **Class:** O6 (with O1 sub-duplication)
- **Severity:** High (impact 3 × drift 4 = 12; downgraded from Critical 16 after verification)
- **Concern:** plan → approve spend → start → poll for a generation batch, including the text-only policy.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/generation/planning.py:75-76` — MCP defaults — `"provider = str(args.get(\"provider\", \"mock-video-provider\"))"` / `"model = str(args.get(\"model\", \"mock-fast\"))"`
  - `src/film_pipeline/app/services/_generation_ops.py:61` — operator defaults — `"provider, model = svc.runtime.default_video_provider()"`
  - `src/film_pipeline/mcp/tools/generation/_text_only.py:100-119` — MCP text-only implementation — `"def _complete_text_only_generation("`
  - `src/film_pipeline/app/services/_generation_ops.py:212-237` — operator text-only implementation — `"def _complete_text_only_generation("`
  - `src/film_pipeline/mcp/tools/generation/_text_only.py:9` / `src/film_pipeline/app/services/_generation_ops.py:20` — duplicated constant — `"_STALE_ISSUE_CODES = frozenset({\"empty_generation_requests\", \"no_generation_requests\"})"` vs `"_STALE_REQUEST_CODES = frozenset({\"empty_generation_requests\", \"no_generation_requests\"})"`
- **Drift proof:** the real, existing divergence is **D7 (provider/model defaults)**, not the text-only row shape. `src/film_pipeline/mcp/tools/generation/planning.py:75-76` defaults to `mock-video-provider`/`mock-fast` for any caller that omits them, while the operator uses `svc.runtime.default_video_provider()` (`src/film_pipeline/app/services/_generation_ops.py:61`), which in real mode returns `seedance-openrouter`/`veo-fast` (`src/film_pipeline/app/_provider_seeds.py:68-80`): an MCP caller omitting provider/model in real mode plans a batch against a provider that does not exist in that runtime (recoverable — submit fails). **Refuted after verification:** the earlier draft also claimed the two text-only writers emit different `prompt_payload` shapes. They do not. `src/film_pipeline/mcp/tools/generation/_text_only.py:51-58` builds `{"text_only": True, "shot_id": shot_id}` per shot and `{"text_only": True}` for the `"all"` fallback; `src/film_pipeline/app/services/_generation_ops.py:240-243` builds `payload = {"text_only": True}` then adds `shot_id` when `shot_id != "all"` — the same two shapes, and the rest of the row (`src/film_pipeline/mcp/tools/generation/_text_only.py:24-36` vs `src/film_pipeline/app/services/_generation_ops.py:244-256`) is field-for-field identical. What survives is the *duplication* (D8): two near-identical `_complete_text_only_generation` implementations and two copies of the stale-issue constant. Mutation scenario for that: change the stale-issue set at `src/film_pipeline/app/services/_generation_ops.py:20`; `src/film_pipeline/mcp/tools/generation/_text_only.py:9` keeps the old set and no test fails (`grep -rn "_STALE_ISSUE_CODES\|_STALE_REQUEST_CODES" tests/` matches nothing).
- **Reproduce:** `grep -rn "_is_text_only_policy\|_complete_text_only_generation\|_STALE_ISSUE_CODES\|_STALE_REQUEST_CODES" src/`
- **Blast radius:** `mcp/tools/generation/*`, `app/services/_generation_ops.py`, `app/runtime.py`; an MCP plan that omits provider/model can target a provider absent from the real-mode runtime (D7), and the duplicated text-only policy/stale-issue set can drift apart silently (D8).
- **Candidate owner module:** `generation.lifecycle` — one plan/approve/start/poll + text-only policy used by both surfaces.
- **Extraction sketch:** keep `GenerationExecutor` as the single lifecycle façade; make `mcp/tools/generation/*` call it (as `_generation_ops.py` already does) and delete `_text_only.py`. Guard test: a single test that drives plan→approve→start→poll through both entry shapes and asserts identical ledger rows and `generation_requests`.
- **Prior art:** `documentation/audit-findings.md:98` ("ledger is only used by MCP tools"); at HEAD the operator path also uses the ledger via `GenerationExecutor` — the duplication is now of *policy*, not storage.

### F-MCP-06 — `OperatorService` mutations bypass the confirmation policy the MCP registry declares, and no single module owns `project_kind`
- **Class:** O3 + O6 (**O3 restored after the round-3 writer census** — the O6-only reclassification rested on a census that is now withdrawn; see the withdrawn-premise note below)
- **Severity:** Medium (impact 2 × drift 4 = 8; band Medium per §1.5, where the band is a function of the score). **Impact 2:** every divergent operator mutator is latent at HEAD — the sole `OperatorService(...)` construction in `src/` is `src/film_pipeline/mcp/tools/generation/planning.py:140` (`preview_generation_prompts`, a read-only preview), no MCP tool or entry point reaches `approve_phase`/`request_revision`/spend approval through the service, no MCP tool exposes delete (`grep -rn "delete_project" src/ tests/ --include=*.py` → `src/film_pipeline/app/runtime.py` and `src/film_pipeline/app/safety.py`, plus test call sites only), and `runtime.delete_project` is invoked only from tests. **Drift 4, re-derived from the corrected census:** the O3 seam has unpinned sites — neither `load_discovered_project` (`src/film_pipeline/app/services/_project_discovery.py:44-58`) nor the MCP creation path (`src/film_pipeline/mcp/tools/projects.py:96-124`) has any test (`grep -rln "load_discovered_project" tests/ --include=*.py` is empty), and the reader's default for an absent key is fail-open — so a partial edit passes the whole suite (e.g. add a marker to `project_kind_for_name`'s tuple, `src/film_pipeline/app/services/_project_discovery.py:68-71`: no test covers the new name, and `normalize_project_kind` would reject it, so the two writers silently classify the same folder differently). It is **4, not 5**, because two tests do pin the operator writer's own vocabulary (`tests/unit/app/services/test_operator_service.py:144-162`); by the same rule applied to F-MCP-04 — where a test pinning part of the axis reduced 5→4 — a partially pinned seam is 4. **Arithmetic: 2 × 4 = 8 → Medium (4–8).** The number is unchanged from the verified revision; what changed is its justification, which no longer rests on "one writer".
- **Concern:** Whether the internal operator service and the MCP surface apply the same safety/confirmation rules to the same use cases.
- **De-facto owners:**
  - `src/film_pipeline/app/services/operator.py:318-328` — unconfirmed approval — `"next_state = self.runtime.approve_phase()"` (no `confirmed` argument anywhere in the method)
  - `src/film_pipeline/mcp/tools/registry.py:169` — the declared requirement — `"confirm=True,"` for `approve_phase` (and 172‑179, 248‑255)
  - `src/film_pipeline/app/services/operator.py:125` — `project_kind` **writer #1 (create path, caller-validated)** — `"state[\"project_kind\"] = normalize_project_kind(request.project_kind)"`, validating the caller's value against `{"production", "test"}` (`src/film_pipeline/app/services/_project_discovery.py:74-80`) with default `"production"` (`src/film_pipeline/app/services/models.py:19`)
  - `src/film_pipeline/app/services/_project_discovery.py:55` — `project_kind` **writer #2 (discovery path, name-derived)** — `"state[\"project_kind\"] = project_kind_for_name(project_id)"`, inferring `"test"` when the folder name contains `test`/`fixture`/`sample`/`tmp`/`demo` (`src/film_pipeline/app/services/_project_discovery.py:68-71`); reached from `src/film_pipeline/app/services/operator.py:438` `_require_project` → `load_discovered_project`
  - `src/film_pipeline/app/services/_project_discovery.py:39` — a third **derivation** of the same classification, for the listing DTO rather than the state dict — `"project_kind=project_kind_for_name(project_id)"` (`ProjectListItem`)
  - `src/film_pipeline/app/safety.py:131-132` — the **raw-key reader** that decides deletability — `"kind = str(state.get(\"project_kind\", \"\")).strip().lower()"` / `"return kind in {\"\", \"test\"}"`; it reads the dict key directly and never consults `project_kind_for_state` (`src/film_pipeline/app/services/_project_discovery.py:61-65`), so an absent key is fail-open (deletable)
- **Drift proof:** existing divergence. A project with `project_kind="production"` (operator default, `src/film_pipeline/app/services/models.py:19`) is refused by `runtime._require_deletable_project` (`src/film_pipeline/app/runtime.py:164-169`); the same project created through MCP `_populate_project_state` (`src/film_pipeline/mcp/tools/projects.py:96-124`, no `project_kind`) carries `""` and is deletable. The two operator-side writers also disagree on *how* the value is produced — validated caller input (`src/film_pipeline/app/services/operator.py:125`) versus a folder-name heuristic (`src/film_pipeline/app/services/_project_discovery.py:55`) — so the same project classifies differently depending on which path materialized its state, and nothing pins the agreement (`grep -rln "load_discovered_project\|project_kind_for_name" tests/ --include=*.py` is empty). Mutation scenario: tighten `can_delete_project` to require an explicit kind; the MCP-created states silently keep being deletable because nothing in `src/film_pipeline/mcp/tools/projects.py` writes the key, and no test creates one project through both paths (`grep -rn "project_kind" tests/unit/mcp/` matches nothing).
- **Writer census (round-3 evidence replay):** `grep -rn 'state\["project_kind"\]' src/ --include=*.py` returns **exactly two** writers — `src/film_pipeline/app/services/operator.py:125` and `src/film_pipeline/app/services/_project_discovery.py:55`. A full `grep -rn "project_kind" src/ --include=*.py` shows every other hit is a declaration/default (`src/film_pipeline/graph/state_schema.py:126`, `src/film_pipeline/schemas/runtime_state.py:39`, `src/film_pipeline/app/services/models.py:19,41`) or a derived reader (`src/film_pipeline/app/services/_project_discovery.py:39,61-65`, `src/film_pipeline/app/services/operator.py:79`). **No third writer exists.**
- **Premise withdrawn (round-3 evidence replay):** the earlier revision of this finding — and `docs/modular-architecture/reviews/verify-11.md` after it — asserted that `src/film_pipeline/app/services/operator.py:125` was the "operator-only `project_kind` writer" and concluded "§1.4 O3 requires state written by 2+ modules, but `project_kind` has exactly one writer", which is why **O3 was dropped** and the class became O6-only. That census was incomplete: `src/film_pipeline/app/services/_project_discovery.py:55` is a second writer *inside `src/`*, reachable from `src/film_pipeline/app/services/operator.py:438`'s `_require_project` → `load_discovered_project`, and it applies a *different* rule (a name heuristic) to the same state key. One logical state written by two modules with different rules and no single writer is exactly `docs/modular-architecture/00-methodology-and-quality-bar.md` §1.4 **O3 (split state authority)**, so O3 is restored alongside O6. The D4 divergence itself is unaffected and still holds: `_populate_project_state` (`src/film_pipeline/mcp/tools/projects.py:96-124`) still writes no `project_kind`, so an MCP-created project still carries `""` and is still deletable by the raw-key reader.
- **Reproduce:** `grep -rn "project_kind" src/film_pipeline/app/services/ src/film_pipeline/app/safety.py src/film_pipeline/mcp/ ; grep -rn "confirmed" src/film_pipeline/app/services/`
- **Blast radius:** `app/services/operator.py`, `app/services/_project_discovery.py`, `app/safety.py`, `app/runtime.py`, `mcp/tools/projects.py`; the operator surface can approve/spend/revise without confirmation and project deletability is path-dependent. Latent at HEAD (no MCP delete tool; `OperatorService` has one production caller) but the second lifecycle is fully tested and ready to be wired.
- **Candidate owner module:** `mcp.policy` (confirmation classification) + a single project-factory that always writes `project_kind`.
- **Extraction sketch:** push `confirmed` into `OperatorService` mutators or route them through `mcp.policy.authorize`; make all three creation paths — `src/film_pipeline/mcp/tools/projects.py:96-124` (`_populate_project_state`), `src/film_pipeline/app/services/operator.py:119-127` (`_apply_requested_settings`), and `src/film_pipeline/app/services/_project_discovery.py:44-58` (`load_discovered_project`) — call one `apply_project_creation_policy(state, source)` so the safety-relevant keys cannot diverge. Guard test: create a project through each path and assert the three states are equal for the safety-relevant keys.
- **Prior art:** `documentation/audit-findings.md:31,127` ("TUI bypasses the MCP contract through an internal OperatorService, creating two divergent operator surfaces"); at HEAD the TUI is gone, so this is now a latent seam between one MCP tool and the service.

### F-MCP-07 — Two project registries must agree but nothing enforces agreement
- **Class:** O4
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** Which structure is authoritative for "projects that can be resolved by `project_ref`".
- **De-facto owners:**
  - `src/film_pipeline/mcp/server.py:43` — MCP-side registry — `"projects: ProjectRegistry = field(default_factory=ProjectRegistry)"`
  - `src/film_pipeline/app/runtime.py:43` — runtime-side registry — `"projects: dict[str, dict[str, Any]] = field(default_factory=dict)"`
  - `src/film_pipeline/mcp/server.py:114-118` — the admission that they diverge — `"# Fall back: if the project exists in the runtime but not in"` / `"# the server's registry, auto-register it. This fixes the gap"`
- **Drift proof:** existing divergence acknowledged in-code, reconciled only on demand at `src/film_pipeline/mcp/server.py:142-177` (`_auto_register_from_runtime`). Mutation scenario: register a project on the runtime (`runtime.create_project`) without going through a tool; until the first `project_ref` call happens to hit the fallback, `server.tools`-level listing (`find_project` uses `rt.projects`, `src/film_pipeline/mcp/tools/projects.py:217`) and `_resolve_project_ref` can disagree; no test asserts the two sets are equal (`grep -rn "_auto_register_from_runtime" tests/` matches nothing).
- **Reproduce:** `grep -rn "ProjectRegistry\|projects.register" src/film_pipeline/mcp/`
- **Blast radius:** `mcp/server.py`, `mcp/resolution.py`, `app/runtime.py`; `AMBIGUOUS_PROJECT` vs `UNKNOWN_PROJECT` outcomes depend on registration order.
- **Candidate owner module:** one `ProjectCatalog` owned by `app` and read by `mcp` (envelope resolution becomes a pure read).
- **Extraction sketch:** make `ProjectRegistry` a view over `StudioRuntime.projects` (or move the registry into `app` and have `MCPServer` hold a reference), delete the auto-register fallback. Guard test: after any create, `set(server.projects.all()) == set(runtime.projects)`.
- **Prior art:** new.

### F-MCP-08 — `RequestEnvelope.requires_confirmation` is dead duplicate normative state
- **Class:** O1
- **Severity:** Medium (impact 2 × drift 4 = 8)
- **Concern:** The normative model for "does this request require confirmation".
- **De-facto owners:**
  - `src/film_pipeline/mcp/envelope.py:28` — field on the request — `"requires_confirmation: bool = False"`
  - `src/film_pipeline/mcp/contract.py:55` — the field that is actually used — `"requires_confirmation: bool = False"`
  - `src/film_pipeline/mcp/envelope.py:42-48` — `new_envelope` never accepts or sets it
- **Drift proof:** mutation scenario with silent failure. Change `src/film_pipeline/mcp/contract.py:55` or the gate at `src/film_pipeline/mcp/server.py:187`; `src/film_pipeline/mcp/envelope.py:28` is never read or written (`grep -rn "requires_confirmation" src/` shows envelope only at its declaration), so the duplicate can rot forever. A reader who trusts the envelope field will look for confirmation plumbing that does not exist.
- **Reproduce:** `grep -rn "requires_confirmation" src/`
- **Blast radius:** `mcp/envelope.py` consumers (any future middleware); misleading type surface.
- **Candidate owner module:** `mcp.contracts` — delete the envelope copy.
- **Extraction sketch:** remove `RequestEnvelope.requires_confirmation`; guard test: the string `requires_confirmation` appears in exactly one module.
- **Prior art:** new.

### F-MCP-09 — The three entry points (plus `langgraph.json`) each re-derive bootstrap and persistence policy
- **Class:** O5
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** One bootstrap decision — set persistence, validate the environment, configure logging, then start — applied uniformly by every entry point.
- **De-facto owners:**
  - `src/film_pipeline/mcp/server.py:243-244` — writes the env flag — `"if not os.getenv(\"FILM_PIPELINE_NO_PERSIST\"):"` / `"os.environ.setdefault(\"FILM_PIPELINE_PERSIST_STATE\", \"1\")"`
  - `src/film_pipeline/mcp/server.py:251-255` — logging + validation — `"configure_logging(configured_runtime_root())"` … `"issues = validate_environment()"`
  - `src/film_pipeline/cli/run.py:224-227` — a different derivation, and no validation — `"configure_logging("` / `"request.runtime_root,"` / `"persist_enabled=not bool(os.getenv(\"FILM_PIPELINE_NO_PERSIST\")),"` (`grep -rn "validate_environment" src/film_pipeline/cli/` is empty)
  - `src/film_pipeline/cli/driver.py:79-82` — a third bootstrap that installs the singleton by touching privates — `"rt = StudioRuntime(server_mode=mode, runtime_root=runtime_root, services=services)"` / `"rt_mod._RUNTIME_MODE_OVERRIDE = mode"` / `"rt_mod._RUNTIME = rt"`
  - `src/film_pipeline/app/product_gate.py:139-145` — no bootstrap at all
  - `langgraph.json:4` — a fourth entry that never constructs `MCPServer` — `"\"film_pipeline\": \"./src/film_pipeline/graph/graph.py:graph\""` (line 3 is the enclosing `"graphs": {`; anchor corrected after verification)
- **Drift proof:** existing divergence. With `FILM_PIPELINE_NO_PERSIST=1` and `FILM_PIPELINE_RUNTIME_ROOT` set, `src/film_pipeline/mcp/server.py:243` skips setting `PERSIST_STATE`, `src/film_pipeline/cli/run.py:226` independently decides `persist_enabled=True` from the absence of `NO_PERSIST` alone, and `src/film_pipeline/graph/graph.py:43`/`src/film_pipeline/graph/services.py:31` read the same flags a third time. Mutation scenario: add a new persistence flag to `_persistence.use_persistent_runtime` (`src/film_pipeline/app/_persistence.py:45-53`); `src/film_pipeline/cli/run.py:226`, `src/film_pipeline/mcp/server.py:243`, `src/film_pipeline/graph/graph.py:43`, and `src/film_pipeline/graph/services.py:31,48` keep the old logic and no test fails — the only tests touching this policy pin each site's *own* literal: `tests/unit/app/test_logging_setup.py:102,123,164-170` and **`tests/unit/test_entrypoints.py:12-39`, which asserts the CLI's `configure.assert_called_once_with(runtime_root, persist_enabled=True)` and the MCP `configure.assert_called_once_with(runtime_root)`** — i.e. the test suite actively pins the *divergent* CLI derivation and would have to change with any fix. No test asserts that the entry points agree; `grep -rn "use_persistent_runtime" tests/` matches only `test_logging_setup.py`.
- **Reproduce:** `grep -rn "FILM_PIPELINE_NO_PERSIST\|FILM_PIPELINE_PERSIST_STATE\|validate_environment\|configure_logging" src/film_pipeline/`
- **Blast radius:** `cli/run.py`, `cli/driver.py`, `mcp/server.py`, `app/product_gate.py`, `graph/graph.py`, `graph/services.py`; the same repo behaves differently (logs, persistence, credential warnings) depending on how it is started, and the `langgraph` server never runs the confirmation or bootstrap layer at all.
- **Candidate owner module:** `app.bootstrap` extended into a single `bootstrap(role) -> Runtime` used by all entry points. **Open reconciliation item (added after verification) — this concern already has three candidate owners, and this file's is the third.** `docs/modular-architecture/audit/03-config-profile-and-defaults.md:373-400` (F-CFG-08) reports the same `FILM_PIPELINE_NO_PERSIST` re-derivation across the same six modules and nominates `app/_persistence`; `docs/modular-architecture/audit/10-checkpoints-and-runtime-persistence.md:817-850` nominates a new `runtime_persistence` with `resolve_persistence()`. One concern, three owners must be resolved once, in `docs/modular-architecture/03-target-architecture.md`, not three times in three cluster files. **Proposed split (this file's recommendation):** `config.environment` is the single *raw env reader* (`docs/modular-architecture/audit/03-config-profile-and-defaults.md:722-760`, config invariant 5), `app/_persistence` (or its `runtime_persistence` successor, if `docs/modular-architecture/audit/10-checkpoints-and-runtime-persistence.md`'s boundary is adopted) owns the *persistence decision*, and extended `app.bootstrap` owns only *when* bootstrap runs at each entry point. `app.bootstrap` must not itself become a raw-env reader — the guard below is stated in those terms deliberately.
- **Extraction sketch:** one `bootstrap()` that resolves persistence via the persistence owner's published accessor, validates, configures logging, and returns a runtime; CLI/driver/MCP call it; `langgraph.json` either points at an MCP-mediated graph factory or is documented as bypassing policy. Guard test: assert each entry module calls `bootstrap`, and that **no module outside `config.environment` reads a raw `FILM_PIPELINE_*` variable and no module outside the persistence owner derives the persist *mode*** — which supersedes the earlier draft's "only `_persistence` reads the PERSIST env" phrasing, since it collided with config's invariant 5.
- **Prior art / precedent:** the untracked prototype module `architecture.py` (never committed and **not at HEAD**; its `PolicyPoint` block was at lines 244-294 *in the revision this audit read*, and the file has since been removed from the worktree, so no reader can open it on the current checkout — it is cited by module name deliberately) declares exactly this `PolicyPoint` with `Exemption`s for `app/logging_setup.py::configure_logging`, `cli/run.py::main`, `graph/graph.py::_default_checkpointer`, `graph/services.py::_artifact_store`, and `mcp/server.py::main`, each marked `"Pending: route through _persistence.use_persistent_runtime()."` — i.e. the seam is already acknowledged in the in-flight work. Colliding prior art, not cited by the earlier draft: `docs/modular-architecture/audit/03-config-profile-and-defaults.md:373-400` (F-CFG-08) and `docs/modular-architecture/audit/10-checkpoints-and-runtime-persistence.md:817-850` (F-CRP-09). `documentation/audit-findings.md:146` notes the Makefile CI gap, unrelated.

### F-MCP-10 — Tool-level failures bypass the `MCPErrorCode` taxonomy entirely
- **Class:** O8
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** One machine-readable error vocabulary for the product boundary.
- **De-facto owners:**
  - `src/film_pipeline/mcp/errors.py:15-22` — the vocabulary — `"VALIDATION_ERROR = \"validation_error\""` … `"CONFIRMATION_REQUIRED = \"confirmation_required\""`
  - `src/film_pipeline/mcp/tools/helpers.py:33-35` — what handlers actually return — `"def _error(message: str, **extra: object) -> dict[str, object]:"` / `"return {\"ok\": False, \"error\": message, **extra}"`
  - `src/film_pipeline/mcp/server.py:216-223` — only handler exceptions are typed — `"except MCPError as exc:"` … `"code=MCPErrorCode.INTERNAL_ERROR"`
- **Drift proof:** mutation scenario. Add a new code (say `QUOTA_EXCEEDED`) to `src/film_pipeline/mcp/errors.py:9-22`; no handler can use it because handlers do not raise `MCPError` — `grep -rn "MCPErrorCode\." src/film_pipeline/mcp/tools/` is empty, and `grep -rn "raise MCPError" src/film_pipeline/mcp/tools/` is empty. Clients keying on `error.code` see `null` for every business failure: the only test that asserts a code originating inside a handler uses a synthetic handler (`tests/unit/test_mcp.py:532-547`, `raise MCPError(code=MCPErrorCode.BUDGET_EXCEEDED, ...)`). **Corrected after verification:** the earlier draft's closing claim that the boundary is "machine-readable only for transport errors" is backwards — the transport erases the typed code too, mapping every failed call to JSON-RPC `-32000` (`src/film_pipeline/mcp/_stdio_transport.py:62-65`); over the wire there is no `MCPErrorCode` at all (F-MCP-13).
- **Reproduce:** `grep -rn "MCPErrorCode\." src/ ; grep -rn "raise MCPError" src/film_pipeline/mcp/tools/`
- **Blast radius:** `mcp/errors.py`, all 77 handlers, `app/product_gate.py` (which string-matches handler source, `src/film_pipeline/app/product_gate.py:130-136`), and the transport; no failure carries a machine-readable code inside the process or over the wire.
- **Candidate owner module:** `mcp.contracts` — make `_error` construct/raise a typed `MCPError`.
- **Extraction sketch:** turn `helpers._error` into a thin wrapper that builds `MCPError` with a required `MCPErrorCode`; the dispatch layer converts it to `MCPResponse`. Guard test: assert no handler returns `{"ok": False}` without a code.
- **Prior art:** new.

### F-MCP-11 — "Which mutations are dangerous" has no owner: provider-block clearing is ungated while comparable state changes are gated
- **Class:** O5 (for a *missing* classification O8 is arguably closer — noted after verification; the substance is unchanged)
- **Severity:** Medium (impact 2 × drift 3 = 6)
- **Concern:** The classification that maps a mutating tool to `requires_confirmation`.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/registry.py:163-179` — gated comparable tools — `"confirm=True,"` on `approve_phase` / `request_revision`
  - `src/film_pipeline/mcp/tools/registry.py:332-338` — ungated safety-relevant mutation — `"_register(registry, \"resolve_provider_block\", ToolGroup.PROVIDER, resolve_provider_block, mutates=True)"`
  - `src/film_pipeline/mcp/tools/providers.py:32` — what it actually does — `"rt.set_provider_health(provider_id, \"healthy\")"`
  - `src/film_pipeline/mcp/tools/registry.py:143` — a second ungated mutation (added after verification) — `"_register(registry, \"set_active_project\", ToolGroup.PROJECT, set_active_project, mutates=True)"`, which repoints the process-global active project every later mutating tool acts on, with no `confirm`
  - `src/film_pipeline/mcp/tools/assembly.py:12-25` — coverage stubs; registered at `src/film_pipeline/mcp/tools/registry.py:358-370` — **measured: only two of the four are mutating** (`plan_coverage_group` `mutates=True` no-confirm; `approve_coverage_generation` `mutates=True` + `confirm=True`; `list_coverage_groups`/`inspect_coverage_group` read-only)
- **Drift proof:** mutation scenario. Reclassify `resolve_provider_block` as dangerous by adding `confirm=True`; nothing else changes and no test fails because the classification lives only in the `_register` call site — there is no predicate ("does this tool clear a safety block?", "does this tool repoint global state?") that could be applied uniformly. Conversely, `approve_coverage_generation` carries `confirm=True` while being a no-op `_stub` (`src/film_pipeline/mcp/tools/assembly.py:25`), so the flag is not even a reliable danger signal. `set_active_project` shows the same hole in the other direction: a comparable global-state mutation accepted with no classification at all. **Corrected after verification:** the earlier draft said "4 tools … registered `mutates=True`/`confirm=True`", which overstates the stub set.
- **Reproduce:** `grep -n "confirm=True" src/film_pipeline/mcp/tools/registry.py ; sed -n '27,33p' src/film_pipeline/mcp/tools/providers.py ; sed -n '143p' src/film_pipeline/mcp/tools/registry.py`
- **Blast radius:** `mcp/tools/registry.py`, `mcp/tools/providers.py`, `mcp/tools/projects.py`, `mcp/tools/assembly.py`; an agent can silently clear a provider block that the router was using to gate generation, or silently repoint the active project.
- **Candidate owner module:** `mcp.policy` — a `Danger` classification per tool, independent of the registration literal.
- **Extraction sketch:** declare `danger: Literal["none","confirm","checkpoint"]` per tool in the argument-model table (F-MCP-03); derive `requires_confirmation`/`creates_checkpoint` from it. Guard test: every tool whose handler calls `set_provider_health`, `approve_*`, `rollback_*`, or `export_*` is classified at least `confirm`.
- **Prior art:** `documentation/audit-findings.md:155` (risk table: "Dangerous MCP mutations without confirmation").

### F-MCP-12 — Bible / assembly tools instantiate agents and write artifacts outside the graph, with their own versioning and no shared policy
- **Class:** O6 (+O1 for the duplicated version arithmetic; **O7 dropped after verification** — both writers use the `ArtifactStore` public API, `src/film_pipeline/mcp/tools/bibles/_shared.py:138` → `store.save` and `src/film_pipeline/graph/nodes/visual.py:52` → `_save_artifact`, so neither reaches into the other's private state)
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** One path for creating `visual_dev`/assembly artifacts with one versioning and policy owner.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/bibles/camera.py:64` — agent instantiated inside a tool — `"from film_pipeline.agents.impl.camera_bible_agent import CameraBibleAgent"`
  - `src/film_pipeline/mcp/tools/bibles/camera.py:90-98` — its own candidate write + state link — `"ref = _save_visual_dev_candidate("` … `"_register_active_artifact_ref(rt, active, project_id, \"camera_bible_ref\", ref)"`
  - `src/film_pipeline/mcp/tools/bibles/_shared.py:124-126` — its own version assignment — `"next_version = ("` / `"_latest_artifact_version(store, project_id, FilmPhase(\"visual_dev\"), artifact_id) + 1"`
  - `src/film_pipeline/mcp/tools/planning.py:74-76` — a second copy of the same versioning pattern — `"next_version = ("` / `"_latest_artifact_version(store, project_id, FilmPhase(\"gen_planning\"), artifact_id) + 1"`
  - `src/film_pipeline/mcp/tools/bibles/shot.py:71` — a **third** `next_version` copy, uncited in the earlier draft (added after verification) — `"next_version = ("`
  - `src/film_pipeline/graph/nodes/visual.py:52` — the graph's own artifact writer for the same phase — `"ref = _save_artifact(new_state, index, \"reference_index\", \"visual_dev\")"`
- **Drift proof:** existing divergence. `grep -rn "CameraBibleAgent" src/film_pipeline/graph/` is empty: at HEAD the graph never creates the bibles, so a bible produced through MCP (`tools/bibles/*`) and the phase artifacts produced by the graph (`src/film_pipeline/graph/nodes/visual.py:52`) advance the same `visual_dev` phase from two unrelated code paths, each computing versions itself. Mutation scenario: change the phase-level version policy in the graph's `_save_artifact`; the three MCP copies (`src/film_pipeline/mcp/tools/bibles/_shared.py:124-126`, `src/film_pipeline/mcp/tools/bibles/shot.py:71`, `src/film_pipeline/mcp/tools/planning.py:74-76`) keep their own arithmetic and no test fails (`grep -rn "_save_visual_dev_candidate" tests/` is empty).
- **Reproduce:** `grep -rn "BibleAgent" src/film_pipeline/mcp/ src/film_pipeline/graph/ ; grep -rn "next_version = (" src/film_pipeline/mcp/`
- **Blast radius:** `mcp/tools/bibles/*`, `mcp/tools/planning.py`, `mcp/tools/assembly.py`, `mcp/tools/reference_generation/*`, `graph/nodes/visual.py`; artifact lineage/orchestrator state does not reflect MCP-created bibles, and versions can collide across writers.
- **Candidate owner module:** `graph` artifact-writer contract (one `save_phase_artifact` used by nodes and tools) — an `artifacts`-domain decision this audit only flags.
- **Extraction sketch:** replace `_save_visual_dev_candidate`/`_save_gen_planning_candidate`/`_save_reference_index_artifact` with one call into the graph's artifact writer; require tools to go through the phase node or a documented `ArtifactStore` API. Guard test: only one module computes `next_version`/`latest_version + 1`.
- **Prior art:** `documentation/audit-findings.md:43` ("Bible tools (`bibles.py`) directly instantiate agents and save artifacts, bypassing LangGraph") and `:45` (hard-coded `version=1`); verified at HEAD with the new split file layout — the bypass persists (a second hard-coded `version=1` remains at `src/film_pipeline/mcp/tools/validation.py:191`).

---

### 4.1 Findings added after verification (F-MCP-13 … F-MCP-15)

These three seams were surfaced by the independent verifier
(`docs/modular-architecture/reviews/verify-11.md` §"Missed in scope") and re-verified against HEAD here. They are
new findings, not corrections of the twelve above.

### F-MCP-13 — The only transport erases the typed error code and never carries actor attribution
- **Class:** O8 (error contract) — the actor half is adjacent to D5
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** One machine-readable failure contract, and one attribution field, on the path from the wire to the tool layer.
- **De-facto owners:**
  - `src/film_pipeline/mcp/_stdio_transport.py:62-65` — the flattening — `"if not tool_response.success:"` / `"error = tool_response.error"` / `"message = error.message if error is not None else \"Tool call failed.\""` / `"return _jsonrpc_error(request_id, -32000, message)"`
  - `src/film_pipeline/mcp/_stdio_transport.py:61` — the actorless call — `"tool_response = await server.call(tool_name, arguments)"` (no `actor_id`/`actor_type` kwargs)
  - `src/film_pipeline/mcp/server.py:51-52` — the accepted attribution with silent defaults — `"actor_id: str | None = None,"` / `"actor_type: str = \"human\","`
  - `src/film_pipeline/mcp/envelope.py:29-30` — where it is stored and never read — `"actor_id: str | None = None"` / `"actor_type: str = \"human\""`
- **Drift proof:** existing divergence with a missed contract. `src/film_pipeline/mcp/server.py:188-199` builds `MCPError(code=MCPErrorCode.CONFIRMATION_REQUIRED)`, but `src/film_pipeline/mcp/_stdio_transport.py:64-65` emits only `-32000` + `message`: a JSON-RPC client sees the identical code for `UNKNOWN_TOOL`, `CONFIRMATION_REQUIRED`, and `BUDGET_EXCEEDED`, so the taxonomy in `src/film_pipeline/mcp/errors.py:9-22` is machine-readable nowhere. Symmetrically, `git grep -n "actor_id" HEAD -- src/` matches `envelope.py`, `server.py`, and the unrelated `src/film_pipeline/schemas/audit.py:22` — no handler reads `_envelope.actor_id`, and the sole transport never passes one, so every MCP mutation is attributed to `None`/"human" by construction. Mutation scenario: add a machine-actionable code (e.g. an agent caller that must retry on `BUDGET_EXCEEDED`) — the client cannot distinguish it from a typo, and the audit trail records a human actor for an automated call. This also corrects F-MCP-10's original closing claim (the erasure happens for *all* codes, transport-level included). The erasure is pinned *for an unknown tool* by `tests/unit/test_mcp.py:473` (`assert response["error"] == {"code": -32000, "message": "Unknown tool: does_not_exist"}`), which is why drift is 4 and not 5: the flattening mechanism itself is asserted, but no test pins the taxonomy→wire *agreement* for the typed codes.
- **Reproduce:** `git grep -n "actor_id" HEAD -- src/film_pipeline/mcp/ ; git grep -n -e "-32000" HEAD -- src/film_pipeline/mcp/`
- **Blast radius:** `src/film_pipeline/mcp/_stdio_transport.py`, `src/film_pipeline/mcp/server.py`, `src/film_pipeline/mcp/envelope.py`, all 77 handlers, and any audit attribution derived from the envelope; both the error vocabulary and the actor identity are dead at the product boundary.
- **Candidate owner module:** `mcp.policy` — the same module that owns `MCPErrorCode` must define the wire mapping, plus a required `actor` on the single `invoke_tool` entry.
- **Extraction sketch:** map `MCPError.code` onto a stable JSON-RPC `error.data.code` (or a reserved code range) in `_serve_tools_call`; have `_serve_stdio` populate `actor_id`/`actor_type` from request params and pass them to `server.call`; make handlers read the envelope actor rather than defaulting. Guard test: assert the JSON-RPC body for a `CONFIRMATION_REQUIRED` refusal carries that code, and that every mutating handler sees a non-`None` actor when the caller supplied one.
- **Prior art / disclosed overlap:** `F-MCP-10` (handlers never use the taxonomy) and D5 (no actor on the operator path). **Partial double-count, disclosed:** the *error-code* half of this finding is the wire-level continuation of `F-MCP-10` — `F-MCP-10` owns "no handler emits a typed code", this finding owns "the one typed code that does exist is erased before it leaves the process" — so the two are one wire-mapping decision and must be scheduled once, not counted as two independent seams; the *actor-attribution* half is genuinely new. `F-MCP-10` already cross-references this finding ("over the wire there is no `MCPErrorCode` at all (F-MCP-13)").

### F-MCP-14 — `MCPServer.active_project_id` is a write-only second active-project state
- **Class:** O3 (split state authority)
- **Severity:** Medium (impact 2 × drift 3 = 6)
- **Concern:** Which structure is authoritative for "the project subsequent calls act on".
- **De-facto owners:**
  - `src/film_pipeline/mcp/server.py:44` — the shadow field — `"active_project_id: str | None = None"`
  - `src/film_pipeline/mcp/server.py:121` / `:157` — written during project resolution — `"self.active_project_id = project.project_id"` / `"self.active_project_id = pid"`
  - `src/film_pipeline/mcp/server.py:230-231` — written again on registration — `"if self.active_project_id is None:"` / `"self.active_project_id = record.project_id"`
  - `src/film_pipeline/app/runtime.py:207-213` — the state every tool actually reads — `"self.active_project_id = project_id"` … `"return self.projects.get(self.active_project_id)"`
  - `src/film_pipeline/mcp/tools/helpers.py:38-52` — the reader that bypasses the server copy — `"_active_project_id(args, rt)"` falls back to `rt.get_active()`, never `server.active_project_id`
- **Drift proof:** mutation scenario with no observable effect — which is the defect. Change what "active" means in `runtime.set_active` (`src/film_pipeline/app/runtime.py:207`); `MCPServer.active_project_id` keeps an independent value and nothing fails. In `git grep -n "active_project_id" HEAD -- src/film_pipeline/mcp/` the `MCPServer` field itself occurs only as the declaration plus writes (`src/film_pipeline/mcp/server.py:44,121,157,230-231`); every other match is the *unrelated* `helpers._active_project_id` helper, which reads `rt.get_active()` (`src/film_pipeline/mcp/tools/helpers.py:49-51`). No `src/` reader consumes the server field: it is a second representation with no `src/` consumer. **Measured after verification (`docs/modular-architecture/reviews/verify-20.md`):** the field is *not* unasserted — five assertions in one first-round test file read it (`tests/unit/test_mcp.py:590,598,616,628,653`, `assert server.active_project_id == …`; `git grep -n "server.active_project_id" HEAD -- tests/` returns exactly those five). It is therefore **dead but asserted**: removing it changes no `src/` behavior, but it does require editing those five assertions, which is a materially different deletion cost from an untested dead field and is why the extraction sketch names them.
- **Reproduce:** `git grep -n "active_project_id" HEAD -- src/film_pipeline/mcp/ src/film_pipeline/app/runtime.py`
- **Blast radius:** `mcp/server.py`; any future middleware, telemetry, or policy check that reads the server's field will silently disagree with the runtime the tools use.
- **Candidate owner module:** delete the field; one active project owned by `app.runtime` (or by the `ProjectCatalog` proposed in F-MCP-07).
- **Extraction sketch:** remove `MCPServer.active_project_id`; if the server needs a "last resolved project" for logging, read it from the runtime. Guard test: the string `active_project_id` appears in exactly one state owner module (adopting this guard requires updating the five asserting tests at `tests/unit/test_mcp.py:590,598,616,628,653`).
- **Prior art:** `F-MCP-07` (two project registries) — this is the active-pointer half of the same split.

### F-MCP-15 — `ToolContract.idempotency_key_field` is dead normative state
- **Class:** O8 (missing contract) — **reclassified from O1 after `docs/modular-architecture/reviews/verify-20.md`**: §1.4 O1 requires the same model to be declared in 2+ modules, but `idempotency_key_field` is declared in exactly one (`src/film_pipeline/mcp/contract.py:57`, echoed at `:110` in the same module), so the evidence supports the missing-contract class rather than O1-by-analogy.
- **Severity:** Medium (impact 2 × drift 3 = 6)
- **Concern:** The normative model for "which argument makes this tool's call idempotent".
- **De-facto owners:**
  - `src/film_pipeline/mcp/contract.py:57` — the declaration — `"idempotency_key_field: str | None = None"`
  - `src/film_pipeline/mcp/tools/registry.py:110-117` — the sole constructor never sets it (`_tool_contract` has no such parameter; measured 0/77 populated)
  - `src/film_pipeline/mcp/contract.py:110` — catalog echoes it — `"\"idempotency_key_field\": c.idempotency_key_field,"`
  - no reader anywhere: `grep -rn "idempotency_key_field" src/` matches exactly those declaration/echo sites, never a consumer
- **Drift proof:** mutation scenario with silent failure. Set `idempotency_key_field` on any tool; nothing changes, because no dedupe path consumes it and no test asserts it is populated. Conversely, `§2`'s "single for flags" row presented the whole flag set as healthy — `idempotency_key_field` is a second dead field alongside `RequestEnvelope.requires_confirmation` (F-MCP-08), and the catalog advertises a dedupe contract the system does not honor.
- **Reproduce:** `git grep -n "idempotency_key_field" HEAD -- src/ tests/`
- **Blast radius:** `mcp/contract.py`, `mcp/tools/registry.py`, the catalog served over `tools/list`; an MCP client that implements retry-on-idempotency-key against the published contract gets no dedupe.
- **Candidate owner module:** `mcp.policy` — either implement the dedupe (key stored per tool, consulted before dispatch) or delete the field; a declared contract the owner does not enforce is the defect either way.
- **Extraction sketch:** if kept, `_register(..., idempotency_key=...)` plus a dispatch-layer cache keyed on `(tool_name, key)`; if not, remove `src/film_pipeline/mcp/contract.py:57` and its catalog echo. Guard test: every declared contract field is either enforced or absent.
- **Prior art:** `F-MCP-08` (dead duplicate normative state). The *pattern* is the same — a declared field nothing enforces — but the *class* is not: `F-MCP-08` is a true O1 because `requires_confirmation` is declared twice (`src/film_pipeline/mcp/envelope.py:28` and `src/film_pipeline/mcp/contract.py:55`), whereas `idempotency_key_field` has a single declaration (`src/film_pipeline/mcp/contract.py:57`), which is why this finding is O8 rather than O1.

---

## 5. Clean concerns (single-owner or no distributed ownership found)

- **Contract flags.** Every `ToolContract` instance is built by `src/film_pipeline/mcp/tools/registry.py:101-117`; `grep -rn "ToolContract" src/` matches only `mcp/contract.py`, `mcp/tools/registry.py`, `mcp/__init__.py`. No tool module re-declares `mutates_state`/`requires_confirmation`/`creates_checkpoint`. Two declared fields are *not* in that healthy set: `input_schema`/`output_schema` are never populated (F-MCP-03) and `idempotency_key_field` is never read (F-MCP-15). **Guard test that pins the enforced flags:** `tests/unit/test_mcp.py:1269-1285` asserts the exact config-group tool set from the catalog; `tests/unit/test_mcp.py:99-104` asserts catalog flags round-trip.
- **Duplicate tool names.** `ToolRegistry.register` refuses a second registration — `src/film_pipeline/mcp/contract.py:81-82` `"if contract.name in self._tools:"` / `"raise ValueError(f\"Tool already registered: {contract.name}\")"`. Partial registration cannot silently shadow.
- **Registry uniqueness of the checkpoint policy.** `creates_checkpoint` is set exactly once (`src/film_pipeline/mcp/tools/registry.py:170`), matching the single graph approval gate; `grep -c "checkpoint=True" registry.py` = 1.
- **Project-reference resolution order.** Single owner in `src/film_pipeline/mcp/resolution.py:61-113`; no second resolution algorithm found in `src/` (`grep -rn "SequenceMatcher" src/` matches only `resolution.py`).
- **Blocker derivation.** `src/film_pipeline/mcp/tools/state.py:89` and `src/film_pipeline/app/services/operator.py:450` both call `graph.router.get_blockers_for_state`; the operator's `_has_blockers` docstring at `src/film_pipeline/app/services/operator.py:446-449` states this explicitly. Convenience duplication with no normative content — not a finding.
- **Delete-path safety.** `app/safety.py` is the single owner of filesystem-delete safety (`is_safe_to_delete` 58, `require_safe_to_delete` 82, `safe_rmtree` 92, `move_to_trash` 98, `can_delete_project` 121) and is pinned by `tests/unit/app/test_safety.py:31-140` (including `test_require_safe_to_delete_message_does_not_advertise_allow_delete_env` and the explicit "env gates project-level deletes only" test at 79‑89). The only caller is `src/film_pipeline/app/runtime.py:150-188`. **Gap (recorded, not a finding):** no MCP tool exposes deletion, so this owner is unreachable from the product boundary — `grep -rn "delete_project" src/` matches `app/runtime.py` and `app/safety.py` only.
- **Bootstrap validation logic.** `src/film_pipeline/app/bootstrap.py:12-78` is the single implementation of the environment checks; `src/film_pipeline/app/health.py:31` and `src/film_pipeline/mcp/server.py:253` both call it. What is distributed is *when* it runs (F-MCP-09), not *what* it checks.
- **`product_gate` stub detection.** `src/film_pipeline/app/product_gate.py:123-136` consumes the canonical registry rather than a copy, so it cannot drift from the registered handler set.

---

## 6. Candidate module boundary — MCP contract + safety owner

**Proposed module `film_pipeline.mcp.policy`** (may be a package):

- **Responsibility (one sentence):** Define and enforce the MCP tool contract — argument schema, danger classification, confirmation gate, checkpoint requirement, and the typed error vocabulary — for every invocation path.
- **Non-goals (explicit):** does not implement tool behavior; does not own the graph, the runtime, or the artifact store; does not resolve projects (consumes one `ProjectCatalog`).
- **Owns (N/I/R):**
  - N: `ToolContract`, `ToolArgs` models, `Danger` classification, `MCPErrorCode`, and the JSON-RPC wire mapping of the code.
  - I: one `authorize(registration, arguments) -> MCPError | None`; one `validate_arguments(registration, arguments)`; the only confirmation/checkpoint refusal path; the only place an actor is required and attached.
  - R: the catalog representation served over `tools/list`.
- **Consumes:** `app.runtime` (via a narrow accessor), `artifacts` (via its public API).
- **Evidence for the boundary (B9):** F-MCP-01, F-MCP-02, F-MCP-03, F-MCP-10, F-MCP-11, F-MCP-13, F-MCP-15 — seven distinct findings all locate their seam at "who decides, enforces, and serializes the contract for a tool call".
- **Extraction keeps `make ci-check` green (B5):** step 1 moves `_check_confirmation` + `MCPErrorCode` into `policy` and points `server.call` at it (behavior-identical); step 2 adds `ToolArgs` and populates `input_schema`; step 3 deletes `checkpoints.py`'s re-check and corrects the `_profile_change.py` docstring; step 4 switches `server.register`/`catalog` to the policy module; step 5 routes the transport's error/actor mapping through it.
- **Guard tests (B6):**
  1. Every registered tool has a non-empty `input_schema`; `confirmed` is a declared property iff `requires_confirmation` (kills F-MCP-03).
  2. Calling each of the 10 confirm-gated handlers directly with `{}` yields a refusal carrying `MCPErrorCode.CONFIRMATION_REQUIRED` (kills F-MCP-01).
  3. No module outside `mcp/` invokes a tool handler without `MCPServer.call`/`invoke_tool` (kills F-MCP-02).
  4. `requires_confirmation` appears in exactly one normative module (kills F-MCP-08).
  5. Every handler that returns `ok:False` carries an `MCPErrorCode` (kills F-MCP-10).
  6. A `CONFIRMATION_REQUIRED` refusal survives to the wire as that code, not `-32000`; a mutating call with a supplied actor sees a non-`None` `_envelope.actor_id` (kills F-MCP-13).
  7. Every declared `ToolContract` field is either populated and read by an enforcement site, or absent (kills F-MCP-15 and pins F-MCP-03).

**Proposed module `film_pipeline.app.bootstrap` (extended):** one `bootstrap(role: Literal["mcp","cli","gate"]) -> StudioRuntime | None` that resolves persistence through the persistence owner's published accessor, runs `validate_environment`, configures logging, and installs the runtime — consumed by `mcp/server.py:main`, `cli/run.py:main`, `cli/driver.py`, and `app/product_gate.py:main`. **Guard-test wording corrected after verification:** not "no module other than `app/_persistence.py` reads `FILM_PIPELINE_PERSIST_STATE`/`FILM_PIPELINE_NO_PERSIST`" — that collides with `config`'s invariant 5 (`docs/modular-architecture/audit/03-config-profile-and-defaults.md:722-760`, one raw-env reader via a new `config.environment`). The split is mechanism (`config.environment` reads raw env) vs policy (the persistence owner decides the mode) vs orchestration (`app.bootstrap` decides *when* it runs); the guard is "every entry module calls `bootstrap`, no module outside `config.environment` reads a raw `FILM_PIPELINE_*` variable, and no module outside the persistence owner derives the persist mode" (kills F-MCP-09). The three-way candidate-owner collision with F-CFG-08 (`app/_persistence`) and F-CRP-09 (`runtime_persistence`) is recorded as an open reconciliation item for `docs/modular-architecture/03-target-architecture.md` in F-MCP-09. This is the same seam the in-flight `architecture.py` `PolicyPoint` records as "Pending" — adopting it retires those exemptions rather than adding new ones.

**Not proposed:** a new `generation.lifecycle` or validator-dispatch module is outside this cluster's ownership (F-MCP-04/F-MCP-05 are reported here but belong to the graph/generation/validation clusters); the MCP-side fix is to stop carrying local copies and delegate.

---

## 7. Unverified hypotheses (excluded from findings, per §1.6.6)

- **`src/film_pipeline/mcp/_stdio_transport.py:134`** runs `asyncio.run(handle_jsonrpc(...))` once per inbound message, so no state survives between requests. I did not verify whether any handler depends on a live event loop or a persistent session; not classified as a finding.
- **`scripts/*`** are developer tools, not shipped entry points (`Makefile` does not invoke them in `ci-check`). Whether they should count as an audited "entry point" under A1 is a program-level scope question; I treated `scripts/test_real_mcp_operator.py` and `scripts/e2e-real-auto-approve.py` as evidence for F-MCP-02 only.
- **`src/film_pipeline/mcp/tools/kb.py:43-45`** ignores the `query` argument (`retrieval.by_tags(phase=...)`) even though it returns `query=query`. I did not confirm whether this is intentional (tag-only retrieval) or a defect, so it is not a finding.
