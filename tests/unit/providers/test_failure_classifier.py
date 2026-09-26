"""Tests for failure classifier."""

from __future__ import annotations

from film_pipeline.providers.failure_classifier import (
    FailureClassifier,
    compress_prompt_for_retry,
    is_token_limit_exceeded,
)
from film_pipeline.providers.health import ProviderHealth, ProviderHealthTracker
from film_pipeline.schemas.base import ProviderStatus


class TestFailureClassifier:
    def test_quota_exhausted(self) -> None:
        failure = FailureClassifier.classify("quota exceeded for this model")
        assert failure.status == ProviderStatus.BLOCKED_QUOTA
        assert failure.is_transient is True

    def test_credit_exhausted(self) -> None:
        failure = FailureClassifier.classify("insufficient funds on account")
        assert failure.status == ProviderStatus.BLOCKED_CREDIT
        assert failure.is_transient is False

    def test_auth_failure(self) -> None:
        failure = FailureClassifier.classify("invalid api key provided")
        assert failure.status == ProviderStatus.BLOCKED_AUTH
        assert failure.is_transient is False

    def test_auth_unauthorized(self) -> None:
        failure = FailureClassifier.classify("HTTP 401: Unauthorized")
        assert failure.status == ProviderStatus.BLOCKED_AUTH

    def test_timeout(self) -> None:
        failure = FailureClassifier.classify("connection timed out after 30s")
        assert failure.status == ProviderStatus.DEGRADED
        assert failure.is_transient is True

    def test_moderation_block(self) -> None:
        failure = FailureClassifier.classify("content policy violation: safety filter triggered")
        assert failure.status == ProviderStatus.DEGRADED
        assert failure.is_transient is False

    def test_network_failure(self) -> None:
        failure = FailureClassifier.classify("connection refused")
        assert failure.status == ProviderStatus.DEGRADED
        assert failure.is_transient is True

    def test_ambiguous(self) -> None:
        failure = FailureClassifier.classify("something strange happened")
        assert failure.status == ProviderStatus.DEGRADED
        assert failure.is_transient is True

    def test_update_health(self) -> None:
        health = ProviderHealth(provider_id="mock")
        assert health.is_healthy()
        FailureClassifier.update_health(health, "quota exceeded: too many requests (429)")
        assert not health.is_healthy()
        assert health.status == ProviderStatus.BLOCKED_QUOTA
        assert "quota" in health.blocked_reason.lower()
        assert len(health.resume_requirements) > 0

    def test_detects_provider_token_limit_errors(self) -> None:
        assert is_token_limit_exceeded(
            ValueError("context_length_exceeded: maximum context length exceeded"),
            "openai/gpt-4.1",
        )
        assert is_token_limit_exceeded(
            RuntimeError("ResourceExhausted: token count exceeds model limit"),
            "google/gemini-3-flash-preview",
        )
        assert not is_token_limit_exceeded(ValueError("bad json"), "deepseek/deepseek-chat")

    def test_compress_prompt_for_retry_preserves_task_and_output(self) -> None:
        prompt = "\n\n".join(
            [
                "# Role\nwriter",
                "# Core Task\nwrite the script",
                "# Context\n" + ("0123456789" * 100),
                "# Constraints\nkeep continuity",
                "# Output\njson schema",
            ]
        )
        compressed = compress_prompt_for_retry(prompt, factor=0.2)
        assert "# Core Task\nwrite the script" in compressed
        assert "# Output\njson schema" in compressed
        assert "context compressed for retry" in compressed
        assert len(compressed) < len(prompt)


class TestProviderHealthTracker:
    def test_register_and_get(self) -> None:
        tracker = ProviderHealthTracker()
        health = tracker.register("mock")
        assert health.provider_id == "mock"
        assert health.is_healthy()
        assert tracker.get("mock") is health

    def test_blocked_providers(self) -> None:
        tracker = ProviderHealthTracker()
        tracker.register("mock")
        tracker.register("seedance")
        mock_health = tracker.get("mock")
        assert mock_health is not None
        mock_health.mark_blocked(ProviderStatus.BLOCKED_QUOTA, "Quota exhausted")
        blocked = tracker.blocked_providers()
        assert len(blocked) == 1
        assert blocked[0].provider_id == "mock"

    def test_all_healthy_false_when_blocked(self) -> None:
        tracker = ProviderHealthTracker()
        tracker.register("mock")
        mock_health = tracker.get("mock")
        assert mock_health is not None
        mock_health.mark_blocked(ProviderStatus.BLOCKED_AUTH, "Auth error")
        assert not tracker.all_healthy()

    def test_all_healthy_true(self) -> None:
        tracker = ProviderHealthTracker()
        tracker.register("mock")
        tracker.register("seedance")
        assert tracker.all_healthy()
