"""Experimental variable-length PDW container, grounded in local GUI exports.

Project metadata is not executable PLC logic. Unknown instructions are inspectable
as bytes, never silently copied into a newly compiled program. No private templates
or masks are included in this module.
"""

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool

from .component_comments import ComponentComment
from .ldr import FOOTER, MAX_SIZE
from .logic import bit_address
from .pdw import MAGIC, PERIOD, SIZE, START, TAIL_START
from .pdw_modules import parse_modules

MAX_PROGRAM = 4094  # Keep the mask-recovery region outside compiled code.
SECOND_START, SECOND_SIZE = 0xA126, 0x6100
MODEL_PROFILES = {
    "FBs-20MC": "FBs-20MC",
    "FBs-32MC": "FBs-32MC-test30",
    "FBs-40MC": "FBs-40MC-test27",
    "FBs-60MC": "FBs-60MC-test16",
}


def word_sum(data: bytes | bytearray) -> int:
    if len(data) % 2:
        raise ValueError("PDW word data must have even byte length")
    return sum(int.from_bytes(data[i : i + 2], "little") for i in range(0, len(data), 2)) & 65535


def text_bytes(text: str) -> bytes:
    if any(ord(c) < 32 and c not in "\r\n" for c in text) or "\x7f" in text:
        raise ValueError("PDW text allows CR/LF but no other control characters")
    try:
        data = text.encode("cp950", errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError("PDW text must be representable in CP950/Big5") from error
    if len(data) > 4096:
        raise ValueError("PDW text exceeds 4096 encoded bytes")
    return data


def signed_sum(data: bytes) -> int:
    return sum(x if x < 128 else x - 256 for x in data)


class PdwSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    network_index: int = Field(strict=True, ge=0, le=999)
    name: str = Field(min_length=1, max_length=100)
    comment: str = Field(default="", max_length=2000)
    embed_comment: StrictBool = False


@dataclass(frozen=True)
class Record:
    tag: int
    payload: bytes
    checksum: bytes

    def encode(self) -> bytes:
        return (
            self.tag.to_bytes(2, "little")
            + len(self.payload).to_bytes(2, "little")
            + self.payload
            + self.checksum
        )


def fields(payload: bytes, count: int) -> list[bytes]:
    result = []
    pos = 0
    for _ in range(count):
        if pos + 2 > len(payload):
            raise ValueError("Truncated PDW text field")
        length = int.from_bytes(payload[pos : pos + 2], "little")
        pos += 2
        if pos + length > len(payload):
            raise ValueError("Truncated PDW text")
        data = payload[pos : pos + length]
        data.decode("cp950", errors="strict")
        result.append(data)
        pos += length
    if pos != len(payload):
        raise ValueError("Unexpected bytes after PDW text fields")
    return result


def record_checksum(tag: int, payload: bytes) -> int | None:
    if tag == 0x1001:
        if len(payload) < 6:
            raise ValueError("Truncated PDW unit")
        a = int.from_bytes(payload[2:4], "little")
        b = int.from_bytes(payload[4:6], "little")
        if len(payload) != 6 + a + b:
            raise ValueError("PDW unit text lengths mismatch")
        payload[6 : 6 + a].decode("cp950", errors="strict")
        payload[6 + a :].decode("cp950", errors="strict")
        return (sum(payload[:6]) + signed_sum(payload[6:])) & 65535
    if tag == 0x1002:
        if len(payload) < 4 or int.from_bytes(payload[2:4], "little") != len(payload) - 4:
            raise ValueError("PDW network comment length mismatch")
        payload[4:].decode("cp950", errors="strict")
        return (sum(payload[:4]) + signed_sum(payload[4:])) & 65535
    if tag == 0x1003:
        chunks = fields(payload, 3)
        return sum(sum(len(x).to_bytes(2, "little")) + signed_sum(x) for x in chunks) & 65535
    return None


def record(tag: int, payload: bytes) -> Record:
    checksum = record_checksum(tag, payload)
    if checksum is None:
        raise ValueError("Cannot synthesize unknown PDW record")
    return Record(tag, payload, checksum.to_bytes(2, "little"))


def unit(address: int, name: str, comment: str = "") -> Record:
    a, b = text_bytes(name), text_bytes(comment)
    return record(
        0x1001,
        address.to_bytes(2, "little")
        + len(a).to_bytes(2, "little")
        + len(b).to_bytes(2, "little")
        + a
        + b,
    )


def xor(data: bytes, mask: bytes) -> bytes:
    return bytes(x ^ mask[i % PERIOD] for i, x in enumerate(data))


@dataclass(frozen=True)
class Project:
    raw: bytes
    plain: bytes
    secondary: bytes
    mask: bytes
    secondary_mask: bytes
    records: tuple[Record, ...]

    @property
    def model(self) -> str:
        return self.raw[160:176].rstrip(b"\0").decode("ascii")

    @property
    def module_payload(self) -> bytes:
        entries = [r for r in self.records if r.tag == 0x1040]
        if len(entries) != 1:
            raise ValueError("PDW requires exactly one module-table record")
        if entries[0].checksum != b"\0\0":
            raise ValueError("Unsupported PDW module-table trailer; no checksum rule inferred")
        return entries[0].payload

    @property
    def program(self) -> bytes:
        count = int.from_bytes(self.plain[0x106:0x108], "little")
        return self.plain[0x200 : 0x200 + count * 2]

    def describe(self) -> dict[str, Any]:
        units = []
        notes = []
        components = []
        for r in self.records:
            if r.tag == 0x1001:
                n = int.from_bytes(r.payload[2:4], "little")
                units.append(
                    {
                        "address": int.from_bytes(r.payload[:2], "little"),
                        "name": r.payload[6 : 6 + n].decode("cp950"),
                        "comment": r.payload[6 + n :].decode("cp950"),
                    }
                )
            elif r.tag == 0x1002:
                notes.append(
                    {
                        "address": int.from_bytes(r.payload[:2], "little"),
                        "comment": r.payload[4:].decode("cp950"),
                    }
                )
            elif r.tag == 0x1003:
                a, b, c = fields(r.payload, 3)
                components.append(
                    {
                        "ref": a.decode("ascii"),
                        "comment": b.decode("cp950"),
                        "description": c.decode("cp950"),
                    }
                )
        markers = []
        for i in range(0, len(self.program) - 3, 2):
            if self.program[i : i + 2] == b"\xf6\x7f":
                markers.append(0x200 + i)
        return {
            "model": self.model,
            "modules": [
                {"index": i, "name": m.name}
                for i, m in enumerate(parse_modules(self.module_payload))
            ],
            "module_parameters": "opaque bytes retained; no I/O mapping or compatibility claim",
            "program_bytes": len(self.program),
            "units": units,
            "network_comments": notes,
            "component_comments": components,
            "func199_candidate_addresses": markers,
            "instruction_analysis": "not a complete instruction decoder; FUNC199 opaque",
            "integrity": {
                "program_checksum": True,
                "header_checksum": True,
                "text_record_checksums": True,
                "all_opaque_fields": "not verified",
            },
        }


def parse(raw: bytes) -> Project:
    if len(raw) > MAX_SIZE or len(raw) < TAIL_START + 6 or not raw.startswith(MAGIC):
        raise ValueError("Unsupported or truncated PDW container")
    if raw[160:176].rstrip(b"\0").decode("ascii", errors="replace") not in MODEL_PROFILES:
        raise ValueError("PDW model is outside the sampled 20MC/32MC/40MC/60MC layouts")
    if raw[START - 4 : START] != bytes.fromhex("0a1800a0") or raw[
        0xA122:SECOND_START
    ] != bytes.fromhex("0b180061"):
        raise ValueError("Unsupported PDW memory block framing")
    encoded = raw[START : START + SIZE]
    mask = bytes(x ^ 255 for x in encoded[4 * PERIOD : 5 * PERIOD])
    plain = xor(encoded, mask)
    other = raw[SECOND_START : SECOND_START + SECOND_SIZE]
    other_mask = bytes(x ^ 255 for x in other[4 * PERIOD : 5 * PERIOD])
    secondary = xor(other, other_mask)
    if plain[:8] != b"FBS40003":
        raise ValueError("PDW mask recovery failed")
    count = int.from_bytes(plain[0x106:0x108], "little")
    length = count * 2
    end = 0x200 + length
    if length > MAX_PROGRAM or plain[end:] != b"\xff" * (SIZE - end):
        raise ValueError("Unsupported PDW program length, padding or mask")
    if int.from_bytes(plain[0xC8:0xCA], "little") != (word_sum(plain[0x100:0x200]) - 24) & 65535:
        raise ValueError("PDW header checksum mismatch")
    if int.from_bytes(plain[0xCA:0xCC], "little") != (word_sum(plain[0x200:end]) - 1) & 65535:
        raise ValueError("PDW program checksum mismatch")
    if (
        int.from_bytes(plain[0x108:0x10A], "little") != 0x4EFF - count
        or plain[0x10C:0x110] != (end + 2).to_bytes(2, "little") * 2
    ):
        raise ValueError("PDW program length metadata mismatch")
    records = []
    pos = TAIL_START
    while raw[pos : pos + 6] != FOOTER:
        if pos + 6 > len(raw):
            raise ValueError("Missing PDW footer")
        tag = int.from_bytes(raw[pos : pos + 2], "little")
        size = int.from_bytes(raw[pos + 2 : pos + 4], "little")
        stop = pos + size + 6
        if stop > len(raw):
            raise ValueError("Truncated PDW record")
        payload = raw[pos + 4 : stop - 2]
        checksum = record_checksum(tag, payload)
        if checksum is not None and checksum != int.from_bytes(raw[stop - 2 : stop], "little"):
            raise ValueError("PDW text record checksum mismatch")
        records.append(Record(tag, payload, raw[stop - 2 : stop]))
        pos = stop
    if pos + 6 != len(raw):
        raise ValueError("Unexpected bytes after PDW footer")
    units = [int.from_bytes(r.payload[:2], "little") for r in records if r.tag == 0x1001]
    if (
        not units
        or units[0] != 0x200
        or units[-1] != end + 2
        or units != sorted(set(units))
        or any(a % 2 or not 0x200 <= a <= end + 2 for a in units)
    ):
        raise ValueError("PDW unit addresses inconsistent with program extent")
    for r in records:
        if r.tag == 0x1002:
            address = int.from_bytes(r.payload[:2], "little")
            if address % 2 or not 0x200 <= address < end:
                raise ValueError("PDW network comment address outside program")
    # Duplicate component names in PLC memory must agree with the project table.
    pointer = int.from_bytes(plain[0x11E:0x120], "little") - 0xA000
    if not 0 <= pointer <= 0x5FFE or secondary[0x5FFE:0x6000] != b"\0\xff":
        raise ValueError("PDW component-name memory pointer invalid")
    if secondary[:pointer] != b"\xff" * pointer:
        raise ValueError("PDW secondary data outside supported component-name area")
    pos = pointer
    memory_names = {}
    while pos < 0x5FFE:
        if secondary[pos] != 0 or pos + 3 > 0x5FFE:
            raise ValueError("Malformed PDW component-name memory")
        address = int.from_bytes(secondary[pos + 1 : pos + 3], "little")
        stop = secondary.find(b"\0", pos + 3, 0x5FFF)
        if stop < 0 or address in memory_names:
            raise ValueError("Malformed or duplicate PDW component name")
        memory_names[address] = secondary[pos + 3 : stop]
        pos = stop
    table_names = {}
    table_refs = set()
    for r in records:
        if r.tag == 0x1003:
            ref, name, _ = fields(r.payload, 3)
            address = bit_address(ref.decode("ascii"))
            if address in table_refs:
                raise ValueError("Duplicate PDW component REF")
            table_refs.add(address)
            if name:
                table_names[address] = name
    if table_names != memory_names:
        raise ValueError("PDW duplicate component-name representations disagree")
    project = Project(raw, plain, secondary, mask, other_mask, tuple(records))
    parse_modules(project.module_payload)
    return project


def build(
    template: bytes,
    payloads: list[bytes],
    sections: list[PdwSection],
    notes: list[str],
    comments: list[ComponentComment],
    module_payload: bytes | None = None,
) -> tuple[bytes, list[int]]:
    project = parse(template)
    if not payloads or len(notes) != len(payloads):
        raise ValueError("PDW needs compiled networks and matching network comments")
    if not sections or sections[0].network_index != 0:
        raise ValueError("PDW sections must begin at network zero")
    indexes = [s.network_index for s in sections]
    if indexes != sorted(set(indexes)) or indexes[-1] >= len(payloads):
        raise ValueError("PDW section indexes must be distinct, ordered and inside program")
    names = [s.name for s in sections]
    if len(names) != len(set(names)):
        raise ValueError("PDW section names must be unique")
    if project.plain[0x112:0x116] != bytes.fromhex("ffa700a8"):
        raise ValueError("Cannot replace a template containing subprogram memory")
    if any(r.tag not in {0x1001, 0x1002, 0x1003, 0x1050, 0x1040, 0x1042} for r in project.records):
        raise ValueError("Cannot generate from a template with unknown record types")
    opaque = [r for r in project.records if r.tag not in {0x1001, 0x1002, 0x1003}]
    if (
        len(opaque) != 3
        or opaque[0].tag != 0x1050
        or len(opaque[0].payload) != 32528
        or opaque[1].tag != 0x1040
        or opaque[2].tag != 0x1042
        or len(opaque[2].payload) != 188
    ):
        raise ValueError("Unsupported PDW settings records")
    if module_payload is not None:
        parse_modules(module_payload)
        opaque[1] = Record(0x1040, module_payload, opaque[1].checksum)
    section_map = {s.network_index: s for s in sections}
    program = b""
    units = []
    network_notes = []
    offsets = []
    for i, payload in enumerate(payloads):
        if i in section_map:
            s = section_map[i]
            units.append(unit(0x200 + len(program), s.name, s.comment))
            if s.embed_comment:
                text = text_bytes(f"SECT:{s.name}:{s.comment}")
                if not text or len(text) % 2 or len(text) > 510:
                    raise ValueError(
                        "Sampled SECT encoding requires even CP950 length, at most 510"
                    )
                program += b"\xf0\x7f" + bytes((len(text) // 2, 0x2D)) + text
        address = 0x200 + len(program)
        offsets.append(address)
        if notes[i]:
            text = text_bytes(notes[i])
            network_notes.append(
                record(
                    0x1002, address.to_bytes(2, "little") + len(text).to_bytes(2, "little") + text
                )
            )
        program += payload
    if len(program) > MAX_PROGRAM or len(program) % 2:
        raise ValueError("PDW compiled program exceeds supported mask-safe extent")
    end = 0x200 + len(program) + 2
    old_units = [r for r in project.records if r.tag == 0x1001]
    last = old_units[-1].payload
    name_size = int.from_bytes(last[2:4], "little")
    sub_name = last[6 : 6 + name_size].decode("cp950")
    if sub_name in names:
        raise ValueError("Main section name conflicts with preserved empty subprogram name")
    units.append(unit(end, sub_name))
    component_records = []
    blob = b""
    refs = set()
    for c in comments:
        address = bit_address(c.ref)
        if address in refs:
            raise ValueError("Duplicate PDW component REF")
        refs.add(address)
        name, description = text_bytes(c.comment), text_bytes(c.description)
        if name:
            blob = b"\0" + address.to_bytes(2, "little") + name + blob
        chunks = [c.ref.encode("ascii"), name, description]
        component_records.append(
            record(0x1003, b"".join(len(x).to_bytes(2, "little") + x for x in chunks))
        )
    if len(blob) > 0x5FFE:
        raise ValueError("PDW component names exceed memory area")
    plain = bytearray(project.plain)
    plain[0x100:0x102] = b"\x40\0"
    count = len(program) // 2
    plain[0x106:0x10A] = count.to_bytes(2, "little") + (0x4EFF - count).to_bytes(2, "little")
    plain[0x10C:0x110] = end.to_bytes(2, "little") * 2
    plain[0x11E:0x120] = (0xFFFE - len(blob)).to_bytes(2, "little")
    plain[0x200:] = program + b"\xff" * (SIZE - 0x200 - len(program))
    plain[0xCA:0xCC] = ((word_sum(program) - 1) & 65535).to_bytes(2, "little")
    plain[0xC8:0xCA] = ((word_sum(plain[0x100:0x200]) - 24) & 65535).to_bytes(2, "little")
    secondary = bytearray(project.secondary)
    secondary[:0x6000] = b"\xff" * (0x5FFE - len(blob)) + blob + b"\0\xff"
    records = units + network_notes + [opaque[0]] + component_records + opaque[1:]
    raw = bytearray(template[:TAIL_START])
    raw[START : START + SIZE] = xor(bytes(plain), project.mask)
    raw[SECOND_START : SECOND_START + SECOND_SIZE] = xor(bytes(secondary), project.secondary_mask)
    result = bytes(raw) + b"".join(r.encode() for r in records) + FOOTER
    emitted = parse(result)
    for offset, payload in zip(offsets, payloads, strict=True):
        if emitted.plain[offset : offset + len(payload)] != payload:
            raise ValueError("PDW emitted program differs from compiled networks")
    return result, offsets
