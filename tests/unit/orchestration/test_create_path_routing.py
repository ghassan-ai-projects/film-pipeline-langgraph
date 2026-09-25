"""Create-path routing honors the call site's explicit agent id [DF-F2 root cause].

``route_agent`` documented that create paths fall back to the caller-supplied
agent, but silently returned the phase default for every create task — so
``shot_bible_node``'s structure-extraction call actually ran the shot-design
agent and no ExecutionBrief was ever produced. These tests pin the repaired
contract: explicit ids are honored when registered, on the create path only.
"""

from __future__ import annotations

from typing import Any

import pytest

from film_pipeline.orchestration._agent_routing import route_agent
from film_pipeline.orchestration.services import GraphServices
from film_pipeline.studio.mock_responses import default_mock_responses


@pytest.fixture()
def registry() -> Any:
    from film_pipeline.agents.mvp import MVP_AGENTS
    from film_pipeline.agents.registry import AgentRegistry

    reg = AgentRegistry()
    reg.register_many(MVP_AGENTS)
    return reg


_STATE: dict[str, Any] = {"project_id": "routing", "current_phase": "shot_bible"}


def test_create_path_honors_explicit_registered_agent(registry: Any) -> None:
    result = route_agent(
        _STATE,
        phase="shot_bible",
        task_type="create",
        registry=registry,
        preferred_agent_id="structure-extractor-agent",
    )
    assert result.agent_id == "structure-extractor-agent"
    assert result.fallback is False


def test_create_path_falls_back_to_phase_default_for_unknown_agent(
    registry: Any,
) -> None:
    result = route_agent(
        _STATE,
        phase="shot_bible",
        task_type="create",
        registry=registry,
        preferred_agent_id="not-a-real-agent",
    )
    assert result.agent_id == "shot-design-agent"


def test_review_and_repair_paths_ignore_preferred_agent(registry: Any) -> None:
    review = route_agent(
        _STATE,
        phase="qc",
        task_type="review",
        registry=registry,
        preferred_agent_id="screenwriter-agent",
    )
    assert review.agent_id != "screenwriter-agent"

    repair = route_agent(
        _STATE,
        phase="script",
        task_type="repair",
        registry=registry,
        preferred_agent_id="intake-classifier-agent",
    )
    assert repair.agent_id != "intake-classifier-agent"


def test_extraction_produces_execution_brief_through_full_lifecycle(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The DF-F2 causal chain end-to-end with mock services, no graph needed."""
    from film_pipeline.orchestration.nodes.visual import _ensure_execution_brief
    from film_pipeline.orchestration.services import _SERVICES_CTX, SERVICES_KEY

    svc = GraphServices.for_mock_runtime(
        artifacts_root=str(tmp_path / "artifacts"), mock_responses=default_mock_responses()
    )
    token = _SERVICES_CTX.set(svc)
    try:
        state: dict[str, Any] = {
            "project_id": "dff2-root-cause",
            "idea": "A lighthouse keeper who mails letters to the future.",
            "current_phase": "shot_bible",
            "target_runtime_seconds": 300,
            SERVICES_KEY: svc,
            "resolved_config": {"studio": {"require_human_approval": False}},
            "artifact_refs": [],
        }
        _ensure_execution_brief(state)
        assert "_orchestrator__execution_brief" in state, (
            "extraction must produce a brief now that the explicit agent runs"
        )
        assert state.get("execution_brief_ref")
    finally:
        _SERVICES_CTX.reset(token)
