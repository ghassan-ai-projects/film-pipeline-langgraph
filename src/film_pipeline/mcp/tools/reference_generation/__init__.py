"""Reference-image generation pipeline tool and supporting helpers.

Split by concern; this facade preserves the original import surface.
"""

from __future__ import annotations

from film_pipeline.mcp.tools.reference_generation.composites import (
    _build_composites,
    _build_optional_sheets,
    _validate_composite,
)
from film_pipeline.mcp.tools.reference_generation.entries import (
    _group_and_sort_entries,
    _group_key,
    _reference_aspect_ratio,
    _reference_job_id,
    _reference_output_dir,
    _reference_prompt,
)
from film_pipeline.mcp.tools.reference_generation.index_files import (
    _reference_entries_from_grouped,
    _save_reference_index_artifact,
    _select_image_provider,
    _write_reference_index_files,
)
from film_pipeline.mcp.tools.reference_generation.tool import generate_reference_images

__all__ = [
    "_build_composites",
    "_build_optional_sheets",
    "_group_and_sort_entries",
    "_group_key",
    "_reference_aspect_ratio",
    "_reference_entries_from_grouped",
    "_reference_job_id",
    "_reference_output_dir",
    "_reference_prompt",
    "_save_reference_index_artifact",
    "_select_image_provider",
    "_validate_composite",
    "_write_reference_index_files",
    "generate_reference_images",
]
