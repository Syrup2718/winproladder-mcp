"""test24: sampled MOV/MOV/, TOGG, SORT/Z-WR and matrix bit operations.

Basic manual 7-23..25; advanced manual 7-111..112, 7-122..124.
Only observed opcode forms; other legal PLC forms need separate encodings.
"""

from typing import TYPE_CHECKING

from .logic import bit_address
from .registers import decode_word, encode_word, register_span, word_references
from .table_functions import output_bits

if TYPE_CHECKING:
    from .ir import ProcessFunction

FIELDS = {
    "move_word": ("source", "destination"),
    "move_inverse": ("source", "destination"),
    "toggle_bit": ("bit_destination",),
    "table_sort": ("source", "destination"),
    "zone_write": ("destination",),
    "matrix_bit_shift": ("source", "destination"),
    "matrix_bit_rotate": ("source", "destination"),
    "matrix_bit_count": ("source", "destination"),
}
CONTROLS = {
    "move_word": ("enable",),
    "move_inverse": ("enable",),
    "toggle_bit": ("trigger",),
    "table_sort": ("enable", "ascending"),
    "zone_write": ("enable", "ones"),
    "matrix_bit_shift": ("enable", "input_bit", "left"),
    "matrix_bit_rotate": ("enable", "left"),
    "matrix_bit_count": ("enable", "ones"),
}
CODES = {
    "move_word": "f4ac",
    "move_inverse": "f4ae",
    "toggle_bit": "f8e4",
    "table_sort": "f456",
    "zone_write": "f75c",
    "matrix_bit_shift": "f402",
    "matrix_bit_rotate": "f44e",
    "matrix_bit_count": "f44c",
}
STATUS = {
    "move_word": (),
    "move_inverse": (),
    "toggle_bit": (),
    "table_sort": ("error",),
    "zone_write": ("error",),
    "matrix_bit_shift": ("output",),
    "matrix_bit_rotate": ("output",),
    "matrix_bit_count": ("zero",),
}
ORDER = {
    "move_word": FIELDS["move_word"],
    "move_inverse": FIELDS["move_inverse"],
    "toggle_bit": FIELDS["toggle_bit"],
    "table_sort": ("source", "destination", "length"),
    "zone_write": ("length", "destination"),
    "matrix_bit_shift": ("source", "destination", "length"),
    "matrix_bit_rotate": ("source", "destination", "length"),
    "matrix_bit_count": ("source", "length", "destination"),
}
LENGTHS = {
    "table_sort": (2, 127),
    "zone_write": (1, 511),
    "matrix_bit_shift": (2, 256),
    "matrix_bit_rotate": (2, 256),
    "matrix_bit_count": (2, 256),
}
MOVES = {"move_word", "move_inverse"}


def move_word(name: str, *, writable: bool = False) -> bytes:
    # WY8 is the exact byte-aligned 16-bit anchor, NOT an R/D word address.
    if name == "WY8":
        return bytes.fromhex("0821")
    if name.startswith("D") and name[1:].isdigit() and int(name[1:]) > 3071:
        raise ValueError("MOV codec follows basic manual 7-23..24 D0..3071; higher D unresolved")
    return encode_word(name, writable=writable)


def operand_check(kind: str, field: str, name: str) -> None:
    if kind == "toggle_bit":
        output_bits(name, 1)
    elif kind in MOVES:
        move_word(name, writable=field == "destination")
        if kind == "move_inverse" and name.startswith("R") and 3848 <= int(name[1:]) <= 3903:
            raise ValueError("MOV/ basic manual 7-24 limits IR to R3847; higher IR unresolved")
    else:
        register_span(name, 1, writable=field == "destination")


def references(action: "ProcessFunction") -> tuple[set[str], set[str]]:
    if action.type == "toggle_bit":
        bits = output_bits(action.operand("bit_destination"), 1)
        return bits, bits.copy()
    if action.type in MOVES:

        def refs(name: str) -> set[str]:
            return (
                {"WY8", *(f"Y{i}" for i in range(8, 24))}
                if name == "WY8"
                else word_references(name)
            )

        return refs(action.operand("source")), refs(action.operand("destination"))
    assert action.length is not None
    reads = (
        register_span(action.operand("source"), action.length)
        if "source" in FIELDS[action.type]
        else set()
    )
    count = 1 if action.type == "matrix_bit_count" else action.length
    writes = register_span(action.operand("destination"), count, writable=True)
    return reads, writes


def compile_operands(action: "ProcessFunction") -> bytes:
    raw = b""
    for field in ORDER[action.type]:
        if field == "length":
            assert action.length is not None
            # Unlike L, Z-WR N is stored literally, without subtracting one.
            raw += (action.length - (action.type != "zone_write")).to_bytes(2, "big")
        elif field == "bit_destination":
            raw += bit_address(action.operand(field)).to_bytes(2, "big")
        else:
            raw += (
                move_word(action.operand(field))
                if action.type in MOVES
                else encode_word(action.operand(field))
            )
    return raw


def decode_operands(kind: str, tail: bytes) -> tuple[dict[str, object], int]:
    size = 2 * len(ORDER[kind])
    if len(tail) < size:
        raise ValueError("Truncated test24 operands")
    fields: dict[str, object] = {}
    for i, field in enumerate(ORDER[kind]):
        raw = tail[2 * i : 2 * i + 2]
        value = int.from_bytes(raw, "big")
        if field == "length":
            fields[field] = value + (kind != "zone_write")
        elif field == "bit_destination":
            if 0x100 <= value <= 0x1FF:
                fields[field] = f"Y{value - 0x100}"
            elif bit_address("M0") <= value <= bit_address("M999"):
                fields[field] = f"M{value - bit_address('M0')}"
            else:
                raise ValueError("Unencoded TOGG bit family")
        else:
            fields[field] = "WY8" if raw == bytes.fromhex("0821") else decode_word(raw)
    return fields, size
