"""Read-only probes for the currently observed LDR framing, not a semantic parser."""

import argparse
import json
from pathlib import Path


def crc16(data: bytes) -> int:
    """Reflected CRC with polynomial 0xA001 and initial register 0xFFFF."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc


def inspect(data: bytes) -> dict[str, object]:
    """Fail explicitly if a file falls outside the observed framing hypothesis."""
    if len(data) < 262 or not data.startswith(b"Fatek Resource File Format 1"):
        raise ValueError("Unsupported or truncated resource header")
    records: list[dict[str, object]] = []
    offset = 256
    while data[offset : offset + 6] != bytes.fromhex("ffff00000000"):
        if data[offset : offset + 2] != b"\x12\x10" or offset + 6 > len(data):
            raise ValueError(f"Unexpected record at 0x{offset:X}")
        length = int.from_bytes(data[offset + 2 : offset + 4], "little")
        payload_length = int.from_bytes(data[offset + 4 : offset + 6], "little")
        end = offset + length + 6
        if length != payload_length + 5 or end > len(data):
            raise ValueError(f"Invalid lengths at 0x{offset:X}")
        stored = int.from_bytes(data[end - 2 : end], "little")
        computed = crc16(data[offset + 4 : end - 2])
        records.append(
            {
                "file_index": len(records),
                "offset": offset,
                "record_length": length,
                "payload_length": payload_length,
                "payload": data[offset + 6 : end - 5].hex(" "),
                "trailer": data[end - 5 : end - 2].hex(" "),
                "stored_crc": stored,
                "computed_crc": computed,
                "crc_valid": stored == computed,
            }
        )
        offset = end
    if offset + 6 != len(data):
        raise ValueError("Unexpected bytes after end marker")
    return {
        "size": len(data),
        "header": data[:256].hex(" "),
        "records": records,
        "footer_offset": offset,
        "footer": data[offset:].hex(" "),
    }


def hexdump(data: bytes) -> str:
    return "\n".join(
        f"{offset:08X}  {data[offset : offset + 16].hex(' '):47}  "
        + "".join(chr(b) if 32 <= b < 127 else "." for b in data[offset : offset + 16])
        for offset in range(0, len(data), 16)
    )


def diff(left: bytes, right: bytes) -> list[dict[str, int | None]]:
    """Compare absolute offsets; insertions are not instruction-aligned."""
    return [
        {
            "offset": i,
            "left": left[i] if i < len(left) else None,
            "right": right[i] if i < len(right) else None,
        }
        for i in range(max(len(left), len(right)))
        if (left[i] if i < len(left) else None) != (right[i] if i < len(right) else None)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inspect", "hexdump", "diff"])
    parser.add_argument("path", type=Path)
    parser.add_argument("other", type=Path, nargs="?")
    args = parser.parse_args()
    if args.command == "diff" and args.other is None:
        parser.error("diff requires two paths")
    try:
        data = args.path.read_bytes()
        if args.command == "hexdump":
            print(hexdump(data))
        else:
            result = (
                diff(data, args.other.read_bytes()) if args.command == "diff" else inspect(data)
            )
            print(json.dumps(result, indent=2))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
