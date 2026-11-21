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


def batch4_spec() -> CommonFunSpec:
    """Fourteen sample-backed conversion, memory and supervisory forms."""

    return CommonFunSpec.model_validate(
        {
            "requirement": "Fourth batch of sample-backed common FUN forms",
            "functions": [
                {
                    "type": "encode_bits",
                    "source": "R1800",
                    "source_index": 2,
                    "count": 8,
                    "destination": "R1810",
                    "high_priority": "TRUE",
                },
                {
                    "type": "to_seven_segment",
                    "source": "R1820",
                    "count": 2,
                    "destination": "R1830",
                },
                {"type": "ascii_literal", "text": "BATCH114", "destination": "R1840"},
                {
                    "type": "ascii_to_hex",
                    "source": "R1850",
                    "count": 4,
                    "destination": "R1860",
                },
                {
                    "type": "hex_to_ascii",
                    "source": "R1870",
                    "count": 4,
                    "destination": "R1880",
                },
                {
                    "type": "bit_shift",
                    "destination": "R1890",
                    "input_bit": "TRUE",
                    "left": "TRUE",
                },
                {"type": "system_status", "group": 0, "destination": "R1900"},
                {
                    "type": "file_register",
                    "source": "R1910",
                    "file_base": "F200",
                    "pointer": "D1900",
                    "length": 4,
                    "increment": "TRUE",
                },
                {
                    "type": "memory_pack_write",
                    "bank": 1,
                    "offset": 0,
                    "source": "R1920",
                    "pointer": "D1910",
                    "length": 4,
                    "work": "R1930",
                    "pulse": True,
                    "increment": "TRUE",
                },
                {
                    "type": "memory_pack_read",
                    "bank": 1,
                    "offset": 0,
                    "destination": "R1950",
                    "pointer": "D1920",
                    "length": 4,
                    "increment": "TRUE",
                },
                {"type": "wdt", "setting": 80},
                {"type": "rswdt"},
                {"type": "hsctr", "counter": "HSC0"},
                {"type": "hsctw", "counter": "HSC0", "source": 0, "target": "PV"},
            ],
        }
    )


def test_batch4_forms_are_parameterized_and_round_trip_individually():
    spec = batch4_spec()
    ladder, design = common_fun_ladder(spec)
    assert len(ladder.networks) == len(spec.functions) == 14
    assert len(COMMON_FUN_EVIDENCE) == 131
    assert len({compile_network(network) for network in ladder.networks}) == 14
    for requested, network, evidence in zip(
        spec.functions, ladder.networks, design["evidence"], strict=True
    ):
        payload = compile_network(network)
        decoded = decode_network(payload)
        assert decoded is not None
        assert compile_network(decoded) == payload
        assert decoded.action.model_dump() == requested.model_dump()
        assert evidence["evidence_level"] == "sample-backed"


def test_batch4_suite_generates_complete_crc_valid_ldr(tmp_path):
    ladder, design = common_fun_ladder(batch4_spec())
    result = Service(tmp_path).generate_design(
        "common-fun-batch4.ldr",
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
        function.model_dump() for function in batch4_spec().functions
    ]
    assert result["artifact_validation"]["decoded_networks"] == 14
