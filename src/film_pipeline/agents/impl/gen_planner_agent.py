"""GenPlannerAgent — produces a generation plan from the shot matrix."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent


def _build_generation_requests(shot_groups: Any) -> list[dict[str, Any]]:
    """Coerce raw shot groups into provider generation requests."""
    return [
        {
            "shot_id": str(g.get("shot_id", f"shot_{i:04d}")),
            "provider": str(g.get("provider", "seedance")),
            "model": str(g.get("model", "2.0")),
            "mode": str(g.get("mode", "test")),
            "priority": int(g.get("priority", i)),
        }
        for i, g in enumerate(shot_groups)
    ]


class GenPlannerAgent(BaseAgent):
    """Plans the generation batch from the shot matrix.

    Output artifact: the generation requests and shot groupings the ledger consumes.
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        project_id = str(state.get("project_id", ""))
        shot_matrix_ref = str(state.get("shot_matrix_ref", ""))
        budget_cap = str(state.get("budget_cap", "unlimited"))
        preferred_providers = str(state.get("preferred_providers", ""))
        return {
            "project_id": project_id,
            "shot_matrix_ref": shot_matrix_ref,
            "budget_cap": budget_cap,
            "preferred_providers": preferred_providers,
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        """Build the generation requests that drive dispatch.

        Cost estimation was removed as a feature: the planner no longer produces a
        `cost_estimate`, and `validate` no longer requires one. The requests and
        shot count are what the generation path actually consumes.
        """
        data = model_output.get("generation_plan", model_output)

        generation_requests = _build_generation_requests(data.get("shot_groups", []))

        return {
            "generation_requests": generation_requests,
            "total_shots": len(generation_requests),
        }

    def validate(self, result: dict[str, Any]) -> bool:
        requests = result.get("generation_requests")
        if not isinstance(requests, list):
            return False
        return all(isinstance(r, dict) and r.get("shot_id") for r in requests)
