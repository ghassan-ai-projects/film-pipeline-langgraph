"""Parity between the MCP clip-generation lifecycle and ``GenerationExecutor``.

Source of the invariants: ``docs/modularity-improvements/09-functional-boundaries.md``
finding F2.

The clip-generation lifecycle — submit, poll, deliver, advance the durable
ledger — is owned by ``GenerationExecutor``. The MCP operator tools in
``mcp.tools.generation.dispatch`` drive that owner and project its typed outcome
instead of reimplementing it. Both write the *same* ledger artifact, so a
divergence between them is a durable representation bug rather than a style
problem: whichever path the operator happens to use would otherwise decide
whether a completed row carries delivered output.

Every test states one invariant on the persisted ledger row and the project's
asset tree, then asserts it through a named entry path. The single statement of
"a completed row is a real delivered output" lives in ``_assert_delivered`` and
is applied to both paths, so the two can only agree or fail.

The tests that pinned the divergence arrived first, as ``xfail(strict=True)``
markers, and were unmarked by the slice that fixed them; ``xfail_strict`` is
configured project-wide so a marker cannot outlive its defect.
"""

from __future__ import annotations

from collections.abc import Callable, Generator
from pathlib import Path
from typing import Any, cast
from unittest import mock

import pytest

from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.roster import MVP_AGENTS
from film_pipeline.agents.runner import PromptRunner
from film_pipeline.generation.executor import GenerationExecutor
from film_pipeline.generation.ledger import (
    TERMINAL_GENERATION_STATUSES,
    GenerationLedgerManager,
)
from film_pipeline.mcp.tools import (
    cancel_generation_request,
    resume_generation_polling,
    start_generation_batch,
)
from film_pipeline.orchestration.services import GraphServices
from film_pipeline.schemas.base import GenerationStatus
from film_pipeline.schemas.generation import GenerationLedgerRow
from film_pipeline.storage.manifest import read_manifest
from film_pipeline.storage.store import ArtifactStore
from film_pipeline.studio._provider_factory import build_provider_adapter
from film_pipeline.studio.runtime import StudioRuntime

CallTool = Callable[..., Any]

PROJECT_ID = "gen-parity"
PROVIDER = "mock-video-provider"
MODEL = "mock-fast"


@pytest.fixture
def rt(tmp_path: Path) -> Generator[StudioRuntime, None, None]:
    """A runtime with one registered mock video provider and one active project."""
    registry = AgentRegistry()
    registry.register_many(MVP_AGENTS)
    services = GraphServices(
        prompt_runner=PromptRunner(),
        artifact_store=ArtifactStore(root=tmp_path / "artifacts"),
        agent_registry=registry,
    )
    runtime = StudioRuntime(runtime_root=tmp_path / "runtime")
    runtime.services = services
    runtime.create_project(PROJECT_ID, "Generation Parity")
    runtime.set_active(PROJECT_ID)
    runtime.register_provider(
        PROVIDER,
        build_provider_adapter(PROVIDER, provider_type="video", models=[MODEL]),
    )
    runtime.set_provider_health(PROVIDER, "healthy")
    yield runtime


def _store(rt: StudioRuntime) -> ArtifactStore:
    assert rt.services is not None
    return rt.services.artifact_store


def _executor(rt: StudioRuntime) -> GenerationExecutor:
    return GenerationExecutor(_store(rt), rt.provider_adapters)


def _row(rt: StudioRuntime, generation_id: str) -> GenerationLedgerRow:
    row = GenerationLedgerManager(_store(rt)).get_row(PROJECT_ID, generation_id)
    assert row is not None, f"no ledger row for {generation_id}"
    return row


def _plan_and_approve(rt: StudioRuntime, shot_ids: list[str]) -> str:
    """Plan through the owner, approve spend, and return the first generation id."""
    executor = _executor(rt)
    executor.plan(PROJECT_ID, provider=PROVIDER, model=MODEL, shot_ids=shot_ids)
    executor.approve_spend(PROJECT_ID)
    rows = GenerationLedgerManager(_store(rt)).list_rows(PROJECT_ID)
    assert len(rows) == len(shot_ids)
    assert all(row.status is GenerationStatus.SUBMITTED for row in rows)
    return rows[0].generation_id


def _assert_submitted(rt: StudioRuntime, generation_id: str) -> None:
    """A submitted row carries a provider job and the evidence of its submission."""
    row = _row(rt, generation_id)
    assert row.status is GenerationStatus.RUNNING
    assert row.provider_job_id
    assert row.next_action == "poll"
    assert row.submitted_at is not None, "submission time must survive on the row"


def _assert_delivered(rt: StudioRuntime, generation_id: str) -> None:
    """A completed row is a real output: refs, a file on disk, one manifest take."""
    row = _row(rt, generation_id)
    assert row.status is GenerationStatus.COMPLETED
    assert row.next_action == "validate"
    assert row.output_refs, "a COMPLETED row must record its delivered output"
    assert Path(row.output_refs[0]).is_file(), row.output_refs

    manifest = read_manifest(PROJECT_ID, root=_store(rt).root)
    assert manifest is not None, "delivery must record the take in the asset manifest"
    shot_entries = [entry for entry in manifest.entries if entry.shot_id == row.shot_id]
    assert {entry.take for entry in shot_entries} == {1}, shot_entries
    assert all(entry.sha256 for entry in shot_entries), shot_entries


def _break_polling(rt: StudioRuntime) -> Any:
    """Make the registered mock provider fail every poll until the patch exits."""
    adapter = rt.get_provider(PROVIDER)
    assert adapter is not None
    return mock.patch.object(adapter, "poll", side_effect=RuntimeError("poll boom"))


def test_executor_start_records_submission_evidence(rt: StudioRuntime) -> None:
    generation_id = _plan_and_approve(rt, ["S001"])

    assert _executor(rt).start(PROJECT_ID).running == 1

    _assert_submitted(rt, generation_id)


def test_executor_poll_once_delivers_completed_job(rt: StudioRuntime) -> None:
    generation_id = _plan_and_approve(rt, ["S001"])
    executor = _executor(rt)
    executor.start(PROJECT_ID)

    assert executor.poll_once(PROJECT_ID).completed == 1

    _assert_delivered(rt, generation_id)


def test_mcp_start_batch_records_submission_evidence(
    rt: StudioRuntime, call_tool: CallTool
) -> None:
    """The one submit invariant MCP already satisfies; the consolidation keeps it.

    The submit fields MCP wrote on its own agreed with
    ``GenerationExecutor._dispatch_row``; this is the parity the consolidation
    had to preserve, so it was never marked as a divergence.
    """
    generation_id = _plan_and_approve(rt, ["S001"])

    call_tool(start_generation_batch, {}, runtime=rt)

    _assert_submitted(rt, generation_id)


def test_mcp_start_batch_does_not_resubmit_a_row_that_has_a_job(
    rt: StudioRuntime, call_tool: CallTool
) -> None:
    """Duplicate prevention: a row already holding a job is reported, not resubmitted."""
    generation_id = _plan_and_approve(rt, ["S001"])
    manager = GenerationLedgerManager(_store(rt))
    manager.update_row(PROJECT_ID, generation_id, provider_job_id="job-already-there")

    result = call_tool(start_generation_batch, {}, runtime=rt)

    assert result["submitted"] == 1
    successes = cast(list[dict[str, str]], result["successes"])
    assert successes[0]["note"] == "already-submitted"
    assert _row(rt, generation_id).provider_job_id == "job-already-there"


def test_cancel_refused_by_the_provider_leaves_the_row_running(
    rt: StudioRuntime, call_tool: CallTool
) -> None:
    """A provider that will not cancel must not be reported as a cancel."""
    generation_id = _plan_and_approve(rt, ["S001"])
    call_tool(start_generation_batch, {}, runtime=rt)
    adapter = rt.get_provider(PROVIDER)
    assert adapter is not None

    with mock.patch.object(adapter, "cancel", return_value=False):
        result = call_tool(cancel_generation_request, {"generation_id": generation_id}, runtime=rt)

    assert result["ok"] is True
    assert result["cancelled"] is False
    assert result["provider"] is True
    assert _row(rt, generation_id).status is GenerationStatus.RUNNING


def test_mcp_resume_polling_delivers_completed_job(rt: StudioRuntime, call_tool: CallTool) -> None:
    generation_id = _plan_and_approve(rt, ["S001"])
    call_tool(start_generation_batch, {}, runtime=rt)

    result = call_tool(resume_generation_polling, {"generation_id": generation_id}, runtime=rt)

    assert result["ok"] is True
    _assert_delivered(rt, generation_id)


def test_mcp_resume_polling_does_not_deliver_the_same_job_twice(
    rt: StudioRuntime, call_tool: CallTool
) -> None:
    generation_id = _plan_and_approve(rt, ["S001"])
    call_tool(start_generation_batch, {}, runtime=rt)
    call_tool(resume_generation_polling, {"generation_id": generation_id}, runtime=rt)
    _assert_delivered(rt, generation_id)

    call_tool(resume_generation_polling, {"generation_id": generation_id}, runtime=rt)

    _assert_delivered(rt, generation_id)


def test_executor_poll_failure_leaves_the_row_recoverable(rt: StudioRuntime) -> None:
    generation_id = _plan_and_approve(rt, ["S001"])
    executor = _executor(rt)
    executor.start(PROJECT_ID)

    with _break_polling(rt):
        assert executor.poll_once(PROJECT_ID).failed == 1

    row = _row(rt, generation_id)
    assert row.status is GenerationStatus.BLOCKED_PROVIDER
    assert row.status not in TERMINAL_GENERATION_STATUSES
    assert row.error_code == "poll_failed"
    assert "poll boom" in str(row.blocking_reason)

    assert executor.poll_once(PROJECT_ID).completed == 1
    _assert_delivered(rt, generation_id)


def test_mcp_poll_failure_leaves_the_row_recoverable(
    rt: StudioRuntime, call_tool: CallTool
) -> None:
    generation_id = _plan_and_approve(rt, ["S001"])
    call_tool(start_generation_batch, {}, runtime=rt)

    with _break_polling(rt):
        result = call_tool(resume_generation_polling, {"generation_id": generation_id}, runtime=rt)

    assert result["ok"] is False
    assert "poll boom" in str(result["error"])
    row = _row(rt, generation_id)
    assert row.status is GenerationStatus.BLOCKED_PROVIDER
    assert row.status not in TERMINAL_GENERATION_STATUSES
    assert row.error_code == "poll_failed"

    result = call_tool(resume_generation_polling, {"generation_id": generation_id}, runtime=rt)
    assert result["ok"] is True
    _assert_delivered(rt, generation_id)


def test_unregistered_provider_leaves_the_row_pollable(
    rt: StudioRuntime, call_tool: CallTool
) -> None:
    """A missing adapter is an operator precondition, not a terminal row state.

    Regression guard for the consolidation: routing this through `_poll_row` wrote
    `FAILED`, which is terminal, so a row whose `provider` string merely named
    something not yet registered could never be polled again once it was.
    Registering the provider and retrying is the remedy, and it only works while
    the row is still pollable.
    """
    generation_id = _plan_and_approve(rt, ["S001"])
    call_tool(start_generation_batch, {}, runtime=rt)
    GenerationLedgerManager(_store(rt)).update_row(
        PROJECT_ID, generation_id, provider="missing-provider"
    )
    before = _row(rt, generation_id)

    result = call_tool(resume_generation_polling, {"generation_id": generation_id}, runtime=rt)

    assert result["ok"] is False
    assert "not registered" in str(result["error"])
    after = _row(rt, generation_id)
    assert after.status is before.status, "a missing adapter must not change the row"
    assert after.status not in TERMINAL_GENERATION_STATUSES
    assert after.error_code is None
    assert after.next_action == "poll"

    _register_missing_provider(rt)
    call_tool(resume_generation_polling, {"generation_id": generation_id}, runtime=rt)
    _assert_delivered(rt, generation_id)


def _register_missing_provider(rt: StudioRuntime) -> None:
    """Point the row's provider name at a real adapter."""
    adapter = rt.get_provider(PROVIDER)
    assert adapter is not None
    rt.register_provider("missing-provider", adapter)
