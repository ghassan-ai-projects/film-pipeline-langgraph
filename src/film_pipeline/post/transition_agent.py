"""Transition agent — plans transitions between clips."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

# Closed vocabulary of transitions the post pipeline can execute.
TRANSITION_TYPES: tuple[str, ...] = ("cut", "dissolve", "fade_in", "fade_out", "crossfade")


@dataclass
class TransitionPlan:
    """A plan for transitions between all clips in an assembly."""

    plan_id: str
    project_id: str
    transitions: list[dict[str, str]] = field(default_factory=list)
    total_count: int = 0


@dataclass
class TransitionAgent:
    """Plans transitions between clips based on scene intent.

    Does not execute ffmpeg — produces a TransitionPlan for the real pipeline.
    """

    def plan_transitions(
        self,
        project_id: str,
        clip_paths: list[str],
        scene_types: dict[str, str] | None = None,
    ) -> TransitionPlan:
        """Generate a transition plan for the given clip sequence.

        Args:
            project_id: The film project identifier.
            clip_paths: Ordered list of clip file paths.
            scene_types: Optional dict mapping clip path to scene type
                         (action, dialogue, mood, transition).
        """
        plan = TransitionPlan(
            plan_id=f"transition-plan:{project_id}:{uuid4().hex[:8]}",
            project_id=project_id,
        )

        types = scene_types or {}
        for i in range(len(clip_paths) - 1):
            from_clip = clip_paths[i]
            to_clip = clip_paths[i + 1]
            from_type = types.get(from_clip, "dialogue")
            to_type = types.get(to_clip, "dialogue")

            ttype = _pick_transition(from_type, to_type)
            plan.transitions.append(
                {
                    "from": from_clip,
                    "to": to_clip,
                    "type": ttype,
                }
            )

        plan.total_count = len(plan.transitions)
        return plan


def _pick_transition(from_type: str, to_type: str) -> str:
    """Choose a transition type based on scene types."""
    if from_type == "action" and to_type == "action":
        return "cut"
    if from_type == "mood" or to_type == "mood":
        return "dissolve"
    if from_type == "transition" or to_type == "transition":
        return "crossfade"
    return "cut"
