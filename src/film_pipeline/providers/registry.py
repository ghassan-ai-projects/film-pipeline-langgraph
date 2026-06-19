"""Provider registry — register, lookup by id or type."""

from __future__ import annotations

from dataclasses import dataclass, field

from film_pipeline.providers.base import BaseProviderAdapter


@dataclass
class ProviderRegistry:
    """Runtime registry of provider adapters, keyed by provider_id."""

    adapters: dict[str, BaseProviderAdapter] = field(default_factory=dict)

    def register(self, adapter: BaseProviderAdapter) -> None:
        pid = adapter.entry.provider_id
        if pid in self.adapters:
            raise ValueError(f"Provider '{pid}' already registered.")
        self.adapters[pid] = adapter

    def lookup(self, provider_id: str) -> BaseProviderAdapter | None:
        return self.adapters.get(provider_id)

    def by_type(self, provider_type: str) -> list[BaseProviderAdapter]:
        return [a for a in self.adapters.values() if a.entry.provider_type == provider_type]

    def enabled_only(self) -> list[BaseProviderAdapter]:
        return [a for a in self.adapters.values() if a.entry.enabled]

    def __len__(self) -> int:
        return len(self.adapters)
