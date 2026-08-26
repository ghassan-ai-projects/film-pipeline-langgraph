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

    def execute(self, model_output: Any) -> dict[str, Any]:
        """Parse model output into a ReferenceIndex artifact."""
        data, entries_data = _normalized_payload(model_output)
        entries = [_build_reference_entry(e, i) for i, e in enumerate(entries_data)]
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


def _normalized_payload(model_output: Any) -> tuple[dict[str, Any], list[Any]]:
    """Normalize raw model output into (data container, reference entries).

    Attempts JSON parse for raw text, then extracts the nested "visual_dev"
    key first, then checks top-level "reference_entries" or "entries" keys,
    and finally treats the whole dict as the data container.
    """
    if isinstance(model_output, str):
        # Model returned raw text — attempt JSON parse
        try:
            model_output = json.loads(model_output)
        except (json.JSONDecodeError, TypeError):
            model_output = {}

    data = model_output.get("visual_dev")
    if not isinstance(data, dict):
        data = model_output

    entries_data = data.get("reference_entries") or data.get("entries")
    if not isinstance(entries_data, list):
        # Model may have returned an array at top level (strategy 4 in chat_json)
        entries_data = []
    return data, entries_data


def _validation_summary(entry: dict[str, Any]) -> ReferenceValidationSummary:
    """Build the validation summary sub-model from a raw entry."""
    validation_data = entry.get("validation", {})
    return ReferenceValidationSummary(
        status=str(validation_data.get("status", "pending")),
        score=float(validation_data.get("score", 0.0)),
        reports=[str(r) for r in validation_data.get("reports", []) if str(r)],
    )


def _ai_usability(entry: dict[str, Any]) -> ReferenceAIUsability:
    """Build the AI-usability sub-model from a raw entry."""
    usability_data = entry.get("ai_usability", {})
    return ReferenceAIUsability(
        score=float(usability_data.get("score", 0.0)),
        risks=[str(r) for r in usability_data.get("risks", []) if str(r)],
        notes=str(usability_data.get("notes", "")),
    )


def _build_reference_entry(entry: dict[str, Any], index: int) -> ReferenceIndexEntry:
    """Build one ReferenceIndexEntry from a raw mapping."""
    return ReferenceIndexEntry(
        reference_id=str(entry.get("reference_id", f"ref_{index:03d}")),
        asset_path=str(entry.get("asset_path", "")),
        asset_type=str(entry.get("asset_type", "character_identity_sheet")),
        subject_type=str(entry.get("subject_type", "character")),
        subject_id=str(entry.get("subject_id", "")),
        approved_for=[str(a) for a in entry.get("approved_for", ["prompt_anchor"])],
        quality_score=float(entry.get("quality_score", 80.0)),
        provider=str(entry.get("provider", "")),
        tier=str(entry.get("tier", "fast")),
        frame_role=str(entry.get("frame_role", "")),
        expression=str(entry.get("expression", "")),
        lighting=str(entry.get("lighting", "")),
        prompt_text=str(entry.get("prompt_text", entry.get("notes", ""))),
        prompt_refs=[str(p) for p in entry.get("prompt_refs", []) if str(p)],
        source_frames=[str(p) for p in entry.get("source_frames", []) if str(p)],
        notes=str(entry.get("notes", "")),
        moderation_risk=str(entry.get("moderation_risk", "low")),
        validation=_validation_summary(entry),
        ai_usability=_ai_usability(entry),
    )
