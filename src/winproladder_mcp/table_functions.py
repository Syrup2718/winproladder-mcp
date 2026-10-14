"""FUN105..112: sampled 16-bit, non-P forms from test22 (manual 7-100..109)."""

from typing import TYPE_CHECKING

from .logic import bit_address
from .registers import decode_register, encode_register, register_span

if TYPE_CHECKING:
    from .ir import ProcessFunction

FIELDS = {
    "register_table_search": ("source", "pointer"),
    "table_compare": ("source", "destination", "pointer"),
    "table_fill": ("destination",),
    "table_shift": ("input_word", "source", "destination", "output_word"),
    "table_rotate": ("source", "destination"),
    "queue": ("input_word", "destination", "pointer", "output_word"),
    "stack": ("input_word", "destination", "pointer", "output_word"),
    "block_compare": ("input_word", "source", "bit_destination"),
}
CONTROLS = {
    "register_table_search": ("enable", "from_head", "different"),
    "table_compare": ("enable", "from_head", "different"),
    "table_fill": ("enable",),
    "table_shift": ("enable", "left"),
    "table_rotate": ("enable", "left"),
    "queue": ("enable", "push"),
    "stack": ("enable", "push"),
    "block_compare": ("enable",),
}
CODES = {
    "register_table_search": "f50c",  # Constant Rs form; not the unobserved register form.
    "table_compare": "f410",
    "table_fill": "f5f8",  # Constant Rs form.
    "table_shift": "f446",
    "table_rotate": "f458",
    "queue": "f448",
    "stack": "f44a",
    "block_compare": "f4d8",
}
STATUS = {
    "register_table_search": ("found", "done", "error"),
    "table_compare": ("found", "done", "error"),
    "table_fill": (),
    "table_shift": (),
    "table_rotate": (),
    "queue": ("empty_flag", "full", "error"),
    "stack": ("empty_flag", "full", "error"),
    "block_compare": ("error",),
}
ORDER = {
    "register_table_search": ("value", "source", "length", "pointer"),
    "table_compare": ("source", "destination", "length", "pointer"),
    "table_fill": ("value", "destination", "length"),
    "table_shift": ("input_word", "source", "destination", "length", "output_word"),
    "table_rotate": ("source", "destination", "length"),
    "queue": ("input_word", "destination", "length", "pointer", "output_word"),
    "stack": ("input_word", "destination", "length", "pointer", "output_word"),
    "block_compare": ("input_word", "source", "length", "bit_destination"),
}


def output_bits(start: str, count: int) -> set[str]:
    bit_address(start)
    if start[0] not in "YM":
        raise ValueError("BKCMP codec supports Y/M result bits; S encoding is unresolved")
    end = int(start[1:]) + count - 1
    if count < 1 or end > (255 if start[0] == "Y" else 999):
        raise ValueError("BKCMP result span exceeds Y255/M999 (manual 7-109)")
    return {f"{start[0]}{i}" for i in range(int(start[1:]), end + 1)}


def references(action: "ProcessFunction") -> tuple[set[str], set[str]]:
    assert action.length is not None
    length = action.length
    kind = action.type
    reads: set[str] = set()
    writes: set[str] = set()
    if "input_word" in FIELDS[kind]:
        reads |= register_span(action.operand("input_word"), 1)
    if "source" in FIELDS[kind]:
        reads |= register_span(
            action.operand("source"), length * (2 if kind == "block_compare" else 1)
        )
    if "pointer" in FIELDS[kind]:
        pointer = register_span(action.operand("pointer"), 1, writable=True)
        reads |= pointer
        writes |= pointer
    if "destination" in FIELDS[kind]:
        table = register_span(
            action.operand("destination"), length, writable=kind != "table_compare"
        )
        if kind in {"table_compare", "queue", "stack"}:
            reads |= table
        if kind != "table_compare":
            writes |= table
    if "output_word" in FIELDS[kind]:
        writes |= register_span(action.operand("output_word"), 1, writable=True)
    if kind == "block_compare":
        reads.add("M1975")  # System setting changes wraparound interval semantics.
        writes |= output_bits(action.operand("bit_destination"), length)
    return reads, writes


def compile_operands(action: "ProcessFunction") -> bytes:
    raw = b""
    for field in ORDER[action.type]:
        if field == "length":
            assert action.length is not None
            raw += (action.length - 1).to_bytes(2, "big")
        elif field == "value":
            assert action.value is not None
            raw += (action.value & 0xFFFF).to_bytes(2, "big")
        elif field == "bit_destination":
            raw += bit_address(action.operand(field)).to_bytes(2, "big")
        else:
            raw += encode_register(action.operand(field))
    return raw


def decode_operands(kind: str, tail: bytes) -> tuple[dict[str, object], int]:
    fields: dict[str, object] = {}
    size = 2 * len(ORDER[kind])
    if len(tail) < size:
        raise ValueError("Truncated table function operands")
    for i, field in enumerate(ORDER[kind]):
        raw = tail[2 * i : 2 * i + 2]
        value = int.from_bytes(raw, "big")
        if field == "length":
            fields[field] = value + 1
        elif field == "value":
            fields[field] = int.from_bytes(raw, "big", signed=True)
        elif field == "bit_destination":
            if 0x100 <= value <= 0x1FF:
                fields[field] = f"Y{value - 0x100}"
            elif bit_address("M0") <= value <= bit_address("M999"):
                fields[field] = f"M{value - bit_address('M0')}"
            else:
                raise ValueError("Unencoded BKCMP result family")
        else:
            fields[field] = decode_register(raw)
    return fields, size
