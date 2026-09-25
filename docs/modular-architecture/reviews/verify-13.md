# Verification — 13-test-doubles-and-harness.md

- **Verifier:** independent adversarial pass (did not author `audit/13-test-doubles-and-harness.md`).
- **Repo / HEAD:** `${REPO_ROOT}` @ `fb85baa0e6b769b709791a96a89980089304bf13` (branch `modular-app`, working tree clean).
- **Method:** every `path:line` anchor opened at HEAD; every count re-run with the stated command; each
  O-class checked against §1.4; each severity recomputed per §1.5; prior art checked against A7.
- **Constraint honoured:** no file under `src/`, `tests/`, or the audit file was modified. Only this file was written.

Anchor policy note: the audit's line ranges are read as inclusive and were checked for *containment* of the
quoted text, not exact-span equality. Genuine off-by-one/two cases are listed as disputes only where they
change what the anchor proves.

---

## F-TEST-01 — verdict: **DOWNGRADED** (High 15 → High 12)

**Confirmed anchors (all open at HEAD):**
- `src/film_pipeline/app/mock_responses.py:97` — `def default_mock_responses() -> dict[str, dict[str, Any]]:`
- `src/film_pipeline/agents/prompt_templates/defaults/spine.py:306` — `'  "development": {\n'`
- `src/film_pipeline/app/mock_responses.py:143` — `"treatment": {` (no `development` wrapper) ✅
- `src/film_pipeline/agents/prompt_templates/defaults/spine.py:159` — `'  "identity": {\n'` ✅
- `src/film_pipeline/app/mock_responses.py:101` — `"intake": {` ✅
- `src/film_pipeline/agents/runner.py:365-367` — `mock_response = self._find_mock_response(...)` / `if mock_response is not None:` / `return mock_response` ✅
- `src/film_pipeline/agents/impl/development_agent.py:76` — `data = model_output.get("development", model_output)` ✅
- `src/film_pipeline/agents/impl/intake_agent.py:35` — `data = model_output.get("intake", model_output)` ✅
- `src/film_pipeline/agents/mvp/__init__.py:120` — `output_artifacts=["shot_bible", "master_film_matrix"]` ✅
- `src/film_pipeline/artifacts/registry.py:157,192` — both `shot_matrix` and `master_film_matrix` registered with `renderer=rendering.render_shot_matrix` ✅

The **core existing divergence is real and confirmed**: the treatment template mandates a `development`
wrapper while the canned payload is flat; the intake template is flat while the canned payload adds an
`intake` wrapper; both agents' tolerant `.get(<wrapper>, model_output)` fallbacks hide it. This part survives
adversarial reading.

**Counter-evidence — drift proof is materially overstated:**
1. The audit states *"No test parses a canned payload through … the agent impl"* and *"The only guard over the
   canned set checks key presence and non-emptiness, not shape"*. **Both are false.** The canned payloads are
   routed through the **real** agent impls end-to-end:
   - `tests/unit/graph/test_scope_contract_node_integration.py:94-121` — `test_development_then_script_node_full_mock_flow`
     calls `nodes.intake_node(state)` then `nodes.development_node(state)` with
     `GraphServices.for_mock_runtime(mock_responses=default_mock_responses())` (`:37`) and asserts
     `assert blocking == []` and `assert dev_updates.get("approved") is True` (`:117-118`).
   - `tests/e2e/test_scenario_01_happy_path.py:75-93` drives `approve_phase` through `constitution` and
     `development` and asserts real artifacts/checkpoints appear.
   - `tests/e2e/test_scenario_11_full_flow_3min.py` drives intake → … → shot_bible with `studio_runtime`.
   So a canned payload that stops *parsing* does fail tests; only the **template-vs-canned wrapper agreement**
   is unguarded. That distinction is the actual drift proof and the audit did not make it.
2. The stated mutation is backwards. Deleting the fallback at `development_agent.py:76` (i.e. `data = model_output`)
   leaves **mock mode working** (the canned payload is flat, so top-level `treatment`/`scenes` are found); what
   breaks is a *real* model that emits the template's `development` wrapper. The claimed silent failure
   ("mock mode then builds an empty `Treatment`") does not follow from the cited line.
3. **Missed third divergence in the same concern:** `src/film_pipeline/agents/impl/screenwriter_agent.py:54` —
   `data = model_output.get("script_output", model_output)` — expects a `script_output` wrapper that appears
   in neither the template (`spine.py:408-444` declares flat `"story_bible"` + `"script"`) nor the canned
   payload (`mock_responses.py:176-268`). Reproduce: `grep -n 'script_output' src/film_pipeline -r`.
4. **A7 gap:** `documentation/reviews/arch-lens-flexibility.md:16` already records the mock-response fixture and
   that `test_mvp_invariants.py` "covers forward direction only"; F-TEST-01 lists prior art but does not cite it.

**Recomputed severity:** impact 3 (mock mode is the default server mode, but both wrappers are normalized so no
wrong output currently reaches a human) × drift 4 (the template↔canned agreement is unguarded, but the canned
payloads *are* exercised end-to-end) = **12, High** (was 15).

---

## F-TEST-02 — verdict: **DOWNGRADED** (High 10 → Medium 4)

**Confirmed anchors:**
- `src/film_pipeline/testing/mock_model.py:47-52` — validator default `{"score": 90, "status": "pass", "issues": [], "mock_model": True}` ✅
- `src/film_pipeline/app/mock_responses.py:371` — `"consensus": {` ✅
- `src/film_pipeline/agents/runner.py:160` — `return {"status": "ok", "agent": "mock", "output": {"_warning": "generic_fallback"}}` ✅
- `tests/e2e/conftest.py:124` (`mock_model: MockModelAdapter,`) vs `:132` (`runner = PromptRunner(mock_responses=default_mock_responses())`) — dead parameter ✅
- `pyproject.toml:136` — `"tests/**/*.py" = ["ARG001", "ARG002", "S101"]` ✅
- `grep -rn "PromptRunner()" --include='*.py' tests | wc -l` → **11** ✅

The **dead-wiring and third-source observations are true**, but they are hygiene/incompleteness (§1.3 excludes
them from ownership findings) rather than a proven duplicated normative model.

**Counter-evidence — the O1 drift proof is a false equivalence:**
- The audit labels `mock_responses.py:371` "the canned production **validator** payload" and compares it with
  `MockModelAdapter.validator_response()` as "same concept, incompatible shapes".
- `"clip-validator"` is an **agent** id (`src/film_pipeline/agents/mvp/__init__.py:143`,
  `agents/impl/registry.py:28` → `QCSynthesisAgent`) and is **not** in `MVP_VALIDATORS`
  (`src/film_pipeline/validation/validators/__init__.py:11-166` lists 15 ids: `logline-validator` …
  `assembly-validator`). Its `consensus` body is consumed by `qc_synthesis_agent.py:20`
  (`consensus = model_output.get("consensus", model_output)`) and is the QCSynthesisAgent's declared output,
  not a validator raw response. The two shapes are not two encodings of one concern.
- `MockModelAdapter` is directly pinned by its own tests (`tests/unit/test_testing_utils.py:72-98`,
  `tests/unit/testing/test_mock_actors.py:60-92`), so drift is not 5.

**Recomputed severity:** impact 2 × drift 2 (own unit tests pin the double; no runtime consumer) = **4, Medium** (was 10).

---

## F-TEST-03 — verdict: **CONFIRMED** (High 12)

**Confirmed anchors and claims:**
- `tests/conftest.py:62-63` is `@pytest.fixture(scope="session", autouse=True)` / `def _fast_checkpoint_backend()` and
  `:75-78` is exactly the quoted import/`previous`/`set_git_backend_type(InMemoryGitBackend)` block ✅
- `src/film_pipeline/testing/in_memory_git.py:120-121` — `selected = tree if only is None else {p: tree[p] for p in only if p in tree}` (silent filter) ✅
- `src/film_pipeline/checkpoints/git_backend.py:59` — `self._run("checkout", commit, "--", *files)`, and `_run`
  raises on non-zero (`:30-31`), so a pathspec absent from the commit raises for the real backend ✅
- `grep -rn "InMemoryGitBackend" --include='*.py' src tests` → only `testing/in_memory_git.py` and
  `tests/conftest.py:75,78` — **no parity test** ✅
- `grep -rn "class .*Fake\|class .*Stub" --include='*.py' tests | wc -l` → **23**, none for `GitBackend` ✅
- O-class O2 is correct (one contract, two enforcement implementations). Impact 3 × drift 4 = 12 is justified
  (suite-wide double, no test runs both backends through one assertion set).

**Minor counter-evidence (does not change verdict):** the audit says the real backend is contracted
"covering commit/tag/branch/rollback/`list_files`/`is_clean`". `grep -c "list_files\|restore_files"
tests/unit/checkpoints/test_checkpoints.py` → **0 and 0**; those methods are at most exercised indirectly via
`RollbackManager`. Reword to avoid asserting direct coverage.

---

## F-TEST-04 — verdict: **CONFIRMED** (High 10)

**Every count and anchor reproduced at HEAD:**
- `grep -rn "ArtifactStore(" --include='*.py' tests | wc -l` → **64**; `grep -rln … | wc -l` → **17** ✅
- `grep -rn "make_store\|sandbox_store_root" --include='*.py' src tests | wc -l` → **48** in **7** files ✅
- `src/film_pipeline/testing/storage.py:17` — `return init_storage_root(path, profile=PROFILE_SANDBOX)` ✅
- `src/film_pipeline/artifacts/store.py:60-61` — `def __init__(self, root: Path) -> None:` / `self._root = ensure_storage_root(root)` ✅
- `src/film_pipeline/artifacts/storage.py:116` — `def init_storage_root(root: Path, *, profile: str = PROFILE_PRODUCTION) -> Path:` ✅
- `tests/e2e/conftest.py:135` — `artifact_store=ArtifactStore(root=tmp_path / "artifacts"),` ✅
- `src/film_pipeline/graph/services.py:48-49` — `profile = PROFILE_SANDBOX if os.getenv("FILM_PIPELINE_NO_PERSIST") else PROFILE_PRODUCTION` / `return ArtifactStore(root=ensure_storage_root(root, profile=profile))` ✅
- `grep -rn "read_marker" --include='*.py' src` → only `artifacts/storage.py:97` (def) and `:138` (layout-version check);
  no consumer branches on `marker.profile`, so the sandbox/production distinction is write-only ✅

Impact 2 × drift 5 = 10 High is defensible: the marker is inert and the only profile assertion
(`tests/unit/artifacts/test_storage.py:167-169`) pins the helper to itself. **Dispute (cosmetic):** the cited
range `:163-167` does not contain the quoted `assert marker.profile == "sandbox"` (actual line **169**).
O-class could also be read as O5 (policy-by-branch at 64 call sites) rather than O1; either way the seam is real.

---

## F-TEST-05 — verdict: **CONFIRMED** (Medium 6)

- `find tests -name conftest.py` → `tests/conftest.py`, `tests/e2e/conftest.py`, `tests/smoke/conftest.py`,
  `tests/unit/mcp/tools/conftest.py` — **no `tests/integration/conftest.py`** ✅
- `grep -rn "StudioRuntime(" --include='*.py' tests | wc -l` → **95** in **30** files ✅
- `grep -rn 'tmp_path / "runtime"' --include='*.py' tests | wc -l` → **102** ✅
- `tests/e2e/conftest.py:155-156` — `rt = StudioRuntime(runtime_root=tmp_path / "e2e-runtime")` / `rt.services = graph_services` ✅
- `src/film_pipeline/app/runtime.py:433-443` — `def _build_services_for_mode(...)` composition root ✅
- `tests/integration/test_generation_mcp.py:31-36` — inline `PromptRunner()` / `GraphServices(` / `ArtifactStore(root=…)` ✅
- `tests/smoke/conftest.py:4-17` re-exports 13 e2e fixture names ✅
- The mitigation claim is accurate: `tests/unit/app/test_runtime.py:19` constructs `StudioRuntime(server_mode="mock")`,
  so composition-root changes are observed by one tier only → drift 3, Medium 6. O5 (policy re-derived per call site) is correct.

---

## F-TEST-06 — verdict: **CONFIRMED** (High 12)

- `tests/conftest.py:111-140` guard fixture; `:121-125` the three watched roots ✅
- `:29-31` per-test `monkeypatch.setenv(...RUNTIME_ROOT...)` / `...STORAGE_ROOT...` / `delenv(PERSIST_STATE)` ✅
- `:98-100` session-scoped raw `os.environ[...NO_PERSIST]`, `tmp_path_factory.mktemp`, `os.environ[...STORAGE_ROOT]` ✅
- `:136-138` `added`/`removed`/`resized` computed by size comparison ✅
- `:160-161` `if "logs" in parts or relative.endswith(".log"): continue` ✅; `:163` stores `path.stat().st_size` only ✅
- `grep -rn "_production_roots_untouched" --include='*.py' tests` → **only** `tests/conftest.py:112` (definition),
  so deleting the guard leaves the suite green ✅
- `src/film_pipeline/app/logging_setup.py:93` — `expected_log = (log_dir / "film_pipeline.log").resolve()` ✅
- `src/film_pipeline/app/services/operator.py:191` — `os.environ["FILM_PIPELINE_MCP_MODE"] = mode` ✅
- `src/film_pipeline/app/safety.py:75` — `if _is_under(resolved, persist_root()):` ✅

Impact 3 × drift 4 = 12 is justified. Classification O2 is defensible (two redirect implementations plus a
detection check); the "primary guard" phrasing slightly overstates its role (env redirection is the
write-prevention, the snapshot is detection), but the blind spots are real.

---

## F-TEST-07 — verdict: **CONFIRMED** (High 10) — with a reproduced undercount

- `grep -rn 'provider_id="mock-video-provider"' --include='*.py' src tests` → **8 hits** ✅
- `src/film_pipeline/providers/factory.py:96-103` generic fallthrough — `aspect_ratios=["16:9"]`,
  no `supports_audio`/`supports_seed` (schema defaults `False` at
  `src/film_pipeline/schemas/registries/provider_registry.py:19`) ✅
- `tests/unit/providers/test_mock_provider.py:32-37` — `aspect_ratios=["16:9", "9:16"]`,
  `supports_audio=True`, `supports_seed=True`, `failure_modes=[...]` ✅
- `tests/unit/generation/test_executor.py:48-49` — `aspect_ratios=["16:9"]`, `supports_audio=True`, `supports_seed=True` ✅
- `tests/e2e/conftest.py:73-79` — `aspect_ratios=["16:9"]`, audio/seed default `False` ✅
- `grep -rn "supports_audio" --include='*.py' src` → only `schemas/registries/provider_registry.py:19`; no behavior
  branches today, so impact 2 is fair ✅; nothing pins the factory entry (`build_provider_adapter` is called in
  tests only for pricing/plumbing), so drift 5 ✅

**Counter-evidence (evidence defect, not a severity change):** the audit's own reproduce line
"`grep … src` finds no consumer outside … and `providers/factory.py`" is wrong — `factory.py` contains **no**
`supports_audio` token. **The "four places" count is also low.** A fifth hand-built `ProviderRegistryEntry`
for the same id exists at `tests/unit/test_schemas.py:946-955` (`capabilities=ProviderCapabilities(text_to_video=True,
return_last_frame=True, max_duration_seconds=30)`), and a fifth capability literal lives at
`tests/unit/generation/test_executor_download_failed.py:36-50` (different id, same duplicated model).
Reproduce: `grep -rn "ProviderCapabilities(" --include='*.py' tests | wc -l`.

---

## F-TEST-08 — verdict: **CONFIRMED** (Medium 8)

- `src/film_pipeline/graph/services.py:62-63` — `prompt_runner: PromptRunner = field(...)` /
  `artifact_store: ArtifactStore = field(...)` (concrete types, no Protocol) ✅
- `tests/unit/graph/test_context_packets.py:12-15` — `class FakeArtifactStore:` / `def __init__(self, artifacts: dict[str, dict[str, Any]]) -> None:` + `load_ref` ✅
- `tests/unit/graph/test_qc_subgraph.py:43-45` — `class FakeArtifactStore:` / `def __init__(self) -> None:` + `list_artifacts` ✅
- `tests/unit/mcp/tools/test_reference_generation_helpers.py:143-145` — `class _FakeRuntime:` / `def list_providers(...)` / `return ["video-provider-1"]` ✅
- `grep -rn "class .*Fake" --include='*.py' tests | wc -l` → **23** ✅
- The two `FakeArtifactStore` classes do disagree (constructor arity and disjoint method sets) while standing in
  for the same `GraphServices.artifact_store` field — an existing divergence, not a hypothesis. Impact 2 × drift 4 = 8 Medium is fair.

---

## Missed in scope (test-double / harness ownership seams)

1. **`film_pipeline.mcp.tools.get_runtime` is rebound by at least three independent mechanisms, with no owner.**
   - `tests/conftest.py:51` — `tools_pkg.get_runtime = reset_runtime.__globals__["get_runtime"]` (autouse, every test)
   - `tests/unit/mcp/tools/conftest.py:29,34` — `tools_pkg.get_runtime = get_runtime` (autouse, before *and* after)
   - `tests/unit/mcp/tools/test_reference_generation.py:117` `mock.patch("film_pipeline.mcp.tools.get_runtime", …)`;
     `:188,210,219` `monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", …)`;
     `tests/integration/test_generation_mcp.py:43` `mock.patch(...)`
   Two conftests plus six test-local patches re-implement "how a test supplies the runtime"; removing either
   conftest leaves the other silently compensating. O2/O5, not covered by F-TEST-05 or F-TEST-06.
2. **`provider_health` has split state authority (O3) with a value-type divergence.**
   `StudioRuntime.set_provider_health` (`src/film_pipeline/app/runtime.py:386-387`) is the declared writer and emits
   `{"status": status, "reason": reason}`; tests bypass it —
   `tests/e2e/conftest.py:158-161` writes a plain dict, while `tests/e2e/test_scenario_04_quota_exhausted.py:35,53`
   writes a `ProviderHealthState` object into the same dict. No test pins the value type. The audit mentions this
   only as a candidate-boundary note, not as a finding.
3. **A third unbound agent-output wrapper** (same concern as F-TEST-01): `screenwriter_agent.py:54` reads
   `script_output`, which neither the template (`spine.py:408-444`) nor the canned payload writes.
4. **Latent backend split in e2e:** `tests/e2e/conftest.py:113-114` builds a **real** `GitBackend.init_temp`, while
   the session autouse fixture installs `InMemoryGitBackend`; the two coexist in the same tier (the fixture is
   currently unreferenced by e2e/smoke tests, which is why this is a latent seam rather than live drift).

---

## Disputes requiring the author to fix

1. **F-TEST-01 mutation is invalid/backwards.** The `.get("development", model_output)` fallback does not need to
   exist for the *wrapper-less* canned payload; deleting it breaks **real** mode, not mock mode. Rewrite the
   drift proof as "change the template wrapper at `spine.py:306` (or add `development` to the canned payload);
   no test compares `PromptTemplate.output_format` with the canned payload, so the disagreement passes."
2. **F-TEST-01 "No test parses a canned payload through … the agent impl" is false.** Cite
   `tests/unit/graph/test_scope_contract_node_integration.py:94-121` and
   `tests/e2e/test_scenario_01_happy_path.py:75-93` and narrow the claim to "no test pins template↔canned shape".
3. **F-TEST-02 validator-shape divergence is a false equivalence.** `clip-validator` is an agent id
   (not in `MVP_VALIDATORS`); comparing its `consensus` payload with `MockModelAdapter.validator_response()` does
   not prove duplicated ownership. Either delete the divergence or find a same-contract pair.
4. **F-TEST-07 "four places" undercounts** (add `tests/unit/test_schemas.py:946`), and the
   "`src` grep … and `providers/factory.py`" parenthetical is factually wrong (no `supports_audio` in the factory).
5. **F-TEST-03 coverage wording:** `list_files`/`restore_files` have zero direct references in
   `tests/unit/checkpoints/test_checkpoints.py`; say "exercised indirectly through `RollbackManager`".
6. **A7 citation gap:** `documentation/reviews/arch-lens-flexibility.md:16` already states the mock-response fixture
   and that the invariant test covers the forward direction only; F-TEST-01 must cite it.
7. **Minor anchor repairs:** `test_storage.py` sandbox assert is at `:169`, not within `:163-167`; the
   `grep -rn "mock_human"` claim ("only those definitions") is wrong — the command returns
   `tests/unit/test_testing_utils.py:7`, `tests/unit/testing/test_mock_actors.py:7`, and `actor_type` assertions
   (the *fixture* is indeed unrequested, but the reproduce output as written is false).

---

## Overall verdict

**CONFIRMED 5 / DOWNGRADED 2 / REJECTED 0** (F-TEST-03, -04, -05, -06, -08 confirmed; F-TEST-01 and
F-TEST-02 downgraded). The cluster's anchors and mechanically reproduced counts are essentially accurate, and
no finding is fabricated; the damage is concentrated in F-TEST-01's overstated drift proof (a reversed mutation
and a false "no test exercises the canned payloads" claim) and F-TEST-02's apples-to-oranges validator-shape
divergence, plus a missed `get_runtime`/`provider_health` harness seam that is more load-bearing than two of the
filed findings. No finding should ship on the author's wording alone until disputes 1–4 are corrected.
