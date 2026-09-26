"""Structured repair feedback — tells agents exactly what to fix.

Replaces the flat string ``_repair_feedback`` with typed per-row instructions.
Agents receive structured data specifying which rows to fix, which to preserve,
and what each fix entails.
"""

from __future__ import annotations

from pydantic import Field

from film_pipeline.schemas.base import SchemaBase


class RowRepairInstruction(SchemaBase):
    """Instruction for fixing a single matrix row."""

    shot_id: str
    issues: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of {code, field, message, recommended_action} dicts.",
    )
    preserve_other_fields: bool = Field(
        default=True,
        description="If True, only fix the listed issues. Other fields left as-is.",
    )


class GlobalRepairIssue(SchemaBase):
    """A repair issue that spans multiple rows or is not row-specific."""

    code: str
    message: str
    recommended_action: str = ""


class RepairFeedback(SchemaBase):
    """Complete repair instructions for a phase re-run."""

    repair_id: str = Field(description="Unique identifier, e.g. 'repair:shot_bible:r1'.")
    phase: str
    round: int = Field(ge=1)
    project_id: str

    failed_rows: list[RowRepairInstruction] = Field(default_factory=list)
    passed_row_ids: list[str] = Field(
        default_factory=list,
        description="Rows that passed validation and should be preserved verbatim.",
    )

    global_issues: list[GlobalRepairIssue] = Field(default_factory=list)

    validation_report_refs: list[str] = Field(default_factory=list)
    previous_artifact_ref: str = Field(default="")
    convergence_round: int = Field(default=1, ge=1, le=5)

    def to_agent_context(self) -> str:
        """Render as structured text for agent prompt injection."""
        lines: list[str] = [
            f"REPAIR ROUND {self.round}: Your previous output was REJECTED.",
            "",
        ]

        if self.passed_row_ids:
            row_list = ", ".join(self.passed_row_ids[:20])
            suffix = "..." if len(self.passed_row_ids) > 20 else ""
            lines.append(
                f"PRESERVE these {len(self.passed_row_ids)} rows verbatim "
                f"(they passed validation): {row_list}{suffix}"
            )
            lines.append("")

        if self.failed_rows:
            lines.append(f"FIX these {len(self.failed_rows)} rows:")
            for fr in self.failed_rows:
                issue_descs: list[str] = []
                for issue in fr.issues:
                    desc = f"[{issue.get('code', '?')}] {issue.get('message', '')}"
                    field = issue.get("field")
                    if field:
                        desc += f" (field: {field})"
                    action = issue.get("recommended_action")
                    if action:
                        desc += f" → {action}"
                    issue_descs.append(desc)

                preserve = " (preserve all other fields)" if fr.preserve_other_fields else ""
                lines.append(f"  {fr.shot_id}: {'; '.join(issue_descs)}{preserve}")
            lines.append("")

        if self.global_issues:
            lines.append("GLOBAL FIXES:")
            for gi in self.global_issues:
                lines.append(f"  [{gi.code}] {gi.message}")
                if gi.recommended_action:
                    lines.append(f"    → {gi.recommended_action}")

        return "\n".join(lines)
