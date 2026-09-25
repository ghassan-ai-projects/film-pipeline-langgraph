# Audit 05 — Provider runtime: registry, credentials, health, failure classification, cost

Audited at `modular-app` = `fb85baa0e6b769b709791a96a89980089304bf13`
(short `fb85baa`). Method: full source reads of `providers/**`, `agents/model_adapter.py`,
`agents/model_routing/**`, `graph/services.py`, `graph/_action_routing.py`,
`graph/orchestrator_state.py`, `graph/nodes/generation.py`,
`graph/nodes/_generation_batch_planning.py`, `generation/executor*.py`,
`generation/ledger.py`, `generation/gemini_client.py`, `mcp/tools/providers.py`,
`mcp/tools/generation/dispatch.py`, `mcp/tools/reference_generation/**`,
`app/runtime.py`, `app/_provider_seeds.py`, `app/health.py`, `app/bootstrap.py`,
`app/mock_responses.py`, `app/services/operator.py`, `app/services/_generation_ops.py`,
`app/services/_browse_ops.py`, `config/profile_resolver.py`, plus
`tests/unit/providers/**` and the health/routing tests. Every finding has an executed
reproduction or an executed grep whose output is quoted.

Test execution performed in this audit (`.venv/bin/python -m pytest --no-cov`):
`tests/unit/providers` → **98 passed**; `tests/unit/graph/test_orchestrator_state.py
tests/unit/graph/test_router_blockers.py tests/unit/mcp/tools/test_providers.py
tests/unit/app/services/test_operator_service.py` → **80 passed**. `make ci-check`
was **not** run (the `uv` cache is outside the sandbox's writable roots); the suite
above is the executed subset. Every "no test fails because Z" claim below is
grounded on a recorded grep showing the pairing is unreferenced by any test, not on
a full-suite run.

## Verification record (revision 2)

This file was independently verified by a second agent that did not write it;
results are in `docs/modular-architecture/reviews/verify-05.md`. Verdicts on the
seven findings of revision 1: **7/7 CONFIRMED in substance, 0 rejected**; 1 class/severity
defect (F-PROV-07 → **DOWNGRADED in part**) and 1 overstated evidence sentence (F-PROV-04)
plus 7 disputes (D1–D7) were returned to this author. All were re-checked against
HEAD in this revision and resolved. Revision 2 carries **8 findings — 1 Critical, 7 High,
0 Medium** (F-PROV-08 was added from verifier seam M1).

| Item | Verdict as returned | Resolution in this revision |
|---|---|---|
| F-PROV-01 | CONFIRMED | D1 anchor corrected to `:130-133`; D4 clause rewritten; M3 folded in (the provider-health representation count is now **five**, not four) |
| F-PROV-02 | CONFIRMED | unchanged |
| F-PROV-03 | CONFIRMED | D2 anchor corrected to `providers/factory.py:44`; M4 folded in (reader-side `Mapping[str, Any]` sites) |
| F-PROV-04 | CONFIRMED with corrections | overstated "never asserts a policy" sentence replaced with the accurate pinning gap; class changed to **O5 + O7** (D7); call-site count stated honestly as 14 credential + 1 non-credential |
| F-PROV-05 | CONFIRMED | D3 anchor corrected to `:62-68`; D6 module/site count reconciled in the title |
| F-PROV-06 | CONFIRMED | unchanged |
| F-PROV-07 | DOWNGRADED in part | O3 clause struck (D5); severity corrected to **High (3×3=9)**; mock-mode scope corrected; M2 folded in, which is what makes impact 3 (not 2) the honest rating |
| F-PROV-08 | *not present in revision 1* | added from verifier M1 (provider endpoint declarations have no owner) |

One verifier figure is not reproduced as stated and is recorded here rather than
silently adopted: `verify-05.md` disaggregates the credential grep as "13 credential
plus 1 base-URL site"; the command below measures **14 credential-resolution sites
plus 1 non-credential base-URL read** across 8 modules. The verifier's *point* (the
"14" conflated a credential read with a `ZAI_BASE_URL` read) is correct and is fixed;
only the arithmetic differs.

**Post-verification addition (not independently verified).** The adversarial coverage pass
(`reviews/adversarial-coverage.md` §H2) surfaced one further concern inside this audit's
declared scope, which this author re-verified against `fb85baa` and records as
**F-PROV-09**. **Findings after this revision: 9 — 1 Critical, 8 High, 0 Medium**
(revision 2's verified eight plus this pending one). Existing verdicts above are unchanged.
- **Added post-verification (PENDING VERIFICATION):** F-PROV-09 — the provider wait budget is
  declared in four `POLLING_CONFIG` keys but only `initial_delay_seconds` is read;
  `poll_interval_seconds`, `max_wait_seconds` and `backoff_multiplier` are dead, and neither
  poll path enforces a deadline (adversarial coverage §H2; High 3×5=15; must be re-checked by
  the second-round verifier).

---

## Coverage

| Scope (task-mandated) | Verdict |
|---|---|
| `providers/**` — all 14 files incl. `adapters/*`, `failure_classifier.py`, `credentials.py`, `health*.py`, mock providers | audited — findings F-PROV-01/02/03/04/05/07/08/09; §"Clean concerns" |
| `agents/model_adapter.py` | audited — F-PROV-04 (credential aliasing), F-PROV-05 (model-id literals), F-PROV-08 (inlined Gemini endpoint + `OPENROUTER_API` cross-layer import); no registry/health ownership |
| `agents/model_routing/**` | audited — F-PROV-05 (`_FALLBACK_PROFILES` duplicates `profiles/base.studio.yaml`); routing itself is single-owner (clean) |
| `graph/services.py` (provider wiring) | audited — clean: constructs `ModelAdapter()`/`ModelRouter()`, holds **no** provider registry or health (F-PROV-01 blast radius) |
| `graph/_action_routing.py` (provider-health decisions) | audited — `_blocked_providers_result` is the single decision site, and it consumes an always-empty snapshot (F-PROV-01) |
| `graph/nodes/visual.py` | audited — no provider calls; only `provider_plan_ref`/`provider-planning-agent` string references (`:525`, `:539`, `:602`). Clean, out of concern. |
| `graph/nodes/generation.py` | audited — clean of direct provider calls; ledger planning only (F-PROV-06 boundary) |
| `generation/*.py` (provider use) | audited — `executor.py` (F-PROV-02/06/07/09), `executor_delivery.py` (clean: consumes `BaseProviderAdapter`, no health/credential logic), `ledger.py` (F-PROV-07), `gemini_client.py:26` (F-PROV-04) and `:13` (F-PROV-08) |
| `mcp/tools/` (provider/health/quota tools) | audited — `providers.py` (F-PROV-01/03), `generation/dispatch.py` (F-PROV-06/09), `reference_generation/index_files.py:62` (F-PROV-05), `registry.py`/`state.py`/`config.py`/`audit.py` (read-only consumers, clean) |
| `app/services/operator.py` (provider parts) | audited — `:193` mode-switch re-seed, `:252` dashboard read, `:419` `list_provider_status` delegation (all F-PROV-01 consumers) |
| `config/*.py` (provider config) | audited — `profile_resolver.py` (F-PROV-03/04); `validator.py` is budget-only, provider-free (cluster 12) |
| `app/runtime.py`, `app/_provider_seeds.py`, `app/health.py`, `app/bootstrap.py`, `app/mock_responses.py` | audited — the de-facto production owner of registry+health; F-PROV-01/03/07 |
| "quota tools" / quota accounting | audited — **there is no quota accounting module at all**; grep `quota` in `src/` returns only enum/message/field declarations. This is *unfinished work*, not distributed ownership (§1.3), so it is recorded under "Unverified hypotheses" rather than as a finding |
| `tests/unit/providers/**` (guard-test inventory) | audited — §"Clean concerns" records which agreements are pinned and which are not |

| Grep target (task-mandated) | Result |
|---|---|
| `provider` | 1,000+ hits across `providers`, `app`, `mcp`, `graph`, `generation` — sampled and walked by call graph, not by count |
| `healthy` / `health` | 42 hits in `src/`; all routed to the five representations in F-PROV-01 |
| `quota` | 10 hits in `src/`, **zero** writes to any quota counter |
| `rate_limit` | **0 hits** in `src/` |
| `credential` | `providers/credentials.py` + 7 consumer modules (F-PROV-04) |
| `api_key` | `credentials._env_var_for` + 6 private `_api_key()` methods + `ModelAdapter` ×3 |
| `capabilit` | 40 hits; **all** are agent capabilities — `ProviderCapabilities` has zero readers outside `factory.py` (F-PROV-05) |
| `failure_class` | 1 defining module + 0 production callers (F-PROV-02) |
| `retry` | `agents/runner.py` ladder + `reference_generation/retry_loop.py` + `failure_classifier.compress_prompt_for_retry` — three independent retry policies |
| `poll(` | `providers/adapters/*`, `generation/executor.py:239`, `mcp/tools/generation/dispatch.py:170`, `reference_generation/retry_loop.py:91` |

---

## Findings

### F-PROV-01 — Provider health has five representations, three writers, and neither checkpointed channel has a producer
- **Class:** O3 (split state authority) + O1 (duplicated normative model)
- **Severity:** Critical (impact 4 × drift 5 = 20)
- **Concern:** which single state holds "is provider P available", who writes it, and what the graph routes on.
- **De-facto owners:**
  - `src/film_pipeline/app/runtime.py:51` — the production live state, stringly typed —
    `"    provider_health: dict[str, Any] = field(default_factory=dict)"`
  - `src/film_pipeline/app/runtime.py:386-387` — its only production writer —
    ```python
    def set_provider_health(self, provider_id: str, status: str, reason: str = "") -> None:
        self.provider_health[provider_id] = {"status": status, "reason": reason}
    ```
  - `src/film_pipeline/providers/health.py:11-23` — a typed record that production never touches —
    `"@dataclass\nclass ProviderHealth:"` with `"    quota_remaining: int = -1  # -1 = unknown / unlimited"`
  - `src/film_pipeline/schemas/provider_health.py:13-20` — a second typed record —
    `"class ProviderHealthState(MutableSchemaBase):"` / `'    quota_state: Literal["ok", "low", "exhausted"]'`
  - `src/film_pipeline/graph/orchestrator_state.py:406-410` — the checkpointed graph copy —
    `"def update_provider_health(state: dict[str, Any], provider_id: str, health: dict[str, Any]) -> None:"`
  - `src/film_pipeline/graph/orchestrator_state.py:130-133` — the repo's own admission that nothing writes it —
    ```python
        _PROVIDER_HEALTH_SNAPSHOT,
        "explicit",
        "dormant writer; wiring decided in D13/P1 (provider health)",
    ```
  - `src/film_pipeline/graph/state_schema.py:178` — a **fifth** representation: a declared
    public graph channel with no accessor, no writer and no reader anywhere —
    `"    provider_health_snapshot: dict[str, object]"`
  - `src/film_pipeline/graph/state_schema.py:195` — the namespaced channel that
    `orchestrator_state` actually addresses —
    `"    _orchestrator__provider_health_snapshot: dict[str, dict[str, Any]]"`
- **Drift proof (existing divergence, executed):** the same real-mode runtime reports
  four *healthy* providers when launched from the repository root and four
  *unconfigured* providers when launched from `/tmp`, with an identical environment —
  and in neither case can the graph see any of it. `graph/_action_routing.py:228`
  reads `ostate.get_blocked_providers(state)`; nothing in `src/` ever calls
  `ostate.update_provider_health`, so
  `grep -rn "update_provider_health" src/` returns only its own definition, and
  `_blocked_providers_result` (`_action_routing.py:226-235`) can never fire in
  production. The sides that must agree are worse than a simple pair: **two graph
  channels** (`graph/state_schema.py:178`, a public `provider_health_snapshot` no code
  addresses, and `:195`'s namespaced `_orchestrator__provider_health_snapshot`) plus
  **three stores** (`runtime.provider_health`, `providers/health.py`,
  `schemas/provider_health.py`) all describe one logical state, and the only writer of
  any graph channel is a function with no caller. Executed at HEAD:
  `grep -rn "provider_health_snapshot" src/` returns exactly the two schema
  declarations plus the `orchestrator_state.py:413/420` accessors for the namespaced
  one — the `:178` channel is never named again.
  Reproduction (both halves executed at HEAD):
  ```bash
  # (a) producers of the graph snapshot in src/ — none
  grep -rn "update_provider_health" src/ --include=*.py
  # (b) runtime health is written only by seed/resolve paths, never mirrored
  grep -rn "set_provider_health(" src/ --include=*.py | grep -v "def set_provider_health"
  # (c) both declared channels, and the absence of a writer for the public one
  grep -rn "provider_health_snapshot" src/ tests/ --include=*.py
  # (d) executed: same env, different cwd -> different health truth
  cd ${REPO_ROOT} && \
    PYTHONPATH=src .venv/bin/python -c "import tempfile,pathlib;from film_pipeline.app.runtime import StudioRuntime;\
    rt=StudioRuntime(server_mode='real',runtime_root=pathlib.Path(tempfile.mkdtemp()));rt.seed_default_provider_health();\
    print({k:v['status'] for k,v in sorted(rt.provider_health.items())})"
  cd /tmp && PYTHONPATH=${REPO_ROOT}/src \
    ${REPO_ROOT}/.venv/bin/python -c "import tempfile,pathlib;\
    from film_pipeline.app.runtime import StudioRuntime;\
    rt=StudioRuntime(server_mode='real',runtime_root=pathlib.Path(tempfile.mkdtemp()));rt.seed_default_provider_health();\
    print({k:v['status'] for k,v in sorted(rt.provider_health.items())})"
  ```
  Also an existing vocabulary divergence: `ProviderStatus`
  (`src/film_pipeline/schemas/_base.py:156-165`) declares exactly 7 members ending at
  `DISABLED_BY_USER = "disabled_by_user"`, but `src/film_pipeline/app/_provider_seeds.py:30-34`
  writes a value outside the model —
  ```python
  rt.set_provider_health(
      provider_id,
      "unconfigured",
      "API credentials not set",
  )
  ```
  `ostate.get_healthy_providers` (`orchestrator_state.py:438-443`) accepts only
  `("healthy", "degraded")` and `is_provider_blocked` (`:418-425`) only
  `startswith("blocked_")`, so an unconfigured provider is simultaneously not
  healthy and not blocked — invisible to every routing decision.
- **Reproduce:** `grep -rn "provider_health\|ProviderHealth" src/ --include=*.py` and the four commands above.
- **Blast radius:** `app/runtime.py`, `app/_provider_seeds.py`, `app/health.py`,
  `mcp/tools/providers.py`, `mcp/tools/state.py`, `app/services/operator.py`,
  `graph/_action_routing.py`, `graph/orchestrator_state.py`, `graph/state_schema.py`,
  `generation/executor.py`, `mcp/tools/generation/dispatch.py`. User-visible: the
  dashboard and `list_providers` report `healthy`, `blocked_quota`, or `unconfigured`
  from a raw dict; generation is dispatched on blocked providers; the "provider-blocked
  generation" route and the resume path (`resolve_provider_block`,
  `mcp/tools/providers.py:27-33`) are unreachable or vacuous.
  On `check_readiness()` (`app/health.py:17-24,36-51`) the defensible statements are
  narrower than revision 1 claimed: (a) it has **no production caller** —
  `grep -rn "check_readiness" src/` returns only its own definition at `health.py:17`,
  and its only callers are tests (`tests/unit/app/test_app_ops.py:149,175,198,220`) —
  and (b) it reads the **runtime dict** via `rt.get_provider_health(pid)`
  (`app/health.py:47`), never the unwritten graph snapshot, so a readiness report can
  disagree with what the graph would route on. The runtime dict it reads *is* maintained
  (`app/_provider_seeds.py:28,30,37`, `config/profile_resolver.py:196`,
  `mcp/tools/providers.py:32`); "no code path maintains it" was wrong and is withdrawn.
- **Candidate owner module:** `provider-health` — one typed health record, one writer,
  one persisted representation, and the classify→transition rule.
- **Extraction sketch:** move `ProviderHealth`/`ProviderHealthState` into one Pydantic
  model (keep the 7 `ProviderStatus` members; add an explicit
  `UNCONFIGURED` or model "unconfigured" as `blocked_auth` with a reason string);
  make `StudioRuntime` hold a `ProviderHealthTracker`-shaped owner instead of a dict;
  replace `ostate.update_provider_health` with a snapshot materialized *from* that
  owner at graph entry, so the checkpoint holds a derived cache, not a second truth;
  and **delete** the dead public channel at `graph/state_schema.py:178` (or give it the
  same accessors as the namespaced one) so one logical state cannot be declared twice.
  Guard tests: (1) a mutation test asserting every status string written anywhere is a
  `ProviderStatus` member; (2) a single-writer test asserting
  `_orchestrator__provider_health_snapshot` equals the tracker's projection after a
  graph step; (3) a test that a `BLOCKED_QUOTA` transition makes
  `compute_actions()` return `continue_unrelated_work`; (4) a state-schema test
  asserting exactly one provider-health channel exists.
- **Prior art:** `documentation/audit-findings.md:102` — "Provider health is tracked in
  an ad-hoc dict instead of the typed `ProviderHealthTracker`." Still present at HEAD
  and **worse** than recorded: there are now *five* representations (including a
  declared-but-addressless graph channel at `graph/state_schema.py:178`), the namespaced
  graph channel is declared "dormant" in its own registry, and `"unconfigured"` is
  outside the enum.

### F-PROV-02 — Failure classification is a dead module; four ad-hoc code vocabularies re-implement it
- **Class:** O2 (duplicated invariant enforcement) + O5 (policy-by-branch)
- **Severity:** High (impact 3 × drift 5 = 15)
- **Concern:** mapping a provider error to a category, a recovery action, and a health transition.
- **De-facto owners:**
  - `src/film_pipeline/providers/failure_classifier.py:135-151` — the nominal owner, with
    six ordered rules (quota, credit, auth, timeout, moderation, network) —
    ```python
    class FailureClassifier:
        """Classify provider errors into health states and recovery actions.
    ```
    and `failure_classifier.py:161-166` — the health transition it was written to perform —
    ```python
    @classmethod
    def update_health(cls, health: ProviderHealth, error_message: str) -> None:
        """Classify an error and update the ProviderHealth accordingly."""
    ```
  - `src/film_pipeline/generation/executor.py:186-195` — the real submit-failure path, which
    invents its own codes and never classifies —
    ```python
    except Exception as exc:
        self._fail_row(
            project_id,
            row.generation_id,
            code="submit_failed",
            reason=str(exc)[:200],
        )
    ```
  - `src/film_pipeline/mcp/tools/generation/dispatch.py:82-86` — a *second* submit path with
    its own copy of the same decision — `"_submit_failure(mgr, project_id, row, \"submit_failed\", str(exc)[:200])"`
  - `src/film_pipeline/mcp/tools/reference_generation/retry_loop.py:195-202` — a third vocabulary —
    `code="generation_failed"` / `code="heuristic_check_failed"` (`:148`)
  - `src/film_pipeline/agents/runner.py:295-309` — a fourth, for model providers —
    `failure: dict[str, Any] = {"status": "model_failure", ...`, which no consumer in `src/` reads
  - `src/film_pipeline/testing/scenarios.py:66-103` — a fifth, overlapping error vocabulary
    (`"quota_exhausted"`, `"auth_failure"`, `"provider_outage"`, `"moderation_block"`,
    `"corrupt_asset"`) that the classifier's regexes were written to match
- **Drift proof (mutation scenario + existing divergence):** `FailureClassifier` has
  exactly zero callers outside its own module —
  `grep -rn "FailureClassifier" src/ --include=*.py` returns only
  `providers/failure_classifier.py` itself, while
  `grep -rn "is_token_limit_exceeded\|compress_prompt_for_retry" src/` finds its
  sibling functions alive in `agents/runner.py:17-20`. So the classifying half of the
  module is dead and the token-limit half is live: the module's public contract is
  half-consumed. Concretely, a real HTTP 429 from Seedance raises `RuntimeError`
  (`providers/adapters/seedance_openrouter.py:82-87`) carrying `"HTTP 429: ..."`; that
  string matches the classifier's quota rule
  (`failure_classifier.py:39` — `"429"`), yet the message is funnelled into
  `blocking_reason` by `executor.py:190-191` and never passed to
  `FailureClassifier.classify`. Mutating `_FAILURE_RULES` patterns therefore changes
  nothing observable, and no test fails —
  `grep -rn "FailureClassifier" tests/` reaches only `tests/unit/providers/test_failure_classifier.py`
  and `tests/e2e/test_scenario_04_quota_exhausted.py`, both of which call the class
  directly and never drive it through the executor or the MCP dispatch path.
- **Reproduce:**
  ```bash
  grep -rn "FailureClassifier" src/ --include=*.py        # only its own module
  grep -rn "is_token_limit_exceeded\|compress_prompt_for_retry" src/ --include=*.py
  grep -rn 'code="' src/film_pipeline/generation src/film_pipeline/mcp/tools --include=*.py
  ```
- **Blast radius:** `generation/executor.py`, `mcp/tools/generation/dispatch.py`,
  `mcp/tools/reference_generation/retry_loop.py`, `agents/runner.py`, the ledger
  (`error_code` becomes an unversioned free-text field). User-visible: quota exhaustion
  and auth failure are recorded as `submit_failed`, no health transition occurs, no
  resume requirement is surfaced, and `resume_generation_polling`
  (`mcp/tools/generation/dispatch.py:182-196`) maps an unknown provider status back to
  `RUNNING` — a permanently stuck row instead of an actionable block.
- **Candidate owner module:** `provider-failure` — owns the error-code vocabulary, the
  classify(error) → (status, is_transient, resume_requirements) map, and the
  "classification must be applied on every provider failure" invariant.
- **Extraction sketch:** make `ProviderJob`/`ProviderJob.metadata["error"]` and the
  ledger's `error_code` a single enum owned by this module; have
  `executor._fail_row` and `_submit_failure` take a classified failure rather than a
  code string; delete the duplicated `"submit_failed"`/`"poll_failed"` literals in
  favour of members. Guard test: drive a mocked 429 through
  `GenerationExecutor.start()` and assert the health record moved to
  `BLOCKED_QUOTA` with a non-empty `resume_requirements`; today no such test exists.
- **Prior art:** `documentation/audit-findings.md:101` notes "Provider `poll()` methods
  for paid providers are stubbed to complete immediately" (still true at
  `seedance_openrouter.py:125-130`); the dead-classifier problem is new.

### F-PROV-03 — Two same-named provider registries exist, neither is the production one, and the real one has different admission rules
- **Class:** O4 (parallel registries) + O8 (missing contract)
- **Severity:** High (impact 3 × drift 5 = 15)
- **Concern:** the set of registered providers and what makes registration legal.
- **De-facto owners:**
  - `src/film_pipeline/providers/registry.py:11-19` — a runtime registry, test-only,
    with a duplicate-admission rule —
    ```python
    class ProviderRegistry:
        """Runtime registry of provider adapters, keyed by provider_id."""
    ```
    ```python
    if pid in self.adapters:
        raise ValueError(f"Provider '{pid}' already registered.")
    ```
  - `src/film_pipeline/schemas/registries/provider_registry.py:45-48` — a *second* class
    with the same name and a different shape — `"class ProviderRegistry(SchemaBase):"` /
    `"    providers: list[ProviderRegistryEntry] = Field(default_factory=list)"`
  - `src/film_pipeline/app/runtime.py:371-372` — the one production actually uses, with
    **no** admission rule — `"def register_provider(self, provider_id: str, adapter: Any) -> None:"` / `"        self.provider_adapters[provider_id] = adapter"`
  - `src/film_pipeline/providers/factory.py:34-44` — a third dispatch table that *raises* on
    unknown ids — `'raise ValueError(f"Unsupported provider_id: {provider_id}")'`
  - `src/film_pipeline/config/profile_resolver.py:185-196` — a second registration path that
    clears and repopulates the production registry —
    `"    rt.clear_providers()"` … `'        rt.set_provider_health(provider_id, "healthy")'`
- **Drift proof (existing divergence, executed via source):** registering the same
  provider twice raises `ValueError` through `providers/registry.py:18-19` and an unknown
  id raises through `providers/factory.py:44` —
  `'raise ValueError(f"Unsupported provider_id: {provider_id}")'` — but the same
  operations **silently overwrite** through `StudioRuntime.register_provider`
  (`app/runtime.py:372`). A third divergence is
  registered-and-listed-but-not-resolvable: in real mode `seed_default_provider_health`
  writes a health row for `"zai"` (`app/_provider_seeds.py:26`) while
  `seed_default_provider_adapters` (`:49-54`) registers only three adapters — executed
  output at HEAD:
  ```
  adapters: ['gemini-imagen-4', 'seedance-openrouter', 'veo-fast']
  health  : ['gemini-imagen-4', 'seedance-openrouter', 'veo-fast', 'zai']
  health rows with no adapter: ['zai']
  get_provider('zai') -> None
  ```
  yet `mcp/tools/providers.py:41` deliberately unions both sources —
  `"provider_ids = list(dict.fromkeys([*rt.list_providers(), *rt.get_all_health()]))"` —
  so `list_providers` advertises a provider that `get_provider` can never return.
  Mutating `ProviderRegistry.register` or the Pydantic `ProviderRegistry` changes nothing
  in production; `grep -rn "ProviderRegistry" src/ --include=*.py` shows the dataclass is
  only re-exported by `providers/__init__.py:14` and the Pydantic model is never
  imported by any non-schema module.
  The **reader side** under-states the blast radius too: the "registry" is consumed as a
  bare `Mapping[str, Any]`, not through any typed contract —
  `generation/executor.py:58` — `"    def __init__(self, store: ArtifactStore, providers: Mapping[str, Any]) -> None:"` —
  and the runtime dict is passed straight in at `app/services/_generation_ops.py:150`,
  `mcp/tools/generation/_text_only.py:110`,
  `mcp/tools/generation/dispatch.py:142`, and
  `mcp/tools/generation/planning.py:41,89`. So a registry change has to be kept in sync
  with six untyped consumer sites that cannot be checked by `mypy` strict, which is the
  O8 half of this finding rather than a side note.
- **Reproduce:**
  ```bash
  grep -rn "ProviderRegistry" src/ --include=*.py
  grep -rn "register_provider\|clear_providers" src/ --include=*.py
  grep -rn "GenerationExecutor(" src/ --include=*.py            # 5 construction sites, all passing the raw dict / Mapping[str, Any]
  grep -n "providers: Mapping\[str, Any\]" src/film_pipeline/generation/executor.py
  PYTHONPATH=src .venv/bin/python -c "import tempfile,pathlib;from film_pipeline.app.runtime import StudioRuntime;\
  rt=StudioRuntime(server_mode='real',runtime_root=pathlib.Path(tempfile.mkdtemp()));rt.seed_default_provider_health();\
  print(sorted(rt.provider_adapters), sorted(rt.provider_health), rt.get_provider('zai'))"
  ```
- **Blast radius:** `app/runtime.py`, `app/_provider_seeds.py`,
  `config/profile_resolver.py`, `providers/factory.py`, `providers/registry.py`,
  `schemas/registries/provider_registry.py`, `mcp/tools/providers.py`,
  `mcp/tools/reference_generation/index_files.py`. User-visible: a profile that declares
  a provider id unknown to `factory.build_provider_adapter` aborts registration with a
  `ValueError` from deep inside config resolution, while the same id registered through
  the runtime API is accepted and then fails at dispatch with
  `"Provider 'X' is not registered."`; and `list_providers` output cannot be used as an
  input to `get_provider`.
- **Candidate owner module:** `provider-registry` — owns the catalog, construction,
  registration admission rules, and enumeration.
- **Extraction sketch:** delete `providers/registry.py` and the Pydantic
  `ProviderRegistry` aggregate (or reduce it to the serialized form of the runtime
  registry); give the registry one `register()` with an explicit duplicate policy and an
  explicit unknown-id error; derive `list_providers` from the registry alone so a health
  row can never introduce an id. Guard tests: (1) `set(rt.provider_adapters) ==
  set(rt.provider_health)` after seeding; (2) duplicate registration raises; (3)
  `list_providers` ⊆ `{p for p in ... if rt.get_provider(p) is not None or health-only}`.
- **Prior art:** `documentation/audit-findings.md:29` — "registries exist but are not
  wired into runtime services." Still present and now measurable as a three-way split.

### F-PROV-04 — Credential access policy is re-derived at 14 call sites (+1 non-credential base-URL read); resolution is CWD-relative and re-keyed through unrelated provider ids
- **Class:** O5 (policy-by-branch) + O7 (leaked internals)
- **Severity:** High (impact 3 × drift 5 = 15)
- **Concern:** when a provider credential is read, from where, and under which provider id.
- **De-facto owners:**
  - `src/film_pipeline/providers/credentials.py:28-37` — the nominal owner, and its
    CWD-relative source —
    ```python
    def lookup(provider_id: str) -> str | None:
    ```
    with `credentials.py:49` — `"    dotenv_value = _read_dotenv(Path.cwd()).get(env_var)"`
  - `src/film_pipeline/providers/adapters/seedance_openrouter.py:51` — caches at construction —
    `"        self._configured_api_key = lookup(entry.provider_id)"`
  - `src/film_pipeline/providers/adapters/imagen4_gemini.py:42` — same caching policy —
    `"        self._configured_api_key = lookup(entry.provider_id)"`
  - `src/film_pipeline/providers/adapters/veo_fast.py:25` — **no** caching, and a hardcoded id
    that ignores its own entry — `'        key = lookup("veo-fast")'`
  - `src/film_pipeline/agents/model_adapter.py:92-107` — the model provider borrows *media*
    provider ids for three different credentials —
    ```python
    key = self._configured_api_key or lookup("seedance-openrouter")
    ...
    key = self._configured_gemini_api_key or lookup("gemini-imagen-4")
    ...
    key = self._configured_zai_api_key or lookup("zai")
    ```
  - `src/film_pipeline/generation/gemini_client.py:26` — a fourth independent read of the
    Google key for *review* calls, again via the image provider id —
    `'    key = api_key or lookup("gemini-imagen-4")'`
  - `src/film_pipeline/config/profile_resolver.py:204-216` — reaches the private mapping
    directly for a readiness report —
    `"from film_pipeline.providers.credentials import _env_var_for, is_configured"`
  - `src/film_pipeline/app/_provider_seeds.py:27,77` and `src/film_pipeline/app/bootstrap.py:76` —
    the app layer resolves the same credentials again to decide seeded health and mode
    readiness —
    `"            if credentials.is_configured(provider_id):"` (`_provider_seeds.py:27`),
    `'    if not credentials.is_configured("seedance-openrouter"):'` (`bootstrap.py:76`)
- **Drift proof (existing divergence, executed):** two adapters in the same process
  resolve the same class of credential with opposite freshness semantics. Running the
  reproduction below at HEAD prints
  ```
  seedance sees: sk-first-key-12345678
  veo sees:      AIza-second-key-12345678
  ```
  i.e. `SeedanceOpenRouterProvider` keeps the key captured at construction
  (`seedance_openrouter.py:51`) while `VeoFastProvider` re-reads per call
  (`veo_fast.py:25`) — a credential rotation is honoured by one adapter and silently
  ignored by the other. Second existing divergence, also executed: the same real-mode
  runtime resolves providers as `healthy` from the repository root and `unconfigured`
  from `/tmp`, because `credentials.env_or_dotenv` reads `Path.cwd()/.env`
  (`credentials.py:49`) rather than the runtime root. Neither divergence is pinned.
  **Correction to revision 1:** this file previously claimed that no test "asserts
  a policy at the adapter or `ModelAdapter` layer" — that sentence was overstated and is
  withdrawn. The *raise-and-present* path **is** pinned — but only for three of the five
  modules that read credentials directly: `tests/unit/providers/test_veo_fast_provider.py:33-40`
  requires `GOOGLE_API_KEY` and `:43-51` returns a present key,
  `tests/unit/providers/test_imagen4_provider.py:53-59` requires it through `submit`, and
  `tests/unit/agents/test_model_adapter.py:149-156` requires `OPENROUTER_API_KEY`. The
  other two direct readers assert nothing about the credential path:
  `providers/adapters/seedance_openrouter.py` does have tests, but they deliberately
  bypass credentials — `tests/integration/providers/test_seedance_adapter.py:139-142`
  builds the provider inside
  `with mock.patch.dict("os.environ", {"OPENROUTER_API_KEY": "sk-test-key"}):`, so its
  construction-time cache is never observed — and `generation/gemini_client.py` has no
  test reference at all (`grep -rn "gemini_client" tests/` → 0 hits). What is genuinely unpinned beyond that
  is exactly the two divergences above plus the id mapping:
  (a) no test rotates a credential after construction, so the cache-versus-per-call
  split is invisible (`grep -rni "rotat" tests/` → 0 hits);
  (b) no test asserts which provider id `ModelAdapter` passes to `lookup` — the only
  test that touches it patches it away, `monkeypatch.setattr(ma, "lookup", lambda _provider_id: None)`
  (`test_model_adapter.py:154`), so the borrowed media ids are never observed;
  (c) no test constrains the working directory the read resolves against.
  The credential *module's* own behaviour is well covered in
  `tests/unit/providers/test_credentials.py`; the other `tests/` hits for these symbol
  names are unrelated `lookup` methods
  (`tests/unit/providers/test_registry_health.py:28`, `tests/unit/test_mcp.py:49`) or
  E2E skip-guards (`tests/e2e/test_real_provider_smoke.py:28`).
  Reproduction (executed):
  ```bash
  PYTHONPATH=src .venv/bin/python - <<'PY'
  import os
  from film_pipeline.providers.adapters.seedance_openrouter import SeedanceOpenRouterProvider
  from film_pipeline.providers.adapters.veo_fast import VeoFastProvider
  from film_pipeline.schemas.registries.provider_registry import ProviderRegistryEntry
  os.environ["OPENROUTER_API_KEY"] = "sk-first-key-12345678"
  os.environ["GOOGLE_API_KEY"] = "AIza-first-key-12345678"
  s = SeedanceOpenRouterProvider(ProviderRegistryEntry(provider_id="seedance-openrouter", provider_type="video"))
  v = VeoFastProvider(ProviderRegistryEntry(provider_id="veo-fast", provider_type="video"))
  os.environ["OPENROUTER_API_KEY"] = "sk-second-key-12345678"
  os.environ["GOOGLE_API_KEY"] = "AIza-second-key-12345678"
  print("seedance sees:", s._api_key()); print("veo sees:     ", v._api_key())
  PY
  grep -rn "lookup(\|is_configured(\|env_or_dotenv(" src/ --include=*.py | grep -v "providers/credentials.py\|providers/registry.py" | wc -l   # 14 credential call sites
  grep -rnF -e 'lookup(' -e 'is_configured(' -e 'env_or_dotenv(' -e '_env_var_for(' src/ --include=*.py | grep -v "src/film_pipeline/providers/credentials.py" | grep -v "def lookup" | wc -l   # 15 (the private read included)
  grep -rn 'env_or_dotenv("ZAI_BASE_URL")' src/ --include=*.py   # the 1 non-credential site: agents/model_adapter.py:122
  ```
- **Blast radius:** `providers/adapters/{seedance_openrouter,imagen4_gemini,veo_fast}.py`,
  `agents/model_adapter.py`, `generation/gemini_client.py`, `app/_provider_seeds.py`,
  `app/bootstrap.py`, `config/profile_resolver.py`. User-visible: launching the MCP
  server or CLI from any directory other than the repository root flips every real
  provider to `unconfigured` (F-PROV-01) and makes
  `_missing_real_mode_credentials_issues` (`app/bootstrap.py:76`) report a missing
  OpenRouter key that is in fact present; a rotated key is only partially picked up;
  and the z.ai credential is reachable only through a health row that has no adapter
  (F-PROV-03).
- **Reproduce:** commands above, plus `grep -rn "_env_var_for" src/ tests/ --include=*.py`.
- **Candidate owner module:** `provider-credentials` — owns the id→env-var map, the
  environment/`.env` precedence rule, the read-at-call-time policy, and redaction.
- **Extraction sketch:** keep `credentials.py` as the owner but (a) anchor `.env` at the
  runtime root rather than `Path.cwd()`, (b) introduce explicit credential *slots*
  (`OPENROUTER`, `GOOGLE`, `ZAI`) so `ModelAdapter` stops borrowing media provider ids,
  (c) delete per-adapter `_configured_api_key` snapshots in favour of one call-time
  accessor, and (d) replace `config/profile_resolver.py`'s private `_env_var_for` import
  with a public `credentials.env_var_for(provider_id)`. Guard tests: (1) rotate a key
  after construction and assert every adapter sees the new value; (2) assert
  `credentials.env_var_for` is the only public mapping and that no adapter module
  contains a literal env-var name; (3) an import-law test forbidding
  `from film_pipeline.providers.credentials import _env_var_for`.
- **Prior art:** `docs/modular-architecture/audit/14-module-boundaries-and-import-law.md:96`
  records the `config → providers` private-symbol import; the resolution-policy and
  CWD divergences are new.

### F-PROV-05 — The provider catalog is re-declared across six Python modules at eight sites (plus profile YAML); `ProviderCapabilities` is written and never read
- **Class:** O1 (duplicated normative model) + O5 (policy-by-branch)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** which provider ids exist, which models each serves, what it can do, and which credential/env var belongs to it.
- **De-facto owners:**
  - `src/film_pipeline/providers/factory.py:47-56` — a model table —
    ```python
    def _default_models(provider_id: str) -> list[str]:
        return {
            "seedance-openrouter": ["bytedance/seedance-2.0"],
    ```
  - `src/film_pipeline/providers/factory.py:59-103` — a capability table, the only writer of
    `ProviderCapabilities` — `"        capabilities=_default_capabilities(provider_id, provider_type),"` (`:30`)
  - `src/film_pipeline/app/_provider_seeds.py:26` — a third id list (health seed) —
    `'        for provider_id in ("zai", "seedance-openrouter", "veo-fast", "gemini-imagen-4"):'`
  - `src/film_pipeline/app/_provider_seeds.py:73-79` — a fourth, the default selection policy,
    hardcoding the same model ids again —
    ```python
    for provider_id, model in (
        ("seedance-openrouter", "bytedance/seedance-2.0"),
        ("veo-fast", "veo-3.1-fast"),
    ):
    ```
  - `src/film_pipeline/providers/credentials.py:67-75` — the credential map — `'        "seedance-openrouter": "OPENROUTER_API_KEY",'`
  - `src/film_pipeline/providers/pricing.py:36-55` — the alias/label catalog —
    `'    "veo-fast": {"unit": "second", "rate_usd": 0.10, "label": "Veo Fast (rate TBD)"},'`
  - `src/film_pipeline/agents/model_routing/__init__.py:18-69` — `_FALLBACK_PROFILES`
    duplicates `profiles/base.studio.yaml:43-85` verbatim while the module docstring
    calls the YAML the source of truth (`:15-17` — `"The project-facing source of truth is profiles/base.studio.yaml."`)
  - `src/film_pipeline/mcp/tools/reference_generation/index_files.py:62-68` — the eighth
    declaration site, a selection policy that ignores configuration entirely —
    ```python
    def _select_image_provider(rt: Any) -> Any | None:
        for provider_id in rt.list_providers():
            adapter = rt.get_provider(provider_id)
    ```
    (`:66` filters on `getattr(entry, "provider_type", "") == "image"` and returns the
    first match.)
- **Drift proof (mutation scenario):** change `factory._default_models` at
  `factory.py:49` to a new Seedance model id. `_provider_seeds.default_video_provider`
  (`:74`) keeps `"bytedance/seedance-2.0"`, `profiles/local-real-provider.yaml:20` and
  `profiles/provider.seedance_primary.yaml` keep theirs, and no test fails:
  the only test that touches the pair derives its expectation *from the same function*
  (`tests/unit/mcp/tools/test_planning.py:225-227` —
  `"provider_id, model_id = rt.default_video_provider()"` then `expected = round(5 * rate_for(provider_id, model_id), 2)`),
  which is self-referential. Likewise, `_FALLBACK_PROFILES` is pinned by
  `tests/unit/agents/model_routing/test_routing.py:22-34` against a hand-written dict,
  not against `profiles/base.studio.yaml`, so mutating the YAML `model_profiles`
  (`base.studio.yaml:43-85`) drifts silently — while
  `agents/registry.py:15-17` derives `known_model_profiles` from the *Python* copy
  (`"return {*ModelRouter().list_profiles(), \"orchestrator\"}"`), so a profile added
  only to YAML fails agent registration and a profile added only to Python silently
  ignores its YAML parameters. Existing divergence for capabilities: `entry.capabilities`
  is written at `factory.py:30` and read **nowhere** —
  `grep -rn "\.capabilities" src/film_pipeline/providers src/film_pipeline/generation src/film_pipeline/mcp`
  returns nothing, so `ProviderCapabilities.max_duration_seconds`,
  `.aspect_ratios`, and `.supported_resolutions` cannot refuse any submission.
- **Reproduce:**
  ```bash
  grep -rn "bytedance/seedance-2.0\|imagen-4.0-fast-generate-001\|veo-3.1-fast" src/ profiles/ --include=*
  grep -rn "\.capabilities" src/film_pipeline/providers src/film_pipeline/generation src/film_pipeline/mcp --include=*.py
  grep -rn "default_video_provider\|_select_image_provider" src/ --include=*.py
  ```
- **Blast radius:** `providers/factory.py`, `app/_provider_seeds.py`,
  `providers/credentials.py`, `providers/pricing.py`, `config/profile_resolver.py`,
  `agents/model_routing/__init__.py`, `agents/registry.py`,
  `mcp/tools/reference_generation/index_files.py`, `generation/executor.py`. User-visible:
  the model an operator sees in `preview_generation_prompts`
  (`app/services/_generation_ops.py:113-140`) and the model actually submitted can
  differ; a 15-second Seedance request against a provider whose declared
  `max_duration_seconds` is smaller is submitted anyway; the planner prompt's price list
  (`pricing.pricing_prompt_block`) and the adapter's `estimate_cost` are the only pair
  that *is* pinned (see "Clean concerns").
- **Candidate owner module:** `provider-catalog` — one declarative table (id, type,
  models, capabilities, credential slot, price entry, aliases) from which the factory,
  the seeds, the credential map, and the planning prompt are all derived.
- **Extraction sketch:** fold `factory._default_models` / `_default_capabilities` /
  `_default_cost_profile`, `credentials._env_var_for`, and the `_provider_seeds` id and
  model literals into one module-level data structure keyed by provider id; make
  `default_video_provider` and `_select_image_provider` read it (and read `resolved_config`)
  rather than carrying private copies; make `pricing.PROVIDER_PRICING` the rate facet of
  the same table. Guard tests: (1) every id in `credentials._env_var_for`,
  `pricing.PROVIDER_PRICING`, `factory` dispatch, and both `_provider_seeds` lists is
  equal to one canonical set; (2) every `profiles/base.studio.yaml` `model_profiles` key
  equals `ModelRouter().list_profiles()`; (3) `max_duration_seconds` is enforced before
  `adapter.submit`.
- **Prior art:** `documentation/audit-findings.md:103` — "No provider capability
  enforcement before submission." Still present at HEAD; the catalog-duplication evidence
  is new.

### F-PROV-06 — The provider job-status to generation-status mapping exists twice, once through the enum and once through a raw string literal
- **Class:** O6 (parallel lifecycle)
- **Severity:** High (impact 3 × drift 4 = 12)
- **Concern:** how a `ProviderJobStatus` becomes a `GenerationStatus` and when a row leaves RUNNING.
- **De-facto owners:**
  - `src/film_pipeline/mcp/tools/generation/dispatch.py:182-196` — the enum-based mapper —
    ```python
    def _generation_status(provider_status: str) -> GenerationStatus:
    ```
    ```python
    try:
        job_status = ProviderJobStatus(provider_status)
    except ValueError:
        return GenerationStatus.RUNNING
    ```
  - `src/film_pipeline/generation/executor.py:245-263` — the operator-service path, which
    branches on string values and hand-rolls its own mapping —
    ```python
    if job.status == "completed":
        self._complete_row(project_id, row, adapter, job, result)
    elif job.status == "failed":
    ```
  - `src/film_pipeline/generation/executor.py:230-237` and
    `src/film_pipeline/mcp/tools/generation/dispatch.py:225-232` — two identical
    reconstructions of the `ProviderJob` from a ledger row (same six arguments), and
    `src/film_pipeline/mcp/tools/generation/dispatch.py:286-292` a third
  - `src/film_pipeline/providers/base.py:15-23` — the vocabulary both must agree on —
    ```python
    class ProviderJobStatus(StrEnum):
        """Lifecycle status of a provider job as reported by its adapter."""
    ```
- **Drift proof (mutation scenario):** change the value of `ProviderJobStatus.COMPLETED`
  from `"completed"` to `"done"` at `providers/base.py:20`. `dispatch._generation_status`
  still resolves through `ProviderJobStatus("done")` and returns
  `GenerationStatus.COMPLETED`, so the MCP path keeps working; `executor.py:245` compares
  `job.status == "completed"` against a now-stale literal and falls into the `else`
  branch, incrementing `poll_count` forever and never delivering the asset. No test
  fails: `executor.py`'s branch is exercised by
  `tests/unit/generation/test_executor.py` only with mock providers that emit the current
  enum value, and `grep -rn '"completed"' src/film_pipeline/generation` shows the literal
  has no single-owner anchor. The two paths are also reachable for the same project —
  `app/services/_generation_ops.py:101-110` (operator service) and
  `mcp/tools/generation/dispatch.py:199-251` (MCP tool) both poll the same ledger.
- **Reproduce:**
  ```bash
  grep -n 'job.status ==\|_generation_status' src/film_pipeline/generation/executor.py src/film_pipeline/mcp/tools/generation/dispatch.py
  grep -rn 'ProviderJob(' src/ --include=*.py
  ```
- **Blast radius:** `generation/executor.py`, `mcp/tools/generation/dispatch.py`,
  `generation/ledger.py` (stuck RUNNING rows), `app/services/_generation_ops.py`.
  User-visible: completed clips never delivered on one surface, and a duplicated
  `ProviderJob` reconstruction that must be kept in sync with
  `GenerationLedgerRow`'s field names in three places.
- **Candidate owner module:** `provider-job-lifecycle` — owns the job status vocabulary,
  the status→ledger-status map, and the ledger-row↔`ProviderJob` projection.
- **Extraction sketch:** keep one `provider_job_from_row(row)` and one
  `to_generation_status(job_status)` in the provider-runtime owner; have both
  `executor._poll_row` and `dispatch.resume_generation_polling` call them; make
  `executor` compare against `ProviderJobStatus.COMPLETED` rather than `"completed"`.
  Guard test: a parametrized test asserting both paths produce the same
  `GenerationStatus` for every `ProviderJobStatus` member, plus a completeness test that
  the map covers all enum members (it currently silently defaults to RUNNING).
- **Prior art:** `documentation/audit-findings.md:29,99` records that the graph and the
  ledger diverge and that `start_generation_batch` passes `prompt_ref` as prompt text
  (`mcp/tools/generation/dispatch.py:76-80`, still present); the duplicated status
  mapping is new. **Overlaps cluster 06** ("generation job lifecycle"); synthesis should
  count this once.
- **Note (verified, not a finding):** `mcp/tools/generation/dispatch.py:76-80` still
  submits `prompt=row.prompt_ref` (a reference string) rather than resolved prompt text,
  while `executor._dispatch_row` resolves it
  (`generation/executor.py:177`). That is the same prior-art item and belongs to
  cluster 06's ledger/prompt concern; recorded here only because it is the second half of
  this parallel lifecycle.

### F-PROV-07 — Cost has two uncoordinated authorities: the catalog the ledger bills and an unpinned estimate the spend ceiling trusts
- **Class:** O1 (duplicated normative model)
- **Severity:** High (impact 3 × drift 3 = 9)
- **Concern:** the authoritative per-provider rate, who computes per-shot cost, and whether the spend ceiling and the ledger agree.
- **De-facto owners:** the *catalog* authority, which the ledger bills from —
  - `src/film_pipeline/providers/pricing.py:36-55` — the declared single source of truth —
    `'    "seedance-openrouter": {"unit": "second", "rate_usd": 0.18, "label": "Seedance 2.0"},'` (`:39`)
  - `src/film_pipeline/generation/executor.py:113-119` — the only production caller that turns
    the catalog into per-shot money —
    `"            sid: estimate_cost_for_duration("`
  - `src/film_pipeline/generation/ledger.py:99` — the only per-row cost writer —
    `"                estimated_cost_usd=max(0.0, float((estimated_costs or {}).get(sid, 0.0))),"`
  - `src/film_pipeline/providers/factory.py:106-111` — a further rate copy in the registry entry —
    `"        return CostProfile(unit=unit_for(provider_id), estimated_rate_usd=rate_for(provider_id))"`

  and the *estimate* authority, which the spend gate trusts —
  - `src/film_pipeline/app/mock_responses.py:14` — a duplicated rate literal in the demo fixture —
    `"_SEEDANCE_RATE_USD_PER_SECOND = 0.18"`
  - `src/film_pipeline/app/mock_responses.py:90` — where the duplicate is spent —
    `'"estimated_cost_usd": round(seconds * _SEEDANCE_RATE_USD_PER_SECOND, 2),'`
  - `src/film_pipeline/app/mock_responses.py:363` — and a hardcoded total to match —
    `'"estimated_cost_usd": 18.72,'`
  - `src/film_pipeline/agents/impl/gen_planner_agent.py:11-20` — the entry point that *coerces*
    the authored payload instead of computing from the catalog —
    `'        estimated_cost_usd=float(estimate_data.get("estimated_cost_usd", 0.0)),'` (`:17`)
  - `src/film_pipeline/graph/nodes/visual.py:493-500` — persists that payload as
    `cost_estimate_ref` — `'def _save_cost_estimate(new_state: dict[str, Any], result: dict[str, Any]) -> None:'`
  - `src/film_pipeline/graph/nodes/_generation_batch_planning.py:38-47` — derives the spend
    ceiling from it, never from the catalog —
    `"                max_cost_usd = float(raw_cost) * 1.1"` (`:45`)
- **Drift proof (mutation scenario + executed divergence):** change
  `pricing.PROVIDER_PRICING["seedance-openrouter"]["rate_usd"]` at `pricing.py:39` from
  `0.18` to `0.25`. Every real adapter's `estimate_cost` and the ledger's
  `estimated_costs` (`executor.py:113-119`) follow, but the mock `provider-planning-agent`
  response still advertises `"$0.18/s"` and `18.72` (`mock_responses.py:363`), which
  `graph/nodes/_generation_batch_planning.py:38-47` turns into the spend ceiling. No test
  fails: `grep -rn "_SEEDANCE_RATE" tests/` returns nothing; the pricing guard suite
  (`tests/unit/providers/test_pricing.py:118-151`) parametrizes `_ADAPTERS` over the
  three *real* adapters only (`:93-115`) and never reads `mock_responses`.
  **Correction to revision 1:** that text said the ledger "bills the new one"; the
  executed reproduction below shows the mock-mode ledger does not bill *either*
  number. The mock fixtures carry provider `"seedance"`, model `"2.0"`
  (`mock_responses.py:86-87`), which are not `PROVIDER_PRICING` keys, so
  `estimate_cost_for_duration` falls through to `_UNKNOWN_PROVIDER_RATE = 0.0`
  (`pricing.py:57,79-81`). Executed:
  ```
  mock fixture provider/model (seedance, 2.0) x 6.5s -> 0.0
  real catalog (seedance-openrouter, bytedance/seedance-2.0) x 6.5s -> 1.17
  ceiling from mock estimate 18.72 -> 20.592
  ```
  So in mock mode the advertised estimate is not merely stale — it is disconnected from
  the ledger, and the ceiling gates a ledger that records zero. In real mode the seam is
  subtler and equally unpinned: the estimate the ceiling uses is *authored*, not
  computed — `gen_planner_agent.py:17` coerces an LLM-produced
  `estimated_cost_usd` whose price context is a prompt block,
  `context_vars["provider_pricing"] = pricing_prompt_block()`
  (`graph/nodes/_agent_prompt_context.py:53`), and nothing asserts the authored total
  matches the catalog total the ledger will bill.
- **Reproduce:**
  ```bash
  grep -rn "0.18\|_SEEDANCE_RATE\|18.72" src/ --include=*.py
  grep -rn "_SEEDANCE_RATE" tests/ --include=*.py   # empty: unpinned
  PYTHONPATH=src .venv/bin/python -c "from film_pipeline.providers.pricing import estimate_cost_for_duration as e; print('mock:', e('seedance','2.0',6.5), 'real:', e('seedance-openrouter','bytedance/seedance-2.0',6.5))"
  ```
- **Blast radius:** `app/mock_responses.py`, `agents/impl/gen_planner_agent.py`,
  `graph/nodes/visual.py`, `graph/nodes/_generation_batch_planning.py`,
  `generation/executor.py`, `generation/ledger.py`, `providers/pricing.py`,
  `providers/factory.py`. User-visible: the advertised cost and the ceiling derived from
  it can disagree with what the ledger bills; in mock mode the ledger bills `0.0` for
  every row, so the demo spend gate constrains nothing; `estimated_cost_usd` is the only
  cost ever recorded (no actuals).
- **Candidate owner module:** `provider-pricing` (already exists as `providers/pricing.py`;
  keep it) plus a `cost-accounting` contract that owns *who writes a cost*.
- **Extraction sketch:** make `mock_responses` derive `_SEEDANCE_RATE_USD_PER_SECOND`
  and the `18.72` total from `pricing.rate_for`/`estimate_cost_for_duration` (the
  fixture already has the provider/model in hand at `:86-87`); make the persisted
  `CostEstimate` carry the catalog-derived total so the ceiling and the ledger read the
  same number; make `CostProfile.estimated_rate_usd` either used or removed. Guard tests:
  (1) `mock_responses` group costs equal
  `estimate_cost_for_duration(provider, model, seconds)`, which also fails if the
  fixture's provider/model are not catalog keys (as today, where they resolve to `0.0`);
  (2) every provider/model pair reachable from a `GenerationRequest` resolves to a
  non-zero `rate_for`; (3) the spend ceiling equals `1.1 ×` the catalog total for the
  same shot set.
- **Prior art:** `documentation/audit-findings.md` has no cost item;
  `providers/pricing.py:1-8` records that the *real-adapter* divergence was already fixed
  and its guard test is `tests/unit/providers/test_pricing.py`. The fixture duplicate, the
  mock-mode `0.0` billing, and the authored-ceiling/catalog-ledger seam are new. The dead
  quota/credit fields that revision 1 folded into this finding have been moved to
  "Unverified hypotheses" — an unwritten field is unfinished work (§1.3), not
  distributed ownership.

### F-PROV-08 — Provider endpoints have no owner: the Gemini base URL is declared three times in three layers and nothing pins any of them
- **Class:** O1 (duplicated normative model) + O7 (leaked internals)
- **Severity:** High (impact 3 × drift 5 = 15)
- **Concern:** the base URL each provider client talks to, and whether one declaration governs them.
- **De-facto owners:**
  - `src/film_pipeline/providers/adapters/imagen4_gemini.py:21` — the adapter layer —
    `'GEMINI_API = "https://generativelanguage.googleapis.com/v1beta/models"'`
  - `src/film_pipeline/generation/gemini_client.py:13` — the generation layer, a second copy —
    `'GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"'`
  - `src/film_pipeline/agents/model_adapter.py:296` — the agent layer, a third copy inlined
    as a literal rather than a constant —
    `'            "https://generativelanguage.googleapis.com/v1beta/models/"'`
  - `src/film_pipeline/providers/adapters/seedance_openrouter.py:27` — the opposite
    arrangement: declared once, `'OPENROUTER_API = "https://openrouter.ai/api/v1"'`, but
    reached across a sub-package boundary by the agent layer —
    `'from film_pipeline.providers.adapters.seedance_openrouter import OPENROUTER_API'`
    (`agents/model_adapter.py:36`), used at `:141`.
- **Drift proof (existing duplication + missing pinning):** three declarations of the same
  Google endpoint exist in three different sub-packages, and they are not
  interchangeable in form — `imagen4_gemini.py:21` and `gemini_client.py:13` define a
  constant while `model_adapter.py:296` inlines the string with a trailing slash, so a
  change to one is invisible to the other two. `grep -rn "generativelanguage\|GEMINI_API"
  tests/ --include=*.py` returns nothing and
  `grep -rn "OPENROUTER_API\b" tests/ --include=*.py` returns nothing, so no test fails
  when an endpoint is changed, duplicated a fourth time, or pointed at a host that no
  other copy uses. The asymmetry is the drift mechanism: the single-declaration case
  (`OPENROUTER_API`) is exported through the adapter module and imported by
  `agents/model_adapter.py:36`, which binds the agent layer to a provider adapter's
  module path — the leak is the cost currently paid to avoid a fourth literal — while the
  three-way-duplicated case has no import at all.
- **Reproduce:**
  ```bash
  grep -rn "generativelanguage\|GEMINI_API" src/ --include=*.py
  grep -rn "OPENROUTER_API\b" src/ --include=*.py
  grep -rn "generativelanguage\|GEMINI_API\|OPENROUTER_API\b" tests/ --include=*.py   # empty: unpinned
  ```
- **Blast radius:** `providers/adapters/imagen4_gemini.py`, `generation/gemini_client.py`,
  `agents/model_adapter.py`. User-visible: a per-environment endpoint override (proxy,
  regional host, or test double) applied to one copy leaves the other two calling
  production, so reference-image generation, review calls, and model-provider chat can
  silently target different hosts; the operator has no single place to change.
- **Candidate owner module:** fold into the `provider-catalog` owner (F-PROV-05) as an
  `endpoint` facet per provider id, or into a small `provider-endpoints` module that the
  adapter, generation, and agent layers all import from — the latter only if the catalog
  is not built first.
- **Extraction sketch:** declare one mapping keyed by provider id —
  `{"gemini-imagen-4": "https://generativelanguage.googleapis.com/v1beta/models",
  "seedance-openrouter": "https://openrouter.ai/api/v1", ...}` — and have
  `Imagen4GeminiProvider._request` (`imagen4_gemini.py:54`), `call_gemini`
  (`gemini_client.py:16`), and `ModelAdapter._gemini_url` (`model_adapter.py:291`)
  read it instead of their own copies; resolve the override through `env_or_dotenv` at
  read time rather than baking a literal into an f-string. Guard tests: (1) no module
  outside the owner contains the substring `generativelanguage` or `openrouter.ai`;
  (2) an import-law test forbidding `agents` from importing any `providers.adapters.*`
  module symbol. Note the second test currently fails for the `OPENROUTER_API` import,
  which is the point of the finding.
- **Prior art:** `documentation/audit-findings.md` has no endpoint item;
  `docs/modular-architecture/audit/14-module-boundaries-and-import-law.md:96` records the
  adjacent `config → providers` private-symbol import but not this
  `agents → providers.adapters` public-constant import. New.

### F-PROV-09 — The provider wait budget is declared in four keys, only one is read, and neither poll path enforces a deadline
- **Class:** O5 (policy-by-branch) + O8 (missing contract)
- **Severity:** High (impact 3 × drift 5 = 15)
- **Concern:** the provider-job wait budget — how long a submitted job may stay `RUNNING`
  before it is failed — and whether any declared value governs it.
- **De-facto owners:**
  - `src/film_pipeline/providers/adapters/seedance_openrouter.py:28-33` — the only
    declaration of a wait-budget policy; three of its four keys are never read by any
    module —
    `"POLLING_CONFIG = {"` … `"max_wait_seconds": 1800,`
  - `src/film_pipeline/providers/adapters/seedance_openrouter.py:122` — the **only**
    behavioral read, and it reads exactly one of the four keys —
    `'time.sleep(self.polling_config["initial_delay_seconds"])'`
  - `src/film_pipeline/providers/adapters/seedance_openrouter.py:128` — the adapter's own
    `poll` ignores both the interval and the cap, completing on the first call —
    `"job.status = ProviderJobStatus.COMPLETED"`
  - `src/film_pipeline/generation/executor.py:239` — the operator poll site, which
    re-derives the budget as "none" — `"job = adapter.poll(job)"`
  - `src/film_pipeline/generation/executor.py:260` — the non-terminal branch just advances
    the counter; no elapsed time is compared to anything —
    `"poll_count=row.poll_count + 1,"`
  - `src/film_pipeline/mcp/tools/generation/dispatch.py:170` — the MCP poll site, the same
    re-derivation — `"result = adapter.poll(job)"`
  - `src/film_pipeline/mcp/tools/generation/dispatch.py:243` — the MCP counter write, also
    unbounded — `"poll_count=polls,"`
  - `src/film_pipeline/providers/base.py:71` — the contract both sites obey; `poll` takes no
    budget and `ProviderJob` carries no deadline field —
    `"def poll(self, job: ProviderJob) -> ProviderJob:"`
- **Drift proof (existing divergence + mutation scenario):** the declared policy and the
  only implementation already disagree — `POLLING_CONFIG["poll_interval_seconds"]` is `30`
  (`:30`) and `POLLING_CONFIG["max_wait_seconds"]` is `1800` (`:31`), yet
  `SeedanceOpenRouterProvider.poll` returns `COMPLETED` on the first call with no sleep
  (`:128`), and both call sites invoke `adapter.poll(job)` with no delay and no cap
  (`executor.py:239`, `dispatch.py:170`). **Mutation:** change `"max_wait_seconds": 1800` to
  `"max_wait_seconds": 60` at `seedance_openrouter.py:31`. No code path reads the key — an
  AST walk of the module reports read keys `['initial_delay_seconds']` and dead keys
  `['backoff_multiplier', 'max_wait_seconds', 'poll_interval_seconds']` — so no behavior
  changes and no test fails:
  `grep -rn "polling_config\|max_wait_seconds\|poll_interval_seconds\|backoff_multiplier\|initial_delay_seconds" tests/ --include=*.py`
  is empty, and the suite over the three directories that exercise the poll paths passes
  unchanged —
  `UV_CACHE_DIR="$PWD/.uv-cache" uv run python -m pytest tests/unit/providers tests/unit/generation tests/unit/mcp -o addopts="" -q`
  → **501 passed, 1 warning**. This drift is silent
  in the §1.6.3 sense *because the declared policy is never consulted*: a change to the only
  declared wait budget is undetectable by any code path or by any test. That is also why
  drift is rated 5 rather than F-PROV-06's 4 — there the divergent branch was at least
  exercised by tests; here the three keys have no readers at all, so nothing can fail. The
  finding is *not* scored on a claim that a loop silently hangs: today all three real
  adapters return `COMPLETED` immediately, so the unbounded behavior is latent (impact 3),
  and the consequence that is reachable now is an inert, unverifiable timeout configuration.
- **Reproduce:**
  ```bash
  cd ${REPO_ROOT}
  grep -rn "polling_config\|max_wait_seconds\|poll_interval_seconds\|backoff_multiplier\|initial_delay_seconds" src/ tests/ --include=*.py
  # 7 hits, all in seedance_openrouter.py: the 4 declaration keys (:29-32), the ctor
  # parameter (:45), the dict copy (:49), and the single key read (:122). 0 hits in tests/.
  grep -rin "max_wait\|poll_interval\|backoff" profiles/ ; echo "profiles: $?"   # -> "profiles: 1" (0 hits)
  UV_CACHE_DIR="$PWD/.uv-cache" uv run python -c "import ast,pathlib; t=ast.parse(pathlib.Path('src/film_pipeline/providers/adapters/seedance_openrouter.py').read_text()); d=next({k.value for k in n.value.keys} for n in ast.walk(t) if isinstance(n,ast.Assign) and any(getattr(x,'id',None)=='POLLING_CONFIG' for x in n.targets)); r={n.slice.value for n in ast.walk(t) if isinstance(n,ast.Subscript) and isinstance(n.value,ast.Attribute) and n.value.attr=='polling_config'}; print('declared',sorted(d)); print('read',sorted(r)); print('dead',sorted(d-r))"
  # declared ['backoff_multiplier', 'initial_delay_seconds', 'max_wait_seconds', 'poll_interval_seconds']
  # read     ['initial_delay_seconds']
  # dead     ['backoff_multiplier', 'max_wait_seconds', 'poll_interval_seconds']
  ```
- **Blast radius:** `providers/adapters/seedance_openrouter.py` (the declaration),
  `providers/base.py` (the budgetless `poll` contract and `ProviderJob`), the two poll
  surfaces `generation/executor.py` and `mcp/tools/generation/dispatch.py`,
  `generation/ledger.py` (a row can stay `RUNNING` with a rising `poll_count`),
  `app/services/_generation_ops.py` (drives `poll_once`) and `app/runtime.py` (provider
  wiring). User-visible: a provider wait budget is inert — lowering or raising
  `max_wait_seconds`, or supplying `polling_config` to the adapter, changes nothing and
  cannot be observed; and any adapter that does not complete on the first poll leaves the
  generation row `RUNNING` indefinitely on both the operator and MCP surfaces, with
  `poll_count` climbing and nothing to fail the row.
- **Candidate owner module:** fold into the `provider-job-lifecycle` owner nominated by
  F-PROV-06 — it already owns the job vocabulary, the status→ledger-status map, and the
  row↔`ProviderJob` projection, so the wait budget belongs beside it — or a small
  `provider-poll-policy` module if the budget is to become profile-configurable.
- **Extraction sketch:** replace the loose `dict[str, float]` (`:28-33`) with one typed
  frozen budget (`initial_delay_seconds`, `poll_interval_seconds`, `max_wait_seconds`,
  `backoff_multiplier`) resolved from the provider catalog/profile rather than a module
  literal, and give the loop that owns the deadline the budget instead of the adapter
  holding it privately. One shared helper — e.g. `poll_until_terminal(job, adapter, budget,
  now)` — computes `elapsed` from the row's existing `submitted_at`, fails the row with
  `error_code="poll_timeout"` once `elapsed > budget.max_wait_seconds`, and sleeps
  `budget.poll_interval_seconds` (scaled by `backoff_multiplier`) between polls; call it
  from `executor._poll_row:239` and `dispatch.resume_generation_polling:170`. Guard tests:
  (1) a row whose `submitted_at + max_wait_seconds` is already in the past is failed
  `poll_timeout` on **both** paths; (2) every field of the typed budget changes an
  observable outcome — a mutation guard that would have caught the three dead keys; (3) an
  architecture test asserting the key literals `"max_wait_seconds"`,
  `"poll_interval_seconds"` and `"backoff_multiplier"` appear only in the owner.
- **Prior art:** `documentation/audit-findings.md:101` — "Provider `poll()` methods for paid
  providers are stubbed to complete immediately" — explains why the inert budget has not yet
  bitten; `documentation/reviews/arch-lens-flexibility.md:109` records the same stub
  ("imagen `poll()` is synchronous-fake (`:123-126` instant COMPLETED)"); and
  `documentation/reviews/arch-lens-observability.md:100-105` traces a provider *timeout* but
  only through `submit_failed`/`poll_failed` message flattening, never the wait budget.
  `documentation/reviews/arch-lens-boundaries.md:135` describes the two poll paths as such.
  **Within this audit:** the §Grep table at `:96` lists the four `poll(` sites as prose, and
  F-PROV-06 mentions `executor.py:245` "incrementing `poll_count` forever" — but attributes
  it to the status-literal mismatch, not to a missing budget; `audit/06`'s F-GEN-04 owns the
  *meaning* of `poll_count`, not any deadline. What is new here is the concrete four-key
  declared budget, its three dead keys, and the total absence of a deadline in either path:
  no prior document names `POLLING_CONFIG`, `max_wait_seconds`, `poll_interval_seconds`, or
  `backoff_multiplier` (grep over `documentation/audit-findings.md`,
  `documentation/reviews/*.md`, `docs/clean-code-refactor/*.md` and every other
  `docs/modular-architecture/audit/*.md` — this file excluded — → 0 hits), so this is
  **new**.
- **Provenance:** uncovered by the adversarial coverage pass
  (`reviews/adversarial-coverage.md` §H2); added post-verification. One H2 claim is corrected
  rather than adopted: its reproducer annotation ("4 hits in seedance_openrouter.py — 3
  declaration + 1 `initial_delay` read") does not reproduce — the quoted pattern returns 6
  hits, none of which is the `initial_delay` read (line 122 matches only via the
  `polling_config` substring). The corrected accounting is in **Reproduce** above; every H2
  `path:line` anchor itself resolves at `fb85baa`. H2's phrase "the MCP poll loop" is also
  narrowed: `resume_generation_polling` (`dispatch.py:199-251`) contains no `while`/`for`
  loop and no `sleep` — it polls exactly once per invocation — so the unboundedness is the
  absence of any budget/deadline state across repeated callers, not an in-code infinite loop.

---

## Ownership map

| Concern | De-facto owners | Single / distributed |
|---|---|---|
| Provider id catalog (which ids exist) | `providers/factory.py:34-44` dispatch, `app/_provider_seeds.py:26`, `:50-59`, `profiles/*.yaml` | **Distributed (≥3)** |
| Provider → model catalog | `providers/factory.py:47-56`, `app/_provider_seeds.py:73-79`, `profiles/local-real-provider.yaml:20-23`, adapter fallbacks (`seedance_openrouter.py:98`, `veo_fast.py:47`, `imagen4_gemini.py:22`) | **Distributed (≥4)** |
| Provider → capability model | `providers/factory.py:59-103` (writer), `schemas/registries/provider_registry.py:7-17` (types) | Single writer, **zero readers** (unenforced) |
| Provider runtime handle seen by `generation` | `generation/executor.py:58` (`Mapping[str, Any]`), constructed at `app/services/_generation_ops.py:150`, `mcp/tools/generation/_text_only.py:110`, `mcp/tools/generation/dispatch.py:141-142`, `mcp/tools/generation/planning.py:41,89` | **Single signature, 5 construction sites**; the untyped mapping (not `BaseProviderAdapter`) is the leaked boundary (F-PROV-03) |
| Provider → credential env var | `providers/credentials.py:67-75` | **Single (normative)** — but 14 credential-resolution call sites (plus 1 non-credential base-URL read) across 8 modules re-derive the read policy (F-PROV-04) |
| Provider → price | `providers/pricing.py:36-55` | **Single for real adapters**; duplicated in `app/mock_responses.py:14` (F-PROV-07) |
| Adapter construction | `providers/factory.py:18-44` | **Single** (partially guarded: `tests/unit/providers/test_pricing.py:145-151` asserts the constructed entry's rate; the unknown-id `ValueError` at `:44` has no test — see F-PROV-03) |
| Adapter registration / lookup | `app/runtime.py:371-380` (production dict), `providers/registry.py:11-32` (test-only), `schemas/registries/provider_registry.py:45-48` (unused), `config/profile_resolver.py:185-196` (second path) | **Distributed (4, none canonical)** |
| Provider → endpoint / base URL | `providers/adapters/imagen4_gemini.py:21`, `generation/gemini_client.py:13`, `agents/model_adapter.py:296` (three Gemini copies); `providers/adapters/seedance_openrouter.py:27` (one OpenRouter copy, imported cross-layer by `agents/model_adapter.py:36`) | **Distributed (3) with no test pinning any of them** (F-PROV-08) |
| Provider selection policy | `app/_provider_seeds.py:68-80` (video, credential-driven), `mcp/tools/reference_generation/index_files.py:62-68` (image, first-registered), `mcp/tools/planning.py:119-144` (profile overlay) | **Distributed (3)** |
| Provider health — normative status model | `schemas/_base.py:156-165` `ProviderStatus` (7 members) | Single, but `"unconfigured"` (`app/_provider_seeds.py:32`) and `"unknown"` (`mcp/tools/providers.py:23,48`) are outside it |
| Provider health — live state | `app/runtime.py:51,386-393` (production dict) | **Distributed** vs the three typed models (F-PROV-01) |
| Provider health — typed record | `providers/health.py:11-44`, `schemas/provider_health.py:13-31` | Two models, **both test-only** |
| Provider health — checkpointed representation | `graph/orchestrator_state.py:406-410,427-443`, `graph/state_schema.py:178,195` | Single reader/one writer function with **no production caller** (declared "dormant writer", `:132`) |
| Provider health — writers | `app/_provider_seeds.py:28,30,37`, `config/profile_resolver.py:196`, `mcp/tools/providers.py:32` | **Distributed (3 modules)**; all write the same dict |
| Provider health — readers | `app/health.py:47`, `mcp/tools/providers.py:21,44`, `mcp/tools/state.py:56`, `app/services/_browse_ops.py:152`, `app/services/operator.py:252`, `graph/_action_routing.py:228,334` | Distributed over 6 modules |
| Provider failure classification | `providers/failure_classifier.py:32-166` (**zero production callers**) vs code literals in `generation/executor.py:169,190,225,241,287`, `mcp/tools/generation/dispatch.py:72,85`, `mcp/tools/reference_generation/retry_loop.py:148,199`, `agents/runner.py:301`, `testing/scenarios.py:66-103` | **Distributed (≥5 vocabularies)** |
| Provider job lifecycle status | `providers/base.py:15-36` | **Single model**; the →`GenerationStatus` projection is duplicated (F-PROV-06) |
| Cost estimate per shot | `providers/pricing.py:92-101`, `generation/executor.py:113-119`, `graph/nodes/_generation_batch_planning.py:146-153` | Single formula, two call sites — **clean** |
| Cost estimate authoring (the ceiling input) | `agents/impl/gen_planner_agent.py:11-20,73`, `app/mock_responses.py:14,90,363`, persisted at `graph/nodes/visual.py:493-500` | **Split from the catalog** (F-PROV-07): the value the ceiling uses is coerced/authored, never computed |
| Cost recording | `generation/ledger.py:99` | **Single writer** for `estimated_cost_usd`; no actual-cost writer |
| Quota / credit accounting | **none** | Absent — a feature never built (§1.3), so recorded as an unverified hypothesis, not a finding |
| Budget ceiling / spend gate | `graph/nodes/_generation_batch_planning.py:30-55`, `generation/ledger.py:264-282` | Owned by clusters 06/12; provider-cost input enters through F-PROV-07 |
| Provider health routing decision | `graph/_action_routing.py:226-235,333-341` | **Single decision site** — sound, but fed by an always-empty snapshot |
| Model profile → model id | `profiles/base.studio.yaml:43-85` + `agents/model_routing/__init__.py:18-69` (`_FALLBACK_PROFILES`) | **Distributed (2 identical copies)** |
| Model provider credential | `agents/model_adapter.py:92-107`, `generation/gemini_client.py:26` | Distributed, and keyed through *media* provider ids |
| Model-call retry ladder | `agents/runner.py:222-344` (3 attempts), `mcp/tools/reference_generation/retry_loop.py:206-226` (3 attempts), `providers/failure_classifier.py:214-242` (prompt compression) | Distributed (3 policies); see F-PROV-02 |

---

## Clean concerns

These are recorded as single-owner at HEAD, with the guard test that pins them (bar A5).

1. **Per-second / per-image price catalog for real adapters.** `providers/pricing.py:36-55`
   is the only rate table; `seedance_openrouter.py:164-168`, `imagen4_gemini.py:162-168`,
   and `veo_fast.py:67-71` each delegate to `rate_for`/`estimate_cost_for_duration`.
   Pinned by `tests/unit/providers/test_pricing.py:118-151`
   (`TestAdapterPricingParity.test_estimate_matches_table`, parametrized over all three
   real adapters) and `:145-151`
   (`test_factory_uses_standard_catalog_rate_for_default_entry`), plus
   `:154-185` for the planner prompt block. **Gap:** the two mock adapters return the
   literal `0.0` (`mock_provider.py:182-185`, `mock_image_provider.py:92-95`) and are not
   in the parity parametrization, so they are exempt from the guard even though the
   catalog declares them (`pricing.py:37-38`). The values agree today; the guard does not
   cover them. **Second gap (F-PROV-07):** the guard bounds only the three *real adapters*
   to `PROVIDER_PRICING`. Nothing bounds the *demo fixture* to it, and the fixture's
   provider/model (`mock_responses.py:86-87` — `"seedance"` / `"2.0"`) are not catalog
   keys at all, so the parity guard cannot be extended to cover it as written; the
   catalog must gain the ids first. The value the spend ceiling actually trusts is
   authored by an agent (`gen_planner_agent.py:17`) and is unchecked against the catalog
   in either mode.
2. **Credential resolution primitive.** `credentials.lookup` / `env_or_dotenv` /
   `is_configured` / `redact` (`providers/credentials.py:28-62`) is a single
   implementation with a single env-var map, and redaction is applied at every adapter
   error boundary (`seedance_openrouter.py:86`, `imagen4_gemini.py:74`,
   `agents/_http_transport` callers). Pinned by `tests/unit/providers/test_credentials.py`
   (env-wins-over-dotenv, redaction, no logging of keys). What is *not* owned is when and
   under which id adapters read it — F-PROV-04.
3. **`BaseProviderAdapter` contract + `ProviderJob` + `ProviderJobStatus`.** One abstract
   base, one job record, one status enum in `providers/base.py:15-93`; all five concrete
   adapters implement it and no other definition of the enum exists
   (`grep -rn "class ProviderJobStatus" src/` → one hit). Verified by the adapter test
   suites (`tests/unit/providers/test_mock_provider.py`,
   `test_imagen4_provider.py`, `test_veo_fast_provider.py`,
   `tests/integration/providers/test_seedance_adapter.py`). **Gap:** there is no test
   asserting that every `ProviderJobStatus` member is handled by the
   `_generation_status` map (F-PROV-06).
4. **Token-limit detection and prompt compression.** `failure_classifier.is_token_limit_exceeded`
   (`:204-211`) and `compress_prompt_for_retry` (`:214-242`) have exactly one production
   consumer, `agents/runner.py:17-20,239-240,280-282`, and are pinned by
   `tests/unit/agents/test_runner.py` and `tests/unit/providers/test_failure_classifier.py`.
   Single-owner — but co-located with the dead `FailureClassifier`, which is why the
   module reads as owned when only half of it is (F-PROV-02).
5. **Provider-health routing decision.** `graph/_action_routing.py:226-235`
   (`_blocked_providers_result`) is the only place that turns provider health into a
   routing outcome, and `:333-341` the only place that blocks `advance_to_generation`.
   Pinned by `tests/unit/graph/test_router_blockers.py:52`,
   `tests/unit/test_graph.py:87,101`, and `tests/integration/test_dynamic_routing.py:52,61`.
   Clean as a *decision*; its input is unreachable in production (F-PROV-01).
6. **Model profile selection.** `agents/model_routing/ModelRouter.select/resolve_or_raise/
   resolve_model_params` (`:86-161`) is the only resolver and is pinned by
   `tests/unit/agents/model_routing/test_routing.py` and
   `tests/unit/agents/test_runner.py` (8 tests). Clean — but its *data* is duplicated
   with the YAML (F-PROV-05).
7. **`graph/services.py` provider wiring.** Contains no provider registry, no health, and
   no credential access; it constructs `ModelAdapter()`/`ModelRouter()`
   (`:83-104`) and nothing else. Clean, and notably *not* the owner of anything in this
   cluster — which is itself the architectural gap.

---

## Candidate module boundary: a provider-runtime owner

The cluster's concerns split into one clearly-owed core plus three modules that exist but
own only half their contract. Proposed boundary (one responsibility per module, B1):

**`provider-catalog`** — *owns* the declarative provider table: provider id, alias ids,
provider type, model list, `ProviderCapabilities`, credential slot, credential env-var
name, price entry, and the default selection policy.
*Does not*: construct adapters, hold live state, or decide failures.
Consumers today: `providers/factory.py`, `app/_provider_seeds.py`,
`providers/credentials.py`, `providers/pricing.py`,
`mcp/tools/reference_generation/index_files.py`, `mcp/tools/planning.py`.

**`provider-registry`** — *owns* adapter construction, registration admission rules, and
enumeration. One `register()` with an explicit duplicate policy; `list_providers()`
derived from the registry alone; health rows cannot introduce ids.
*Does not*: read credentials policy, classify failures, or evaluate health.
Replaces: `providers/registry.py`, the Pydantic `ProviderRegistry` aggregate, the
`StudioRuntime.provider_adapters` dict, and the second registration path in
`config/profile_resolver.py`.

**`provider-credentials`** — *owns* the credential slot→env-var map, the
environment/`.env` precedence rule, the read-at-call-time policy, and redaction.
*Does not*: cache per adapter, key model credentials through media provider ids, or
resolve `.env` relative to the process working directory.
Public contract: `env_var_for(slot)`, `resolve(slot) -> str | None`,
`is_configured(slot) -> bool`, `redact(text) -> str`.

**`provider-health`** — *owns* the single typed health record, the
`ProviderStatus` vocabulary, the classify→transition rule, and the single persisted
representation (materialized into graph state and checkpointed as a derived cache).
*Does not*: hold a second copy in the runtime dict, or accept status strings outside the
enum. Public contract: `ProviderHealth`, `record(provider_id, status, reason, resume)`,
`get`, `project() -> dict`, `blocked()`.

**`provider-failure`** — *owns* the error-code enum, the pattern→category rules, the
transience flag, and `resume_requirements`. *Does not*: own prompt compression (that
stays with the model-call retry policy in `agents/`) or own ledger statuses.
Every provider failure — submit, poll, download, model call — must pass through it.

**`provider-job-lifecycle`** — *owns* `ProviderJob`/`ProviderJobStatus`, the
status→`GenerationStatus` map, and the ledger-row↔job projection.
*Does not*: own the ledger or the delivery step.

**Stays where it is:** `providers/pricing.py` (already single-owner; becomes the price
facet of `provider-catalog`), `generation/ledger.py` (owns the ledger row and its
`estimated_cost_usd` write), `generation/executor.py` (owns batch orchestration and
calls the lifecycle owner), `graph/_action_routing.py` (owns the routing decision and
*reads* health — it must not become a second health store).

**Dependency law for the extracted cluster:** `provider-health` and
`provider-failure` may import `provider-catalog`; `provider-registry`,
`provider-credentials`, and `provider-job-lifecycle` may not import `provider-health`;
`generation` and `graph` consume only `provider-registry`/`provider-health`/
`provider-job-lifecycle`. Mechanically checkable as an import test in the
`tests/unit/graph/test_startup_boundaries.py` style already present in the repo.

**Why these six and not fewer (B9):** each is justified by a named finding —
`provider-catalog` by F-PROV-05 (and it absorbs F-PROV-08's endpoint facet),
`provider-registry` by F-PROV-03, `provider-credentials` by F-PROV-04,
`provider-health` by F-PROV-01, `provider-failure` by F-PROV-02,
`provider-job-lifecycle` by F-PROV-06 — plus `pricing`', `ledger`'s and
`_action_routing`'s existing contracts. No module is proposed for future flexibility.
F-PROV-07 is deliberately *not* given a new module: `providers/pricing.py` already exists
and the missing half is a contract (who authors the ceiling) rather than a boundary.

**Extraction cost estimate:** `provider-health` M, `provider-failure` M,
`provider-credentials` S, `provider-registry` S, `provider-catalog` M,
`provider-job-lifecycle` S. Cost never lowers severity (bar §1.5); the ordering above is
by dependency, not by score.

---

## Unverified hypotheses (explicitly not findings)

These are recorded for completeness and must not be promoted without evidence:

1. **Actual-cost recording is absent by design, not by omission.** The ledger records
   only `estimated_cost_usd` (`generation/ledger.py:99`) and nothing writes an actual
   provider-billed amount. I did not find a spec that requires actuals, so I have not
   claimed a finding; a spec may exist in `documentation/product-completion/`, which was
   out of this cluster's scope.
2. **`ProviderJobStatus.CANCELLED` has no ledger counterpart.** `Schemas._base.GenerationStatus`
   (`:168-179`) has `CANCELLED` and `mcp/tools/generation/dispatch.py:182-196` does not map
   the provider's `CANCELLED`, so a provider-side cancellation resolves to RUNNING. I
   did not build a reproduction, so this stays a hypothesis pending one.
3. **`.env` is present in the working tree** (`${REPO_ROOT}/.env`,
   413 bytes) and is read by `credentials._read_dotenv(Path.cwd())`. I did not inspect
   its contents and make no claim about what it holds; whether it is git-ignored is a
   secrets-handling question outside this cluster's scope. It is recorded only because it
   is what makes the executed CWD reproduction produce `healthy` from the repo root.
4. **Quota and credit accounting do not exist.** Moved here in revision 2 from F-PROV-07,
   where revision 1 had classified it as O3 (split state authority). That classification
   was wrong: a field with no writer anywhere is *unfinished work*, and §1.3 excludes
   incomplete features from distributed ownership. The facts stand and are verified —
   `providers/health.py:19-20` declares `quota_remaining` / `credit_remaining_usd`,
   `schemas/provider_health.py:20-27` declares `quota_state` / `credit_state`,
   `grep -rn "quota" src/ --include=*.py` returns only those declarations, the
   `BLOCKED_QUOTA` enum member (`schemas/_base.py`), the classifier's regex strings, and
   `testing/scenarios.py` fixtures, and `grep -rn "rate_limit" src/ --include=*.py`
   returns **0 hits** — so nothing decrements a quota, sets a quota state, or reads a
   credit balance. The audit does **not** claim this is distributed ownership; it claims
   only that the health model advertises a surface no code maintains. A spec requiring
   quota accounting may exist in `documentation/product-completion/`, which was outside
   this cluster's scope.
5. **`resume_provider_block` clears a block it cannot re-derive.** `mcp/tools/providers.py:27-33`
   unconditionally resets a blocked provider (quoted in revision 1 as supporting the
   withdrawn O3 clause). With no quota/credit authoritative state anywhere, the operator
   action is unverifiable — but I did not build a reproduction showing a wrong outcome, so
   it stays a hypothesis rather than a finding.
