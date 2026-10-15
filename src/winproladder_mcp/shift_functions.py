"""FUN50..57: test26 forms, advanced manual 7-38..45."""

from typing import TYPE_CHECKING

from .packing_functions import span
from .registers import decode_word, encode_word, register_bank, register_span, word_references

if TYPE_CHECKING:
    from .ir import ProcessFunction

FIELDS = {
    "byte_distribute": ("source", "destination", "length_register"),
    "shift_left": ("destination",),
    "shift_right": ("destination", "length_register"),
    "rotate_left": ("destination", "length_register"),
    "rotate_right": ("destination",),
    "binary_to_gray": ("source", "destination"),
    "gray_to_binary": ("source", "destination"),
    "decode_bits": ("source", "destination"),
}
CONTROLS = {
    k: (("enable", "input_bit") if k in {"shift_left", "shift_right"} else ("enable",))
    for k in FIELDS
}
CODES = {
    "byte_distribute": "f478",
    "shift_left": "f550",  # observed constant N
    "shift_right": "f452",  # observed register N
    "rotate_left": "f4a2",  # observed register N
    "rotate_right": "f5aa",  # observed constant N
    "binary_to_gray": "f47a",
    "gray_to_binary": "f479",
    "decode_bits": "f4a8",
}
SHIFTS = {"shift_left", "shift_right", "rotate_left", "rotate_right"}
STATUS = {
    k: (("output", "error") if k in SHIFTS else ("error",) if k == "decode_bits" else ())
    for k in FIELDS
}
ORDER = {
    "byte_distribute": ("length_register", "source", "destination"),
    "shift_left": ("count", "destination"),
    "shift_right": ("length_register", "destination"),
    "rotate_left": ("length_register", "destination"),
    "rotate_right": ("count", "destination"),
    "binary_to_gray": ("source", "destination"),
    "gray_to_binary": ("source", "destination"),
    "decode_bits": ("source", "destination", "source_index", "bit_length"),
}


def check_parameters(action: "ProcessFunction") -> None:
    if action.type in {"shift_left", "rotate_right"}:
        if action.count is None or not 1 <= action.count <= 16:
            raise ValueError("16-bit shift/rotate count requires 1..16 (manual 7-39..42)")
    elif action.count is not None:
        raise ValueError(f"{action.type} has no sampled constant N form")
    if action.type == "decode_bits":
        if action.source_index is None or action.bit_length is None:
            raise ValueError("DECOD requires source_index=Ns and bit_length=NL (1..8 bits)")
    elif action.source_index is not None or action.bit_length is not None:
        raise ValueError(f"{action.type} has no source_index/bit_length")
    if action.destination_index is not None:
        raise ValueError(f"{action.type} has no destination_index")


def operand_check(kind: str, field: str, name: str) -> None:
    if kind == "byte_distribute":
        register_span(name, 1, writable=True)  # HR/ROR/DR only, including N and S.
    else:
        encode_word(name, writable=field == "destination")


def decode_source_span(name: str, start: int, bits: int) -> set[str]:
    words = 2 if start + bits > 16 else 1
    if name.startswith(("R", "D")):
        address, _, high = register_bank(name)
        # Manual 7-45: clip at end of operand bank instead of rejecting Ns+NL>16.
        return register_span(name, min(words, high - address + 1))
    if name in {"WX0", "WY0"}:
        return {name} | {f"{name[1]}{i}" for i in range(words * 16)}
    if name.startswith("T"):
        n = int(name[1:])
        return {f"T{i}" for i in range(n, min(n + words, 256))}
    return span(name, words)


def references(action: "ProcessFunction") -> tuple[set[str], set[str]]:
    kind = action.type
    if kind == "byte_distribute":
        # Runtime N bytes: ceil(N/2) source words and N zero-extended output words.
        reads = register_span(action.operand("source"), 128)
        reads |= register_span(action.operand("length_register"), 1)
        return reads, register_span(action.operand("destination"), 256, writable=True)
    if kind == "decode_bits":
        assert action.source_index is not None and action.bit_length is not None
        reads = decode_source_span(action.operand("source"), action.source_index, action.bit_length)
        count = max(1, (1 << action.bit_length) // 16)
        writes = span(action.operand("destination"), count, writable=True)
        if action.bit_length < 4:
            reads |= writes  # Manual specifies 2^NL bits; unused word bits not resolved.
        return reads, writes
    writes = span(action.operand("destination"), 1, writable=True)
    if kind in SHIFTS:
        reads = writes.copy()
        if "length_register" in FIELDS[kind]:
            reads |= word_references(action.operand("length_register"))
    else:
        reads = word_references(action.operand("source"))
    return reads, writes


def compile_operands(action: "ProcessFunction") -> bytes:
    raw = b""
    for field in ORDER[action.type]:
        if field in {"count", "source_index", "bit_length"}:
            value = getattr(action, field)
            assert isinstance(value, int)
            raw += value.to_bytes(2, "big")
        else:
            raw += encode_word(action.operand(field))
    return raw


def decode_operands(kind: str, tail: bytes) -> tuple[dict[str, object], int]:
    size = 2 * len(ORDER[kind])
    if len(tail) < size:
        raise ValueError("Truncated shift/conversion operands")
    fields: dict[str, object] = {}
    for i, field in enumerate(ORDER[kind]):
        raw = tail[2 * i : 2 * i + 2]
        fields[field] = (
            int.from_bytes(raw, "big")
            if field in {"count", "source_index", "bit_length"}
            else decode_word(raw)
        )
    return fields, size
