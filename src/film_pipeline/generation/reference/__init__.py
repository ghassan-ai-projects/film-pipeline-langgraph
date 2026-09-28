"""Reference-image generation: the use case, without the tool surface.

Moved out of `mcp/tools/reference_generation/` (doc 03 slice 2). These modules are
the retry loop, outcome recording, composite assembly and index persistence for
reference generation — `GraphServices` and an artifact store in, artifacts out. None
of them touches an MCP context, shapes a response, or reads a tool argument.

The MCP handler stayed in `mcp/tools/reference_generation/tool.py`. It is the one
piece that speaks MCP (`ToolContext`, `ToolArgs`, `_ok`/`_error`), and keeping it
here would close `generation <-> mcp` — a package that owns a use case must not
depend on the surface that exposes it. Before the split, `mcp -> generation` was 23
imports; the handler plus the five `generation` tool modules now account for 14.

The facade below is private-name-heavy on purpose: these helpers were `_`-prefixed
when they were `mcp`-internal and are still internal to the use case. Only the tool
module imports them.
"""

from __future__ import annotations

from film_pipeline.generation.reference.composites import (
    build_composites,
    build_optional_sheets,
    validate_composite,
)
from film_pipeline.generation.reference.context import (
    GenerationBatch,
    copied_entries,
    latest_artifact_version,
    load_character_bibles,
    prepare_entry_context,
    reference_services,
    requested_reference_ids,
)
from film_pipeline.generation.reference.entries import (
    group_and_sort_entries,
    group_key,
    reference_aspect_ratio,
    reference_job_id,
    reference_output_dir,
    reference_prompt,
)
from film_pipeline.generation.reference.index_files import (
    reference_entries_from_grouped,
    save_reference_index_artifact,
    select_image_provider,
    write_reference_index_files,
)
from film_pipeline.generation.reference.outcomes import (
    register_generated_entry,
    stamp_retry_stats,
    update_identity_group,
)
from film_pipeline.generation.reference.retry_loop import run_retry_attempts

__all__ = [
    "GenerationBatch",
    "build_composites",
    "build_optional_sheets",
    "copied_entries",
    "group_and_sort_entries",
    "group_key",
    "latest_artifact_version",
    "load_character_bibles",
    "prepare_entry_context",
    "reference_aspect_ratio",
    "reference_entries_from_grouped",
    "reference_job_id",
    "reference_output_dir",
    "reference_prompt",
    "reference_services",
    "register_generated_entry",
    "requested_reference_ids",
    "run_retry_attempts",
    "save_reference_index_artifact",
    "select_image_provider",
    "stamp_retry_stats",
    "update_identity_group",
    "validate_composite",
    "write_reference_index_files",
]
