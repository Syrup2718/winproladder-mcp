import asyncio
from pathlib import Path

import pytest
from pydantic import ValidationError

from winproladder_mcp.common_functions import (
    CommonFunSpec,
    common_fun_ladder,
    common_fun_physical_types,
)
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import Arithmetic, compile_network, decode_network
from winproladder_mcp.ldr import parse
from winproladder_mcp.server import build_server
from winproladder_mcp.service import Service

HSC_SELECTORS = {"HSC0": 0, "HSC1": 1, "HSC2": 2, "HSC3": 3, "HSTA": 4}


def direction_a_spec() -> CommonFunSpec:
    return CommonFunSpec.model_validate(
        {
            "requirement": "Direction A signed constants and selector variants",
            "functions": [
                {
                    "type": "arithmetic",
                    "operation": operation,
                    "sa": f"R{100 + index * 4}",
                    "sb": value,
                    "destination": f"R{200 + index * 4}",
                    "enable": "M0",
                }
                for index, (operation, value) in enumerate(
                    (("add", -1), ("sub", -123), ("mul", -7), ("div", -3))
                )
            ]
            + [
                {"type": "hsctr", "counter": counter}
                for counter in ("HSC1", "HSC2", "HSC3", "HSTA")
            ],
        }
    )


@pytest.mark.parametrize(
    ("operation", "value", "opcode"),
    [
        ("add", -1, "f662"),
        ("sub", -123, "f664"),
        ("mul", -7, "f666"),
        ("div", -3, "f668"),
    ],
)
def test_signed_arithmetic_constants_are_parameterized_and_round_trip(
    operation: str, value: int, opcode: str
):
    action = Arithmetic(
        operation=operation,
        sa="R100",
        sb=value,
        destination="R200",
        enable="X0 AND M0",
    )
    ladder, design = common_fun_ladder(
        CommonFunSpec(requirement="Signed constant", functions=[action])
    )
    payload = compile_network(ladder.networks[0])
    assert bytes.fromhex(opcode) in payload
    assert value.to_bytes(2, "big", signed=True) in payload
    decoded = decode_network(payload)
    assert decoded is not None
    decoded_data = decoded.action.model_dump()
    assert decoded_data | {"enable": action.enable} == action.model_dump()
    assert design["evidence"][0]["evidence_level"] == "inferred"
    assert design["evidence"][0]["gui_verification"].startswith("display verified 2026-11-23")


def test_signed_arithmetic_constant_limits_and_divide_zero_are_rejected():
    base = {"operation": "add", "sa": "R0", "destination": "R1"}
    for value in (-32769, 32768):
        with pytest.raises(ValidationError):
            Arithmetic(**base, sb=value)
    with pytest.raises(ValidationError, match="division by zero"):
        Arithmetic(operation="div", sa="R0", sb=0, destination="R2")


def test_adcnv_keeps_unipolar_anchor_and_rejects_failed_bipolar_probe():
    data = {
        "type": "adcnv",
        "source": "R310",
        "count": 5,
        "destination": "R420",
        "selector": "M20",
    }
    spec = CommonFunSpec.model_validate(
        {"requirement": "Sample-backed ADCNV polarity", "functions": [data | {"polarity": 0}]}
    )
    ladder, design = common_fun_ladder(spec)
    payload = compile_network(ladder.networks[0])
    assert bytes.fromhex("f55a") in payload
    decoded = decode_network(payload)
    assert decoded is not None
    assert decoded.action.model_dump() == spec.functions[0].model_dump()
    assert design["evidence"][0]["evidence_level"] == "sample-backed"
    with pytest.raises(ValidationError):
        CommonFunSpec.model_validate(
            {"requirement": "Reject failed Pl=1 probe", "functions": [data | {"polarity": 1}]}
        )


@pytest.mark.parametrize("counter", ["HSC0", "HSC1", "HSC2", "HSC3", "HSTA"])
def test_hsctr_selectors_round_trip(counter: str):
    data = {"type": "hsctr", "counter": counter}
    spec = CommonFunSpec.model_validate(
        {"requirement": "Parameterized HSC selector", "functions": [data]}
    )
    ladder, design = common_fun_ladder(spec)
    payload = compile_network(ladder.networks[0])
    selector = HSC_SELECTORS[counter].to_bytes(2, "big")
    assert bytes.fromhex("f4e5") + selector in payload
    decoded = decode_network(payload)
    assert decoded is not None
    assert decoded.action.model_dump() == spec.functions[0].model_dump()
    expected = "sample-backed" if counter == "HSC0" else "inferred"
    assert design["evidence"][0]["evidence_level"] == expected
    if counter != "HSC0":
        assert design["evidence"][0]["gui_verification"].startswith("display verified 2026-11-23")


def test_hsctw_rejects_nonzero_counter_selectors_after_failed_gui_probe():
    for counter in ("HSC1", "HSC2", "HSC3", "HSTA"):
        with pytest.raises(ValidationError, match="CN=HSC0"):
            CommonFunSpec.model_validate(
                {
                    "requirement": "Reject selector bytes that alter S",
                    "functions": [
                        {"type": "hsctw", "counter": counter, "source": 0, "target": "PV"}
                    ],
                }
            )


def test_nonzero_hsc_selectors_require_explicit_profile_at_mcp_boundary(tmp_path):
    spec = CommonFunSpec.model_validate(
        {
            "requirement": "Explicit CPU for inferred HSC selector",
            "functions": [{"type": "hsctr", "counter": "HSC2"}],
        }
    )
    assert common_fun_physical_types(spec) == ["hsctr"]
    assert (
        common_fun_physical_types(
            CommonFunSpec.model_validate(
                {"requirement": "Sampled HSC0", "functions": [{"type": "hsctr"}]}
            )
        )
        == []
    )

    async def run():
        server = build_server(tmp_path)
        arguments = {
            "output_name": "hsc2.ldr",
            "spec": spec.model_dump(),
            "io_contract": {"inputs": [], "outputs": []},
        }
        denied = await server.call_tool("generate_common_fun_ldr", arguments)
        assert denied.isError and "target_profile" in str(denied)
        arguments["target_profile"] = "FBs-20MC"
        allowed = await server.call_tool("generate_common_fun_ldr", arguments)
        assert not allowed.isError

    asyncio.run(run())


def test_direction_a_batch_generates_complete_crc_valid_ldr(tmp_path):
    (tmp_path / ".winproladder-policy.json").write_text(
        '{"forbid_m_to_m":true,"allow_function_m_to_m":true}'
    )
    spec = direction_a_spec()
    ladder, design = common_fun_ladder(spec, profile="FBs-20MC")
    result = Service(tmp_path).generate_design(
        "direction-a-gui-verified-8.ldr",
        ladder,
        design,
        io_contract=IOContract(inputs=["X0"], outputs=[]),
        strict_writers=True,
    )
    document = parse(Path(result["path"]).read_bytes())
    decoded = [decode_network(record.payload) for record in reversed(document.records)]
    assert len(spec.functions) == len(document.records) == 8
    assert all(record.crc_valid for record in document.records)
    assert all(network is not None for network in decoded)
    assert [network.action.model_dump() for network in decoded] == [
        function.model_dump() for function in spec.functions
    ]
    assert [item["evidence_level"] for item in design["evidence"]] == ["inferred"] * 8
    assert all(
        item["gui_verification"].startswith("display verified") for item in design["evidence"]
    )
    assert result["artifact_validation"]["decoded_networks"] == 8
    assert result["architecture"]["valid"]
