"""Tests for provider registry and health tracker."""

from __future__ import annotations

from film_pipeline.providers.health import ProviderHealth, ProviderHealthTracker
from film_pipeline.providers.mock_provider import MockVideoProvider
from film_pipeline.providers.registry import ProviderRegistry
from film_pipeline.schemas._base import ProviderStatus
from film_pipeline.schemas.registries.provider_registry import (
    ProviderRegistryEntry,
)


def _make_entry(
    provider_id: str = "test",
    provider_type: str = "video",
    enabled: bool = True,
) -> ProviderRegistryEntry:
    return ProviderRegistryEntry(
        provider_id=provider_id,
        provider_type=provider_type,
        models=["mock"],
        enabled=enabled,
    )


class TestProviderRegistry:
    def test_register_and_lookup(self) -> None:
        reg = ProviderRegistry()
        provider = MockVideoProvider(entry=_make_entry("mock-video"))
        reg.register(provider)
        assert len(reg) == 1
        assert reg.lookup("mock-video") is provider

    def test_register_duplicate_raises(self) -> None:
        reg = ProviderRegistry()
        reg.register(MockVideoProvider(entry=_make_entry("dup")))
        try:
            reg.register(MockVideoProvider(entry=_make_entry("dup")))
            raise AssertionError("Expected ValueError")
        except ValueError:
            pass

    def test_by_type(self) -> None:
        reg = ProviderRegistry()
        reg.register(MockVideoProvider(entry=_make_entry("v1", "video")))
        reg.register(MockVideoProvider(entry=_make_entry("v2", "video")))
        videos = reg.by_type("video")
        assert len(videos) == 2

    def test_enabled_only(self) -> None:
        reg = ProviderRegistry()
        reg.register(MockVideoProvider(entry=_make_entry("v1", enabled=False)))
        reg.register(MockVideoProvider(entry=_make_entry("v2")))
        assert len(reg.enabled_only()) == 1


class TestProviderHealth:
    def test_initial_state(self) -> None:
        h = ProviderHealth(provider_id="p1")
        assert h.is_healthy() is True
        assert h.is_blocked() is False

    def test_mark_blocked(self) -> None:
        h = ProviderHealth(provider_id="p1")
        h.mark_blocked(ProviderStatus.BLOCKED_QUOTA, "Out of credits")
        assert h.is_healthy() is False
        assert h.is_blocked() is True
        assert h.blocked_reason == "Out of credits"

    def test_mark_healthy(self) -> None:
        h = ProviderHealth(provider_id="p1")
        h.mark_blocked(ProviderStatus.BLOCKED_AUTH, "Bad key")
        h.mark_healthy()
        assert h.is_healthy() is True


class TestProviderHealthTracker:
    def test_register_and_get(self) -> None:
        tracker = ProviderHealthTracker()
        tracker.register("p1")
        assert tracker.get("p1") is not None
        assert tracker.get("p1").provider_id == "p1"  # type: ignore[union-attr]

    def test_all_healthy(self) -> None:
        tracker = ProviderHealthTracker()
        tracker.register("p1")
        tracker.register("p2")
        assert tracker.all_healthy() is True

    def test_blocked_providers(self) -> None:
        tracker = ProviderHealthTracker()
        tracker.register("p1")
        tracker.register("p2")
        tracker.get("p1").mark_blocked(ProviderStatus.BLOCKED_QUOTA, "none")  # type: ignore[union-attr]
        blocked = tracker.blocked_providers()
        assert len(blocked) == 1
        assert blocked[0].provider_id == "p1"

    def test_record_successful_job(self) -> None:
        tracker = ProviderHealthTracker()
        tracker.register("p1")
        h = tracker.get("p1")
        assert h is not None
        assert h.last_successful_job_at is None
        tracker.record_successful_job("p1")
        assert tracker.get("p1").last_successful_job_at is not None  # type: ignore[union-attr]
