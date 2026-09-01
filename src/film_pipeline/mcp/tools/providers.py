"""Provider health and listing tools."""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg

from .helpers import _error, _ok


async def check_provider_health(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    provider_id = str(args.get("provider_id", "")).strip()
    if not provider_id:
        provider_ids = rt.list_providers()
        if rt.server_mode == "mock" and not provider_ids:
            provider_id = "mock-video-provider"
        elif provider_ids:
            provider_id = provider_ids[0]
        else:
            return _error("provider_id is required when no providers are registered.")
    health = rt.get_provider_health(provider_id)
    if health is None:
        return _ok(provider_id=provider_id, status="unknown", message="No health data recorded.")
    return _ok(provider_id=provider_id, status=health["status"], reason=health.get("reason", ""))


async def resolve_provider_block(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    provider_id = str(args.get("provider_id", ""))
    if not provider_id:
        return _error("provider_id is required")
    rt.set_provider_health(provider_id, "healthy")
    return _ok(provider_id=provider_id, status="healthy")


async def list_providers(args: dict[str, object]) -> dict[str, object]:
    rt = tools_pkg.get_runtime()
    # Include model-provider health rows (for example z.ai) alongside media
    # adapters. Model adapters intentionally do not implement the media
    # provider contract, so they remain health-only entries here.
    provider_ids = list(dict.fromkeys([*rt.list_providers(), *rt.get_all_health()]))
    result = []
    for pid in provider_ids:
        health = rt.get_provider_health(pid)
        result.append(
            {
                "provider_id": pid,
                "status": health["status"] if health else "unknown",
            }
        )
    if not result and rt.server_mode == "mock":
        result.append({"provider_id": "mock-video-provider", "status": "healthy"})
    return _ok(providers=result, total=len(result))
