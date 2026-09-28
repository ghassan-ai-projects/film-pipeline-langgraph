"""A fresh runtime must be able to execute the graph without extra setup.

## The regression this pins

`orchestration.execution` cannot import `studio.graph_factory` — that closes a
package cycle, since `graph_factory` imports `orchestration` to wire the nodes — so
the composition root *injects* the builder:

    orchestration.execution.register_graph_builder(build_graph)

The first attempt called that from `studio/graph_factory.py` at module import. That
works whenever something has already imported `graph_factory`, which is what the
unit suite does. **The integration suite does not**: it drives `MCPServer` against a
runtime whose graph was never built, so `graph_factory` was never imported, nothing
was registered, and `ensure_graph` raised

    RuntimeError: No graph builder is registered.

`make ci-check` was green through that — the tests that exercise this path are
integration tests, and they were the ones that failed.

## What the guard checks

That the registration happens on a path a caller cannot avoid: importing
`film_pipeline.studio.runtime`, which every runtime construction goes through. The
test deliberately does **not** import `graph_factory` first — doing so would
re-register the builder and pass even if the runtime-side install were removed,
which is exactly how the original defect hid.
"""

from __future__ import annotations

import subprocess
import sys


def test_importing_the_runtime_registers_the_graph_builder() -> None:
    """`studio.runtime` alone must leave a usable graph builder installed."""
    probe = (
        "import film_pipeline.orchestration.execution as ex;"
        "assert ex._GRAPH_BUILDER is None, 'already registered at import time';"
        "import film_pipeline.studio.runtime;"
        "assert ex._GRAPH_BUILDER is not None, 'studio.runtime did not register it';"
        "print('registered')"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "importing film_pipeline.studio.runtime did not install a graph builder "
        f"without film_pipeline.studio.graph_factory being imported first:\n{result.stderr}"
    )
    assert "registered" in result.stdout


def test_ensure_graph_fails_loudly_without_a_builder() -> None:
    """The guard-the-guard: the error must name the missing call.

    If `ensure_graph` silently returned `None` instead of raising, the first test
    could pass while every graph run failed later with an obscure error.
    """
    probe = (
        "import film_pipeline.orchestration.execution as ex\n"
        "class Rt:\n"
        "    graph = None\n"
        "    runtime_root = None\n"
        "saved = ex._GRAPH_BUILDER\n"
        "ex._GRAPH_BUILDER = None\n"
        "try:\n"
        "    ex.ensure_graph(Rt())\n"
        "except RuntimeError as exc:\n"
        "    assert 'register_graph_builder' in str(exc), str(exc)\n"
        "    print('raised')\n"
        "finally:\n"
        "    ex._GRAPH_BUILDER = saved\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "raised" in result.stdout, result.stderr
