"""Runtime context — holds the operational state for MCP tools.

This is the bridge between the MCP tool surface and the LangGraph backend.
In production, this would be a proper session/process manager.
"""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.graph.router import PHASE_ORDER
from film_pipeline.graph.services import GraphServices
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
    server_mode: str = "mock"
    services: GraphServices | None = None
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

    def __post_init__(self) -> None:
        self.server_mode = _normalize_server_mode(self.server_mode)
        if self.services is None:
            self.services = _build_services_for_mode(self.server_mode)

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
            "server_mode": self.server_mode,
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
        """Run the graph with the given state.

        Supplies ``GraphServices`` through runtime context before invocation
        so checkpoints never need to serialize service objects.

        With LangGraph ``interrupt()`` + checkpointer, the graph pauses at
        human gates and resumes via ``graph.invoke(Command(...), config)``.
        No recursion-limit workaround needed.

        Persists graph state to disk for crash recovery (Phase 7+ P0).
        """
        graph = self.ensure_graph()

        state = dict(state)

        # Set context-var fallback so nodes can find services without storing
        # runtime dependencies in checkpointed graph state.
        import film_pipeline.graph.nodes as _gn

        token = _gn._SERVICES_CTX.set(self.services)
        try:
            config: dict[str, Any] = {
                "configurable": {
                    "thread_id": state.get("project_id", "default"),
                    "services": self.services,
                },
                "recursion_limit": 50,  # 10 phases x ~3 steps each + repair headroom
            }
            result: dict[str, Any] = cast(dict[str, Any], graph.invoke(state, config))
        finally:
            _gn._SERVICES_CTX.reset(token)
        pid = str(result.get("project_id", ""))
        if pid:
            self._save_graph_state(dict(result), pid)
            self._auto_checkpoint(result)
        return result

    def _auto_checkpoint(self, state: dict[str, Any]) -> None:
        """Create a checkpoint after a graph step completes."""
        project_id = str(state.get("project_id", ""))
        if not project_id or project_id not in self.projects:
            return
        manager = self.checkpoint_managers.get(project_id)
        if manager is None:
            return
        phase = str(state.get("current_phase", "") or "intake")
        if not phase:
            return

        graph_state_ref = ""
        if self.services is not None:
            store = self.services.artifact_store
            try:
                from datetime import UTC, datetime

                from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
                from film_pipeline.schemas.artifact import ArtifactMetadata
                from film_pipeline.schemas.checkpoint import CheckpointState

                version = store.next_version(project_id, "intake", "graph_state")
                meta = ArtifactMetadata(
                    artifact_id="graph_state",
                    artifact_type=ArtifactType.CHECKPOINT,
                    project_id=project_id,
                    phase=FilmPhase("intake"),
                    version=version,
                    status=ArtifactStatus.CANDIDATE,
                    created_by="runtime_auto_checkpoint",
                    created_at=datetime.now(UTC),
                )
                safe_state = {k: v for k, v in state.items() if not k.startswith("_services")}
                store.save(CheckpointState(state=safe_state), meta)
                graph_state_ref = f"artifact:graph_state:v{version}"
            except Exception:
                pass

        from film_pipeline.graph.orchestrator_state import get_candidate_refs

        candidate_refs = get_candidate_refs(state)
        artifact_versions = dict(candidate_refs)

        with contextlib.suppress(Exception):
            self.create_checkpoint(
                project_id=project_id,
                phase=phase,
                reason="auto: graph step completed",
                artifact_versions=artifact_versions,
                graph_state_ref=graph_state_ref,
            )

    def _save_graph_state(self, state: dict[str, Any], project_id: str) -> None:
        """Persist graph state to disk for crash recovery."""
        root = self.project_roots.get(project_id)
        if root is None:
            return
        root.mkdir(parents=True, exist_ok=True)
        state_path = root / ".graph_state.json"
        safe = {k: v for k, v in state.items() if not k.startswith("_services")}
        state_path.write_text(json.dumps(safe, indent=2, sort_keys=True, default=str))

    def approve_phase(self) -> dict[str, Any]:
        """Approve the current phase and advance.

        Resumes the graph via ``Command(resume={"action": "approve"})``
        when a checkpoint exists. Falls back to manual phase advance
        when no graph checkpoint has been created (e.g. after direct
        ``_run_phase_node`` calls).
        """
        from langgraph.types import Command

        active = self.get_active()
        if not active:
            raise ValueError("No active project.")

        current_phase = str(active.get("current_phase", ""))
        if not current_phase:
            raise ValueError("No active phase to approve.")

        graph = self.ensure_graph()
        config: dict[str, Any] = {
            "configurable": {"thread_id": active["project_id"], "services": self.services},
        }

        # Set the services context variable so graph nodes can find
        # GraphServices without checkpointing runtime objects.
        import film_pipeline.graph.nodes as _gn

        token = _gn._SERVICES_CTX.set(self.services)
        try:
            state = graph.invoke(
                Command(resume=_build_resume_payload("approve", active)),
                config,
            )
            _preserve_external_generation_requests(state, active)
            _strip_stale_generation_request_blockers(state)
            if not _approval_made_progress(
                state, current_phase
            ) or _has_stale_generation_request_blocker(state, active):
                state = self._advance_to_next_phase(dict(active))
        except Exception:
            # No checkpoint exists — advance manually via phase nodes
            state = self._advance_to_next_phase(dict(active))
        finally:
            _gn._SERVICES_CTX.reset(token)
        state = cast(dict[str, Any], state)

        self.projects[active["project_id"]] = state
        self._persist_project_state(active["project_id"])
        self._save_graph_state(dict(state), active["project_id"])

        checkpoint = self.create_checkpoint(
            project_id=active["project_id"],
            phase=str(state.get("current_phase", "")),
            reason=f"Approved at {current_phase}",
        )

        self._record_audit(
            "human",
            "approve_phase",
            project_id=active["project_id"],
            phase=current_phase,
            next_phase=str(state.get("current_phase", "")),
            checkpoint_id=checkpoint.checkpoint_id,
        )
        return state

    def run_validation(self, project_id: str | None = None) -> dict[str, Any]:
        """Run validators against the active project's current-phase artifacts.

        Executes the same validator dispatch the QC node uses, but against the
        live project state and *without* advancing the phase. Validator-produced
        findings replace any prior validator findings (issues tagged with a
        ``validator_id``) while non-validator blockers are preserved, then the
        refreshed issues and validation reports are merged back and persisted.
        """
        from film_pipeline.graph.nodes import _run_validators
        from film_pipeline.graph.services import SERVICES_KEY

        active = self.get_project(project_id) if project_id else self.get_active()
        if active is None:
            raise ValueError("No active project.")
        project_id_value = str(active["project_id"])

        preserved_issues = [
            issue
            for issue in cast(list[dict[str, Any]], active.get("issues", []))
            if not (isinstance(issue, dict) and issue.get("validator_id"))
        ]
        working = dict(active)
        working[SERVICES_KEY] = self.services
        working["issues"] = list(preserved_issues)
        working["_validation_reports"] = []
        working.pop("_pending_row_updates", None)
        _run_validators(working)
        working.pop(SERVICES_KEY, None)

        active["issues"] = list(working.get("issues", []))
        active["_validation_reports"] = list(working.get("_validation_reports", []))
        consensus_ref = working.get("consensus_report_ref")
        if consensus_ref:
            active["consensus_report_ref"] = consensus_ref
        self.projects[project_id_value] = active
        self._persist_project_state(project_id_value)
        self._record_audit(
            "human",
            "run_validation",
            project_id=project_id_value,
            phase=str(active.get("current_phase", "")),
        )
        return active

    def request_revision(self, note: str = "") -> dict[str, Any]:
        """Request revision of the current phase.

        Resumes the graph via ``Command(resume={"action": "revise"})``.
        The graph routes to repair automatically.
        """
        from langgraph.types import Command

        active = self.get_active()
        if not active:
            raise ValueError("No active project.")

        graph = self.ensure_graph()
        config: dict[str, Any] = {
            "configurable": {"thread_id": active["project_id"], "services": self.services},
        }

        import film_pipeline.graph.nodes as _gn

        token = _gn._SERVICES_CTX.set(self.services)
        try:
            state = graph.invoke(
                Command(resume=_build_resume_payload("revise", active, note=note)),
                config,
            )
        finally:
            _gn._SERVICES_CTX.reset(token)
        state = cast(dict[str, Any], state)

        self.projects[active["project_id"]] = state
        self._persist_project_state(active["project_id"])
        self._save_graph_state(dict(state), active["project_id"])

        self._record_audit(
            "human",
            "request_revision",
            project_id=active["project_id"],
            note=note,
        )
        return state

    # --- Checkpoints ---

    def create_checkpoint(
        self,
        project_id: str,
        phase: str,
        reason: str,
        *,
        artifact_versions: dict[str, str] | None = None,
        graph_state_ref: str = "",
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
            artifact_versions=artifact_versions,
            graph_state_ref=graph_state_ref,
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

    # --- Operator comments ---

    def add_operator_comment(
        self,
        project_id: str,
        *,
        target_type: str,
        target_id: str,
        body: str,
        phase: str = "",
        source: str = "tui",
    ) -> dict[str, Any]:
        """Persist an operator comment on a project target."""
        project = self.projects.get(project_id)
        if project is None:
            raise ValueError(f"Project '{project_id}' not found.")
        comment = {
            "comment_id": f"comment:{uuid4().hex[:8]}",
            "project_id": project_id,
            "target_type": target_type,
            "target_id": target_id,
            "body": body,
            "phase": phase,
            "source": source,
            "created_at": datetime.now(UTC).isoformat(),
            "resolved": False,
        }
        project.setdefault("_operator_comments", []).append(comment)
        self._persist_project_state(project_id)
        self._record_audit(
            "human",
            "add_operator_comment",
            project_id=project_id,
            target_type=target_type,
            target_id=target_id,
            phase=phase,
        )
        return comment

    def list_operator_comments(
        self,
        project_id: str,
        *,
        include_resolved: bool = False,
    ) -> list[dict[str, Any]]:
        """Return operator comments for a project."""
        project = self.projects.get(project_id)
        if project is None:
            raise ValueError(f"Project '{project_id}' not found.")
        comments = [
            comment
            for comment in cast(list[dict[str, Any]], project.get("_operator_comments", []))
            if include_resolved or not comment.get("resolved", False)
        ]
        return list(comments)

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

    def clear_providers(self) -> None:
        self.provider_adapters.clear()
        self.provider_health.clear()

    # --- Provider health ---

    def set_provider_health(self, provider_id: str, status: str, reason: str = "") -> None:
        self.provider_health[provider_id] = {"status": status, "reason": reason}

    def get_provider_health(self, provider_id: str) -> dict[str, Any] | None:
        return self.provider_health.get(provider_id)

    def get_all_health(self) -> dict[str, dict[str, Any]]:
        return dict(self.provider_health)

    def seed_default_provider_health(self) -> None:
        """Seed provider health rows for the configured runtime mode.

        Mock mode advertises the zero-cost mock providers as healthy. Real mode
        advertises the live generation providers, marking each healthy only when
        its API credentials are configured so the operator can see at a glance
        what is wired up. Existing health entries are never overwritten.
        """
        if self.provider_health:
            return
        if self.server_mode == "real":
            from film_pipeline.providers import credentials

            for provider_id in ("seedance-openrouter", "veo-fast", "gemini-imagen-4"):
                if credentials.is_configured(provider_id):
                    self.set_provider_health(provider_id, "healthy")
                else:
                    self.set_provider_health(
                        provider_id,
                        "unconfigured",
                        "API credentials not set",
                    )
            return
        for provider_id in ("mock-image-provider", "mock-video-provider"):
            self.set_provider_health(provider_id, "healthy", "mock runtime")

    def _persist_project_state(self, project_id: str) -> None:
        project = self.projects[project_id]
        project_root = self.project_roots[project_id]
        project_root.mkdir(parents=True, exist_ok=True)
        state_path = project_root / STATE_FILENAME
        state_path.write_text(json.dumps(project, indent=2, sort_keys=True, default=str))

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
        from film_pipeline.graph.services import SERVICES_KEY

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
        # Inject graph services so nodes can invoke agents and persist artifacts
        state = dict(state)
        state[SERVICES_KEY] = self.services
        node_result = node(state)
        # Merge node result back into state (graph would do this via reducers,
        # but direct node calls bypass the graph's state accumulation)
        merged = dict(state)
        merged.update(node_result)
        # Append-only channels: merge lists manually (graph uses Annotated[list, add])
        for key in (
            "artifact_refs",
            "issues",
            "validation_report_refs",
            "generation_requests",
            "_routing_decisions",
            "_validation_reports",
        ):
            prev = state.get(key, [])
            new = node_result.get(key, [])
            if new:
                merged[key] = list(prev) + list(new)
        # Strip runtime-only keys that must not leak into persisted state
        merged.pop(SERVICES_KEY, None)
        return merged


def create_runtime(server_mode: str | None = None) -> StudioRuntime:
    """Create a runtime aligned to the requested or configured server mode."""
    mode = _normalize_server_mode(server_mode or _configured_server_mode())
    return StudioRuntime(server_mode=mode)


def reset_runtime(server_mode: str | None = None) -> StudioRuntime:
    """Recreate the global runtime, primarily for tests and mode changes."""
    global _RUNTIME, _RUNTIME_MODE_OVERRIDE
    _RUNTIME_MODE_OVERRIDE = (
        _normalize_server_mode(server_mode) if server_mode is not None else None
    )
    _RUNTIME = create_runtime(server_mode)
    return _RUNTIME


def get_runtime() -> StudioRuntime:
    global _RUNTIME
    configured_mode = _configured_server_mode()
    if _RUNTIME is None or _RUNTIME.server_mode != configured_mode:
        _RUNTIME = create_runtime(configured_mode)
        _RUNTIME.seed_default_provider_health()
    return _RUNTIME


def _build_services_for_mode(server_mode: str) -> GraphServices:
    if server_mode == "real":
        return GraphServices.for_real_runtime()
    return GraphServices.for_mock_runtime()


def _normalize_server_mode(server_mode: str) -> str:
    mode = server_mode.strip().lower()
    if mode not in {"mock", "real"}:
        raise ValueError(f"server_mode must be 'mock' or 'real', got '{server_mode}'")
    return mode


def _approval_made_progress(state: dict[str, Any], previous_phase: str) -> bool:
    """Return whether a graph approval resume changed phase or intentionally blocked."""
    if state.get("completed"):
        return True
    if state.get("_approval_blocked_by_issues"):
        return True
    issues = state.get("issues", [])
    if isinstance(issues, list) and any(
        isinstance(issue, dict) and issue.get("severity") == "blocking" for issue in issues
    ):
        return True
    current_phase = str(state.get("current_phase", ""))
    if current_phase == previous_phase:
        return False
    if current_phase in PHASE_ORDER and previous_phase in PHASE_ORDER:
        return PHASE_ORDER.index(current_phase) > PHASE_ORDER.index(previous_phase)
    return bool(current_phase)


def _has_stale_generation_request_blocker(
    resumed_state: dict[str, Any],
    active_state: dict[str, Any],
) -> bool:
    """Detect graph checkpoints that predate externally planned generation requests."""
    if str(active_state.get("current_phase", "")) != "generation":
        return False
    if not active_state.get("generation_requests"):
        return False
    if resumed_state.get("generation_requests"):
        return False
    issues = resumed_state.get("issues", [])
    if not isinstance(issues, list):
        return False
    stale_codes = {"empty_generation_requests", "no_generation_requests"}
    return any(isinstance(issue, dict) and issue.get("code") in stale_codes for issue in issues)


def _preserve_external_generation_requests(
    resumed_state: dict[str, Any],
    active_state: dict[str, Any],
) -> None:
    """Carry generation requests created by MCP tools across graph checkpoint resumes."""
    if resumed_state.get("generation_requests"):
        return
    generation_requests = active_state.get("generation_requests")
    if generation_requests:
        resumed_state["generation_requests"] = generation_requests


def _strip_stale_generation_request_blockers(state: dict[str, Any]) -> None:
    """Remove generated request-missing blockers after requests are restored."""
    if not state.get("generation_requests"):
        return
    issues = state.get("issues", [])
    if not isinstance(issues, list):
        return
    stale_codes = {"empty_generation_requests", "no_generation_requests"}
    state["issues"] = [
        issue
        for issue in issues
        if not (isinstance(issue, dict) and issue.get("code") in stale_codes)
    ]


def _build_resume_payload(
    action: str,
    active: dict[str, Any],
    note: str = "",
) -> dict[str, Any]:
    """Build a Command resume payload, carrying external MCP state into the graph.

    MCP tools such as ``plan_generation_batch`` update the active project state
    after the graph checkpoint was created. Without replaying those mutations,
    a resumed checkpoint sees stale state (e.g. empty generation requests) and
    loops on repair. The ``_external_state`` key is applied by ``await_approval_node``
    before the approval/revision action is processed.
    """
    payload: dict[str, Any] = {"action": action}
    if note:
        payload["note"] = note
    external_state: dict[str, Any] = {}
    generation_requests = active.get("generation_requests")
    if generation_requests:
        external_state["generation_requests"] = generation_requests
    if external_state:
        payload["_external_state"] = external_state
    return payload


def _configured_server_mode() -> str:
    if _RUNTIME_MODE_OVERRIDE is not None:
        return _RUNTIME_MODE_OVERRIDE
    return _normalize_server_mode(os.getenv("FILM_PIPELINE_MCP_MODE", "mock"))


# Global singleton for MCP tools
_RUNTIME: StudioRuntime | None = None
_RUNTIME_MODE_OVERRIDE: str | None = None
