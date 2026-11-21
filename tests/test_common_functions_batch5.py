import asyncio
from pathlib import Path

from winproladder_mcp.common_functions import (
    COMMON_FUN_EVIDENCE,
    CommonComparisonContact,
    CommonFunSpec,
    common_fun_ladder,
    common_fun_physical_types,
)
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import compile_network, decode_network
from winproladder_mcp.ldr import parse
from winproladder_mcp.server import build_server
from winproladder_mcp.service import Service

PROFILE = "FBs-40MA-test12"
IO = IOContract(
    inputs=[
        *(f"X{i}" for i in range(18)),
        *(f"X{i}" for i in range(24, 32)),
        "X34",
        "X35",
    ],
    outputs=[
        "Y0",
        "Y1",
        "Y2",
        "Y4",
        "Y5",
        "Y6",
        *(f"Y{i}" for i in range(20, 28)),
        *(f"Y{i}" for i in range(32, 44)),
    ],
)


def batch5_spec() -> CommonFunSpec:
    """Seventeen existing Production forms newly exposed through Common."""

    return CommonFunSpec.model_validate(
        {
            "requirement": "Fifth batch of safe Production-backed Common adapters",
            "functions": [
                {
                    "type": "udctr",
                    "cv": "R2100",
                    "preset": 1234,
                    "pulse": "M700",
                    "up": "M701",
                    "clear": "M702",
                },
                {"type": "imdio", "start": "X34", "count": 2},
                {"type": "tkey", "input": "X0", "destination": "R2101", "key_start": "M100"},
                {
                    "type": "hkey",
                    "input": "X10",
                    "output": "Y20",
                    "destination": "R2110",
                    "key_start": "M200",
                    "work": "R2120",
                },
                {
                    "type": "dsw",
                    "input": "X14",
                    "output": "Y24",
                    "destination": "R2130",
                    "work": "R2140",
                },
                {
                    "type": "7sgdl",
                    "source": "R2150",
                    "output": "Y32",
                    "mode": 1,
                    "work": "R2160",
                },
                {
                    "type": "muxi",
                    "input": "X24",
                    "output": "Y40",
                    "rows": 4,
                    "destination": "R2170",
                    "work": "R2180",
                },
                {
                    "type": "pulse_output",
                    "mode": 0,
                    "frequency": "R2200",
                    "pulse_count": "R2201",
                    "forward_output": "Y0",
                    "reverse_output": "Y1",
                    "destination": "R2202",
                    "up": "TRUE",
                },
                {"type": "pwm", "on_ms": 40, "period_ms": 100, "physical_output": "Y2"},
                {
                    "type": "speed_detect",
                    "physical_input": "X6",
                    "sample_ms": 500,
                    "destination": "R2210",
                },
                {
                    "type": "tpctl",
                    "output": "Y4",
                    "start": 0,
                    "zones": 3,
                    "setpoint": "R2230",
                    "offset": "R2240",
                    "proportional": "R2250",
                    "integral": "R2260",
                    "derivative": "R2270",
                    "destination": "R2280",
                    "work": "R2290",
                },
                *[
                    {
                        "type": "comparison_contact",
                        "operation": operation,
                        "sa": f"R{2300 + 2 * index}",
                        "sb": f"R{2301 + 2 * index}",
                        "result": [{"device": "M", "address": 500 + index}],
                    }
                    for index, operation in enumerate(("eq", "gt", "lt", "ne", "ge", "le"))
                ],
            ],
        }
    )


def test_batch5_forms_are_parameterized_and_round_trip_individually():
    spec = batch5_spec()
    ladder, design = common_fun_ladder(spec, profile=PROFILE)
    assert len(ladder.networks) == len(spec.functions) == 17
    assert len(COMMON_FUN_EVIDENCE) == 131
    assert common_fun_physical_types(spec) == [
        "7sgdl",
        "dsw",
        "hkey",
        "imdio",
        "muxi",
        "pulse_output",
        "pwm",
        "speed_detect",
        "tkey",
        "tpctl",
    ]
    for requested, network, evidence in zip(
        spec.functions, ladder.networks, design["evidence"], strict=True
    ):
        payload = compile_network(network)
        decoded = decode_network(payload)
        assert decoded is not None
        assert compile_network(decoded) == payload
        if isinstance(requested, CommonComparisonContact):
            assert decoded.comparison_chain == [requested.contact()]
            assert decoded.coils == requested.result
            expected = "sample-backed" if requested.operation in {"eq", "ne"} else "inferred"
            assert evidence["evidence_level"] == expected
        else:
            assert decoded.action.model_dump() == requested.model_dump()
            assert evidence["evidence_level"] == "sample-backed"


def test_batch5_suite_generates_complete_crc_valid_ldr(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(
        '{"forbid_m_to_m":true,"allow_function_m_to_m":true}'
    )
    ladder, design = common_fun_ladder(batch5_spec(), profile=PROFILE)
    result = Service(tmp_path).generate_design(
        "common-fun-batch5.ldr",
        ladder,
        design,
        io_contract=IO,
        strict_writers=True,
    )
    document = parse(Path(result["path"]).read_bytes())
    decoded = [decode_network(record.payload) for record in reversed(document.records)]
    assert all(record.crc_valid for record in document.records)
    assert all(network is not None for network in decoded)
    assert all(
        compile_network(network) == record.payload
        for network, record in zip(decoded, reversed(document.records), strict=True)
    )
    assert result["artifact_validation"]["decoded_networks"] == 17
    assert result["architecture"]["valid"]


def test_physical_common_requires_explicit_profile_at_mcp_boundary(tmp_path):
    async def run():
        server = build_server(tmp_path)
        arguments = {
            "output_name": "physical.ldr",
            "spec": {
                "requirement": "Explicit physical IO",
                "functions": [{"type": "imdio", "start": "X0", "count": 1}],
            },
            "io_contract": {"inputs": ["X0"], "outputs": []},
        }
        denied = await server.call_tool("generate_common_fun_ldr", arguments)
        assert denied.isError and "target_profile" in str(denied)
        arguments["target_profile"] = "FBs-44MN-test13"
        allowed = await server.call_tool("generate_common_fun_ldr", arguments)
        assert not allowed.isError

    asyncio.run(run())
