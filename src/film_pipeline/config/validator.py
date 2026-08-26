"""Config conflict detection.

Detects irreconcilable combinations such as:
- festival quality + free_only budget
- visual_poetry film type + heavy dialogue requirements
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class ConfigConflict:
    """One detected config conflict."""

    code: str
    message: str
    severity: Literal["warning", "blocking"] = "warning"


def _detect_festival_free_conflict(resolved: dict[str, Any]) -> ConfigConflict | None:
    """Festival-grade quality is irreconcilable with an all-free provider lineup."""
    quality = str(resolved.get("quality_profile", "")).lower()
    provider_order: list[str] = (resolved.get("providers", {}) or {}).get("order", [])
    is_free_only = bool(
        provider_order and all("free" in p.lower() or "mock" in p.lower() for p in provider_order)
    )
    if "festival" in quality and is_free_only:
        return ConfigConflict(
            code="festival_free_conflict",
            message="festival quality + free-only provider detected",
            severity="blocking",
        )
    return None


def _detect_poetry_dialogue_conflict(resolved: dict[str, Any]) -> ConfigConflict | None:
    """visual_poetry films conflict with dialogue-heavy writing styles."""
    film_type = str(resolved.get("film_type", "")).lower()
    writing_style = str(resolved.get("writing_style", "")).lower()
    if "visual_poetry" in film_type and "dialogue" in writing_style:
        return ConfigConflict(
            code="poetry_dialogue_conflict",
            message="visual_poetry + dialogue-heavy style conflict",
        )
    return None


def _detect_budget_shot_mismatch(resolved: dict[str, Any]) -> ConfigConflict | None:
    """A small project cap may not stretch across many expected shots."""
    budget = resolved.get("budget", {}) or {}
    generation = resolved.get("generation", {}) or {}
    cap: float = float(budget.get("project_cap_usd", 0))
    shot_count: int = int(generation.get("expected_shot_count", 0))
    if cap < 10 and shot_count > 20:
        return ConfigConflict(
            code="budget_shot_mismatch",
            message=f"Budget ${cap} may not cover {shot_count} shots",
            severity="warning",
        )
    return None


@dataclass
class ConfigValidator:
    """Validate resolved configs for known conflicts."""

    def validate(self, resolved: dict[str, Any]) -> list[ConfigConflict]:
        """Return all detected conflicts; an empty list means valid."""
        conflicts: list[ConfigConflict] = []
        for detect_conflict in (
            _detect_festival_free_conflict,
            _detect_poetry_dialogue_conflict,
            _detect_budget_shot_mismatch,
        ):
            conflict = detect_conflict(resolved)
            if conflict is not None:
                conflicts.append(conflict)
        return conflicts
