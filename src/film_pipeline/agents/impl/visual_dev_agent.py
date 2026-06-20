"""VisualDevAgent — produces a ReferenceIndex from script and constitution."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.reference import ReferenceIndex, ReferenceIndexEntry


class VisualDevAgent(BaseAgent):
    """Creates visual development references from the script and constitution.

    Output artifact: ``ReferenceIndex``
    """

    def prepare(
        self,
        state: dict[str, Any],
        kb_context: object,
        task: str,
    ) -> dict[str, Any]:
        _ = kb_context
        project_id = str(state.get("project_id", ""))
        script_ref = str(state.get("script_ref", ""))
        constitution_ref = str(state.get("constitution_ref", ""))
        return {
            "project_id": project_id,
            "script_ref": script_ref,
            "constitution_ref": constitution_ref,
            "task": task,
        }

    def execute(self, model_output: dict[str, Any]) -> dict[str, Any]:
        data = model_output.get("visual_dev", model_output)
        entries_data = data.get("reference_entries", data.get("entries", []))
        entries = [
            ReferenceIndexEntry(
                reference_id=str(e.get("reference_id", f"ref_{i:03d}")),
                asset_path=str(e.get("asset_path", "")),
                asset_type=str(e.get("asset_type", "character_identity_sheet")),
                subject_type=str(e.get("subject_type", "character")),
                subject_id=str(e.get("subject_id", "")),
                approved_for=[str(a) for a in e.get("approved_for", ["prompt_anchor"])],
                quality_score=float(e.get("quality_score", 80.0)),
                notes=str(e.get("notes", "")),
            )
            for i, e in enumerate(entries_data)
        ]
        reference_index = ReferenceIndex(
            project_id=str(data.get("project_id", "")),
            entries=entries,
        )
        return {"reference_index": reference_index}

    def validate(self, result: dict[str, Any]) -> bool:
        index = result.get("reference_index")
        if not isinstance(index, ReferenceIndex):
            return False
        return len(index.entries) > 0
