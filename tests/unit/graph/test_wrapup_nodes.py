"""Direct unit tests for wrapup-phase nodes (post, delivery, consistency check).

Pins the node contract that previously only had e2e coverage:
deepcopy-then-update state handling, assembly-manifest persistence and ref
wiring, human-approval gate parking, agent-failure propagation, and
staleness-warning surfacing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import film_pipeline.graph.nodes.wrapup as wrapup_module
from film_pipeline.app.mock_responses import default_mock_responses
from film_pipeline.artifacts.store import ArtifactStore
from film_pipeline.graph.nodes import consistency_check_node, delivery_node, post_node
from film_pipeline.graph.orchestrator_state import set_approved_ref
from film_pipeline.graph.services import SERVICES_KEY, GraphServices
from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
from film_pipeline.schemas.artifact import ArtifactMetadata
from film_pipeline.schemas.film_constitution import FilmConstitution


def _services(tmp_path: Path) -> GraphServices:
    return GraphServices.for_mock_runtime(
        artifacts_root=str(tmp_path / "artifacts"), mock_responses=default_mock_responses()
    )


def _post_state(services: GraphServices) -> dict[str, Any]:
    return {
        "project_id": "p1",
        "constitution_ref": "artifact:film_constitution:v1",
        "artifact_refs": ["artifact:treatment:v1"],
        SERVICES_KEY: services,
    }


def _save_constitution_version(store: ArtifactStore, project_id: str, version: int) -> str:
    constitution = FilmConstitution(
        project_id=project_id,
        theme="Hope",
        tone="grounded sci-fi",
        emotional_promise="Inspiration",
        visual_language="desaturated palette with neon accents",
        camera_philosophy="handheld intimacy",
        quality_bar="high",
    )
    meta = ArtifactMetadata(
        artifact_id="film_constitution",
        artifact_type=ArtifactType.FILM_CONSTITUTION,
        project_id=project_id,
        phase=FilmPhase("constitution"),
        version=version,
        status=ArtifactStatus.CANDIDATE,
        created_by="test",
        created_at=datetime.now(UTC),
    )
    store.save(constitution, meta)
    return f"artifact:film_constitution:v{version}"


class TestPostNodeArtifactPersistence:
    def test_persists_assembly_manifest_and_wires_refs(self, tmp_path: Path) -> None:
        services = _services(tmp_path)
        state = _post_state(services)

        updates = post_node(state)

        ref = updates["assembly_manifest_ref"]
        assert ref == "artifact:post:assembly_manifest:v1"
        # Reducer channel carries only the newly created ref, not carried-over ones.
        assert updates["artifact_refs"] == [ref]

        # The manifest was really persisted and is loadable.
        manifest = services.artifact_store.load("p1", FilmPhase("post"), "assembly_manifest", 1)
        assert manifest["cut_id"] == "review-cut-v1"
        assert len(manifest["clip_order"]) == 2

        # Provenance: built_from captures the upstream refs from the input state.
        meta = services.artifact_store.load_metadata("p1", "post", "assembly_manifest", 1)
        assert meta.built_from["film_constitution"] == "artifact:film_constitution:v1"

    def test_rerun_bumps_manifest_version_instead_of_overwriting(self, tmp_path: Path) -> None:
        services = _services(tmp_path)

        first = post_node(_post_state(services))
        second = post_node(_post_state(services))

        assert first["assembly_manifest_ref"] == "artifact:post:assembly_manifest:v1"
        assert second["assembly_manifest_ref"] == "artifact:post:assembly_manifest:v2"
        assert second["artifact_refs"] == ["artifact:post:assembly_manifest:v2"]
        v2 = services.artifact_store.load("p1", FilmPhase("post"), "assembly_manifest", 2)
        assert v2["cut_id"] == "review-cut-v1"

    def test_propagates_routing_decision_and_leaves_input_state_untouched(
        self, tmp_path: Path
    ) -> None:
        services = _services(tmp_path)
        state = _post_state(services)

        updates = post_node(state)

        routes = updates["_routing_decisions"]
        assert len(routes) == 1
        assert routes[0]["agent_id"] == "failure-handling-agent"
        assert routes[0]["phase"] == "post"
        assert "assembly_manifest" in routes[0]["output_keys"]
        # Deepcopy idiom: side effects land in updates, not in the caller's dict.
        assert "_routing_decisions" not in state


class TestPostNodeApprovalGate:
    def test_parks_at_assembly_gate_by_default(self, tmp_path: Path) -> None:
        services = _services(tmp_path)

        updates = post_node(_post_state(services))

        assert updates["current_phase"] == "post"
        assert updates["approved"] is False
        assert updates["human_approval_required"] is True
        assert updates["human_approval_phase"] == "assembly"

    def test_pre_approves_in_auto_mode(self, tmp_path: Path) -> None:
        services = _services(tmp_path)
        state = _post_state(services)
        state["resolved_config"] = {"studio": {"require_human_approval": False}}

        updates = post_node(state)

        assert updates["current_phase"] == "post"
        assert updates["approved"] is True
        assert updates["human_approval_required"] is False
        assert updates["human_approval_phase"] == "assembly"


class TestPostNodeAgentFailurePropagation:
    def test_without_services_returns_only_gate_updates(self) -> None:
        state: dict[str, Any] = {
            "project_id": "p1",
            "constitution_ref": "artifact:film_constitution:v1",
        }

        updates = post_node(state)

        assert set(updates) == {
            "current_phase",
            "approved",
            "human_approval_required",
            "human_approval_phase",
        }
        assert updates["current_phase"] == "post"
        assert updates["approved"] is False

    def test_agent_result_without_manifest_publishes_no_refs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        services = _services(tmp_path)
        requested_agents: list[str] = []

        def failing_run_agent(
            state: dict[str, Any],
            *,
            agent_id: str,
            phase: str,
            task: str,
            task_type: str = "create",
        ) -> dict[str, Any]:
            requested_agents.append(agent_id)
            return {"status": "no_impl", "agent": agent_id}

        monkeypatch.setattr(wrapup_module, "_run_agent", failing_run_agent)

        updates = post_node(_post_state(services))

        assert requested_agents == ["failure-handling-agent"]
        assert "assembly_manifest_ref" not in updates
        assert "artifact_refs" not in updates
        assert updates["current_phase"] == "post"

    def test_failed_artifact_save_wires_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        services = _services(tmp_path)

        def manifest_run_agent(
            state: dict[str, Any],
            *,
            agent_id: str,
            phase: str,
            task: str,
            task_type: str = "create",
        ) -> dict[str, Any]:
            return {"assembly_manifest": {"clip_order": []}}

        def failing_save_artifact(
            state: dict[str, Any],
            artifact: Any,
            artifact_id: str,
            phase: str,
            artifact_type: str | None = None,
            **kwargs: Any,
        ) -> None:
            _ = state, artifact, artifact_id, phase, artifact_type, kwargs

        monkeypatch.setattr(wrapup_module, "_run_agent", manifest_run_agent)
        monkeypatch.setattr(wrapup_module, "_save_artifact", failing_save_artifact)

        updates = post_node(_post_state(services))

        assert "assembly_manifest_ref" not in updates
        assert "artifact_refs" not in updates
        assert updates["current_phase"] == "post"

    def test_invalid_agent_output_raises_and_persists_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        services = _services(tmp_path)

        # An empty model output yields a manifest with no clips; AssemblyAgent's
        # validate() rejects it and the node must not swallow the failure.
        def empty_model_output(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], str, str]:
            return ({}, "template-id", "operations_triage")

        monkeypatch.setattr(services.prompt_runner, "run_from_template", empty_model_output)

        with pytest.raises(ValueError, match="failure-handling-agent"):
            post_node(_post_state(services))

        with pytest.raises(FileNotFoundError):
            services.artifact_store.load("p1", FilmPhase("post"), "assembly_manifest", 1)


class TestDeliveryNodeGate:
    def test_parks_at_final_delivery_gate_by_default(self) -> None:
        updates = delivery_node({"project_id": "p1"})

        assert updates == {
            "current_phase": "delivery",
            "approved": False,
            "human_approval_required": True,
            "human_approval_phase": "final_delivery",
        }

    def test_pre_approves_in_auto_mode(self) -> None:
        state: dict[str, Any] = {"resolved_config": {"studio": {"require_human_approval": False}}}

        updates = delivery_node(state)

        assert updates["approved"] is True
        assert updates["human_approval_required"] is False
        assert updates["human_approval_phase"] == "final_delivery"


class TestConsistencyCheckNode:
    def test_noop_without_services(self) -> None:
        assert consistency_check_node({"project_id": "p1"}) == {}

    def test_flags_stale_upstream_dependency(self, tmp_path: Path) -> None:
        services = _services(tmp_path)
        store = services.artifact_store
        _save_constitution_version(store, "p1", 1)
        _save_constitution_version(store, "p1", 2)

        state: dict[str, Any] = {
            "project_id": "p1",
            "constitution_ref": "artifact:film_constitution:v1",
            SERVICES_KEY: services,
        }
        manifest_ref = post_node(state)["assembly_manifest_ref"]

        check_state: dict[str, Any] = {
            "project_id": "p1",
            "artifact_refs": [manifest_ref],
            SERVICES_KEY: services,
        }
        set_approved_ref(check_state, "film_constitution", "artifact:film_constitution:v2")

        updates = consistency_check_node(check_state)

        warnings = updates["consistency_warnings"]
        assert len(warnings) == 1
        warning = warnings[0]
        assert warning["artifact_id"] == "assembly_manifest"
        assert warning["dependency_id"] == "film_constitution"
        assert warning["built_with_version"] == "artifact:film_constitution:v1"
        assert warning["current_version"] == "artifact:film_constitution:v2"
        assert warning["severity"] == "stale"

    def test_silent_when_all_dependencies_current(self, tmp_path: Path) -> None:
        services = _services(tmp_path)
        _save_constitution_version(services.artifact_store, "p1", 1)

        state: dict[str, Any] = {
            "project_id": "p1",
            "constitution_ref": "artifact:film_constitution:v1",
            SERVICES_KEY: services,
        }
        manifest_ref = post_node(state)["assembly_manifest_ref"]

        check_state: dict[str, Any] = {
            "project_id": "p1",
            "artifact_refs": [manifest_ref],
            SERVICES_KEY: services,
        }
        set_approved_ref(check_state, "film_constitution", "artifact:film_constitution:v1")

        assert consistency_check_node(check_state) == {}
