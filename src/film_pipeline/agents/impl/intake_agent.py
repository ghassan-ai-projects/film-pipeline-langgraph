"""IntakeAgent — classifies the user's idea and prepares the project profile."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas._base import FilmType
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
        profile = ProjectProfile(
            identity=identity,
            film_type=_coerce_film_type(data.get("film_type")),
            target_runtime_seconds=_coerce_runtime_seconds(data),
            aspect_ratio=str(data.get("aspect_ratio", "16:9") or "16:9"),
            delivery_modes=_coerce_delivery_modes(data.get("delivery_modes")),
            budget_cap_usd=_coerce_budget_cap(data.get("budget_cap_usd")),
            provider_preferences=[str(p) for p in data.get("provider_preferences", []) if str(p)],
            human_owner=_coerce_human_owner(data.get("human_owner")),
        )
        return {"profile": profile, "classified_input": data}

    def validate(self, result: dict[str, Any]) -> bool:
        profile = result.get("profile")
        if not isinstance(profile, ProjectProfile):
            return False
        return bool(profile.identity.title and profile.target_runtime_seconds > 0)


def _coerce_runtime_seconds(data: dict[str, Any]) -> int:
    """Prefer explicit runtime fields, but never collapse bad model output to 1 second."""
    candidates = (
        data.get("target_runtime_seconds"),
        data.get("estimated_runtime_seconds"),
    )
    for candidate in candidates:
        parsed = _parse_positive_int(candidate)
        if parsed is not None and parsed > 1:
            return parsed

    minutes = _parse_positive_int(data.get("target_runtime_minutes"))
    if minutes is not None and minutes >= 1:
        return minutes * 60

    # A literal 1 second is almost always an artifact of weak prompting in intake.
    one_second = _parse_positive_int(data.get("target_runtime_seconds"))
    if one_second == 1:
        return 300

    return 300


def _coerce_film_type(value: object) -> FilmType:
    raw = str(value or "").strip().lower()
    if not raw:
        return FilmType.NARRATIVE
    try:
        return FilmType(raw)
    except ValueError:
        return FilmType.NARRATIVE


def _coerce_delivery_modes(value: object) -> list[str]:
    if isinstance(value, list):
        modes = [str(mode) for mode in value if str(mode)]
        if modes:
            return modes
    return ["mp4"]


def _coerce_budget_cap(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(str(value))
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def _coerce_human_owner(value: object) -> str | None:
    raw = str(value or "").strip()
    return raw or None


def _parse_positive_int(value: object) -> int | None:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 1 else None
