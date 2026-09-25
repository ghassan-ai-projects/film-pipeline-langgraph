# verify-20 — A6 independent verification of ten post-verification findings

## 1. Method

Independent adversarial verification (bar A6, `00-methodology-and-quality-bar.md` §1.6,
§1.8) of the ten findings that were added to their audit files *after* those files had
already been verified, and therefore were never re-checked by any first-round verifier:

| audit file | finding ids |
|---|---|
| `audit/09-kb-context-and-provenance.md` | `F-KBCTX-11`, `F-KBCTX-12`, `F-KBCTX-13` |
| `audit/11-mcp-surface-safety-and-entrypoints.md` | `F-MCP-13`, `F-MCP-14`, `F-MCP-15` |
| `audit/12-post-delivery-constraints-budget.md` | `F-BUD-06` |
| `audit/13-test-doubles-and-harness.md` | `F-TEST-09`, `F-TEST-10`, `F-TEST-11` |

For each finding I (1) re-derived every `path:line` anchor from a pristine snapshot,
(2) ran the `Reproduce` block verbatim, (3) attacked the drift proof by making the
stated mutation in the snapshot copy and running the relevant tests, (4) re-scored
severity under §1.5, (5) checked double-counting against the already-verified
first-round findings, and (6) checked O-class and prior art.

No file other than this one was written. `docs/` is gitignored; the working tree was
left clean.

### 1.1 Revision pins

```
$ git rev-parse HEAD
fb85baa0e6b769b709791a96a89980089304bf13
```

Snapshot (all source reads and all mutations were done here — never in the repo):

```
$ mkdir -p /tmp/v20 && git archive fb85baa | tar -x -C /tmp/v20 && git rev-parse fb85baa
fb85baa0e6b769b709791a96a89980089304bf13
```

`/tmp/v20` was re-checked against a second fresh extraction after all mutations:

```
$ diff -rq /tmp/v20 /tmp/v20-check        # (only __pycache__/.pytest_cache differ)
```

Tests were run against the snapshot source, not the installed editable package:

```
$ cd /tmp/v20 && PYTHONPATH=/tmp/v20/src ${REPO_ROOT}/.venv/bin/python \
    -c "import film_pipeline; print(film_pipeline.__file__)"
/tmp/v20/src/film_pipeline/__init__.py
```

Every pytest invocation below uses `--no-cov` (and `-n0` where a single worker is
needed). This matters: `pyproject.toml` `addopts` contains `--cov-fail-under=90`
(`pyproject.toml:80`), so any subset run without `--no-cov` fails on coverage rather
than on the behaviour under test. **None of the ten `Reproduce` blocks is a pytest
command** (all ten are `sed`/`grep`/`git grep`), so no `Reproduce` block in this batch
is exposed to that trap; the `--no-cov` requirement applies only to the mutation runs
in this document.

### 1.2 Concurrent revision drift (recorded, §1.6.8)

Audit files 11 and 13 changed **while this verification was running**. Audit 11 grew
from 467 to 480 lines (F-MCP-13 heading 371 → 384) and audit 13 from 525 to 527 lines
(F-TEST-10 heading 354 → 356, F-TEST-11 376 → 378). The substantive change observed in
audit 13 was that the two count commands (`mock.patch(...)` → 3 and
`mcp_tools.get_runtime = ...` → 5) were moved *into* F-TEST-09's `Reproduce` block.
I re-ran the current four-command block against the pinned snapshot and record both
the old and current block where relevant (see §2.8). The hashes of the revisions this
document judges are:

```
$ sha256sum docs/modular-architecture/audit/{09,11,12,13}-*.md
5e8f4f5237558cd1cc08095a5dc2b1a70e4db1300bc6bcc31ba5eb68c1ca87fd  09-kb-context-and-provenance.md   (860 lines)
9b44193642ca1774a13440cb5bc78c6a5d8ace333c7ea7bc2785cc7261f5d114  11-mcp-surface-safety-and-entrypoints.md (480 lines)
1b4b03f63caefc3915524c2c3338fc0d74f462e047ebf42b65cbf815f3a83772  12-post-delivery-constraints-budget.md (1204 lines)
25364a334d7a39ae0924fbf5a4a7775386da0356ca2a85b633061ec65674b875  13-test-doubles-and-harness.md (527 lines)
```

### 1.3 Excluded scope

Not verified here: `F-KBCTX-14` (audit 09, marked PENDING VERIFICATION by its own
author), the withdrawn `F-TEST-02` block (audit 13 — confirmed to have two headings,
`:186` and `:401`, and no `- **Severity:**` bullet, as stated in the brief), and every
first-round finding `F-KBCTX-01…10`, `F-MCP-01…12`, `F-POST-*`/`F-BUD-01…05`,
`F-TEST-01…08`.

---

## 2. Finding-by-finding

### 2.1 `F-KBCTX-11` — One matrix payload has two registry identities — **DOWNGRADED (Critical 16 → High 12)**

**Anchors — all resolve** (snapshot `/tmp/v20`):

```
$ sed -n '119p;157p;192p' src/film_pipeline/artifacts/registry.py
    return f"film.studio/{artifact_id.replace('_', '-')}"
        "shot_matrix": _spec("shot_matrix", renderer=rendering.render_shot_matrix),
        "master_film_matrix": _spec("master_film_matrix", renderer=rendering.render_shot_matrix),
$ sed -n '447p' src/film_pipeline/graph/nodes/visual.py
    ref = _save_artifact(new_state, shot_matrix, "shot_matrix", "shot_bible")
$ sed -n '108p;230p' src/film_pipeline/mcp/tools/planning.py
        version = max(1, store.latest_version(project_id, "shot_bible", "master_film_matrix"))
        return _error("MasterFilmMatrix not found. Run generate_shot_bible first.")
$ sed -n '199p' src/film_pipeline/mcp/tools/bibles/shot.py
        store, project_id, "master_film_matrix", ArtifactType.MASTER_FILM_MATRIX, matrix
$ sed -n '88p' src/film_pipeline/validation/validators/__init__.py
        input_schema="master_film_matrix",
```

Supporting anchors also resolve: `planning.py:101-115` `_load_master_matrix` wraps the
read in `except FileNotFoundError: return None`; `store.py:543-545` raises
`FileNotFoundError` for an absent version; `registry.py:119` is the kind-slug helper.

**Reproduce — verbatim, output as stated:**

```
$ sed -n '157p;192p' src/film_pipeline/artifacts/registry.py
        "shot_matrix": _spec("shot_matrix", renderer=rendering.render_shot_matrix),
        "master_film_matrix": _spec("master_film_matrix", renderer=rendering.render_shot_matrix),
$ sed -n '447p' src/film_pipeline/graph/nodes/visual.py
    ref = _save_artifact(new_state, shot_matrix, "shot_matrix", "shot_bible")
$ sed -n '108p;230p' src/film_pipeline/mcp/tools/planning.py
        version = max(1, store.latest_version(project_id, "shot_bible", "master_film_matrix"))
        return _error("MasterFilmMatrix not found. Run generate_shot_bible first.")
$ grep -rn "master_film_matrix" --include=*.py src/film_pipeline/graph/   # no output
[exit=1]
```

**Drift proof — the existing divergence (a) holds; the mutation (b) is falsified.**

The existing divergence is real: the graph writes artifact id `shot_matrix`
(`visual.py:447`) while `planning.py:108` reads `master_film_matrix`, and
`store.load` raises `FileNotFoundError` for the absent version, so the planning tool
returns the hard error at `:230` for a matrix that exists under the other id.

The mutation claim is false. The finding says *"change `visual.py:447`'s artifact id
to `master_film_matrix`; … no test fails"*. I made exactly that mutation in the
snapshot:

```
$ sed -i '' 's/_save_artifact(new_state, shot_matrix, "shot_matrix", "shot_bible")/_save_artifact(new_state, shot_matrix, "master_film_matrix", "shot_bible")/' \
    src/film_pipeline/graph/nodes/visual.py
$ PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/unit/graph/test_shot_bible_structure.py \
    -n0 --no-cov -q -p no:cacheprovider
FAILED tests/unit/graph/test_shot_bible_structure.py::test_five_scene_film_shot_matrix_conforms_to_three_act_brief
E   FileNotFoundError: Artifact version not found: .../05-shot-bible/shot_matrix/versions/v001.json
```

The author's reasoning enumerated `shot_matrix_ref ==` assertions but missed
`tests/unit/graph/test_shot_bible_structure.py:180`, which loads the artifact by the
hard-coded id:

```
$ sed -n '180p' tests/unit/graph/test_shot_bible_structure.py
        **services.artifact_store.load("third-interval", FilmPhase("shot_bible"), "shot_matrix", 1)
```

So the graph's writer id **is** pinned by a test (threaded through the whole run in the
same file), and the "no test fails" assertion is wrong.

**Two further evidence defects.**

1. The `input_schema` characterization is materially incomplete. The finding says the
   grep returns *"the field's definition plus two unrelated MCP tool schemas at
   `mcp/contract.py:111` / `mcp/_stdio_transport.py:39`"*. The real command returns 26
   matches — the field definition (`schemas/registries/validator_registry.py:28`), the
   two MCP-tool-schema sites, and **22 validator registration sites that pass
   `input_schema=`** (`validation/validators/__init__.py:17…161`,
   `validation/impl/*.py:112,136,163,179,196,208,216`):

```
$ grep -rn "input_schema" --include=*.py src/ | wc -l
      26
```

   The *conclusion* ("no module consumes `ValidatorRegistryEntry.input_schema`") still
   holds — producers setting a kwarg are not consumers — but the printed
   characterization of the grep is wrong (§1.6.4 / §1.6.7).
2. The claim *"every other `artifact:shot_bible:shot_matrix:v1` occurrence is a
   hand-written fixture ref (`tests/unit/artifacts/test_matrix_projection.py:52,66,79,99,116`)"*
   omits three further occurrences:

```
$ grep -rn "artifact:shot_bible:shot_matrix:v1" tests/ --include=*.py
tests/unit/artifacts/test_matrix_projection.py:52,66,79,99,116
tests/unit/graph/test_generation_node_ledger.py:53,130
tests/unit/graph/test_context_packets.py:174
```

   They are also hand-written refs, so the substance survives, but the enumeration is
   presented as exhaustive and is not.

**Severity attack (§1.5).** The finding scores Critical (impact 4 × drift 4 = 16).
Impact 4 is not supported: the graph's matrix content is correct; the failure is that
one surface cannot *find* the other's artifact and the planning tool returns
"Run generate_shot_bible first." for a matrix that exists. That is wrong behaviour
which is fully recoverable by re-running the producer (recoverable internal/UX error),
not wrong behaviour reaching a human deliverable and not durable-data corruption. That
is impact **3**. Drift 4 is appropriate (the cross-surface disagreement is live and no
test pins the agreement). **3 × 4 = 12 → High**, not Critical.

**Class / prior art.** O4, prior art `new` — both present and appropriate.

**Double-counting.** No first-round duplicate. Within the post-verification batch it
shares its `MasterFilmMatrix` instance with `F-KBCTX-13` (see §2.3): the two findings
are distinct (artifact **id** vs `artifact_type`) but the roadmap must schedule the one
registry identity decision once, not twice.

**Verdict: DOWNGRADED to High (impact 3 × drift 4 = 12)**, plus required fixes
(§3, items 1–3).

---

### 2.2 `F-KBCTX-12` — `kb_context_packet` has no producer — **CONFIRMED**

**Anchors — all resolve:**

```
$ sed -n '185p' src/film_pipeline/artifacts/registry.py
        "kb_context_packet": _spec("kb_context_packet"),
$ sed -n '66p' src/film_pipeline/schemas/_base.py
    KB_CONTEXT_PACKET = "kb_context_packet"
$ sed -n '107,119p' src/film_pipeline/kb/packets.py
        return KBContextPacket(
            kb_context_id=f"kbctx:{project_id}:{agent_id}:{uuid4().hex[:8]}",
            ...
            payload=_build_payload_map(all_kept),
        )
```

The `_spec` call takes no keywords, so `payload_model` is indeed unbound.

**Reproduce — verbatim, output exactly as stated:**

```
$ grep -rn "kb_context_packet" --include=*.py src/ tests/
src/film_pipeline/artifacts/registry.py:185:        "kb_context_packet": _spec("kb_context_packet"),
src/film_pipeline/schemas/_base.py:66:    KB_CONTEXT_PACKET = "kb_context_packet"
tests/unit/test_schemas.py:645:def test_kb_context_packet_excluded_refs() -> None:
$ grep -rn "KBContextPacket" --include=*.py src/ | grep -i "save"
[exit=1]
```

The only test match builds the schema object, not the registered kind.

**Drift proof.** The mutation scenario is compound (it presumes `F-KBCTX-01` is fixed
first) but the silent failure is real and correctly reasoned: once a real packet is
built and its ref stamped, nothing writes the kind the ref names, and no test
round-trips `kb_context_packet`. The structural half of the proof is an existing
divergence in its own right — the registry/`ArtifactType` declare a kind with an empty
producer set. The finding is candid that it is latent and scopes severity accordingly.

**Severity.** Medium (impact 2 × drift 4 = 8) is defensible: latent, no current
consumer. No change.

**Class / prior art.** O4; prior art `new` and correctly distinguishes itself from
`F-KBCTX-01` (which owns the unwired builder and cross-references this finding at
`audit/09:145`). No double-count.

**Verdict: CONFIRMED.**

---

### 2.3 `F-KBCTX-13` — `_ARTIFACT_TYPE_BY_CLASS` is a second normative type model — **CONFIRMED-WITH-FIX**

**Anchors — all resolve:**

```
$ sed -n '300,321p' src/film_pipeline/graph/nodes/_context.py
_ARTIFACT_TYPE_BY_CLASS: dict[str, str] = {
    ...
    "MasterFilmMatrix": "shot_bible",
    ...
}
def _infer_artifact_type(artifact: Any) -> _ArtifactType:
    class_name = type(artifact).__name__
    try:
        return _ArtifactType(_ARTIFACT_TYPE_BY_CLASS.get(class_name, "script"))
    except ValueError:
        return _ArtifactType.SCRIPT
$ sed -n '119p' src/film_pipeline/graph/nodes/visual.py
    brief_ref = _save_artifact(new_state, brief, "execution_brief", "shot_bible")
$ sed -n '148p;758p' src/film_pipeline/artifacts/store.py
            artifact_type=meta.artifact_type,
        f"- type: {meta.artifact_type.value}",
```

The supporting claim "15 of 19 `_save_artifact` sites omit `artifact_type` (four pass
it explicitly: `generation.py:98`, `qc.py:88`, `_repair_loop.py:175`, `visual.py:546`)"
is exactly right:

```
$ grep -rn "_save_artifact(" --include=*.py src/film_pipeline/graph/ | grep -v "def _save_artifact" | wc -l
      19
$ for s in generation.py:98 qc.py:88 _repair_loop.py:175 visual.py:546; do ...; done
             artifact_type="generation_plan",      (generation.py:98)
             artifact_type="consensus_report",      (qc.py:88)
         artifact_type="script",                    (_repair_loop.py:175)
         artifact_type="generation_plan",           (visual.py:546)
```

The explicit writer `shot.py:199` uses `ArtifactType.MASTER_FILM_MATRIX` while the map
says `"shot_bible"`; both members exist in `schemas/_base.py:48,50`, so the divergence
is genuine. The finding also correctly names the fallback path (`_context.py:315-321`)
and the second, unrelated fallback in `_agent_artifacts.py:37-43`.

**Reproduce — verbatim, output as stated:**

```
$ sed -n '300,312p' src/film_pipeline/graph/nodes/_context.py
_ARTIFACT_TYPE_BY_CLASS: dict[str, str] = {
    ... (the 11-entry map) ...
}
$ grep -n "artifact_type" src/film_pipeline/graph/nodes/visual.py
546:        artifact_type="generation_plan",
$ sed -n '148p;758p' src/film_pipeline/artifacts/store.py
            artifact_type=meta.artifact_type,
        f"- type: {meta.artifact_type.value}",
```

**Drift proof — mutation executed and confirmed.** The finding claims nothing pins the
inferred type for classes absent from the map. No test references the map or the
inference helper at all:

```
$ grep -rn "_ARTIFACT_TYPE_BY_CLASS\|_infer_artifact_type" tests/
[exit=1]
```

I then changed the default fallback and ran the graph/artifact suites:

```
$ sed -i '' 's/_ARTIFACT_TYPE_BY_CLASS.get(class_name, "script")/_ARTIFACT_TYPE_BY_CLASS.get(class_name, "shot_bible")/' \
    src/film_pipeline/graph/nodes/_context.py
$ PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/unit/graph tests/unit/artifacts --no-cov -q -p no:cacheprovider
... 100% ...   (0 failures)
```

So the mutation claim holds. The **existing divergence** (map says `shot_bible`, the
explicit writer says `master_film_matrix`) is also real and is the stronger of the two
proofs.

**Evidence defect.** The drift proof asserts "(reproduced during verification:
`shot_bible execution_brief type=script`)" but records no command that produces it
(§1.6.4: counts/claims must name the command). Same for `F-KBCTX-11`'s
`.venv/bin/python` reproduction (see §3, item 2).

**Severity.** High (impact 3 × drift 4 = 12) stands: the wrong `artifact_type` is
written into the envelope and rendered into `current.md` and MCP listings
(`store.py:148,758`, `mcp/tools/artifacts.py:40`, `mcp/tools/projects.py:260` — all
verified) — externally visible but recoverable metadata, with no test pinning the map.

**Class / prior art.** O1, prior art `new` — appropriate. Note the shared
`MasterFilmMatrix` instance with `F-KBCTX-11` (§2.1): same underlying identity decision,
different field; cross-reference them and schedule one fix.

**Verdict: CONFIRMED-WITH-FIX** (record the command for the reproduced claim).

---

### 2.4 `F-MCP-13` — the transport erases the typed error code and carries no actor — **CONFIRMED**

**Anchors — all resolve:**

```
$ sed -n '61,65p' src/film_pipeline/mcp/_stdio_transport.py
    tool_response = await server.call(tool_name, arguments)
    if not tool_response.success:
        error = tool_response.error
        message = error.message if error is not None else "Tool call failed."
        return _jsonrpc_error(request_id, -32000, message)
$ sed -n '51,52p' src/film_pipeline/mcp/server.py
        actor_id: str | None = None,
        actor_type: str = "human",
$ sed -n '29,30p' src/film_pipeline/mcp/envelope.py
    actor_id: str | None = None
    actor_type: str = "human"
$ sed -n '188,199p' src/film_pipeline/mcp/server.py
        if registration.contract.requires_confirmation and not arguments.get("confirmed"):
            return MCPResponse(success=False, request_id=envelope.request_id,
                error=MCPError(code=MCPErrorCode.CONFIRMATION_REQUIRED, ...))
```

**Reproduce — verbatim, output as stated:**

```
$ git grep -n "actor_id" HEAD -- src/film_pipeline/mcp/
HEAD:src/film_pipeline/mcp/envelope.py:29:    actor_id: str | None = None
HEAD:src/film_pipeline/mcp/envelope.py:38:    actor_id: str | None = None,
HEAD:src/film_pipeline/mcp/envelope.py:46:        actor_id=actor_id,
HEAD:src/film_pipeline/mcp/server.py:51:        actor_id: str | None = None,
HEAD:src/film_pipeline/mcp/server.py:57:            actor_id=actor_id,
$ git grep -n -e "-32000" HEAD -- src/film_pipeline/mcp/
HEAD:src/film_pipeline/mcp/_stdio_transport.py:65:        return _jsonrpc_error(request_id, -32000, message)
```

The prose claim about the `src/`-wide grep also holds — the only extra match is the
unrelated `src/film_pipeline/schemas/audit.py:22`, and no handler reads
`_envelope.actor_id` / `.actor_type` (`git grep` over `src/film_pipeline/mcp/` returns
only the declaration, parameter, and construction sites). `_stdio_transport.py` is the
sole transport (`ls src/film_pipeline/mcp/`), and its call at `:61` is the only
`server.call(...)` in `src/`.

**Drift proof — existing divergence, demonstrated live.** The finding claims a client
sees `-32000` for `CONFIRMATION_REQUIRED` as well as `UNKNOWN_TOOL`. I drove the real
JSON-RPC path:

```
$ PYTHONPATH=/tmp/v20/src <venv>/bin/python - <<'EOF'
import asyncio
from film_pipeline.mcp.contract import make_registry
from film_pipeline.mcp.server import MCPServer, handle_jsonrpc
reg = make_registry(); gated = [c["name"] for c in reg.catalog() if c.get("requires_confirmation")]
server = MCPServer(); name = gated[0]
print(asyncio.run(handle_jsonrpc(server, {"jsonrpc":"2.0","id":1,"method":"tools/call",
      "params":{"name":name,"arguments":{}}})))
print(asyncio.run(server.call(name, {})).error.code)
EOF
{'jsonrpc': '2.0', 'id': 1, 'error': {'code': -32000, 'message': "Tool 'approve_coverage_generation' requires explicit confirmation. Pass 'confirmed': true to proceed."}}
confirmation_required
```

In-process the code is `confirmation_required`; on the wire it is `-32000`. Both sites
cited, divergence live. The actor half is confirmed by the same grep (no reader, no
transport argument).

**Severity.** High (impact 3 × drift 4 = 12) stands. Note that
`tests/unit/test_mcp.py:473` asserts the erasure for `UNKNOWN_TOOL`
(`assert response["error"] == {"code": -32000, "message": "Unknown tool: does_not_exist"}`),
so the transport side is deliberately pinned; that does not reduce the drift of the
*taxonomy-to-wire* agreement, which no test pins.

**Class / prior art.** O8 with the actor half flagged as adjacent to D5 — both
appropriate. **Partial double-count:** the error-code half is already stated in
`F-MCP-10` (audit 11:321, the post-verification correction that cross-references
`F-MCP-13`); the actor-attribution half is new. The audit cross-links them, so this is
a disclosed overlap, not hidden duplication — but the roadmap must fix the wire mapping
once.

**Verdict: CONFIRMED.**

---

### 2.5 `F-MCP-14` — `MCPServer.active_project_id` is write-only — **CONFIRMED**

**Anchors — all resolve:** `server.py:44` (field), `:121`/`:157` (writes in project
resolution), `:230-231` (write on registration), `runtime.py:207-213` (the state tools
read), `helpers.py:38-52` (the reader that uses `rt.get_active()`).

**Reproduce — verbatim; output matches the prose exactly** (the `MCPServer` field occurs
only as declaration + writes; every other `mcp/` match is the unrelated
`helpers._active_project_id`):

```
$ git grep -n "active_project_id" HEAD -- src/film_pipeline/mcp/ src/film_pipeline/app/runtime.py
... runtime.py:44,176,177,207,211,213; server.py:44,121,157,230,231; helpers.py:38 + 20 tool call sites ...
```

No `src/` module reads `server.active_project_id`. The five assertions that do read it
are tests:

```
$ git grep -n "active_project_id" HEAD -- tests/ | grep "server\."
tests/unit/test_mcp.py:590,598,616,628,653:    assert server.active_project_id == ...
```

**Drift proof.** The proof is a mutation scenario "with no observable effect", i.e. a
non-consumption argument rather than a two-site divergence; the finding says so
explicitly. It is the same form as the first-round, already-verified `F-MCP-08`
(dead duplicate normative state) and is accepted on that precedent. Caveat: because
five tests assert the field, deleting it is not free — the guard test proposed
("`active_project_id` appears in exactly one state owner module") will require those
test edits, which the finding should acknowledge.

**Severity.** Medium (impact 2 × drift 3 = 6) is appropriate: no current consumer, no
user-visible effect, future-middleware hazard. No change.

**Class / prior art.** O3 (written by two modules, read from one) with prior art
`F-MCP-07` — appropriate. No double-count (F-MCP-07 owns the two *registries*; this is
the active pointer).

**Verdict: CONFIRMED.**

---

### 2.6 `F-MCP-15` — `ToolContract.idempotency_key_field` is dead normative state — **CONFIRMED**

**Anchors — all resolve:** `contract.py:57` (declaration), `contract.py:110` (catalog
echo), `registry.py:104-117` (`_tool_contract` has no such parameter).

**Reproduce — verbatim, output as stated (only declaration + echo):**

```
$ git grep -n "idempotency_key_field" HEAD -- src/ tests/
HEAD:src/film_pipeline/mcp/contract.py:57:    idempotency_key_field: str | None = None
HEAD:src/film_pipeline/mcp/contract.py:110:                    "idempotency_key_field": c.idempotency_key_field,
```

The "measured 0/77 populated" claim is exactly reproducible:

```
$ PYTHONPATH=/tmp/v20/src <venv>/bin/python -c "
from film_pipeline.mcp.contract import make_registry
cat = make_registry().catalog()
print(len(cat), sum(1 for c in cat if c.get('idempotency_key_field')))"
77 0
```

`ToolContract(` occurs exactly once in `src/` (`registry.py:110`), so the constructor
really is the only producer.

**Drift proof.** "Set the field on any tool; nothing changes, no test fails" is a valid
§1.6.3(b) silent-failure mutation and is verified by the zero-reader grep.

**§1.3 caveat (not a rejection).** `F-MCP-15`'s `Prior art` calls it "the same O1
pattern as `F-MCP-08`", but `F-MCP-08` has two owners (the envelope copy and the
contract copy) whereas `idempotency_key_field` is declared **once** (`contract.py:57`)
and merely never populated. Strictly, this is a declared-but-unenforced field (the O8
reading the finding itself notes) rather than two modules independently satisfying N/I/R.
The drift proof survives; the `O1` label is defensible only by analogy. Fixed by
wording, not by re-scoring.

**Severity.** Medium (impact 2 × drift 3 = 6) is appropriate: the catalog advertises a
dedupe contract the system does not honour, but no current client depends on it. No
change.

**Verdict: CONFIRMED** (recommended wording fix in §3).

---

### 2.7 `F-BUD-06` — a sixth budget-cap vocabulary — **CONFIRMED**

**Anchors — all resolve:**

```
$ sed -n '59p' src/film_pipeline/graph/orchestrator_state.py
_BUDGET_SNAPSHOT = f"{_ORCH_NS}__budget_snapshot"
$ sed -n '121,123p' src/film_pipeline/graph/context_packets.py
    budget = state.get("budget_snapshot", {})
    cap = budget.get("cap_usd", 0) if isinstance(budget, dict) else 0
    parts.append(f"Budget cap: ${cap}")
$ sed -n '177p;196p' src/film_pipeline/graph/state_schema.py
    budget_snapshot: dict[str, object]
    _orchestrator__budget_snapshot: dict[str, Any]
$ sed -n '251p' src/film_pipeline/app/services/operator.py
            budget_snapshot=dict(ostate.get_budget_snapshot(state)),
$ sed -n '64p' src/film_pipeline/app/services/models.py
    budget_snapshot: dict[str, Any] = field(default_factory=dict)
$ sed -n '175p' tests/unit/graph/test_context_packets.py
            "budget_snapshot": {"cap_usd": 42},
```

**Reproduce — verbatim; output exactly as stated** (only the read and the test
fabrication match; the orchestrator-owned key is the namespaced one):

```
$ grep -rn '"budget_snapshot"' src/ tests/ | grep -v __pycache__
src/film_pipeline/graph/context_packets.py:121:    budget = state.get("budget_snapshot", {})
tests/unit/graph/test_context_packets.py:175:            "budget_snapshot": {"cap_usd": 42},
$ sed -n '59p' src/film_pipeline/graph/orchestrator_state.py
_BUDGET_SNAPSHOT = f"{_ORCH_NS}__budget_snapshot"
$ sed -n '177p;196p' src/film_pipeline/graph/state_schema.py
    budget_snapshot: dict[str, object]
    _orchestrator__budget_snapshot: dict[str, Any]
$ grep -rn "scoped_context" src/
src/film_pipeline/graph/nodes/_agent_prompt_context.py:116:            context_vars["scoped_context"] = builder(state, services)
$ grep -n "budget_snapshot" src/film_pipeline/graph/context_packets.py
121:    budget = state.get("budget_snapshot", {})
```

The blast-radius claim "no prompt template contains `{scoped_context}`" also holds (the
grep returns only the assignment).

**Drift proof — existing divergence, demonstrated live.** The reader's key is never
written, so the cap is always 0. I drove the owner's writer and the reader's exact
expression:

```
$ PYTHONPATH=/tmp/v20/src <venv>/bin/python - <<'EOF'
from film_pipeline.graph import orchestrator_state as ostate
state = {}; ostate.ensure_orchestrator_state(state)
ostate.update_budget_snapshot(state, cap_usd=500.0, spent_usd=10.0, threshold_exceeded=False)
print("owner cap_usd:", ostate.get_budget_snapshot(state)["cap_usd"])
print("plain key in state:", "budget_snapshot" in state)
budget = state.get("budget_snapshot", {}); cap = budget.get("cap_usd", 0) if isinstance(budget, dict) else 0
print("context_packets renders: Budget cap: $%s" % cap)
EOF
owner cap_usd: 500.0
plain key in state: False
context_packets renders: Budget cap: $0
```

**Mutation executed and confirmed.** Deleting the plain channel leaves the suite green
(the covering test manufactures the key):

```
$ sed -i '' '177d' src/film_pipeline/graph/state_schema.py
$ PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/unit/graph --no-cov -q -p no:cacheprovider
... 100% ...   (0 failures)
```

**Severity.** High (impact 2 × drift 5 = 10) is correct under §1.5: impact 2 (the wrong
string is computed and dropped today — latent) times drift 5 (demonstrated: no test
fails when the channel changes). No change.

**Class / prior art.** O7 (with O8/O5 readings noted) — appropriate. The prior-art
reference is written as a **bare basename**: `arch-lens-dataflow.md:32`
(audit/12:1039). The file is `documentation/reviews/arch-lens-dataflow.md`, and line 32
does discuss the `budget_snapshot` (orch) channel's missing writer as claimed. Flag as a
readability defect (§3).

**Double-counting.** Adjacent to `F-BUD-04` (also a writerless plain `budget_*` key read
by prompt context) but a different key (`budget_snapshot` vs `budget_cap`) and a
different consumer (`context_packets.build_gen_planning_context` vs
`gen_planner_agent.prepare`). Not a duplicate; cross-reference them so the `budget`
extraction deletes both keys once.

**Verdict: CONFIRMED.**

---

### 2.8 `F-TEST-09` — runtime injection re-derived at dozens of call sites — **CONFIRMED-WITH-FIX**

**Anchors — all resolve:** `tests/conftest.py:51` (autouse rebind),
`tests/unit/mcp/tools/conftest.py:29,34` (second autouse rebind), and the dominant
pattern at `tests/unit/mcp/tools/test_artifacts.py:130`.

**Reproduce — three commands reproduce; the fourth does not.**

The revision I first read had a two-command `Reproduce` block (67 and 31). The file was
edited during verification to a four-command block (the current revision pinned in
§1.2). Running the **current** block verbatim in the pristine snapshot:

```
$ grep -rn 'monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime"' --include='*.py' tests | wc -l
      67          # matches the finding
$ grep -rn 'mock.patch("film_pipeline.mcp.tools.get_runtime"' --include='*.py' tests | wc -l
       3          # matches
$ grep -rn 'mcp_tools.get_runtime = \|tools_pkg.get_runtime = ' tests | wc -l
       5          # matches
$ grep -rln 'mcp.tools.get_runtime\|mcp_tools.get_runtime\|tools_pkg.get_runtime' tests | wc -l
      12          # finding text and fence comment say 31
```

The `31` reproduces **only in the author's working tree**, because the fourth command has
no `--include='*.py'` and therefore counts compiled bytecode:

```
$ cd ${REPO_ROOT}   # has __pycache__
$ grep -rln 'mcp.tools.get_runtime\|mcp_tools.get_runtime\|tools_pkg.get_runtime' tests | wc -l
      31
$ grep -rln --include='*.py' 'mcp.tools.get_runtime\|mcp_tools.get_runtime\|tools_pkg.get_runtime' tests | wc -l
      12
```

So the finding's bolded "= **31 files**" and the fence comment `# 31` are an artefact of
stale `.pyc` files in the working tree; the source-file count at the pinned revision is
**12**. This is a §1.6.4 / §1.6.7 defect: the count is presented as mechanically
reproducible but is environment-dependent and counts the wrong thing. (Commands 1–3 are
stable in both environments, so the moved-in 3 / 5 counts the adversarial evidence
replay flagged are now inside the `Reproduce` block and are correct.)

**Drift proof — mutation executed and confirmed.** The finding claims deleting either
autouse conftest leaves the suite green because the other compensates. I tested both
directions:

```
$ sed -i '' '51s/.*/    # MUTATION: rebind removed/' tests/conftest.py
$ PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/unit/mcp/tools tests/unit/test_mcp.py --no-cov -q -p no:cacheprovider
... 100% ...   (0 failures)

$ sed -i '' 's/^    tools_pkg.get_runtime = get_runtime$/    pass  # MUTATION/' tests/unit/mcp/tools/conftest.py
$ PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/unit/mcp/tools --no-cov -q -p no:cacheprovider
... 100% ...   (0 failures)
```

Both partial edits pass, so the "partial edit is invisible" claim holds.

**Evidence defect (minor).** The finding says the order-dependence comment at
`tests/conftest.py:32-36` "was added for" the `get_runtime` rebind. That quote documents
the `FILM_PIPELINE_MCP_MODE` env leak; the rebind's own rationale is at `:46-48`
("a stale MagicMock must never survive into the next test"). The failure *class*
overlaps, but the attribution is wrong.

**Severity.** Medium (impact 2 × drift 4 = 8) stands. This is a finding whose only
victim is the test harness — impact 2 is already at the floor for a non-cosmetic
defect, and drift 4 is conservative (no test can fail; §1.5 would allow 5). It should be
recorded as a harness-quality finding and not scheduled ahead of product seams.

**Class / prior art.** O5 + O2; prior art cites `verify-13.md:207-214` (a bare
basename — see §3) and is accurate that this was a verifier-found gap not covered by
`F-TEST-05`/`F-TEST-06`.

**Verdict: CONFIRMED-WITH-FIX** (fix the fourth `Reproduce` command and its stated
count).

---

### 2.9 `F-TEST-10` — `provider_health` holds two incompatible value types — **CONFIRMED-WITH-FIX**

**Anchors — all resolve:**

```
$ sed -n '51p' src/film_pipeline/app/runtime.py
    provider_health: dict[str, Any] = field(default_factory=dict)
$ sed -n '386,389p' src/film_pipeline/app/runtime.py
    def set_provider_health(self, provider_id: str, status: str, reason: str = "") -> None:
        self.provider_health[provider_id] = {"status": status, "reason": reason}

    def get_provider_health(self, provider_id: str) -> dict[str, Any] | None:
$ sed -n '35p;53p' tests/e2e/test_scenario_04_quota_exhausted.py
        rt.provider_health["mock-video-provider"] = health
        rt.provider_health["mock-video-provider"] = ProviderHealthState(
$ sed -n '158,161p' tests/e2e/conftest.py
    rt.provider_health["mock-video-provider"] = {
        "status": "healthy",
        "reason": "",
    }
$ sed -n '24p' src/film_pipeline/mcp/tools/providers.py
    return _ok(provider_id=provider_id, status=health["status"], reason=health.get("reason", ""))
$ sed -n '48p' src/film_pipeline/app/health.py
        if h and h.get("status") != "healthy":
$ sed -n '12p' src/film_pipeline/schemas/provider_health.py
class ProviderHealthState(MutableSchemaBase):
```

**Reproduce — verbatim, output matches the prose:**

```
$ grep -n "provider_health" src/film_pipeline/app/runtime.py
51,382,386,387,389,390,393,395,397,429
$ grep -rn "ProviderHealthState" --include='*.py' tests/e2e
tests/e2e/test_scenario_04_quota_exhausted.py:14,29,53
$ grep -rn 'health\["status"\]\|h.get("status")' src/film_pipeline
src/film_pipeline/app/health.py:48
src/film_pipeline/graph/orchestrator_state.py:434,442
src/film_pipeline/mcp/tools/providers.py:24,48
```

**Drift proof — mutation executed and confirmed.** The object type the e2e test stores
is not a mapping:

```
$ PYTHONPATH=/tmp/v20/src <venv>/bin/python - <<'EOF'
from film_pipeline.schemas.provider_health import ProviderHealthState
from film_pipeline.schemas._base import ProviderStatus
h = ProviderHealthState(provider_id="p", status=ProviderStatus.BLOCKED_QUOTA,
                        blocked_reason="q", quota_state="exhausted")
for expr, fn in [('h["status"]', lambda: h["status"]), ('h.get("status")', lambda: h.get("status"))]:
    try: print(expr, "->", fn())
    except Exception as e: print(expr, "->", type(e).__name__, e)
EOF
h["status"] -> TypeError 'ProviderHealthState' object is not subscriptable
h.get("status") -> AttributeError 'ProviderHealthState' object has no attribute 'get'
```

No test feeds an object to a reader: the only reader call sites are
`tests/unit/mcp/tools/test_providers.py:16,22`, `tests/unit/test_mcp.py:865`, and
`tests/smoke/test_operator_workflow.py:247`, and the smoke/e2e fixtures seed plain dicts
(`tests/e2e/conftest.py:158-161`). The claim holds.

**Evidence defect.** The blast radius says "e2e scenarios 4 and 5". Only scenario 4
touches `provider_health` at all:

```
$ grep -rn "provider_health\|ProviderHealthState" tests/e2e/test_scenario_05_network_error.py
[exit=1]
```

Scenario 5 is the generation-ledger duplicate-submit scenario. Fix to "scenario 4".

**Severity.** Medium (impact 2 × drift 4 = 8) stands — latent, no production path is fed
the object type today.

**Class / prior art.** O3; prior art cites the verifier's missed-seam note
(`verify-13.md:215-220`, bare basename). No double-count with first-round findings.

**Verdict: CONFIRMED-WITH-FIX** (correct the blast radius).

---

### 2.10 `F-TEST-11` — e2e can build a real `GitBackend` where the session installs the double — **CONFIRMED-WITH-FIX**

**Anchors — all resolve:**

```
$ sed -n '78p' tests/conftest.py
    set_git_backend_type(InMemoryGitBackend)
$ sed -n '113,114p' tests/e2e/conftest.py
def git_backend(tmp_path: Path) -> GitBackend:
    return GitBackend.init_temp(tmp_path / "repo")
```

**Reproduce — second command's stated output is wrong.**

```
$ grep -rn "GitBackend.init_temp" tests/e2e tests/smoke
tests/e2e/conftest.py:114:    return GitBackend.init_temp(tmp_path / "repo")
$ grep -rn "git_backend\|checkpoint_manager" tests/e2e tests/smoke | grep -v "def \|import"
tests/e2e/conftest.py:119:    return CheckpointManager(git_backend)
tests/smoke/conftest.py:6:    checkpoint_manager,
tests/smoke/conftest.py:7:    git_backend,
```

The finding says the command "returns only the definitions/imports
(`tests/e2e/conftest.py:113,118`; `tests/smoke/conftest.py:6-7`)". Lines 113 and 118
are the `def` lines, which the command's own `grep -v "def \|import"` filter removes;
the command actually prints line **119** (the `CheckpointManager` return), which the
finding does not mention. The substantive conclusion (no e2e/smoke **test** requests
either fixture) still holds, but the printed-output description is wrong (§1.6.7).

**Drift proof — mutation executed and demonstrated.** I added a probe test that requests
the fixture in the e2e tier:

```
$ cat > tests/e2e/test_zz_probe.py <<'EOF'
def test_probe_git_backend(git_backend):
    from film_pipeline.artifacts.project_storage import get_git_backend_type
    print("FIXTURE TYPE:", type(git_backend).__name__)
    print("INJECTED TYPE:", get_git_backend_type().__name__)
EOF
$ PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/e2e/test_zz_probe.py -n0 --no-cov -q -p no:cacheprovider -s
FIXTURE TYPE: GitBackend
INJECTED TYPE: InMemoryGitBackend
```

So the same tier hands one test a real subprocess-git backend while the session installs
the in-process double, and nothing fails. (`tests/smoke/conftest.py` re-exports the same
fixture.)

**Severity.** Medium (impact 2 × drift 4 = 8) stands, with the harness-only caveat
stated explicitly: this finding's only victim is the test harness, and it is latent
today (the fixture is unrequested). Impact 2 is correct; drift 4 is conservative (no
test can fail when the injected type or the fixture changes). It should not be scored
against product impact.

**Class / prior art.** O6 + O2; prior art cites `verify-13.md:223-225` (bare basename).
Distinct from `F-TEST-03` (the whole-suite double's missing parity test) and
`F-TEST-04` (the storage-store bypass): this is a *real-backend* fixture inside the
doubled tier. No double-count.

**Verdict: CONFIRMED-WITH-FIX** (correct the stated output of the second command).

---

## 3. Summary

| # | finding | verdict | severity (as filed) | severity (verified) | principal defect found |
|---|---|---|---|---|---|
| 1 | `F-KBCTX-11` | **DOWNGRADED** | Critical (4×4=16) | **High (3×4=12)** | mutation proof falsified (a test fails); `input_schema` grep undercounts 26→3; fixture enumeration incomplete |
| 2 | `F-KBCTX-12` | CONFIRMED | Medium (2×4=8) | Medium (2×4=8) | — |
| 3 | `F-KBCTX-13` | CONFIRMED-WITH-FIX | High (3×4=12) | High (3×4=12) | reproduced claim has no command |
| 4 | `F-MCP-13` | CONFIRMED | High (3×4=12) | High (3×4=12) | partial (disclosed) overlap with `F-MCP-10` |
| 5 | `F-MCP-14` | CONFIRMED | Medium (2×3=6) | Medium (2×3=6) | drift proof is non-consumption; 5 tests assert the field |
| 6 | `F-MCP-15` | CONFIRMED | Medium (2×3=6) | Medium (2×3=6) | O1 label is by analogy only (single owner) |
| 7 | `F-BUD-06` | CONFIRMED | High (2×5=10) | High (2×5=10) | bare prior-art basename |
| 8 | `F-TEST-09` | CONFIRMED-WITH-FIX | Medium (2×4=8) | Medium (2×4=8) | 4th `Reproduce` counts `.pyc`: 31 stated, 12 real; comment mis-attributed |
| 9 | `F-TEST-10` | CONFIRMED-WITH-FIX | Medium (2×4=8) | Medium (2×4=8) | blast radius names scenario 5, which has no `provider_health` |
| 10 | `F-TEST-11` | CONFIRMED-WITH-FIX | Medium (2×4=8) | Medium (2×4=8) | 2nd `Reproduce` output described as `:113,118`; it prints `:119` |

Totals: **5 CONFIRMED, 4 CONFIRMED-WITH-FIX, 1 DOWNGRADED, 0 REJECTED.**

No finding is rejected, because none fails §1.6.3 outright: `F-KBCTX-11` has a valid
*existing-divergence* proof alongside its falsified mutation, and the remaining nine
drift proofs survived their mutations. No finding needs to move to an
unverified-hypothesis section under §1.6.6 — each was independently reproduced, including
the two that are latent (`F-KBCTX-12`, `F-TEST-11`).

### Text-vs-command mismatches (the specific danger)

Three of the ten `Reproduce` blocks state output their own command does not print:

1. **`F-TEST-09`** — cmd 4 `# 31`, real **12** at the pinned revision (31 only when
   `.pyc` files are present; no `--include='*.py'`). This is the finding flagged by the
   adversarial evidence replay for its 3 / 5 counts; those two are now inside the block
   and correct, but the 31 is still wrong.
2. **`F-TEST-11`** — cmd 2 is described as printing `:113,118`; it prints `:119`
   (`:113`/`:118` are filtered out by the command's own `grep -v "def \|import"`).
3. **`F-KBCTX-11`** — the prose characterization of
   `grep -rn "input_schema" --include=*.py src/` ("the field's definition plus two
   unrelated MCP tool schemas") suppresses 23 of the 26 real matches.

The other seven `Reproduce` blocks reproduce their stated output.

---

## 4. What the authors should fix

1. **`F-KBCTX-11` — rewrite the drift proof and re-score.** Delete or correct the
   `visual.py:447` mutation claim ("no test fails" is false:
   `tests/unit/graph/test_shot_bible_structure.py:180` loads by the hard-coded id and
   fails). Keep the existing-divergence proof, which is sound. Change severity to
   **High (impact 3 × drift 4 = 12)** and state why impact is 3 (recoverable
   cross-surface refusal, no deliverable/data corruption). Correct the `input_schema`
   parenthetical to report all 26 matches (or add `ValidatorRegistryEntry.` to the
   pattern). Add the three omitted `artifact:shot_bible:shot_matrix:v1` occurrences
   (`tests/unit/graph/test_generation_node_ledger.py:53,130`,
   `tests/unit/graph/test_context_packets.py:174`) or drop "every other".
2. **`F-KBCTX-13`** — record the exact command that produced
   `shot_bible execution_brief type=script`; likewise record the `.venv/bin/python`
   reproduction cited in prose by `F-KBCTX-11`. Add a cross-reference to `F-KBCTX-11`
   so the one `MasterFilmMatrix` identity decision is scheduled once.
3. **`F-TEST-09`** — add `--include='*.py'` to the fourth `Reproduce` command and change
   both the bolded count and the fence comment from `31` to `12`; note explicitly that
   the unfiltered form returns 31 only because it counts `__pycache__`/`.pyc`. Move the
   order-dependence citation from `tests/conftest.py:32-36` to `:46-48` (or quote both).
4. **`F-TEST-10`** — change "e2e scenarios 4 and 5" to "e2e scenario 4`"; scenario 5
   (`test_scenario_05_network_error.py`) contains no `provider_health` reference.
5. **`F-TEST-11`** — correct the second `Reproduce` command's stated output: it prints
   `tests/e2e/conftest.py:119` plus `tests/smoke/conftest.py:6-7`, not
   `tests/e2e/conftest.py:113,118`.
6. **`F-MCP-14`** — state that the field is asserted by five first-round tests
   (`tests/unit/test_mcp.py:590,598,616,628,653`), so the proposed deletion and its
   guard test require those edits; this does not change the severity.
7. **`F-MCP-15`** — reclassify: with a single declaring module
   (`contract.py:57`) and a constructor that never populates it, this is a
   declared-but-unenforced field (O8 reading) rather than two-module O1 distributed
   ownership. Keep the finding; align the class with the evidence as `F-MCP-08` did.
8. **Bare-basename prior-art references** (readability defect, §1.6.4 as applied by this
   program): `arch-lens-dataflow.md:32` in `F-BUD-06` →
   `documentation/reviews/arch-lens-dataflow.md:32`; `verify-13.md:207-214`, `:215-220`,
   `:223-225` in `F-TEST-09/10/11` → `reviews/verify-13.md:…` (or the full docs path).
9. **Program-level:** audits 11 and 13 were edited during this verification (see §1.2).
   Since docs are untracked and concurrently revised, pin the revision inside each
   finding block as `00-methodology` §1.6.8 requires; the moved-in `3`/`5` counts in
   `F-TEST-09` are an improvement, but a changed `Reproduce` block silently invalidates
   a verifier's prior run.

---

## 5. Commands run (complete)

All commands below were run from `/tmp/v20` unless the working directory is shown as the
repo (only `git grep`-against-`HEAD` and the `.pyc`-inflation comparison were run in the
repo, both read-only). `<venv>` abbreviates
`${REPO_ROOT}/.venv`.

```
# snapshot + identity
mkdir -p /tmp/v20 && git archive fb85baa | tar -x -C /tmp/v20
git rev-parse HEAD
diff -rq /tmp/v20 /tmp/v20-check
PYTHONPATH=/tmp/v20/src <venv>/bin/python -c "import film_pipeline; print(film_pipeline.__file__)"

# F-KBCTX-11
sed -n '157p;192p' src/film_pipeline/artifacts/registry.py
sed -n '447p' src/film_pipeline/graph/nodes/visual.py
sed -n '108p;230p' src/film_pipeline/mcp/tools/planning.py
grep -rn "master_film_matrix" --include=*.py src/film_pipeline/graph/
grep -rn "input_schema" --include=*.py src/ | wc -l
grep -rn "artifact:shot_bible:shot_matrix:v1" tests/ --include=*.py
sed -n '180p' tests/unit/graph/test_shot_bible_structure.py
sed -i '' 's/...shot_matrix.../...master_film_matrix.../' src/film_pipeline/graph/nodes/visual.py   # mutation
PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/unit/graph tests/unit/mcp/tools/test_bibles.py \
    tests/unit/mcp/tools/test_planning.py tests/unit/artifacts --no-cov -q -p no:cacheprovider
PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/unit/graph/test_shot_bible_structure.py \
    -n0 --no-cov -q -p no:cacheprovider

# F-KBCTX-12
sed -n '185p' src/film_pipeline/artifacts/registry.py
sed -n '66p' src/film_pipeline/schemas/_base.py
sed -n '107,119p' src/film_pipeline/kb/packets.py
grep -rn "kb_context_packet" --include=*.py src/ tests/
grep -rn "KBContextPacket" --include=*.py src/ | grep -i "save"

# F-KBCTX-13
sed -n '300,321p' src/film_pipeline/graph/nodes/_context.py
sed -n '119p' src/film_pipeline/graph/nodes/visual.py
sed -n '148p;758p' src/film_pipeline/artifacts/store.py
grep -rn "_save_artifact(" --include=*.py src/film_pipeline/graph/ | grep -v "def _save_artifact"
grep -rn "_ARTIFACT_TYPE_BY_CLASS\|_infer_artifact_type" tests/
sed -i '' 's/get(class_name, "script")/get(class_name, "shot_bible")/' src/film_pipeline/graph/nodes/_context.py  # mutation
PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/unit/graph tests/unit/artifacts --no-cov -q -p no:cacheprovider

# F-MCP-13
sed -n '40,75p' src/film_pipeline/mcp/_stdio_transport.py
sed -n '40,60p' src/film_pipeline/mcp/server.py
sed -n '20,40p' src/film_pipeline/mcp/envelope.py
sed -n '180,205p' src/film_pipeline/mcp/server.py
sed -n '1,25p' src/film_pipeline/mcp/errors.py
git grep -n "actor_id" HEAD -- src/film_pipeline/mcp/
git grep -n -e "-32000" HEAD -- src/film_pipeline/mcp/
git grep -n "actor_id" HEAD -- src/
git grep -n "actor_type\|\.actor_id\|envelope.actor" HEAD -- src/film_pipeline/mcp/
git grep -n -- "-32000" HEAD -- tests/
<JSON-RPC drift demo, see 2.4>

# F-MCP-14
sed -n '118,124p;155,160p;226,234p' src/film_pipeline/mcp/server.py
sed -n '203,215p' src/film_pipeline/app/runtime.py
sed -n '36,54p' src/film_pipeline/mcp/tools/helpers.py
git grep -n "active_project_id" HEAD -- src/film_pipeline/mcp/ src/film_pipeline/app/runtime.py
git grep -n "active_project_id" HEAD -- tests/ | grep "server\."

# F-MCP-15
sed -n '48,60p;105,115p' src/film_pipeline/mcp/contract.py
sed -n '105,120p' src/film_pipeline/mcp/tools/registry.py
git grep -n "idempotency_key_field" HEAD -- src/ tests/
git grep -n "ToolContract(" HEAD -- src/
PYTHONPATH=/tmp/v20/src <venv>/bin/python -c "from film_pipeline.mcp.contract import make_registry; c=make_registry().catalog(); print(len(c), sum(1 for x in c if x.get('idempotency_key_field')))"

# F-BUD-06
sed -n '55,62p' src/film_pipeline/graph/orchestrator_state.py
sed -n '115,140p' src/film_pipeline/graph/context_packets.py
sed -n '174,198p' src/film_pipeline/graph/state_schema.py
sed -n '245,255p' src/film_pipeline/app/services/operator.py
sed -n '60,68p' src/film_pipeline/app/services/models.py
sed -n '170,180p' tests/unit/graph/test_context_packets.py
grep -rn '"budget_snapshot"' src/ tests/ | grep -v __pycache__
sed -n '59p' src/film_pipeline/graph/orchestrator_state.py
sed -n '177p;196p' src/film_pipeline/graph/state_schema.py
grep -rn "scoped_context" src/
grep -n "budget_snapshot" src/film_pipeline/graph/context_packets.py
<live cap demo, see 2.7>
sed -i '' '177d' src/film_pipeline/graph/state_schema.py   # mutation
PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/unit/graph --no-cov -q -p no:cacheprovider
sed -n '28,36p' documentation/reviews/arch-lens-dataflow.md

# F-TEST-09
sed -n '1,27p;75,82p' tests/conftest.py
sed -n '1,35p' tests/unit/mcp/tools/conftest.py
sed -n '126,132p' tests/unit/mcp/tools/test_artifacts.py
sed -n '27,35p' tests/unit/mcp/tools/test_planning.py
grep -rn 'monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime"' --include='*.py' tests | wc -l
grep -rn 'mock.patch("film_pipeline.mcp.tools.get_runtime"' --include='*.py' tests | wc -l
grep -rn 'mcp_tools.get_runtime = \|tools_pkg.get_runtime = ' tests | wc -l
grep -rln 'mcp.tools.get_runtime\|mcp_tools.get_runtime\|tools_pkg.get_runtime' tests | wc -l
# same four commands re-run in the repo (has __pycache__) and in /tmp/v20-clean
sed -i '' '51s/.*/    # MUTATION: rebind removed/' tests/conftest.py                                   # mutation A
PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/unit/mcp/tools tests/unit/test_mcp.py --no-cov -q -p no:cacheprovider
sed -i '' 's/^    tools_pkg.get_runtime = get_runtime$/    pass  # MUTATION/' tests/unit/mcp/tools/conftest.py  # mutation B
PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/unit/mcp/tools --no-cov -q -p no:cacheprovider

# F-TEST-10
sed -n '49,53p;383,392p' src/film_pipeline/app/runtime.py
sed -n '30,56p' tests/e2e/test_scenario_04_quota_exhausted.py
sed -n '154,163p' tests/e2e/conftest.py
sed -n '18,26p' src/film_pipeline/mcp/tools/providers.py
sed -n '38,52p' src/film_pipeline/app/health.py
sed -n '10,14p' src/film_pipeline/schemas/provider_health.py
grep -n "provider_health" src/film_pipeline/app/runtime.py
grep -rn "ProviderHealthState" tests/e2e
grep -rn 'health\["status"\]\|h.get("status")' src/film_pipeline
grep -rn "provider_health\|ProviderHealthState" tests/e2e/test_scenario_05_network_error.py
PYTHONPATH=/tmp/v20/src <venv>/bin/python -m pytest tests/e2e/test_scenario_04_quota_exhausted.py -n0 --no-cov -q -p no:cacheprovider
<subscript/get demo, see 2.9>

# F-TEST-11
sed -n '108,125p' tests/e2e/conftest.py
sed -n '1,12p' tests/smoke/conftest.py
grep -rn "GitBackend.init_temp" tests/e2e tests/smoke
grep -rn "git_backend\|checkpoint_manager" tests/e2e tests/smoke | grep -v "def \|import"
<probe-test demo, see 2.10>
```

Every test command in this document passed on the pristine snapshot before its mutation,
and the snapshot was verified byte-identical to a fresh extraction afterwards.
