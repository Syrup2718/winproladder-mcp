"""End-to-end example and negative acceptance matrix over actual MCP stdio."""

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from winproladder_mcp.ldr import parse


def test_every_design_example_over_stdio(tmp_path):
    async def run():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "winproladder_mcp.server", "--root", str(tmp_path)],
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()

            async def call(name, arguments):
                result = await session.call_tool(name, arguments)
                assert not result.isError, result.content
                return json.loads(result.content[0].text)

            guide = await call("get_design_guide", {})
            for name, ladder in guide["examples"].items():
                arguments = {"output_name": f"{name}.ldr", "ladder": ladder}
                if name == "self_hold_stop_active_high":
                    arguments["acceptance"] = guide["acceptance_example"]
                elif name == "on_delay_3_seconds_while_x0":
                    arguments["acceptance"] = guide["timed_acceptance"][name]
                generated = await call("generate_ldr", arguments)
                raw = (tmp_path / "artifacts" / f"{name}.ldr").read_bytes()
                assert parse(raw).encode() == raw
                assert generated["validation"]["valid"]
                decoded = await call("read_ldr", {"path": f"artifacts/{name}.ldr"})
                assert decoded["ladder"] is not None
                rebuilt = await call(
                    "generate_ldr",
                    {"output_name": f"rebuilt_{name}.ldr", "ladder": decoded["ladder"]},
                )
                assert rebuilt["sha256"] == generated["sha256"]
                if "acceptance" in arguments:
                    assert generated["acceptance"]["passed"]

            bad_cases = guide["timed_acceptance"]["on_delay_3_seconds_while_x0"]
            bad_cases[0]["scans"][0]["expected"]["Y0"] = True
            failed = await session.call_tool(
                "generate_ldr",
                {
                    "output_name": "must-not-exist.ldr",
                    "ladder": guide["examples"]["on_delay_3_seconds_while_x0"],
                    "acceptance": bad_cases,
                },
            )
            assert failed.isError
            assert not (tmp_path / "artifacts/must-not-exist.ldr").exists()

    asyncio.run(asyncio.wait_for(run(), timeout=60))
