"""Keep the compact documentation navigable and its examples executable."""

import asyncio
import json
import re
from pathlib import Path
from urllib.parse import unquote

from winproladder_mcp.ir import Ladder
from winproladder_mcp.layout import safe_ladder
from winproladder_mcp.server import build_server

ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    *ROOT.glob("*.md"),
    *sorted((ROOT / "docs").glob("*.md")),
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


def test_agent_tool_table_matches_server(tmp_path):
    text = (ROOT / "docs/agent-guide.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^\| `([a-z_]+)` \|", text, re.MULTILINE))
    actual = {tool.name for tool in asyncio.run(build_server(tmp_path).list_tools())}
    assert documented == actual


def test_reference_json_examples_compile():
    text = (ROOT / "docs/reference.md").read_text(encoding="utf-8")
    examples = re.findall(r"```json\n(.*?)\n```", text, re.DOTALL)
    assert examples
    for example in examples:
        safe_ladder(Ladder.model_validate(json.loads(example)))
