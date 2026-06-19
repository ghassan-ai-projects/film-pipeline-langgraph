"""Product smoke tests — validates the studio is operational.

Run with: `python -m film_pipeline.app.smoke`
"""

from __future__ import annotations


def run_smoke_checks() -> list[tuple[str, bool, str]]:
    """Run all smoke checks. Returns list of (name, passed, detail)."""
    results: list[tuple[str, bool, str]] = []

    # 1. Graph compiles
    try:
        from film_pipeline.graph.graph import build_graph

        build_graph()
        results.append(("graph_compiles", True, "Graph compiles successfully"))
    except Exception as e:
        results.append(("graph_compiles", False, str(e)))

    # 2. Agent registry populated
    try:
        from film_pipeline.agents.mvp import MVP_AGENTS

        assert len(MVP_AGENTS) == 19
        results.append(("agent_registry", True, f"{len(MVP_AGENTS)} agents registered"))
    except Exception as e:
        results.append(("agent_registry", False, str(e)))

    # 3. Validator registry populated
    try:
        from film_pipeline.validation.validators import MVP_VALIDATORS

        assert len(MVP_VALIDATORS) == 15
        results.append(("validator_registry", True, f"{len(MVP_VALIDATORS)} validators"))
    except Exception as e:
        results.append(("validator_registry", False, str(e)))

    # 4. KB manifest loads
    try:
        from pathlib import Path

        from film_pipeline.kb.manifest import KBManifest

        manifest = KBManifest.from_yaml(Path("film-knowledge-base/index/kb-manifest.yaml"))
        assert len(manifest) == 12
        results.append(("kb_manifest", True, f"{len(manifest)} KB items"))
    except Exception as e:
        results.append(("kb_manifest", False, str(e)))

    # 5. Config loads
    try:
        from film_pipeline.config.loader import ProfileLoader

        loader = ProfileLoader()
        loader.load("base.studio")
        results.append(("config_loads", True, "base.studio profile loaded"))
    except Exception as e:
        results.append(("config_loads", False, str(e)))

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
