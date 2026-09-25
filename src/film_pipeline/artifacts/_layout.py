"""Compatibility aliases for :mod:`film_pipeline.storage._layout`."""

from __future__ import annotations

from film_pipeline.storage._layout import ARTIFACTS_DIRNAME as ARTIFACTS_DIRNAME
from film_pipeline.storage._layout import ASSET_MANIFEST_FILENAME as ASSET_MANIFEST_FILENAME
from film_pipeline.storage._layout import AUDIT_RELPATH as AUDIT_RELPATH
from film_pipeline.storage._layout import CHECKPOINTS_RELPATH as CHECKPOINTS_RELPATH
from film_pipeline.storage._layout import DELIVERABLES_DIRNAME as DELIVERABLES_DIRNAME
from film_pipeline.storage._layout import GITIGNORE_FILENAME as GITIGNORE_FILENAME
from film_pipeline.storage._layout import GRAPH_STATE_RELPATH as GRAPH_STATE_RELPATH
from film_pipeline.storage._layout import INDEX_DIRNAME as INDEX_DIRNAME
from film_pipeline.storage._layout import JSONL_STORAGE_VERSION as JSONL_STORAGE_VERSION
from film_pipeline.storage._layout import JSONL_STORAGE_VERSION_KEY as JSONL_STORAGE_VERSION_KEY
from film_pipeline.storage._layout import MEDIA_DIRNAME as MEDIA_DIRNAME
from film_pipeline.storage._layout import PROJECT_FILENAME as PROJECT_FILENAME
from film_pipeline.storage._layout import PROJECT_GITIGNORE as PROJECT_GITIGNORE
from film_pipeline.storage._layout import STORAGE_LOCK_FILENAME as STORAGE_LOCK_FILENAME

# Private helpers still reached through this path during migration.
from film_pipeline.storage._layout import _logger as _logger
from film_pipeline.storage._layout import append_jsonl as append_jsonl
from film_pipeline.storage._layout import ensure_project_gitignore as ensure_project_gitignore
from film_pipeline.storage._layout import jsonl_ids as jsonl_ids
from film_pipeline.storage._layout import project_relpaths as project_relpaths
from film_pipeline.storage._layout import read_json_file as read_json_file
from film_pipeline.storage._layout import read_jsonl as read_jsonl
from film_pipeline.storage._layout import write_json as write_json

__all__ = [
    "ARTIFACTS_DIRNAME",
    "ASSET_MANIFEST_FILENAME",
    "AUDIT_RELPATH",
    "CHECKPOINTS_RELPATH",
    "DELIVERABLES_DIRNAME",
    "GITIGNORE_FILENAME",
    "GRAPH_STATE_RELPATH",
    "INDEX_DIRNAME",
    "JSONL_STORAGE_VERSION",
    "JSONL_STORAGE_VERSION_KEY",
    "MEDIA_DIRNAME",
    "PROJECT_FILENAME",
    "PROJECT_GITIGNORE",
    "STORAGE_LOCK_FILENAME",
    "append_jsonl",
    "ensure_project_gitignore",
    "jsonl_ids",
    "project_relpaths",
    "read_json_file",
    "read_jsonl",
    "write_json",
]
