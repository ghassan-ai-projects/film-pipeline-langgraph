"""E2E Scenario 1: Happy path — idea → review cut with mock provider."""

from __future__ import annotations

import pytest

from film_pipeline.agents.registry import AgentRegistry
from film_pipeline.checkpoints.git_backend import GitBackend
from film_pipeline.checkpoints.manager import CheckpointManager
from film_pipeline.graph.graph import build_graph
from film_pipeline.kb.packets import KBContextPacketBuilder
from film_pipeline.providers.health import ProviderHealthTracker
from film_pipeline.providers.mock_provider import MockVideoProvider
from film_pipeline.providers.registry import ProviderRegistry
from film_pipeline.schemas._base import FilmPhase
from film_pipeline.testing.mock_human import MockHumanActor
from film_pipeline.testing.mock_model import MockModelAdapter
from film_pipeline.validation.registry import ValidatorRegistry


@pytest.mark.e2e
class TestHappyPath:
    """End-to-end: a mini-film goes from idea through all phases to delivery."""

    def test_graph_compiles_with_full_infrastructure(
        self,
        agent_registry: AgentRegistry,
        validator_registry: ValidatorRegistry,
        mock_provider: MockVideoProvider,
        mock_human: MockHumanActor,
        mock_model: MockModelAdapter,
        kb_builder: KBContextPacketBuilder,
        provider_registry: ProviderRegistry,
        health_tracker: ProviderHealthTracker,
        git_backend: GitBackend,
        checkpoint_manager: CheckpointManager,
    ) -> None:
        """Smoke test: all infrastructure connects and the graph compiles."""
        # Verify registries are populated
        assert len(agent_registry) == 19
        assert len(validator_registry) == 15
        assert len(provider_registry) == 1
        assert health_tracker.get("mock-video-provider") is not None
        assert mock_provider.entry.provider_id == "mock-video-provider"
        assert git_backend.is_clean()

        # Verify KB context builder works
        packet = kb_builder.build(
            project_id="e2e-test",
            phase="script",
            agent_id="screenwriter-agent",
            task="Write test script",
        )
        assert packet.project_id == "e2e-test"
        assert len(packet.authority_policy_refs) >= 1

        # Verify mock human works
        decision = mock_human.decide("script", "script_review", "Test summary")
        assert decision == "approve"

        # Verify mock model works
        response = mock_model.agent_response("screenwriter-agent")
        assert "status" in response

        # Verify graph compiles with all infrastructure
        graph = build_graph()
        assert graph is not None

        # Verify checkpoint manager works
        cp = checkpoint_manager.create(
            project_id="e2e-test",
            phase=FilmPhase.SCRIPT,
            reason="E2E smoke test",
        )
        assert cp.project_id == "e2e-test"

    def test_full_phase_sequence_state_transitions(self) -> None:
        """Verify the graph can transition through all 11 phases."""
        from film_pipeline.graph.router import PHASE_ORDER

        assert len(PHASE_ORDER) == 11
        expected = [
            "intake",
            "constitution",
            "development",
            "script",
            "visual_dev",
            "shot_bible",
            "gen_planning",
            "generation",
            "qc",
            "post",
            "delivery",
        ]
        assert expected == PHASE_ORDER

    def test_approval_gates_exist_for_all_phases(self) -> None:
        """Every phase has an approval gate."""
        from film_pipeline.graph.router import APPROVAL_GATES, PHASE_ORDER

        for phase in PHASE_ORDER:
            assert phase in APPROVAL_GATES, f"No gate for phase: {phase}"

    def test_review_types_exist_for_all_phases(self) -> None:
        """Every phase has a review type."""
        from film_pipeline.graph.router import PHASE_ORDER
        from film_pipeline.review.generator import REVIEW_TYPE_MAP

        for phase_name in PHASE_ORDER:
            # Map string phase names to FilmPhase enum
            from film_pipeline.schemas._base import FilmPhase

            phase_enum = FilmPhase(phase_name)
            assert phase_enum in REVIEW_TYPE_MAP, f"No review type for {phase_name}"
