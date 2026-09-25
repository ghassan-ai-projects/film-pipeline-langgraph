"""The ordered film-phase sequence used by graph and operator routing.

``FilmPhase`` owns the serialized phase vocabulary. Its declaration order is
the execution order; this module exposes that order and its successor relation.
Approval and provider-readiness decisions belong to the router, not here.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from film_pipeline.schemas import FilmPhase

# The tuple is the immutable source used by internal routing. ``PHASE_ORDER``
# remains a list-shaped compatibility view for existing imports from router.
PHASE_SEQUENCE: tuple[str, ...] = tuple(phase.value for phase in FilmPhase)
PHASE_ORDER: list[str] = list(PHASE_SEQUENCE)

# Graph node names are a projection of the phase vocabulary. Every phase has
# exactly one phase node; gate and terminal nodes are declared by graph.py.
PHASE_NODES: Mapping[str, str] = MappingProxyType(
    {phase: f"{phase}_node" for phase in PHASE_SEQUENCE}
)


def next_phase(phase: str) -> str | None:
    """Return the successor, or ``None`` for delivery or an unknown phase."""
    try:
        index = PHASE_SEQUENCE.index(phase)
    except ValueError:
        return None
    if index == len(PHASE_SEQUENCE) - 1:
        return None
    return PHASE_SEQUENCE[index + 1]
