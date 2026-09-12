"""Real stdio client/server tests, not just Python function calls."""

import asyncio
import json
import shutil
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from winproladder_mcp.design import design_guide
from winproladder_mcp.ir import start_stop


def test_stdio_tool_workflow(tmp_path: Path) -> None:
    (tmp_path / "samples").mkdir()
    shutil.copyfile(Path(__file__).parents[1] / "samples/test3.ldr", tmp_path / "samples/test3.ldr")

    async def run() -> None:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "winproladder_mcp.server", "--root", str(tmp_path)],
        )
        async with (
            stdio_client(params) as (read, write),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            tools = (await session.list_tools()).tools
            assert {tool.name for tool in tools} == {
                "get_capabilities",
                "inspect_ldr",
                "read_ldr",
                "validate_ladder",
                "create_ldr",
                "create_start_stop",
                "export_ldr",
                "modify_network",
                "simulate_ladder",
                "get_design_guide",
                "generate_ldr",
                "generate_sequence_ldr",
                "generate_control_ldr",
                "generate_system_ldr",
                "analyze_ldr",
                "compare_ldr",
            }
            create = next(t for t in tools if t.name == "create_ldr")
            assert "ladder" in create.inputSchema["properties"]
            assert create.annotations.destructiveHint is False
            caps = await session.call_tool("get_capabilities", {})
            assert not caps.isError
            resource = await session.read_resource("winproladder://capabilities")
            assert "start_stop" in resource.contents[0].text
            block_ladder = {"networks": [{"block": {"type": "timer", "address": 1, "preset": 256}}]}
            for name, args in [
                (
                    "generate_ldr",
                    {
                        "output_name": "accepted.ldr",
                        "ladder": start_stop().model_dump(),
                        "acceptance": design_guide()["acceptance_example"],
                    },
                ),
                ("get_design_guide", {}),
                (
                    "generate_ldr",
                    {
                        "output_name": "generated.ldr",
                        "ladder": {
                            "networks": [
                                {"condition": "X0 AND (X1 OR Y0)", "coils": [{"address": 0}]}
                            ]
                        },
                    },
                ),
                (
                    "simulate_ladder",
                    {"ladder": start_stop().model_dump(), "inputs": [{"X0": True}]},
                ),
                ("inspect_ldr", {"path": "samples/test3.ldr"}),
                ("read_ldr", {"path": "samples/test3.ldr"}),
                ("analyze_ldr", {"path": "samples/test3.ldr"}),
                (
                    "create_ldr",
                    {"output_name": "timer.ldr", "ladder": block_ladder, "allow_unverified": True},
                ),
                ("read_ldr", {"path": "artifacts/timer.ldr"}),
                (
                    "compare_ldr",
                    {"left_path": "samples/test3.ldr", "right_path": "samples/test3.ldr"},
                ),
                ("validate_ladder", {"ladder": start_stop().model_dump()}),
                (
                    "create_ldr",
                    {"output_name": "motor.ldr", "ladder": start_stop().model_dump()},
                ),
                ("create_start_stop", {"output_name": "motor-template.ldr"}),
                ("export_ldr", {"path": "samples/test3.ldr", "output_name": "copy.ldr"}),
                (
                    "modify_network",
                    {
                        "path": "samples/test3.ldr",
                        "output_name": "edit.ldr",
                        "operation": "replace",
                        "index": 0,
                        "network": start_stop().networks[0].model_dump(),
                        "allow_unverified": True,
                    },
                ),
            ]:
                result = await session.call_tool(name, args)
                assert not result.isError, (name, result.content)
                assert result.structuredContent is not None
            for name, args in [
                ("simulate_ladder", {"ladder": block_ladder, "inputs": [{}]}),
                ("create_ldr", {"output_name": "timer-denied.ldr", "ladder": block_ladder}),
                ("create_start_stop", {"output_name": "motor.ldr"}),
                ("create_start_stop", {"output_name": "../escape.ldr"}),
                ("create_ldr", {"output_name": "bad.ldr", "ladder": {"networks": []}}),
                ("inspect_ldr", {"path": "missing.ldr"}),
            ]:
                assert (await session.call_tool(name, args)).isError
            assert json.loads(caps.content[0].text)["transport"] == "stdio"
            analysis = await session.call_tool("analyze_ldr", {"path": "samples/test3.ldr"})
            assert json.loads(analysis.content[0].text)["decoded_count"] == 12

    asyncio.run(asyncio.wait_for(run(), timeout=60))
    assert (tmp_path / "artifacts/copy.ldr").read_bytes() == (
        tmp_path / "samples/test3.ldr"
    ).read_bytes()
    assert (tmp_path / "artifacts/motor.ldr").read_bytes() == (
        tmp_path / "artifacts/motor-template.ldr"
    ).read_bytes()
