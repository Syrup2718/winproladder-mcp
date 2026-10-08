"""FUN76..80 operand helpers; exact special-word anchors remain instruction scoped."""

from .logic import bit_address
from .registers import decode_word, encode_word, register_span, word_references


def bit_span(start: str, count: int, families: str, maximum_start: int = 240) -> set[str]:
    bit_address(start)
    n = int(start[1:])
    maximum = 1896 if start[0] == "M" else maximum_start
    if start[0] not in families or n > maximum or count < 1:
        raise ValueError("Unsupported peripheral start address or span")
    end = n + count - 1
    bit_address(f"{start[0]}{end}")
    return {f"{start[0]}{i}" for i in range(n, end + 1)}


def peripheral_word(name: str, *, writable: bool = False) -> bytes:
    if name == "R3999":
        return bytes.fromhex("023e")
    if name == "V" and not writable:
        return bytes.fromhex("0388")
    return encode_word(name, writable=writable)


def decode_peripheral_word(raw: bytes) -> str:
    if raw == bytes.fromhex("023e"):
        return "R3999"
    if raw == bytes.fromhex("0388"):
        return "V"
    return decode_word(raw)


def peripheral_words(name: str, count: int = 1, *, writable: bool = False) -> set[str]:
    peripheral_word(name, writable=writable)
    if name in {"R3999", "V"}:
        if count != 1:
            raise ValueError("Only the sampled single special word is encoded")
        return {name}
    if count != 1:
        return register_span(name, count, writable=writable)
    return word_references(name)
