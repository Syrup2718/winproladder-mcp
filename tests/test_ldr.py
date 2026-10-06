from dataclasses import replace
from pathlib import Path

import pytest

from winproladder_mcp.ldr import FOOTER, Document, LdrError, Record, parse
from winproladder_mcp.service import default_header

SAMPLES = Path(__file__).parents[1] / "samples"


@pytest.mark.parametrize("path", sorted(SAMPLES.glob("*.ldr")), ids=lambda p: p.name)
def test_lossless_roundtrip(path: Path) -> None:
    data = path.read_bytes()
    doc = parse(data)
    assert doc.encode() == data
    assert doc.editable
    profile = {
        "test6.ldr": "FBs-24MA",
        "test7.ldr": "FBs-24MA-test7",
        "test8.ldr": "FBs-24MA-test7",
        "test9.ldr": "FBs-24MA-test7",
        "test10.ldr": "FBs-24MA-test7",
        "test11.ldr": "FBs-32MA-test11",
    }.get(path.name, "FBs-20MC")
    assert doc.header == default_header(profile)


def test_unknown_payload_and_trailer_roundtrip() -> None:
    record = Record.create(bytes.fromhex("deadbeef001210ffff"))
    record = replace(record, trailer=b"\x02\x03\x04")
    data = Document(default_header(), (record,), FOOTER).encode()
    parsed = parse(data, strict_crc=False)
    assert parsed.encode() == data
    assert not parsed.editable


def test_unknown_tail_not_scanned() -> None:
    tail = bytes.fromhex("ab0012100000ffff00000000")
    data = default_header() + tail
    doc = parse(data)
    assert not doc.records
    assert doc.tail == tail
    assert doc.encode() == data
    assert not doc.editable


def test_bad_crc_strict_and_forensic() -> None:
    data = bytearray((SAMPLES / "w1.ldr").read_bytes())
    data[269] ^= 1
    with pytest.raises(LdrError, match="CRC mismatch at 0x10D"):
        parse(bytes(data))
    assert parse(bytes(data), strict_crc=False).encode() == bytes(data)


@pytest.mark.parametrize("size", [0, 20, 255, 256, 257, 258, 260, 267, 270, 271, 272, 276])
def test_truncation(size: int) -> None:
    data = (SAMPLES / "w1.ldr").read_bytes()[:size]
    with pytest.raises(LdrError):
        parse(data)


def test_invalid_length_and_extra_footer_bytes() -> None:
    data = bytearray((SAMPLES / "w1.ldr").read_bytes())
    data[258] = 2
    with pytest.raises(LdrError, match="lengths at 0x100"):
        parse(bytes(data))
    data = (SAMPLES / "w1.ldr").read_bytes() + b"extra"
    doc = parse(data)
    assert not doc.editable
    assert doc.encode() == data
