"""Checkpointing, resume snapshots, invalidation engine, and rollback.

Git is the underlying versioning backend. The pipeline adds semantic
checkpoint metadata on top.
"""

from __future__ import annotations
