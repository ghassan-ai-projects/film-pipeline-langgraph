"""Operator-surface models.

## Why only two remain

`operations` was built as the in-process surface for a TUI
(`documentation/audit-findings.md` #8: the TUI bypassed the MCP contract through
an internal `OperatorService`). The TUI is gone
(`docs/plans/remove-tui-support.md`) and so is its client: of `OperatorService`'s
31 public methods, **6** were reached from outside this package, and all 7 view
models had **0** consumers.

`DashboardSummary`, `ReviewWorkspace`, `ValidationWorkspace`,
`GenerationWorkspace`, `AuditEvent`, `ProjectListItem`, `MutationResult`,
`ProjectCreateRequest`, `OperatorComment`/`OperatorCommentRequest`, and
`ArtifactDetail` are deleted along with the methods that produced them.

The two below stay because the surviving checkpoint rollback functions return
them and `mcp/tools/checkpoints.py` renders them. They are result records — what
a use case did — not view models.

See `docs/modularity-improvements/03-one-use-case-layer.md`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckpointRollbackResult:
    """Completed project rollback and persisted bookkeeping references."""

    rollback_target: str
    phase: str
    reason: str
    invalidation_report_ref: str
    rollback_record_ref: str


@dataclass(frozen=True)
class ArtifactRollbackResult:
    """Completed artifact restore and persisted bookkeeping references."""

    artifact_id: str
    restored_from: str
    git_commit: str
    invalidation_report_ref: str
    rollback_record_ref: str


__all__ = ["ArtifactRollbackResult", "CheckpointRollbackResult"]
