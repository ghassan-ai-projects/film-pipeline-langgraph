"""Runtime context — holds the operational state for MCP tools.

This is the bridge between the MCP tool surface and the LangGraph backend.
In production, this would be a proper session/process manager.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StudioRuntime:
    """Operational state for the film studio runtime.

    Holds active project state, graph instance, and registries.
    MCP tools read and write through this context.
    """

    projects: dict[str, dict[str, Any]] = field(default_factory=dict)
    active_project_id: str = ""
    graph: Any = None  # CompiledStateGraph

    def create_project(self, project_id: str, title: str = "", slug: str = "") -> dict[str, Any]:
        if project_id in self.projects:
            raise ValueError(f"Project '{project_id}' already exists.")
        state: dict[str, Any] = {
            "project_id": project_id,
            "title": title,
            "slug": slug or project_id,
            "current_phase": "",
            "approved": False,
            "human_approval_required": False,
            "human_approval_phase": "",
            "issues": [],
        }
        self.projects[project_id] = state
        return state

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self.projects.get(project_id)

    def set_active(self, project_id: str) -> None:
        if project_id not in self.projects:
            raise ValueError(f"Project '{project_id}' not found.")
        self.active_project_id = project_id

    def get_active(self) -> dict[str, Any] | None:
        if not self.active_project_id:
            return None
        return self.projects.get(self.active_project_id)

    def ensure_graph(self) -> Any:
        """Lazy-load and cache the graph instance."""
        if self.graph is None:
            from film_pipeline.graph.graph import build_graph

            self.graph = build_graph()
        return self.graph

    def run_graph(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the graph with the given state, streaming results.

        The graph will cycle through approval gates without human intervention,
        so we run with a low recursion limit and capture the latest state.
        """
        graph = self.ensure_graph()
        from langgraph.errors import GraphRecursionError

        try:
            return graph.invoke(  # type: ignore[no-any-return]
                state,
                config={"recursion_limit": 3},
            )
        except GraphRecursionError:
            # Fall back to streaming to get the latest state
            latest: dict[str, Any] = dict(state)
            try:
                for event in graph.stream(
                    state,
                    config={"recursion_limit": 3},
                    stream_mode="values",
                ):
                    latest = dict(event)
            except GraphRecursionError:
                pass
            return latest

    def approve_phase(self) -> dict[str, Any]:
        """Approve the current phase and advance."""
        active = self.get_active()
        if not active:
            raise ValueError("No active project.")
        from film_pipeline.graph.nodes import approve_phase_node

        result = approve_phase_node(active)
        self.projects[active["project_id"]] = result
        return result

    def request_revision(self, note: str = "") -> dict[str, Any]:
        """Request revision of the current phase."""
        active = self.get_active()
        if not active:
            raise ValueError("No active project.")
        from film_pipeline.graph.nodes import request_revision_node

        result = request_revision_node(active)
        if note:
            result["issues"][-1]["note"] = note
        self.projects[active["project_id"]] = result
        return result


# Global singleton for MCP tools
_RUNTIME = StudioRuntime()


def get_runtime() -> StudioRuntime:
    return _RUNTIME
