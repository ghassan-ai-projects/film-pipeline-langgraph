"""Compatibility aliases for :mod:`film_pipeline.orchestration.context_packets`."""

from __future__ import annotations

from film_pipeline.orchestration.context_packets import PHASE_BUILDERS as PHASE_BUILDERS

# Private helpers still reached through this path during migration.
from film_pipeline.orchestration.context_packets import _ArtifactLoader as _ArtifactLoader
from film_pipeline.orchestration.context_packets import (
    _ContextPacketSources as _ContextPacketSources,
)
from film_pipeline.orchestration.context_packets import _count_rows_per_act as _count_rows_per_act
from film_pipeline.orchestration.context_packets import _load_ref as _load_ref
from film_pipeline.orchestration.context_packets import _load_state_ref as _load_state_ref
from film_pipeline.orchestration.context_packets import (
    _render_target_and_type as _render_target_and_type,
)
from film_pipeline.orchestration.context_packets import (
    _summarize_execution_brief as _summarize_execution_brief,
)
from film_pipeline.orchestration.context_packets import (
    build_constitution_context as build_constitution_context,
)
from film_pipeline.orchestration.context_packets import (
    build_development_context as build_development_context,
)
from film_pipeline.orchestration.context_packets import (
    build_gen_planning_context as build_gen_planning_context,
)
from film_pipeline.orchestration.context_packets import build_script_context as build_script_context
from film_pipeline.orchestration.context_packets import (
    build_shot_bible_context as build_shot_bible_context,
)
from film_pipeline.orchestration.context_packets import (
    build_visual_dev_context as build_visual_dev_context,
)

__all__ = [
    "PHASE_BUILDERS",
    "build_constitution_context",
    "build_development_context",
    "build_gen_planning_context",
    "build_script_context",
    "build_shot_bible_context",
    "build_visual_dev_context",
]
