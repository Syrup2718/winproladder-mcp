from pathlib import Path

from winproladder_mcp.common_functions import (
    COMMON_FUN_EVIDENCE,
    CommonFunSpec,
    common_fun_ladder,
)
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import compile_network, decode_network
from winproladder_mcp.ldr import parse
from winproladder_mcp.service import Service


def batch2_spec() -> CommonFunSpec:
    """Thirty sample-backed register/table/matrix forms with independent parameters."""

    return CommonFunSpec.model_validate(
        {
            "requirement": "Second batch of sample-backed common FUN forms",
            "functions": [
                {
                    "type": "ramp",
                    "preset": "R100",
                    "timer": "T10",
                    "lower": "R101",
                    "upper": "R102",
                    "destination": "R103",
                    "up": "TRUE",
                },
                {
                    "type": "ramp2",
                    "maximum": "R110",
                    "rise_ms": "R111",
                    "fall_ms": "R112",
                    "target": "R113",
                    "destination": "R114",
                    "work": "R115",
                },
                {
                    "type": "reg_to_table",
                    "source": "R120",
                    "destination": "R130",
                    "pointer": "R140",
                    "length": 4,
                    "increment": "TRUE",
                },
                {
                    "type": "table_to_reg",
                    "source": "R150",
                    "pointer": "R160",
                    "destination": "R170",
                    "length": 4,
                    "increment": "TRUE",
                },
                {
                    "type": "table_to_table",
                    "source": "R180",
                    "destination": "R190",
                    "pointer": "R200",
                    "length": 4,
                    "increment": "TRUE",
                },
                {
                    "type": "block_table_move",
                    "source": "R210",
                    "destination": "R220",
                    "length": 4,
                },
                {
                    "type": "table_swap",
                    "source": "R230",
                    "destination": "R240",
                    "length": 4,
                },
                {
                    "type": "register_table_search",
                    "source": "R250",
                    "pointer": "R260",
                    "length": 4,
                    "value": 123,
                },
                {
                    "type": "table_compare",
                    "source": "R270",
                    "destination": "R280",
                    "pointer": "R290",
                    "length": 4,
                    "different": "TRUE",
                },
                {"type": "table_fill", "destination": "R300", "length": 4, "value": -12},
                {
                    "type": "table_shift",
                    "input_word": "R310",
                    "source": "R311",
                    "destination": "R320",
                    "output_word": "R330",
                    "length": 4,
                    "left": "TRUE",
                },
                {
                    "type": "table_rotate",
                    "source": "R340",
                    "destination": "R350",
                    "length": 4,
                },
                {
                    "type": "queue",
                    "input_word": "R360",
                    "destination": "R370",
                    "pointer": "R380",
                    "output_word": "R381",
                    "length": 4,
                    "push": "TRUE",
                },
                {
                    "type": "stack",
                    "input_word": "R390",
                    "destination": "R400",
                    "pointer": "R410",
                    "output_word": "R411",
                    "length": 4,
                    "push": "TRUE",
                },
                {
                    "type": "block_compare",
                    "input_word": "R420",
                    "source": "R430",
                    "bit_destination": "M200",
                    "length": 4,
                },
                {
                    "type": "matrix_and",
                    "source": "R450",
                    "source_b": "R460",
                    "destination": "R470",
                    "length": 4,
                },
                {
                    "type": "matrix_or",
                    "source": "R480",
                    "source_b": "R490",
                    "destination": "R500",
                    "length": 4,
                },
                {
                    "type": "matrix_xor",
                    "source": "R510",
                    "source_b": "R520",
                    "destination": "R530",
                    "length": 4,
                },
                {
                    "type": "matrix_xnr",
                    "source": "R540",
                    "source_b": "R550",
                    "destination": "R560",
                    "length": 4,
                },
                {
                    "type": "matrix_invert",
                    "source": "D0",
                    "destination": "D300",
                    "length_register": "R570",
                },
                {
                    "type": "matrix_compare",
                    "source": "R580",
                    "source_b": "R590",
                    "pointer": "R600",
                    "length": 4,
                    "different": "TRUE",
                },
                {
                    "type": "matrix_bit_read",
                    "source": "R610",
                    "pointer": "R620",
                    "length": 4,
                    "increment": "TRUE",
                },
                {
                    "type": "matrix_bit_write",
                    "destination": "R630",
                    "pointer": "R640",
                    "length": 4,
                    "input_bit": "TRUE",
                    "increment": "TRUE",
                },
                {
                    "type": "matrix_bit_shift",
                    "source": "R650",
                    "destination": "R660",
                    "length": 4,
                    "input_bit": "TRUE",
                    "left": "TRUE",
                },
                {
                    "type": "matrix_bit_rotate",
                    "source": "R670",
                    "destination": "R680",
                    "length": 4,
                    "left": "TRUE",
                },
                {
                    "type": "matrix_bit_count",
                    "source": "R690",
                    "destination": "R700",
                    "length": 4,
                    "ones": "TRUE",
                },
                {
                    "type": "table_sort",
                    "source": "R710",
                    "destination": "R720",
                    "length": 4,
                    "ascending": "TRUE",
                },
                {
                    "type": "zone_write",
                    "destination": "R730",
                    "length": 4,
                    "ones": "TRUE",
                },
                {"type": "move_inverse", "source": "R740", "destination": "R741"},
                {"type": "toggle_bit", "bit_destination": "M220", "trigger": "TRUE"},
            ],
        }
    )


def test_batch2_forms_are_parameterized_and_round_trip_individually():
    spec = batch2_spec()
    ladder, design = common_fun_ladder(spec)
    assert len(ladder.networks) == len(spec.functions) == 30
    assert len(COMMON_FUN_EVIDENCE) == 131
    assert len({compile_network(network) for network in ladder.networks}) == 30
    for requested, network, evidence in zip(
        spec.functions, ladder.networks, design["evidence"], strict=True
    ):
        payload = compile_network(network)
        decoded = decode_network(payload)
        assert decoded is not None
        assert compile_network(decoded) == payload
        assert decoded.action.model_dump() == requested.model_dump()
        assert evidence["evidence_level"] == "sample-backed"


def test_batch2_suite_generates_complete_crc_valid_ldr(tmp_path):
    ladder, design = common_fun_ladder(batch2_spec())
    result = Service(tmp_path).generate_design(
        "common-fun-batch2.ldr",
        ladder,
        design,
        io_contract=IOContract(inputs=[], outputs=[]),
        strict_writers=True,
    )
    document = parse(Path(result["path"]).read_bytes())
    decoded = [decode_network(record.payload) for record in reversed(document.records)]
    assert all(record.crc_valid for record in document.records)
    assert all(network is not None for network in decoded)
    assert [network.action.model_dump() for network in decoded] == [
        function.model_dump() for function in batch2_spec().functions
    ]
    assert result["artifact_validation"]["decoded_networks"] == 30
