"""Re-measure every count cited in docs/modularity-improvements/.

Run from the repository root:

    uv run python docs/modularity-improvements/measure.py

Stdlib AST analysis over ``src/film_pipeline`` plus one import of the MCP
registry (for the tool-contract counts). Prints the numbers; asserts nothing.
A count in these documents that disagrees with this script's output is stale.
"""

from __future__ import annotations

import ast
import collections
import re
import sys
from pathlib import Path

ROOT = Path("src/film_pipeline")
PKG = "film_pipeline"


def module_name(path: Path) -> str:
    parts = list(path.relative_to(ROOT.parent).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


MODULES: dict[str, Path] = {
    module_name(f): f for f in ROOT.rglob("*.py") if "__pycache__" not in f.parts
}


def _is_type_checking(node: ast.AST) -> bool:
    return isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test)


def _resolve_from(mod: str, path: Path, node: ast.ImportFrom) -> str | None:
    if not node.level:
        return node.module
    base = mod.split(".")
    if path.name != "__init__.py":
        base = base[:-1]
    if node.level > 1:
        base = base[: len(base) - (node.level - 1)]
    return ".".join(base + ([node.module] if node.module else []))


def _nearest_module(name: str) -> str | None:
    while name not in MODULES and "." in name:
        name = name.rsplit(".", 1)[0]
    return name if name in MODULES else None


def _parents(mod: str) -> list[str]:
    parts = mod.split(".")
    return [".".join(parts[:i]) for i in range(2, len(parts)) if ".".join(parts[:i]) in MODULES]


Edge = tuple[str, str, int]  # (source module, target module, line)


def collect_imports() -> tuple[dict[str, set[str]], list[Edge]]:
    """Return (eager module graph, function-level internal imports)."""
    eager: dict[str, set[str]] = collections.defaultdict(set)
    lazy: list[Edge] = []
    for mod, path in MODULES.items():
        eager[mod].update(_parents(mod))

        def visit(node: ast.AST, in_function: bool, mod: str = mod, path: Path = path) -> None:
            for child in ast.iter_child_nodes(node):
                if _is_type_checking(child):
                    continue
                targets: list[str] = []
                if isinstance(child, ast.ImportFrom):
                    base = _resolve_from(mod, path, child)
                    if base and base.startswith(PKG):
                        targets = [f"{base}.{a.name}" for a in child.names]
                elif isinstance(child, ast.Import):
                    targets = [a.name for a in child.names if a.name.startswith(PKG)]
                for raw in targets:
                    target = _nearest_module(raw)
                    if target is None:
                        continue
                    if in_function:
                        lazy.append((mod, target, child.lineno))
                    else:
                        eager[mod].add(target)
                        eager[mod].update(_parents(target))
                nested = in_function or isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef)
                visit(child, nested)

        visit(ast.parse(path.read_text()), False)
    return eager, lazy


def reaches(graph: dict[str, set[str]], start: str, goal: str) -> bool:
    seen, stack = {start}, [start]
    while stack:
        node = stack.pop()
        if node == goal:
            return True
        for nxt in graph[node] - seen:
            seen.add(nxt)
            stack.append(nxt)
    return False


def sccs(graph: dict[str, set[str]]) -> list[list[str]]:
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    out: list[list[str]] = []
    counter = [0]
    sys.setrecursionlimit(10_000)

    def strong(v: str) -> None:
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in graph[v]:
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(sorted(comp))

    for v in list(MODULES):
        if v not in index:
            strong(v)
    return out


def package_of(mod: str) -> str:
    return mod.split(".")[1] if mod.count(".") else mod


def grep_count(pattern: str, under: Path = ROOT) -> int:
    rx = re.compile(pattern, re.MULTILINE)
    return sum(len(rx.findall(f.read_text())) for f in under.rglob("*.py"))


def main() -> None:
    eager, lazy = collect_imports()

    print("== Package graph (runtime imports, distinct packages)")
    pkg_edges: collections.Counter[tuple[str, str]] = collections.Counter()
    for src, targets in eager.items():
        for dst in targets:
            a, b = package_of(src), package_of(dst)
            if a != b and a != PKG and b != PKG:
                pkg_edges[(a, b)] += 1
    with_lazy = set(pkg_edges)
    for s, t, _ in lazy:
        a, b = package_of(s), package_of(t)
        if a != b and a != PKG and b != PKG:
            with_lazy.add((a, b))
    fan_out = collections.Counter(a for a, _ in pkg_edges)
    fan_in = collections.Counter(b for _, b in pkg_edges)
    fan_out_all = collections.Counter(a for a, _ in with_lazy)
    for p in sorted(set(fan_out) | set(fan_in), key=lambda p: -fan_out_all[p]):
        print(f"  {p:14} out={fan_out[p]:2} out_incl_lazy={fan_out_all[p]:2} in={fan_in[p]:2}")

    print("\n== Function-level (lazy) internal imports")
    required = [(s, t, n) for s, t, n in lazy if reaches(eager, t, s)]
    hoistable = len(lazy) - len(required)
    print(f"  total={len(lazy)} cycle-required={len(required)} hoistable={hoistable}")
    by_pkg = collections.Counter(package_of(s) for s, t, n in lazy if (s, t, n) not in required)
    print("  hoistable by package:", dict(by_pkg.most_common()))
    for s, t, n in required:
        print(f"  required: {s}:{n} -> {t}")

    print("\n== Module-level cycles (eager + lazy, child->parent edges excluded)")
    full: dict[str, set[str]] = collections.defaultdict(set)
    for m, targets in eager.items():
        full[m] = {t for t in targets if not m.startswith(t + ".")}
    for s, t, _ in lazy:
        full[s].add(t)
    for comp in sccs(full):
        print("  ", comp)

    print("\n== Runtime access from MCP handlers")
    mcp = ROOT / "mcp"
    print("  get_runtime() calls in mcp:", grep_count(r"get_runtime\(\)", mcp))
    print("  `rt: Any` parameters in mcp:", grep_count(r"\brt: Any\b", mcp))
    print("  args.get( in mcp:", grep_count(r"args\.get\(", mcp))

    print("\n== MCP tool contract")
    from film_pipeline.mcp.contract import make_registry

    catalog = make_registry().catalog()
    print("  tools:", len(catalog))
    print("  with input_schema:", sum(1 for t in catalog if t["input_schema"]))
    print("  with output_schema:", sum(1 for t in catalog if t["output_schema"]))
    generic = sum(1 for t in catalog if t["description"] == f"MCP tool: {t['name']}")
    print("  with generic 'MCP tool: <name>' description:", generic)
    tools_init = (ROOT / "mcp/tools/__init__.py").read_text()
    lazy_map = set(re.findall(r'^\s+"(\w+)": "film_pipeline', tools_init, re.M))
    print("  _TOOL_MODULES entries:", len(lazy_map))
    stub = (ROOT / "mcp/tools/__init__.pyi").read_text()
    stub_names = set(re.findall(r"\bas (\w+)\b", stub))
    print(
        "  registered tools missing from the .pyi stub:",
        sorted({t["name"] for t in catalog} - stub_names),
    )
    print(
        "  names in _TOOL_MODULES but not registered:",
        sorted(lazy_map - {t["name"] for t in catalog}),
    )

    print("\n== Operations layer consumers (outside operations/)")
    ops_models = [
        "DashboardSummary",
        "ReviewWorkspace",
        "ValidationWorkspace",
        "GenerationWorkspace",
        "AuditEvent",
        "ProjectListItem",
        "MutationResult",
    ]
    for name in ops_models:
        users = [
            f
            for f in ROOT.rglob("*.py")
            if "operations" not in f.parts and re.search(rf"\b{name}\b", f.read_text())
        ]
        print(f"  {name}: {len(users)} src modules")

    print("\n== Duplicated literals")
    print(
        "  Gemini API base URL / models endpoints:",
        grep_count(r'"https://generativelanguage\.googleapis\.com/v1beta/models"'),
    )
    print("  OpenRouter API base URL:", grep_count(r'"https://openrouter\.ai/api/v1"'))
    # Counts the literal, whatever the constant is called: the original pattern
    # matched only the private spelling, so renaming the survivor to the public
    # ORCH_NS reported 0 definitions instead of 1.
    print("  _orchestrator namespace literal:", grep_count(r'= "_orchestrator"'))


if __name__ == "__main__":
    main()
