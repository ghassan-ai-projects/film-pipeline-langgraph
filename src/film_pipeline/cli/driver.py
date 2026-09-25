"""Headless driver that runs the pipeline from a file without human gates."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from film_pipeline.app.runtime import StudioRuntime
from film_pipeline.cli.io import read_idea_file


class HeadlessDriverError(RuntimeError):
    """Raised when the headless driver cannot continue."""


@dataclass(frozen=True)
class HeadlessRunSpec:
    """Immutable request describing one headless pipeline run."""

    file_path: Path
    project_id: str
    title: str
    slug: str
    runtime_mode: str
    runtime_root: Path
    profile_stack: list[str]
    target_phase: str = "shot_bible"
    target_runtime_seconds: int | None = None
    target_scene_count: int | None = None
    constraints: dict[str, Any] | None = None


class HeadlessDriver:
    """Drive a film project from idea file through a target phase.

    The driver is intentionally thin: it reuses the existing MCP tool surface
    so behavior stays identical to the MCP workflow, and it auto-approves
    every gate so no human is required.
    """

    def __init__(
        self,
        runtime: StudioRuntime,
        project_id: str,
        target_phase: str = "shot_bible",
        max_phase_iterations: int = 30,
    ) -> None:
        self.rt = runtime
        self.project_id = project_id
        self.target_phase = target_phase
        self.max_phase_iterations = max_phase_iterations

    @classmethod
    def setup_runtime(
        cls,
        mode: str,
        runtime_root: Path,
    ) -> StudioRuntime:
        """Create and globally install a runtime for the requested mode."""
        import film_pipeline.app.runtime as rt_mod
        from film_pipeline.graph.services import GraphServices

        mode = mode.lower().strip()
        if mode not in {"mock", "real"}:
            raise HeadlessDriverError(f"runtime_mode must be 'mock' or 'real', got '{mode}'")

        artifacts_root = str(runtime_root / "artifacts")
        if mode == "real":
            services = GraphServices.for_real_runtime(artifacts_root=artifacts_root)
        else:
            from film_pipeline.app.mock_responses import default_mock_responses

            services = GraphServices.for_mock_runtime(
                artifacts_root=artifacts_root,
                mock_responses=default_mock_responses(),
            )
        rt = StudioRuntime(server_mode=mode, runtime_root=runtime_root, services=services)
        rt_mod._RUNTIME_MODE_OVERRIDE = mode
        rt_mod._RUNTIME = rt
        return rt

    async def create_project(
        self,
        title: str,
        slug: str,
        runtime_mode: str,
        profile_stack: list[str],
        target_runtime_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Create the project with the requested profile stack."""
        result = await self._call_tool(
            "create_film_project",
            project_id=self.project_id,
            title=title,
            slug=slug,
            runtime_mode=runtime_mode,
            provider_profile=profile_stack[0] if profile_stack else "",
            quality_profile=profile_stack[1] if len(profile_stack) > 1 else "",
            film_type_profile=profile_stack[2] if len(profile_stack) > 2 else "",
        )
        if not result.get("ok"):
            raise HeadlessDriverError(f"create_film_project failed: {result}")
        active = await self._call_tool("set_active_project", project_ref=self.project_id)
        if not active.get("ok"):
            raise HeadlessDriverError(f"set_active_project failed: {active}")
        if target_runtime_seconds is not None and target_runtime_seconds > 0:
            state = self.rt.get_project(self.project_id)
            if state is not None:
                state["target_runtime_seconds"] = target_runtime_seconds
        return result

    async def submit_idea_from_file(
        self,
        file_path: Path,
        target_scene_count: int | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Read the idea file and submit it to the active project."""
        idea = read_idea_file(file_path)
        args: dict[str, Any] = {"idea": idea}
        if target_scene_count is not None and target_scene_count > 0:
            args["target_scene_count"] = target_scene_count
        if constraints:
            args["constraints"] = constraints
        result = await self._call_tool("submit_idea", **args)
        if not result.get("ok"):
            raise HeadlessDriverError(f"submit_idea failed: {result}")
        return result

    async def run_to_target(self) -> dict[str, Any]:
        """Auto-approve gates until the project advances past ``target_phase``.

        Returns the runtime state after the target phase has been approved.
        Raises ``HeadlessDriverError`` if the target is not reached within
        ``max_phase_iterations`` or a tool error blocks progress.
        """
        from film_pipeline.graph.phase_sequence import PHASE_SEQUENCE

        try:
            target_index = PHASE_SEQUENCE.index(self.target_phase)
        except ValueError as exc:
            raise HeadlessDriverError(f"Unknown target phase: {self.target_phase}") from exc

        state = self._active_state()
        for _ in range(self.max_phase_iterations):
            current_phase = str(state.get("current_phase", ""))
            current_index = _phase_order_index(current_phase)

            if current_phase == self.target_phase or current_index > target_index:
                # Approve the target gate (if still waiting) and finish.
                if current_phase == self.target_phase and state.get("human_approval_required"):
                    await self._approve_gate()
                # The graph advances to the next phase on approval. For the
                # headless target contract, report the target phase as approved
                # rather than the unapproved next phase the graph landed on.
                return self._target_met_state(target_index)

            await self._approve_gate()
            state = self._active_state()

        state = self._active_state()
        current_phase = str(state.get("current_phase", ""))
        raise HeadlessDriverError(
            f"Did not reach target phase '{self.target_phase}' "
            f"after {self.max_phase_iterations} iterations. "
            f"Current phase: {current_phase}, blockers: {_blocker_summary(state)}"
        )

    def _target_met_state(self, target_index: int) -> dict[str, Any]:
        """Return a state snapshot that reports the target phase as approved.

        Does not mutate the persisted runtime state; the graph is allowed to
        keep advancing past the target internally.
        """
        state = dict(self._active_state())
        current_phase = str(state.get("current_phase", ""))
        from film_pipeline.graph.phase_sequence import PHASE_SEQUENCE

        if _phase_order_index(current_phase) > target_index:
            state["current_phase"] = PHASE_SEQUENCE[target_index]
            state["approved"] = True
            state["human_approval_required"] = False
        return state

    def _active_state(self) -> dict[str, Any]:
        state = self.rt.get_project(self.project_id)
        if state is None:
            raise HeadlessDriverError(f"Project '{self.project_id}' disappeared from runtime.")
        return state

    async def _approve_gate(self) -> None:
        """Auto-approve the current human gate, raising on tool failure."""
        result = await self._call_tool("approve_phase", confirmed=True)
        if not result.get("ok"):
            raise HeadlessDriverError(f"approve_phase failed: {result}")

    async def _call_tool(self, tool_name: str, **args: Any) -> dict[str, Any]:
        """Invoke an async MCP tool by name against the bound runtime."""
        mod = importlib.import_module("film_pipeline.mcp.tools")
        handler = getattr(mod, tool_name, None)
        if handler is None:
            raise HeadlessDriverError(f"Unknown MCP tool: {tool_name}")
        result: dict[str, Any] = await handler(dict(args))
        return result


def _phase_order_index(phase: str) -> int:
    """Return the position of ``phase`` in the sequence, or -1 when unknown."""
    from film_pipeline.graph.phase_sequence import PHASE_SEQUENCE

    try:
        return PHASE_SEQUENCE.index(phase)
    except ValueError:
        return -1


def _blocker_summary(state: dict[str, Any]) -> str:
    issues = state.get("issues", [])
    blockers = [i for i in issues if isinstance(i, dict) and i.get("severity") == "blocking"]
    if not blockers:
        return "none"
    return "; ".join(str(b.get("message", b.get("code", "unknown"))) for b in blockers)


async def run_headless(spec: HeadlessRunSpec) -> dict[str, Any]:
    """High-level helper: create runtime, project, submit idea, and run to target.

    This is the synchronous-friendly entry point used by the CLI.
    """
    rt = HeadlessDriver.setup_runtime(spec.runtime_mode, spec.runtime_root)
    driver = HeadlessDriver(rt, spec.project_id, target_phase=spec.target_phase)
    await driver.create_project(
        title=spec.title,
        slug=spec.slug,
        runtime_mode=spec.runtime_mode,
        profile_stack=spec.profile_stack,
        target_runtime_seconds=spec.target_runtime_seconds,
    )
    await driver.submit_idea_from_file(
        spec.file_path,
        target_scene_count=spec.target_scene_count,
        constraints=spec.constraints,
    )
    return await driver.run_to_target()
