"""test27 FUN06/58..64; basic 7-20, advanced 7-46..57."""

from typing import TYPE_CHECKING

from .packing_functions import span
from .registers import decode_word, encode_word, register_bank, register_span

if TYPE_CHECKING:
    from .ir import ProcessFunction

FIELDS = {
    "encode_bits": ("source", "destination"),
    "to_seven_segment": ("source", "destination"),
    "ascii_literal": ("destination",),
    "hms_to_seconds": ("source", "destination"),
    "seconds_to_hms": ("source", "destination"),
    "ascii_to_hex": ("source", "destination"),
    "hex_to_ascii": ("source", "destination"),
    "bit_shift": ("destination",),
}
CONTROLS = {
    k: (
        ("enable", "high_priority")
        if k == "encode_bits"
        else ("enable", "input_bit", "left", "clear")
        if k == "bit_shift"
        else ("enable",)
    )
    for k in FIELDS
}
CODES = {
    "encode_bits": "f44d",
    "to_seven_segment": "f4e6",
    "ascii_literal": "f4f0",
    "hms_to_seconds": "f4dc",
    "seconds_to_hms": "f4dd",
    "ascii_to_hex": "f5bf",
    "hex_to_ascii": "f5a9",
    "bit_shift": "f428",
}
STATUS = {
    "encode_bits": ("zero", "error"),
    "to_seven_segment": ("error",),
    "ascii_literal": (),
    "hms_to_seconds": ("zero",),
    "seconds_to_hms": ("zero", "overflow"),
    "ascii_to_hex": ("error",),
    "hex_to_ascii": (),
    "bit_shift": ("output",),
}
ORDER = {
    "encode_bits": ("source", "destination", "source_index", "count"),
    "to_seven_segment": ("source", "destination", "count"),
    "ascii_literal": ("destination",),
    "hms_to_seconds": ("source", "destination"),
    "seconds_to_hms": ("source", "destination"),
    "ascii_to_hex": ("count", "source", "destination"),
    "hex_to_ascii": ("count", "source", "destination"),
    "bit_shift": ("destination",),
}
COUNTS = {
    "encode_bits": (2, 256),
    "to_seven_segment": (0, 3),
    "ascii_to_hex": (1, 511),
    "hex_to_ascii": (1, 511),
}
# Exact sampled ABCDEF literal block. Do not infer arbitrary text from one sample.
ASCII_LITERAL = bytes.fromhex("0007204221442246000000000000")


def check_parameters(action: "ProcessFunction") -> None:
    if action.type in COUNTS:
        low, high = COUNTS[action.type]
        if action.count is None or not low <= action.count <= high:
            raise ValueError(f"{action.type} count requires {low}..{high}")
    elif action.count is not None:
        raise ValueError(f"{action.type} has no count")
    if (action.type == "encode_bits") != (action.source_index is not None):
        raise ValueError("Only ENCOD requires source_index=Ns")
    if action.destination_index is not None or action.bit_length is not None:
        raise ValueError("Unencoded destination_index/bit_length for test27")
    if action.type == "ascii_literal":
        if action.text != "ABCDEF":
            raise ValueError("ASC currently encodes exact ABCDEF literal; other strings unresolved")
    elif action.text is not None:
        raise ValueError(f"{action.type} has no literal text")


def operand_check(kind: str, field: str, name: str) -> None:
    encode_word(name, writable=field == "destination")
    if kind == "bit_shift" and name.startswith("D") and int(name[1:]) > 3071:
        raise ValueError("BSHF basic manual 7-20 D0..3071; higher D codec not confirmed")


def encode_source_span(name: str, start: int, count: int) -> set[str]:
    words = (start + count + 15) // 16
    if name.startswith(("R", "D")):
        address, _, high = register_bank(name)
        return register_span(name, min(words, high - address + 1))
    if name in {"WX0", "WY0"}:
        return {name} | {f"{name[1]}{i}" for i in range(min(words * 16, 256))}
    if name.startswith("T"):
        address = int(name[1:])
        return {f"T{i}" for i in range(address, min(address + words, 256))}
    return span(name, words)


def references(action: "ProcessFunction") -> tuple[set[str], set[str]]:
    kind = action.type
    dest = action.operand("destination")
    if kind == "ascii_literal":
        return set(), span(dest, 3, writable=True)
    if kind == "bit_shift":
        words = span(dest, 1, writable=True)
        return words.copy(), words
    if kind == "encode_bits":
        assert action.source_index is not None and action.count is not None
        return encode_source_span(
            action.operand("source"), action.source_index, action.count
        ), span(dest, 1, writable=True)
    if kind in {"hms_to_seconds", "seconds_to_hms"}:
        source_count, dest_count = (3, 2) if kind == "hms_to_seconds" else (2, 3)
        return span(action.operand("source"), source_count), span(dest, dest_count, writable=True)
    assert action.count is not None
    n = action.count
    if kind == "to_seven_segment":
        source_count, dest_count = 1, (n + 2) // 2
        preserve = n % 2 == 0  # N+1 odd: unused final high byte remains unchanged.
    elif kind == "ascii_to_hex":
        source_count, dest_count = n, (n + 3) // 4
        preserve = n % 4 != 0
    else:
        source_count, dest_count = (n + 3) // 4, n
        preserve = True  # Every destination high byte is preserved.
    reads = span(action.operand("source"), source_count)
    writes = span(dest, dest_count, writable=True)
    if preserve:
        reads |= writes  # Conservative whole-word dependency for preserved bits.
    return reads, writes


def compile_operands(action: "ProcessFunction") -> bytes:
    raw = (
        ASCII_LITERAL
        if action.type == "ascii_literal"
        else b"\x00\x00"
        if action.type == "seconds_to_hms"
        else b""
    )
    for field in ORDER[action.type]:
        if field in {"source_index", "count"}:
            value = getattr(action, field)
            assert isinstance(value, int)
            raw += (value - (field == "count" and action.type == "encode_bits")).to_bytes(2, "big")
        else:
            raw += encode_word(action.operand(field))
    return raw


def decode_operands(kind: str, tail: bytes) -> tuple[dict[str, object], int]:
    prefix = (
        ASCII_LITERAL
        if kind == "ascii_literal"
        else b"\x00\x00"
        if kind == "seconds_to_hms"
        else b""
    )
    size = len(prefix) + 2 * len(ORDER[kind])
    if len(tail) < size or not tail.startswith(prefix):
        raise ValueError("Truncated or unencoded conversion operands")
    fields: dict[str, object] = {"text": "ABCDEF"} if kind == "ascii_literal" else {}
    tail = tail[len(prefix) :]
    for i, field in enumerate(ORDER[kind]):
        raw = tail[2 * i : 2 * i + 2]
        fields[field] = (
            int.from_bytes(raw, "big") + (field == "count" and kind == "encode_bits")
            if field in {"source_index", "count"}
            else decode_word(raw)
        )
    return fields, size
