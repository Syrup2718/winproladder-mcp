"""Run maintenance entry points with the same explicit-I/O requirements as MCP users."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from winproladder_mcp.ldr import parse

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("script", ["generate_design_examples.py", "generate_control_examples.py"])
@pytest.mark.parametrize("policy", [False, True])
def test_example_scripts_supply_io_and_respect_policy(tmp_path, script, policy):
    if policy:
        (tmp_path / ".winproladder-policy.json").write_text(
            '{"forbid_m_to_m":true,"allow_function_m_to_m":true}'
        )
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / script),
            "--root",
            str(tmp_path),
            "--prefix",
            "audit",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith("{")]
    assert rows
    paths = [Path(row["path"]) for row in rows if "path" in row]
    assert paths and all(parse(path.read_bytes()).editable for path in paths)
    assert not any(row.get("status") == "policy_rejected" for row in rows) or policy
    if policy:
        assert json.loads((tmp_path / ".winproladder-policy.json").read_text())["forbid_m_to_m"]
