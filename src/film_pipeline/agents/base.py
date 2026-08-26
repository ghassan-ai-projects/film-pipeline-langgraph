"""Base agent contract — standard lifecycle: prepare → execute → validate."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from film_pipeline.schemas.handoff import AgentRegistration
from film_pipeline.schemas.kb import KBContextPacket


class BaseAgent(ABC):
    """Standard agent lifecycle contract.

    Every agent implements:
    - prepare(state, kb_context, task) → assembled prompt inputs
    - execute(model_output) → parsed result
    - validate(result) → bool
    """

    contract: AgentRegistration

    def __init__(self, contract: AgentRegistration) -> None:
        self.contract = contract

    @abstractmethod
    def prepare(
        self,
        state: dict[str, Any],
        kb_context: KBContextPacket,
        task: str,
    ) -> dict[str, Any]:
        """Assemble prompt inputs from state and KB context."""
        ...

    @abstractmethod
    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        """Parse and transform model output into structured result."""
        ...

    @abstractmethod
    def validate(self, result: dict[str, Any]) -> bool:
        """Validate the result against the expected output schema."""
        ...

    def run(
        self,
        state: dict[str, Any],
        kb_context: KBContextPacket,
        task: str,
        model_output: dict[str, Any],
    ) -> dict[str, Any]:
        """Full lifecycle: prepare → execute → validate."""
        # prepare() runs as the lifecycle step; the graph node layer assembles
        # the actual prompt context, so its inputs are not consumed here.
        self.prepare(state, kb_context, task)
        result = self.execute(model_output)
        if not self.validate(result):
            raise ValueError(f"Agent '{self.contract.agent_id}' produced invalid output.")
        return result
