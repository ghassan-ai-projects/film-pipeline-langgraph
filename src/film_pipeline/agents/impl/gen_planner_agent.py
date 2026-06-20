"""GenPlannerAgent — produces a generation plan from the shot matrix."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.budget import CostEstimate


class GenPlannerAgent(BaseAgent):
    """Plans the generation batch from the shot matrix.

    Output artifacts: ``CostEstimate``, plan metadata dict with shot groupings.
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
        data = model_output.get("generation_plan", model_output)

        estimate_data = data.get("cost_estimate", {})
        cost_estimate = CostEstimate(
            project_id=str(estimate_data.get("project_id", "")),
            batch_id=str(estimate_data.get("batch_id", "batch-001")),
            provider=str(estimate_data.get("provider", "seedance")),
            estimated_cost_usd=float(estimate_data.get("estimated_cost_usd", 0.0)),
            clip_count=int(estimate_data.get("clip_count", 0)),
            notes=str(estimate_data.get("notes", "")),
        )

        shot_groups = data.get("shot_groups", [])
        generation_requests = [
            {
                "shot_id": str(g.get("shot_id", f"shot_{i:04d}")),
                "provider": str(g.get("provider", "seedance")),
                "model": str(g.get("model", "2.0")),
                "mode": str(g.get("mode", "test")),
                "priority": int(g.get("priority", i)),
                "estimated_cost_usd": float(g.get("estimated_cost_usd", 0.0)),
            }
            for i, g in enumerate(shot_groups)
        ]

        return {
            "cost_estimate": cost_estimate,
            "generation_requests": generation_requests,
            "total_shots": len(generation_requests),
            "total_cost_usd": sum(r["estimated_cost_usd"] for r in generation_requests),
        }

    def validate(self, result: dict[str, Any]) -> bool:
        estimate = result.get("cost_estimate")
        if not isinstance(estimate, CostEstimate):
            return False
        return estimate.clip_count >= 0
