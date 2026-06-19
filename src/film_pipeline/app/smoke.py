"""Product smoke tests — validates every subsystem is operational.

Run with: `python -m film_pipeline.app.smoke`
"""

from __future__ import annotations


def check_graph_compiles() -> tuple[bool, str]:
    """Verify the LangGraph graph compiles."""
    try:
        from film_pipeline.graph.graph import build_graph

        build_graph()
        return True, "Graph compiles successfully"
    except Exception as e:
        return False, str(e)


def check_agent_registry() -> tuple[bool, str]:
    """Verify 19 MVP agents are registered."""
    try:
        from film_pipeline.agents.mvp import MVP_AGENTS

        count = len(MVP_AGENTS)
        if count != 19:
            return False, f"Expected 19 agents, got {count}"
        return True, f"{count} agents registered"
    except Exception as e:
        return False, str(e)


def check_validator_registry() -> tuple[bool, str]:
    """Verify 15 MVP validators are registered."""
    try:
        from film_pipeline.validation.validators import MVP_VALIDATORS

        count = len(MVP_VALIDATORS)
        if count != 15:
            return False, f"Expected 15 validators, got {count}"
        return True, f"{count} validators registered"
    except Exception as e:
        return False, str(e)


def check_kb_manifest() -> tuple[bool, str]:
    """Verify KB manifest loads with 12 items."""
    try:
        from pathlib import Path

        from film_pipeline.kb.manifest import KBManifest

        path = Path("film-knowledge-base/index/kb-manifest.yaml")
        if not path.exists():
            return False, f"Manifest not found at {path}"
        manifest = KBManifest.from_yaml(path)
        if len(manifest) != 12:
            return False, f"Expected 12 KB items, got {len(manifest)}"
        return True, f"{len(manifest)} KB items loaded"
    except Exception as e:
        return False, str(e)


def check_config_loads() -> tuple[bool, str]:
    """Verify base.studio profile loads."""
    try:
        from film_pipeline.config.loader import ProfileLoader

        loader = ProfileLoader()
        loader.load("base.studio")
        return True, "base.studio profile loaded"
    except Exception as e:
        return False, str(e)


ALL_CHECKS = [
    ("graph_compiles", check_graph_compiles),
    ("agent_registry", check_agent_registry),
    ("validator_registry", check_validator_registry),
    ("kb_manifest", check_kb_manifest),
    ("config_loads", check_config_loads),
]


def run_smoke_checks() -> list[tuple[str, bool, str]]:
    """Run all smoke checks. Returns list of (name, passed, detail)."""
    results: list[tuple[str, bool, str]] = []
    for name, fn in ALL_CHECKS:
        try:
            ok, detail = fn()
            results.append((name, ok, detail))
        except Exception as e:
            results.append((name, False, str(e)))
    return results


if __name__ == "__main__":
    results = run_smoke_checks()
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\nSmoke checks: {passed}/{total} passed\n")
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}: {detail}")
    if passed == total:
        print("\nAll smoke checks passed.")
    else:
        print(f"\n{total - passed} check(s) failed.")
