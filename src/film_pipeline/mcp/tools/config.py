"""Config / profile and runtime-mode tools.

The mid-project profile-change write path (``propose_profile_change`` /
``approve_profile_change``) lives in ``_profile_change``; this module
re-exports those tools so existing ``film_pipeline.mcp.tools.config``
import paths keep resolving.
"""

from __future__ import annotations

import film_pipeline.mcp.tools as tools_pkg
from film_pipeline.config.profile_resolver import load_profile_flex

from ._profile_change import approve_profile_change, propose_profile_change
from .helpers import _active_project_id, _error, _ok

__all__ = [
    "approve_profile_change",
    "get_runtime_mode",
    "inspect_profile",
    "list_profiles",
    "propose_profile_change",
]


async def list_profiles(args: dict[str, object]) -> dict[str, object]:
    """List available config profiles from the profiles/ directory."""
    from film_pipeline.config.loader import ProfileLoader

    try:
        loader = ProfileLoader()
        names = loader.all_names()
        profiles: list[dict[str, object]] = []
        for name in names:
            try:
                src = loader.load(name)
                pid = src.raw.get("profile", {}).get("id", name)
                pname = src.raw.get("profile", {}).get("name", name)
                desc = src.raw.get("profile", {}).get("description", "")
                mode = src.raw.get("studio", {}).get("mode", "unknown")
                profiles.append(
                    {
                        "id": pid,
                        "name": pname,
                        "description": desc,
                        "studio_mode": mode,
                        "file": str(src.path),
                    }
                )
            except Exception:
                continue
        return _ok(profiles=profiles, total=len(profiles))
    except Exception as e:
        return _error(str(e))


async def inspect_profile(args: dict[str, object]) -> dict[str, object]:
    """Load and return the full content of a specific profile."""
    profile_id = str(args.get("profile_id", ""))
    if not profile_id:
        return _error("profile_id is required.")

    try:
        _loader, src = load_profile_flex(profile_id, ("provider", "quality", "film-type", "review"))
        return _ok(
            profile_id=src.path.stem,
            file=str(src.path),
            raw=src.raw,
        )
    except FileNotFoundError:
        return _error(f"Profile '{profile_id}' not found.")
    except Exception as e:
        return _error(str(e))


async def get_runtime_mode(args: dict[str, object]) -> dict[str, object]:
    """Return current server mode and the active project's stored runtime mode."""
    rt = tools_pkg.get_runtime()
    project_id = _active_project_id(args, rt)
    active = rt.get_project(project_id) if project_id is not None else rt.get_active()
    project_mode = rt.server_mode
    profile_stack: dict[str, str] = {}
    if active is not None:
        project_mode = str(active.get("runtime_mode", project_mode))
        stack = active.get("profile_stack", {})
        if isinstance(stack, dict):
            profile_stack = {str(k): str(v) for k, v in stack.items()}
    if active is not None and project_mode != rt.server_mode:
        return _error(
            "Active project runtime_mode does not match the MCP server mode.",
            server_mode=rt.server_mode,
            project_runtime_mode=project_mode,
            profile_stack=profile_stack,
        )
    return _ok(
        server_mode=rt.server_mode,
        runtime_mode=project_mode,
        project_runtime_mode=project_mode if active is not None else "",
        aligned=True,
        profile_stack=profile_stack,
        profile_version=int(active.get("profile_version", 0)) if active is not None else 0,
    )
