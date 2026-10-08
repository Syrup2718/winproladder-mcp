"""Floating word banks and IEEE-754 immediates, evidenced by test11/test12."""

import math
import re
import struct


def float_bank(name: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"[RD](0|[1-9][0-9]{0,3})", name):
        raise ValueError("Use a direct R/D floating register")
    n = int(name[1:])
    if name[0] == "R" and n <= 3839:
        return n, 0, 3839
    if name[0] == "R" and 5000 <= n <= 8071:
        return n, 5000, 8071
    if name[0] == "D" and n <= 4095:
        return n, 0, 4095
    raise ValueError("Float banks: R0..3839, R5000..8071, D0..4095")


def float_span(name: str, count: int) -> set[str]:
    n, _, high = float_bank(name)
    if count < 1 or n + count - 1 > high:
        raise ValueError("Floating register span crosses a bank boundary")
    return {f"{name[0]}{i}" for i in range(n, n + count)}


def encode_float_register(name: str) -> bytes:
    n, low, _ = float_bank(name)
    v = (
        0x4000 + 2 * n
        if name[0] == "D"
        else 0x2800 + 2 * (n - 5000)
        if low == 5000
        else 0xA00 + 2 * n
    )
    return v.to_bytes(2, "big")


def decode_float_register(raw: bytes) -> str:
    v = int.from_bytes(raw, "big")
    if len(raw) != 2 or v % 2:
        raise ValueError("Unaligned floating register")
    if 0xA00 <= v <= 0x27FE:
        return f"R{(v - 0xA00) // 2}"
    if 0x2800 <= v <= 0x3FFE:
        return f"R{5000 + (v - 0x2800) // 2}"
    if 0x4000 <= v <= 0x5FFE:
        return f"D{(v - 0x4000) // 2}"
    raise ValueError("Unknown floating register bank")


def encode_float_source(value: str | float) -> bytes:
    if isinstance(value, str):
        float_span(value, 2)
        return b"\x00\x00" + encode_float_register(value)
    if not math.isfinite(value):
        raise ValueError("Floating constants must be finite")
    try:
        return struct.pack(">f", value)
    except (OverflowError, struct.error) as error:
        raise ValueError("Floating constant exceeds IEEE-754 binary32") from error


def decode_float_source(raw: bytes, constant: bool) -> str | float:
    if len(raw) != 4:
        raise ValueError("Float source requires four bytes")
    if constant:
        value = float(struct.unpack(">f", raw)[0])
        encode_float_source(value)
        return value
    if raw[:2] != b"\x00\x00":
        raise ValueError("Unknown register-source prefix")
    value_reg = decode_float_register(raw[2:])
    float_span(value_reg, 2)
    return value_reg


def float_source_reads(value: str | float) -> set[str]:
    return float_span(value, 2) if isinstance(value, str) else set()


def normalize_float_source(value: str | float) -> str | float:
    if isinstance(value, str):
        return value
    return decode_float_source(encode_float_source(value), True)
