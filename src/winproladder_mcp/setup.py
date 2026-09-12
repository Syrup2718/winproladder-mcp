"""Portable client configuration and real MCP connection self-check."""

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def client_config(root: Path) -> dict[str, object]:
    return {
        "command": sys.executable,
        "args": ["-m", "winproladder_mcp.server", "--root", str(root.resolve(strict=True))],
    }


async def check(root: Path) -> None:
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "winproladder_mcp.server", "--root", str(root)]
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        required = {
            "generate_control_ldr",
            "generate_sequence_ldr",
            "generate_system_ldr",
            "generate_ldr",
            "get_design_guide",
            "get_capabilities",
            "create_start_stop",
            "read_ldr",
            "analyze_ldr",
            "compare_ldr",
        }
        if not required.issubset({tool.name for tool in tools}):
            raise RuntimeError("Missing required MCP tools")
        result = await session.call_tool("create_start_stop", {"output_name": "self-check.ldr"})
        if result.isError:
            raise RuntimeError(str(result.content))
        data = (root / "artifacts/self-check.ldr").read_bytes()
        import hashlib

        if (
            hashlib.sha256(data).hexdigest()
            != "b917c9e8d50f38f6d6b568637e3afd3f0ef6091ea49a8aaca6b1b4f73db025b9"
        ):
            raise RuntimeError("Start-stop output does not match verified file")
        for name, arguments in [
            ("analyze_ldr", {"path": "artifacts/self-check.ldr"}),
            (
                "compare_ldr",
                {"left_path": "artifacts/self-check.ldr", "right_path": "artifacts/self-check.ldr"},
            ),
        ]:
            if (await session.call_tool(name, arguments)).isError:
                raise RuntimeError(f"{name} self-check failed")
        print(
            f"PASS: MCP connection, {len(tools)} tools, start-stop generation and verified SHA-256"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    config = sub.add_parser("config", help="Print client config; never overwrite existing settings")
    config.add_argument("--format", choices=["codex", "json"], default="codex")
    config.add_argument("--root", type=Path, default=Path.cwd())
    sub.add_parser("check", help="Test real stdio MCP in a temporary workspace; repeatable")
    args = parser.parse_args()
    if args.command == "check":
        with tempfile.TemporaryDirectory(prefix="winproladder-check-") as directory:
            asyncio.run(asyncio.wait_for(check(Path(directory)), timeout=60))
    else:
        settings = client_config(args.root)
        if args.format == "json":
            print(json.dumps({"mcpServers": {"winproladder": settings}}, indent=2))
        else:
            print("[mcp_servers.winproladder]")
            print("command = " + json.dumps(settings["command"]))
            print("args = " + json.dumps(settings["args"]))
            print("startup_timeout_sec = 30\ntool_timeout_sec = 60")


if __name__ == "__main__":
    main()
