"""FUN42..49 sampled 16-bit non-P forms (test25, manual 7-30..37)."""

from typing import TYPE_CHECKING

from .registers import decode_word, encode_word, register_span, word_references

if TYPE_CHECKING:
    from .ir import ProcessFunction

INDEX_MAX = {"bit_move": 15, "nibble_move": 3, "byte_move": 1}
FIELDS = {
    **{k: ("source", "destination") for k in INDEX_MAX},
    "word_exchange": ("source", "destination"),
    "byte_swap": ("destination",),
    "nibble_unite": ("source", "destination"),
    "nibble_distribute": ("source", "destination"),
    "byte_unite": ("source", "destination", "length_register"),
}
CONTROLS = {k: ("enable",) for k in FIELDS}
CODES = dict(
    zip(FIELDS, ("f4b0", "f4b2", "f4b4", "f4b6", "f4b8", "f5bc", "f6bd", "f477"), strict=True)
)
STATUS = {
    k: (() if k in {"word_exchange", "byte_swap", "byte_unite"} else ("error",)) for k in FIELDS
}
ORDER = {
    **{k: ("source", "destination", "source_index", "destination_index") for k in INDEX_MAX},
    "word_exchange": FIELDS["word_exchange"],
    "byte_swap": FIELDS["byte_swap"],
    "nibble_unite": ("count", "source", "destination"),
    "nibble_distribute": ("source", "count", "destination"),
    "byte_unite": ("length_register", "source", "destination"),
}


def check_parameters(action: "ProcessFunction") -> None:
    for field in ("source_index", "destination_index"):
        value = getattr(action, field)
        if action.type in INDEX_MAX:
            if value is None or not 0 <= value <= INDEX_MAX[action.type]:
                raise ValueError(f"{action.type} {field} requires 0..{INDEX_MAX[action.type]}")
        elif value is not None:
            raise ValueError(f"{action.type} has no {field}")
    if action.type in {"nibble_unite", "nibble_distribute"}:
        if action.count is None or not 1 <= action.count <= 4:
            raise ValueError("UNIT/DIST count requires constant 1..4 (manual 7-35..36)")
    elif action.count is not None:
        raise ValueError(f"{action.type} has no constant count form")


def operand_check(kind: str, field: str, name: str) -> None:
    if kind == "byte_unite":
        # All three operands are HR/ROR/DR, even the source and length register.
        register_span(name, 1, writable=True)
    else:
        encode_word(name, writable=field == "destination" or kind == "word_exchange")


def span(name: str, count: int, *, writable: bool = False) -> set[str]:
    if name.startswith(("R", "D")):
        return register_span(name, count, writable=writable)
    encode_word(name, writable=writable)
    if count == 1:
        return word_references(name)
    # A T/WX/WY base codec does not establish how a multiword bank progresses.
    raise ValueError("Multiword packing spans currently require R/D; other bank spans unresolved")


def references(action: "ProcessFunction") -> tuple[set[str], set[str]]:
    kind = action.type
    if kind == "byte_unite":
        # N is runtime data, not an address-sized constant. Track maximum legal footprint.
        reads = register_span(action.operand("source"), 256)
        reads |= register_span(action.operand("length_register"), 1)
        writes = register_span(action.operand("destination"), 128, writable=True)
        # Odd N's unused final byte is unspecified in this manual: conservatively read it.
        return reads | writes, writes
    source_count = action.count if kind == "nibble_unite" else 1
    dest_count = action.count if kind == "nibble_distribute" else 1
    assert source_count is not None and dest_count is not None
    reads = span(action.operand("source"), source_count) if "source" in FIELDS[kind] else set()
    writes = span(action.operand("destination"), dest_count, writable=True)
    if kind in INDEX_MAX or kind in {"word_exchange", "byte_swap"}:
        reads |= writes  # Preserve unselected bits / read-modify-write / exchange both words.
    if kind == "word_exchange":
        writes |= span(action.operand("source"), 1, writable=True)
    return reads, writes


def compile_operands(action: "ProcessFunction") -> bytes:
    raw = b""
    for field in ORDER[action.type]:
        if field in {"source_index", "destination_index", "count"}:
            value = getattr(action, field)
            assert isinstance(value, int)
            raw += value.to_bytes(2, "big")
        else:
            raw += encode_word(action.operand(field))
    return raw


def decode_operands(kind: str, tail: bytes) -> tuple[dict[str, object], int]:
    size = 2 * len(ORDER[kind])
    if len(tail) < size:
        raise ValueError("Truncated packing operands")
    fields: dict[str, object] = {}
    for i, field in enumerate(ORDER[kind]):
        raw = tail[2 * i : 2 * i + 2]
        fields[field] = (
            int.from_bytes(raw, "big")
            if field in {"source_index", "destination_index", "count"}
            else decode_word(raw)
        )
    return fields, size
