"""Integration test for the headless CLI driver."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from film_pipeline.cli.driver import HeadlessRunSpec, run_headless


@pytest.fixture
def idea_file(tmp_path: Path) -> Path:
    p = tmp_path / "idea.txt"
    p.write_text(
        'A 3-minute science-fiction drama called "The Bot and the Brush".\n'
        "Twelve scenes, roughly 15 seconds each.\n"
        "Target runtime: 180 seconds.\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture
def isolated_runtime() -> Any:
    """Save and restore the global runtime singleton around the test."""
    import film_pipeline.app.runtime as rt_mod

    previous_runtime = rt_mod._RUNTIME
    previous_override = rt_mod._RUNTIME_MODE_OVERRIDE
    try:
        yield None
    finally:
        rt_mod._RUNTIME = previous_runtime
        rt_mod._RUNTIME_MODE_OVERRIDE = previous_override


@pytest.mark.integration
class TestRunHeadless:
    def test_run_through_shot_bible_mock(
        self,
        idea_file: Path,
        tmp_path: Path,
        isolated_runtime: Any,
    ) -> None:
        state = asyncio.run(
            run_headless(
                HeadlessRunSpec(
                    file_path=idea_file,
                    project_id="cli-mock-test",
                    title="The Bot and the Brush",
                    slug="cli-mock-test",
                    runtime_mode="mock",
                    runtime_root=tmp_path / "runtime",
                    profile_stack=["quality.draft", "film-type.narrative"],
                    target_phase="shot_bible",
                    target_runtime_seconds=20,
                    target_scene_count=2,
                )
            )
        )

        assert state["project_id"] == "cli-mock-test"
        # The driver stops after approving the shot_bible gate, so the next
        # phase node (gen_planning) has usually run and paused.
        assert state.get("current_phase") in ("gen_planning", "shot_bible")
        assert state.get("target_scene_count") == 2
        artifact_refs = {str(r) for r in state.get("artifact_refs", [])}
        assert any("shot_matrix" in r for r in artifact_refs)
        assert any("script" in r for r in artifact_refs)
