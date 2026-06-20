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
    from film_pipeline.app.bootstrap import validate_environment
    from film_pipeline.kb.paths import kb_manifest_path

    status = HealthStatus()
    env_issues = validate_environment()
    status.checks["bootstrap"] = len(env_issues) == 0
    if env_issues:
        status.messages.extend(env_issues)

    # Check provider health
    from film_pipeline.app.runtime import get_runtime

    rt = get_runtime()
    provider_ids = rt.list_providers()
    if provider_ids:
        all_healthy = True
        for pid in provider_ids:
            h = rt.get_provider_health(pid)
            if h and h.get("status") != "healthy":
                all_healthy = False
                status.messages.append(f"Provider '{pid}' status: {h['status']}")
        status.checks["providers"] = all_healthy
    else:
        status.checks["providers"] = True  # No providers = no failures

    # Check KB
    status.checks["kb"] = kb_manifest_path().exists()
    if not status.checks["kb"]:
        status.messages.append("KB manifest not found.")

    status.ready = all(status.checks.values())
    return status
