"""OrchestratorAgent — autonomous quality review between creative phases.

Replaces the human in ``await_approval_node``. Inspects phase output against
the film's target runtime and constitution, then decides: approve, revise, or
escalate. Only escalates to human when stuck (convergence exhausted or the
output is fundamentally wrong).
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from film_pipeline.agents.base import BaseAgent

_logger = logging.getLogger(__name__)


class OrchestratorDecision(BaseModel):
    """Validated decision shape for the autonomous phase reviewer."""

    action: Literal["approve", "revise", "escalate"]
    feedback: str = ""
    preserve: list[str] = Field(default_factory=list)
    reasoning: str = ""
    quality_score: int = Field(default=3, ge=1, le=5)
    critical_issues: list[str] = Field(default_factory=list)


class OrchestratorAgent(BaseAgent):
    """Autonomous quality reviewer — decides approve / revise / escalate.

    Output: ``{"action": "approve"|"revise"|"escalate", "feedback": "...", ...}``
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        return {
            "project_id": str(state.get("project_id", "")),
            "current_phase": str(state.get("current_phase", "")),
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        data = model_output.get("orchestrator_decision", model_output)
        if not isinstance(data, dict):
            data = {}
        normalized = dict(data)
        normalized["action"] = str(normalized.get("action", "escalate")).strip().lower()
        if "quality_score" not in normalized:
            normalized["quality_score"] = 3
        try:
            decision = OrchestratorDecision.model_validate(normalized)
        except ValidationError as exc:
            _logger.warning("Invalid orchestrator decision; escalating: %s", exc)
            decision = OrchestratorDecision(
                action="escalate",
                feedback="Orchestrator decision was malformed and requires human review.",
                reasoning=str(exc),
                critical_issues=["malformed_orchestrator_decision"],
            )
        return decision.model_dump()

    def validate(self, result: dict[str, Any]) -> bool:
        return result.get("action", "") in ("approve", "revise", "escalate")
