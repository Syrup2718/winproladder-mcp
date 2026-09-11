"""Exercise the actual project MCP configuration and create a verified-template file."""

import asyncio
import json
import tomllib
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main() -> None:
    config = tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
    server = config["mcp_servers"]["winproladder"]
    parameters = StdioServerParameters(
        command=server["command"], args=server["args"], cwd=server["cwd"]
    )
    async with (
        stdio_client(parameters) as (read, write),
        ClientSession(read, write) as session,
    ):
        await session.initialize()
        names = [t.name for t in (await session.list_tools()).tools]
        print(json.dumps({"tools": names}))
        result = await session.call_tool("create_start_stop", {"output_name": "start_stop_mcp.ldr"})
        if result.isError:
            raise RuntimeError(str(result.content))
        print(result.content[0].text)
        candidate = ROOT / "artifacts/start_stop_candidate.ldr"
        if candidate.exists():
            assert (ROOT / "artifacts/start_stop_mcp.ldr").read_bytes() == candidate.read_bytes()
            print("MCP-generated file is byte-identical to the user-import-verified candidate.")


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=60))
