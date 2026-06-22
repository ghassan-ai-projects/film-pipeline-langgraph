"""Execution brief — the orchestrator's structural contract for a film.

Extracted automatically from the approved story by the StructureExtractorAgent.
The orchestrator uses this to enforce shot-count, runtime, and structural
invariants across downstream phases (Gates A/B/C).
"""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas._base import SchemaBase


class MovementSpec(SchemaBase):
    """One movement (act) in the film's structural blueprint.

    ``movement_id`` maps to ``MasterFilmMatrixRow.act_id`` for validation.
    """

    movement_id: str = Field(description="Identifier matching act_id in the shot matrix.")
    shot_count: int = Field(ge=1, description="Expected number of shots in this movement.")
    duration_range_seconds: tuple[int, int] = Field(
        description="(min, max) duration per shot in this movement."
    )
    description: str = Field(default="", description="Short description of this movement.")


class ExecutionBrief(SchemaBase):
    """Structural contract extracted from the approved story.

    Produced once after script approval. Persisted as an artifact so the
    orchestrator and validators can enforce shot-count, runtime, and
    structural invariants without relying on the raw story text.
    """

    project_id: str
    target_runtime_seconds: int = Field(ge=1, description="Authored total runtime in seconds.")
    movements: list[MovementSpec] = Field(
        default_factory=list,
        description="Ordered list of movements with expected shot counts and durations.",
    )
    mandatory_anchors: list[str] = Field(
        default_factory=list,
        description="Characters, objects, and motifs that must appear in the shot matrix.",
    )
    environment_progression: list[str] = Field(
        default_factory=list,
        description="Ordered list of environment states across the film.",
    )
    pacing_style: str = Field(
        default="standard", description="Pacing style: 'slow_cinema', 'standard', 'dynamic'."
    )
