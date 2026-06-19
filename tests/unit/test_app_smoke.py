"""Tests for smoke test runner."""

from __future__ import annotations

from film_pipeline.app.smoke import (
    check_agent_registry,
    check_graph_compiles,
    check_kb_manifest,
    check_validator_registry,
    run_smoke_checks,
)


class TestSmokeChecks:
    def test_graph_compiles(self) -> None:
        ok, detail = check_graph_compiles()
        assert ok is True, detail

    def test_agent_registry(self) -> None:
        ok, detail = check_agent_registry()
        assert ok is True, detail
        assert "19" in detail

    def test_validator_registry(self) -> None:
        ok, detail = check_validator_registry()
        assert ok is True, detail
        assert "15" in detail

    def test_kb_manifest(self) -> None:
        from pathlib import Path

        if not Path("film-knowledge-base/index/kb-manifest.yaml").exists():
            import pytest

            pytest.skip("kb-manifest.yaml not found")
        ok, detail = check_kb_manifest()
        assert ok is True, detail

    def test_run_all_checks(self) -> None:
        results = run_smoke_checks()
        assert len(results) == 5
        for name, ok, detail in results:
            assert isinstance(name, str)
            assert isinstance(ok, bool)
            assert isinstance(detail, str)
