"""Tests for provider credentials."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from film_pipeline.providers.credentials import (
    _env_var_for,
    _read_dotenv,
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

    def test_lookup_missing(self, tmp_path: Path) -> None:
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("film_pipeline.providers.credentials.Path.cwd", return_value=tmp_path),
        ):
            assert lookup("seedance-openrouter") is None

    def test_lookup_falls_back_to_dotenv(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("OPENROUTER_API_KEY=sk-dotenv-12345678\n")
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("film_pipeline.providers.credentials.Path.cwd", return_value=tmp_path),
        ):
            assert lookup("seedance-openrouter") == "sk-dotenv-12345678"

    def test_lookup_prefers_environment_over_dotenv(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text("OPENROUTER_API_KEY=sk-dotenv-12345678\n")
        with (
            mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-env-abcdefghi"}),
            mock.patch("film_pipeline.providers.credentials.Path.cwd", return_value=tmp_path),
        ):
            assert lookup("seedance-openrouter") == "sk-env-abcdefghi"

    def test_is_configured_true(self) -> None:
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-abc"}):
            assert is_configured("seedance-openrouter") is True

    def test_is_configured_false(self, tmp_path: Path) -> None:
        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("film_pipeline.providers.credentials.Path.cwd", return_value=tmp_path),
        ):
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

    def test_read_dotenv_ignores_comments_and_quotes(self, tmp_path: Path) -> None:
        (tmp_path / ".env").write_text(
            "# comment\n"
            "OPENROUTER_API_KEY='sk-quoted-12345678'\n"
            'GOOGLE_API_KEY="AIza1234567890xyz"\n'
        )
        values = _read_dotenv(tmp_path)
        assert values["OPENROUTER_API_KEY"] == "sk-quoted-12345678"
        assert values["GOOGLE_API_KEY"] == "AIza1234567890xyz"
