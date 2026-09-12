"""Generate every high-level recipe via MCP; keep a JSON design report beside each LDR."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--prefix", default="v04")
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "winproladder_mcp.server", "--root", str(root)]
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        guide_result = await session.call_tool("get_design_guide", {})
        if guide_result.isError:
            raise RuntimeError(str(guide_result.content))
        guide = json.loads(guide_result.content[0].text)
        requests = [
            (kind, "generate_control_ldr", {"requirement": f"Example: {kind}", "kind": kind})
            for kind in guide["control_recipes"]["kinds"]
        ]
        requests.append(
            (
                "fill_mix_drain",
                "generate_sequence_ldr",
                guide["sequence_generation"]["example_spec"],
            )
        )
        requests.append(
            ("two_motors", "generate_system_ldr", guide["system_generation"]["example_spec"])
        )
        for name, tool, spec in requests:
            filename = f"{args.prefix}_{name}.ldr"
            report_path = root / "artifacts" / f"{filename}.design.json"
            if report_path.exists():
                raise FileExistsError(report_path)
            result = await session.call_tool(tool, {"output_name": filename, "spec": spec})
            if result.isError:
                raise RuntimeError(str(result.content))
            data = json.loads(result.content[0].text)
            if "design_report" not in data:
                raise RuntimeError(data.get("design_report_warning", "Missing design report"))
            print(
                json.dumps(
                    {
                        "path": data["path"],
                        "design_report": str(report_path),
                        "sha256": data["sha256"],
                    }
                )
            )


if __name__ == "__main__":
    asyncio.run(asyncio.wait_for(main(), timeout=120))
