import asyncio
import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

from winproladder_mcp.setup import check, client_config, prepare


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


def test_prepare_creates_portable_configs_and_preserves_policy(tmp_path: Path) -> None:
    root = tmp_path / "梯形圖 work"
    configs = tmp_path / "client snippets"
    prepare(root, configs)
    policy = root / ".winproladder-policy.json"
    assert json.loads(policy.read_text()) == {"forbid_m_to_m": True, "allow_function_m_to_m": True}
    settings = json.loads((configs / "mcp-config.json").read_text(encoding="utf-8"))["mcpServers"][
        "winproladder"
    ]
    toml = tomllib.loads((configs / "mcp-config.toml").read_text(encoding="utf-8"))
    assert toml["mcp_servers"]["winproladder"]["args"] == settings["args"]
    assert settings["command"] == sys.executable
    assert settings["args"][-1] == str(root.resolve())
    original = '{"forbid_m_to_m": true, "allow_function_m_to_m": false}\n'
    policy.write_text(original)
    prepare(root, configs)
    assert policy.read_text() == original
    # The generated absolute executable works even from an unrelated current directory.
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def connect() -> None:
        params = StdioServerParameters(**settings, cwd=str(tmp_path))
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            assert "generate_ldr" in {tool.name for tool in (await session.list_tools()).tools}

    asyncio.run(connect())


def test_prepare_rejects_invalid_existing_policy(tmp_path: Path) -> None:
    policy = tmp_path / ".winproladder-policy.json"
    policy.write_text('{"forbid_m_to_m": "invalid"}')
    with pytest.raises(ValueError):
        prepare(tmp_path, tmp_path / "config")
    assert not (tmp_path / "config/mcp-config.json").exists()
    assert policy.read_text() == '{"forbid_m_to_m": "invalid"}'
