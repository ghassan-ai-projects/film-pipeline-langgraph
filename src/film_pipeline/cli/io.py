"""Read film ideas from supported file formats."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class UnsupportedIdeaFileError(ValueError):
    """Raised when the supplied file type cannot be read as a film idea."""


SUPPORTED_EXTENSIONS: set[str] = {".txt", ".md", ".pdf"}


def read_idea_file(path: Path) -> str:
    """Return plain text from a ``.txt``, ``.md``, or ``.pdf`` file.

    Raises:
        UnsupportedIdeaFileError: if the extension is not supported.
        FileNotFoundError: if the file does not exist.
        UnicodeDecodeError: if a text file is not valid UTF-8.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Idea file not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise UnsupportedIdeaFileError(f"Unsupported file type '{suffix}'. Supported: {supported}")

    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8").strip()

    return _read_pdf_text(path)


def _read_pdf_text(path: Path) -> str:
    """Extract text from a PDF using ``pypdf``."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[Any] = reader.pages if hasattr(reader, "pages") else []
    text_parts = [str(page.extract_text() or "") for page in pages]
    return "\n\n".join(part.strip() for part in text_parts if part.strip())
