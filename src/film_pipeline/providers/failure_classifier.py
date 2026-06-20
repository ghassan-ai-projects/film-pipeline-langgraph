"""Failure classifier — maps provider errors to categorized health states."""

from __future__ import annotations

from dataclasses import dataclass

from film_pipeline.providers.health import ProviderHealth
from film_pipeline.schemas._base import ProviderStatus


@dataclass
class ClassifiedFailure:
    """A classified provider failure with severity and recommended action."""

    status: ProviderStatus
    reason: str
    resume_requirements: list[str]
    is_transient: bool  # True if retrying may help


class FailureClassifier:
    """Classify provider errors into health states and recovery actions.

    Maps exception messages and error codes to ``ProviderStatus`` categories.
    Used by the MCP tools and graph nodes to update provider health on failure.
    """

    # ── quota ────────────────────────────────────────────────────────

    _QUOTA_PATTERNS = (
        "quota exceeded",
        "rate limit",
        "too many requests",
        "429",
        "quota_exhausted",
    )

    # ── credit ───────────────────────────────────────────────────────

    _CREDIT_PATTERNS = (
        "insufficient funds",
        "credit exceeded",
        "billing issue",
        "payment required",
        "402",
    )

    # ── auth ─────────────────────────────────────────────────────────

    _AUTH_PATTERNS = (
        "unauthorized",
        "invalid api key",
        "authentication failed",
        "forbidden",
        "403",
        "401",
        "auth_error",
    )

    # ── timeout ──────────────────────────────────────────────────────

    _TIMEOUT_PATTERNS = (
        "timeout",
        "timed out",
        "connection reset",
        "read timeout",
        "connect timeout",
    )

    # ── moderation ───────────────────────────────────────────────────

    _MODERATION_PATTERNS = (
        "content policy",
        "safety filter",
        "moderation",
        "blocked by policy",
        "inappropriate content",
        "content_filter",
    )

    # ── network ──────────────────────────────────────────────────────

    _NETWORK_PATTERNS = (
        "connection refused",
        "name resolution",
        "dns",
        "network unreachable",
        "host unreachable",
        "no route to host",
        "socket error",
    )

    @classmethod
    def classify(cls, error_message: str) -> ClassifiedFailure:
        """Classify an error message string into a failure category.

        Returns a ``ClassifiedFailure`` with status, reason, and recovery info.
        """
        msg_lower = error_message.lower()

        # Check quota
        if any(p in msg_lower for p in cls._QUOTA_PATTERNS):
            return ClassifiedFailure(
                status=ProviderStatus.BLOCKED_QUOTA,
                reason=f"Quota exhausted: {error_message[:120]}",
                resume_requirements=["Wait for quota refresh or upgrade plan."],
                is_transient=True,
            )

        # Check credit
        if any(p in msg_lower for p in cls._CREDIT_PATTERNS):
            return ClassifiedFailure(
                status=ProviderStatus.BLOCKED_CREDIT,
                reason=f"Credit exhausted: {error_message[:120]}",
                resume_requirements=["Add credits or update billing."],
                is_transient=False,
            )

        # Check auth
        if any(p in msg_lower for p in cls._AUTH_PATTERNS):
            return ClassifiedFailure(
                status=ProviderStatus.BLOCKED_AUTH,
                reason=f"Authentication failure: {error_message[:120]}",
                resume_requirements=["Check API key or credentials."],
                is_transient=False,
            )

        # Check timeout
        if any(p in msg_lower for p in cls._TIMEOUT_PATTERNS):
            return ClassifiedFailure(
                status=ProviderStatus.DEGRADED,
                reason=f"Timeout: {error_message[:120]}",
                resume_requirements=["Retry with backoff or check network."],
                is_transient=True,
            )

        # Check moderation
        if any(p in msg_lower for p in cls._MODERATION_PATTERNS):
            return ClassifiedFailure(
                status=ProviderStatus.DEGRADED,
                reason=f"Moderation block: {error_message[:120]}",
                resume_requirements=["Review prompt content and retry."],
                is_transient=False,
            )

        # Check network
        if any(p in msg_lower for p in cls._NETWORK_PATTERNS):
            return ClassifiedFailure(
                status=ProviderStatus.DEGRADED,
                reason=f"Network failure: {error_message[:120]}",
                resume_requirements=["Check connectivity and retry."],
                is_transient=True,
            )

        # Ambiguous
        return ClassifiedFailure(
            status=ProviderStatus.DEGRADED,
            reason=f"Ambiguous failure: {error_message[:120]}",
            resume_requirements=["Investigate logs and retry."],
            is_transient=True,
        )

    @classmethod
    def update_health(cls, health: ProviderHealth, error_message: str) -> None:
        """Classify an error and update the ProviderHealth accordingly."""
        failure = cls.classify(error_message)
        health.mark_blocked(failure.status, failure.reason)
        health.resume_requirements = failure.resume_requirements
