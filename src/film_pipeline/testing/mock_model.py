"""Mock model adapter — canned JSON responses for agents and validators.

Returns correctly-typed JSON per agent_id or validator_id.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MockModelAdapter:
    """Returns canned JSON responses for zero-cost agent/validator testing.

    Register responses by agent_id or validator_id. When a response is not
    found, returns a default placeholder.
    """

    responses: dict[str, dict[str, Any]] = field(default_factory=dict)

    def register(self, key: str, response: dict[str, Any]) -> None:
        self.responses[key] = response

    def call(self, key: str) -> dict[str, Any]:
        """Return the canned response for the given agent/validator key."""
        if key in self.responses:
            return dict(self.responses[key])
        # Default placeholder
        return {
            "status": "ok",
            "mock_model": True,
            "agent": key,
            "output": {},
        }

    def agent_response(self, agent_id: str) -> dict[str, Any]:
        """Return a canned agent response."""
        return self.call(agent_id)

    def validator_response(self, validator_id: str) -> dict[str, Any]:
        """Return a canned validation response with score and status."""
        if validator_id in self.responses:
            return dict(self.responses[validator_id])
        return {
            "score": 90,
            "status": "pass",
            "issues": [],
            "mock_model": True,
        }
