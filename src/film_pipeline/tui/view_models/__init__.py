"""View models for the Textual operator cockpit.

This package is split into focused modules (models, builders_*, helpers) but
re-exports everything from the original ``view_models`` flat module so that
existing imports such as ``from film_pipeline.tui.view_models import X``
continue to work unchanged.
"""

from __future__ import annotations

from film_pipeline.tui.view_models.builders_command import (
    build_command_help_rows,
    build_command_options,
    build_command_suggestions,
    build_command_validation,
    complete_command_prefix,
    filter_command_suggestions,
)
from film_pipeline.tui.view_models.builders_dashboard import (
    build_dashboard_action_rows,
    build_dashboard_kpi_rows,
    summarize_attention,
)
from film_pipeline.tui.view_models.builders_matrix import (
    build_graph_rows,
    build_matrix_impact,
    build_matrix_pivot_rows,
    build_matrix_rows,
    build_phase_detail,
    build_scene_rows,
    filter_matrix_rows,
)
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
from film_pipeline.tui.view_models.builders_reading import (
    PhaseReading,
    ReadingSection,
    build_phase_reading,
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
    "PhaseReading",
    "ReaderView",
    "ReadingSection",
    "ReviewIssueTarget",
    "TargetSelection",
    "ValidationFixSuggestion",
    "ValidationGroup",
    "build_artifact_reader",
    "build_asset_action_rows",
    "build_command_help_rows",
    "build_command_options",
    "build_command_suggestions",
    "build_command_validation",
    "build_comment_thread_rows",
    "build_dashboard_action_rows",
    "build_dashboard_kpi_rows",
    "build_graph_rows",
    "build_matrix_impact",
    "build_matrix_pivot_rows",
    "build_matrix_rows",
    "build_phase_detail",
    "build_phase_reading",
    "build_reader_index_rows",
    "build_reader_link_rows",
    "build_review_checklist_rows",
    "build_review_issue_rows",
    "build_review_issue_targets",
    "build_scene_rows",
    "build_validation_fix_suggestions",
    "build_validation_groups",
    "complete_command_prefix",
    "filter_command_suggestions",
    "filter_matrix_rows",
    "format_fix_draft",
    "format_selection_detail",
    "format_targeted_revision_note",
    "selection_from_row",
    "summarize_attention",
    "validation_issue_rows",
]
