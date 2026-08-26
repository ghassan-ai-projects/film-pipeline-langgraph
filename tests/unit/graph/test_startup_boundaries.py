"""Boundary guards for the graph package [B-F4].

Locks in the repair that removed fixture data from the production default
startup path:

1. No module under ``graph/`` may import ``film_pipeline.testing`` (test
   fixtures) or ``film_pipeline.app`` (composition root) — in any import
   statement, module-level or function-body.
2. Constructing mock-mode services pulls in no ``film_pipeline.testing``
   modules; canned responses are injected from the composition root.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path
from typing import Any

_GRAPH_DIR = Path(__file__).resolve().parents[3] / "src" / "film_pipeline" / "graph"

_FORBIDDEN_ROOTS = ("film_pipeline.testing", "film_pipeline.app")


def test_graph_package_never_imports_testing_or_app() -> None:
    """AST sweep over every graph module, including lazy function-body imports."""
    offenders: list[str] = []
    for path in sorted(_GRAPH_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(_FORBIDDEN_ROOTS):
                        offenders.append(f"{path.name}:{node.lineno} import {alias.name}")
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith(_FORBIDDEN_ROOTS)
            ):
                offenders.append(f"{path.name}:{node.lineno} from {node.module} import ...")
    assert not offenders, "forbidden graph imports:\n" + "\n".join(offenders)


def test_mock_service_construction_imports_no_testing_modules() -> None:
    """Run in a fresh interpreter so unrelated tests cannot preload fixtures."""
    code = (
        "import sys\n"
        "import tempfile\n"
        "from pathlib import Path\n"
        "from film_pipeline.app.mock_responses import default_mock_responses\n"
        "from film_pipeline.graph.services import GraphServices\n"
        "root = Path(tempfile.mkdtemp())\n"
        "GraphServices.for_mock_runtime(\n"
        "    artifacts_root=str(root), mock_responses=default_mock_responses()\n"
        ")\n"
        "loaded = sorted(m for m in sys.modules if m.startswith('film_pipeline.testing'))\n"
        "assert not loaded, f'testing modules leaked into mock startup: {loaded}'\n"
        "print('CLEAN')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, result.stderr
    assert "CLEAN" in result.stdout


def test_default_runtime_mode_builds_services_from_composition_root(tmp_path: Any) -> None:
    """The production default wiring passes injected canned responses."""
    from film_pipeline.app.runtime import StudioRuntime

    rt = StudioRuntime(server_mode="mock", runtime_root=tmp_path / "runtime")
    assert rt.services is not None
    assert rt.services.prompt_runner.mock_responses, (
        "mock mode must receive injected canned responses"
    )
