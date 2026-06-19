"""Invalidation engine — dependency graph and rollback impact reports."""

from __future__ import annotations

from dataclasses import dataclass

from film_pipeline.schemas.checkpoint import InvalidationReport

# Dependencies: artifact_type → dependent artifact_types
DEPENDENCY_GRAPH: dict[str, list[str]] = {
    "film_constitution": ["treatment", "script", "character_bible", "environment_bible"],
    "treatment": ["script", "scene_intents", "shot_bible"],
    "script": ["scene_intents", "shot_bible", "prompt_registry", "continuity_ledger"],
    "character_bible": ["reference_strategy", "prompt_registry", "validation_reports"],
    "environment_bible": ["reference_strategy", "prompt_registry", "validation_reports"],
    "scene_intents": ["shot_bible", "prompt_registry"],
    "shot_bible": ["prompt_registry", "continuity_ledger", "generation_schedule"],
    "reference_strategy": ["prompt_registry"],
    "prompt_registry": ["provider_plan", "generation_schedule"],
    "provider_plan": ["generation_schedule"],
    "generation_schedule": ["generated_clips"],
    "continuity_ledger": ["validation_reports"],
    "project_config": ["model_routing", "validators", "provider_plan"],
}


@dataclass
class InvalidationEngine:
    """Computes what gets invalidated by a rollback or artifact change."""

    def report(
        self,
        rollback_target: str,
        artifact_types: list[str] | None = None,
        requires_regeneration: bool = False,
    ) -> InvalidationReport:
        """Build an invalidation report for the given rollback target.

        Args:
            rollback_target: Human-readable target description.
            artifact_types: Which artifact types are being reverted.
            requires_regeneration: Whether generation must re-run.
        """
        will_invalidate: list[str] = []
        types = artifact_types or []

        for atype in types:
            deps = DEPENDENCY_GRAPH.get(atype, [])
            for dep in deps:
                if dep not in will_invalidate and dep not in types:
                    will_invalidate.append(dep)

        return InvalidationReport(
            rollback_target=rollback_target,
            will_revert=list(types),
            will_invalidate=sorted(will_invalidate),
            requires_regeneration=requires_regeneration,
            requires_human_confirmation=True,
            notes=(
                f"Rollback to {rollback_target}. "
                f"{len(will_invalidate)} dependent artifacts affected."
            ),
        )

    def dependencies_of(self, artifact_type: str) -> list[str]:
        """Return all artifact types that depend on the given type."""
        return DEPENDENCY_GRAPH.get(artifact_type, [])
