"""Provider health state."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from film_pipeline.schemas.base import MutableSchemaBase, ProviderStatus


class ProviderHealthState(MutableSchemaBase):
    """Runtime health state for a single provider."""

    provider_id: str
    status: ProviderStatus = ProviderStatus.HEALTHY
    last_health_check_at: datetime | None = None
    last_successful_job_at: datetime | None = None
    quota_state: Literal["ok", "low", "exhausted"] = Field(
        default="ok",
        description="'ok' | 'low' | 'exhausted'.",
    )
    credit_state: Literal["ok", "low", "exhausted"] = Field(
        default="ok",
        description="'ok' | 'low' | 'exhausted'.",
    )
    known_outage: bool = False
    blocked_reason: str | None = None
    resume_requirements: str | None = None
    affected_generation_ids: list[str] = Field(default_factory=list)
    safe_continuation_phases: list[str] = Field(default_factory=list)
