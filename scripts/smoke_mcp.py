"""Exercise the actual project MCP configuration and create a verified-template file."""

import argparse
import asyncio
import json
import sys
import tomllib
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-name", default="start_stop_mcp.ldr")
    args = parser.parse_args()
    config_path = ROOT / ".codex/config.toml"
    if config_path.exists():
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        server = config["mcp_servers"]["winproladder"]
    else:
        server = {
            "command": sys.executable,
            "args": ["-m", "winproladder_mcp.server", "--root", str(ROOT)],
            "cwd": str(ROOT),
        }
    parameters = StdioServerParameters(
        command=server["command"], args=server["args"], cwd=server.get("cwd")
    )
    async with (
        stdio_client(parameters) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        names = [t.name for t in (await session.list_tools()).tools]
        print(json.dumps({"tools": names}))
        result = await session.call_tool("create_start_stop", {"output_name": args.output_name})
        if result.isError:
            raise RuntimeError(str(result.content))
        print(result.content[0].text)
        candidate = ROOT / "artifacts/start_stop_candidate.ldr"
        if candidate.exists():
            assert (ROOT / "artifacts" / args.output_name).read_bytes() == candidate.read_bytes()
            print("MCP-generated file is byte-identical to the user-import-verified candidate.")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=60))
