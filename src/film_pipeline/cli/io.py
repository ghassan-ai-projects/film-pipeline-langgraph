"""Read film ideas from supported file formats."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class UnsupportedIdeaFileError(ValueError):
    """Raised when the supplied file type cannot be read as a film idea."""


SUPPORTED_EXTENSIONS: set[str] = {".txt", ".md", ".pdf"}


def read_constraints_file(path: Path) -> dict[str, Any]:
    """Return a dict from a JSON or YAML constraints file.

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file cannot be parsed.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Constraints file not found: {path}")

    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}

    import json

    if suffix == ".json":
        data = json.loads(raw)
    elif suffix in {".yaml", ".yml"}:
        import yaml

        data = yaml.safe_load(raw)
    else:
        # Default to JSON for unknown extensions.
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Constraints file '{path}' must be JSON or YAML.") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Constraints file '{path}' must contain a single object.")
    return data


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
    text_parts = [str(page.extract_text() or "") for page in reader.pages]
    return "\n\n".join(part.strip() for part in text_parts if part.strip())
