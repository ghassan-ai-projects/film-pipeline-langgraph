"""Tests for working-product gate enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from film_pipeline.cli.product_gate import (
    ProductGateManifest,
    ProductGateReport,
    detect_stubbed_critical_tools,
    evaluate_product_gate,
    load_manifest,
    load_plan_manifest,
    main,
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


def test_load_manifest_rejects_non_mapping(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text("- not\n- mapping\n")

    with pytest.raises(ValueError, match="must be a mapping"):
        load_manifest(manifest_path)


def test_load_manifest_rejects_non_string_lists(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "allowed_stub_tools": [123],
                "critical_mcp_tools": [],
                "required_docs": [],
                "required_e2e_tests": [],
                "required_behavior_tests": [],
            }
        )
    )

    with pytest.raises(ValueError, match="allowed_stub_tools"):
        load_manifest(manifest_path)


def test_load_plan_manifest_reads_plan_keys(tmp_path: Path) -> None:
    manifest_path = tmp_path / "plan-manifest.yaml"
    manifest_path.write_text(
        yaml.safe_dump(
            {
                "allowed_stub_behaviors": ["costly_video_generation_execution_only"],
                "critical_mcp_tools": [],
                "required_docs": ["docs/plan/README.md"],
                "required_e2e_scenarios": ["tests/e2e/test_scenario_01.py"],
            }
        )
    )

    manifest = load_plan_manifest(manifest_path)
    assert manifest is not None
    assert manifest.allowed_stub_tools == frozenset({"costly_video_generation_execution_only"})
    assert manifest.required_docs == ("docs/plan/README.md",)
    assert manifest.required_e2e_tests == ("tests/e2e/test_scenario_01.py",)


def test_load_plan_manifest_returns_none_for_missing_file() -> None:
    assert load_plan_manifest(Path("nonexistent/manifest.yaml")) is None


def test_load_plan_manifest_returns_none_for_invalid_shape(tmp_path: Path) -> None:
    manifest_path = tmp_path / "plan-manifest.yaml"
    manifest_path.write_text("- invalid\n")

    assert load_plan_manifest(manifest_path) is None


def test_detect_stubbed_critical_tools_ignores_allowed_stubs() -> None:
    manifest = ProductGateManifest(
        allowed_stub_tools=frozenset({"start_generation_batch"}),
        critical_mcp_tools=(
            "start_generation_batch",
            "approve_phase",
            "approve_coverage_generation",
        ),
        required_docs=(),
        required_e2e_tests=(),
        required_behavior_tests=(),
    )

    stubbed = detect_stubbed_critical_tools(manifest)

    assert "start_generation_batch" not in stubbed
    assert "approve_phase" not in stubbed
    assert "approve_coverage_generation" in stubbed


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


def test_evaluate_product_gate_merges_plan_manifest_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "ok.md").write_text("ok")
    (tmp_path / "docs" / "plan").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "plan" / "README.md").write_text("plan")

    manifest = ProductGateManifest(
        allowed_stub_tools=frozenset(),
        critical_mcp_tools=(),
        required_docs=("docs/ok.md",),
        required_e2e_tests=(),
        required_behavior_tests=(),
    )
    plan_manifest = ProductGateManifest(
        allowed_stub_tools=frozenset(),
        critical_mcp_tools=(),
        required_docs=("docs/plan/README.md", "docs/plan/missing.md"),
        required_e2e_tests=(),
        required_behavior_tests=(),
    )

    report = evaluate_product_gate(manifest, plan_manifest)

    assert report.ok is False
    assert "docs/plan/missing.md" in report.missing_files


def test_evaluate_product_gate_plan_manifest_missing_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    manifest = ProductGateManifest(
        allowed_stub_tools=frozenset(),
        critical_mcp_tools=(),
        required_docs=(),
        required_e2e_tests=(),
        required_behavior_tests=(),
    )

    report = evaluate_product_gate(manifest, None)

    assert report.ok is False
    assert report.plan_manifest_missing is True


def test_product_gate_report_lines_for_pass_and_fail() -> None:
    passing = ProductGateReport()
    failing = ProductGateReport(
        missing_files=["docs/missing.md"],
        stubbed_critical_tools=["approve_phase"],
        plan_manifest_missing=True,
    )

    assert passing.ok is True
    assert passing.lines() == ["Product gate: PASS"]
    assert failing.ok is False
    lines = failing.lines()
    assert lines[0] == "Product gate: FAIL"
    assert "Missing required evidence files:" in lines
    assert "- docs/missing.md" in lines
    assert "Critical MCP tools still stubbed:" in lines
    assert "- approve_phase" in lines
    assert any("Product-completion plan manifest missing" in line for line in lines)


def test_main_returns_zero_for_passing_report(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = ProductGateManifest(
        allowed_stub_tools=frozenset(),
        critical_mcp_tools=(),
        required_docs=(),
        required_e2e_tests=(),
        required_behavior_tests=(),
    )

    monkeypatch.setattr("film_pipeline.cli.product_gate.load_manifest", lambda: manifest)
    monkeypatch.setattr("film_pipeline.cli.product_gate.load_plan_manifest", lambda: manifest)
    monkeypatch.setattr(
        "film_pipeline.cli.product_gate.evaluate_product_gate",
        lambda _manifest, _plan_manifest: ProductGateReport(),
    )

    assert main() == 0


def test_main_returns_one_for_failing_report(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = ProductGateManifest(
        allowed_stub_tools=frozenset(),
        critical_mcp_tools=(),
        required_docs=(),
        required_e2e_tests=(),
        required_behavior_tests=(),
    )

    monkeypatch.setattr("film_pipeline.cli.product_gate.load_manifest", lambda: manifest)
    monkeypatch.setattr("film_pipeline.cli.product_gate.load_plan_manifest", lambda: None)
    monkeypatch.setattr(
        "film_pipeline.cli.product_gate.evaluate_product_gate",
        lambda _manifest, _plan_manifest: ProductGateReport(plan_manifest_missing=True),
    )

    assert main() == 1
