import math

import pytest

from winproladder_mcp.floating import (
    decode_float_register,
    decode_float_source,
    encode_float_register,
    encode_float_source,
    float_bank,
    float_source_reads,
    float_span,
    normalize_float_source,
)
from winproladder_mcp.native_codec import (
    inferred_opcode,
    is_sample_backed_mode_opcode,
    pack_e4_join,
    sample_backed_opcode,
    unpack_e4_join,
)


def test_opcode_evidence_boundaries_and_join_coordinates() -> None:
    assert sample_backed_opcode("move_word", "register") == bytes.fromhex("f4ac")
    assert inferred_opcode("mean", "constant_count") == bytes.fromhex("f6e2")
    assert is_sample_backed_mode_opcode(bytes.fromhex("f4ac"))
    assert not is_sample_backed_mode_opcode(b"\xf4")
    assert not is_sample_backed_mode_opcode(bytes.fromhex("f6e2"))
    with pytest.raises(ValueError, match="Unsupported native opcode form"):
        sample_backed_opcode("move_word", "unknown")
    with pytest.raises(ValueError, match="Unsupported inferred native opcode form"):
        inferred_opcode("mean", "unknown")

    for row, column in [(0, 0), (7, 31), (8, 0), (15, 31)]:
        assert unpack_e4_join(*pack_e4_join(row, column)) == (row, column)
    for row in [-1, 16, True]:
        with pytest.raises(ValueError, match="row"):
            pack_e4_join(row, 0)
    for column in [-1, 32, True]:
        with pytest.raises(ValueError, match="column"):
            pack_e4_join(0, column)
    for first, second in [(0xE3, 0), (0xE4, -1), (0xE4, 256), (0xE4, True)]:
        with pytest.raises(ValueError):
            unpack_e4_join(first, second)


@pytest.mark.parametrize("name", ["R0", "R3839", "R5000", "R8071", "D0", "D4095"])
def test_float_register_banks_round_trip(name: str) -> None:
    assert decode_float_register(encode_float_register(name)) == name


def test_float_register_and_span_rejections() -> None:
    for name in ["R3840", "R4999", "R8072", "D4096", "M0", "R01", "R-1"]:
        with pytest.raises(ValueError):
            float_bank(name)
    assert float_span("R3838", 2) == {"R3838", "R3839"}
    for name, count in [("R3839", 2), ("D0", 0)]:
        with pytest.raises(ValueError, match="span"):
            float_span(name, count)
    for raw in [b"\x0a", b"\x0a\x01", b"\x60\x00"]:
        with pytest.raises(ValueError):
            decode_float_register(raw)


def test_float_sources_are_bounded_and_canonical() -> None:
    register = encode_float_source("D10")
    assert decode_float_source(register, False) == "D10"
    assert float_source_reads("D10") == {"D10", "D11"}
    assert float_source_reads(1.25) == set()
    value = normalize_float_source(1.1)
    assert isinstance(value, float) and value != 1.1
    assert normalize_float_source("R10") == "R10"
    assert decode_float_source(encode_float_source(-0.0), True) == -0.0
    for value in [math.inf, math.nan, 1e100]:
        with pytest.raises(ValueError):
            encode_float_source(value)
    for raw, constant in [(b"\x00", True), (b"\x00\x01\x0a\x00", False)]:
        with pytest.raises(ValueError):
            decode_float_source(raw, constant)
