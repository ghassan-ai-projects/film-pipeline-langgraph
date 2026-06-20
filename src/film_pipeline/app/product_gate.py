"""Working-product gate enforcement.

Loads both the product-completion standard manifest and the product-completion
plan manifest. Fails when the repository claims product readiness against
either manifest without the required implementation and test evidence.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from film_pipeline.mcp.contract import make_registry

MANIFEST_PATH = Path("docs/product-completion/acceptance-manifest.yaml")
PLAN_MANIFEST_PATH = Path("docs/product-completion-plan/acceptance-manifest.yaml")


@dataclass(frozen=True)
class ProductGateManifest:
    allowed_stub_tools: frozenset[str]
    critical_mcp_tools: tuple[str, ...]
    required_docs: tuple[str, ...]
    required_e2e_tests: tuple[str, ...]
    required_behavior_tests: tuple[str, ...]


@dataclass
class ProductGateReport:
    missing_files: list[str] = field(default_factory=list)
    stubbed_critical_tools: list[str] = field(default_factory=list)
    plan_manifest_missing: bool = False

    @property
    def ok(self) -> bool:
        return (
            not self.missing_files
            and not self.stubbed_critical_tools
            and not self.plan_manifest_missing
        )

    def lines(self) -> list[str]:
        lines = ["Product gate: PASS" if self.ok else "Product gate: FAIL"]
        if self.missing_files:
            lines.append("Missing required evidence files:")
            lines.extend(f"- {path}" for path in self.missing_files)
        if self.stubbed_critical_tools:
            lines.append("Critical MCP tools still stubbed:")
            lines.extend(f"- {tool}" for tool in self.stubbed_critical_tools)
        if self.plan_manifest_missing:
            lines.append(
                "Product-completion plan manifest missing — "
                "docs/product-completion-plan/acceptance-manifest.yaml"
            )
        return lines


def load_manifest(path: Path = MANIFEST_PATH) -> ProductGateManifest:
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise ValueError("Product gate manifest must be a mapping.")
    return ProductGateManifest(
        allowed_stub_tools=frozenset(_read_list(raw, "allowed_stub_tools")),
        critical_mcp_tools=tuple(_read_list(raw, "critical_mcp_tools")),
        required_docs=tuple(_read_list(raw, "required_docs")),
        required_e2e_tests=tuple(_read_list(raw, "required_e2e_tests")),
        required_behavior_tests=tuple(_read_list(raw, "required_behavior_tests")),
    )


def load_plan_manifest(path: Path = PLAN_MANIFEST_PATH) -> ProductGateManifest | None:
    if not path.exists():
        return None
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        return None
    return ProductGateManifest(
        allowed_stub_tools=frozenset(_read_list(raw, "allowed_stub_behaviors")),
        critical_mcp_tools=tuple(_read_list(raw, "critical_mcp_tools", [])),
        required_docs=tuple(_read_list(raw, "required_docs", [])),
        required_e2e_tests=tuple(_read_list(raw, "required_e2e_scenarios", [])),
        required_behavior_tests=tuple(_read_list(raw, "required_behavior_tests", [])),
    )


def evaluate_product_gate(
    manifest: ProductGateManifest,
    plan_manifest: ProductGateManifest | None = None,
) -> ProductGateReport:
    required_files = (
        *manifest.required_docs,
        *manifest.required_e2e_tests,
        *manifest.required_behavior_tests,
    )
    if plan_manifest:
        required_files = (
            *required_files,
            *plan_manifest.required_docs,
            *plan_manifest.required_e2e_tests,
            *plan_manifest.required_behavior_tests,
        )
    missing_files = [path for path in required_files if not Path(path).exists()]
    stubbed_tools = detect_stubbed_critical_tools(manifest)
    return ProductGateReport(
        missing_files=sorted(set(missing_files)),
        stubbed_critical_tools=sorted(stubbed_tools),
        plan_manifest_missing=plan_manifest is None,
    )


def detect_stubbed_critical_tools(manifest: ProductGateManifest) -> list[str]:
    registry = make_registry()
    stubbed: list[str] = []
    for tool_name in manifest.critical_mcp_tools:
        if tool_name in manifest.allowed_stub_tools:
            continue
        registration = registry.get(tool_name)
        try:
            source = inspect.getsource(registration.handler)
        except (OSError, TypeError):
            source = ""
        if "_stub(" in source:
            stubbed.append(tool_name)
    return stubbed


def main() -> int:
    manifest = load_manifest()
    plan_manifest = load_plan_manifest()
    report = evaluate_product_gate(manifest, plan_manifest)
    for line in report.lines():
        print(line)
    return 0 if report.ok else 1


def _read_list(raw: dict[str, Any], key: str, default: object = None) -> list[str]:
    value = raw.get(key, default or [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"Manifest key '{key}' must be a list of strings.")
    return list(value)


if __name__ == "__main__":
    raise SystemExit(main())
