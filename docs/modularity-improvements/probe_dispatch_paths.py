"""Show that the CLI's direct handler path skips the MCP dispatch checks.

Run from the repository root (profiles resolve relative to it):

    FILM_PIPELINE_NO_PERSIST=1 uv run python docs/modularity-improvements/probe_dispatch_paths.py

Expected on 2450616: path A returns typed errors; path B raises on the missing
project and advances a human gate without ``confirmed``.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from film_pipeline.cli.driver import HeadlessDriver
from film_pipeline.mcp.server import MCPServer


async def main() -> None:
    rt = HeadlessDriver.setup_runtime("mock", Path(tempfile.mkdtemp()))
    driver = HeadlessDriver(rt, "probe")
    server = MCPServer()

    resp = await server.call("get_blockers", {})
    print("A  get_blockers, no project   ->", resp.error.code if resp.error else "ok")
    try:
        await driver._call_tool("get_blockers")
        print("B  get_blockers, no project   -> ok")
    except Exception as exc:
        print("B  get_blockers, no project   -> raised", type(exc).__name__)

    resp = await server.call("approve_phase", {})
    print("A  approve_phase, unconfirmed -> ", resp.error.code if resp.error else "ok")

    await driver._call_tool(
        "create_film_project", project_id="probe", title="Probe", slug="probe", runtime_mode="mock"
    )
    await driver._call_tool("set_active_project", project_ref="probe")
    await driver._call_tool("submit_idea", idea="A lighthouse keeper finds a door in the sea.")
    before = rt.get_project("probe")["current_phase"]  # type: ignore[index]
    result = await driver._call_tool("approve_phase")
    after = rt.get_project("probe")["current_phase"]  # type: ignore[index]
    print(f"B  approve_phase, unconfirmed -> ok={result.get('ok')} phase {before} -> {after}")


if __name__ == "__main__":
    asyncio.run(main())
