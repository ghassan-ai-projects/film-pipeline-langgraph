"""Tests for provider credentials."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

import pytest

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
        assert _env_var_for("gemini-imagen-4") == "GOOGLE_API_KEY"
        assert _env_var_for("imagen-4") == "GOOGLE_API_KEY"

    def test_env_var_for_unknown_provider(self) -> None:
        assert _env_var_for("unknown") is None

    def test_lookup_returns_none_for_unknown_provider(self) -> None:
        assert lookup("totally-unknown-provider") is None

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


class TestSecretRedaction:
    """Prove that API keys are never leaked in error messages or logs."""

    def test_model_adapter_error_redacts_key(self) -> None:
        """Provider errors must not expose the API key in the error message."""
        from io import BytesIO

        from film_pipeline.agents.model_adapter import ModelAdapter

        # Simulate an HTTP error response that includes the key in the body
        error_body = b'{"error": "Invalid key sk-test1234abcdef", "details": "auth failed"}'

        def _error_open(req):  # type: ignore[no-untyped-def]
            import urllib.error

            http_err = urllib.error.HTTPError(
                "https://api/",
                401,
                "Unauthorized",
                None,  # type: ignore[arg-type]
                BytesIO(error_body),
            )
            raise http_err

        opener = mock.MagicMock()
        opener.open = _error_open
        adapter = ModelAdapter(http_opener=opener, api_key="sk-test1234abcdef")

        with pytest.raises(RuntimeError, match="OpenRouter chat completions failed") as exc_info:
            adapter.chat("Hello", model="test-model")

        error_msg = str(exc_info.value)
        assert "sk-test1234abcdef" not in error_msg
        assert "[REDACTED]" in error_msg

    def test_redact_openrouter_key_pattern(self) -> None:
        """OpenRouter keys (sk-...) must be redacted."""
        assert "sk-test" not in redact("Authorization: Bearer sk-test1234567890ab")
        assert "[REDACTED]" in redact("Authorization: Bearer sk-test1234567890ab")

    def test_redact_google_key_pattern(self) -> None:
        """Google API keys (AIza...) must be redacted."""
        assert "AIza" not in redact("key=AIzaSyD1234567890abcdef")
        assert "[REDACTED]" in redact("key=AIzaSyD1234567890abcdef")

    def test_redact_in_json_response(self) -> None:
        """Keys embedded in JSON responses must be redacted."""
        json_body = '{"api_key": "sk-live-1234567890abcdef", "ok": true}'
        redacted = redact(json_body)
        assert "sk-live" not in redacted
        assert "[REDACTED]" in redacted
        assert "ok" in redacted

    def test_dotenv_loading_does_not_print_keys(self, tmp_path: Path) -> None:
        """Loading .env must not write keys to stdout or stderr."""
        import sys
        from io import StringIO

        (tmp_path / ".env").write_text("OPENROUTER_API_KEY=sk-secret-12345678\n")

        captured = StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured
        try:
            with (
                mock.patch.dict(os.environ, {}, clear=True),
                mock.patch(
                    "film_pipeline.providers.credentials.Path.cwd",
                    return_value=tmp_path,
                ),
            ):
                result = lookup("seedance-openrouter")
        finally:
            sys.stderr = old_stderr

        assert result == "sk-secret-12345678"
        stderr_output = captured.getvalue()
        assert "sk-secret" not in stderr_output

    def test_lookup_does_not_log_keys(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        """lookup() must not print anything to stdout or stderr."""
        (tmp_path / ".env").write_text("OPENROUTER_API_KEY=sk-silent-12345678\n")

        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch(
                "film_pipeline.providers.credentials.Path.cwd",
                return_value=tmp_path,
            ),
        ):
            result = lookup("seedance-openrouter")

        assert result == "sk-silent-12345678"
        captured = capsys.readouterr()
        assert "sk-silent" not in captured.out
        assert "sk-silent" not in captured.err
