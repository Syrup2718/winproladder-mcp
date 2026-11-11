"""Enforce stable high-level dependency direction without rewriting legacy codecs."""

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "winproladder_mcp"
BASELINE = ROOT / "tests" / "fixtures" / "import-boundaries.json"

# These modules form the transport, orchestration, and application-facing layers.
# Lower-level domain/codec modules may not import them.
UPPER_LAYERS = {
    "server",
    "setup",
    "service",
    "capabilities",
    "design",
    "manual_reference",
    "control",
    "sequence",
    "system",
}


def import_graph(source: Path = SOURCE) -> dict[str, set[str]]:
    paths = {path.stem: path for path in source.glob("*.py")}
    graph = {name: set() for name in paths}
    for name, path in paths.items():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.level != 1:
                continue
            candidates = (
                [node.module.split(".", 1)[0]]
                if node.module
                else [alias.name.split(".", 1)[0] for alias in node.names]
            )
            graph[name].update(candidate for candidate in candidates if candidate in paths)
    return graph


def upward_imports(graph: dict[str, set[str]]) -> set[str]:
    return {
        f"{source}->{target}"
        for source, targets in graph.items()
        if source not in UPPER_LAYERS
        for target in targets
        if target in UPPER_LAYERS
    }


def cycles(graph: dict[str, set[str]]) -> list[set[str]]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indexes: dict[str, int] = {}
    low_links: dict[str, int] = {}
    result: list[set[str]] = []

    def visit(module: str) -> None:
        nonlocal index
        indexes[module] = low_links[module] = index
        index += 1
        stack.append(module)
        on_stack.add(module)
        for dependency in graph[module]:
            if dependency not in indexes:
                visit(dependency)
                low_links[module] = min(low_links[module], low_links[dependency])
            elif dependency in on_stack:
                low_links[module] = min(low_links[module], indexes[dependency])
        if low_links[module] != indexes[module]:
            return
        component: set[str] = set()
        while True:
            dependency = stack.pop()
            on_stack.remove(dependency)
            component.add(dependency)
            if dependency == module:
                break
        if len(component) > 1:
            result.append(component)

    for module in sorted(graph):
        if module not in indexes:
            visit(module)
    return result


def test_lower_layers_do_not_import_application_or_transport_layers():
    violations = upward_imports(import_graph())
    assert not violations, "Forbidden upward imports: " + ", ".join(sorted(violations))


def test_boundary_helper_detects_a_deliberate_reverse_import():
    graph = import_graph()
    graph["logic"].add("service")
    assert "logic->service" in upward_imports(graph)


def test_legacy_cycles_are_a_ceiling_not_a_required_shape():
    graph = import_graph()
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    allowed_cycles = [set(group) for group in baseline["legacy_cycles"]]
    unexpected_cycles = [
        sorted(group) for group in cycles(graph) if not any(group <= old for old in allowed_cycles)
    ]
    assert not unexpected_cycles, f"New import cycles: {unexpected_cycles}"

    allowed_edges = set(baseline["legacy_internal_edges"])
    actual_legacy_edges = {
        f"{source}->{target}"
        for old in allowed_cycles
        for source in old
        for target in graph[source]
        if target in old
    }
    added_edges = actual_legacy_edges - allowed_edges
    assert not added_edges, "New edges inside legacy cycles: " + ", ".join(sorted(added_edges))
