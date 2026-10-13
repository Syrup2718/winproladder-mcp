"""Generate explicit demo I/O examples; report policy-rejected recipes without bypassing rules."""

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
            (
                kind,
                "generate_control_ldr",
                {
                    "requirement": f"Demo fixture: {kind}, X0 signal/X1 stop/X2 reset/X3 reverse, "
                    "outputs Y0..Y2 as required by the recipe",
                    "kind": kind,
                    "signal": "X0",
                    "stop": "X1",
                    "reset": "X2",
                    "reverse": "X3",
                    "output": 0,
                },
                {"inputs": ["X0", "X1", "X2", "X3"], "outputs": ["Y0", "Y1", "Y2"]},
            )
            for kind in guide["control_recipes"]["kinds"]
        ]
        requests.append(
            (
                "fill_mix_drain",
                "generate_sequence_ldr",
                guide["sequence_generation"]["example_spec"],
                {"inputs": ["X0", "X5", "X6"], "outputs": ["Y0", "Y1", "Y2"]},
            )
        )
        requests.append(
            (
                "two_motors",
                "generate_system_ldr",
                guide["system_generation"]["example_spec"],
                {"inputs": ["X0", "X1", "X2", "X3"], "outputs": ["Y0", "Y1"]},
            )
        )
        for name, tool, spec, contract in requests:
            filename = f"{args.prefix}_{name}.ldr"
            report_path = root / "artifacts" / f"{filename}.design.json"
            if report_path.exists():
                raise FileExistsError(report_path)
            result = await session.call_tool(
                tool, {"output_name": filename, "spec": spec, "io_contract": contract}
            )
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
