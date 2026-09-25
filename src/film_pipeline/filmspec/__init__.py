"""Pure film vocabulary and phase order shared by every studio layer."""

from __future__ import annotations

from enum import StrEnum


class FilmPhase(StrEnum):
    """The canonical production phases of a film."""

    INTAKE = "intake"
    CONSTITUTION = "constitution"
    DEVELOPMENT = "development"
    SCRIPT = "script"
    VISUAL_DEV = "visual_dev"
    SHOT_BIBLE = "shot_bible"
    GEN_PLANNING = "gen_planning"
    GENERATION = "generation"
    QC = "qc"
    POST = "post"
    DELIVERY = "delivery"


PHASE_SEQUENCE: tuple[str, ...] = tuple(phase.value for phase in FilmPhase)


def next_phase(phase: str) -> str | None:
    """Return the next phase, or ``None`` for delivery or an unknown phase."""
    try:
        index = PHASE_SEQUENCE.index(phase)
    except ValueError:
        return None
    if index == len(PHASE_SEQUENCE) - 1:
        return None
    return PHASE_SEQUENCE[index + 1]
