"""Subtitle agent — generates SRT subtitle data from script."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class SubtitleCue:
    """A single subtitle cue."""

    index: int
    start: str  # HH:MM:SS,mmm
    end: str
    text: str


@dataclass
class SubtitlePlan:
    """A subtitle plan with all cues."""

    plan_id: str
    project_id: str
    cues: list[SubtitleCue] = field(default_factory=list)
    language: str = "en"
    cue_count: int = 0

    def to_srt(self) -> str:
        """Render to SRT format."""
        lines: list[str] = []
        for cue in self.cues:
            lines.append(str(cue.index))
            lines.append(f"{cue.start} --> {cue.end}")
            lines.append(cue.text)
            lines.append("")
        return "\n".join(lines)


@dataclass
class SubtitleAgent:
    """Generates subtitle cues from dialogue lines and timestamps.

    Produces a SubtitlePlan and can persist the SRT content as an artifact.
    """

    def generate_subtitles(
        self,
        project_id: str,
        dialogue_lines: list[str],
        duration_per_line: float = 5.0,
        language: str = "en",
    ) -> SubtitlePlan:
        """Generate a subtitle plan from dialogue lines."""
        plan = SubtitlePlan(
            plan_id=f"subtitle:{project_id}:{uuid4().hex[:8]}",
            project_id=project_id,
            language=language,
        )

        for i, line in enumerate(dialogue_lines):
            start_time = _format_time(i * duration_per_line)
            end_time = _format_time((i + 1) * duration_per_line - 0.5)
            plan.cues.append(SubtitleCue(index=i + 1, start=start_time, end=end_time, text=line))

        plan.cue_count = len(plan.cues)
        return plan

    def persist(
        self,
        plan: SubtitlePlan,
        artifact_store: Any,
    ) -> str:
        """Persist the subtitle SRT content as a versioned artifact.

        Returns the artifact reference string.
        """
        from datetime import UTC, datetime

        from film_pipeline.schemas._base import ArtifactStatus, ArtifactType, FilmPhase
        from film_pipeline.schemas.artifact import ArtifactMetadata

        artifact_id = "subtitles"
        data = {
            "plan_id": plan.plan_id,
            "project_id": plan.project_id,
            "language": plan.language,
            "cue_count": plan.cue_count,
            "srt_content": plan.to_srt(),
            "cues": [
                {"index": c.index, "start": c.start, "end": c.end, "text": c.text}
                for c in plan.cues
            ],
        }
        meta = ArtifactMetadata(
            artifact_id=artifact_id,
            artifact_type=ArtifactType.SUBTITLE,
            project_id=plan.project_id,
            phase=FilmPhase("post"),
            version=1,
            status=ArtifactStatus.CANDIDATE,
            parents=[],
            created_by="subtitle-agent",
            created_at=datetime.now(UTC),
        )
        artifact_store.save_dict(data, meta)
        return f"artifact:{artifact_id}:v1"


def _format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"
