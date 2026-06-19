"""Runtime metrics — durations, counts, success rates, cost tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from statistics import mean


@dataclass
class MetricPoint:
    """A single metric data point."""

    name: str
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricsCollector:
    """Collects runtime metrics across all subsystems.

    In production, this would feed a Prometheus/Grafana stack.
    """

    points: list[MetricPoint] = field(default_factory=list)

    def record(self, name: str, value: float, **tags: str) -> None:
        self.points.append(MetricPoint(name=name, value=value, tags=dict(tags)))

    def phase_duration(self, phase: str, duration_ms: float, project_id: str) -> None:
        self.record("phase_duration_ms", duration_ms, phase=phase, project_id=project_id)

    def agent_call(self, agent_id: str, success: bool, duration_ms: float) -> None:
        self.record(
            "agent_call",
            1.0 if success else 0.0,
            agent=agent_id,
            outcome="success" if success else "failure",
        )
        self.record("agent_duration_ms", duration_ms, agent=agent_id)

    def validation_score(self, validator_id: str, score: float) -> None:
        self.record("validation_score", score, validator=validator_id)

    def provider_job(self, provider_id: str, success: bool, cost_usd: float) -> None:
        self.record(
            "provider_job",
            1.0 if success else 0.0,
            provider=provider_id,
            outcome="success" if success else "failure",
        )
        self.record("provider_cost_usd", cost_usd, provider=provider_id)

    def cost_tracking(self, project_id: str, estimated: float, actual: float) -> None:
        self.record("cost_estimated_usd", estimated, project_id=project_id)
        self.record("cost_actual_usd", actual, project_id=project_id)

    def agent_success_rate(self, agent_id: str) -> float | None:
        calls = [
            p for p in self.points if p.name == "agent_call" and p.tags.get("agent") == agent_id
        ]
        if not calls:
            return None
        return mean(p.value for p in calls)

    def total_provider_cost(self) -> float:
        return sum(p.value for p in self.points if p.name == "provider_cost_usd")
