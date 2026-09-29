# Functional boundaries: organize by operator outcome

Date: 2026-09-29. Source revision: `83441607a4c5` (`improve-modular-2`), clean tree before this document. Scope: current `src/film_pipeline/`, relevant tests, [architecture blueprint](../../documentation/architecture-blueprint.md), and [product standard](../../documentation/product-completion/00-product-standard.md). This is a research and decision proposal, not an implemented migration or a claim of product readiness.

## Decision

**Use functional ownership for workflows, while keeping the stable technical mechanisms shared.** A functional module owns an operator outcome and its rules: for example, *plan a clip, submit it, poll it, deliver its output, and advance its durable ledger*. MCP remains the operator transport and safety boundary; LangGraph remains the phase orchestration engine. Storage, provider adapters, checkpoint machinery, and broadly shared schemas remain infrastructure. Moving every file into a phase folder would add imports and duplicate these mechanisms.

This refines [03 — One use-case layer](03-one-use-case-layer.md), whose reference-generation and profile-change moves have since landed. It does not revive the superseded per-package import law in [modular architecture 03](../modular-architecture/03-target-architecture.md). The adopted [independent decision](../modular-architecture/06-independent-review-and-decision.md#4-target-shape) treats the package map as ownership, not an allowed-import table.

The unit of improvement is **one user-visible action with one policy owner**, rather than a directory rename. Start with clip generation, then settle the intended scope of validation, where current code contains parallel workflow paths. Keep `StudioRuntime` as composition for now: the [current remeasurement](08-studioruntime-remeasured.md) found 29 public methods and eight concerns, but did not establish that splitting its facade improves the consumer contract.

## What I checked

The current source has 20 top-level packages under `src/film_pipeline/`. Running `uv run python docs/modularity-improvements/measure.py` at the revision above reports `mcp` with outbound imports to 16 distinct packages, `studio` to 11, and `orchestration` to 9; 75 MCP tools have input schemas. These figures describe coupling, not defects. The script also finds two module-level strongly connected components when it includes lazy imports; [AGENTS.md](../../AGENTS.md) explains why a cycle-required lazy import must not be hoisted casually.

I traced two outcomes through their transport, service, persistence, and tests. The observations below are source-level facts. Where operator impact needs an executable comparison, I label that as a test to write before changing code.

| Outcome | Transport / orchestration | Functional rules and durable state | Boundary assessment |
|---|---|---|---|
| Validate a project | [`mcp/tools/validation.py:267`](../../src/film_pipeline/mcp/tools/validation.py) and [`orchestration/execution.py:411`](../../src/film_pipeline/orchestration/execution.py) | [`nodes/qc.py:61`](../../src/film_pipeline/orchestration/nodes/qc.py), [`qc_steps.py`](../../src/film_pipeline/orchestration/qc_steps.py), validators and artifact reports | Two paths select validators and record outcomes; see F1. |
| Produce a clip | [`mcp/tools/generation/dispatch.py:134`](../../src/film_pipeline/mcp/tools/generation/dispatch.py) | [`generation/executor.py:132`](../../src/film_pipeline/generation/executor.py), [`generation/ledger.py:52`](../../src/film_pipeline/generation/ledger.py), [`executor_delivery.py`](../../src/film_pipeline/generation/executor_delivery.py) | MCP reimplements part of the lifecycle; see F2. |
| Generate visual references | [`mcp/tools/reference_generation/tool.py`](../../src/film_pipeline/mcp/tools/reference_generation/tool.py) | [`generation/reference/`](../../src/film_pipeline/generation/reference) owns retries, outcomes, composites, and index files | A functional subpackage already exists; the tool still coordinates the workflow. See C1. |
| Review and approve | [`mcp/tools/review.py`](../../src/film_pipeline/mcp/tools/review.py) | [`governance/generator.py`](../../src/film_pipeline/governance/generator.py), [`orchestration/execution.py:377`](../../src/film_pipeline/orchestration/execution.py) | Approval is tied to graph progress, audit, checkpoints, and human gating; preserve that transactional path. |

### F1 — Validation has two workflow owners

`mcp.tools.validation.run_validation` branches only for `visual_dev` and `script` at [lines 283–289](../../src/film_pipeline/mcp/tools/validation.py). For other phases it returns “No validators found for this phase.” It constructs and saves reports in the tool, then writes `_validation_reports` and `validation_refs` to project state at [lines 253–265](../../src/film_pipeline/mcp/tools/validation.py). The graph-facing `orchestration.execution.run_validation` instead calls the QC validator chain and handles issues and matrix updates at [lines 411–480](../../src/film_pipeline/orchestration/execution.py). The MCP report reader has a broader live validator table at [lines 113–165](../../src/film_pipeline/mcp/tools/validation.py), which makes the write and read paths different even within the tool module.

**Drift proof:** add a validator for a phase other than `script` or `visual_dev` in the graph/QC path; the MCP `run_validation` branch still returns no validators, and its existing unit tests cover those two success phases and the no-validator branch independently ([`test_validation.py:23–90`](../../tests/unit/mcp/tools/test_validation.py)). The product standard requires validators to block downstream work. This is a **confirmed split in selection and persistence logic**; whether a particular phase already causes an operator-visible mismatch needs a shared-project behavior test. The direct symptom is more important than whether `validation` or `orchestration` gets the final directory name.

**Functional target:** one current-project validation operation returns a typed outcome containing reports, issue changes, artifact refs, and any matrix patch. Graph and MCP call the same policy; the MCP tool only parses the request and presents the result. Keep validator implementations in `validation`, phase routing in `orchestration`, artifact writes in `storage`. Place the operation where it can consume these dependencies without creating a package cycle; choose the exact file only after an import-cycle and call-site check. First pin what `run_validation` should do for each phase, including QC, and test MCP and graph against the same persisted project. If the two actions intentionally have different scope, name and document that difference explicitly instead of forcing false parity.

### F2 — Clip generation has parallel submit and poll lifecycles

`GenerationExecutor.start` and `poll_once` own submission, status transitions, and completion. On provider completion, [`executor.py:254–294`](../../src/film_pipeline/generation/executor.py) calls `deliver_completed_job`, records `output_refs`, and sets `next_action="validate"`. The MCP `start_generation_batch` at [`dispatch.py:134–166`](../../src/film_pipeline/mcp/tools/generation/dispatch.py) constructs an executor only to load shot rows and resolve prompts, then submits each row itself. Its `resume_generation_polling` at [`dispatch.py:211–251`](../../src/film_pipeline/mcp/tools/generation/dispatch.py) maps a completed provider status directly to `COMPLETED` and updates the ledger without calling the delivery path or writing `output_refs`. The existing status-mapping test checks the response id, not delivered output ([`test_generation.py:397–436`](../../tests/unit/mcp/tools/test_generation.py)).

**Drift proof:** if the provider reports `completed` to the MCP poller, its code can mark the ledger row complete without the output delivery that the executor requires. This is a source-level divergence in durable representation. The provider and storage conditions under which it manifests should be demonstrated with a mock-provider characterization test before a production edit. It directly threatens the product contract that a validated clip is a real output, and the [generation standard](../../documentation/product-completion/05-generation-providers-and-post.md) explicitly requires recoverable submit/poll/download transitions.

**Functional target:** `generation` owns plan, submit, poll, cancel, delivery, and ledger transitions through one application-facing interface. The MCP handlers retain schema validation, confirmation, and response projection. Start with poll/completion parity, then submit parity; do not move files simply to put all generation code under one directory. A successful test must assert the persisted ledger status, `output_refs`, actual mock output, duplicate-prevention on resume, and failure handling after a provider accepted a job. Avoid a real paid provider in this proof.

### C1 — Visual-reference generation is a useful boundary with a remaining coordination seam

The prior program moved retry, outcome, composite, and index operations into `generation/reference/`. The current MCP [`tool.py:1–145`](../../src/film_pipeline/mcp/tools/reference_generation/tool.py) still chooses inputs and provider, runs the per-entry loop, persists the updated index, publishes project refs, and records audit. Its 242 lines do not themselves prove misplaced ownership. It is a **candidate**, because a change to the reference-generation lifecycle still spans the tool and the functional subpackage. Before moving more, compare those responsibilities with any graph entry path and write one use-case test with no MCP context. Keep request parsing and presentation in MCP; move only policy that another entry point needs or that could silently diverge. The test split proposed in [03](03-one-use-case-layer.md) has not been established by the current source inspection.

## Why the split arose (five whys)

1. **Why can one outcome behave differently by entry path?** MCP handlers and graph/runtime functions each execute parts of validation or generation.
2. **Why is logic present in transport?** The original implementation packages were organized around mechanisms (`mcp`, `orchestration`, `validation`, `generation`), so the operator action had no single end-to-end owner.
3. **Why did the second path persist?** Shared helpers cover small pieces (for example, the generation ledger and prompt resolution), but neither entry point must call one complete operation.
4. **Why did tests not expose the gap?** The cited tests check per-path responses and statuses; they do not assert equivalent persisted outputs for a completed action.
5. **Why would a broad package reshuffle fail to cure it?** Relocating files changes import paths while both callers can still implement the lifecycle independently. The repair is one authoritative transition with a behavior test at each entry path.

This is a causal hypothesis grounded in the two traced workflows, not a claim that every package has the same defect.

## Practical module shape

Treat a feature as an **owned operation**, with the least structure needed to keep its invariant in one place:

```text
MCP / CLI request
    -> shared MCP dispatch: identity, typed args, active project, confirmation
    -> functional operation: validate, approve, generate, or restore
    -> shared mechanisms: graph, storage, providers, checkpoints
    -> one persisted result, then transport response
```

The full pipeline suggests the following ownership map. It is a map of **change reasons**, not a proposal to create seven new packages:

| Functional area | Current home | Present decision |
|---|---|---|
| Project setup and profile choice | `projects`, `config`, `mcp/tools/projects.py`, `mcp/tools/_profile_change.py` | Keep the existing owners; reopen only on a reproduced second policy path. |
| Creative development and shot planning | `agents`, `orchestration/nodes`, `governance`, feature schemas | Keep phase nodes together while the shared repair loop and services couple them. |
| Visual references | `generation/reference`, `mcp/tools/reference_generation` | Re-measure C1 after the two correctness seams. |
| Clip generation and handoff | `generation`, `mcp/tools/generation`, `providers` | Consolidate lifecycle in `generation`; keep provider adapters shared. |
| Quality and human decision | `validation`, `orchestration/qc_steps.py`, `governance`, `mcp/tools/validation.py`, `mcp/tools/review.py` | Clarify validation scopes and make each transition authoritative; retain MCP confirmation and graph approval. |
| Recovery and durable evidence | `checkpoints`, `storage`, `studio` | Keep as shared mechanisms; verify their use from each functional operation. |
| Post-production | `post` | Leave in place; [the current product standard](../../documentation/product-completion/00-product-standard.md) excludes final assembly and delivery packaging from completion scope. |

| Keep shared | Prefer functional ownership | Do not preemptively move |
|---|---|---|
| `mcp` dispatch, tool contracts, response envelopes | Clip job lifecycle in `generation`; reference lifecycle in `generation/reference`; review-package policy in `governance` | Every `mcp/tools/*` file: a thin adapter naturally belongs to MCP. |
| `orchestration` graph and phase-node execution | Current-project validation operation with one result contract | Every phase node into its own package: [07](../modular-architecture/07-module-decomposition-analysis.md#3-orchestration-should-not-be-split) measured shared node infrastructure and repair-loop coupling. |
| `storage`, `providers`, `checkpoints`, `filmspec`, shared `schemas` | Feature-specific contracts only when they have one clear owner and consumers | All schemas into feature folders: the existing schema package is nearly uncoupled internally, and moving it en masse removes little coupling. |
| `studio` composition and runtime lifecycle | A new operation exposed through existing owners when it closes a demonstrated parallel path | One collaborator per `StudioRuntime` concern: the [measured split](08-studioruntime-remeasured.md) was deferred for concrete reasons. |

The organizing question for each change is: **if this rule changes, which single operation should change, and which entry paths must prove the same persisted result?** Folder names are a consequence of that answer.

## Recommended sequence and exit checks

1. **Pin outcomes before moving code.** For generation, mock a completed provider job and compare MCP polling with `GenerationExecutor.poll_once`, including delivered output. For validation, run the same project through MCP and graph and compare reports, issues, refs, matrix patches, and refusal behavior. Record intended differences instead of assuming perfect parity.
2. **Consolidate clip poll/completion, then submit.** Route the MCP actions through generation's lifecycle. Keep existing tool names and envelopes. Exit when a completed row always has delivery evidence, and retry/resume does not duplicate a provider submission or artifact.
3. **Consolidate validation one transition at a time.** Make the operator-visible validation action invoke the chosen functional operation once its intended phase scope is decided. Remove the superseded branch and its parallel report writer. Exit when mutation of validator selection or report persistence fails a test on both entry paths.
4. **Re-measure C1.** Move remaining reference policy only if a no-MCP use-case test or a second consumer demonstrates value. Otherwise leave the adapter where it is.
5. **Re-measure architecture, not only file counts.** For each production slice: run relevant tests and the full `make ci-check`, `uv run mypy src tests`, and the docs-local Enola gate before and after commit. Check package acyclicity and the lazy-import guard. Verify persisted-data compatibility and the mock MCP operator path. A new package is justified only if the resulting public contract is smaller and there is no new cycle or duplicated lifecycle.

## Boundaries and uncertainty

- This report changed no production code or tests and did not run a full MCP workflow. F1 and F2 are proven source-path divergences; their exact operator-visible effects and safe repair shape require the characterization tests above.
- No throughput or performance estimate is implied by package fan-out. `mcp` has a large fan-out because it adapts many operations; reducing that count is not an objective by itself.
- The existing architecture tests enforce cycles and selected private reach-ins, not a universal layering law. A feature-oriented design should preserve those guards and add behavior checks where a duplicated lifecycle can escape them.
- Human approval, audit, checkpoint recovery, storage compatibility, and mock-mode output evidence are product contracts. Any consolidation must preserve them at the MCP boundary.

## Verification on this docs change

- Focused generation and validation unit/integration suites: pass (`uv run pytest -q --no-cov tests/unit/mcp/tools/test_generation.py tests/unit/generation/test_executor.py tests/unit/mcp/tools/test_validation.py tests/integration/test_generation_mcp.py tests/integration/test_validation_runtime.py`). They establish the current baseline, not F1/F2 parity.
- `make ci-check`: pass; 2,349 passed, 8 skipped, 1 xfailed, 91.92% coverage, build and product gate pass.
- Docs-local `enola check --baseline=docs/modular-architecture/enola-out docs/modular-architecture/enola-config.yaml`: exit 0. Its advisory output is not a feature-boundary proof.
- All relative links in this report resolve; `git diff --check` is clean.
