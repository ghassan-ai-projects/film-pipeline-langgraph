"""Frame metadata sidecar — .meta.json per generated PNG."""

from __future__ import annotations

from pathlib import Path

from film_pipeline.schemas.reference import ReferenceFrame
from film_pipeline.storage.project_storage import ProjectStorage


def _sidecar_path_for(frame_path: Path) -> Path:
    """Return the ``{frame_path}.meta.json`` sidecar path for a frame PNG."""
    return Path(str(frame_path) + ".meta.json")


def write_frame_sidecar(frame_path: Path, metadata: ReferenceFrame) -> Path:
    """Write a ``{frame_path}.meta.json`` sidecar next to a frame PNG.

    Returns the sidecar path.
    """
    sidecar_path = _sidecar_path_for(frame_path)
    ProjectStorage.for_root(sidecar_path.parent).write_json_document(
        sidecar_path, metadata.model_dump(mode="json")
    )
    return sidecar_path


def read_frame_sidecar(frame_path: Path) -> ReferenceFrame:
    """Read and parse a ``{frame_path}.meta.json`` sidecar.

    Raises FileNotFoundError if the sidecar doesn't exist.
    Raises ValueError if the JSON is malformed or doesn't match the schema.
    """
    return ReferenceFrame.model_validate_json(_sidecar_path_for(frame_path).read_text())
