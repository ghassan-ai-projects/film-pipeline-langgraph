"""Tests for the CLI argument handling and helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from film_pipeline.cli.run import _build_parser, _profile_stack, main


def test_parser_accepts_file_only(tmp_path: Path) -> None:
    p = tmp_path / "idea.txt"
    p.write_text("A robot learns to paint.", encoding="utf-8")
    args = _build_parser().parse_args([str(p)])
    assert args.file == p
    assert args.runtime_mode == "mock"


def test_real_mode_requires_confirm_real(tmp_path: Path, capsys: Any) -> None:
    p = tmp_path / "idea.txt"
    p.write_text("A robot learns to paint.", encoding="utf-8")
    code = main([str(p), "--runtime-mode", "real"])
    assert code == 2
    captured = capsys.readouterr()
    assert "--confirm-real" in captured.err


def test_profile_stack_mock() -> None:
    parser = _build_parser()
    args = parser.parse_args(["idea.txt"])
    assert _profile_stack(args) == ["quality.studio", "film-type.narrative"]


def test_profile_stack_real_with_confirm() -> None:
    parser = _build_parser()
    args = parser.parse_args(["idea.txt", "--runtime-mode", "real", "--confirm-real"])
    assert _profile_stack(args) == [
        "provider.seedance_primary",
        "quality.studio",
        "film-type.narrative",
    ]


def test_main_file_not_found(tmp_path: Path, capsys: Any) -> None:
    missing = tmp_path / "missing.txt"
    code = main([str(missing)])
    assert code == 1
    captured = capsys.readouterr()
    assert "Idea file not found" in captured.err


def test_print_summary_blockers(capsys: Any) -> None:
    from film_pipeline.cli.run import _print_summary

    state = {
        "current_phase": "shot_bible",
        "approved": True,
        "artifact_refs": ["artifact:shot_matrix:v1"],
        "issues": [{"severity": "blocking", "code": "TOO_SHORT", "message": "runtime too short"}],
    }
    _print_summary(state, "proj")
    captured = capsys.readouterr()
    assert "Blockers: 1" in captured.out
    assert "TOO_SHORT" in captured.out
