"""Sample-bound FBs-60MC project editing, not a general PDW serializer.

Only equal-length replacement of one/two independent X -> Y rungs is supported.
Templates, masks and private project data are supplied locally, never bundled.
"""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictBool

from .ir import Coil, Ladder, Network
from .ldr import FOOTER, MAX_SIZE

MAGIC = b"Fatek WinProladder, File Format 1"
START, SIZE, PERIOD = 0x122, 0xA000, 1280
TAIL_START = 0x10228


class PdwRung(BaseModel):
    """Deliberately restricted to addresses covered by the current GUI evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    input: Literal["X0", "X1"]
    output: Literal["Y0", "Y1", "Y2"]
    normally_closed: StrictBool = False

    def encode(self) -> bytes:
        return bytes(
            (
                0x50 if self.normally_closed else 0x40,
                int(self.input[1:]),
                0xC1,
                int(self.output[1:]),
            )
        )


def as_ladder(rungs: list[PdwRung]) -> Ladder:
    return Ladder(
        profile="FBs-60MC-test16",
        networks=[
            Network(
                condition=("NOT " if r.normally_closed else "") + r.input,
                coils=[Coil(address=int(r.output[1:]))],
            )
            for r in rungs
        ],
    )


def decode_rungs(program: bytes) -> list[PdwRung]:
    rungs = []
    if len(program) not in (4, 8):
        raise ValueError("PDW supports one or two direct-contact rungs only")
    for i in range(0, len(program), 4):
        op, x, coil, y = program[i : i + 4]
        if op not in (0x40, 0x50) or coil != 0xC1:
            raise ValueError("Unsupported PDW instruction; only direct X -> Y is supported")
        rungs.append(
            PdwRung.model_validate(
                {"input": f"X{x}", "output": f"Y{y}", "normally_closed": op == 0x50}
            )
        )
    return rungs


def _xor(data: bytes, mask: bytes) -> bytes:
    return bytes(x ^ mask[i % PERIOD] for i, x in enumerate(data))


@dataclass(frozen=True)
class Project:
    raw: bytes
    plain: bytes
    mask: bytes
    rungs: tuple[PdwRung, ...]


def parse(data: bytes) -> Project:
    """Reject unsupported topology/layout before changing any bytes.

    Mask recovery assumes FF padding, checked over multiple independent periods.
    Unknown metadata is retained; this is not a full-file integrity validator.
    """
    if not TAIL_START + 6 <= len(data) <= MAX_SIZE or not data.startswith(MAGIC):
        raise ValueError("Unsupported or truncated PDW header")
    if data[160:176].rstrip(b"\0") != b"FBs-60MC":
        raise ValueError("PDW supports the sampled FBs-60MC layout only")
    if data[START - 4 : START] != bytes.fromhex("0a1800a0"):
        raise ValueError("Unsupported PDW program block layout")
    if data[0xA122:0xA126] != bytes.fromhex("0b180061"):
        raise ValueError("Unsupported PDW secondary block layout")
    encoded = data[START : START + SIZE]
    mask = bytes(x ^ 255 for x in encoded[4 * PERIOD : 5 * PERIOD])
    plain = _xor(encoded, mask)
    if plain[:8] != b"FBS40003":
        raise ValueError("PDW mask/header recovery failed")
    count_words = int.from_bytes(plain[0x106:0x108], "little")
    if count_words not in (2, 4):
        raise ValueError("PDW template must contain one or two nonempty rungs")
    program_end = 0x200 + count_words * 2
    rungs = decode_rungs(plain[0x200:program_end])
    checksum = (1 if len(rungs) == 1 else 0x102) + sum(
        (0x1000 if r.normally_closed else 0) + int(r.input[1:]) + int(r.output[1:]) for r in rungs
    )
    if int.from_bytes(plain[0xCA:0xCC], "big") != checksum or plain[0xC8:0xCA] != (
        b"\x28\xff" if len(rungs) == 1 else b"\x30\xff"
    ):
        raise ValueError("PDW sampled program checksum/metadata mismatch")
    if plain[program_end:] != b"\xff" * (SIZE - program_end):
        raise ValueError("PDW template contains extra program data or inconsistent padding")
    if (
        plain[0x100:0x106] != bytes.fromhex("40004000004f")
        or plain[0x108:0x10A] != bytes((255 - count_words, 0x4E))
        or plain[0x10A:0x110] != b"\x00\x02" + (0x202 + count_words * 2).to_bytes(2, "little") * 2
        or plain[0x11E:0x120] != b"\xfe\xff"
    ):
        raise ValueError("Unsupported PDW program metadata or embedded annotations")
    # Secondary memory may duplicate comments; do not silently retain stale text.
    other = data[0xA126 : 0xA126 + 0x6100]
    other_mask = bytes(x ^ 255 for x in other[4 * PERIOD : 5 * PERIOD])
    secondary = _xor(other, other_mask)
    if secondary[:0x6000] != b"\xff" * 0x5FFE + b"\x00\xff":
        raise ValueError("PDW templates with secondary memory data/comments are unsupported")
    offset = TAIL_START
    tags = []
    sizes = []
    while data[offset : offset + 6] != FOOTER:
        if offset + 6 > len(data):
            raise ValueError("Missing PDW footer")
        tag = int.from_bytes(data[offset : offset + 2], "little")
        size = int.from_bytes(data[offset + 2 : offset + 4], "little")
        end = offset + size + 6
        if end > len(data):
            raise ValueError("Truncated PDW tail record")
        tags.append(tag)
        sizes.append(size)
        offset = end
    if offset + 6 != len(data) or tags != [0x1001, 0x1001, 0x1050, 0x1040, 0x1042]:
        raise ValueError("Unsupported PDW tail records, annotations or trailing data")
    if sizes != [14, 14, 32528, 0, 188]:
        raise ValueError("Unsupported PDW tail record sizes")
    return Project(data, plain, mask, tuple(rungs))


def replace_rungs(template: bytes, rungs: list[PdwRung]) -> bytes:
    project = parse(template)
    if len(rungs) != len(project.rungs):
        raise ValueError("PDW rung count must match the template; topology changes unsupported")
    program = b"".join(r.encode() for r in rungs)
    end = 0x200 + len(program)
    old = project.plain[0x200:end]
    # Observed equal-length word delta, not a general checksum for resizing a project.
    delta = sum(
        int.from_bytes(program[i : i + 2], "big") - int.from_bytes(old[i : i + 2], "big")
        for i in range(0, len(program), 2)
    )
    plain = bytearray(project.plain)
    checksum = int.from_bytes(plain[0xCA:0xCC], "big")
    plain[0xCA:0xCC] = ((checksum + delta) & 65535).to_bytes(2, "big")
    plain[0x200:end] = program
    result = template[:START] + _xor(bytes(plain), project.mask) + template[START + SIZE :]
    emitted = parse(result)
    if list(emitted.rungs) != rungs:
        raise ValueError("PDW emitted-byte verification failed")
    return result


def capabilities() -> dict[str, object]:
    return {
        "status": "experimental_sample_bound",
        "model": "FBs-60MC",
        "template_required": True,
        "rung_count": "one or two, must match template",
        "inputs": ["X0", "X1"],
        "outputs": ["Y0", "Y1", "Y2"],
        "contacts": ["normally_open", "normally_closed"],
        "unsupported": ["topology changes", "branches", "functions", "timers", "comments"],
        "verification": "Prior examples user-confirmed in GUI; each new artifact needs GUI check",
        "plc_verified": False,
    }
