"""``storage_migrate`` — bring legacy project layouts into the v2 store.

Thin MCP wrapper over :mod:`film_pipeline.artifacts.migration` (the same
implementation backs the command-line entry point). Requires
``confirmed=True``; ``dry_run=True`` prints the plan and writes nothing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from film_pipeline.artifacts.migration import (
    ConfirmationRequired,
    MigrationError,
    migrate,
    plan_migration,
    storage_verify,
)

_OK = True


def _ok(**extra: object) -> dict[str, object]:
    return {"ok": _OK, **extra}


def _error(message: str, **extra: object) -> dict[str, object]:
    return {"ok": False, "error": message, **extra}


async def storage_migrate(args: dict[str, object]) -> dict[str, object]:
    """Plan or run the legacy→v2 storage migration."""
    raw_sources = args.get("sources") or []
    if not isinstance(raw_sources, list) or not all(isinstance(item, str) for item in raw_sources):
        return _error("sources must be a list of directory paths.")
    sources = [Path(item) for item in cast(list[str], raw_sources)]
    if not sources:
        return _error("sources is required: a list of legacy root directories.")
    target_value = str(args.get("target", "")).strip()
    if not target_value:
        return _error("target is required: the v2 storage root directory.")
    target = Path(target_value)
    dry_run = args.get("dry_run") is True
    confirmed = args.get("confirmed") is True

    if dry_run:
        plan = plan_migration(sources, target)
        return _ok(
            dry_run=True,
            target=str(plan.target_root),
            projects=[
                {
                    "project_id": p.project_id,
                    "source": str(p.source_dir),
                    "files": p.file_count,
                    "bytes": p.total_bytes,
                    "skip": p.skip_reason,
                }
                for p in plan.projects
            ],
        )

    try:
        result = migrate(sources, target, confirmed=confirmed)
    except ConfirmationRequired as exc:
        return _error(str(exc), requires_confirmation=True)
    except MigrationError as exc:
        return _error(str(exc))
    verification: dict[str, Any] = storage_verify(target)
    return _ok(
        migrated=result.migrated,
        skipped=result.skipped,
        quarantined=result.quarantined,
        failed=result.failed,
        files_copied=result.files_copied,
        verified=result.verified,
        verification=verification,
    )
