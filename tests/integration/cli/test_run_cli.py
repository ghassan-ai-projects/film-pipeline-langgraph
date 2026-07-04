"""Integration test for the CLI entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from film_pipeline.cli.run import main


@pytest.fixture
def idea_file(tmp_path: Path) -> Path:
    p = tmp_path / "idea.txt"
    p.write_text(
        "A 1-minute animated short about a paper boat crossing a city sewer.\n"
        "Six scenes, roughly 10 seconds each.\n",
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
class TestRunCli:
    def test_main_mock_mode(
        self,
        idea_file: Path,
        tmp_path: Path,
        isolated_runtime: Any,
        capsys: Any,
    ) -> None:
        code = main(
            [
                str(idea_file),
                "--runtime-root",
                str(tmp_path / "runtime"),
                "--target-scene-count",
                "2",
                "--target-runtime-seconds",
                "20",
            ]
        )
        assert code == 0
        captured = capsys.readouterr()
        assert "Project: idea" in captured.out
        assert "shot_matrix" in captured.out
