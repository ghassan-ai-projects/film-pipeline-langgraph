"""Channel-registry parity and node-boundary propagation contracts [D1/DF-F1/DF-F2].

Three layers of guard:

1. *Triangle completeness* — orchestrator constants, ``GraphState`` schema
   declarations, and ``ORCH_CHANNELS`` rows must agree exactly. Adding an
   orchestrator state key anywhere without a registry row fails here.
2. *Propagation parity* — ``_propagate_side_effects`` copies each registered
   key according to its declared policy, and only those keys.
3. *Writer sweep* — every direct subscript write to a boundary key inside
   ``graph/nodes/**`` must carry a recorded disposition, so a write into the
   node working copy can never silently die at the boundary again (the
   D-009 bug class).
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest

from film_pipeline.app.mock_responses import default_mock_responses
from film_pipeline.graph.nodes._agent_handoff import _propagate_side_effects
from film_pipeline.graph.orchestrator_state import ORCH_CHANNELS, OrchChannelSpec
from film_pipeline.graph.state_schema import StudioGraphState

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ORCH_STATE_PATH = _REPO_ROOT / "src" / "film_pipeline" / "graph" / "orchestrator_state.py"
_NODES_DIR = _REPO_ROOT / "src" / "film_pipeline" / "graph" / "nodes"

# Reducer channels declared on GraphState that cross node boundaries but are
# not orchestrator-namespaced; swept alongside the registry keys.
_EXTRA_SWEEP_KEYS = frozenset(
    {"artifact_refs", "generation_requests", "_qc_reports", "_qc_raw_reports"}
)


# --- 1. Triangle completeness ------------------------------------------------


def _ast_orchestrator_keys() -> set[str]:
    """Collect the ``_ORCH_NS``-built state keys defined in orchestrator_state."""
    tree = ast.parse(_ORCH_STATE_PATH.read_text())
    keys: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            value = node.value
            if (
                isinstance(target, ast.Name)
                and isinstance(value, ast.JoinedStr)
                and any(
                    isinstance(part, ast.FormattedValue)
                    and isinstance(part.value, ast.Name)
                    and part.value.id == "_ORCH_NS"
                    for part in value.values
                )
            ):
                literal = "".join(
                    str(part.value) if isinstance(part, ast.Constant) else ""
                    for part in value.values
                )
                keys.add(f"_orchestrator{literal}")
    return keys


def test_every_orchestrator_constant_has_a_registry_row() -> None:
    constants = _ast_orchestrator_keys()
    registered = {spec.key for spec in ORCH_CHANNELS if spec.key.startswith("_orchestrator")}
    missing = constants - registered
    unknown = registered - constants
    assert not missing, f"orchestrator constants without ORCH_CHANNELS row: {sorted(missing)}"
    assert not unknown, f"registry rows without orchestrator constant: {sorted(unknown)}"


def test_every_schema_declared_orchestrator_key_has_a_registry_row() -> None:
    schema_keys = {
        field for field in StudioGraphState.__annotations__ if field.startswith("_orchestrator")
    }
    registered = {spec.key for spec in ORCH_CHANNELS}
    missing = schema_keys - registered
    assert not missing, f"GraphState orchestrator keys without registry row: {sorted(missing)}"


def test_registry_rows_are_unique() -> None:
    keys = [spec.key for spec in ORCH_CHANNELS]
    duplicates = {key for key in keys if keys.count(key) > 1}
    assert not duplicates, f"duplicate ORCH_CHANNELS rows: {sorted(duplicates)}"


# --- 2. Propagation parity ---------------------------------------------------


def _sample_value(key: str) -> Any:
    if key.endswith("candidate_refs"):
        return {"script": "artifact:script:v2"}
    if key.endswith("execution_brief"):
        return {"runtime_seconds": 300, "movements": []}
    if key.startswith("_orchestrator"):
        return [{"phase": "intake"}] if "cycles" in key or "revisions" in key else {}
    if key.startswith("_"):
        return [{"decision": "route"}]
    return [{"issue_id": "i1"}]


def _assert_not_copied(dest: dict[str, Any], key: str) -> None:
    assert key not in dest, f"'{key}' must not be auto-propagated"


@pytest.mark.parametrize("spec", ORCH_CHANNELS, ids=lambda spec: spec.key)
def test_full_and_explicit_policies(spec: OrchChannelSpec) -> None:
    if spec.propagation == "append_only":
        pytest.skip("append-only policies are exercised by the slicing tests")
    value = _sample_value(spec.key)
    dest: dict[str, Any] = {}
    _propagate_side_effects({spec.key: value}, dest)

    if spec.propagation == "full":
        assert dest[spec.key] == value
    elif spec.propagation == "full_truthy":
        if value:
            assert dest[spec.key] == value
        else:
            _assert_not_copied(dest, spec.key)
    else:
        _assert_not_copied(dest, spec.key)


@pytest.mark.parametrize(
    "spec",
    [row for row in ORCH_CHANNELS if row.propagation == "full_truthy"],
    ids=lambda spec: spec.key,
)
def test_full_truthy_skips_falsy_values(spec: OrchChannelSpec) -> None:
    dest: dict[str, Any] = {}
    _propagate_side_effects({spec.key: {}}, dest)
    _assert_not_copied(dest, spec.key)


def test_repair_feedback_survives_when_cleared_to_empty() -> None:
    """``_capture_run_outcome`` clears consumed feedback; the '' must cross."""
    dest: dict[str, Any] = {}
    _propagate_side_effects({"_repair_feedback": ""}, dest)
    assert dest["_repair_feedback"] == ""


@pytest.mark.parametrize(
    "spec",
    [row for row in ORCH_CHANNELS if row.propagation == "append_only"],
    ids=lambda spec: spec.key,
)
def test_append_only_slices_against_original(spec: OrchChannelSpec) -> None:
    original = {spec.key: ["old"]}
    source = {spec.key: ["old", "new"]}
    dest: dict[str, Any] = {}
    _propagate_side_effects(source, dest, original)
    assert dest[spec.key] == ["new"]


@pytest.mark.parametrize(
    "spec",
    [row for row in ORCH_CHANNELS if row.propagation == "append_only"],
    ids=lambda spec: spec.key,
)
def test_append_only_carries_all_without_original(spec: OrchChannelSpec) -> None:
    dest: dict[str, Any] = {}
    _propagate_side_effects({spec.key: ["a"]}, {}, None)
    _propagate_side_effects({spec.key: ["a"]}, dest, None)
    assert dest[spec.key] == ["a"]


def test_execution_brief_and_candidate_refs_land_together() -> None:
    """Both high-value channels survive a single boundary crossing."""
    source = {
        "_orchestrator__execution_brief": {"runtime_seconds": 300},
        "_orchestrator__candidate_refs": {"script": "artifact:script:v2"},
    }
    dest: dict[str, Any] = {}
    _propagate_side_effects(source, dest)
    assert dest["_orchestrator__execution_brief"] == {"runtime_seconds": 300}
    assert dest["_orchestrator__candidate_refs"] == {"script": "artifact:script:v2"}


def test_absent_brief_stays_absent_while_refs_land() -> None:
    """Predicate interaction: copy-on-present must not invent an empty brief.

    'Absent from source' differs from 'present but empty' — the former must
    stay absent while truthy candidate refs land beside it.
    """
    source = {"_orchestrator__candidate_refs": {"scope_contract": "artifact:sc:v1"}}
    dest: dict[str, Any] = {}
    _propagate_side_effects(source, dest)
    _assert_not_copied(dest, "_orchestrator__execution_brief")
    assert dest["_orchestrator__candidate_refs"] == {"scope_contract": "artifact:sc:v1"}


def test_unregistered_keys_are_never_copied() -> None:
    """No hidden local key lists: anything unregistered stays behind."""
    dest: dict[str, Any] = {}
    _propagate_side_effects({"_services": object(), "unknown_channel": [1]}, dest)
    assert "_services" not in dest
    assert "unknown_channel" not in dest


# --- 3. Writer sweep ----------------------------------------------------------

# Every direct subscript write to a boundary key under graph/nodes/** must be
# accounted for here. Keyed by (file name, state key) — never line numbers.
# Dispositions:
#   explicit-writer — the write targets the returned updates/result container
#                     (or is module-owned bookkeeping in _agent_handoff).
#   propagated      — the write lands on a working copy whose node calls
#                     _propagate_side_effects, so the registry carries it.
#   known-dropped:<reason> — deliberate deferral, cited to the debt register.
WRITER_DISPOSITIONS: dict[tuple[str, str], str] = {
    ("_agent_handoff.py", "_repair_feedback"): "explicit-writer",
    ("_agent_handoff.py", "_routing_decisions"): "explicit-writer",
    ("_generation_batch_planning.py", "generation_requests"): "explicit-writer",
    ("_repair_loop.py", "_repair_feedback"): "propagated",
    ("_repair_loop.py", "_orchestrator__pending_revisions"): "explicit-writer",
    ("_repair_loop.py", "issues"): "explicit-writer",
    ("_shared.py", "generation_requests"): "explicit-writer",
    ("_shared.py", "issues"): "explicit-writer",
    ("approval.py", "_repair_feedback"): (
        "known-dropped:headless auto-revise feedback dies at the "
        "request_revision_node boundary; triage with D13/P1 wire-or-delete"
    ),
    ("generation.py", "artifact_refs"): "explicit-writer",
    ("generation.py", "generation_requests"): "explicit-writer",
    ("generation.py", "issues"): "explicit-writer",
    ("prep.py", "artifact_refs"): "explicit-writer",
    ("prep.py", "issues"): "explicit-writer",
    ("qc.py", "artifact_refs"): "explicit-writer",
    ("qc.py", "issues"): "explicit-writer",
    ("visual.py", "artifact_refs"): "explicit-writer",
    ("visual.py", "issues"): "explicit-writer",
    ("visual.py", "generation_requests"): (
        "known-dropped:gen_planning request write dies at the boundary; deferred to D13/P1#12"
    ),
    ("wrapup.py", "artifact_refs"): "explicit-writer",
}


def _sweep_boundary_writes() -> dict[tuple[str, str], list[int]]:
    """Map (file, key) → write sites for direct subscript assignments."""
    hits: dict[tuple[str, str], list[int]] = {}
    scope = _sweep_scope()
    for path in sorted(_NODES_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text())
        for stmt in ast.walk(tree):
            if isinstance(stmt, ast.Call):
                # ``state.update({...})`` merges bypass subscript assignment;
                # scan their dict literals for scope keys too.
                func = stmt.func
                if (
                    isinstance(func, ast.Attribute)
                    and func.attr == "update"
                    and stmt.args
                    and isinstance(stmt.args[0], ast.Dict)
                ):
                    for key in stmt.args[0].keys:
                        if (
                            isinstance(key, ast.Constant)
                            and isinstance(key.value, str)
                            and key.value in scope
                        ):
                            entry = (path.name, key.value)
                            hits.setdefault(entry, []).append(stmt.lineno)
                continue
            targets: list[ast.expr]
            if isinstance(stmt, ast.Assign):
                targets = stmt.targets
            elif isinstance(stmt, (ast.AnnAssign, ast.AugAssign)):
                targets = [stmt.target]
            else:
                continue
            for target in targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.slice, ast.Constant)
                    and isinstance(target.slice.value, str)
                    and target.slice.value in scope
                ):
                    entry = (path.name, target.slice.value)
                    hits.setdefault(entry, []).append(stmt.lineno)
    return hits


def _sweep_scope() -> frozenset[str]:
    return frozenset(spec.key for spec in ORCH_CHANNELS) | _EXTRA_SWEEP_KEYS


def test_writer_sweep_matches_recorded_dispositions() -> None:
    found = set(_sweep_boundary_writes())
    recorded = set(WRITER_DISPOSITIONS)
    unaccounted = found - recorded
    stale = recorded - found
    assert not unaccounted, (
        "boundary-key writes without a disposition (extend WRITER_DISPOSITIONS "
        f"or fix the drop): {sorted(unaccounted)}"
    )
    assert not stale, f"dispositions whose write site disappeared: {sorted(stale)}"


# --- 4. DF-F2 regression -------------------------------------------------------


def test_execution_brief_survives_propagation() -> None:
    dest: dict[str, Any] = {}
    brief = {"runtime_seconds": 240, "movements": [{"name": "act-1"}]}
    _propagate_side_effects({"_orchestrator__execution_brief": brief}, dest)
    assert dest["_orchestrator__execution_brief"] == brief


class TestShotBibleBriefReachesUpdates:
    """End-to-end: the brief written mid-node must land in ``shot_bible_node``'s update."""

    @pytest.fixture(autouse=True)
    def _services_env(self, tmp_path: Path) -> Any:
        from film_pipeline.graph import nodes
        from film_pipeline.graph.services import SERVICES_KEY, GraphServices

        svc = GraphServices.for_mock_runtime(
            artifacts_root=str(tmp_path / "artifacts"), mock_responses=default_mock_responses()
        )
        self._token = nodes._SERVICES_CTX.set(svc)
        self._nodes = nodes
        self._services_key = SERVICES_KEY
        self._svc = svc
        yield
        nodes._SERVICES_CTX.reset(self._token)

    def _state(self) -> dict[str, Any]:
        return {
            "project_id": "dff2-regression",
            "idea": "A lighthouse keeper who mails letters to the future.",
            "current_phase": "shot_bible",
            "story_bible_ref": "artifact:story_bible:v1",
            "script_ref": "artifact:script:v1",
            "shot_matrix_ref": "artifact:shot_matrix:v1",
            "target_runtime_seconds": 300,
            self._services_key: self._svc,
            "resolved_config": {"studio": {"require_human_approval": False}},
            "artifact_refs": [],
        }

    def test_update_carries_execution_brief(self) -> None:
        from film_pipeline.graph.nodes.visual import shot_bible_node

        updates = shot_bible_node(self._state())
        assert "_orchestrator__execution_brief" in updates, (
            "DF-F2 regression: brief written by _ensure_execution_brief died at the node boundary"
        )
        assert updates.get("execution_brief_ref")

    def test_replay_is_idempotent_and_does_not_reextract(self) -> None:
        """Checkpoint replay re-carries an identical brief; extraction runs once."""
        from film_pipeline.graph.nodes.visual import shot_bible_node

        state = self._state()
        first = shot_bible_node(state)
        merged = {**state, **first}
        second = shot_bible_node(merged)

        assert second["_orchestrator__execution_brief"] == first["_orchestrator__execution_brief"]
        # The extractor saved exactly one artifact version across both runs.
        store = self._svc.artifact_store
        assert store.next_version("dff2-regression", "shot_bible", "execution_brief") == 2
