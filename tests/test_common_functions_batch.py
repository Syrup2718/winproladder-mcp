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


def batch_spec() -> CommonFunSpec:
    """Twenty-five new Common forms with parameters distinct from native samples."""

    return CommonFunSpec.model_validate(
        {
            "requirement": "Batch sample-backed common FUN integration",
            "functions": [
                {
                    "type": "adcnv",
                    "selector": "FALSE",
                    "source": "D0",
                    "count": 3,
                    "destination": "D100",
                    "polarity": 0,
                },
                {
                    "type": "mlc",
                    "selector": "TRUE",
                    "source": "D200",
                    "count": 2,
                    "destination": "D300",
                    "x_table": "D500",
                    "y_table": "D800",
                    "table_length": "D1100",
                },
                {
                    "type": "bitrd",
                    "word": "D1200",
                    "bit": 7,
                    "output": [{"device": "M", "address": 100}],
                },
                {
                    "type": "bitwr",
                    "word": "D1201",
                    "bit": 5,
                    "input_bit": "TRUE",
                },
                {
                    "type": "float_operation",
                    "operation": "i_to_f",
                    "sa": "R0",
                    "destination": "R1000",
                },
                {
                    "type": "float_operation",
                    "operation": "f_to_i",
                    "sa": "R2",
                    "destination": "R1002",
                },
                {
                    "type": "float_operation",
                    "operation": "add",
                    "sa": "R4",
                    "sb": "R6",
                    "destination": "R1004",
                },
                {
                    "type": "float_operation",
                    "operation": "sub",
                    "sa": "R8",
                    "sb": "R10",
                    "destination": "R1006",
                },
                {
                    "type": "float_operation",
                    "operation": "mul",
                    "sa": "R12",
                    "sb": "R14",
                    "destination": "R1008",
                },
                {
                    "type": "float_operation",
                    "operation": "div",
                    "sa": 6.5,
                    "sb": "R16",
                    "destination": "R1010",
                },
                {
                    "type": "float_operation",
                    "operation": "sqrt",
                    "sa": "R18",
                    "destination": "R1012",
                },
                {
                    "type": "float_operation",
                    "operation": "sin",
                    "sa": "R20",
                    "destination": "R1014",
                },
                {
                    "type": "float_operation",
                    "operation": "cos",
                    "sa": "R21",
                    "destination": "R1016",
                },
                {
                    "type": "float_operation",
                    "operation": "tan",
                    "sa": 321.0,
                    "destination": "R1018",
                },
                {
                    "type": "float_operation",
                    "operation": "neg",
                    "destination": "R1020",
                },
                {
                    "type": "float_operation",
                    "operation": "abs",
                    "destination": "R1022",
                },
                {
                    "type": "float_operation",
                    "operation": "ln",
                    "sa": "R22",
                    "destination": "R1024",
                },
                {
                    "type": "float_operation",
                    "operation": "exp",
                    "sa": "R24",
                    "destination": "R1026",
                },
                {
                    "type": "float_operation",
                    "operation": "log",
                    "sa": "R26",
                    "destination": "R1028",
                },
                {
                    "type": "float_operation",
                    "operation": "pow",
                    "sa": "R28",
                    "sb": 3.0,
                    "destination": "R1030",
                },
                {
                    "type": "float_operation",
                    "operation": "asin",
                    "sa": "R30",
                    "destination": "R1032",
                },
                {
                    "type": "float_operation",
                    "operation": "acos",
                    "sa": "R32",
                    "destination": "R1034",
                },
                {
                    "type": "float_operation",
                    "operation": "atan",
                    "sa": "R34",
                    "destination": "R1036",
                },
                {
                    "type": "float_compare",
                    "sa": 3.25,
                    "sb": "R36",
                    "equal": [{"device": "M", "address": 110}],
                    "greater": [{"device": "M", "address": 111}],
                    "less": [{"device": "M", "address": 112}],
                },
                {
                    "type": "float_zone_compare",
                    "source": "R38",
                    "upper": 2.5,
                    "lower": "R40",
                    "within": [{"device": "M", "address": 113}],
                    "above": [{"device": "M", "address": 114}],
                    "below": [{"device": "M", "address": 115}],
                },
            ],
        }
    )


def test_batch_forms_are_parameterized_and_round_trip_individually():
    spec = batch_spec()
    ladder, design = common_fun_ladder(spec)
    assert len(ladder.networks) == len(spec.functions) == 25
    assert len(COMMON_FUN_EVIDENCE) == 131
    assert len({compile_network(network) for network in ladder.networks}) == 25
    for requested, network, evidence in zip(
        spec.functions, ladder.networks, design["evidence"], strict=True
    ):
        decoded = decode_network(compile_network(network))
        assert decoded is not None
        assert compile_network(decoded) == compile_network(network)
        assert decoded.action.model_dump() == requested.model_dump()
        assert evidence["evidence_level"] == "sample-backed"
        assert evidence["gui_verification"] == "not verified for generated artifact"


def test_batch_suite_generates_complete_crc_valid_ldr(tmp_path):
    service = Service(tmp_path)
    ladder, design = common_fun_ladder(batch_spec())
    result = service.generate_design(
        "common-fun-batch.ldr",
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
        function.model_dump() for function in batch_spec().functions
    ]
    assert result["artifact_validation"]["decoded_networks"] == 25
