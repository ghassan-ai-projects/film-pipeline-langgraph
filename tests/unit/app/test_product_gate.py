"""Tests for working-product gate enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from film_pipeline.app.product_gate import (
    ProductGateManifest,
    detect_stubbed_critical_tools,
    evaluate_product_gate,
    load_manifest,
)


def test_load_manifest_reads_lists(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "allowed_stub_tools": ["start_generation_batch"],
                "critical_mcp_tools": ["approve_phase"],
                "required_docs": ["docs/a.md"],
                "required_e2e_tests": ["tests/e2e/test_a.py"],
                "required_behavior_tests": ["tests/integration/test_b.py"],
            }
        )
    )

    manifest = load_manifest(manifest_path)

    assert manifest.allowed_stub_tools == frozenset({"start_generation_batch"})
    assert manifest.critical_mcp_tools == ("approve_phase",)
    assert manifest.required_docs == ("docs/a.md",)


def test_detect_stubbed_critical_tools_ignores_allowed_stubs() -> None:
    manifest = ProductGateManifest(
        allowed_stub_tools=frozenset({"start_generation_batch"}),
        critical_mcp_tools=(
            "start_generation_batch",
            "approve_phase",
            "promote_test_to_production",
        ),
        required_docs=(),
        required_e2e_tests=(),
        required_behavior_tests=(),
    )

    stubbed = detect_stubbed_critical_tools(manifest)

    assert "start_generation_batch" not in stubbed
    assert "approve_phase" not in stubbed
    assert "promote_test_to_production" in stubbed


def test_evaluate_product_gate_reports_missing_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "ok.md").write_text("ok")

    manifest = ProductGateManifest(
        allowed_stub_tools=frozenset(),
        critical_mcp_tools=(),
        required_docs=("docs/ok.md", "docs/missing.md"),
        required_e2e_tests=("tests/e2e/test_missing.py",),
        required_behavior_tests=(),
    )

    report = evaluate_product_gate(manifest)

    assert report.ok is False
    assert "docs/missing.md" in report.missing_files
    assert "tests/e2e/test_missing.py" in report.missing_files
