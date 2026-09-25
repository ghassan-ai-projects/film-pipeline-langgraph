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
    rows = cast(list[dict[str, object]], listed["checkpoints"])
    ids = [c["checkpoint_id"] for c in rows]
    assert checkpoint_id in ids
    # Contract (§5): the documented checkpoint row fields are all present.
    # The git short hash is embedded in checkpoint_id rather than a separate key.
    row = next(c for c in rows if c["checkpoint_id"] == checkpoint_id)
    assert set(row) == {
        "checkpoint_id",
        "project_id",
        "phase",
        "created_at",
        "reason",
    }
    assert row["project_id"] == "proj-cp-1"
    assert row["reason"] == "unit test checkpoint"


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
    result = asyncio.run(
        rollback_to_checkpoint({"confirmed": True, "checkpoint_id": created["checkpoint_id"]})
    )
    assert result["ok"] is True
    assert "Rollback completed" in cast(str, result["message"])
    assert result.get("invalidation_report_ref")
    assert result.get("rollback_record_ref")


def test_rollback_to_checkpoint_rejects_without_confirmation() -> None:
    _make_active_project("proj-cp-no-confirm")
    created = asyncio.run(create_checkpoint({"reason": "rollback target"}))
    result = asyncio.run(
        rollback_to_checkpoint({"confirmed": False, "checkpoint_id": created["checkpoint_id"]})
    )
    assert result["ok"] is False
    assert "confirmation" in cast(str, result["error"])


def test_rollback_to_checkpoint_not_found() -> None:
    result = asyncio.run(rollback_to_checkpoint({"confirmed": True, "checkpoint_id": "no-such-id"}))
    assert result["ok"] is False


def test_rollback_artifact_rejects_without_confirmation() -> None:
    _make_active_project("proj-cp-art-no-confirm")
    asyncio.run(create_checkpoint({"reason": "rollback target"}))
    result = asyncio.run(rollback_artifact({"confirmed": False, "artifact_id": "script"}))
    assert result["ok"] is False
    assert "confirmation" in cast(str, result["error"])


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
    result = asyncio.run(rollback_artifact({"confirmed": True}))
    assert result["ok"] is False
    assert "artifact_id is required" in cast(str, result["error"])


def test_rollback_artifact_requires_active_project() -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    result = asyncio.run(rollback_artifact({"confirmed": True, "artifact_id": "script"}))
    assert result["ok"] is False


def test_rollback_artifact_checkpoint_not_found() -> None:
    _make_active_project("proj-cp-7")
    result = asyncio.run(
        rollback_artifact(
            {"confirmed": True, "artifact_id": "script", "checkpoint_id": "no-such-checkpoint"}
        )
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
        rollback_artifact(
            {"confirmed": True, "artifact_id": "script", "checkpoint_id": created["checkpoint_id"]}
        )
    )
    assert result["ok"] is False
    assert "no git commit ref" in cast(str, result["error"])


def test_rollback_artifact_no_checkpoint_contains_artifact() -> None:
    _make_active_project("proj-cp-9")
    asyncio.run(create_checkpoint({"reason": "no matching artifact"}))
    result = asyncio.run(
        rollback_artifact({"confirmed": True, "artifact_id": "totally-unused-artifact-xyz"})
    )
    assert result["ok"] is False
    assert "No checkpoint found containing artifact" in cast(str, result["error"])


def test_create_checkpoint_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _make_active_project("proj-cp-ve")
    from film_pipeline.app.runtime import get_runtime as gr

    def _raise(**_kwargs: object) -> None:
        raise ValueError("bad checkpoint")

    rt = gr()
    monkeypatch.setattr(rt, "create_checkpoint", _raise)
    result = asyncio.run(create_checkpoint({"reason": "will fail"}))
    assert result["ok"] is False
    assert "bad checkpoint" in cast(str, result["error"])


def test_list_artifact_versions_no_checkpoints() -> None:
    _make_active_project("proj-cp-empty")
    result = asyncio.run(list_artifact_versions({}))
    assert result["ok"] is True
    assert result["versions"] == []


def test_rollback_artifact_specific_checkpoint_git_restore_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_active_project("proj-cp-restore-fail")
    created = asyncio.run(create_checkpoint({"reason": "restore fail"}))
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    cp = rt.get_checkpoint(cast(str, created["checkpoint_id"]))
    assert cp is not None
    manager = rt.checkpoint_managers.get("proj-cp-restore-fail")
    assert manager is not None
    monkeypatch.setattr(
        manager.git, "list_files", lambda _c: ["artifacts/03-script/script/meta.json"]
    )

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("git")

    monkeypatch.setattr(manager.git, "restore_files", _raise)
    result = asyncio.run(
        rollback_artifact(
            {"confirmed": True, "artifact_id": "script", "checkpoint_id": created["checkpoint_id"]}
        )
    )
    assert result["ok"] is False
    assert "git" in cast(str, result["error"])


def test_rollback_artifact_fallback_loop_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _make_active_project("proj-cp-fallback")
    asyncio.run(create_checkpoint({"reason": "fallback"}))
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    project_id = "proj-cp-fallback"
    cps = rt.list_checkpoints(project_id)
    assert len(cps) == 1
    cp = cps[0]
    # Inject the artifact into the checkpoint's artifact_versions so the fallback loop finds it.
    updated = cp.model_copy(update={"artifact_versions": {"my_artifact": "v1"}})
    rt.checkpoints[cp.checkpoint_id] = updated
    rt.checkpoint_managers[project_id].checkpoints[cp.checkpoint_id] = updated

    manager = rt.checkpoint_managers[project_id]
    calls: list[tuple[object, ...]] = []

    def _restore(commit: str, files: list[str]) -> None:
        calls.append((commit, files))

    monkeypatch.setattr(
        manager.git, "list_files", lambda _c: ["artifacts/post/my_artifact/meta.json"]
    )
    monkeypatch.setattr(manager.git, "restore_files", _restore)
    result = asyncio.run(rollback_artifact({"confirmed": True, "artifact_id": "my_artifact"}))

    assert result["ok"] is True
    assert result["artifact_id"] == "my_artifact"
    assert len(calls) == 1


def test_rollback_artifact_specific_checkpoint_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_active_project("proj-cp-restore-ok")
    created = asyncio.run(create_checkpoint({"reason": "restore ok"}))
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    manager = rt.checkpoint_managers.get("proj-cp-restore-ok")
    assert manager is not None
    monkeypatch.setattr(
        manager.git, "list_files", lambda _c: ["artifacts/03-script/script/meta.json"]
    )
    monkeypatch.setattr(manager.git, "restore_files", lambda *_args, **_kwargs: None)
    result = asyncio.run(
        rollback_artifact(
            {"confirmed": True, "artifact_id": "script", "checkpoint_id": created["checkpoint_id"]}
        )
    )
    assert result["ok"] is True
    assert result["artifact_id"] == "script"


def test_rollback_artifact_specific_checkpoint_no_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _make_active_project("proj-cp-no-manager")
    created = asyncio.run(create_checkpoint({"reason": "no manager"}))
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    monkeypatch.setattr(rt, "checkpoint_managers", {})
    result = asyncio.run(
        rollback_artifact(
            {"confirmed": True, "artifact_id": "script", "checkpoint_id": created["checkpoint_id"]}
        )
    )
    assert result["ok"] is False
    assert "No checkpoint manager" in cast(str, result["error"])


def test_rollback_artifact_fallback_no_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    _make_active_project("proj-cp-fallback-no-manager")
    asyncio.run(create_checkpoint({"reason": "fallback no manager"}))
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    project_id = "proj-cp-fallback-no-manager"
    cps = rt.list_checkpoints(project_id)
    cp = cps[0]
    updated = cp.model_copy(update={"artifact_versions": {"my_artifact": "v1"}})
    rt.checkpoints[cp.checkpoint_id] = updated
    rt.checkpoint_managers[project_id].checkpoints[cp.checkpoint_id] = updated
    monkeypatch.setattr(rt, "checkpoint_managers", {})

    result = asyncio.run(rollback_artifact({"confirmed": True, "artifact_id": "my_artifact"}))
    assert result["ok"] is False
    assert "No checkpoint found containing artifact" in cast(str, result["error"])


def test_rollback_artifact_fallback_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    _make_active_project("proj-cp-fallback-exc")
    asyncio.run(create_checkpoint({"reason": "fallback exc"}))
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    project_id = "proj-cp-fallback-exc"
    cps = rt.list_checkpoints(project_id)
    cp = cps[0]
    updated = cp.model_copy(update={"artifact_versions": {"my_artifact": "v1"}})
    rt.checkpoints[cp.checkpoint_id] = updated
    rt.checkpoint_managers[project_id].checkpoints[cp.checkpoint_id] = updated

    manager = rt.checkpoint_managers[project_id]

    def _raise(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("git")

    monkeypatch.setattr(manager.git, "restore_files", _raise)
    result = asyncio.run(rollback_artifact({"confirmed": True, "artifact_id": "my_artifact"}))
    assert result["ok"] is False
    assert "No checkpoint found containing artifact" in cast(str, result["error"])
