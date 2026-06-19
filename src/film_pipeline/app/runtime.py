"""Runtime context — holds the operational state for MCP tools.

This is the bridge between the MCP tool surface and the LangGraph backend.
In production, this would be a proper session/process manager.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.graph.router import PHASE_ORDER
from film_pipeline.graph.services import SERVICES_KEY, GraphServices
from film_pipeline.schemas._base import FilmPhase
from film_pipeline.schemas.checkpoint import CheckpointMetadata

STATE_FILENAME = "project-state.json"


@dataclass
class StudioRuntime:
    """Operational state for the film studio runtime.

    Holds active project state, graph instance, checkpoints, audit trail,
    and provider registries. MCP tools read and write through this context.
    """

    projects: dict[str, dict[str, Any]] = field(default_factory=dict)
    active_project_id: str = ""
    graph: Any = None  # CompiledStateGraph
    services: GraphServices = field(default_factory=GraphServices)
    checkpoints: dict[str, CheckpointMetadata] = field(default_factory=dict)
    audit_events: list[dict[str, Any]] = field(default_factory=list)
    block_entries: list[dict[str, str]] = field(default_factory=list)
    provider_adapters: dict[str, Any] = field(default_factory=dict)
    provider_health: dict[str, Any] = field(default_factory=dict)
    project_roots: dict[str, Path] = field(default_factory=dict)
    checkpoint_managers: dict[str, CheckpointManager] = field(default_factory=dict)
    runtime_root: Path = field(
        default_factory=lambda: Path(tempfile.gettempdir()) / "film_pipeline_runtime"
    )

    # --- Project management ---

    def create_project(self, project_id: str, title: str = "", slug: str = "") -> dict[str, Any]:
        if project_id in self.projects:
            raise ValueError(f"Project '{project_id}' already exists.")
        project_root = self.runtime_root / f"{project_id}-{uuid4().hex[:8]}"
        git = GitBackend.init_temp(project_root)
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
        self.project_roots[project_id] = project_root
        self.checkpoint_managers[project_id] = CheckpointManager(git)
        self._persist_project_state(project_id)
        git.commit("project: initialize runtime state", [STATE_FILENAME])
        self._record_audit("system", "create_project", project_id=project_id)
        return state

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self.projects.get(project_id)

    def set_active(self, project_id: str) -> None:
        if project_id not in self.projects:
            raise ValueError(f"Project '{project_id}' not found.")
        self.active_project_id = project_id
        self._record_audit("system", "set_active", project_id=project_id)

    def get_active(self) -> dict[str, Any] | None:
        if not self.active_project_id:
            return None
        return self.projects.get(self.active_project_id)

    # --- Graph ---

    def ensure_graph(self) -> Any:
        """Lazy-load and cache the graph instance."""
        if self.graph is None:
            from film_pipeline.graph.graph import build_graph

            self.graph = build_graph()
        return self.graph

    def run_graph(self, state: dict[str, Any]) -> dict[str, Any]:
        """Run the graph with the given state, streaming results.

        Injects ``GraphServices`` into state before invocation so nodes can
        access agents, artifact store, and validators.
        """
        graph = self.ensure_graph()
        from langgraph.errors import GraphRecursionError

        # Inject graph services so nodes can invoke agents and persist artifacts
        state = dict(state)
        state[SERVICES_KEY] = self.services

        try:
            return graph.invoke(  # type: ignore[no-any-return]
                state,
                config={
                    "recursion_limit": 50,
                    "configurable": {"thread_id": state.get("project_id", "default")},
                },
            )
        except GraphRecursionError:
            latest: dict[str, Any] = dict(state)
            try:
                for event in graph.stream(
                    state,
                    config={
                        "recursion_limit": 50,
                        "configurable": {"thread_id": state.get("project_id", "default")},
                    },
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
        current_phase = str(active.get("current_phase", ""))
        if not current_phase:
            raise ValueError("No active phase to approve.")
        approved_state = self._approve_current_phase(active)
        checkpoint = self.create_checkpoint(
            project_id=active["project_id"],
            phase=current_phase,
            reason=f"Approved {current_phase}",
        )
        result = self._advance_to_next_phase(approved_state)
        self._record_audit(
            "human",
            "approve_phase",
            project_id=active["project_id"],
            phase=current_phase,
            next_phase=str(result.get("current_phase", "")),
            checkpoint_id=checkpoint.checkpoint_id,
        )
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
        self._persist_project_state(active["project_id"])
        self._record_audit(
            "human",
            "request_revision",
            project_id=active["project_id"],
            note=note,
        )
        return result

    # --- Checkpoints ---

    def create_checkpoint(
        self,
        project_id: str,
        phase: str,
        reason: str,
    ) -> CheckpointMetadata:
        project = self.projects.get(project_id)
        if project is None:
            raise ValueError(f"Project '{project_id}' not found.")
        manager = self.checkpoint_managers.get(project_id)
        if manager is None:
            raise ValueError(f"Checkpoint manager for project '{project_id}' not found.")
        self._persist_project_state(project_id)
        meta = manager.create(
            project_id=project_id,
            phase=FilmPhase(phase or "intake"),
            reason=reason,
        )
        self.checkpoints[meta.checkpoint_id] = meta
        self._record_audit(
            "system",
            "create_checkpoint",
            project_id=project_id,
            checkpoint_id=meta.checkpoint_id,
            phase=phase,
        )
        return meta

    def list_checkpoints(self, project_id: str | None = None) -> list[CheckpointMetadata]:
        if project_id:
            return [c for c in self.checkpoints.values() if c.project_id == project_id]
        return list(self.checkpoints.values())

    def get_checkpoint(self, checkpoint_id: str) -> CheckpointMetadata | None:
        return self.checkpoints.get(checkpoint_id)

    # --- Audit ---

    def _record_audit(self, actor: str, action: str, **details: str) -> None:
        self.audit_events.append(
            {
                "event_id": f"audit:{action}:{uuid4().hex[:8]}",
                "timestamp": datetime.now(UTC).isoformat(),
                "actor": actor,
                "action": action,
                "details": details,
            }
        )

    def get_audit_log(
        self, project_id: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        events = self.audit_events
        if project_id:
            events = [e for e in events if e.get("details", {}).get("project_id") == project_id]
        return events[-limit:]

    # --- Blockers ---

    def get_blockers(self, project_id: str) -> list[dict[str, str]]:
        return [b for b in self.block_entries if b.get("project_id") == project_id]

    def add_blocker(
        self, project_id: str, phase: str, reason: str, severity: str = "blocking"
    ) -> None:
        self.block_entries.append(
            {
                "project_id": project_id,
                "phase": phase,
                "reason": reason,
                "severity": severity,
            }
        )

    # --- Provider registry ---

    def register_provider(self, provider_id: str, adapter: Any) -> None:
        self.provider_adapters[provider_id] = adapter

    def get_provider(self, provider_id: str) -> Any | None:
        return self.provider_adapters.get(provider_id)

    def list_providers(self) -> list[str]:
        return list(self.provider_adapters.keys())

    # --- Provider health ---

    def set_provider_health(self, provider_id: str, status: str, reason: str = "") -> None:
        self.provider_health[provider_id] = {"status": status, "reason": reason}

    def get_provider_health(self, provider_id: str) -> dict[str, Any] | None:
        return self.provider_health.get(provider_id)

    def get_all_health(self) -> dict[str, dict[str, Any]]:
        return dict(self.provider_health)

    def _persist_project_state(self, project_id: str) -> None:
        project = self.projects[project_id]
        project_root = self.project_roots[project_id]
        project_root.mkdir(parents=True, exist_ok=True)
        state_path = project_root / STATE_FILENAME
        state_path.write_text(json.dumps(project, indent=2, sort_keys=True, default=str))

    def _approve_current_phase(self, state: dict[str, Any]) -> dict[str, Any]:
        from film_pipeline.graph.nodes import approve_phase_node

        approved_state = approve_phase_node(state)
        self.projects[state["project_id"]] = approved_state
        self._persist_project_state(state["project_id"])
        return approved_state

    def _advance_to_next_phase(self, state: dict[str, Any]) -> dict[str, Any]:
        current_phase = str(state.get("current_phase", ""))
        if current_phase not in PHASE_ORDER:
            self.projects[state["project_id"]] = state
            self._persist_project_state(state["project_id"])
            return state

        current_index = PHASE_ORDER.index(current_phase)
        if current_index == len(PHASE_ORDER) - 1:
            final_state = dict(state)
            final_state["completed"] = True
            final_state["human_approval_phase"] = ""
            self.projects[state["project_id"]] = final_state
            self._persist_project_state(state["project_id"])
            return final_state

        next_phase = PHASE_ORDER[current_index + 1]
        advanced_state = self._run_phase_node(state, next_phase)
        self.projects[state["project_id"]] = advanced_state
        self._persist_project_state(state["project_id"])
        return advanced_state

    def _run_phase_node(self, state: dict[str, Any], phase: str) -> dict[str, Any]:
        from film_pipeline.graph.nodes import (
            constitution_node,
            delivery_node,
            development_node,
            gen_planning_node,
            generation_node,
            intake_node,
            post_node,
            qc_node,
            script_node,
            shot_bible_node,
            visual_dev_node,
        )

        phase_nodes = {
            "intake": intake_node,
            "constitution": constitution_node,
            "development": development_node,
            "script": script_node,
            "visual_dev": visual_dev_node,
            "shot_bible": shot_bible_node,
            "gen_planning": gen_planning_node,
            "generation": generation_node,
            "qc": qc_node,
            "post": post_node,
            "delivery": delivery_node,
        }
        node = phase_nodes[phase]
        return node(state)


# Global singleton for MCP tools
_RUNTIME = StudioRuntime()


def get_runtime() -> StudioRuntime:
    return _RUNTIME
