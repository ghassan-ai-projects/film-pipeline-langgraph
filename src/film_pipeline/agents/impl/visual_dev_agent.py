"""VisualDevAgent — produces a ReferenceIndex from script and constitution."""

from __future__ import annotations

import json
from typing import Any

from film_pipeline.agents.base import BaseAgent
from film_pipeline.schemas.reference import (
    ReferenceAIUsability,
    ReferenceIndex,
    ReferenceIndexEntry,
    ReferenceValidationSummary,
)


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
        # --- Normalize model output ---
        if isinstance(model_output, str):
            # Model returned raw text — attempt JSON parse
            try:
                model_output = json.loads(model_output)
            except (json.JSONDecodeError, TypeError):
                model_output = {}

        # Try extracting the nested "visual_dev" key first, then check for
        # top-level "reference_entries" or "entries" keys, and finally
        # treat the whole dict as the data container.
        data = model_output.get("visual_dev")
        if not isinstance(data, dict):
            data = model_output

        entries_data = data.get("reference_entries") or data.get("entries")
        if not isinstance(entries_data, list):
            # Model may have returned an array at top level (strategy 4 in chat_json)
            entries_data = []

        entries = [
            ReferenceIndexEntry(
                reference_id=str(e.get("reference_id", f"ref_{i:03d}")),
                asset_path=str(e.get("asset_path", "")),
                asset_type=str(e.get("asset_type", "character_identity_sheet")),
                subject_type=str(e.get("subject_type", "character")),
                subject_id=str(e.get("subject_id", "")),
                approved_for=[str(a) for a in e.get("approved_for", ["prompt_anchor"])],
                quality_score=float(e.get("quality_score", 80.0)),
                provider=str(e.get("provider", "")),
                tier=str(e.get("tier", "fast")),
                frame_role=str(e.get("frame_role", "")),
                expression=str(e.get("expression", "")),
                lighting=str(e.get("lighting", "")),
                prompt_text=str(e.get("prompt_text", e.get("notes", ""))),
                prompt_refs=[str(p) for p in e.get("prompt_refs", []) if str(p)],
                source_frames=[str(p) for p in e.get("source_frames", []) if str(p)],
                notes=str(e.get("notes", "")),
                moderation_risk=str(e.get("moderation_risk", "low")),
                validation=ReferenceValidationSummary(
                    status=str(e.get("validation", {}).get("status", "pending")),
                    score=float(e.get("validation", {}).get("score", 0.0)),
                    reports=[str(r) for r in e.get("validation", {}).get("reports", []) if str(r)],
                ),
                ai_usability=ReferenceAIUsability(
                    score=float(e.get("ai_usability", {}).get("score", 0.0)),
                    risks=[str(r) for r in e.get("ai_usability", {}).get("risks", []) if str(r)],
                    notes=str(e.get("ai_usability", {}).get("notes", "")),
                ),
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
