"""Exercise MCP handlers in-process so transport-boundary coverage cannot hide regressions."""

import asyncio
from typing import Any

from winproladder_mcp.server import build_server


def structured(result: Any) -> dict[str, Any]:
    if isinstance(result, tuple):
        return result[1]
    assert result.structuredContent is not None
    return result.structuredContent


def test_read_validation_and_artifact_handlers_in_process(tmp_path):
    async def run():
        server = build_server(tmp_path)
        full_server = build_server(tmp_path, compact_responses=False)

        compact = structured(await server.call_tool("get_capabilities", {}))
        complete = structured(await full_server.call_tool("get_capabilities", {}))
        assert compact["response_mode"] == "compact"
        assert complete["response_mode"] == "full"
        assert "more" in compact and "instruction_matrix" in complete

        families = structured(await server.call_tool("get_instruction_capabilities", {}))
        family = families["families"][0]["family"]
        assert (
            structured(await server.call_tool("get_instruction_capabilities", {"family": family}))[
                "family"
            ]
            == family
        )
        assert (
            structured(await server.call_tool("get_design_guide", {"detail": True}))[
                "response_mode"
            ]
            == "full"
        )

        ladder = {"networks": [{"condition": "X0", "coils": [{"address": 0}]}]}
        generated = await server.call_tool(
            "generate_ldr",
            {
                "output_name": "direct.ldr",
                "ladder": ladder,
                "io_contract": {"inputs": ["X0"], "outputs": ["Y0"]},
            },
        )
        assert not generated.isError
        generated_data = structured(generated)
        assert generated_data["artifact_validation"]["decoded_networks"] == 1

        for tool, arguments, expected in [
            ("inspect_ldr", {"path": "artifacts/direct.ldr"}, "records"),
            ("read_ldr", {"path": "artifacts/direct.ldr"}, "ladder"),
            ("analyze_ldr", {"path": "artifacts/direct.ldr"}, "references"),
            (
                "compare_ldr",
                {
                    "left_path": "artifacts/direct.ldr",
                    "right_path": "artifacts/direct.ldr",
                },
                "changes",
            ),
            ("validate_ladder", {"ladder": ladder}, "optimized_ladder"),
            (
                "simulate_ladder",
                {"ladder": ladder, "inputs": [{"X0": True}, {}]},
                "trace",
            ),
        ]:
            assert expected in structured(await server.call_tool(tool, arguments))

        exported = await server.call_tool(
            "export_ldr",
            {"path": "artifacts/direct.ldr", "output_name": "exported.ldr"},
        )
        assert not exported.isError
        assert structured(exported)["byte_identical"] is True
        modified = await server.call_tool(
            "modify_network",
            {
                "path": "artifacts/direct.ldr",
                "output_name": "modified.ldr",
                "operation": "replace",
                "index": 0,
                "network": {"condition": "NOT X0", "coils": [{"address": 0}]},
                "allow_unverified": True,
            },
        )
        assert not modified.isError
        downloaded = await server.call_tool("get_ldr_artifact", {"output_name": "modified.ldr"})
        assert not downloaded.isError
        assert structured(downloaded)["artifact"]["name"] == "modified.ldr"

    asyncio.run(run())


def test_high_level_generation_handlers_in_process(tmp_path):
    async def run():
        server = build_server(tmp_path)
        cases = [
            (
                "generate_control_ldr",
                {
                    "output_name": "control.ldr",
                    "spec": {
                        "kind": "start_stop",
                        "requirement": "X0 starts Y0 and X1 stops it",
                        "signal": "X0",
                        "stop": "X1",
                        "output": 0,
                    },
                    "io_contract": {"inputs": ["X0", "X1"], "outputs": ["Y0"]},
                    "target_profile": "FBs-20MC",
                },
            ),
            (
                "generate_system_ldr",
                {
                    "output_name": "system.ldr",
                    "spec": {
                        "requirement": "two independent outputs",
                        "controls": [
                            {
                                "kind": "rising_edge",
                                "requirement": "X0 pulses Y0",
                                "signal": "X0",
                                "output": 0,
                            },
                            {
                                "kind": "falling_edge",
                                "requirement": "X1 pulses Y1",
                                "signal": "X1",
                                "output": 1,
                            },
                        ],
                    },
                    "io_contract": {"inputs": ["X0", "X1"], "outputs": ["Y0", "Y1"]},
                },
            ),
            (
                "generate_sequence_ldr",
                {
                    "output_name": "sequence.ldr",
                    "spec": {
                        "requirement": "X0 starts one timed Y0 step",
                        "start": "X0",
                        "steps": [{"name": "run", "outputs": [0], "ticks": 1}],
                    },
                    "io_contract": {"inputs": ["X0"], "outputs": ["Y0"]},
                },
            ),
        ]
        for tool, arguments in cases:
            result = await server.call_tool(tool, arguments)
            assert not result.isError, (tool, result.content)
            data = structured(result)
            assert data["artifact_validation"]["crc_valid"] is True
            assert data["io_contract"]["extra"] == []

    asyncio.run(run())
