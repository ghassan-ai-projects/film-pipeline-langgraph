"""Tests for operational app modules — bootstrap, health, version, smoke."""

from __future__ import annotations

from pathlib import Path

from film_pipeline.app.bootstrap import bootstrap_ok, validate_environment
from film_pipeline.app.health import HealthStatus, check_readiness
from film_pipeline.app.version import __version__, BUILD_LABEL, _VERSION_INFO


class TestBootstrap:
    def test_validate_environment_empty(self, tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
        """In an empty tmp_path, bootstrap should report issues."""
        monkeypatch.chdir(tmp_path)
        issues = validate_environment()
        assert len(issues) >= 1  # profiles/ and KB manifest missing

    def test_bootstrap_ok_false_when_issues(self, tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        assert bootstrap_ok() is False

    def test_validate_environment_with_profiles(self, tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        (tmp_path / "profiles").mkdir()
        (tmp_path / "film-knowledge-base").mkdir()
        (tmp_path / "film-knowledge-base" / "manifest.yaml").write_text("items: []")
        issues = validate_environment()
        # Still missing artifacts checks, but profiles + KB manifest exist
        assert all("profiles/" not in i for i in issues)
        assert all("manifest.yaml" not in i for i in issues)

    def test_bootstrap_ok_true(self, tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        (tmp_path / "profiles").mkdir()
        (tmp_path / "film-knowledge-base").mkdir()
        (tmp_path / "film-knowledge-base" / "manifest.yaml").write_text("items: []")
        assert bootstrap_ok() is True


class TestHealth:
    def test_health_status_default(self) -> None:
        hs = HealthStatus()
        assert hs.ready is False
        assert hs.checks == {}
        assert hs.messages == []

    def test_check_readiness(self, tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
        monkeypatch.chdir(tmp_path)
        status = check_readiness()
        assert isinstance(status, HealthStatus)
        assert status.ready is False  # missing profiles + KB in tmp


class TestVersion:
    def test_version_string(self) -> None:
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_build_label(self) -> None:
        assert isinstance(BUILD_LABEL, str)

    def test_version_info(self) -> None:
        assert _VERSION_INFO["version"] == __version__
        assert _VERSION_INFO["build_label"] == BUILD_LABEL
