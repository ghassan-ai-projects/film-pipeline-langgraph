"""Budget state and spend records.

The `CostEstimate` record was removed with the cost feature: its only reader
was the planning gate, which now sources its clip count from the shot matrix.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from film_pipeline.schemas.base import MutableSchemaBase


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
