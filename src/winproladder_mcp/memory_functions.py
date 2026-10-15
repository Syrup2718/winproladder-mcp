"""test30 memory codecs; manual 7-137..142 and 7-149..150.

Only sampled bank 1, constant offset 0 and constant lengths are serialized.
File/pack addresses depend on runtime pointers; STAT write footprint depends on
hardware. References conservatively cover the possible destination bank.
"""

import re
from typing import TYPE_CHECKING

from .registers import decode_register, encode_register, register_span

if TYPE_CHECKING:
    from .ir import ProcessFunction

FIELDS = {
    "file_register": ("source", "file_base", "pointer"),
    "memory_pack_write": ("source", "pointer", "work"),
    "memory_pack_read": ("destination", "pointer"),
    "system_status": ("destination",),
}
CONTROLS = {
    "file_register": ("enable", "read_mode", "increment"),
    "memory_pack_write": ("enable", "increment"),
    "memory_pack_read": ("enable", "increment"),
    "system_status": ("enable",),
}
STATUS = {
    "file_register": ("error",),
    "memory_pack_write": ("active", "error", "done"),
    "memory_pack_read": ("error",),
    "system_status": (),
}
CODES = {
    "file_register": "f51e",
    "memory_pack_write": "f35b",
    "memory_pack_read": "f75d",
    "system_status": "f472",
}
LENGTHS = {"file_register": 511, "memory_pack_write": 128, "memory_pack_read": 128}


def check_parameters(a: "ProcessFunction") -> None:
    if a.mode is not None:
        raise ValueError("Memory functions use bank/group fields, not mode")
    if a.pulse != (True if a.type == "memory_pack_write" else None):
        raise ValueError("Encoded forms: 160/162 non-P, 161P, 190")
    if a.type in LENGTHS and (a.length is None or not 1 <= a.length <= LENGTHS[a.type]):
        raise ValueError(f"{a.type}: constant length must be 1..{LENGTHS[a.type]}")
    expected = {
        "bank": 1 if a.type in {"memory_pack_write", "memory_pack_read"} else None,
        "offset": 0 if a.type in {"memory_pack_write", "memory_pack_read"} else None,
        "group": 0 if a.type == "system_status" else None,
    }
    for field, value in expected.items():
        if getattr(a, field) != value:
            raise ValueError(f"{a.type}: only sampled {field}={value} encoding is established")


def operand_check(kind: str, field: str, name: str) -> None:
    if field == "file_base":
        if not re.fullmatch(r"F(0|[1-9][0-9]{0,3})", name) or int(name[1:]) > 8191:
            raise ValueError("File register requires F0..F8191")
        return
    register_span(name, 1, writable=True)
    if (
        kind in {"memory_pack_read", "system_status"}
        and name.startswith("D")
        and int(name[1:]) > 3999
    ):
        raise ValueError("Manual D bank ends at D3999 for FUN162/190")


def references(a: "ProcessFunction") -> tuple[set[str], set[str]]:
    if a.type == "system_status":
        d = a.operand("destination")
        n = int(d[1:])
        end = 4000 if d.startswith("D") else 3840 if n < 3840 else 8072
        return set(), register_span(d, end - n, writable=True)
    assert a.length is not None
    pointer = {a.operand("pointer")}
    writes = pointer if a.increment != "FALSE" else set()
    if a.type == "file_register":
        words = register_span(a.operand("source"), a.length, writable=True)
        files = {f"F{i}" for i in range(8192)}  # Runtime record pointer; not a fixed slice.
        if a.read_mode == "TRUE":
            return pointer | files, writes | words
        if a.read_mode == "FALSE":
            return pointer | words, writes | files
        return pointer | words | files, writes | words | files
    if a.type == "memory_pack_write":
        work = register_span(a.operand("work"), 2, writable=True)
        words = register_span(a.operand("source"), a.length)
        if work & (words | pointer):
            raise ValueError("WR-MP work area overlaps source or pointer")
        return pointer | words | work, writes | work
    words = register_span(a.operand("destination"), a.length, writable=True)
    if any(w.startswith("D") and int(w[1:]) > 3999 for w in words):
        raise ValueError("RD-MP destination span crosses D3999")
    return pointer, writes | words


def compile_operands(a: "ProcessFunction") -> bytes:
    def reg(field: str) -> bytes:
        return encode_register(a.operand(field))

    if a.type == "system_status":
        return reg("destination")
    assert a.length is not None
    length = a.length.to_bytes(2, "big")
    if a.type == "file_register":
        return (
            reg("source")
            + (int(a.operand("file_base")[1:]) * 2).to_bytes(2, "big")
            + reg("pointer")
            + length
        )
    if a.type == "memory_pack_write":
        return reg("source") + bytes(2) + reg("pointer") + length + reg("work")
    return reg("destination") + bytes(2) + reg("pointer") + length


def decode_operands(kind: str, tail: bytes) -> tuple[dict[str, object], int]:
    size = {"system_status": 2, "file_register": 8, "memory_pack_write": 10, "memory_pack_read": 8}[
        kind
    ]
    if len(tail) < size:
        raise ValueError("Truncated memory operands")
    if kind == "system_status":
        return {"group": 0, "destination": decode_register(tail[:2])}, size
    fields: dict[str, object] = {
        "source" if kind != "memory_pack_read" else "destination": decode_register(tail[:2]),
        "pointer": decode_register(tail[4:6]),
        "length": int.from_bytes(tail[6:8], "big"),
    }
    if kind == "file_register":
        n = int.from_bytes(tail[2:4], "big")
        if n % 2:
            raise ValueError("Unaligned file register")
        fields["file_base"] = f"F{n // 2}"
    else:
        if tail[2:4] != bytes(2):
            raise ValueError("Unencoded memory pack offset")
        fields.update(bank=1, offset=0)
        if kind == "memory_pack_write":
            fields.update(pulse=True, work=decode_register(tail[8:10]))
    return fields, size
