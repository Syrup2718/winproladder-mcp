"""Constant-Sb comparison contacts and their bounded offline model."""

from pathlib import Path

import pytest

from winproladder_mcp.acceptance import AcceptanceCase
from winproladder_mcp.common_functions import CommonFunSpec, common_fun_ladder
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import (
    Coil,
    ComparisonContact,
    Ladder,
    Network,
    compile_network,
    decode_network,
)
from winproladder_mcp.service import Service
from winproladder_mcp.validation_evidence import collect_instruction_evidence


def direct_constant_chain() -> Ladder:
    return Ladder(
        networks=[
            Network(
                comparison_chain=[
                    ComparisonContact(operation="gt", sa="R100", sb=0),
                    ComparisonContact(operation="lt", sa="R100", sb=100),
                    ComparisonContact(operation="eq", sa="D1", sb=1),
                ],
                coils=[Coil(address=0)],
            )
        ]
    )


def acceptance_case(name: str, r100: int, d1: int, expected: bool) -> AcceptanceCase:
    return AcceptanceCase.model_validate(
        {
            "name": name,
            "initial": {"R100": r100, "D1": d1},
            "scans": [{"inputs": {}, "expected": {"Y0": expected}}],
        }
    )


CASES = [
    acceptance_case("zero excluded", 0, 1, False),
    acceptance_case("one included", 1, 1, True),
    acceptance_case("middle included", 50, 1, True),
    acceptance_case("ninety-nine included", 99, 1, True),
    acceptance_case("one hundred excluded", 100, 1, False),
    acceptance_case("negative excluded", -1, 1, False),
    acceptance_case("D1 zero excluded", 50, 0, False),
    acceptance_case("D1 two excluded", 50, 2, False),
]


def test_constant_chain_has_direct_fun171_fun172_fun170_bytes_and_round_trips():
    network = direct_constant_chain().networks[0]
    payload = compile_network(network)
    assert payload.hex() == ("f67f00160ac80000f67f00230ac80064f67f002140020001c100")
    assert decode_network(payload) == network
    evidence = collect_instruction_evidence(0, network, payload)
    assert evidence == [
        {
            "network_index": 0,
            "instruction": "comparison_chain",
            "status": "inferred_variant",
            "source": "sampled FUN175 F6 marker + inferred opcode family",
            "gui_import_verified": True,
            "gui_display_verified": True,
            "gui_save_reopen_verified": False,
            "plc_verified": False,
        }
    ]


def test_constant_chain_generates_crc_valid_ldr_and_passes_acceptance(tmp_path: Path):
    (tmp_path / ".winproladder-policy.json").write_text(
        '{"forbid_m_to_m":true,"allow_function_m_to_m":true}'
    )
    result = Service(tmp_path).generate(
        "direct-comparison.ldr",
        direct_constant_chain(),
        CASES,
        io_contract=IOContract(inputs=[], outputs=["Y0"]),
        require_acceptance=True,
        strict_writers=True,
    )
    assert result["artifact_validation"] == {
        "crc_valid": True,
        "decoded_networks": 1,
        "scope": "Exact emitted LDR bytes; offline model, not GUI or PLC validation",
    }
    assert result["acceptance"]["passed"]
    decoded = Service(tmp_path).read("artifacts/direct-comparison.ldr")["ladder"]
    assert Ladder.model_validate(decoded) == direct_constant_chain()


@pytest.mark.parametrize("operation", ["eq", "gt", "lt", "ne", "ge", "le"])
@pytest.mark.parametrize("position", ["first", "series"])
@pytest.mark.parametrize("value", [0, 1, 100, 32767])
def test_all_constant_relations_positions_and_values_round_trip(operation, position, value):
    contacts = [ComparisonContact(operation=operation, sa="R10", sb=value)]
    if position == "series":
        contacts.insert(0, ComparisonContact(operation="eq", sa="R0", sb="R1"))
    network = Network(comparison_chain=contacts, coils=[Coil(address=0)])
    assert decode_network(compile_network(network)) == network


@pytest.mark.parametrize("value", [-1, 32768, True])
def test_comparison_constant_bounds_remain_rejected(value):
    with pytest.raises(ValueError):
        ComparisonContact(operation="gt", sa="R0", sb=value)


def test_common_builder_marks_new_constant_form_inferred():
    spec = CommonFunSpec.model_validate(
        {
            "requirement": "R100 greater than zero",
            "functions": [
                {
                    "type": "comparison_contact",
                    "operation": "gt",
                    "sa": "R100",
                    "sb": 0,
                    "result": [{"device": "Y", "address": 0}],
                }
            ],
        }
    )
    ladder, design = common_fun_ladder(spec)
    decoded = decode_network(compile_network(ladder.networks[0]))
    assert decoded is not None
    assert decoded.comparison_chain == ladder.networks[0].comparison_chain
    assert decoded.coils == ladder.networks[0].coils
    assert design["evidence"][0]["evidence_level"] == "inferred"
