"""Config resolution — the single entry point that loads, merges, and validates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from film_pipeline.config.loader import ProfileLoader, ProfileSource
from film_pipeline.config.merger import ProfileMerger
from film_pipeline.config.runtime_overrides import apply_runtime_overrides
from film_pipeline.config.validator import ConfigConflict, ConfigValidator


@dataclass
class ResolvedConfig:
    """The resolved, merged, validated configuration for a project."""

    raw: dict[str, Any]
    sources: list[ProfileSource]
    conflicts: list[ConfigConflict]

    @property
    def is_blocked(self) -> bool:
        return any(c.severity == "blocking" for c in self.conflicts)


@dataclass
class ConfigResolver:
    """Load profiles, merge them, and validate."""

    loader: ProfileLoader = field(default_factory=ProfileLoader)
    merger: ProfileMerger = field(default_factory=ProfileMerger)
    validator: ConfigValidator = field(default_factory=ConfigValidator)

    def resolve(self, names: list[str]) -> ResolvedConfig:
        """Layer profiles in order and return a validated config."""
        sources = self.loader.load_many(names)
        raw = apply_runtime_overrides(self.merger.merge(sources))
        conflicts = self.validator.validate(raw)
        return ResolvedConfig(raw=raw, sources=sources, conflicts=conflicts)
