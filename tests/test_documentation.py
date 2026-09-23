"""Keep the compact documentation navigable and its examples executable."""

import asyncio
import json
import re
from pathlib import Path

from winproladder_mcp.ir import Ladder
from winproladder_mcp.layout import safe_ladder
from winproladder_mcp.server import build_server

ROOT = Path(__file__).resolve().parents[1]
DOCS = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md")), ROOT / "examples/README.md"]


def test_documentation_local_links_exist():
    for document in DOCS:
        text = document.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            path = document.parent / target.split("#", 1)[0]
            assert path.is_file(), f"{document.name}: broken link {target}"


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
