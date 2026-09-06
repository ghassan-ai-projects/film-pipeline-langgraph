"""Smoke test fixtures — re-use E2E fixtures via explicit imports."""

# Re-export the E2E fixtures so pytest discovers them for smoke tests.
from tests.e2e.conftest import (  # noqa: F401
    agent_registry,
    graph_services,
    kb_builder,
    kb_manifest,
    mock_model,
    mock_provider,
    studio_runtime,
)
