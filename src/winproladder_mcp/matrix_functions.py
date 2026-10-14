"""Sampled matrix functions FUN120..127; manual 7-113..121, test23."""

from typing import TYPE_CHECKING

from .registers import decode_register, encode_register, register_span

if TYPE_CHECKING:
    from .ir import ProcessFunction

FIELDS = {
    **{
        k: ("source", "source_b", "destination")
        for k in ("matrix_and", "matrix_or", "matrix_xor", "matrix_xnr")
    },
    "matrix_invert": ("source", "destination", "length_register"),
    "matrix_compare": ("source", "source_b", "pointer"),
    "matrix_bit_read": ("source", "pointer"),
    "matrix_bit_write": ("destination", "pointer"),
}
CONTROLS = {
    **{
        k: ("enable",)
        for k in ("matrix_and", "matrix_or", "matrix_xor", "matrix_xnr", "matrix_invert")
    },
    "matrix_compare": ("enable", "from_head", "different"),
    "matrix_bit_read": ("enable", "increment", "clear"),
    "matrix_bit_write": ("enable", "input_bit", "increment", "clear"),
}
CODES = {
    "matrix_and": "f4d2",
    "matrix_or": "f4d3",
    "matrix_xor": "f4d4",
    "matrix_xnr": "f4d5",
    "matrix_invert": "f4d6",
    "matrix_compare": "f412",
    "matrix_bit_read": "f40e",
    "matrix_bit_write": "f42a",
}
STATUS = {
    **{k: () for k in ("matrix_and", "matrix_or", "matrix_xor", "matrix_xnr", "matrix_invert")},
    "matrix_compare": ("found", "done", "error"),
    "matrix_bit_read": ("output", "done", "error"),
    "matrix_bit_write": ("done", "error"),
}
ORDER = {
    **{k: (*FIELDS[k], "length") for k in ("matrix_and", "matrix_or", "matrix_xor", "matrix_xnr")},
    "matrix_invert": FIELDS["matrix_invert"],
    "matrix_compare": ("source", "source_b", "length", "pointer"),
    "matrix_bit_read": ("source", "length", "pointer"),
    "matrix_bit_write": ("destination", "length", "pointer"),
}


def references(action: "ProcessFunction") -> tuple[set[str], set[str]]:
    count = 256 if action.type == "matrix_invert" else action.length
    assert count is not None
    reads: set[str] = set()
    writes: set[str] = set()
    for field in FIELDS[action.type]:
        name = action.operand(field)
        if field in {"source", "source_b"}:
            reads |= register_span(name, count)
        elif field == "destination":
            writes |= register_span(name, count, writable=True)
            if action.type == "matrix_bit_write":
                reads |= writes  # Preserve the other 15 bits of the selected word.
        elif field == "pointer":
            words = register_span(name, 1, writable=True)
            reads |= words
            writes |= words
        elif field == "length_register":
            if name.startswith("R") and 3840 <= int(name[1:]) <= 3903:
                raise ValueError("MINV length register requires HR/ROR/DR (manual 7-118)")
            reads |= register_span(name, 1)
    return reads, writes


def compile_operands(action: "ProcessFunction") -> bytes:
    raw = b""
    for field in ORDER[action.type]:
        if field == "length":
            assert action.length is not None
            raw += (action.length - 1).to_bytes(2, "big")
        else:
            raw += encode_register(action.operand(field))
    return raw


def decode_operands(kind: str, tail: bytes) -> tuple[dict[str, object], int]:
    fields: dict[str, object] = {}
    size = 2 * len(ORDER[kind])
    if len(tail) < size:
        raise ValueError("Truncated matrix operands")
    for i, field in enumerate(ORDER[kind]):
        raw = tail[2 * i : 2 * i + 2]
        fields[field] = (
            int.from_bytes(raw, "big") + 1 if field == "length" else decode_register(raw)
        )
    return fields, size
