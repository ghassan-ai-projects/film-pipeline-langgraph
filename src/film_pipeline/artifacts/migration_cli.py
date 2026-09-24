"""Command-line entry point for the storage migration.

Usage: ``python -m film_pipeline.artifacts.migration --source <dir> \
        --target <storage-root> [--dry-run] [--confirm]``

The MCP tool ``storage_migrate`` wraps the same implementation.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from film_pipeline.artifacts.migration import (
    ConfirmationRequired,
    migrate,
    plan_migration,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate legacy project storage.")
    parser.add_argument(
        "--source",
        type=Path,
        action="append",
        required=True,
        help="A legacy root containing project directories (repeatable).",
    )
    parser.add_argument(
        "--target",
        type=Path,
        required=True,
        help="The v2 storage root (must exist or be creatable).",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the plan and exit without writing."
    )
    parser.add_argument(
        "--confirm", action="store_true", help="Confirm the migration (refused without this)."
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if args.dry_run:
        plan = plan_migration(args.source, args.target)
        print(
            json.dumps(
                {
                    "target": str(plan.target_root),
                    "projects": [
                        {
                            "project_id": p.project_id,
                            "source": str(p.source_dir),
                            "files": p.file_count,
                            "bytes": p.total_bytes,
                            "skip": p.skip_reason,
                        }
                        for p in plan.projects
                    ],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    try:
        result = migrate(args.source, args.target, confirmed=args.confirm)
    except ConfirmationRequired as exc:
        print(str(exc))
        return 2
    print(
        json.dumps(
            {
                "migrated": result.migrated,
                "skipped": result.skipped,
                "quarantined": result.quarantined,
                "failed": result.failed,
                "files_copied": result.files_copied,
                "verified": result.verified,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
