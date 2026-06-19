"""KB conflict detection — authority hierarchy resolution.

Authority hierarchy: canonical > active_playbook > case_study > raw_archive.
Newer active version > older active version.
Superseded items are excluded unless explicitly requested.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from film_pipeline.kb.manifest import KBManifest
from film_pipeline.schemas._base import KbAuthority
from film_pipeline.schemas.kb import KBConflictRecord, KBExcludedRef, KBItemMetadata

AUTHORITY_RANK: dict[KbAuthority, int] = {
    KbAuthority.CANONICAL: 4,
    KbAuthority.ACTIVE_PLAYBOOK: 3,
    KbAuthority.CASE_STUDY: 2,
    KbAuthority.RAW_ARCHIVE: 1,
}


@dataclass
class KBConflictDetector:
    """Detects and resolves conflicts between KB items."""

    manifest: KBManifest

    def detect_conflicts(self, items: list[KBItemMetadata]) -> list[KBConflictRecord]:
        """Find items that conflict with each other (declared conflicts or
        same-id different versions)."""
        conflicts: list[KBConflictRecord] = []
        ids = {item.id for item in items}

        for item in items:
            for conflict_ref in item.conflicts_with:
                if conflict_ref in ids:
                    conflicts.append(
                        KBConflictRecord(
                            conflict_id=f"conflict:{item.id}:{conflict_ref}",
                            items=[item.id, conflict_ref],
                            description=f"{item.id} conflicts with {conflict_ref}",
                            detected_at=datetime.now(UTC),
                        )
                    )

        return conflicts

    def resolve_superseded(
        self, items: list[KBItemMetadata]
    ) -> tuple[list[KBItemMetadata], list[KBExcludedRef]]:
        """Filter out items that have been superseded by other items in the
        same set. Returns (kept, excluded)."""
        excluded: list[KBExcludedRef] = []
        kept: list[KBItemMetadata] = []

        superseded_set: set[str] = set()
        for item in items:
            for sup in item.supersedes:
                superseded_set.add(sup)

        for item in items:
            if item.id in superseded_set:
                excluded.append(
                    KBExcludedRef(
                        ref=item.id,
                        reason="Superseded by a newer item in the retrieval set.",
                    )
                )
            else:
                kept.append(item)

        return kept, excluded

    def resolve_authority(
        self, items: list[KBItemMetadata]
    ) -> tuple[list[KBItemMetadata], list[KBExcludedRef]]:
        """Resolve conflicts by authority: higher authority wins. When equal
        authority, newer version wins. Excluded items are recorded with
        reasons."""
        if not items:
            return [], []

        # Group by id stem (strip version suffix)
        by_stem: dict[str, list[KBItemMetadata]] = {}
        for item in items:
            stem = _id_stem(item.id)
            by_stem.setdefault(stem, []).append(item)

        kept: list[KBItemMetadata] = []
        excluded: list[KBExcludedRef] = []

        for _stem, group in by_stem.items():
            if len(group) == 1:
                kept.append(group[0])
            else:
                winner = max(
                    group,
                    key=lambda i: (
                        AUTHORITY_RANK.get(i.authority, 0),
                        i.version,
                    ),
                )
                kept.append(winner)
                for loser in group:
                    if loser.id != winner.id:
                        excluded.append(
                            KBExcludedRef(
                                ref=loser.id,
                                reason=(
                                    f"Superseded by {winner.id} "
                                    f"(higher authority: {winner.authority.value}"
                                    f" > {loser.authority.value})"
                                ),
                            )
                        )

        return kept, excluded


def _id_stem(item_id: str) -> str:
    """Strip the version suffix from a KB item id.

    Example: 'kb.policy.prompt.rctco.v1' → 'kb.policy.prompt.rctco'
    """
    parts = item_id.rsplit(".", 1)
    if len(parts) == 2 and parts[1].startswith("v") and parts[1][1:].isdigit():
        return parts[0]
    return item_id
