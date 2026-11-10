"""Real stdio client/server tests, not just Python function calls."""

import asyncio
import json
import re
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
            assert sum(len(tool.description or "") for tool in tools) < 12000
            for tool in tools:
                properties = tool.inputSchema.get("properties", {})
                assert all(schema.get("description") for schema in properties.values()), tool.name
                assert tool.outputSchema is not None, tool.name
            assert {tool.name for tool in tools} == {
                "get_capabilities",
                "get_instruction_capabilities",
                "get_manual_reference",
                "inspect_rtc_snapshot",
                "get_ldr_artifact",
                "get_pdw_artifact",
                "inspect_pdw",
                "generate_pdw",
                "generate_project_pdw",
                "generate_component_comments",
                "inspect_ldr",
                "read_ldr",
                "validate_ladder",
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
            generate = next(t for t in tools if t.name == "generate_ldr")
            assert "ladder" in generate.inputSchema["properties"]
            assert generate.annotations.destructiveHint is False
            assert "custom Ladder IR" in generate.description
            control = next(t for t in tools if t.name == "generate_control_ldr")
            assert "common control function" in control.description
            descriptions = {
                tool.name: re.sub(r"\s+", " ", tool.description or "") for tool in tools
            }
            expected_boundaries = {
                "get_capabilities": ("modify_network", "metadata only"),
                "generate_system_ldr": ("simulate_ladder", "does not execute"),
                "generate_control_ldr": ("generate_component_comments", "creates only"),
                "generate_sequence_ldr": ("validate_ladder", "cannot derive"),
                "generate_ldr": ("generate_component_comments", "cannot compile"),
                "generate_project_pdw": ("generate_component_comments", "cannot create"),
                "generate_pdw": ("generate_component_comments", "separate .txt"),
                "generate_component_comments": ("analyze_ldr", "does not inspect"),
                "compare_ldr": ("validate caller-supplied IR", "does not"),
                "validate_ladder": ("compare_ldr", "without reading or writing"),
                "simulate_ladder": ("compare_ldr", "neither generates"),
                "modify_network": ("get_capabilities", "changes program content"),
            }
            for tool_name, boundary_phrases in expected_boundaries.items():
                assert all(phrase in descriptions[tool_name] for phrase in boundary_phrases), (
                    tool_name
                )
            instruction_detail = next(t for t in tools if t.name == "get_instruction_capabilities")
            assert "family" not in instruction_detail.inputSchema.get("required", [])
            rtc = next(t for t in tools if t.name == "inspect_rtc_snapshot")
            rtc_schema = rtc.inputSchema["$defs"]["RTCSnapshot"]
            assert set(rtc_schema["required"]) == {
                "R4128",
                "R4129",
                "R4130",
                "R4131",
                "R4132",
                "R4133",
                "R4134",
            }
            assert rtc_schema["additionalProperties"] is False
            assert all(field["description"] for field in rtc_schema["properties"].values())
            assert "no PLC-access tool" in rtc.description
            assert "get_manual_reference" in rtc.description
            guide = next(t for t in tools if t.name == "get_design_guide")
            detail_schema = guide.inputSchema["properties"]["detail"]
            assert detail_schema["default"] is False
            assert "compact control recipes" in detail_schema["description"]
            assert "Ladder IR schema" in detail_schema["description"]
            for sibling in (
                "get_capabilities",
                "get_instruction_capabilities",
                "get_manual_reference",
            ):
                assert sibling in guide.description
            assert "does not validate IR or create a file" in re.sub(r"\s+", " ", guide.description)
            caps = await session.call_tool("get_capabilities", {})
            assert not caps.isError
            families = await session.call_tool("get_instruction_capabilities", {})
            assert not families.isError and families.structuredContent["count"] > 0
            family = families.structuredContent["families"][0]["family"]
            family_detail = await session.call_tool(
                "get_instruction_capabilities", {"family": family}
            )
            assert not family_detail.isError
            assert family_detail.structuredContent["family"] == family
            manual = await session.call_tool("get_manual_reference", {})
            assert not manual.isError and "R4135" in manual.content[0].text
            clock = await session.call_tool(
                "inspect_rtc_snapshot",
                {
                    "registers": {
                        "R4128": 0,
                        "R4129": 30,
                        "R4130": 8,
                        "R4131": 7,
                        "R4132": 10,
                        "R4133": 26,
                        "R4134": 3,
                        "R4135": 2078,
                    }
                },
            )
            assert not clock.isError and "2078" in clock.content[0].text
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
                    "generate_ldr",
                    {"output_name": "timer.ldr", "ladder": block_ladder},
                ),
                ("read_ldr", {"path": "artifacts/timer.ldr"}),
                (
                    "compare_ldr",
                    {"left_path": "samples/test3.ldr", "right_path": "samples/test3.ldr"},
                ),
                ("validate_ladder", {"ladder": start_stop().model_dump()}),
                (
                    "generate_ldr",
                    {"output_name": "motor.ldr", "ladder": start_stop().model_dump()},
                ),
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
                if name == "generate_ldr":
                    args["io_contract"] = {"inputs": ["X0", "X1"], "outputs": ["Y0"]}
                result = await session.call_tool(name, args)
                assert not result.isError, (name, result.content)
                assert result.structuredContent is not None
            for name, args in [
                ("simulate_ladder", {"ladder": block_ladder, "inputs": [{}]}),
                (
                    "generate_ldr",
                    {
                        "output_name": "motor.ldr",
                        "ladder": start_stop().model_dump(),
                        "io_contract": {"inputs": ["X0", "X1"], "outputs": ["Y0"]},
                    },
                ),
                (
                    "generate_ldr",
                    {
                        "output_name": "../escape.ldr",
                        "ladder": start_stop().model_dump(),
                        "io_contract": {"inputs": ["X0", "X1"], "outputs": ["Y0"]},
                    },
                ),
                (
                    "generate_ldr",
                    {
                        "output_name": "bad.ldr",
                        "ladder": {"networks": []},
                        "io_contract": {"inputs": [], "outputs": []},
                    },
                ),
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
