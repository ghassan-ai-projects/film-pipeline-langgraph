"""Tests for operational app modules — bootstrap, health, version, smoke."""

from __future__ import annotations

from pathlib import Path

import pytest

from film_pipeline.app.bootstrap import bootstrap_ok, validate_environment
from film_pipeline.app.health import HealthStatus, check_readiness
from film_pipeline.app.version import _VERSION_INFO, BUILD_LABEL, __version__


class TestBootstrap:
    def test_validate_environment_empty(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """In an empty tmp_path, bootstrap should report issues."""
        monkeypatch.chdir(tmp_path)
        issues = validate_environment()
        assert len(issues) >= 1  # profiles/ and KB manifest missing

    def test_bootstrap_ok_false_when_issues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        assert bootstrap_ok() is False

    def test_validate_environment_with_profiles(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "profiles").mkdir()
        (tmp_path / "film-knowledge-base").mkdir()
        (tmp_path / "film-knowledge-base" / "manifest.yaml").write_text("items: []")
        issues = validate_environment()
        # Still missing artifacts checks, but profiles + KB manifest exist
        assert all("profiles/" not in i for i in issues)
        assert all("manifest.yaml" not in i for i in issues)

    def test_bootstrap_ok_true(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "profiles").mkdir()
        (tmp_path / "film-knowledge-base").mkdir()
        (tmp_path / "film-knowledge-base" / "manifest.yaml").write_text("items: []")
        assert bootstrap_ok() is True

    def test_validate_environment_requires_openrouter_key_in_real_mode(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("FILM_PIPELINE_MCP_MODE", "real")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        (tmp_path / "profiles").mkdir()
        (tmp_path / "film-knowledge-base").mkdir()
        (tmp_path / "film-knowledge-base" / "manifest.yaml").write_text("items: []")
        issues = validate_environment()
        assert any("OPENROUTER_API_KEY" in issue for issue in issues)

    def test_validate_environment_requires_zai_key_in_real_mode(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Real mode now demands ZAI_API_KEY — chat agents default to z.ai GLM."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("FILM_PIPELINE_MCP_MODE", "real")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-12345678")
        monkeypatch.delenv("ZAI_API_KEY", raising=False)
        monkeypatch.setattr("film_pipeline.providers.credentials._read_dotenv", lambda _root: {})
        (tmp_path / "profiles").mkdir()
        (tmp_path / "film-knowledge-base").mkdir()
        (tmp_path / "film-knowledge-base" / "manifest.yaml").write_text("items: []")
        issues = validate_environment()
        assert any("ZAI_API_KEY" in issue for issue in issues)

    def test_validate_environment_real_mode_ok_with_all_keys(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("FILM_PIPELINE_MCP_MODE", "real")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-12345678")
        monkeypatch.setenv("ZAI_API_KEY", "zai-test-12345678")
        (tmp_path / "profiles").mkdir()
        (tmp_path / "film-knowledge-base").mkdir()
        (tmp_path / "film-knowledge-base" / "manifest.yaml").write_text("items: []")
        (tmp_path / "artifacts").mkdir()
        issues = validate_environment()
        assert issues == []

    def test_validate_environment_accepts_credentials_from_dotenv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Bootstrap and adapters must agree when credentials live in .env."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("FILM_PIPELINE_MCP_MODE", "real")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("ZAI_API_KEY", raising=False)
        (tmp_path / ".env").write_text(
            "OPENROUTER_API_KEY=sk-dotenv-12345678\nZAI_API_KEY=zai-dotenv-12345678\n"
        )
        (tmp_path / "profiles").mkdir()
        (tmp_path / "film-knowledge-base").mkdir()
        (tmp_path / "film-knowledge-base" / "manifest.yaml").write_text("items: []")
        (tmp_path / "artifacts").mkdir()

        assert validate_environment() == []

    def test_validate_environment_rejects_artifacts_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "profiles").mkdir()
        (tmp_path / "film-knowledge-base").mkdir()
        (tmp_path / "film-knowledge-base" / "manifest.yaml").write_text("items: []")
        (tmp_path / "artifacts").write_text("not a directory")

        issues = validate_environment()

        assert "artifacts exists but is not a directory." in issues

    def test_validate_environment_reports_unwritable_artifacts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / "profiles").mkdir()
        (tmp_path / "film-knowledge-base").mkdir()
        (tmp_path / "film-knowledge-base" / "manifest.yaml").write_text("items: []")
        (tmp_path / "artifacts").mkdir()

        def fail_touch(self: Path) -> None:
            if self.name == ".write_test":
                raise OSError("denied")
            Path.touch(self)

        monkeypatch.setattr(Path, "touch", fail_touch)

        issues = validate_environment()

        assert "Cannot write to artifacts/ directory." in issues


class TestHealth:
    def test_health_status_default(self) -> None:
        hs = HealthStatus()
        assert hs.ready is False
        assert hs.checks == {}
        assert hs.messages == []

    def test_check_readiness(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        status = check_readiness()
        assert isinstance(status, HealthStatus)
        assert status.ready is False  # missing profiles + KB in tmp

    def test_check_readiness_reports_degraded_provider(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import film_pipeline.app.bootstrap as bootstrap
        import film_pipeline.app.runtime as runtime
        import film_pipeline.kb.paths as kb_paths

        class FakeRuntime:
            def list_providers(self) -> list[str]:
                return ["veo", "imagen"]

            def get_provider_health(self, provider_id: str) -> dict[str, str] | None:
                if provider_id == "veo":
                    return {"status": "degraded"}
                return {"status": "healthy"}

        kb_manifest = tmp_path / "kb.yaml"
        kb_manifest.write_text("items: []")
        monkeypatch.setattr(bootstrap, "validate_environment", list)
        monkeypatch.setattr(kb_paths, "kb_manifest_path", lambda: kb_manifest)
        monkeypatch.setattr(runtime, "get_runtime", lambda: FakeRuntime())

        status = check_readiness()

        assert status.ready is False
        assert status.checks == {"bootstrap": True, "providers": False, "kb": True}
        assert "Provider 'veo' status: degraded" in status.messages

    def test_check_readiness_with_no_providers_and_existing_kb(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import film_pipeline.app.bootstrap as bootstrap
        import film_pipeline.app.runtime as runtime
        import film_pipeline.kb.paths as kb_paths

        class FakeRuntime:
            def list_providers(self) -> list[str]:
                return []

        kb_manifest = tmp_path / "kb.yaml"
        kb_manifest.write_text("items: []")
        monkeypatch.setattr(bootstrap, "validate_environment", list)
        monkeypatch.setattr(kb_paths, "kb_manifest_path", lambda: kb_manifest)
        monkeypatch.setattr(runtime, "get_runtime", lambda: FakeRuntime())

        status = check_readiness()

        assert status.ready is True
        assert status.checks == {"bootstrap": True, "providers": True, "kb": True}
        assert status.messages == []

    def test_check_readiness_includes_bootstrap_and_kb_messages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import film_pipeline.app.bootstrap as bootstrap
        import film_pipeline.app.runtime as runtime
        import film_pipeline.kb.paths as kb_paths

        class FakeRuntime:
            def list_providers(self) -> list[str]:
                return []

        missing_kb = tmp_path / "missing.yaml"
        monkeypatch.setattr(bootstrap, "validate_environment", lambda: ["profiles missing"])
        monkeypatch.setattr(kb_paths, "kb_manifest_path", lambda: missing_kb)
        monkeypatch.setattr(runtime, "get_runtime", lambda: FakeRuntime())

        status = check_readiness()

        assert status.ready is False
        assert status.checks == {"bootstrap": False, "providers": True, "kb": False}
        assert status.messages == ["profiles missing", "KB manifest not found."]


class TestVersion:
    def test_version_string(self) -> None:
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_build_label(self) -> None:
        assert isinstance(BUILD_LABEL, str)

    def test_version_info(self) -> None:
        assert _VERSION_INFO["version"] == __version__
        assert _VERSION_INFO["build_label"] == BUILD_LABEL
