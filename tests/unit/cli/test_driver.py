"""Unit tests for the headless CLI driver helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.cli.driver import HeadlessDriver, HeadlessDriverError


def test_setup_runtime_rejects_invalid_mode(tmp_path: Path) -> None:
    with pytest.raises(HeadlessDriverError, match="runtime_mode must be"):
        HeadlessDriver.setup_runtime("invalid", tmp_path)


def test_unknown_target_phase(tmp_path: Path) -> None:
    import film_pipeline.app.runtime as rt_mod

    previous_runtime = rt_mod._RUNTIME
    previous_override = rt_mod._RUNTIME_MODE_OVERRIDE
    try:
        rt = HeadlessDriver.setup_runtime("mock", tmp_path / "runtime")
        driver = HeadlessDriver(rt, "p1", target_phase="not_a_phase")
        with pytest.raises(HeadlessDriverError, match="Unknown target phase"):
            rt.create_project(project_id="p1", title="T", slug="p1")
            rt.set_active("p1")
            rt.projects["p1"]["current_phase"] = "intake"
            rt.projects["p1"]["human_approval_required"] = True
            import asyncio

            asyncio.run(driver.run_to_target())
    finally:
        rt_mod._RUNTIME = previous_runtime
        rt_mod._RUNTIME_MODE_OVERRIDE = previous_override


def test_call_tool_unknown_tool() -> None:
    import film_pipeline.app.runtime as rt_mod

    previous_runtime = rt_mod._RUNTIME
    previous_override = rt_mod._RUNTIME_MODE_OVERRIDE
    try:
        rt = HeadlessDriver.setup_runtime("mock", Path("/tmp/film-cli-unit-test"))
        driver = HeadlessDriver(rt, "p1")
        import asyncio

        with pytest.raises(HeadlessDriverError, match="Unknown MCP tool"):
            asyncio.run(driver._call_tool("not_a_real_tool"))
    finally:
        rt_mod._RUNTIME = previous_runtime
        rt_mod._RUNTIME_MODE_OVERRIDE = previous_override
