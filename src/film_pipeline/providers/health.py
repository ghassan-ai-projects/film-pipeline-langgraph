"""Provider health tracker — status, quota, credit, outage monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from film_pipeline.schemas._base import ProviderStatus


@dataclass
class ProviderHealth:
    """Health state for one provider."""

    provider_id: str
    status: ProviderStatus = ProviderStatus.HEALTHY
    last_health_check_at: datetime | None = None
    last_successful_job_at: datetime | None = None
    quota_remaining: int = -1  # -1 = unknown / unlimited
    credit_remaining_usd: float = -1.0  # -1 = unknown
    known_outage: bool = False
    blocked_reason: str = ""
    resume_requirements: list[str] = field(default_factory=list)

    def mark_healthy(self) -> None:
        self.status = ProviderStatus.HEALTHY
        self.last_health_check_at = datetime.now(UTC)

    def mark_blocked(self, status: ProviderStatus, reason: str) -> None:
        self.status = status
        self.blocked_reason = reason
        self.last_health_check_at = datetime.now(UTC)

    def is_healthy(self) -> bool:
        return self.status == ProviderStatus.HEALTHY

    def is_blocked(self) -> bool:
        return self.status in (
            ProviderStatus.BLOCKED_QUOTA,
            ProviderStatus.BLOCKED_CREDIT,
            ProviderStatus.BLOCKED_AUTH,
            ProviderStatus.BLOCKED_OUTAGE,
            ProviderStatus.DISABLED_BY_USER,
        )


@dataclass
class ProviderHealthTracker:
    """Tracks health for all registered providers."""

    providers: dict[str, ProviderHealth] = field(default_factory=dict)

    def register(self, provider_id: str) -> ProviderHealth:
        if provider_id not in self.providers:
            self.providers[provider_id] = ProviderHealth(provider_id=provider_id)
        return self.providers[provider_id]

    def get(self, provider_id: str) -> ProviderHealth | None:
        return self.providers.get(provider_id)

    def all_healthy(self) -> bool:
        return all(p.is_healthy() for p in self.providers.values())

    def blocked_providers(self) -> list[ProviderHealth]:
        return [p for p in self.providers.values() if p.is_blocked()]

    def record_successful_job(self, provider_id: str) -> None:
        health = self.get(provider_id)
        if health:
            health.last_successful_job_at = datetime.now(UTC)
