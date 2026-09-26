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
        registered = self._registered_response(key)
        if registered is not None:
            return registered
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
        registered = self._registered_response(validator_id)
        if registered is not None:
            return registered
        return {
            "score": 90,
            "status": "pass",
            "issues": [],
            "mock_model": True,
        }

    def _registered_response(self, key: str) -> dict[str, Any] | None:
        """Return a defensive copy of the canned response, or None when unregistered."""
        if key in self.responses:
            return dict(self.responses[key])
        return None
