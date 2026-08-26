"""Generation requests, ledger rows, shot plans, and resume tokens."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from film_pipeline.schemas._base import GenerationMode, GenerationStatus, SchemaBase


class GenerationRequest(SchemaBase):
    """A request to generate a clip.

    The :attr:`idempotency_key` is computed from project+shot+prompt+reference
    versions+provider+model+mode and prevents duplicate paid submissions.
    """

    generation_request_id: str
    project_id: str
    shot_id: str
    coverage_group_id: str | None = None
    mode: GenerationMode = GenerationMode.TEST
    provider: str
    model: str
    prompt_ref: str
    reference_refs: list[str] = Field(default_factory=list)
    idempotency_key: str = Field(
        description="Deterministic key used to block duplicate submissions.",
    )


class ResumeToken(SchemaBase):
    """Lightweight runtime checkpoint used to continue after interruption."""

    resume_token: str
    project_id: str
    generation_id: str
    graph_node: str
    provider_job_id: str | None = None
    last_safe_step: str
    next_action: str
    can_continue_automatically: bool = True
    requires_human_review: bool = False
    requires_provider_fix: bool = False
    created_at: datetime


class GenerationLedgerRow(SchemaBase):
    """One row in the generation ledger — the source of truth for spend."""

    generation_request_id: str
    generation_id: str
    project_id: str
    shot_id: str
    mode: GenerationMode
    provider: str
    model: str
    prompt_ref: str
    reference_refs: list[str] = Field(default_factory=list)
    status: GenerationStatus = GenerationStatus.PREPARED
    provider_job_id: str | None = None
    submitted_at: datetime | None = None
    last_polled_at: datetime | None = None
    poll_count: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0)
    actual_cost_usd: float | None = None
    output_refs: list[str] = Field(default_factory=list)
    error_code: str | None = None
    resume_token: str | None = None
    blocking_reason: str | None = None
    next_action: Literal[
        "submit",
        "poll",
        "download",
        "validate",
        "wait_human",
        "stop",
    ] = "submit"


class GenerationLedger(SchemaBase):
    """Aggregate generation ledger."""

    project_id: str
    rows: list[GenerationLedgerRow] = Field(default_factory=list)


class ShotPlan(SchemaBase):
    """One shot in the generation plan with provider routing."""

    shot_id: str
    priority: int = Field(default=3, ge=1, le=5)
    risk: str = "medium"
    provider_id: str = ""
    model_id: str = ""
    tier: str = "fast"
    estimated_duration: float = Field(default=5.0, ge=0)
    estimated_cost: float = Field(default=0.0, ge=0)
    prompt_ref: str = ""
    generation_order: int = 0
    dependencies: list[str] = Field(default_factory=list)


class GenerationPlan(SchemaBase):
    """Ordered shot execution plan with provider routing and cost estimates."""

    project_id: str
    shots: list[ShotPlan] = Field(default_factory=list)
    total_estimated_cost: float = Field(default=0.0, ge=0)
    provider_utilization: dict[str, int] = Field(default_factory=dict)
    created_at: str = ""
