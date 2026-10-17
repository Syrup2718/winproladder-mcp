import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import ResourceLink


def test_compact_stdio_preserves_evidence_and_binary(tmp_path):
    async def run():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "winproladder_mcp.server", "--compact-responses", "--root", str(tmp_path)],
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            for tool in ("get_capabilities", "get_design_guide"):
                brief = await session.call_tool(tool, {})
                full = await session.call_tool(tool, {"detail": True})
                assert not brief.isError and not full.isError
                assert len(brief.model_dump_json()) < len(full.model_dump_json()) / 2
                assert (
                    brief.structuredContent["architecture_policy"]
                    == full.structuredContent["architecture_policy"]
                )
            result = await session.call_tool(
                "generate_control_ldr",
                {
                    "output_name": "compact.ldr",
                    "spec": {
                        "kind": "start_stop",
                        "requirement": "start stop",
                        "signal": "X0",
                        "stop": "X1",
                        "output": 0,
                    },
                    "io_contract": {"inputs": ["X0", "X1"], "outputs": ["Y0"]},
                    "acceptance": [
                        {
                            "name": "start",
                            "scans": [{"inputs": {"X0": True}, "expected": {"Y0": True}}],
                        }
                    ],
                },
            )
            assert not result.isError
            brief = result.structuredContent
            full = json.loads((tmp_path / "artifacts/compact.ldr.design.json").read_text())
            for key in (
                "validation",
                "acceptance",
                "compiled_acceptance",
                "io_contract",
                "architecture",
                "artifact_validation",
                "timer_settings",
                "sha256",
            ):
                assert brief[key] == full[key]
            assert "design" not in brief and "network_notes" not in brief
            if full["design"].get("assumptions"):
                assert brief["design_assumptions"] == full["design"]["assumptions"]
            assert any(isinstance(c, ResourceLink) for c in result.content)
            download = await session.call_tool("get_ldr_artifact", {"output_name": "compact.ldr"})
            assert not download.isError
            assert download.structuredContent["sha256"] == brief["sha256"]

    asyncio.run(run())
