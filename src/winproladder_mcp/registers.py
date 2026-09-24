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
