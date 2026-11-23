"""Native codec compatibility anchors with explicit evidence boundaries.

This module deliberately contains only forms backed by privately retained native evidence.
Static Prolad18 metadata aliases and inferred operand forms belong in test
fixtures or the separate inferred table until an exported LDR establishes
their exact serialized form.
"""

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final


def _forms(**values: bytes) -> Mapping[str, bytes]:
    return MappingProxyType(values)


SAMPLE_BACKED_MODE_OPCODE_FORMS: Final[Mapping[str, Mapping[str, bytes]]] = MappingProxyType(
    {
        "move_word": _forms(register=bytes.fromhex("f4ac"), constant=bytes.fromhex("f5ac")),
        "arithmetic": _forms(
            add_register=bytes.fromhex("f462"),
            add_constant=bytes.fromhex("f662"),
            sub_constant=bytes.fromhex("f664"),
            mul_constant=bytes.fromhex("f666"),
            div_constant=bytes.fromhex("f668"),
        ),
        "adcnv": _forms(unipolar=bytes.fromhex("f55a")),
        "lcnv": _forms(mode0_length1=bytes.fromhex("f57c")),
        "accumulative_timer": _forms(
            unit_10_ms=bytes.fromhex("fc41"),
            unit_100_ms=bytes.fromhex("fc42"),
            unit_1000_ms=bytes.fromhex("fc43"),
        ),
    }
)

SAMPLE_BACKED_MODE_OPCODE_ALLOWLIST: Final[frozenset[bytes]] = frozenset(
    opcode for family in SAMPLE_BACKED_MODE_OPCODE_FORMS.values() for opcode in family.values()
)

# These forms are supported for productive generation from static metadata and
# a verified neighbouring opcode family, but do not have their own native LDR
# export.  Keeping them separate prevents offline round trips from being
# mislabeled as native-sample verification.
INFERRED_MODE_OPCODE_FORMS: Final[Mapping[str, Mapping[str, bytes]]] = MappingProxyType(
    {
        "arithmetic": _forms(
            sub_register=bytes.fromhex("f464"),
            mul_register=bytes.fromhex("f466"),
            div_register=bytes.fromhex("f468"),
        ),
        "mean": _forms(constant_count=bytes.fromhex("f6e2")),
    }
)


def sample_backed_opcode(family: str, form: str) -> bytes:
    """Return one exact sampled mode/opcode pair, rejecting unknown forms."""

    try:
        return SAMPLE_BACKED_MODE_OPCODE_FORMS[family][form]
    except KeyError as error:
        raise ValueError(f"Unsupported native opcode form: {family}/{form}") from error


def is_sample_backed_mode_opcode(opcode: bytes) -> bool:
    """Report whether an exact two-byte mode/opcode pair has a native sample."""

    return len(opcode) == 2 and opcode in SAMPLE_BACKED_MODE_OPCODE_ALLOWLIST


def inferred_opcode(family: str, form: str) -> bytes:
    """Return an explicitly inferred pair without granting sample-backed status."""

    try:
        return INFERRED_MODE_OPCODE_FORMS[family][form]
    except KeyError as error:
        raise ValueError(f"Unsupported inferred native opcode form: {family}/{form}") from error


def pack_e4_join(row: int, column: int) -> bytes:
    """Pack a proven WinProLadder E4/E5 join coordinate into two bytes."""

    if type(row) is not int or not 0 <= row <= 15:
        raise ValueError("E4/E5 join row must be an integer in 0..15")
    if type(column) is not int or not 0 <= column <= 31:
        raise ValueError("E4/E5 join column must be an integer in 0..31")
    return bytes((0xE4 | (row >> 3), ((row & 0x07) << 5) | column))


def unpack_e4_join(byte0: int, byte1: int) -> tuple[int, int]:
    """Unpack an E4/E5 join word into its native row and column."""

    if type(byte0) is not int or byte0 not in {0xE4, 0xE5}:
        raise ValueError("E4/E5 join first byte must be 0xE4 or 0xE5")
    if type(byte1) is not int or not 0 <= byte1 <= 0xFF:
        raise ValueError("E4/E5 join second byte must be an integer byte")
    return ((byte0 & 0x01) << 3) | (byte1 >> 5), byte1 & 0x1F
