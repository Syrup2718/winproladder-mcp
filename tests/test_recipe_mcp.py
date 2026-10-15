import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_high_level_tools_produce_files_and_disclose_defaults(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(
        '{"forbid_m_to_m":true,"allow_function_m_to_m":true}'
    )
    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "winproladder_mcp.server", "--root", str(tmp_path)]
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            preview = await session.call_tool(
                "validate_ladder",
                {
                    "ladder": {
                        "networks": [{"condition": "X0 AND (X1 OR X2)", "coils": [{"address": 0}]}]
                    }
                },
            )
            assert not preview.isError, preview.content
            preview_data = json.loads(preview.content[0].text)
            assert preview_data["layout"]["helper_devices"] == []
            assert preview_data["layout"]["metrics"]["networks_after"] == 1
            assert preview_data["optimized_ladder"]["networks"][0]["condition"]
            assert not (tmp_path / "artifacts").exists()
            for tool, spec in [
                (
                    "generate_system_ldr",
                    {
                        "requirement": "two controls",
                        "controls": [
                            {"requirement": "first", "kind": "toggle", "signal": "X0", "output": 0},
                            {
                                "requirement": "second",
                                "kind": "toggle",
                                "signal": "X1",
                                "output": 1,
                            },
                        ],
                    },
                ),
                (
                    "generate_control_ldr",
                    {
                        "requirement": "single button toggle",
                        "kind": "toggle",
                        "signal": "X0",
                        "output": 0,
                    },
                ),
                (
                    "generate_sequence_ldr",
                    {
                        "requirement": "timed sequence",
                        "start": "X0",
                        "steps": [{"name": "mix", "ticks": 3, "outputs": [0]}],
                    },
                ),
            ]:
                result = await session.call_tool(
                    tool,
                    {
                        "output_name": f"{tool}.ldr",
                        "spec": spec,
                        "io_contract": {"inputs": ["X0", "X1"], "outputs": ["Y0", "Y1"]},
                    },
                )
                assert not result.isError, result.content
                data = json.loads(result.content[0].text)
                assert data["design"]["assumptions"]
                report = tmp_path / "artifacts" / f"{tool}.ldr.design.json"
                assert report.is_file()
                assert json.loads(report.read_text(encoding="utf-8"))["sha256"] == data["sha256"]
                assert not data["design"]["gui_import_verified"]
                assert (tmp_path / "artifacts" / f"{tool}.ldr").is_file()

    asyncio.run(asyncio.wait_for(run(), timeout=60))
