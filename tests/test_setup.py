import asyncio
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from winproladder_mcp.setup import check, client_config


def test_portable_config_with_spaces(tmp_path: Path) -> None:
    root = tmp_path / "folder with spaces"
    root.mkdir()
    for format_name in ["codex", "json"]:
        output = subprocess.check_output(
            [
                sys.executable,
                "-m",
                "winproladder_mcp.setup",
                "config",
                "--format",
                format_name,
                "--root",
                str(root),
            ],
            text=True,
        )
        if format_name == "codex":
            config = tomllib.loads(output)["mcp_servers"]["winproladder"]
        else:
            config = json.loads(output)["mcpServers"]["winproladder"]
        assert config["command"] == sys.executable
        assert config["args"][-1] == str(root.resolve())


def test_check_without_repository_assets(tmp_path: Path) -> None:
    asyncio.run(check(tmp_path))
    assert (tmp_path / "artifacts/self-check.ldr").stat().st_size == 281
    assert (tmp_path / "artifacts/requirement-check.ldr").is_file()


def test_config_custom_output_directory(tmp_path: Path) -> None:
    config = client_config(tmp_path, Path("VM exchange"))
    assert config["args"][-2:] == ["--output-dir", str(tmp_path / "VM exchange")]
    assert not (tmp_path / "VM exchange").exists()
    with pytest.raises(ValueError, match="subdirectory"):
        client_config(tmp_path, tmp_path.parent / "outside")
