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


_TOKEN_LIMIT_PATTERNS_BY_PROVIDER: dict[str, tuple[str, ...]] = {
    "anthropic": (
        "prompt is too long",
        "input is too long",
        "maximum context length",
    ),
    "deepseek": (
        "context_length_exceeded",
        "maximum context length",
        "too many tokens",
        "token limit",
    ),
    "gemini": (
        "input too long",
        "maximum number of tokens",
        "resourceexhausted",
        "token count exceeds",
    ),
    "openai": (
        "context_length_exceeded",
        "maximum context length",
        "reduce the length",
    ),
}

_COMMON_TOKEN_LIMIT_PATTERNS: tuple[str, ...] = (
    "context length",
    "context_length_exceeded",
    "maximum context",
    "prompt too long",
    "too many tokens",
    "token limit",
)


def is_token_limit_exceeded(exception: Exception, model_id: str = "") -> bool:
    """Return True when a provider error means the input exceeded context limits."""
    error_text = str(exception).lower()
    model_text = model_id.lower()
    for provider, patterns in _TOKEN_LIMIT_PATTERNS_BY_PROVIDER.items():
        if provider in model_text and any(pattern in error_text for pattern in patterns):
            return True
    return any(pattern in error_text for pattern in _COMMON_TOKEN_LIMIT_PATTERNS)


def compress_prompt_for_retry(prompt_text: str, *, factor: float = 0.6) -> str:
    """Reduce prompt context for a token-limit retry while preserving task/schema sections.

    This is deliberately deterministic. It does not invent summaries, and it keeps
    role, task, constraints, and output instructions intact while cutting the
    usually-largest ``# Context`` section.
    """
    safe_factor = max(0.1, min(0.9, factor))
    sections = _split_markdown_sections(prompt_text)
    if not sections:
        keep_chars = max(1, int(len(prompt_text) * safe_factor))
        return (
            f"{prompt_text[:keep_chars]}\n\n"
            f"[context compressed for retry: removed {len(prompt_text) - keep_chars} chars]"
        )

    compressed: list[str] = []
    for heading, body in sections:
        normalized = heading.strip().lower()
        if normalized == "context":
            keep_chars = max(1, int(len(body) * safe_factor))
            removed = max(0, len(body) - keep_chars)
            compressed.append(
                f"# {heading}\n{body[:keep_chars].rstrip()}\n"
                f"[context compressed for retry: removed {removed} chars]"
            )
        else:
            compressed.append(f"# {heading}\n{body.rstrip()}")
    return "\n\n".join(compressed)


def _split_markdown_sections(prompt_text: str) -> list[tuple[str, str]]:
    """Split an RCTCO-style prompt into top-level markdown sections."""
    sections: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_body: list[str] = []
    for line in prompt_text.splitlines():
        if line.startswith("# "):
            if current_heading:
                sections.append((current_heading, current_body))
            current_heading = line[2:].strip()
            current_body = []
            continue
        if current_heading:
            current_body.append(line)
    if current_heading:
        sections.append((current_heading, current_body))
    return [(heading, "\n".join(body).strip()) for heading, body in sections]
