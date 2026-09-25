"""The ordered film-phase sequence used by graph and operator routing.

``FilmPhase`` owns the serialized phase vocabulary. Its declaration order is
the execution order; this module exposes that order and its successor relation.
Approval and provider-readiness decisions belong to the router, not here.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from film_pipeline.filmspec import PHASE_SEQUENCE as PHASE_SEQUENCE
from film_pipeline.filmspec import next_phase as next_phase

# The tuple is the immutable source used by internal routing. ``PHASE_ORDER``
# remains a list-shaped compatibility view for existing imports from router.
PHASE_ORDER: list[str] = list(PHASE_SEQUENCE)

# Graph node names are a projection of the phase vocabulary. Every phase has
# exactly one phase node; gate and terminal nodes are declared by graph.py.
PHASE_NODES: Mapping[str, str] = MappingProxyType(
    {phase: f"{phase}_node" for phase in PHASE_SEQUENCE}
)
