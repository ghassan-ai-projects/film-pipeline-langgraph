"""Budget state, cost estimates, and spend records."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from film_pipeline.schemas._base import MutableSchemaBase, SchemaBase


class CostEstimate(SchemaBase):
    """Estimated cost for one generation batch."""

    project_id: str
    batch_id: str
    provider: str
    estimated_cost_usd: float = Field(ge=0)
    clip_count: int = Field(ge=0)
    notes: str = ""


class SpendRecord(MutableSchemaBase):
    """One recorded spend line."""

    spend_id: str
    project_id: str
    generation_id: str
    provider: str
    amount_usd: float = Field(ge=0)
    mode: str
    created_at: datetime


class BudgetState(MutableSchemaBase):
    """Mutable running budget state for a project."""

    project_id: str
    cap_usd: float = Field(default=0.0, ge=0)
    spent_usd: float = Field(default=0.0, ge=0)
    per_phase_caps_usd: dict[str, float] = Field(default_factory=dict)
    per_phase_spent_usd: dict[str, float] = Field(default_factory=dict)
    max_auto_approved_cost_usd: float = Field(default=1.0, ge=0)
    human_approval_above_usd: float = Field(default=1.0, ge=0)

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.cap_usd - self.spent_usd)
