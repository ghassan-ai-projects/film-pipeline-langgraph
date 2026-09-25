"""Health checks for readiness and dependency health."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HealthStatus:
    """Aggregate health status for the studio runtime."""

    ready: bool = False
    checks: dict[str, bool] = field(default_factory=dict)
    messages: list[str] = field(default_factory=list)


def check_readiness() -> HealthStatus:
    """Run all health checks and return aggregate status."""
    status = HealthStatus()
    _record_bootstrap_status(status)
    _record_provider_status(status)
    _record_kb_status(status)
    status.ready = all(status.checks.values())
    return status


def _record_bootstrap_status(status: HealthStatus) -> None:
    """Record whether the environment passes bootstrap validation."""
    from film_pipeline.studio.bootstrap import validate_environment

    env_issues = validate_environment()
    status.checks["bootstrap"] = len(env_issues) == 0
    status.messages.extend(env_issues)


def _record_provider_status(status: HealthStatus) -> None:
    """Record whether every registered provider reports healthy."""
    from film_pipeline.studio.runtime import get_runtime

    rt = get_runtime()
    provider_ids = rt.list_providers()
    if not provider_ids:
        status.checks["providers"] = True  # No providers = no failures
        return
    all_healthy = True
    for pid in provider_ids:
        h = rt.get_provider_health(pid)
        if h and h.get("status") != "healthy":
            all_healthy = False
            status.messages.append(f"Provider '{pid}' status: {h['status']}")
    status.checks["providers"] = all_healthy


def _record_kb_status(status: HealthStatus) -> None:
    """Record whether the knowledge-base manifest is present."""
    from film_pipeline.kb.paths import kb_manifest_path

    kb_manifest_present = kb_manifest_path().exists()
    status.checks["kb"] = kb_manifest_present
    if not kb_manifest_present:
        status.messages.append("KB manifest not found.")
