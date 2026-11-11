"""Keep the compact documentation navigable and its examples executable."""

import asyncio
import json
import re
from pathlib import Path
from urllib.parse import unquote

from winproladder_mcp.ir import Ladder
from winproladder_mcp.layout import safe_ladder
from winproladder_mcp.ldr import parse as parse_ldr
from winproladder_mcp.server import build_server

ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    *ROOT.glob("*.md"),
    *sorted((ROOT / "docs").rglob("*.md")),
    *(ROOT / name / "README.md" for name in ["examples", "samples", "scripts", "tests"]),
]


def test_documentation_local_links_exist():
    for document in DOCS:
        text = document.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            path = document.parent / unquote(target.split("#", 1)[0])
            resolved = path.resolve()
            assert resolved.is_relative_to(ROOT), (
                f"{document.name}: link leaves repository: {target}"
            )
            relative = resolved.relative_to(ROOT)
            assert not relative.parts or relative.parts[0] not in {
                "artifacts",
                "dist",
                "tmp",
                ".venv",
                ".codex",
            }, f"{document.name}: published link depends on local files: {target}"
            assert path.exists(), f"{document.name}: broken link {target}"


def test_documentation_index_covers_every_topic():
    index = (ROOT / "docs/README.md").read_text(encoding="utf-8")
    for document in (ROOT / "docs").glob("*.md"):
        if document.name != "README.md":
            assert f"({document.name})" in index, f"Unindexed document: {document.name}"


def test_agent_guide_is_a_compact_map_to_sources_of_truth():
    guide = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert len(guide.splitlines()) <= 60
    for target in [
        "ARCHITECTURE.md",
        "docs/agent-guide.md",
        "docs/development.md",
        ".winproladder-policy.json",
    ]:
        assert target in guide


def test_architecture_documents_the_artifact_validation_layers():
    architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
    for term in [
        "Source validation",
        "Lowered validation",
        "Emitted-byte validation",
        "MCP simulation",
        "GUI verification",
        "PLC verification",
        "test_import_boundaries.py",
    ]:
        assert term in architecture


def test_agent_tool_table_matches_server(tmp_path):
    text = (ROOT / "docs/agent-guide.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^\| `([a-z_]+)` \|", text, re.MULTILINE))
    actual = {tool.name for tool in asyncio.run(build_server(tmp_path).list_tools())}
    assert documented == actual


def test_current_tool_count_matches_feature_documents(tmp_path):
    count = len(asyncio.run(build_server(tmp_path).list_tools()))
    chinese = (ROOT / "docs/project/FEATURES.md").read_text(encoding="utf-8")
    english = (ROOT / "docs/project/FEATURES.en.md").read_text(encoding="utf-8")
    assert f"目前原始碼提供 {count} 個工具" in chinese
    assert f"The current source provides {count} tools" in english


def test_sample_and_network_counts_match_current_evidence_documents():
    samples = sorted((ROOT / "samples").glob("*.ldr"))
    sample_count = len(samples)
    network_count = sum(len(parse_ldr(path.read_bytes()).records) for path in samples)
    expected = {
        ROOT / "samples/README.md": f"**{sample_count} 份原始匯出、{network_count} 個網路記錄**",
        ROOT / "docs/verification.md": f"**{sample_count} 份匯出、{network_count} 個網路**",
        ROOT
        / "docs/verification.en.md": f"**{sample_count} exports and {network_count} networks**",
        ROOT / "docs/project/FEATURES.md": (
            f"目前保存 {sample_count} 份原始 WinProLadder 匯出、共 {network_count} 個網路"
        ),
        ROOT / "docs/project/FEATURES.en.md": (
            f"preserves {sample_count} original WinProLadder exports "
            f"containing {network_count} networks"
        ),
    }
    for document, claim in expected.items():
        assert claim in document.read_text(encoding="utf-8"), (
            f"{document.relative_to(ROOT)} does not contain the current claim: {claim}"
        )


def test_reference_json_examples_compile():
    text = (ROOT / "docs/reference.md").read_text(encoding="utf-8")
    examples = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
    assert examples
    for example in examples:
        safe_ladder(Ladder.model_validate(json.loads(example)))
