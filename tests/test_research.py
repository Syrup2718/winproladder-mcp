"""Sample evidence and adversarial checks for the framing probe."""

from pathlib import Path

import pytest

from winproladder_mcp.research import crc16, diff, hexdump, inspect

SAMPLES = Path(__file__).parents[1] / "samples"
PAYLOADS = {
    "test4.ldr": [
        "41026004a00560069007e443e200c109",
        "e0005001c103",
        "e0004000c101",
        "581691038107c108",
        "41038816c105",
        "50028003d102",
        "5100c101",
        "5000c100",
    ],
    "test3.ldr": [
        "4812c105",
        "4301c812",
        "4fe87fe8f94000110596",
        "4fe87fe8f94000100594",
        "4fe87fe8f940000a0592",
        "4fe8fd8000650396",
        "4fe8fd8003e80394",
        "4fe8fd8001000392",
        "5feb",
        "4001c101",
        "5feb",
        "4000c100",
    ],
    "w1.ldr": ["4000c101"],
    "test.ldr": [
        "5feb",
        "5feb",
        "5006a00880076009a00ae200c106",
        "4201800380049005c105",
        "4fe8fd80006403926ffcc104",
        "4002c102c103",
        "4001c102",
        "4000c101",
    ],
    "test2.ldr": [
        "4000a001c100",
        "4fe8fd80006503946ffcc100",
        "4000c810",
        "5000c810",
        "5000c100",
        "4000c100",
    ],
}


@pytest.mark.parametrize("name", PAYLOADS)
def test_all_observed_records(name: str) -> None:
    data = (SAMPLES / name).read_bytes()
    report = inspect(data)
    records = report["records"]
    assert isinstance(records, list)
    assert [r["payload"].replace(" ", "") for r in records] == PAYLOADS[name]
    offset = 256
    for record in records:
        assert record["offset"] == offset
        assert record["record_length"] == record["payload_length"] + 5
        assert record["crc_valid"]
        assert record["trailer"] == "01 00 00"
        offset += record["record_length"] + 6
    assert offset == len(data) - 6 == report["footer_offset"]
    assert report["footer"] == "ff ff 00 00 00 00"


def test_headers_identical() -> None:
    headers = [(SAMPLES / name).read_bytes()[:256] for name in PAYLOADS]
    assert len(set(headers)) == 1
    header = headers[0]
    assert header[:29] == b"Fatek Resource File Format 1\x16"
    assert header[128:134] == b"FB-RES"
    assert header[144:156] == b"WinProladder"
    assert header[160:168] == b"FBs-20MC"


def test_crc_known_vectors() -> None:
    assert crc16(b"123456789") == 0x4B37
    assert crc16(bytes.fromhex("04004000c100010000")) == 0xE515


def test_corruption_is_reported() -> None:
    data = bytearray((SAMPLES / "w1.ldr").read_bytes())
    data[262] ^= 1
    records = inspect(bytes(data))["records"]
    assert isinstance(records, list)
    assert records[0]["crc_valid"] is False


@pytest.mark.parametrize("size", [0, 26, 255, 256, 261, 262, 269, 270, 271, 276])
def test_truncation_rejected(size: int) -> None:
    with pytest.raises(ValueError):
        inspect((SAMPLES / "w1.ldr").read_bytes()[:size])


@pytest.mark.parametrize("offset", [256, 258, 260, 271])
def test_invalid_framing_rejected(offset: int) -> None:
    data = bytearray((SAMPLES / "w1.ldr").read_bytes())
    data[offset] ^= 1
    with pytest.raises(ValueError):
        inspect(bytes(data))


def test_trailing_bytes_rejected() -> None:
    with pytest.raises(ValueError):
        inspect((SAMPLES / "w1.ldr").read_bytes() + b"extra")


def test_diff_reports_changes_and_missing_bytes() -> None:
    assert diff(b"ab", b"acx") == [
        {"offset": 1, "left": 98, "right": 99},
        {"offset": 2, "left": None, "right": 120},
    ]
    assert diff(b"x", b"") == [{"offset": 0, "left": 120, "right": None}]
    assert diff(b"same", b"same") == []
    assert hexdump(b"A\x00").endswith("A.")
