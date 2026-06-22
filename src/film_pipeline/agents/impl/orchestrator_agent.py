"""OrchestratorAgent — autonomous quality review between creative phases.

Replaces the human in ``await_approval_node``. Inspects phase output against
the film's target runtime and constitution, then decides: approve, revise, or
escalate. Only escalates to human when stuck (convergence exhausted or the
output is fundamentally wrong).
"""

from __future__ import annotations

import logging
from typing import Any

from film_pipeline.agents.base import BaseAgent

_logger = logging.getLogger(__name__)


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
        action = str(data.get("action", "escalate")).strip().lower()
        if action not in ("approve", "revise", "escalate"):
            action = "escalate"
        return {
            "action": action,
            "feedback": str(data.get("feedback", "")),
            "preserve": [str(p) for p in data.get("preserve", [])],
            "reasoning": str(data.get("reasoning", "")),
        }

    def validate(self, result: dict[str, Any]) -> bool:
        return result.get("action", "") in ("approve", "revise", "escalate")
