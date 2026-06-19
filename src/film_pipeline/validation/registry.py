"""Validator registry — register, lookup by scope, modality, or id.

Distinct from the Pydantic ``ValidatorRegistry`` schema (which is
serializable). This is the runtime registry backed by a dict.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from film_pipeline.schemas._base import ValidationModality, ValidationScope
from film_pipeline.schemas.registries.validator_registry import ValidatorRegistryEntry


@dataclass
class ValidatorRegistry:
    """Runtime registry of validators, keyed by validator_id."""

    entries: dict[str, ValidatorRegistryEntry] = field(default_factory=dict)

    def register(self, entry: ValidatorRegistryEntry) -> None:
        if entry.validator_id in self.entries:
            raise ValueError(f"Validator '{entry.validator_id}' already registered.")
        self.entries[entry.validator_id] = entry

    def register_many(self, entries: list[ValidatorRegistryEntry]) -> None:
        for e in entries:
            self.register(e)

    def lookup_by_id(self, validator_id: str) -> ValidatorRegistryEntry | None:
        return self.entries.get(validator_id)

    def lookup_by_scope(self, scope: ValidationScope) -> list[ValidatorRegistryEntry]:
        return [e for e in self.entries.values() if e.scope == scope]

    def lookup_by_modality(self, modality: ValidationModality) -> list[ValidatorRegistryEntry]:
        return [e for e in self.entries.values() if modality in e.modalities]

    def enabled_only(self) -> list[ValidatorRegistryEntry]:
        return [e for e in self.entries.values() if e.enabled]

    def __len__(self) -> int:
        return len(self.entries)

    def __contains__(self, validator_id: str) -> bool:
        return validator_id in self.entries
