"""Direct word operands inferred from test5/test6, not from FUN numbers."""

import re


def register_bank(name: str) -> tuple[int, int, int]:
    """Return numeric address and inclusive bank bounds for supported R/D words."""
    if not re.fullmatch(r"[RD](0|[1-9][0-9]{0,3})", name):
        raise ValueError("Use canonical direct R/D register names; no indirect operands")
    address = int(name[1:])
    if name[0] == "R" and address <= 3839:
        return address, 0, 3839
    if name[0] == "R" and address <= 3903:
        return address, 3840, 3903
    if name[0] == "D" and address <= 3999:
        return address, 0, 3999
    raise ValueError("Supported inferred banks: R0..3839, R3840..3903, D0..3999")


def register_span(name: str, count: int, *, writable: bool = False) -> set[str]:
    address, low, high = register_bank(name)
    if count < 1 or address + count - 1 > high:
        raise ValueError(f"Register span {name}+{count} crosses a supported bank boundary")
    if writable and name.startswith("R") and low == 3840:
        raise ValueError("R3840..R3903 is an input register bank, not a writable destination")
    return {f"{name[0]}{i}" for i in range(address, address + count)}


def encode_register(name: str) -> bytes:
    address, low, _ = register_bank(name)
    if name[0] == "D":
        value = 0x4000 + 2 * address
    elif low == 3840:
        value = 0x100 + 2 * (address - 3840)
    else:
        value = 0xA00 + 2 * address
    return value.to_bytes(2, "big")


def decode_register(raw: bytes) -> str:
    if len(raw) != 2:
        raise ValueError("Word operand must contain two bytes")
    value = int.from_bytes(raw, "big")
    if value % 2:
        raise ValueError("Unaligned word operand")
    if 0x100 <= value <= 0x17E:
        return f"R{3840 + (value - 0x100) // 2}"
    if 0xA00 <= value <= 0x27FE:
        return f"R{(value - 0xA00) // 2}"
    if 0x4000 <= value <= 0x5F3E:
        return f"D{(value - 0x4000) // 2}"
    raise ValueError("Unknown direct-register bank")


# Deliberately separate from legacy R/D operands: these banks are established by test10.
def encode_word(name: str, *, writable: bool = False) -> bytes:
    if name in {"WX0", "WY0"}:
        if writable and name == "WX0":
            raise ValueError("WX0 is input-only")
        return bytes.fromhex("0800" if name == "WX0" else "0820")
    if re.fullmatch(r"T(0|[1-9][0-9]{0,2})", name) and int(name[1:]) <= 255:
        if writable:
            raise ValueError("Timer word destinations are not supported")
        return (0x390 + 2 * int(name[1:])).to_bytes(2, "big")
    register_span(name, 1, writable=writable)
    return encode_register(name)


def decode_word(raw: bytes) -> str:
    if raw == bytes.fromhex("0800"):
        return "WX0"
    if raw == bytes.fromhex("0820"):
        return "WY0"
    value = int.from_bytes(raw, "big")
    if len(raw) == 2 and 0x390 <= value <= 0x58E and value % 2 == 0:
        return f"T{(value - 0x390) // 2}"
    return decode_register(raw)


def word_references(name: str) -> set[str]:
    encode_word(name)
    if name in {"WX0", "WY0"}:
        return {name} | {f"{name[1]}{i}" for i in range(16)}
    return {name}


# Comparison-only operands: exact test11 addresses, not a guessed global bank mapping.
COMPARISON_WORDS = {
    "WS0": bytes.fromhex("0885"),
    "WM0": bytes.fromhex("0902"),
    "C2": bytes.fromhex("0594"),
    "R5111": bytes.fromhex("28de"),
}


def encode_comparison_word(name: str) -> bytes:
    return COMPARISON_WORDS[name] if name in COMPARISON_WORDS else encode_word(name)


def decode_comparison_word(raw: bytes) -> str:
    for name, encoded in COMPARISON_WORDS.items():
        if raw == encoded:
            return name
    return decode_word(raw)


def comparison_word_references(name: str) -> set[str]:
    encode_comparison_word(name)
    if name in {"WM0", "WS0"}:
        return {name} | {f"{name[1]}{i}" for i in range(16)}
    if name in COMPARISON_WORDS:
        return {name}
    return word_references(name)
