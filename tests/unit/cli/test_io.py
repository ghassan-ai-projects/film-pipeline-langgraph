"""Tests for idea-file reading."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.cli.io import SUPPORTED_EXTENSIONS, UnsupportedIdeaFileError, read_idea_file


def test_read_txt_file(tmp_path: Path) -> None:
    p = tmp_path / "idea.txt"
    p.write_text("  A robot learns to paint.  ", encoding="utf-8")
    assert read_idea_file(p) == "A robot learns to paint."


def test_read_md_file(tmp_path: Path) -> None:
    p = tmp_path / "idea.md"
    p.write_text("# Idea\n\nA gardener discovers sentient plants.", encoding="utf-8")
    assert read_idea_file(p) == "# Idea\n\nA gardener discovers sentient plants."


def test_read_pdf_file(tmp_path: Path) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612.0, height=792.0)
    # pypdf does not easily support adding text in a writer-agnostic way across
    # versions, so we rely on the blank-page extraction returning an empty string
    # and assert the function completes without error for a valid PDF.
    p = tmp_path / "idea.pdf"
    with p.open("wb") as f:
        writer.write(f)
    text = read_idea_file(p)
    assert isinstance(text, str)

    # Now write a file with real extracted text by round-tripping through a
    # text-only PDF created via reportlab if available; otherwise skip.
    try:
        from reportlab.pdfgen import canvas  # type: ignore[import-untyped]
    except ImportError:
        pytest.skip("reportlab not installed")
    p2 = tmp_path / "idea2.pdf"
    c = canvas.Canvas(str(p2))
    c.drawString(100, 700, "A chef competes in a cooking duel.")
    c.save()
    assert "cooking duel" in read_idea_file(p2)


def test_unsupported_extension(tmp_path: Path) -> None:
    p = tmp_path / "idea.docx"
    p.write_text("not supported", encoding="utf-8")
    with pytest.raises(UnsupportedIdeaFileError) as exc_info:
        read_idea_file(p)
    assert ".docx" in str(exc_info.value)
    assert {".txt", ".md", ".pdf"} == SUPPORTED_EXTENSIONS


def test_missing_file(tmp_path: Path) -> None:
    p = tmp_path / "missing.txt"
    with pytest.raises(FileNotFoundError):
        read_idea_file(p)
