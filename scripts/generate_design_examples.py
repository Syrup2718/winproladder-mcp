"""Generate all design-guide examples through a real MCP client."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from winproladder_mcp.analysis import device_references
from winproladder_mcp.ir import Ladder


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
            # These are explicit guide fixtures, not an inferred customer's I/O contract.
            program = Ladder.model_validate(ladder)
            devices = device_references(list(enumerate(program.networks)))["devices"]
            contract = {
                "inputs": sorted(d for d in devices if d.startswith("X")),
                "outputs": sorted(d for d in devices if d.startswith("Y")),
            }
            request = {
                "output_name": f"{args.prefix}_{name}.ldr",
                "ladder": ladder,
                "io_contract": contract,
            }
            if name == "self_hold_stop_active_high":
                request["acceptance"] = guide["acceptance_example"]
            elif name in guide.get("timed_acceptance", {}):
                request["acceptance"] = guide["timed_acceptance"][name]
            result = await session.call_tool("generate_ldr", request)
            if result.isError:
                if "M-to-M" in str(result.content):
                    print(
                        json.dumps(
                            {
                                "example": name,
                                "status": "policy_rejected",
                                "reason": str(result.content),
                            }
                        )
                    )
                    continue
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
