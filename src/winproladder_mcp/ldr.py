"""Lossless resource framing. Unknown framing is retained as an opaque tail."""

from dataclasses import dataclass

from .research import crc16

MAGIC = b"Fatek Resource File Format 1"
FOOTER = bytes.fromhex("ffff00000000")
MAX_SIZE = 16 * 1024 * 1024


class LdrError(ValueError):
    """Malformed or unsupported LDR data, with an offset when available."""


@dataclass(frozen=True)
class Record:
    payload: bytes
    trailer: bytes
    crc: int
    offset: int = 0

    @property
    def body(self) -> bytes:
        return len(self.payload).to_bytes(2, "little") + self.payload + self.trailer

    @property
    def crc_valid(self) -> bool:
        return crc16(self.body) == self.crc

    def encode(self) -> bytes:
        if len(self.trailer) != 3 or len(self.payload) > 65530:
            raise LdrError("Record exceeds supported framing")
        return (
            b"\x12\x10"
            + (len(self.payload) + 5).to_bytes(2, "little")
            + self.body
            + self.crc.to_bytes(2, "little")
        )

    @classmethod
    def create(cls, payload: bytes) -> "Record":
        if len(payload) > 65530:
            raise LdrError("Payload too large")
        body = len(payload).to_bytes(2, "little") + payload + b"\x01\x00\x00"
        return cls(payload, b"\x01\x00\x00", crc16(body))


@dataclass(frozen=True)
class Document:
    header: bytes
    records: tuple[Record, ...]  # Physical order, reverse of displayed networks.
    tail: bytes

    @property
    def editable(self) -> bool:
        return self.tail == FOOTER and all(
            r.crc_valid and r.trailer == b"\x01\x00\x00" for r in self.records
        )

    def encode(self) -> bytes:
        return self.header + b"".join(r.encode() for r in self.records) + self.tail


def parse(data: bytes, *, strict_crc: bool = True) -> Document:
    if len(data) > MAX_SIZE:
        raise LdrError("File exceeds 16 MiB limit")
    if len(data) < 256 or not data.startswith(MAGIC):
        raise LdrError("Unsupported or truncated header at 0x0")
    records = []
    offset = 256
    while True:
        if offset >= len(data):
            raise LdrError(f"Missing footer at 0x{offset:X}")
        if data[offset:] in {b"\x12", b"\xff"}:
            raise LdrError(f"Truncated marker at 0x{offset:X}")
        if data[offset : offset + 2] == b"\xff\xff":
            if data[offset : offset + 6] != FOOTER:
                raise LdrError(f"Malformed footer at 0x{offset:X}")
            break
        if data[offset : offset + 2] != b"\x12\x10":
            # Never scan within an unknown body for a marker: it might be payload data.
            break
        if offset + 6 > len(data):
            raise LdrError(f"Truncated record header at 0x{offset:X}")
        length = int.from_bytes(data[offset + 2 : offset + 4], "little")
        size = int.from_bytes(data[offset + 4 : offset + 6], "little")
        end = offset + length + 6
        if length != size + 5 or end > len(data):
            raise LdrError(f"Invalid record lengths at 0x{offset:X}")
        record = Record(
            data[offset + 6 : end - 5],
            data[end - 5 : end - 2],
            int.from_bytes(data[end - 2 : end], "little"),
            offset,
        )
        if strict_crc and not record.crc_valid:
            raise LdrError(f"CRC mismatch at 0x{end - 2:X} (record 0x{offset:X})")
        records.append(record)
        offset = end
    return Document(data[:256], tuple(records), data[offset:])
