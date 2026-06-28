"""Unit tests for film_pipeline.mcp.tools.checkpoints."""

from __future__ import annotations

import asyncio
from typing import cast

import pytest

from film_pipeline.mcp.tools import (
    compare_versions,
    create_checkpoint,
    create_film_project,
    get_checkpoint,
    get_invalidation_report,
    list_artifact_versions,
    list_checkpoints,
    rollback_artifact,
    rollback_to_checkpoint,
    set_active_project,
)


def _make_active_project(project_id: str) -> None:
    asyncio.run(create_film_project({"project_id": project_id}))
    asyncio.run(set_active_project({"project_ref": project_id}))


def test_create_checkpoint_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(create_checkpoint({"reason": "no project"}))
    assert result["ok"] is False


def test_create_and_list_checkpoints() -> None:
    _make_active_project("proj-cp-1")
    created = asyncio.run(create_checkpoint({"reason": "unit test checkpoint"}))
    assert created["ok"] is True
    checkpoint_id = cast(str, created["checkpoint_id"])
    assert checkpoint_id.startswith("checkpoint:proj-cp-1:")

    listed = asyncio.run(list_checkpoints({"project_id": "proj-cp-1"}))
    assert listed["ok"] is True
    ids = [c["checkpoint_id"] for c in cast(list[dict[str, object]], listed["checkpoints"])]
    assert checkpoint_id in ids


def test_get_checkpoint_found_and_missing() -> None:
    _make_active_project("proj-cp-2")
    created = asyncio.run(create_checkpoint({"reason": "for get"}))
    checkpoint_id = created["checkpoint_id"]

    found = asyncio.run(get_checkpoint({"checkpoint_id": checkpoint_id}))
    assert found["ok"] is True
    assert found["checkpoint_id"] == checkpoint_id

    missing = asyncio.run(get_checkpoint({"checkpoint_id": "no-such-checkpoint"}))
    assert missing["ok"] is False


def test_compare_versions() -> None:
    _make_active_project("proj-cp-3")
    cp_a = asyncio.run(create_checkpoint({"reason": "a"}))
    cp_b = asyncio.run(create_checkpoint({"reason": "b"}))

    result = asyncio.run(
        compare_versions(
            {
                "checkpoint_id_a": cp_a["checkpoint_id"],
                "checkpoint_id_b": cp_b["checkpoint_id"],
            }
        )
    )
    assert result["ok"] is True
    assert result["older_reason"] == "a"
    assert result["newer_reason"] == "b"


def test_compare_versions_missing_checkpoint() -> None:
    result = asyncio.run(
        compare_versions({"checkpoint_id_a": "missing-a", "checkpoint_id_b": "missing-b"})
    )
    assert result["ok"] is False


def test_list_artifact_versions_returns_ok() -> None:
    _make_active_project("proj-cp-4")
    asyncio.run(create_checkpoint({"reason": "versions"}))
    result = asyncio.run(list_artifact_versions({}))
    assert result["ok"] is True
    assert "versions" in result


def test_rollback_to_checkpoint_requires_confirmation_message() -> None:
    _make_active_project("proj-cp-5")
    created = asyncio.run(create_checkpoint({"reason": "rollback target"}))
    result = asyncio.run(rollback_to_checkpoint({"checkpoint_id": created["checkpoint_id"]}))
    assert result["ok"] is True
    assert "confirmation" in cast(str, result["message"])


def test_rollback_to_checkpoint_not_found() -> None:
    result = asyncio.run(rollback_to_checkpoint({"checkpoint_id": "no-such-id"}))
    assert result["ok"] is False


def test_get_invalidation_report_not_found() -> None:
    result = asyncio.run(get_invalidation_report({"checkpoint_id": "no-such-id"}))
    assert result["ok"] is False


def test_get_invalidation_report_success() -> None:
    _make_active_project("proj-cp-6")
    created = asyncio.run(create_checkpoint({"reason": "for invalidation"}))
    result = asyncio.run(get_invalidation_report({"checkpoint_id": created["checkpoint_id"]}))
    assert result["ok"] is True
    assert "rollback_target" in result


def test_rollback_artifact_requires_artifact_id() -> None:
    result = asyncio.run(rollback_artifact({}))
    assert result["ok"] is False
    assert "artifact_id is required" in cast(str, result["error"])


def test_rollback_artifact_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(rollback_artifact({"artifact_id": "script"}))
    assert result["ok"] is False


def test_rollback_artifact_checkpoint_not_found() -> None:
    _make_active_project("proj-cp-7")
    result = asyncio.run(
        rollback_artifact({"artifact_id": "script", "checkpoint_id": "no-such-checkpoint"})
    )
    assert result["ok"] is False
    assert "not found" in cast(str, result["error"])


def test_rollback_artifact_checkpoint_without_git_commit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_active_project("proj-cp-8")
    created = asyncio.run(create_checkpoint({"reason": "no git ref"}))
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    cp = rt.get_checkpoint(cast(str, created["checkpoint_id"]))
    assert cp is not None
    no_git_cp = cp.model_copy(update={"git_commit": ""})
    monkeypatch.setattr(rt, "get_checkpoint", lambda _id: no_git_cp)

    result = asyncio.run(
        rollback_artifact({"artifact_id": "script", "checkpoint_id": created["checkpoint_id"]})
    )
    assert result["ok"] is False
    assert "no git commit ref" in cast(str, result["error"])


def test_rollback_artifact_no_checkpoint_contains_artifact() -> None:
    _make_active_project("proj-cp-9")
    asyncio.run(create_checkpoint({"reason": "no matching artifact"}))
    result = asyncio.run(rollback_artifact({"artifact_id": "totally-unused-artifact-xyz"}))
    assert result["ok"] is False
    assert "No checkpoint found containing artifact" in cast(str, result["error"])
