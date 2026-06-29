"""Unit tests for film_pipeline.mcp.tools.assembly."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.mcp.tools import (
    approve_coverage_generation,
    assemble_final_cut,
    assemble_review_cut,
    export_delivery_package,
    inspect_coverage_group,
    list_coverage_groups,
    plan_coverage_group,
)


def _stub_check(result: dict[str, object], handler: str) -> None:
    assert result["stub"] is True
    assert result["handler"] == handler


def test_plan_coverage_group_stub() -> None:
    _stub_check(asyncio.run(plan_coverage_group({})), "plan_coverage_group")


def test_list_coverage_groups_stub() -> None:
    _stub_check(asyncio.run(list_coverage_groups({})), "list_coverage_groups")


def test_inspect_coverage_group_stub() -> None:
    _stub_check(asyncio.run(inspect_coverage_group({})), "inspect_coverage_group")


def test_approve_coverage_generation_stub() -> None:
    _stub_check(
        asyncio.run(approve_coverage_generation({"confirmed": True})),
        "approve_coverage_generation",
    )


def test_assemble_review_cut_no_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)
    result = asyncio.run(assemble_review_cut({}))
    assert result["ok"] is False
    assert "No active project" in cast(str, result["error"])


def test_assemble_review_cut_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("asm-review", "Assembly Review")
    rt.set_active("asm-review")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(
        assemble_review_cut({"shot_ids": ["S001", "S002"], "clip_paths": ["/clips/S001.mp4"]})
    )
    assert result["ok"] is True
    assert "plan_id" in result
    assert result["clip_count"] == 1


def test_assemble_final_cut_stub() -> None:
    _stub_check(asyncio.run(assemble_final_cut({})), "assemble_final_cut")


def test_export_delivery_package_no_active_project(monkeypatch: pytest.MonkeyPatch) -> None:
    from film_pipeline.app.runtime import get_runtime as gr

    rt = gr()
    rt.active_project_id = ""
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)
    result = asyncio.run(export_delivery_package({"confirmed": True}))
    assert result["ok"] is False
    assert "No active project" in cast(str, result["error"])


def test_export_delivery_package_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rt = StudioRuntime(runtime_root=tmp_path / "runtime")
    rt.create_project("asm-delivery", "Delivery")
    rt.set_active("asm-delivery")
    monkeypatch.setattr("film_pipeline.mcp.tools.get_runtime", lambda: rt)

    result = asyncio.run(
        export_delivery_package(
            {
                "video_path": "/out/final.mp4",
                "subtitle_path": "/out/subs.srt",
                "audio_stems_dir": "/out/audio",
                "stills_dir": "/out/stills",
                "validation_report_path": "/out/val.json",
                "cost_report_path": "/out/cost.json",
                "credits_path": "/out/credits.txt",
                "confirmed": True,
            }
        )
    )
    assert result["ok"] is True
    assert "package_id" in result
    assert result["is_complete"] is True
