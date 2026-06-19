"""Config conflict detection.

Detects irreconcilable combinations such as:
- festival quality + free_only budget
- visual_poetry film type + heavy dialogue requirements
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConfigConflict:
    """One detected config conflict."""

    code: str
    message: str
    severity: str = "warning"


@dataclass
class ConfigValidator:
    """Validate resolved configs for known conflicts."""

    def validate(self, resolved: dict[str, Any]) -> list[ConfigConflict]:
        """Return all detected conflicts; an empty list means valid."""
        conflicts: list[ConfigConflict] = []

        budget = resolved.get("budget", {}) or {}
        providers = resolved.get("providers", {}) or {}
        generation = resolved.get("generation", {}) or {}

        quality = resolved.get("quality_profile", "")
        provider_order: list[str] = providers.get("order", [])
        is_free = bool(
            provider_order
            and all("free" in p.lower() or "mock" in p.lower() for p in provider_order)
        )
        if "festival" in str(quality).lower() and is_free:
            conflicts.append(
                ConfigConflict(
                    code="festival_free_conflict",
                    message="festival quality + free-only provider detected",
                    severity="blocking",
                )
            )

        film_type = str(resolved.get("film_type", "")).lower()
        writing_style = str(resolved.get("writing_style", "")).lower()
        if "visual_poetry" in film_type and "dialogue" in writing_style:
            conflicts.append(
                ConfigConflict(
                    code="poetry_dialogue_conflict",
                    message="visual_poetry + dialogue-heavy style conflict",
                    severity="warning",
                )
            )

        cap: float = float(budget.get("project_cap_usd", 0))
        shot_count: int = int(generation.get("expected_shot_count", 0))
        if cap < 10 and shot_count > 20:
            conflicts.append(
                ConfigConflict(
                    code="budget_shot_mismatch",
                    message=f"Budget ${cap} may not cover {shot_count} shots",
                    severity="warning",
                )
            )

        return conflicts
