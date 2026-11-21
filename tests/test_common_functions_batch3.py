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


def batch3_spec() -> CommonFunSpec:
    """Eighteen packing, shift and time-conversion forms without physical I/O."""

    return CommonFunSpec.model_validate(
        {
            "requirement": "Third batch of sample-backed common FUN forms",
            "functions": [
                {
                    "type": "bit_move",
                    "source": "R800",
                    "destination": "R801",
                    "source_index": 5,
                    "destination_index": 9,
                },
                {
                    "type": "nibble_move",
                    "source": "R802",
                    "destination": "R803",
                    "source_index": 1,
                    "destination_index": 2,
                },
                {
                    "type": "byte_move",
                    "source": "R804",
                    "destination": "R805",
                    "source_index": 0,
                    "destination_index": 1,
                },
                {"type": "word_exchange", "source": "R806", "destination": "R807"},
                {"type": "byte_swap", "destination": "R808"},
                {
                    "type": "nibble_unite",
                    "source": "R810",
                    "destination": "R820",
                    "count": 3,
                },
                {
                    "type": "nibble_distribute",
                    "source": "R821",
                    "destination": "R830",
                    "count": 3,
                },
                {
                    "type": "byte_unite",
                    "source": "R850",
                    "destination": "R1150",
                    "length_register": "R840",
                },
                {
                    "type": "byte_distribute",
                    "source": "R1300",
                    "destination": "R1450",
                    "length_register": "R1290",
                },
                {"type": "shift_left", "destination": "R1710", "count": 3, "input_bit": "TRUE"},
                {
                    "type": "shift_right",
                    "destination": "R1711",
                    "length_register": "R1712",
                    "input_bit": "TRUE",
                },
                {
                    "type": "rotate_left",
                    "destination": "R1713",
                    "length_register": "R1714",
                },
                {"type": "rotate_right", "destination": "R1715", "count": 4},
                {"type": "binary_to_gray", "source": "R1720", "destination": "R1721"},
                {"type": "gray_to_binary", "source": "R1722", "destination": "R1723"},
                {
                    "type": "decode_bits",
                    "source": "R1730",
                    "destination": "R1740",
                    "source_index": 4,
                    "bit_length": 4,
                },
                {"type": "hms_to_seconds", "source": "R1750", "destination": "R1760"},
                {"type": "seconds_to_hms", "source": "R1770", "destination": "R1780"},
            ],
        }
    )


def test_batch3_forms_are_parameterized_and_round_trip_individually():
    spec = batch3_spec()
    ladder, design = common_fun_ladder(spec)
    assert len(ladder.networks) == len(spec.functions) == 18
    assert len(COMMON_FUN_EVIDENCE) == 131
    assert len({compile_network(network) for network in ladder.networks}) == 18
    for requested, network, evidence in zip(
        spec.functions, ladder.networks, design["evidence"], strict=True
    ):
        payload = compile_network(network)
        decoded = decode_network(payload)
        assert decoded is not None
        assert compile_network(decoded) == payload
        assert decoded.action.model_dump() == requested.model_dump()
        assert evidence["evidence_level"] == "sample-backed"


def test_batch3_suite_generates_complete_crc_valid_ldr(tmp_path):
    ladder, design = common_fun_ladder(batch3_spec())
    result = Service(tmp_path).generate_design(
        "common-fun-batch3.ldr",
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
        function.model_dump() for function in batch3_spec().functions
    ]
    assert result["artifact_validation"]["decoded_networks"] == 18
