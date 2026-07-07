"""Orchestrator structural validators — Gates S, A, B, and C.

These run at phase boundaries to enforce film-level invariants:
- Gate S (development/script): scene counts survive each hop
- Gate A (shot_bible): shot-count per movement, runtime totals
- Gate B (gen_planning): field completeness, non-placeholder cost estimates
- Gate C (generation): dispatch readiness — real clip counts, executable requests

On failure they append blocking issues to ``state["issues"]``, which the
router's ``compute_actions()`` already handles via the ``handle_blockers``
path. No new router tier needed.
"""

from __future__ import annotations

from film_pipeline.graph.orchestrator_validators.brief import (
    load_execution_brief,
    validate_execution_brief,
)
from film_pipeline.graph.orchestrator_validators.planning_gates import (
    validate_dispatch_readiness,
    validate_planning_completeness,
    validate_shot_scene_references,
)
from film_pipeline.graph.orchestrator_validators.prep_gates import (
    validate_scene_count,
    validate_script_scene_preservation,
    validate_shot_structure,
)

__all__ = [
    "load_execution_brief",
    "validate_dispatch_readiness",
    "validate_execution_brief",
    "validate_planning_completeness",
    "validate_scene_count",
    "validate_script_scene_preservation",
    "validate_shot_scene_references",
    "validate_shot_structure",
]
