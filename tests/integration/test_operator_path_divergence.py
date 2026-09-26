"""Characterize graph, app, and MCP operator paths before their repairs."""

from __future__ import annotations

import asyncio
import importlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from film_pipeline.mcp.resolution import ProjectRecord
from film_pipeline.mcp.server import MCPServer
from film_pipeline.orchestration.router import compute_actions
from film_pipeline.orchestration.services import SERVICES_KEY
from film_pipeline.orchestration.state_schema import StudioGraphState
from film_pipeline.schemas.artifact import ArtifactMetadata, ArtifactRef
from film_pipeline.schemas.base import (
    ArtifactStatus,
    ArtifactType,
    FilmPhase,
    IssueSeverity,
    ValidationModality,
    ValidationScope,
    ValidationStatus,
)
from film_pipeline.schemas.matrix import MasterFilmMatrix, MasterFilmMatrixRow
from film_pipeline.schemas.matrix_patch import MatrixPatch, MatrixRowUpdate
from film_pipeline.schemas.validation import ValidationIssue, ValidationReport
from film_pipeline.studio.runtime import StudioRuntime


def _make_runtime(tmp_path: Path) -> StudioRuntime:
    runtime = StudioRuntime(runtime_root=tmp_path / "runtime")
    runtime.create_project("operator-path", "Operator Path")
    runtime.set_active("operator-path")
    return runtime


def _make_project_pair(runtime_root: Path) -> StudioRuntime:
    runtime = StudioRuntime(runtime_root=runtime_root)
    runtime.create_project("active-project", "Active Project")
    runtime.create_project("requested-project", "Requested Project")
    runtime.set_active("active-project")
    active = runtime.get_project("active-project")
    requested = runtime.get_project("requested-project")
    assert active is not None
    assert requested is not None
    active["current_phase"] = "intake"
    requested["current_phase"] = "intake"
    return runtime


def _save_shot_matrix(runtime: StudioRuntime, project_id: str) -> str:
    services = runtime.services
    assert services is not None
    matrix = MasterFilmMatrix(
        project_id=project_id,
        rows=[
            MasterFilmMatrixRow(
                shot_id="shot-001",
                act_id="act-001",
                sequence_id="sequence-001",
                scene_id="scene-001",
                scene_intent_ref="artifact:development:scene_intent:v1",
                duration_seconds=8,
            )
        ],
    )
    metadata = ArtifactMetadata(
        artifact_id="shot_matrix",
        artifact_type=ArtifactType.MASTER_FILM_MATRIX,
        project_id=project_id,
        phase=FilmPhase.SHOT_BIBLE,
        version=1,
        status=ArtifactStatus.CANDIDATE,
        created_by="operator-path-test",
        created_at=datetime.now(UTC),
    )
    return services.artifact_store.save(matrix, metadata).to_string()


def _load_qc_patch(
    runtime: StudioRuntime,
    project_id: str,
    patch_ref: object,
) -> MatrixPatch | None:
    if not isinstance(patch_ref, str):
        return None
    reference = ArtifactRef.from_string(patch_ref)
    assert reference.artifact_id == "matrix_patch_qc"
    assert reference.phase == FilmPhase.QC
    services = runtime.services
    assert services is not None
    raw_patch = services.artifact_store.load(
        project_id,
        FilmPhase.QC,
        reference.artifact_id,
        reference.version,
    )
    return MatrixPatch.model_validate(raw_patch)


def _blocked_provider_state() -> dict[str, Any]:
    return {
        "current_phase": "gen_planning",
        "approved": False,
        "human_approval_required": True,
        "issues": [],
        "_orchestrator__candidate_refs": {},
        "_orchestrator__approved_refs": {},
        "_orchestrator__active_review_cycles": [],
        "_orchestrator__pending_revisions": [],
        "_orchestrator__routing_decisions": [],
        "_orchestrator__convergence": {},
        "_orchestrator__failure_decisions": [],
        "_orchestrator__provider_health_snapshot": {
            "mock-video-provider": {"status": "blocked_quota"},
        },
        "_orchestrator__budget_snapshot": {
            "cap_usd": 100.0,
            "spent_usd": 0.0,
            "remaining_usd": 100.0,
            "threshold_exceeded": False,
        },
        "_orchestrator__execution_brief": {},
    }


@pytest.mark.xfail(
    strict=True,
    reason=(
        "O-01 captures MCP handlers using runtime active state instead of resolved project_ref."
    ),
)
def test_mcp_operator_mutation_uses_resolved_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import film_pipeline.mcp.tools as tools_pkg

    runtime = _make_project_pair(tmp_path / "runtime")
    active_project = runtime.get_project("active-project")
    requested_project = runtime.get_project("requested-project")
    assert active_project is not None
    assert requested_project is not None
    monkeypatch.setattr(tools_pkg, "get_runtime", lambda: runtime)

    def record_phase_node(
        _runtime: StudioRuntime,
        state: dict[str, Any],
        phase: str,
    ) -> dict[str, Any]:
        return {**state, "current_phase": phase}

    app_graph_exec = importlib.import_module("film_pipeline.studio._graph_exec")
    monkeypatch.setattr(app_graph_exec, "run_phase_node", record_phase_node)

    server = MCPServer()
    server.register_project(
        ProjectRecord(
            project_id="requested-project",
            slug="requested-project",
            title="Requested Project",
        )
    )
    response = asyncio.run(
        server.call(
            "approve_phase",
            {"project_ref": "requested-project", "confirmed": True},
        )
    )

    assert response.success is True
    data = cast(dict[str, object], response.data)
    assert data["ok"] is True
    assert data["project_id"] == "requested-project"
    active_after = runtime.get_project("active-project")
    requested_after = runtime.get_project("requested-project")
    assert active_after is not None
    assert requested_after is not None
    assert data["current_phase"] == "constitution"
    assert requested_after["current_phase"] == "constitution"
    assert active_after["current_phase"] == "intake"


@pytest.mark.xfail(
    strict=True,
    reason="O-01 captures request_revision selecting the runtime active project.",
)
def test_mcp_revision_uses_resolved_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import film_pipeline.mcp.tools as tools_pkg

    runtime = _make_project_pair(tmp_path / "runtime")
    monkeypatch.setattr(tools_pkg, "get_runtime", lambda: runtime)
    selected_projects: list[str] = []

    def record_revision(*, note: str = "", project_id: str | None = None) -> dict[str, Any]:
        selected_id = project_id or "active-project"
        selected_projects.append(selected_id)
        selected = runtime.get_project(selected_id)
        assert selected is not None
        selected["revision_note"] = note
        return selected

    monkeypatch.setattr(runtime, "request_revision", record_revision)
    server = MCPServer()
    server.register_project(
        ProjectRecord(
            project_id="requested-project",
            slug="requested-project",
            title="Requested Project",
        )
    )

    response = asyncio.run(
        server.call(
            "request_revision",
            {
                "project_ref": "requested-project",
                "confirmed": True,
                "note": "Clarify the character goal.",
            },
        )
    )

    assert response.success is True
    data = cast(dict[str, object], response.data)
    assert data["project_id"] == "requested-project"
    assert selected_projects == ["requested-project"]
    active = runtime.get_project("active-project")
    requested = runtime.get_project("requested-project")
    assert active is not None
    assert requested is not None
    assert "revision_note" not in active
    assert requested["revision_note"] == "Clarify the character goal."


def test_mcp_validation_uses_resolved_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import film_pipeline.mcp.tools as tools_pkg
    import film_pipeline.mcp.tools.validation as validation_tools

    runtime = _make_project_pair(tmp_path / "runtime")
    active = runtime.get_project("active-project")
    requested = runtime.get_project("requested-project")
    assert active is not None
    assert requested is not None
    active["current_phase"] = "script"
    requested["current_phase"] = "script"
    monkeypatch.setattr(tools_pkg, "get_runtime", lambda: runtime)
    reports = [{"validator_id": "script-structure", "status": "pass", "score": 100.0}]
    saved_refs = ["artifact:script:validation_report:v1"]
    monkeypatch.setattr(
        validation_tools,
        "_validate_script",
        lambda _store, _project_id, _phase: (reports, saved_refs),
    )
    server = MCPServer()
    server.register_project(
        ProjectRecord(
            project_id="requested-project",
            slug="requested-project",
            title="Requested Project",
        )
    )

    response = asyncio.run(server.call("run_validation", {"project_ref": "requested-project"}))

    assert response.success is True
    data = cast(dict[str, object], response.data)
    assert data.get("phase") == "script"
    assert data.get("reports") == reports
    assert data.get("saved_refs") == saved_refs
    active = runtime.get_project("active-project")
    requested = runtime.get_project("requested-project")
    assert active is not None
    assert requested is not None
    assert "validation_refs" not in active
    assert requested["validation_refs"] == saved_refs


@pytest.mark.xfail(
    strict=True,
    reason="O-01 captures rollback_to_checkpoint selecting the runtime active project.",
)
def test_mcp_rollback_uses_resolved_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import film_pipeline.mcp.tools as tools_pkg
    from film_pipeline.checkpoints.rollback import RollbackManager

    runtime = _make_project_pair(tmp_path / "runtime")
    checkpoint = runtime.create_checkpoint(
        project_id="requested-project",
        phase="qc",
        reason="requested project rollback",
    )
    monkeypatch.setattr(tools_pkg, "get_runtime", lambda: runtime)
    selected_managers: list[object] = []

    def record_rollback(
        manager: RollbackManager,
        _checkpoint_id: str,
        *,
        performed_by: str = "system",
        artifact_types: list[str] | None = None,
    ) -> tuple[object, object]:
        del performed_by, artifact_types
        selected_managers.append(manager.checkpoint_manager)
        return None, None

    monkeypatch.setattr(RollbackManager, "rollback_to_checkpoint", record_rollback)
    server = MCPServer()
    server.register_project(
        ProjectRecord(
            project_id="requested-project",
            slug="requested-project",
            title="Requested Project",
        )
    )

    response = asyncio.run(
        server.call(
            "rollback_to_checkpoint",
            {
                "project_ref": "requested-project",
                "checkpoint_id": checkpoint.checkpoint_id,
                "confirmed": True,
            },
        )
    )

    assert response.success is True
    data = cast(dict[str, object], response.data)
    assert data["rollback_target"] == checkpoint.checkpoint_id
    assert selected_managers == [runtime.checkpoint_managers["requested-project"]]


@pytest.mark.xfail(
    strict=True,
    reason=("O-01 captures compiled approval routing into generation with a blocked provider."),
)
def test_compiled_graph_approval_edge_remains_blocked_after_human_approval() -> None:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.memory import MemorySaver

    from film_pipeline.studio.graph_factory import build_graph

    before_approval = _blocked_provider_state()
    gate = compute_actions(before_approval)
    approved_state = {
        **before_approval,
        "approved": True,
        "human_approval_required": False,
    }
    graph = build_graph(checkpointer=MemorySaver())
    config = cast(
        RunnableConfig,
        {"configurable": {"thread_id": "blocked-provider-approval"}},
    )
    graph.update_state(config, approved_state, as_node="await_approval")
    snapshot = graph.get_state(config)
    post_gate = compute_actions(dict(snapshot.values))

    assert gate.next_action == "wait_for_human"
    assert snapshot.values["current_phase"] == "gen_planning"
    assert any("mock-video-provider" in blocker["reason"] for blocker in post_gate.blocked)
    assert post_gate.next_action == "continue_unrelated_work"
    assert snapshot.next == ("consistency_check",)


@pytest.mark.xfail(
    strict=True,
    reason="O-01 captures that the app no-checkpoint fallback advances into blocked generation.",
)
def test_mcp_approval_fallback_remains_blocked_after_human_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import film_pipeline.mcp.tools as tools_pkg

    runtime = _make_runtime(tmp_path)
    active = runtime.get_active()
    assert active is not None
    before_approval = _blocked_provider_state()
    active.update(before_approval)
    runtime.projects["operator-path"] = active
    monkeypatch.setattr(tools_pkg, "get_runtime", lambda: runtime)

    visited_phases: list[str] = []

    def record_phase_node(
        _runtime: StudioRuntime,
        state: dict[str, Any],
        phase: str,
    ) -> dict[str, Any]:
        visited_phases.append(phase)
        return {**state, "current_phase": phase}

    app_graph_exec = importlib.import_module("film_pipeline.studio._graph_exec")
    monkeypatch.setattr(app_graph_exec, "run_phase_node", record_phase_node)
    response = asyncio.run(MCPServer().call("approve_phase", {"confirmed": True}))
    assert response.success is True
    data = cast(dict[str, object], response.data)

    assert data["ok"] is True
    assert visited_phases == []
    assert data["current_phase"] == "gen_planning"
    assert active["_orchestrator__provider_health_snapshot"] == {
        "mock-video-provider": {"status": "blocked_quota"}
    }


def _validation_report() -> ValidationReport:
    return ValidationReport(
        validation_id="validation:deterministic-validator:shot-001",
        validator_id="deterministic-validator",
        scope=ValidationScope.CLIP,
        modalities=[ValidationModality.CONTINUITY],
        score=40.0,
        status=ValidationStatus.NEEDS_REVISION,
        blocking_issues=[
            ValidationIssue(
                code="missing_take",
                message="Shot needs another take.",
                severity=IssueSeverity.BLOCKING,
                affected_shot="shot-001",
            )
        ],
    )


def _expected_issue() -> dict[str, object]:
    return {
        "issue_id": "val:deterministic-validator:missing_take",
        "severity": "blocking",
        "code": "missing_take",
        "message": "Shot needs another take.",
        "validator_id": "deterministic-validator",
        "affected_shot": "shot-001",
    }


def _expected_patch_update() -> MatrixRowUpdate:
    return MatrixRowUpdate(
        shot_id="shot-001",
        append={"validation_refs": ["deterministic-validator"]},
        set={"status": "failed"},
    )


def _deterministic_app_validation(state: dict[str, Any]) -> None:
    """Provide one stable affected-shot finding to app validation."""
    state["_validation_reports"] = [_validation_report().model_dump(mode="json")]
    state["issues"] = [_expected_issue()]
    state["_pending_row_updates"] = [_expected_patch_update()]


class _DeterministicValidator:
    """Return one affected-shot report for the compiled QC worker."""

    def run(self, _artifact: dict[str, Any]) -> ValidationReport:
        return _validation_report()


def _compiled_qc_result(
    runtime: StudioRuntime,
    monkeypatch: pytest.MonkeyPatch,
    shot_matrix_ref: str,
) -> dict[str, Any]:
    """Run the production QC subgraph with one deterministic validator worker."""
    qc_module = importlib.import_module("film_pipeline.orchestration.subgraphs.qc")
    monkeypatch.setattr(
        qc_module,
        "_resolve_validator_instance",
        lambda _services, validator_id: (
            _DeterministicValidator() if validator_id == "script-structure" else None
        ),
    )
    monkeypatch.setattr(
        qc_module,
        "_load_artifact_for_validator",
        lambda _state, validator_id: (
            {"project_id": "operator-path"} if validator_id == "script-structure" else None
        ),
    )
    services = runtime.services
    assert services is not None
    state = cast(
        StudioGraphState,
        {
            "project_id": "operator-path",
            "current_phase": "qc",
            "shot_matrix_ref": shot_matrix_ref,
            "approved": False,
            "human_approval_required": True,
            "issues": [],
            "artifact_refs": [],
            SERVICES_KEY: services,
        },
    )
    return cast(dict[str, Any], qc_module.build_qc_subgraph().invoke(state))


@pytest.mark.xfail(
    strict=True,
    reason=("O-01 captures compiled QC dropping affected-shot identity and its row patch."),
)
def test_compiled_graph_qc_preserves_affected_shot_in_issue_and_matrix_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _make_runtime(tmp_path)
    shot_matrix_ref = _save_shot_matrix(runtime, "operator-path")
    result = _compiled_qc_result(runtime, monkeypatch, shot_matrix_ref)
    issue = next(
        issue
        for issue in cast(list[dict[str, Any]], result["issues"])
        if issue.get("code") == "missing_take"
    )
    patch_ref = result.get("qc_patch_ref")
    patch = _load_qc_patch(runtime, "operator-path", patch_ref)
    patch_matches = (
        patch is not None
        and patch.matrix_ref == shot_matrix_ref
        and patch.phase == FilmPhase.QC.value
        and patch.updates == [_expected_patch_update()]
    )

    assert (issue.get("affected_shot"), patch_matches) == ("shot-001", True)


@pytest.mark.xfail(
    strict=True,
    reason="O-01 captures app run_validation leaving its pending row update unmaterialized.",
)
def test_app_validation_materializes_qc_row_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import film_pipeline.orchestration.nodes as nodes

    runtime = _make_runtime(tmp_path)
    shot_matrix_ref = _save_shot_matrix(runtime, "operator-path")
    active = runtime.get_active()
    assert active is not None
    active["current_phase"] = "qc"
    active["shot_matrix_ref"] = shot_matrix_ref
    monkeypatch.setattr(nodes, "_run_validators", _deterministic_app_validation)

    result = runtime.run_validation()
    assert result["issues"] == [_expected_issue()]
    patch_ref = result.get("qc_patch_ref")
    assert isinstance(patch_ref, str)
    patch = _load_qc_patch(runtime, "operator-path", patch_ref)
    assert patch is not None
    assert patch.matrix_ref == shot_matrix_ref
    assert patch.phase == FilmPhase.QC.value
    assert patch.updates == [_expected_patch_update()]


def _mcp_qc_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[StudioRuntime, dict[str, Any], dict[str, object]]:
    import film_pipeline.mcp.tools as tools_pkg

    runtime = _make_runtime(tmp_path)
    shot_matrix_ref = _save_shot_matrix(runtime, "operator-path")
    active = runtime.get_active()
    assert active is not None
    active["current_phase"] = "qc"
    active["shot_matrix_ref"] = shot_matrix_ref
    graph_result = _compiled_qc_result(runtime, monkeypatch, shot_matrix_ref)
    monkeypatch.setattr(tools_pkg, "get_runtime", lambda: runtime)

    response = asyncio.run(MCPServer().call("run_validation", {}))
    assert response.success is True
    data = cast(dict[str, object], response.data)
    assert data.get("ok") is True
    return runtime, graph_result, data


def _report_summary(report: ValidationReport) -> dict[str, object]:
    return {
        "validator_id": report.validator_id,
        "score": report.score,
        "status": report.status.value,
        "blocking_count": len(report.blocking_issues),
        "warning_count": len(report.warnings),
    }


def _normalized_summaries(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    keys = ("validator_id", "score", "status", "blocking_count", "warning_count")
    return [{key: report.get(key) for key in keys} for report in value if isinstance(report, dict)]


@pytest.mark.xfail(
    strict=True,
    reason="O-01 captures MCP QC findings diverging from the compiled graph QC result.",
)
def test_mcp_validation_matches_compiled_qc_findings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _runtime, graph_result, data = _mcp_qc_result(tmp_path, monkeypatch)
    raw_reports = cast(list[dict[str, Any]], graph_result.get("_validation_reports", []))
    graph_reports = [
        _report_summary(ValidationReport.model_validate(report))
        for report in raw_reports
        if "blocking_issues" in report
    ]
    graph_issues = cast(list[dict[str, object]], graph_result.get("issues", []))

    assert {
        "graph_reports": graph_reports,
        "mcp_reports": _normalized_summaries(data.get("reports")),
        "graph_issues": graph_issues,
        "mcp_issues": data.get("issues"),
    } == {
        "graph_reports": [_report_summary(_validation_report())],
        "mcp_reports": [_report_summary(_validation_report())],
        "graph_issues": [_expected_issue()],
        "mcp_issues": [_expected_issue()],
    }


@pytest.mark.xfail(
    strict=True,
    reason="O-01 captures MCP QC omitting the compiled graph's materialized row patch.",
)
def test_mcp_validation_returns_compiled_qc_matrix_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime, graph_result, data = _mcp_qc_result(tmp_path, monkeypatch)
    graph_patch_ref = graph_result.get("qc_patch_ref")
    mcp_patch_ref = data.get("qc_patch_ref")
    graph_patch = _load_qc_patch(runtime, "operator-path", graph_patch_ref)
    mcp_patch = _load_qc_patch(runtime, "operator-path", mcp_patch_ref)
    shot_matrix_ref = "artifact:shot_bible:shot_matrix:v1"

    assert {
        "graph_patch": graph_patch is not None
        and graph_patch.matrix_ref == shot_matrix_ref
        and graph_patch.phase == FilmPhase.QC.value
        and graph_patch.updates == [_expected_patch_update()],
        "mcp_patch": mcp_patch is not None
        and mcp_patch.matrix_ref == shot_matrix_ref
        and mcp_patch.phase == FilmPhase.QC.value
        and mcp_patch.updates == [_expected_patch_update()],
    } == {
        "graph_patch": True,
        "mcp_patch": True,
    }
