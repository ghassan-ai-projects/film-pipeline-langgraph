"""Profile loading, merging, and resolution.

Profiles are composable YAML files under ``profiles/``. The loader layers
them in order: ``base.studio`` → film-type → quality → provider → review →
project override. Later values override earlier ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ProfileSource:
    """A resolved profile source with its origin path."""

    name: str
    path: Path
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProfileLoader:
    """Load profiles from the ``profiles/`` directory."""

    profiles_dir: Path = Path("profiles")

    def load(self, name: str) -> ProfileSource:
        """Load a profile by name (with or without ``.yaml`` suffix)."""
        fname = name if name.endswith(".yaml") else f"{name}.yaml"
        path = self.profiles_dir / fname
        if not path.exists():
            raise FileNotFoundError(f"Profile not found: {path}")
        with path.open() as fh:
            raw: dict[str, Any] = yaml.safe_load(fh) or {}
        return ProfileSource(name=name, path=path, raw=raw)

    def load_many(self, names: list[str]) -> list[ProfileSource]:
        return [self.load(n) for n in names]

    def all_names(self) -> list[str]:
        return sorted(
            [p.stem for p in self.profiles_dir.glob("*.yaml")]
            + [p.stem for p in self.profiles_dir.glob("*.yml")]
        )
