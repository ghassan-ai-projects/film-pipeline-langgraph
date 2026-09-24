"""Artifact diff engine — compare current vs last approved version."""

from __future__ import annotations

from dataclasses import dataclass, field

from film_pipeline.schemas.artifact import ArtifactRef


@dataclass
class ArtifactDiff:
    """A structural diff between current and previous artifact sets."""

    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.changed or self.removed)

    @property
    def total_changes(self) -> int:
        return len(self.added) + len(self.changed) + len(self.removed)


def compute_artifact_diff(
    current: list[str],
    previous: list[str],
) -> ArtifactDiff:
    """Compare two artifact ref lists and produce a diff.

    Compares by id stem (stripping version suffix) so that
    ``artifact:script:S001:v2 → artifact:script:S001:v3`` is a *change*,
    not an add+remove.
    """
    cur_by_stem = {_id_stem(r): r for r in current}
    prev_by_stem = {_id_stem(r): r for r in previous}

    added: list[str] = []
    changed: list[str] = []
    removed: list[str] = []

    for stem, cur_ref in cur_by_stem.items():
        if stem not in prev_by_stem:
            added.append(cur_ref)
        elif cur_ref != prev_by_stem[stem]:
            changed.append(cur_ref)

    for stem, prev_ref in prev_by_stem.items():
        if stem not in cur_by_stem:
            removed.append(prev_ref)

    return ArtifactDiff(
        added=sorted(added),
        changed=sorted(changed),
        removed=sorted(removed),
    )


def _id_stem(artifact_ref: str) -> str:
    """Strip version suffix from an artifact ref.

    Example: 'artifact:script:S001:v3' → 'artifact:script:S001'
    """
    try:
        parsed = ArtifactRef.from_string(artifact_ref)
    except ValueError:
        return artifact_ref
    return f"artifact:{parsed.phase}:{parsed.artifact_id}"
