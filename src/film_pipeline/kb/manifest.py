"""KB manifest reader — loads and validates the KB item inventory."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from film_pipeline.schemas._base import KbAuthority
from film_pipeline.schemas.kb import KBItemMetadata


@dataclass
class KBManifest:
    """Loaded and validated KB manifest with all item metadata."""

    items: dict[str, KBItemMetadata] = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path) -> KBManifest:
        """Load manifest from a YAML file and validate every item."""
        with path.open() as fh:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}
        raw_items: list[dict[str, Any]] = raw.get("items", [])
        manifest = cls()
        for item_dict in raw_items:
            item = KBItemMetadata(**item_dict)
            manifest.items[item.id] = item
        return manifest

    def get(self, item_id: str) -> KBItemMetadata | None:
        return self.items.get(item_id)

    def by_authority(self, authority: KbAuthority) -> list[KBItemMetadata]:
        return [i for i in self.items.values() if i.authority == authority]

    def by_phase(self, phase: str) -> list[KBItemMetadata]:
        return [
            i
            for i in self.items.values()
            if "all" in i.applies_to_phases or phase in i.applies_to_phases
        ]

    def by_agent(self, agent_id: str) -> list[KBItemMetadata]:
        return [
            i
            for i in self.items.values()
            if "all" in i.applies_to_agents or agent_id in i.applies_to_agents
        ]

    def by_domain(self, domain: str) -> list[KBItemMetadata]:
        return [i for i in self.items.values() if domain in i.domains]

    def active_only(self) -> list[KBItemMetadata]:
        return [i for i in self.items.values() if i.status == "active"]

    def canonical(self) -> list[KBItemMetadata]:
        return self.by_authority(KbAuthority.CANONICAL)

    def playbooks(self) -> list[KBItemMetadata]:
        return self.by_authority(KbAuthority.ACTIVE_PLAYBOOK)

    def case_studies(self) -> list[KBItemMetadata]:
        return self.by_authority(KbAuthority.CASE_STUDY)

    def __len__(self) -> int:
        return len(self.items)

    def __contains__(self, item_id: str) -> bool:
        return item_id in self.items

    def __iter__(self) -> Iterator[KBItemMetadata]:
        return iter(self.items.values())
