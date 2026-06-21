"""Frame metadata sidecar — .meta.json per generated PNG."""

from __future__ import annotations

import json
from pathlib import Path

from film_pipeline.schemas.reference import ReferenceFrame


def write_frame_sidecar(frame_path: Path, metadata: ReferenceFrame) -> Path:
    """Write a ``{frame_path}.meta.json`` sidecar next to a frame PNG.

    Returns the sidecar path.
    """
    sidecar_path = Path(str(frame_path) + ".meta.json")
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar_path.write_text(metadata.model_dump_json(indent=2))
    return sidecar_path


def read_frame_sidecar(frame_path: Path) -> ReferenceFrame:
    """Read and parse a ``{frame_path}.meta.json`` sidecar.

    Raises FileNotFoundError if the sidecar doesn't exist.
    Raises ValueError if the JSON is malformed or doesn't match the schema.
    """
    sidecar_path = Path(str(frame_path) + ".meta.json")
    raw = sidecar_path.read_text()
    data = json.loads(raw)
    return ReferenceFrame(**data)
