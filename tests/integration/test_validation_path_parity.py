"""Parity between the MCP validation action and the runtime validation operation.

Source of the invariants: ``docs/modularity-improvements/09-functional-boundaries.md``
finding F1.

"Validate the current project" is owned by one operation:
``orchestration.execution.run_validation``, reached through
``StudioRuntime.run_validation``. It runs the QC validator chain for six phase
groups, records findings in project state, saves each report as an artifact, and
records the refs on the declared ``validation_report_refs`` channel. The MCP
action in ``mcp.tools.validation`` drives that operation and presents its typed
outcome.

Before the consolidation the MCP action was a second implementation: it selected
only ``script`` and ``visual_dev``, recorded no findings at all — so a blocking
validator result did not stop phase advancement, which is the product contract
validators exist to enforce — and wrote its refs to an undeclared state key.

These tests arrived first, as ``xfail(strict=True)`` markers pinning the
divergences, and were unmarked by the slice that fixed them; ``xfail_strict`` is
configured project-wide, so a marker cannot outlive its defect.

The project is built directly rather than by running the phase nodes: the point
is what the two actions do to one identical state, and a hand-built
``gen_planning`` project with a deliberately unready prompt registry makes the
phase-selection, the finding-recording and the evidence divergence observable in
one fixture. The registry entry is missing RCTCO fields, which
``PromptReadinessValidator`` rates ``BLOCKED`` with blocking issues.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.roster import MVP_AGENTS
from film_pipeline.agents.runner import PromptRunner
from film_pipeline.mcp.tools import run_validation
from film_pipeline.orchestration.services import GraphServices
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.storage.store import ArtifactStore
from film_pipeline.studio.runtime import StudioRuntime

CallTool = Callable[..., Any]

PROJECT_ID = "val-parity"
PHASE = "gen_planning"


class PromptRegistry(BaseModel):
    """The prompt-package shape ``PromptReadinessValidator`` reads."""

    entries: list[dict[str, Any]]


@pytest.fixture
def rt(tmp_path: Path) -> Generator[StudioRuntime, None, None]:
    """A runtime whose active project is at ``gen_planning`` with an unready registry."""
    registry = AgentRegistry()
    registry.register_many(MVP_AGENTS)
    store = ArtifactStore(root=tmp_path / "artifacts")
    runtime = StudioRuntime(runtime_root=tmp_path / "runtime")
    runtime.services = GraphServices(
        prompt_runner=PromptRunner(),
        artifact_store=store,
        agent_registry=registry,
    )
    runtime.create_project(PROJECT_ID, "Validation Parity")
    runtime.set_active(PROJECT_ID)

    state = runtime.get_active()
    assert state is not None
    state["current_phase"] = PHASE
    # Missing RCTCO fields and no artifact refs: PromptReadinessValidator scores
    # this BLOCKED with blocking findings, so "did the validators run" and "were
    # the findings recorded" are both observable.
    state["artifact_refs"] = [_save_unready_prompt_registry(store)]
    state["issues"] = []
    state["_validation_reports"] = []
    state.pop("validation_refs", None)
    runtime.projects[PROJECT_ID] = state
    yield runtime


def _save_unready_prompt_registry(store: ArtifactStore) -> str:
    """Persist one prompt entry that is missing its RCTCO role and task fields."""
    return store.save(
        PromptRegistry(entries=[{"prompt_id": "P1", "rctco": {"r": "director"}}]),
        ArtifactMetadata(
            artifact_id="prompt_registry",
            artifact_type=ArtifactType.PROMPT_REGISTRY,
            project_id=PROJECT_ID,
            phase=FilmPhase.GEN_PLANNING,
            version=1,
            status=ArtifactStatus.APPROVED,
            created_by="test",
            created_at=datetime.now(UTC),
        ),
    ).to_string()


def _state(rt: StudioRuntime) -> dict[str, Any]:
    state = rt.get_project(PROJECT_ID)
    assert state is not None
    return state


def _validator_issues(rt: StudioRuntime) -> list[dict[str, Any]]:
    return [
        issue
        for issue in _state(rt).get("issues", [])
        if isinstance(issue, dict) and issue.get("validator_id")
    ]


def _assert_validators_ran(rt: StudioRuntime) -> None:
    """The single statement of "this action validated the current phase"."""
    assert _state(rt)["_validation_reports"], "the phase's validators must run"
    blocking = [issue for issue in _validator_issues(rt) if issue["severity"] == "blocking"]
    assert blocking, "a blocking finding must be recorded so advancement stops"


def _assert_evidence_is_durable(rt: StudioRuntime) -> None:
    """Every report this action produced is saved and its ref recorded.

    The refs go on the *declared* ``validation_report_refs`` channel — the one
    registered in ``ORCH_CHANNELS`` and wired to a reducer — not the undeclared
    ``validation_refs`` project-state key the MCP tool used to write (audit
    F-VR-14, which found the declared channel had no writer at all).
    """
    refs = _state(rt).get("validation_report_refs", [])
    assert refs, "a validation action must record the reports it produced"
    assert len(refs) == len(_state(rt)["_validation_reports"])
    services = rt.services
    assert services is not None
    for ref in refs:
        parsed = str(ref).split(":")
        assert parsed[0] == "artifact"
        services.artifact_store.load(
            PROJECT_ID, FilmPhase(parsed[1]), parsed[2], int(parsed[3].removeprefix("v"))
        )


# ── the runtime operation: what the two paths must agree on ──────────────────


def test_runtime_validation_covers_gen_planning(rt: StudioRuntime) -> None:
    rt.run_validation(PROJECT_ID)

    _assert_validators_ran(rt)


def test_runtime_validation_records_report_artifact_refs(rt: StudioRuntime) -> None:
    rt.run_validation(PROJECT_ID)

    _assert_evidence_is_durable(rt)


# ── the MCP action must produce the same persisted result ────────────────────


def test_mcp_validation_covers_the_same_phases(rt: StudioRuntime, call_tool: CallTool) -> None:
    result = call_tool(run_validation, {}, runtime=rt)

    assert result["ok"] is True
    assert result.get("phase") == PHASE
    _assert_validators_ran(rt)


def test_mcp_validation_records_evidence_the_same_way(
    rt: StudioRuntime, call_tool: CallTool
) -> None:
    call_tool(run_validation, {}, runtime=rt)

    _assert_evidence_is_durable(rt)
