"""IntakeAgent — classifies the user's idea and prepares the project profile."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.project import ProjectIdentity, ProjectProfile


class IntakeAgent(BaseAgent):
    """Classifies the raw user idea into a structured project profile.

    Output artifact: ``ProjectProfile``
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        project_id = str(state.get("project_id", ""))
        idea = str(state.get("idea", ""))
        return {
            "project_id": project_id,
            "idea": idea,
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        """Parse model output into a ProjectProfile."""
        data = model_output.get("intake", model_output)
        identity_data = data.get("identity", data)
        identity = ProjectIdentity(
            project_id=str(identity_data.get("project_id", data.get("project_id", ""))),
            slug=str(identity_data.get("slug", data.get("slug", ""))),
            title=str(identity_data.get("title", data.get("title", ""))),
            aliases=[str(a) for a in identity_data.get("aliases", data.get("aliases", []))],
        )
        try:
            profile = ProjectProfile(
                identity=identity,
                target_runtime_seconds=int(data.get("target_runtime_seconds", 300)),
                aspect_ratio=str(data.get("aspect_ratio", "16:9")),
                delivery_modes=data.get("delivery_modes", ["mp4"]),
                budget_cap_usd=data.get("budget_cap_usd"),
                provider_preferences=[str(p) for p in data.get("provider_preferences", [])],
                human_owner=str(data.get("human_owner", "")),
            )
        except Exception:
            profile = ProjectProfile(
                identity=identity,
                target_runtime_seconds=1,
            )
        return {"profile": profile, "classified_input": data}

    def validate(self, result: dict[str, Any]) -> bool:
        profile = result.get("profile")
        if not isinstance(profile, ProjectProfile):
            return False
        return bool(profile.identity.title and profile.target_runtime_seconds > 0)
