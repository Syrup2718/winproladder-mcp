import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_high_level_tools_produce_files_and_disclose_defaults(tmp_path):
    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "winproladder_mcp.server", "--root", str(tmp_path)]
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            for tool, spec in [
                (
                    "generate_system_ldr",
                    {
                        "requirement": "two controls",
                        "controls": [
                            {"requirement": "first", "kind": "toggle"},
                            {"requirement": "second", "kind": "toggle", "signal": "X1"},
                        ],
                    },
                ),
                ("generate_control_ldr", {"requirement": "single button toggle", "kind": "toggle"}),
                (
                    "generate_sequence_ldr",
                    {
                        "requirement": "pause and resume",
                        "steps": [{"name": "mix", "ticks": 3, "outputs": [0]}],
                    },
                ),
            ]:
                result = await session.call_tool(tool, {"output_name": f"{tool}.ldr", "spec": spec})
                assert not result.isError, result.content
                data = json.loads(result.content[0].text)
                assert data["design"]["assumptions"]
                report = tmp_path / "artifacts" / f"{tool}.ldr.design.json"
                assert report.is_file()
                assert json.loads(report.read_text(encoding="utf-8"))["sha256"] == data["sha256"]
                assert not data["design"]["gui_import_verified"]
                assert (tmp_path / "artifacts" / f"{tool}.ldr").is_file()

    asyncio.run(asyncio.wait_for(run(), timeout=60))
