"""View models for the redesigned Textual film studio TUI.

This package keeps the shared dataclasses and artifact/scene rendering helpers
used by the new widgets. Table-specific builders from the old cockpit have been
removed along with the old presentation layer.
"""

from __future__ import annotations

from film_pipeline.tui.view_models.builders_reader import (
    build_artifact_reader,
    build_asset_action_rows,
    build_comment_thread_rows,
    build_reader_index_rows,
    build_reader_link_rows,
    build_review_checklist_rows,
    build_review_issue_rows,
    build_review_issue_targets,
    build_validation_fix_suggestions,
    build_validation_groups,
    format_fix_draft,
    format_selection_detail,
    format_targeted_revision_note,
    selection_from_row,
    validation_issue_rows,
)
from film_pipeline.tui.view_models.helpers import (
    _all_issues,
    _issue_target,
    _validation_for_target,
)
from film_pipeline.tui.view_models.models import (
    GRAPH_PHASES,
    CockpitSnapshot,
    CommandOptions,
    CommandValidation,
    MatrixImpact,
    PhaseDetail,
    ReaderView,
    ReviewIssueTarget,
    TargetSelection,
    ValidationFixSuggestion,
    ValidationGroup,
)

__all__ = [
    "GRAPH_PHASES",
    "CockpitSnapshot",
    "CommandOptions",
    "CommandValidation",
    "MatrixImpact",
    "PhaseDetail",
    "ReaderView",
    "ReviewIssueTarget",
    "TargetSelection",
    "ValidationFixSuggestion",
    "ValidationGroup",
    "_all_issues",
    "_issue_target",
    "_validation_for_target",
    "build_artifact_reader",
    "build_asset_action_rows",
    "build_comment_thread_rows",
    "build_reader_index_rows",
    "build_reader_link_rows",
    "build_review_checklist_rows",
    "build_review_issue_rows",
    "build_review_issue_targets",
    "build_validation_fix_suggestions",
    "build_validation_groups",
    "format_fix_draft",
    "format_selection_detail",
    "format_targeted_revision_note",
    "selection_from_row",
    "validation_issue_rows",
]
