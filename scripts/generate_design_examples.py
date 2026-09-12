"""Generate all design-guide examples through a real MCP client."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prefix", default="v03")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    parameters = StdioServerParameters(
        command=sys.executable, args=["-m", "winproladder_mcp.server", "--root", str(root)]
    )
    async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("get_design_guide", {})
        if result.isError:
            raise RuntimeError(str(result.content))
        guide = json.loads(result.content[0].text)
        for name, ladder in guide["examples"].items():
            request = {"output_name": f"{args.prefix}_{name}.ldr", "ladder": ladder}
            if name == "self_hold_stop_active_high":
                request["acceptance"] = guide["acceptance_example"]
            elif name in guide.get("timed_acceptance", {}):
                request["acceptance"] = guide["timed_acceptance"][name]
            result = await session.call_tool("generate_ldr", request)
            if result.isError:
                raise RuntimeError(str(result.content))
            created = json.loads(result.content[0].text)
            print(
                json.dumps(
                    {
                        "path": created["path"],
                        "valid": created["validation"]["valid"],
                        "import_verified": created["validation"]["import_verified"],
                        "acceptance": created["acceptance"],
                    }
                )
            )


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=60))
