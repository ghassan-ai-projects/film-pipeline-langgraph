"""AssemblyAgent — produces an AssemblyManifest from generated media and the shot matrix."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.assembly import (
    AssemblyManifest,
    AudioPlan,
    ClipOrderEntry,
    ColorPlan,
    TransitionPlan,
)


class AssemblyAgent(BaseAgent):
    """Assembles the final cut from generated media and the shot matrix.

    Output artifact: ``AssemblyManifest``
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        project_id = str(state.get("project_id", ""))
        media_refs = str(state.get("media_refs", ""))
        shot_matrix_ref = str(state.get("shot_matrix_ref", ""))
        script_ref = str(state.get("script_ref", ""))
        return {
            "project_id": project_id,
            "media_refs": media_refs,
            "shot_matrix_ref": shot_matrix_ref,
            "script_ref": script_ref,
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        data = model_output.get("assembly", model_output)

        clip_order = _build_clip_order(data.get("clip_order", data.get("clips", [])))
        transitions = _build_transitions(data.get("transitions", []))
        audio_plan = _build_audio_plan(data.get("audio_plan", {}))
        color_plan = _build_color_plan(data.get("color_plan", {}))

        duration = data.get(
            "duration_total_seconds",
            sum(c.out_seconds - c.in_seconds for c in clip_order),
        )

        manifest = AssemblyManifest(
            cut_id=str(data.get("cut_id", "review-cut-v1")),
            project_id=str(data.get("project_id", "")),
            clip_order=clip_order,
            transitions=transitions,
            audio_plan=audio_plan,
            color_plan=color_plan,
            duration_total_seconds=float(duration),
        )
        return {"assembly_manifest": manifest}

    def validate(self, result: dict[str, Any]) -> bool:
        manifest = result.get("assembly_manifest")
        if not isinstance(manifest, AssemblyManifest):
            return False
        return len(manifest.clip_order) > 0


def _build_clip_order(clip_data: list[Any]) -> list[ClipOrderEntry]:
    """Build ordered clip entries from raw clip mappings."""
    return [
        ClipOrderEntry(
            shot_id=str(c.get("shot_id", f"shot_{i:04d}")),
            source_asset_ref=str(c.get("source_asset_ref", "")),
            in_seconds=float(c.get("in_seconds", 0.0)),
            out_seconds=float(c.get("out_seconds", 5.0)),
            coverage_role=str(c.get("coverage_role", "")),
        )
        for i, c in enumerate(clip_data)
    ]


def _build_transitions(transition_data: list[Any]) -> list[TransitionPlan]:
    """Build transition plans from raw transition mappings."""
    return [
        TransitionPlan(
            from_shot_id=str(t.get("from_shot_id", "")),
            to_shot_id=str(t.get("to_shot_id", "")),
            transition_type=str(t.get("transition_type", "cut")),
            duration_seconds=float(t.get("duration_seconds", 0.0)),
        )
        for t in transition_data
    ]


def _build_audio_plan(audio_data: dict[str, Any]) -> AudioPlan:
    """Build the audio plan from raw track reference lists."""
    return AudioPlan(
        music_track_refs=[str(m) for m in audio_data.get("music_track_refs", [])],
        sfx_track_refs=[str(s) for s in audio_data.get("sfx_track_refs", [])],
        dialogue_track_refs=[str(d) for d in audio_data.get("dialogue_track_refs", [])],
    )


def _build_color_plan(color_data: dict[str, Any]) -> ColorPlan:
    """Build the color plan from raw look and per-scene fields."""
    return ColorPlan(
        look=str(color_data.get("look", "")),
        per_scene={str(k): str(v) for k, v in color_data.get("per_scene", {}).items()},
    )
