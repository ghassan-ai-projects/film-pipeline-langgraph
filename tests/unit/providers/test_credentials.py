"""Tests for provider credentials."""

from __future__ import annotations

import os
from unittest import mock

from film_pipeline.providers.credentials import (
    _env_var_for,
    is_configured,
    lookup,
    redact,
)


class TestCredentials:
    def test_env_var_for_known_provider(self) -> None:
        assert _env_var_for("seedance-openrouter") == "OPENROUTER_API_KEY"
        assert _env_var_for("veo-fast") == "GOOGLE_API_KEY"

    def test_env_var_for_unknown_provider(self) -> None:
        assert _env_var_for("unknown") is None

    def test_lookup_returns_key(self) -> None:
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-test-1234"}):
            assert lookup("seedance-openrouter") == "sk-test-1234"

    def test_lookup_missing(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            assert lookup("seedance-openrouter") is None

    def test_is_configured_true(self) -> None:
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-abc"}):
            assert is_configured("seedance-openrouter") is True

    def test_is_configured_false(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            assert is_configured("seedance-openrouter") is False

    def test_redact_replaces_keys(self) -> None:
        text = "Error: key sk-test1234abcde failed. Also AIza1234567890xyz here."
        redacted = redact(text)
        assert "sk-test1234abcde" not in redacted
        assert "AIza1234567890xyz" not in redacted
        assert "[REDACTED]" in redacted

    def test_redact_no_keys(self) -> None:
        text = "No credentials here, just normal text."
        assert redact(text) == text

    def test_redact_key_prefix_only(self) -> None:
        text = "Using key-abcdefghijklmnop"
        assert "key-" not in redact(text)
        assert "[REDACTED]" in redact(text)
