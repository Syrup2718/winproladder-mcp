from pathlib import Path

from winproladder_mcp.common_functions import (
    COMMON_FUN_EVIDENCE,
    CommonFunSpec,
    common_fun_ladder,
)
from winproladder_mcp.io_contract import IOContract
from winproladder_mcp.ir import Arithmetic, ProcessFunction, compile_network, decode_network
from winproladder_mcp.ldr import parse
from winproladder_mcp.service import Service


def common_spec() -> CommonFunSpec:
    return CommonFunSpec.model_validate(
        {
            "requirement": "Exercise parameterized common functions with series enables",
            "functions": [
                {
                    "type": "move_word",
                    "source": -12,
                    "destination": "R0",
                    "enable": "X0 & M0",
                },
                {
                    "type": "arithmetic",
                    "operation": "add",
                    "sa": "R0",
                    "sb": 5,
                    "destination": "R1",
                    "enable": "X0 & M0",
                },
                {
                    "type": "arithmetic",
                    "operation": "sub",
                    "sa": "R1",
                    "sb": "R10",
                    "destination": "R2",
                },
                {
                    "type": "arithmetic",
                    "operation": "mul",
                    "sa": "R2",
                    "sb": "R11",
                    "destination": "R3",
                },
                {
                    "type": "arithmetic",
                    "operation": "div",
                    "sa": "R3",
                    "sb": "R12",
                    "destination": "R5",
                },
                {"type": "increment", "destination": "R140", "enable": "X0 & M0"},
                {"type": "decrement", "destination": "R141", "enable": "X0 & M0"},
                {
                    "type": "bitwise",
                    "operation": "and",
                    "sa": "R140",
                    "sb": "R141",
                    "destination": "R142",
                    "enable": "X0 & M0",
                },
                {
                    "type": "bitwise",
                    "operation": "or",
                    "sa": "R140",
                    "sb": "R141",
                    "destination": "R143",
                    "enable": "X0 & M0",
                },
                {
                    "type": "exclusive_logic",
                    "operation": "xor",
                    "sa": "R142",
                    "sb": "R143",
                    "destination": "R144",
                    "enable": "X0 & M0",
                },
                {
                    "type": "exclusive_logic",
                    "operation": "xnr",
                    "sa": "R142",
                    "sb": "R143",
                    "destination": "R145",
                    "enable": "X0 & M0",
                },
                {
                    "type": "zone_compare",
                    "source": "R144",
                    "upper": 100,
                    "lower": -100,
                    "enable": "X0",
                    "within": [{"device": "M", "address": 20}],
                    "above": [{"device": "M", "address": 21}],
                    "below": [{"device": "M", "address": 22}],
                },
                {
                    "type": "mean",
                    "source": "D200",
                    "count": 10,
                    "destination": "D500",
                    "enable": "X0",
                    "error": [{"device": "M", "address": 23}],
                },
                {
                    "type": "sqrt",
                    "source": "R150",
                    "destination": "R151",
                    "enable": "X0",
                    "error": [{"device": "M", "address": 24}],
                },
                {"type": "neg", "destination": "R152", "enable": "X0 & M0"},
                {"type": "abs", "destination": "R153", "enable": "X0 & M0"},
                {"type": "ext", "destination": "R154", "enable": "X0 & M0"},
                {
                    "type": "compare",
                    "sa": "R5",
                    "sb": "R6",
                    "equal": [{"device": "M", "address": 10}],
                    "greater": [{"device": "M", "address": 11}],
                    "less": [{"device": "M", "address": 12}],
                },
                {
                    "type": "word_conversion",
                    "operation": "to_bcd",
                    "source": 123,
                    "destination": "R7",
                },
                {
                    "type": "word_conversion",
                    "operation": "to_bin",
                    "source": "R7",
                    "destination": "R8",
                },
                {
                    "type": "div48",
                    "encoding": "two_inputs",
                    "sa": "R160",
                    "sb": "R163",
                    "destination": "R166",
                    "enable": "X0 & M0",
                },
                {
                    "type": "sum",
                    "source": "R170",
                    "count": 4,
                    "destination": "R180",
                    "enable": "X0",
                },
                {
                    "type": "lcnv",
                    "mode": 0,
                    "source": "R8",
                    "table": "R20",
                    "destination": "R30",
                    "length": 1,
                },
                {"type": "timer", "address": 0, "preset": 100, "enable": "X0 & M0"},
                {
                    "type": "counter",
                    "address": 0,
                    "preset": 10,
                    "pulse": "X0 & M0",
                    "clear": "X1",
                },
                {
                    "type": "accumulative_timer",
                    "unit_ms": 10,
                    "timing": "X0 & M0",
                    "enable": "X1",
                    "pv": "R40",
                    "cv": "R41",
                },
                {
                    "type": "pid",
                    "enable": "X0 & M0",
                    "bumpless": "X1",
                    "direction": "TRUE",
                    "interval": 10,
                    "setting": "R100",
                    "destination": "R110",
                    "parameters": "R120",
                    "work": "R130",
                },
            ],
        }
    )


def test_common_fun_builder_uses_canonical_actions_and_preserves_parameters():
    ladder, design = common_fun_ladder(common_spec())
    assert len(ladder.networks) == 27
    move = ladder.networks[0].action
    assert isinstance(move, ProcessFunction)
    assert (move.source, move.destination, move.enable) == (-12, "R0", "X0 & M0")
    add = ladder.networks[1].action
    assert isinstance(add, Arithmetic)
    assert add.model_dump()["sb"] == 5
    assert [ladder.networks[i].action.sb for i in (2, 3, 4)] == ["R10", "R11", "R12"]
    assert ladder.networks[12].action.count == 10
    assert ladder.networks[23].block is not None
    assert ladder.networks[24].block is not None
    assert design["network_count"] == 27
    assert len(design["evidence"]) == 27
    assert {item["key"] for item in design["evidence"]} <= set(COMMON_FUN_EVIDENCE)
    by_key = {item["key"]: item for item in design["evidence"]}
    assert by_key["div48"]["evidence_level"] == "sample-backed"
    assert by_key["sum"]["evidence_level"] == "sample-backed"
    assert all(
        item["gui_verification"] == "not verified for generated artifact"
        for item in design["evidence"]
    )


def test_common_fun_suite_generates_crc_valid_round_trippable_ldr(tmp_path):
    service = Service(tmp_path)
    ladder, _ = common_fun_ladder(common_spec())
    result = service.generate(
        "common-fun-suite.ldr",
        ladder,
        io_contract=IOContract(inputs=["X0", "X1"], outputs=[]),
        strict_writers=True,
    )
    path = Path(result["path"])
    document = parse(path.read_bytes())
    decoded = [decode_network(record.payload) for record in reversed(document.records)]
    assert all(record.crc_valid for record in document.records)
    assert all(network is not None for network in decoded)
    assert result["artifact_validation"] == {
        "crc_valid": True,
        "decoded_networks": 27,
        "scope": "Exact emitted LDR bytes; offline model, not GUI or PLC validation",
    }


def test_common_fun_evidence_covers_every_supported_discriminator_form():
    keys = {
        "move_word",
        "arithmetic:add",
        "arithmetic:sub",
        "arithmetic:mul",
        "arithmetic:div",
        "increment",
        "decrement",
        "compare",
        "bitwise:and",
        "bitwise:or",
        "word_conversion:to_bcd",
        "word_conversion:to_bin",
        "adcnv",
        "mlc",
        "bitrd",
        "bitwr",
        "float_compare",
        "float_zone_compare",
        "float_operation:i_to_f",
        "float_operation:f_to_i",
        "float_operation:add",
        "float_operation:sub",
        "float_operation:mul",
        "float_operation:div",
        "float_operation:sqrt",
        "float_operation:sin",
        "float_operation:cos",
        "float_operation:tan",
        "float_operation:neg",
        "float_operation:abs",
        "float_operation:ln",
        "float_operation:exp",
        "float_operation:log",
        "float_operation:pow",
        "float_operation:asin",
        "float_operation:acos",
        "float_operation:atan",
        "ramp",
        "ramp2",
        "reg_to_table",
        "table_to_reg",
        "table_to_table",
        "block_table_move",
        "table_swap",
        "register_table_search",
        "table_compare",
        "table_fill",
        "table_shift",
        "table_rotate",
        "queue",
        "stack",
        "block_compare",
        "matrix_and",
        "matrix_or",
        "matrix_xor",
        "matrix_xnr",
        "matrix_invert",
        "matrix_compare",
        "matrix_bit_read",
        "matrix_bit_write",
        "matrix_bit_shift",
        "matrix_bit_rotate",
        "matrix_bit_count",
        "table_sort",
        "zone_write",
        "move_inverse",
        "toggle_bit",
        "bit_move",
        "nibble_move",
        "byte_move",
        "word_exchange",
        "byte_swap",
        "nibble_unite",
        "nibble_distribute",
        "byte_unite",
        "byte_distribute",
        "shift_left",
        "shift_right",
        "rotate_left",
        "rotate_right",
        "binary_to_gray",
        "gray_to_binary",
        "decode_bits",
        "hms_to_seconds",
        "seconds_to_hms",
        "encode_bits",
        "to_seven_segment",
        "ascii_literal",
        "ascii_to_hex",
        "hex_to_ascii",
        "bit_shift",
        "system_status",
        "file_register",
        "memory_pack_write",
        "memory_pack_read",
        "wdt",
        "rswdt",
        "hsctr",
        "hsctw",
        "udctr",
        "imdio",
        "tkey",
        "hkey",
        "dsw",
        "7sgdl",
        "muxi",
        "pulse_output",
        "pwm",
        "speed_detect",
        "tpctl",
        "comparison_contact:eq",
        "comparison_contact:gt",
        "comparison_contact:lt",
        "comparison_contact:ne",
        "comparison_contact:ge",
        "comparison_contact:le",
        "div48",
        "sum",
        "mean",
        "sqrt",
        "neg",
        "abs",
        "ext",
        "pid",
        "lcnv",
        "exclusive_logic:xor",
        "exclusive_logic:xnr",
        "zone_compare",
        "timer",
        "counter",
        "accumulative_timer",
    }
    assert set(COMMON_FUN_EVIDENCE) == keys
    assert all(item["samples"] and item["forms"] for item in COMMON_FUN_EVIDENCE.values())


def test_fun19_or_is_round_trippable_but_not_mislabeled_as_native_export():
    spec = CommonFunSpec.model_validate(
        {
            "requirement": "Parameterizable inferred OR form",
            "functions": [
                {
                    "type": "bitwise",
                    "operation": "or",
                    "sa": "R0",
                    "sb": "R1",
                    "destination": "R2",
                    "enable": "X0 & M0",
                }
            ],
        }
    )
    ladder, design = common_fun_ladder(spec)
    payload = compile_network(ladder.networks[0])
    decoded = decode_network(payload)
    assert decoded is not None and compile_network(decoded) == payload
    evidence = design["evidence"][0]
    assert evidence["key"] == "bitwise:or"
    assert "inferred" in evidence["forms"]
    assert evidence["evidence_level"] == "inferred"


def test_inferred_register_arithmetic_forms_preserve_user_parameters():
    for operation, opcode in [("sub", "f464"), ("mul", "f466"), ("div", "f468")]:
        action = Arithmetic(
            operation=operation,
            sa="D100",
            sb="R20",
            destination="D200",
            enable="X0 & M0",
        )
        ladder, design = common_fun_ladder(
            CommonFunSpec(requirement="Inferred register Sb", functions=[action])
        )
        payload = compile_network(ladder.networks[0])
        assert bytes.fromhex(opcode) in payload
        decoded = decode_network(payload)
        assert decoded is not None
        assert decoded.action.model_dump(exclude={"enable"}) == action.model_dump(
            exclude={"enable"}
        )
        assert compile_network(decoded) == payload
        assert design["evidence"][0]["evidence_level"] == "inferred"


def test_inferred_mean_constant_count_round_trips_with_exact_source_span():
    spec = CommonFunSpec.model_validate(
        {
            "requirement": "MEAN with constant N",
            "functions": [
                {
                    "type": "mean",
                    "source": "D200",
                    "count": 10,
                    "destination": "D500",
                    "enable": "X0 & M0",
                }
            ],
        }
    )
    ladder, design = common_fun_ladder(spec)
    action = ladder.networks[0].action
    payload = compile_network(ladder.networks[0])
    assert bytes.fromhex("f6e20009") in payload
    assert action.source_devices() == {f"D{i}" for i in range(200, 210)}
    decoded = decode_network(payload)
    assert decoded is not None
    assert decoded.action.model_dump(exclude={"enable"}) == action.model_dump(exclude={"enable"})
    assert compile_network(decoded) == payload
    assert design["evidence"][0]["evidence_level"] == "inferred"


def test_gui_observed_mean_constant_count_uses_n_minus_one_encoding():
    for count, encoded in [(2, 1), (10, 9), (11, 10), (256, 255)]:
        spec = CommonFunSpec.model_validate(
            {
                "requirement": "GUI-observed MEAN count mapping",
                "functions": [
                    {
                        "type": "mean",
                        "source": "D300",
                        "count": count,
                        "destination": "D400",
                    }
                ],
            }
        )
        ladder, _ = common_fun_ladder(spec)
        payload = compile_network(ladder.networks[0])
        assert bytes.fromhex("f6e2") + encoded.to_bytes(2, "big") in payload
        decoded = decode_network(payload)
        assert decoded is not None and decoded.action.count == count
        assert compile_network(decoded) == payload
