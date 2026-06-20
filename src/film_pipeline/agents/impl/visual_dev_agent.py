"""VisualDevAgent — produces visual reference plans from script and constitution."""

from __future__ import annotations

from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.reference import ReferenceIndexEntry


class VisualDevAgent(BaseAgent):
    """Creates visual development references from the script and constitution.

    Output artifact: list of ``ReferenceIndexEntry``
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
        return {"reference_entries": entries}

    def validate(self, result: dict[str, Any]) -> bool:
        entries = result.get("reference_entries")
        if not isinstance(entries, list):
            return False
        return len(entries) > 0
