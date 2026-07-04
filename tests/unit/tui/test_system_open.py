"""Tests for the system file opener helper."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from film_pipeline.tui.system_open import open_path


def test_open_path_raises_for_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.mp4"
    with pytest.raises(RuntimeError, match="Path does not exist"):
        open_path(missing)


def test_open_path_calls_system_opener(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "clip.mp4"
    target.write_text("mock video")

    with patch("subprocess.run") as mock_run:
        monkeypatch.setattr("sys.platform", "linux")
        monkeypatch.setattr("shutil.which", lambda _cmd: "xdg-open")
        open_path(target)
        mock_run.assert_called_once_with(["xdg-open", str(target)], check=False)
