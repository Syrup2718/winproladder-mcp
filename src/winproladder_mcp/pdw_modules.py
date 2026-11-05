"""PDW expansion-module records: names and order only, opaque parameters retained.

Never bundle private exports or synthesize initialization bytes for an unseen SKU.
The observed zero trailer is not a claim of a generally solved module checksum.
"""

import re
from dataclasses import dataclass

ENTRY_SIZE = 76
MAX_ENTRIES = 256  # Serialization guard, not PLC slot or expansion-capacity advice.


@dataclass(frozen=True)
class Module:
    name: str
    raw: bytes


def parse_modules(payload: bytes) -> tuple[Module, ...]:
    if len(payload) % ENTRY_SIZE:
        raise ValueError("Unsupported PDW module record size; expected 76-byte entries")
    if len(payload) // ENTRY_SIZE > MAX_ENTRIES:
        raise ValueError("PDW module count exceeds implementation limit (not PLC capacity)")
    result = []
    for offset in range(0, len(payload), ENTRY_SIZE):
        raw = payload[offset : offset + ENTRY_SIZE]
        name_field = raw[:16]
        name, separator, padding = name_field.partition(b"\0")
        if not separator or any(padding) or not re.fullmatch(rb"FBs-[A-Za-z0-9-]+", name):
            raise ValueError("Unsupported PDW module name field")
        result.append(Module(name.decode("ascii"), raw))
    return tuple(result)


def select_modules(payloads: list[bytes], order: list[str]) -> bytes:
    """Copy exact, unambiguous local records; preserve requested duplicates and order."""
    if len(order) > MAX_ENTRIES:
        raise ValueError("PDW module count exceeds implementation limit (not PLC capacity)")
    catalog: dict[str, set[bytes]] = {}
    for payload in payloads:
        for module in parse_modules(payload):
            catalog.setdefault(module.name, set()).add(module.raw)
    result = []
    for name in order:
        entries = catalog.get(name)
        if not entries:
            raise ValueError(
                f"Module {name!r} has no supplied local record; cannot invent parameters"
            )
        if len(entries) != 1:
            raise ValueError(f"Module {name!r} has conflicting local parameter records")
        result.append(next(iter(entries)))
    return b"".join(result)
