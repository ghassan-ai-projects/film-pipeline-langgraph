# LENS-OBSERVABILITY — Architectural Review

- Repo: `/Users/ghassan/my-projects/film-pipeline-langgraph`, branch `arch-improvement-review`, HEAD `e811d1d`
- Scope: observability only — logging, audit, tracing, error surfacing, run forensics. Read-only analysis; single output (this file).
- Method: read the full `observability` package, `app/runtime.py`, `app/_persistence.py`, `app/_graph_exec.py`, `mcp/server.py` + tool layer, `generation/executor.py`, `agents/runner.py`, graph nodes, TUI gateways/screens; grepped every consumer of each public symbol; walked D-007 commit `1a61b9e`.

---

## 0. Surface inventory (Mission 1)

### 0.1 Declared surface of `src/film_pipeline/observability/`

| Public symbol | Defined | Consumers in `src/` (outside the package) |
|---|---|---|
| `AuditTrail` | `observability/audit.py:44` | **None.** Only tests (`tests/unit/observability/test_observability.py`). |
| `AuditEvent` (dataclass) | `observability/audit.py:27` | Reconstructed-from-dict only by TUI/app feed mappers — but they import a **different** class named `AuditEvent` from `app/services/models.py:167` (TUI view model). The observability dataclass has zero construction sites outside tests. |
| `AuditEventType` (StrEnum, 12 members incl. `ROUTING = "routing_decision"`) | `observability/audit.py:11-23` | **None.** Dead in production. D-007 fixed a typo in this enum's value (`1a61b9e`) — a fix to code nothing executes. |
| `BlockerReporter` / `BlockerReport` / `BlockEntry` | `observability/blockers.py:48/22/11` | **None.** |
| `MetricsCollector` / `MetricPoint` (incl. `phase_duration()`, `provider_job(cost_usd)`, `cost_tracking()`) | `observability/metrics.py:21/11` | **None.** The duration/cost API exists and is never called. |

Note: `__init__.py:9-15` `__all__` omits `BlockEntry` and `MetricPoint` even though the review brief references `BlockEntry` as a known symbol.

### 0.2 The live audit system is a *different*, parallel implementation

The production audit trail is `StudioRuntime._record_audit()` (`app/runtime.py:284-296`): plain dicts `{event_id, timestamp, actor, action, details}` appended to `rt.audit_events` (`runtime.py:48`), persisted per project to `<root>/<project>/audit-log.json` (`app/_persistence.py:24,277-287`), restored on boot (`_persistence.py:252-261`). It shares no code, no schema, and no vocabulary with the `observability` package.

All emit sites for runtime audit events (complete list, 11 actions across 6 files):

| Action string (free-form) | Site |
|---|---|
| `create_project` | `runtime.py:117` |
| `delete_project` | `runtime.py:162` |
| `set_active` | `runtime.py:201` |
| `create_checkpoint` | `runtime.py:265-271` |
| `add_operator_comment` | `runtime.py:335-342` |
| `approve_phase` | `app/_graph_exec.py:214-221` |
| `run_validation` | `_graph_exec.py:262-267` |
| `request_revision` | `_graph_exec.py:304-309` |
| `create_film_project` | `mcp/tools/projects.py:121-128` |
| `approve_profile_change` | `mcp/tools/_profile_change.py:333-339` |
| `generate_reference_images` | `mcp/tools/reference_generation/tool.py:63-70` |

Vocabulary drift is already visible: project creation records `create_project` on one path and `create_film_project` on another.

### 0.3 Are AuditTrail events wired uniformly into graph nodes?

**No graph node emits any audit event at all** — nodes have no handle to `StudioRuntime`; audit emission lives only in the MCP-tool/runtime layer above. What nodes do record is a third mechanism: handoff dicts appended to graph-state key `_routing_decisions` via `_record_handoff` (`graph/nodes/_agent_handoff.py:115-149`), propagated across node boundaries by `_propagate_side_effects` (`_agent_handoff.py:62-79`).

Quantified against the 18 registered nodes (`graph/graph.py:108-129`: `phase_router`, intake, constitution, development, script, visual_dev, shot_bible, gen_planning, generation, qc, post, delivery, consistency_check, await_approval, approve_phase, request_revision, repair, end):

- **10 emit handoff/routing records on at least one path**: intake, constitution, development, script, visual_dev, shot_bible, gen_planning, post (`wrapup.py:24`), qc (only when multi-validator consensus runs — `qc.py:98-100`), await_approval (only the orchestrator-advisory path, `approval.py:24-50`; the headless short-circuit can skip it).
- **8 never produce one**: `phase_router` & `end` (passthroughs), `generation_node` (ledger/gates only), `delivery_node` (flag-only, `wrapup.py:43-44`), `consistency_check_node`, `approve_phase_node`, `request_revision_node`, `repair_phase_node` (re-runs a phase node so its child's handoff is deduped away — `_is_duplicate_handoff`, `_agent_handoff.py:105-112`).
- **0 of 18 emit runtime audit events.**
- Additionally, `orchestrator_state.record_routing_decision()` (`orchestrator_state.py:205-225`) — the only decision recorder that assigns a `routing_decision_id` — has **zero production callers** (tests only). The live handoff records carry **no event id and no timestamp** (`_agent_handoff.py:137-148`).

So the honest answer to "is AuditTrail wired into graph nodes uniformly?": there are three non-integrated mechanisms (dead typed package, runtime dict log, graph-state handoffs), and none of them covers all nodes.

---

## Findings

### Finding 1 — Two-and-a-half parallel observability systems; the typed one is dead code

- **EVIDENCE:** `observability/__init__.py:5-15` exports 6 symbols; grep shows `AuditTrail`, `MetricsCollector`, `BlockerReporter`, `AuditEventType` have zero `src/` consumers outside their own package. Live replacements: `runtime.py:284-296` (audit dicts), `runtime.py:49+367-377` (`block_entries` vs `BlockerReporter`), nothing at all for metrics. Name collision: two distinct `AuditEvent` classes (`observability/audit.py:27`, `app/services/models.py:167`). The dead docstrings admit it: *"In production, this would write to a database or structured log"* (`audit.py:47`, `metrics.py:24`).
- **SEVERITY:** High (architectural debt + false confidence; reviewers and D-007-style fixes land in code that never runs).
- **OPERATOR SCENARIO IT BREAKS:** Any operator-facing promise derived from reading the observability package ("there's an audit trail with cost/duration fields") is untrue in production: the live events have no `success`, `error_message`, `cost_usd`, or `duration_ms` fields — those exist only in the unused dataclass.
- **TARGET DESIGN:** One event model. A Pydantic `AuditEvent` schema (v2, matching AGENTS.md standards) with a typed vocabulary (Finding 2), owned by `observability/`, used by `StudioRuntime`, MCP tools, TUI translations (`tui/gateways/_translations.py:209-220`), and persistence. Delete or absorb `BlockerReporter`/`MetricsCollector` into it (blockers → `get_blockers` fix in Finding 6; metrics → cost seam in Finding 9).
- **MIGRATION:** (1) Make `StudioRuntime._record_audit` construct the new schema internally while still persisting the same JSON shape (additive fields); (2) switch TUI translation to the shared schema; (3) delete dead classes once parity is proven by tests that exercise the runtime, not the package in isolation.
- **EFFORT:** M. **RISK:** Low — additive fields keep old `audit-log.json` readable; restore path already tolerates unknown keys (`_persistence.py:257-260`).

### Finding 2 — No event-kind vocabulary on the live path; D-007 generalizes

- **EVIDENCE:** Live `action` is a free string typed per call site (`runtime.py:287` `f"audit:{action}:{uuid4().hex[:8]}"`), `details: dict[str, str]` free-form (`runtime.py:291`). 11 action strings scattered over 6 files, with near-duplicates (`create_project` vs `create_film_project`). D-007 (`commit 1a61b9e`) had to fix `"routing_decisión"` → `"routing_decision"` inside `AuditEventType` — proving both that values are unvalidated strings *and* that the typed home for them is unused. Nothing validates new strings at write time; `get_audit_log` (`runtime.py:298-304`) filters by `details.project_id` only.
- **SEVERITY:** High.
- **OPERATOR SCENARIO IT BREAKS:** An agent or future tool emitting `"approve_phse"` writes silently; downstream consumers that filter by action (TUI audit feed summary rendering, `explain_last_decision`) mis-categorize or drop the event; nobody gets an error. Forensics queries like "show me every approval" require knowing every spelling variant.
- **TARGET DESIGN:** `AuditActionKind` StrEnum (project lifecycle, gate transitions, checkpoint, validation, generation step, error, provider health) + Pydantic payload schemas per kind (discriminated union on `action`). Reject unknown kinds at `record()` time (raise `ValueError` — fail loudly at emit, not at query). Keep the JSON field names stable for backward compatibility.
- **MIGRATION:** Introduce enum with the existing 11 strings as members; add a lint-time grep guard or unit test asserting every `_record_audit(` call uses enum members; migrate call sites file-by-file.
- **EFFORT:** S–M. **RISK:** Low.

### Finding 3 — Graph execution is invisible to the audit trail; per-node coverage is ~10/18 and partial

- **EVIDENCE:** Zero `_record_audit` calls under `graph/` (nodes cannot reach the runtime). Audit log therefore contains only human/tool-level actions (see §0.2). Handoff records exist only for agent-running nodes (§0.3); `generation_node`, `delivery_node`, `consistency_check_node`, `approve_phase_node`, `request_revision_node`, `repair_phase_node` leave no trace except implicit state diffs. KNOWN FACT corroborated: the approval-autonomous branch (`approval.py:69-87` headless decision) leaves no dedicated record distinguishing auto-approval from human approval beyond state flags.
- **SEVERITY:** High.
- **OPERATOR SCENARIO IT BREAKS:** Headless/auto-approve run finishes; operator opens `get_audit_log` and sees `submit_idea` then nothing until approvals — no record that 10 phase nodes executed, what each decided, or that repair ran 3 rounds. The operator guide itself concedes: *"audit proof for live model/provider execution is still limited"* (`documentation/openclaw-mcp-operator-guide.md:823`).
- **TARGET DESIGN:** Node lifecycle events emitted where the graph actually executes: wrap `run_graph`/`resume` invocation points (`_graph_exec.py:40-76,153-185`) with a LangGraph stream/callback listener (or a thin decorator around `_PHASE_NODES`) recording `node_start`/`node_end` {node, phase, run_id, duration_ms, ok, error_kind}. Emit from the executor side so nodes stay runtime-free.
- **MIGRATION:** Start with the three runtime entry points (`run_graph`, `_resume_after_approval`, `request_revision`) — one wrapper captures every node transition without touching node bodies.
- **EFFORT:** M. **RISK:** Low-medium (must not break LangGraph replay semantics; events must be fire-and-forget).

### Finding 4 — Exceptions swallowed silently on resume and auto-checkpoint paths

- **EVIDENCE:** `_graph_exec.py:181-183`: `except Exception: return advance_to_next_phase(rt, dict(active))` — a failed graph resume (which includes any provider/agent exception raised during post-approval node execution) falls back to manual phase advance with **no log line and no audit event**. `_graph_exec.py:125`: `with contextlib.suppress(Exception): rt.create_checkpoint(...)` — auto-checkpoint failures vanish entirely. Only `auto_checkpoint`'s artifact write logs a warning (`_graph_exec.py:115-118`), which goes nowhere durable (Finding 10).
- **SEVERITY:** High.
- **OPERATOR SCENARIO IT BREAKS:** Provider timeout mid-resume → pipeline silently takes the manual-advance fallback; gate bookkeeping (`approved`, candidate promotion) may diverge from what the graph would have done. Operator later sees an inconsistent project and has no artifact telling them an exception occurred, when, or with what message.
- **TARGET DESIGN:** Narrow the catch (resume-specific errors only); on catch always: `_logger.exception(...)`, `rt._record_audit("system", "resume_fallback", project_id=..., error=repr(exc))`. Replace bare `suppress(Exception)` with logged best-effort helper.
- **MIGRATION:** Trivial local change; add regression test asserting an audit ERROR row exists after a forced resume failure.
- **EFFORT:** S. **RISK:** Low.

### Finding 5 — Same failure renders differently per surface; exception types are lost at every boundary

Trace of the representative failure — **provider timeout during `start_generation_batch`**:

| Layer | What is recorded | Evidence |
|---|---|---|
| Adapter/executor | `except Exception as exc:` → ledger row `error_code="submit_failed"` (or `poll_failed`/`download_failed`), `blocking_reason=str(exc)[:200]`. Exception class gone, message truncated, stack nowhere. | `generation/executor.py:175-184, 229-233, 272-281, 386-394` |
| Failure taxonomy | `FailureClassifier.classify()` — which would map "timeout" → `DEGRADED` + resume guidance — has **zero callers**; provider health is only ever set *healthy* (`_provider_seeds.py:28,37`, `config/profile_resolver.py:196`, `mcp/tools/providers.py:32`). Classification is substring matching on already-flattened messages (`failure_classifier.py:143-159`). | grep: only import of helpers from `agents/runner.py:17` |
| MCP tool response | Uncaught exceptions → `MCPError(INTERNAL_ERROR, message=str(exc))`; no traceback logged, no audit event written, `request_id` not persisted anywhere correlatable. | `mcp/server.py:216-223` |
| TUI | Gateway converts failure envelope to `RuntimeError(str(result.get("error")))` — the machine-readable `MCPErrorCode` is discarded (`tui/gateways/mcp.py:163-168`); screens show `set_status(f"Generation failed: {exc}")` — one transient footer line, str-flattened (`tui/screens/studio.py:351, 377-378, 391-392, 461-463`). |
| Logs | Nothing (no handler configured; see Finding 10). |
| Audit log | Nothing — no audit event exists for failed operations; all 11 emit sites are success paths. |

Also on the LLM lane: the 3-attempt retry ladder ends in `{"status": "model_failure", "error": "all_retries_exhausted", ...}` with **the underlying exception text discarded entirely** (`agents/runner.py:300-309, 336-344`) — an operator cannot distinguish timeout from auth from quota.

- **SEVERITY:** High (this is the core "error surfacing" defect).
- **OPERATOR SCENARIO IT BREAKS:** "Why did my batch fail?" yields three different answers depending on which surface you check: a truncated string in the ledger, a generic `internal_error` over MCP, or a vanished footer line in the TUI — and nothing in the audit log or files.
- **TARGET DESIGN:** (a) Single `PipelineError(code, kind, cause_type, provider_id?, retriable)` hierarchy raised by adapters/executor; (b) MCP boundary logs `exc` with traceback (`_logger.exception`) before shaping response and records an audit `error` event with `{tool, error_code, cause_type}`; (c) wire `FailureClassifier` at the adapter boundary so classification happens on typed errors, not substrings; (d) preserve `MCPErrorCode` through the TUI gateway.
- **MIGRATION:** Boundary logging first (S), then error type preservation gateway-by-gateway, then classifier wiring.
- **EFFORT:** M. **RISK:** Medium — changing executor error codes affects ledger consumers/tests; keep codes additive.

### Finding 6 — `get_blockers` always returns empty: documented blocker tool is unwired

- **EVIDENCE:** `mcp/tools/state.py:77-82` reads `rt.get_blockers()` → filters `rt.block_entries` (`runtime.py:364-365`); the sole writer `add_blocker` (`runtime.py:367-377`) has **zero callers** in `src/`. Meanwhile `observability.BlockerReporter` (the designed mechanism) also has zero callers. Real blocking truth lives in graph-state `issues` surfaced via `get_orchestrator_summary` (`state.py:43-60`) and `compute_actions`.
- **SEVERITY:** High (documented operator contract lies).
- **OPERATOR SCENARIO IT BREAKS:** Operator guide instructs: *"see why approvals are blocked with `get_blockers`"* (`openclaw-mcp-operator-guide.md:73`). Today that returns `{blockers: [], has_blockers: false}` even when approval is blocked by blocking issues, pending revisions, or stall escalation — sending the operator to the wrong diagnostic.
- **TARGET DESIGN:** Either implement `get_blockers` from orchestrator truth (blocking issues + pending revisions + stalled phases + budget threshold, optionally materialized through the revived `BlockerReporter` with typed severities), or remove the tool and repoint docs to `get_orchestrator_summary`.
- **MIGRATION:** S — compute entries in `get_blockers` from `compute_actions(state)` + `issues`; keep response shape.
- **EFFORT:** S. **RISK:** Low.

### Finding 7 — Run forensics: "what ran, what decided, why blocked" is not answerable from persisted artifacts alone

Walking the actual artifacts for project X (post-run): `<root>/<project>/project-state.json`, `checkpoints.json`, `audit-log.json`, `.graph_state.json`, checkpoint `CheckpointState` blobs, generation ledger artifact.

Answerable today:
- *Which phases were approved & when:* audit-log.json (`approve_phase` rows with timestamps) — human gates only.
- *Which agents ran and rough routing reasons:* `_routing_decisions` handoffs preserved in `.graph_state.json` / latest checkpoint blob (`save_graph_state`, `_graph_exec.py:135-143`), rendered by `explain_agent_routing` (`mcp/tools/audit.py:48-68`). UNCERTAIN: `.graph_state.json` holds only the *latest* invocation's result — history survives only if a checkpoint blob captured it; interleaved runs overwrite.
- *Why blocked (partially):* `issues[]` + orchestrator summary fields (`state.py:43-60`).

Gaps (each independently evidenced):
1. **No run/correlation id.** `thread_id == project_id` (`_graph_exec.py:63-64`); multiple runs over one project are inseparable; audit events, handoffs, ledger rows share no id space. Ledger rows have ids but nothing links them to a graph invocation.
2. **No node timing.** Handoffs lack timestamps/durations (`_agent_handoff.py:137-148`); no `perf_counter`/monotonic capture anywhere under `graph/` or `generation/` (grep: only film-shot durations). The `duration_ms` field exists solely in the unused `AuditEvent`/`MetricsCollector`.
3. **Decision records incomplete.** 8 of 18 nodes emit nothing (Finding 3); `model_failure` collapses to `all_retries_exhausted` without cause (Finding 5).
4. **Checkpoint blobs are filed under the wrong phase.** Auto-checkpoints always persist `graph_state` under `phase="intake"` regardless of actual phase (`_graph_exec.py:101-106` hard-codes `FilmPhase("intake")`), so browsing checkpoints by phase misleads forensics.
5. **`explain_last_decision` ignores project scope** — returns `rt.audit_events[-1]` globally (`mcp/tools/audit.py:33-45`), so in a multi-project session it explains another project's event.
6. **Audit persistence rewrites the whole file per event** (`persist_audit_events` dumps all events each time, `_persistence.py:277-287`) — O(n²) I/O over a long-lived project and truncation risk on crash mid-write (no atomic rename).

- **SEVERITY:** High (aggregate — this is mission item 3's verdict: **not answerable today** without reconstructing from heterogeneous, partially overwritten artifacts).
- **TARGET DESIGN:** A per-run manifest: `run:{uuid}` created at each `run_graph`/resume entry, stamped onto every audit event, handoff, and ledger mutation issued within it; node start/end events with durations (Finding 3); correct checkpoint phase tagging; append-friendly persistence (JSONL or size-capped rotation).
- **MIGRATION:** run_id first (thread through config `configurable` + stamp at emit points — S); then lifecycle events (M).
- **EFFORT:** M overall. **RISK:** Low-medium (checkpoint blob growth; keep events out of resumed state channels).

### Finding 8 — Provider failure taxonomy and health states exist but are never fed

- **EVIDENCE:** `FailureClassifier.classify/update_health` (`providers/failure_classifier.py:135-166`) — zero production callers; `ProviderStatus.BLOCKED_QUOTA/CREDIT/AUTH`, `DEGRADED` reachable only from seeds. Runtime provider health is monotonic-healthy (grep in Finding 5 table). The e2e quota scenario (`tests/e2e/test_scenario_04_quota_exhausted.py`) exercises orchestration around blockers but nothing in `src/` derives those states from real adapter errors.
- **SEVERITY:** Medium-High (overlaps Finding 5; listed separately because it is a *wiring* gap, not a formatting gap).
- **OPERATOR SCENARIO IT BREAKS:** After a real quota exhaustion, `list_providers`/health views still say healthy; the orchestrator's `continue_unrelated_work` intelligence depends on blocked-provider state that no runtime path produces.
- **TARGET DESIGN:** Call `FailureClassifier.update_health` (typed-error variant) in the executor/adapters on every submit/poll failure; mirror to `rt.set_provider_health` and an audit `provider_health_changed` event.
- **MIGRATION:** Behind the same change as Finding 5(c).
- **EFFORT:** S once error types exist. **RISK:** Low.

### Finding 9 — Cost is estimated everywhere and recorded nowhere; budget gate routes on a frozen number

- **EVIDENCE:** `pricing.py:27-33` is authoritative and feeds planning prompts (`pricing_prompt_block`) — good. But: `GenerationLedgerRow.actual_cost_usd` is declared and **never written** (`schemas/generation.py:68`; grep shows only the declaration). `BudgetState.spent_usd` is initialized to `0.0` (`mcp/tools/planning.py:29`) and **never incremented** anywhere — yet the orchestrator's priority-5 `escalate_to_human` gate reads `threshold_exceeded` off it (writer `orchestrator_state.py:351-370`; live reader `is_budget_blocked` at `:374-377`, consumed by `_action_routing.py:239`). `status_rows()` reports the estimate under the label `cost_usd` (`executor.py:321`). The only cost aggregation APIs (`AuditTrail.total_cost_usd`, `MetricsCollector.total_provider_cost`) belong to dead classes. LLM-lane usage/tokens are never captured at all (`agents/model_adapter.py` has no usage extraction; `chat_json` returns parsed content only).
- **SEVERITY:** High for the stated flexibility ask (cost is currently *unobservable*, and a safety gate is a no-op).
- **OPERATOR SCENARIO IT BREAKS:** "What did this run spend?" — unanswerable; worse, "budget threshold exceeded → escalate_to_human" can never trigger because spend is structurally zero, silently disabling a documented safety behavior.
- **TARGET DESIGN (minimal seams):** (1) adapters return `usage`/actual-cost on job completion → executor writes `actual_cost_usd` (field already exists) and calls `rate_for(provider)` × delivered units as fallback; (2) one seam function `record_cost(project_id, run_id, node, usd)` in the runtime that both appends an audit cost row and updates `BudgetState.spent_usd`/`per_phase_spent_usd` (fields already exist, `schemas/budget.py:40-42`); (3) rename `status_rows` label to `estimated_cost_usd`.
- **MIGRATION:** Seam (2) is pure-additive and unlocks both reporting and the gate; do it before any dashboard work.
- **EFFORT:** M (adapter return-shape changes ripple). **RISK:** Medium — touching spend accounting affects gate tests; keep estimates as-is, make actuals additive.

### Finding 10 — Structured logging: consistent naming, zero configuration, ephemeral by design

- **EVIDENCE:** 14 modules use `logging.getLogger(__name__)` (consistent, idiomatic — `app/runtime.py:31`, `app/_graph_exec.py:28`, `agents/runner.py:27`, etc.), but there is **no `basicConfig`/`dictConfig`/handler/file anywhere** under `src/` (grep confirms; MCP transport, CLI, TUI entrypoints configure nothing). Default root behavior = WARNING+ to stderr only. Consequently the retry-ladder warnings (`runner.py:155-160, 241-257, 283-299, 319-343`) and auto-checkpoint warnings (`_graph_exec.py:116-117`) are lost unless the embedding host (OpenClaw/TUI subprocess) happens to capture stderr, and no INFO-level operational detail ever exists. `print()` usage is confined to CLI/smoke/stdio-bootstrap (acceptable: `cli/run.py`, `app/smoke.py`, `mcp/_stdio_transport.py:111-132`; stdio protocol requires stdout purity, stderr prints are fine). No structlog/loguru.
- **SEVERITY:** Medium.
- **OPERATOR SCENARIO IT BREAKS:** "Attach the logs" — there are no logs; post-mortems depend entirely on the sparse audit-log.json and whatever stderr the host retained.
- **TARGET DESIGN:** One `logging.config.dictConfig` in the server bootstrap (`mcp/server.py:main`) and TUI app start: level via env (`FILM_PIPELINE_LOG_LEVEL`), a rotating file handler under the project runtime root (or `FILM_PIPELINE_LOG_FILE`), `%(asctime)s %(name)s %(levelname)s` format; keep stderr at WARNING for stdio safety.
- **MIGRATION:** Purely additive bootstrap change; no call-site edits.
- **EFFORT:** S. **RISK:** Low (mind stdio transport: never log to stdout).

### Finding 11 — Audit store operational quirks (minor but compounding)

- **EVIDENCE:** Full-file rewrite per event (`_persistence.py:277-287`, no atomic tmp+rename); restore dedups by `event_id` and sorts by string timestamp (`_persistence.py:257-261`) — ISO UTC strings sort correctly today, but mixed-offset timestamps would sort wrongly; events whose `details` lack `project_id` are never persisted yet stay queryable in-memory until restart (`runtime.py:294-296` gate) — silent divergence between what `get_audit_log` shows live vs after restart.
- **SEVERITY:** Low-Medium.
- **OPERATOR SCENARIO IT BREAKS:** Long-running project → audit write cost grows quadratically; crash during rewrite can lose the log; operator comparing pre/post-restart `get_audit_log` output sees events disappear.
- **TARGET DESIGN:** Atomic write (tmp + `os.replace`); either stamp `project_id` top-level on every event or refuse to record unscoped events; optional size cap/rotation.
- **EFFORT:** S. **RISK:** Low.

---

## Top-3 priorities

1. **Stop losing failures (Findings 4 + 5 + 8):** log-with-traceback + audit `error` events at the MCP boundary and resume fallback; preserve exception types/codes end-to-end (executor → MCP → TUI); wire the already-written `FailureClassifier` into the executor and provider health. Smallest effort, largest forensic payoff, closes the "same failure looks different everywhere" hole.
2. **One typed event catalog + single audit implementation (Findings 1 + 2):** Pydantic `AuditEvent` + `AuditActionKind` StrEnum owned by `observability/`, used by `StudioRuntime._record_audit`; delete/absorb the dead `AuditTrail`/`MetricsCollector`/`BlockerReporter`. This retroactively makes D-007-class bugs unrepresentable and gives every later finding (run ids, costs, node events) a schema to land in.
3. **Run correlation + node lifecycle events (Findings 3 + 7):** mint `run_id` at each graph invocation/resume, emit `node_start/node_end` (with `duration_ms`, `ok`, `error_kind`) from the three runtime entry points, tag checkpoint blobs with the true phase. This is what makes "for project X run Y: which nodes ran, what decided, why blocked" answerable from disk.

*(Finding 9's `record_cost` seam rides along with #3's plumbing and should be treated as the first payload of the catalog.)*

## UNCERTAIN markers

- **UNCERTAIN:** exact behavior of each agent impl when handed a `model_failure` output dict — some impls may degrade gracefully rather than fail; I did not trace all of `agents/impl/*`.
- **UNCERTAIN:** whether `.graph_state.json`/checkpoint blobs retain full multi-invocation handoff history or only the last invocation's slice (dedup logic in `_is_duplicate_handoff` implies replay awareness, but overwrite semantics of `save_graph_state` suggest last-write-wins).
- **UNCERTAIN (given, not re-derived):** "approval autonomous branch observable only via scripted e2e" — accepted per briefing; consistent with `approval.py:69-87` leaving no dedicated autonomous-decision record, but I did not audit every scenario test.
- **UNCERTAIN:** whether deployment hosts (OpenClaw wrapper) capture server stderr into files externally, which would soften Finding 10's impact in practice though not in-repo.

## Evidence index (primary)

`observability/{__init__,audit,blockers,metrics}.py` · `app/runtime.py:48,117,162,201,265,284-296,335,364-377` · `app/_persistence.py:24,152,252-261,277-287` · `app/_graph_exec.py:40-76,101-106,114-118,125,181-183,214,262,304` · `mcp/server.py:216-223` · `mcp/tools/state.py:77-82` · `mcp/tools/audit.py:24-68` · `mcp/tools/projects.py:121` · `mcp/tools/_profile_change.py:333` · `mcp/tools/reference_generation/tool.py:63` · `generation/executor.py:175-184,229-233,272-281,308-332,386-394` · `schemas/generation.py:50-80` · `agents/runner.py:202-382` · `agents/model_adapter.py` · `providers/pricing.py:27-52` · `providers/failure_classifier.py:135-166` · `graph/graph.py:108-129` · `graph/nodes/_agent_handoff.py:105-149` · `graph/nodes/wrapup.py:19-44` · `graph/nodes/approval.py:193-240` · `graph/orchestrator_state.py:205-236` · `tui/gateways/mcp.py:163-168,283-293` · `tui/screens/studio.py:102-130,340-400,450-475` · commit `1a61b9e` (D-007)
