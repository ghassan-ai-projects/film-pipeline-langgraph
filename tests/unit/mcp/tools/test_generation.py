"""Unit tests for film_pipeline.mcp.tools.generation (start/promote paths).

The bulk of plan/approve/status/cancel/resume coverage already lives in
``tests/integration/test_generation_mcp.py``; this file focuses on
``start_generation_batch`` and ``promote_test_to_production``, which were
previously untested in isolation.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any, cast
from unittest import mock

import pytest

from film_pipeline.agents.mvp import MVP_AGENTS
from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.agents.runner import PromptRunner
from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.graph.services import GraphServices
from film_pipeline.mcp.tools import (
    approve_generation_spend,
    cancel_generation_request,
    get_generation_status,
    list_active_generations,
    plan_generation_batch,
    preview_generation_prompts,
    promote_test_to_production,
    resume_generation_polling,
    start_generation_batch,
)
from film_pipeline.providers.factory import build_provider_adapter
from film_pipeline.schemas._base import SchemaBase


@pytest.fixture
def rt(tmp_path: Path) -> Generator[StudioRuntime, None, None]:
    runner = PromptRunner()
    registry = AgentRegistry()
    registry.register_many(MVP_AGENTS)
    services = GraphServices(
        prompt_runner=runner,
        artifact_store=ArtifactStore(root=tmp_path / "artifacts"),
        agent_registry=registry,
    )
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.services = services
    rt.create_project("gen-start-test", "Gen Start Test")
    rt.set_active("gen-start-test")
    rt.register_provider(
        "mock-video-provider",
        build_provider_adapter("mock-video-provider", provider_type="video", models=["mock-fast"]),
    )
    rt.set_provider_health("mock-video-provider", "healthy")
    with mock.patch("film_pipeline.mcp.tools.get_runtime", return_value=rt):
        yield rt


async def _plan_and_approve(shot_ids: list[str]) -> dict[str, object]:
    await plan_generation_batch(
        {"shot_ids": shot_ids, "provider": "mock-video-provider", "model": "mock-fast"}
    )
    return await approve_generation_spend({"confirmed": True})


def test_start_generation_batch_no_submitted_rows(rt: StudioRuntime) -> None:
    import asyncio

    result = asyncio.run(start_generation_batch({}))
    assert result["ok"] is True
    assert result["submitted"] == 0
    assert "Approve spend first" in cast(str, result["message"])


def test_start_generation_batch_unknown_provider(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(
        plan_generation_batch({"shot_ids": ["S001"], "provider": "no-such-provider", "model": "m"})
    )
    asyncio.run(approve_generation_spend({"confirmed": True}))

    result = asyncio.run(start_generation_batch({}))
    assert result["ok"] is True
    assert result["failed"] == 1
    assert result["submitted"] == 0
    failures = cast(list[dict[str, Any]], result["failures"])
    assert "not registered" in failures[0]["error"]


def test_start_generation_batch_success(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))

    result = asyncio.run(start_generation_batch({}))
    assert result["ok"] is True
    assert result["submitted"] == 1
    assert result["failed"] == 0
    successes = cast(list[dict[str, Any]], result["successes"])
    assert successes[0]["provider_job_id"]


def test_start_generation_batch_skips_already_submitted(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))
    first = asyncio.run(start_generation_batch({}))
    assert first["submitted"] == 1

    # Re-approving has nothing new to submit since rows already moved past
    # SUBMITTED, but calling start again should be a no-op (no SUBMITTED rows).
    second = asyncio.run(start_generation_batch({}))
    assert second["ok"] is True
    assert second["submitted"] == 0


def test_promote_test_to_production_no_active_project() -> None:
    import asyncio

    from film_pipeline.app.runtime import get_runtime as gr

    rt2 = gr()
    rt2.active_project_id = ""
    result = asyncio.run(promote_test_to_production({"confirmed": True}))
    assert result["ok"] is False


def test_promote_test_to_production_no_eligible_rows(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))
    # Rows are SUBMITTED, not yet COMPLETED, so nothing is eligible to promote.
    result = asyncio.run(promote_test_to_production({"confirmed": True}))
    assert result["ok"] is True
    assert result["promoted"] == 0


def test_plan_generation_batch_no_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from film_pipeline.app.runtime import get_runtime as gr

    rt2 = gr()
    rt2.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt2)
    result = asyncio.run(plan_generation_batch({}))
    assert result["ok"] is False


def test_plan_generation_batch_from_shot_bible(rt: StudioRuntime) -> None:
    import asyncio
    from datetime import UTC, datetime

    from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata

    assert rt.services is not None
    store = rt.services.artifact_store
    meta = ArtifactMetadata(
        artifact_id="shot_bible",
        artifact_type=ArtifactType.SHOT_BIBLE,
        project_id="gen-start-test",
        phase=FilmPhase.SHOT_BIBLE,
        version=1,
        status=ArtifactStatus.CANDIDATE,
        parents=[],
        created_by="test",
        created_at=datetime.now(UTC),
    )

    class _ShotBible(SchemaBase):
        shots: list[dict[str, str]]

    store.save(_ShotBible(shots=[{"shot_id": "S010"}, {"shot_id": "S011"}]), meta)

    # Passing a non-list shot_ids forces the tool to read from the shot bible.
    result = asyncio.run(
        plan_generation_batch(
            {"shot_ids": "from-bible", "provider": "mock-video-provider", "model": "mock-fast"}
        )
    )
    assert result["ok"] is True
    assert result["planned"] == 2


def test_plan_generation_batch_invalid_shot_ids_type(rt: StudioRuntime) -> None:
    import asyncio

    result = asyncio.run(
        plan_generation_batch(
            {"shot_ids": "not-a-list", "provider": "mock-video-provider", "model": "mock-fast"}
        )
    )
    assert result["ok"] is False
    assert "No shot IDs to plan" in cast(str, result["error"])


def test_approve_generation_spend_no_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from film_pipeline.app.runtime import get_runtime as gr

    rt2 = gr()
    rt2.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt2)
    result = asyncio.run(approve_generation_spend({"confirmed": True}))
    assert result["ok"] is False


def test_approve_generation_spend_value_error(
    rt: StudioRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    from film_pipeline.generation.ledger import GenerationLedgerManager

    asyncio.run(
        plan_generation_batch(
            {"shot_ids": ["S001"], "provider": "mock-video-provider", "model": "mock-fast"}
        )
    )
    monkeypatch.setattr(
        GenerationLedgerManager,
        "approve_spend",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("Total estimated cost $10.00 exceeds budget $5.00.")
        ),
    )
    result = asyncio.run(approve_generation_spend({"max_cost_usd": 5.0, "confirmed": True}))
    assert result["ok"] is False
    assert "exceeds budget" in cast(str, result["error"])


def test_get_generation_status_missing_id() -> None:
    import asyncio

    result = asyncio.run(get_generation_status({}))
    assert result["ok"] is False
    assert "generation_id is required" in cast(str, result["error"])


def test_get_generation_status_no_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from film_pipeline.app.runtime import get_runtime as gr

    rt2 = gr()
    rt2.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt2)
    result = asyncio.run(get_generation_status({"generation_id": "g1"}))
    assert result["ok"] is False


def test_get_generation_status_not_found(rt: StudioRuntime) -> None:
    import asyncio

    result = asyncio.run(get_generation_status({"generation_id": "no-such-generation"}))
    assert result["ok"] is False
    assert "not found" in cast(str, result["error"])


def test_get_generation_status_success(rt: StudioRuntime) -> None:
    import asyncio

    planned = asyncio.run(
        plan_generation_batch(
            {"shot_ids": ["S001"], "provider": "mock-video-provider", "model": "mock-fast"}
        )
    )
    gen_id = cast(list[dict[str, Any]], planned["rows"])[0]["generation_id"]
    result = asyncio.run(get_generation_status({"generation_id": gen_id}))
    assert result["ok"] is True
    assert result["generation_id"] == gen_id


def test_list_active_generations_no_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from film_pipeline.app.runtime import get_runtime as gr

    rt2 = gr()
    rt2.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt2)
    result = asyncio.run(list_active_generations({}))
    assert result["ok"] is False


def test_list_active_generations_success(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(
        plan_generation_batch(
            {"shot_ids": ["S001"], "provider": "mock-video-provider", "model": "mock-fast"}
        )
    )
    result = asyncio.run(list_active_generations({}))
    assert result["ok"] is True
    assert result["count"] == 1


def test_start_generation_batch_skips_already_submitted_with_job_id(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))
    # Manually set provider_job_id on the SUBMITTED row to exercise the skip branch.
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationStatus

    assert rt.services is not None
    mgr = GenerationLedgerManager(rt.services.artifact_store)
    for row in mgr.list_rows("gen-start-test", status=GenerationStatus.SUBMITTED):
        mgr.update_row("gen-start-test", row.generation_id, provider_job_id="existing-job-id")

    result = asyncio.run(start_generation_batch({}))
    assert result["ok"] is True
    assert result["submitted"] == 1
    successes = cast(list[dict[str, Any]], result["successes"])
    assert successes[0]["provider_job_id"] == "existing-job-id"
    assert successes[0]["note"] == "already-submitted"


def test_start_generation_batch_submit_exception(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))
    adapter = rt.get_provider("mock-video-provider")
    assert adapter is not None
    original_submit = adapter.submit
    adapter.submit = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("provider down"))
    try:
        result = asyncio.run(start_generation_batch({}))
    finally:
        adapter.submit = original_submit
    assert result["ok"] is True
    assert result["failed"] == 1
    failures = cast(list[dict[str, Any]], result["failures"])
    assert "provider down" in failures[0]["error"]


def test_resume_generation_polling_missing_id() -> None:
    import asyncio

    result = asyncio.run(resume_generation_polling({}))
    assert result["ok"] is False
    assert "generation_id is required" in cast(str, result["error"])


def test_resume_generation_polling_no_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from film_pipeline.app.runtime import get_runtime as gr

    rt2 = gr()
    rt2.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt2)
    result = asyncio.run(resume_generation_polling({"generation_id": "g1"}))
    assert result["ok"] is False


def test_resume_generation_polling_not_found(rt: StudioRuntime) -> None:
    import asyncio

    result = asyncio.run(resume_generation_polling({"generation_id": "no-such-generation"}))
    assert result["ok"] is False
    assert "not found" in cast(str, result["error"])


def test_resume_generation_polling_no_provider_job_id(rt: StudioRuntime) -> None:
    import asyncio

    planned = asyncio.run(
        plan_generation_batch(
            {"shot_ids": ["S001"], "provider": "mock-video-provider", "model": "mock-fast"}
        )
    )
    gen_id = cast(list[dict[str, Any]], planned["rows"])[0]["generation_id"]
    result = asyncio.run(resume_generation_polling({"generation_id": gen_id}))
    assert result["ok"] is False
    assert "no provider_job_id" in cast(str, result["error"])


def test_resume_generation_polling_unknown_provider(rt: StudioRuntime) -> None:
    import asyncio

    from film_pipeline.generation.ledger import GenerationLedgerManager

    planned = asyncio.run(
        plan_generation_batch(
            {"shot_ids": ["S001"], "provider": "mock-video-provider", "model": "mock-fast"}
        )
    )
    gen_id = cast(list[dict[str, Any]], planned["rows"])[0]["generation_id"]
    assert rt.services is not None
    mgr = GenerationLedgerManager(rt.services.artifact_store)
    mgr.update_row("gen-start-test", gen_id, provider_job_id="job-1", provider="missing-provider")

    result = asyncio.run(resume_generation_polling({"generation_id": gen_id}))
    assert result["ok"] is False
    assert "not registered" in cast(str, result["error"])


def test_resume_generation_polling_poll_exception(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))
    asyncio.run(start_generation_batch({}))
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationStatus

    assert rt.services is not None
    mgr = GenerationLedgerManager(rt.services.artifact_store)
    row = mgr.list_rows("gen-start-test", status=GenerationStatus.RUNNING)[0]

    adapter = rt.get_provider("mock-video-provider")
    assert adapter is not None
    original_poll = adapter.poll
    adapter.poll = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("poll boom"))
    try:
        result = asyncio.run(resume_generation_polling({"generation_id": row.generation_id}))
    finally:
        adapter.poll = original_poll
    assert result["ok"] is False
    assert "poll boom" in cast(str, result["error"])


@pytest.mark.parametrize("provider_status", ["completed", "failed", "processing"])
def test_resume_generation_polling_status_mapping(rt: StudioRuntime, provider_status: str) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))
    asyncio.run(start_generation_batch({}))
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.providers.base import ProviderJob
    from film_pipeline.schemas._base import GenerationStatus

    assert rt.services is not None
    mgr = GenerationLedgerManager(rt.services.artifact_store)
    row = mgr.list_rows("gen-start-test", status=GenerationStatus.RUNNING)[0]

    adapter = rt.get_provider("mock-video-provider")
    assert adapter is not None
    original_poll = adapter.poll

    def _fake_poll(job: ProviderJob) -> ProviderJob:
        return ProviderJob(
            job_id=job.job_id,
            shot_id=job.shot_id,
            provider_id=job.provider_id,
            model=job.model,
            status=provider_status,
            polls=job.polls + 1,
        )

    adapter.poll = _fake_poll
    try:
        result = asyncio.run(resume_generation_polling({"generation_id": row.generation_id}))
    finally:
        adapter.poll = original_poll
    assert result["ok"] is True
    assert result["generation_id"] == row.generation_id


def test_cancel_generation_request_missing_id() -> None:
    import asyncio

    result = asyncio.run(cancel_generation_request({}))
    assert result["ok"] is False
    assert "generation_id is required" in cast(str, result["error"])


def test_cancel_generation_request_no_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from film_pipeline.app.runtime import get_runtime as gr

    rt2 = gr()
    rt2.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt2)
    result = asyncio.run(cancel_generation_request({"generation_id": "g1"}))
    assert result["ok"] is False


def test_cancel_generation_request_not_found(rt: StudioRuntime) -> None:
    import asyncio

    result = asyncio.run(cancel_generation_request({"generation_id": "no-such-generation"}))
    assert result["ok"] is False
    assert "not found" in cast(str, result["error"])


def test_cancel_generation_request_no_provider_job_id(rt: StudioRuntime) -> None:
    import asyncio

    planned = asyncio.run(
        plan_generation_batch(
            {"shot_ids": ["S001"], "provider": "mock-video-provider", "model": "mock-fast"}
        )
    )
    gen_id = cast(list[dict[str, Any]], planned["rows"])[0]["generation_id"]
    result = asyncio.run(cancel_generation_request({"generation_id": gen_id}))
    assert result["ok"] is True
    assert result["cancelled"] is True
    assert result["provider"] is False


def test_cancel_generation_request_unknown_provider(rt: StudioRuntime) -> None:
    import asyncio

    from film_pipeline.generation.ledger import GenerationLedgerManager

    planned = asyncio.run(
        plan_generation_batch(
            {"shot_ids": ["S001"], "provider": "mock-video-provider", "model": "mock-fast"}
        )
    )
    gen_id = cast(list[dict[str, Any]], planned["rows"])[0]["generation_id"]
    assert rt.services is not None
    mgr = GenerationLedgerManager(rt.services.artifact_store)
    mgr.update_row("gen-start-test", gen_id, provider_job_id="job-1", provider="missing-provider")

    result = asyncio.run(cancel_generation_request({"generation_id": gen_id}))
    assert result["ok"] is False
    assert "not registered" in cast(str, result["error"])


def test_cancel_generation_request_with_provider(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))
    asyncio.run(start_generation_batch({}))
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationStatus

    assert rt.services is not None
    mgr = GenerationLedgerManager(rt.services.artifact_store)
    row = mgr.list_rows("gen-start-test", status=GenerationStatus.RUNNING)[0]

    result = asyncio.run(cancel_generation_request({"generation_id": row.generation_id}))
    assert result["ok"] is True
    assert result["cancelled"] is True
    assert result["provider"] is True


def test_cancel_generation_request_provider_returns_false(rt: StudioRuntime) -> None:
    import asyncio

    asyncio.run(_plan_and_approve(["S001"]))
    asyncio.run(start_generation_batch({}))
    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationStatus

    assert rt.services is not None
    mgr = GenerationLedgerManager(rt.services.artifact_store)
    row = mgr.list_rows("gen-start-test", status=GenerationStatus.RUNNING)[0]

    adapter = rt.get_provider("mock-video-provider")
    assert adapter is not None
    original_cancel = adapter.cancel
    adapter.cancel = lambda *_args, **_kwargs: False
    try:
        result = asyncio.run(cancel_generation_request({"generation_id": row.generation_id}))
    finally:
        adapter.cancel = original_cancel
    assert result["ok"] is True
    assert result["cancelled"] is False
    assert result["provider"] is True


def test_promote_test_to_production_with_shot_ids_filter(rt: StudioRuntime) -> None:
    import asyncio

    from film_pipeline.generation.ledger import GenerationLedgerManager
    from film_pipeline.schemas._base import GenerationMode, GenerationStatus

    asyncio.run(
        plan_generation_batch(
            {"shot_ids": ["S001", "S002"], "provider": "mock-video-provider", "model": "mock-fast"}
        )
    )
    assert rt.services is not None
    mgr = GenerationLedgerManager(rt.services.artifact_store)
    for row in mgr.list_rows("gen-start-test"):
        mgr.update_row(
            "gen-start-test",
            row.generation_id,
            status=GenerationStatus.COMPLETED,
            mode=GenerationMode.TEST,
        )

    result = asyncio.run(promote_test_to_production({"shot_ids": ["S001"], "confirmed": True}))
    assert result["ok"] is True
    assert result["promoted"] == 1


def test_preview_generation_prompts_no_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio

    from film_pipeline.app.runtime import get_runtime as gr

    rt2 = gr()
    rt2.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt2)
    result = asyncio.run(preview_generation_prompts({}))
    assert result["ok"] is False
    assert "active project" in cast(str, result["error"]).lower()


def test_preview_generation_prompts_resolves_from_shot_matrix(rt: StudioRuntime) -> None:
    import asyncio
    from datetime import UTC, datetime

    from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
    from film_pipeline.schemas.artifact import ArtifactMetadata
    from film_pipeline.schemas.matrix import MasterFilmMatrix, MasterFilmMatrixRow

    assert rt.services is not None
    store = rt.services.artifact_store
    matrix = MasterFilmMatrix(
        project_id="gen-start-test",
        rows=[
            MasterFilmMatrixRow(
                shot_id="shot_0001",
                act_id="act1",
                sequence_id="seq_001",
                scene_id="sc_001",
                scene_intent_ref="s_001",
                duration_seconds=8,
                story_function="inciting image",
                characters=["mara"],
                environment="field",
                camera_profile="wide_establishing",
            )
        ],
    )
    store.save(
        matrix,
        ArtifactMetadata(
            artifact_id="shot_matrix",
            artifact_type=ArtifactType.MASTER_FILM_MATRIX,
            project_id="gen-start-test",
            phase=FilmPhase.SHOT_BIBLE,
            version=1,
            status=ArtifactStatus.CANDIDATE,
            created_by="test",
            created_at=datetime.now(UTC),
        ),
    )

    result = asyncio.run(preview_generation_prompts({}))
    assert result["ok"] is True
    previews = cast(list[dict[str, object]], result["previews"])
    assert len(previews) == 1
    assert previews[0]["shot_id"] == "shot_0001"
    assert previews[0]["provider"] == "mock-video-provider"
    assert "wide_establishing" in str(previews[0]["prompt"]).lower()
