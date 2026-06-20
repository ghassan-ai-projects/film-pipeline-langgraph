"""Smoke test fixtures — re-use E2E fixtures via explicit imports."""

# Re-export the E2E fixtures so pytest discovers them for smoke tests.
from tests.e2e.conftest import (  # noqa: F401
    agent_registry,
    checkpoint_manager,
    git_backend,
    graph_services,
    health_tracker,
    kb_builder,
    kb_manifest,
    mock_human,
    mock_model,
    mock_provider,
    provider_registry,
    studio_runtime,
    validator_registry,
)
