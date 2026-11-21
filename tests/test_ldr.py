from dataclasses import replace
from typing import get_args

import pytest

from winproladder_mcp.crc import crc16
from winproladder_mcp.ir import HeaderProfile
from winproladder_mcp.ldr import FOOTER, Document, LdrError, Record, parse
from winproladder_mcp.service import default_header, header_profile


def synthetic_document() -> bytes:
    records = (Record.create(bytes.fromhex("deadbeef")), Record.create(b"public-fixture"))
    return Document(default_header(), records, FOOTER).encode()


def test_synthetic_document_round_trips_losslessly() -> None:
    data = synthetic_document()
    document = parse(data)
    assert document.encode() == data
    assert document.editable
    assert all(record.crc_valid for record in document.records)


def test_crc16_public_check_vectors() -> None:
    assert crc16(b"123456789") == 0x4B37
    assert crc16(bytes.fromhex("04004000c100010000")) == 0xE515


def test_unknown_payload_and_trailer_roundtrip() -> None:
    record = replace(Record.create(bytes.fromhex("deadbeef001210ffff")), trailer=b"\x02\x03\x04")
    data = Document(default_header(), (record,), FOOTER).encode()
    parsed = parse(data, strict_crc=False)
    assert parsed.encode() == data
    assert not parsed.editable


def test_unknown_tail_not_scanned() -> None:
    tail = bytes.fromhex("ab0012100000ffff00000000")
    data = default_header() + tail
    document = parse(data)
    assert not document.records
    assert document.tail == tail
    assert document.encode() == data
    assert not document.editable


def test_bad_crc_strict_and_forensic() -> None:
    data = bytearray(synthetic_document())
    data[262] ^= 1
    with pytest.raises(LdrError, match="CRC mismatch"):
        parse(bytes(data))
    assert parse(bytes(data), strict_crc=False).encode() == bytes(data)


@pytest.mark.parametrize("size", [0, 20, 255, 256, 257, 258, 260, 267])
def test_truncation(size: int) -> None:
    with pytest.raises(LdrError):
        parse(synthetic_document()[:size])


def test_invalid_length_and_extra_footer_bytes() -> None:
    data = bytearray(synthetic_document())
    data[258] = 2
    with pytest.raises(LdrError, match="lengths"):
        parse(bytes(data))
    extra = synthetic_document() + b"extra"
    document = parse(extra)
    assert not document.editable
    assert document.encode() == extra


@pytest.mark.parametrize("marker", [b"\x12", b"\xff"])
def test_truncated_marker_after_many_records(marker: bytes) -> None:
    record = Record.create(b"\xde\xad").encode()
    data = default_header() + record * 1000 + marker
    with pytest.raises(LdrError, match="Truncated marker"):
        parse(data)


def test_unknown_metadata_is_not_recognized_as_known_model() -> None:
    header = bytearray(default_header())
    header[177] ^= 1
    assert header_profile(bytes(header)) is None


def test_every_declared_profile_has_distinct_exact_header() -> None:
    for profile in get_args(HeaderProfile):
        assert header_profile(default_header(profile)) == profile
