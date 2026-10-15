"""Exact sampled headers; model names alone do not establish encoding compatibility."""

from typing import Literal

HeaderProfile = Literal[
    "FBs-40MC-test27",
    "HB1-32M-test23",
    "FB-28MA-test22",
    "FBe-40MC-test21",
    "FBe-20MA-test19",
    "FBn-26MC-test17",
    "FBs-60MC-test16",
    "FBs-20MC",
    "FBs-24MA",
    "FBs-24MA-test7",
    "FBs-32MA-test11",
    "FBs-40MA-test12",
    "FBs-44MN-test13",
]

_PROFILE_DATA: dict[HeaderProfile, tuple[str, str]] = {
    "FBs-20MC": ("FBs-20MC", "4040"),
    "FBs-24MA": ("FBs-24MA", "1045"),
    "FBs-24MA-test7": ("FBs-24MA", "1040"),
    "FBs-32MA-test11": ("FBs-32MA", "1040"),
    "FBs-40MA-test12": ("FBs-40MA", "1040"),
    "FBs-44MN-test13": ("FBs-44MN", "4040"),
    "FBs-60MC-test16": ("FBs-60MC", "4040"),
    "FBn-26MC-test17": ("FBn-26MC", "4030"),
    "FBe-20MA-test19": ("FBe-20MA", "1030"),
    "FBe-40MC-test21": ("FBe-40MC", "4030"),
    "FB-28MA-test22": ("FB-28MA", "1020"),
    "HB1-32M-test23": ("HB1-32M", "1055"),
    "FBs-40MC-test27": ("FBs-40MC", "4040"),
}


def _build_header(model: str, metadata: str) -> bytes:
    header = bytearray(256)
    header[:29] = b"Fatek Resource File Format 1\x16"
    header[128:134] = b"FB-RES"
    header[144:156] = b"WinProladder"
    header[160:168] = model.encode("ascii").ljust(8, b"\x00")
    header[176:178] = bytes.fromhex(metadata)
    header[192:194] = b"H\x01"
    return bytes(header)


_HEADERS = {name: _build_header(*data) for name, data in _PROFILE_DATA.items()}
_PROFILES = {header: name for name, header in _HEADERS.items()}
if len(_PROFILES) != len(_HEADERS):
    raise RuntimeError("Sampled header profiles must be unique")


def default_header(profile: HeaderProfile = "FBs-20MC") -> bytes:
    try:
        return _HEADERS[profile]
    except KeyError:
        raise ValueError("Unsupported header profile") from None


def header_profile(header: bytes) -> HeaderProfile | None:
    return _PROFILES.get(header)
