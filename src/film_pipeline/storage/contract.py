"""Filesystem-safe artifact identity rules."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

Renderer = Callable[[dict[str, Any]], str]

# Artifact ids are lowercase snake_case so directory names are unambiguous on
# case-insensitive filesystems.
ARTIFACT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class KindSpec:
    """Storage contract for one artifact kind."""

    artifact_id: str
    kind: str  # stable registry key, e.g. "film.studio/script"
    schema_version: int = 1
    payload_model: type[BaseModel] | None = None  # None: payload stays a plain dict
    mutable: bool = False  # mutable kinds rewrite a single file instead of versioning
    # Typed markdown view for current.md; None selects the generic renderer.
    renderer: Renderer | None = None


def validate_artifact_id(artifact_id: str) -> None:
    """Enforce the artifact id rules (lowercase snake_case, filesystem-safe)."""
    if not ARTIFACT_ID_PATTERN.match(artifact_id):
        raise ValueError(
            f"Invalid artifact id '{artifact_id}': must match {ARTIFACT_ID_PATTERN.pattern} "
            "(lowercase snake_case, no ':' or '/')."
        )


def sanitize_artifact_id(raw_id: str) -> str:
    """Map an arbitrary entity id onto a valid artifact id, injectively.

    Entity ids (proposal ids, run ids) may contain ``:`` or ``-``; artifact
    ids may not. Non-conforming characters are hex-escaped (``:`` → ``_3a_``)
    so distinct entity ids can never collide into one artifact directory.
    """
    sanitized = re.sub(r"[^a-z0-9_]", lambda match: f"_{ord(match.group()):02x}_", raw_id.lower())
    if not sanitized or not ARTIFACT_ID_PATTERN.match(sanitized):
        sanitized = f"a_{sanitized}" if sanitized else "a"
    return sanitized
