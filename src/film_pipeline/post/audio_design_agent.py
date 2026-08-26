"""Audio design agent — creates audio plan for music, SFX, dialogue."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

# Placeholder timeline until real media probing exists: scenes are spaced
# evenly and dialogue/SFX get fixed slot lengths.
_SCENE_SPACING_SECONDS = 30.0
_DIALOGUE_SLOT_SECONDS = 25.0
_SFX_SLOT_SECONDS = 5.0


@dataclass
class AudioTrack:
    """A single audio track in the plan."""

    track_id: str
    kind: str  # music, sfx, dialogue
    start_seconds: float = 0.0
    duration_seconds: float = 0.0
    source: str = ""
    notes: str = ""


@dataclass
class AudioPlan:
    """An audio plan for the full film."""

    plan_id: str
    project_id: str
    tracks: list[AudioTrack] = field(default_factory=list)
    total_tracks: int = 0
    notes: list[str] = field(default_factory=list)


def _append_dialogue_tracks(plan: AudioPlan, scene_count: int, dialogue: dict[str, bool]) -> None:
    for i in range(scene_count):
        scene_id = f"S{i + 1:03d}"
        if dialogue.get(scene_id, True):
            plan.tracks.append(
                AudioTrack(
                    track_id=f"dialogue-{scene_id}",
                    kind="dialogue",
                    start_seconds=i * _SCENE_SPACING_SECONDS,
                    duration_seconds=_DIALOGUE_SLOT_SECONDS,
                    source=f"script/{scene_id}/audio",
                )
            )


def _append_music_track(plan: AudioPlan, total_duration: float) -> None:
    plan.tracks.append(
        AudioTrack(
            track_id="music-main",
            kind="music",
            start_seconds=0.0,
            duration_seconds=total_duration,
            source="score/main-theme.wav",
        )
    )


def _append_sfx_tracks(plan: AudioPlan, scene_count: int) -> None:
    for i in range(scene_count):
        plan.tracks.append(
            AudioTrack(
                track_id=f"sfx-scene-{i + 1:03d}",
                kind="sfx",
                start_seconds=i * _SCENE_SPACING_SECONDS,
                duration_seconds=_SFX_SLOT_SECONDS,
                notes="Ambient + spot effects",
            )
        )


@dataclass
class AudioDesignAgent:
    """Creates an audio plan based on scene types and emotional arc.

    Produces an AudioPlan for the real pipeline to execute with ffmpeg.
    """

    def plan_audio(
        self,
        project_id: str,
        scene_count: int,
        total_duration: float,
        has_dialogue: dict[str, bool] | None = None,
    ) -> AudioPlan:
        """Generate an audio plan for the given film parameters.

        Args:
            project_id: The film project identifier.
            scene_count: Number of scenes.
            total_duration: Total film duration in seconds.
            has_dialogue: Optional dict mapping scene_id to whether it has dialogue.
        """
        plan = AudioPlan(
            plan_id=f"audio-plan:{project_id}:{uuid4().hex[:8]}",
            project_id=project_id,
        )

        _append_dialogue_tracks(plan, scene_count, has_dialogue or {})
        _append_music_track(plan, total_duration)
        _append_sfx_tracks(plan, scene_count)

        plan.total_tracks = len(plan.tracks)
        if plan.total_tracks == 0:
            plan.notes.append("No audio tracks generated. Check input parameters.")

        return plan
