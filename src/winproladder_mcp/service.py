"""File-scoped application service shared by MCP and tests."""

import hashlib
from pathlib import Path
from typing import Any

from .ir import Ladder, Network, compile_network, decode_network, start_stop, validation
from .ldr import FOOTER, MAX_SIZE, Document, LdrError, Record, parse


def default_header() -> bytes:
    # Exact shared header from all five v3.28 FBs-20MC exports; no unknown
    # metadata is inferred. See test_lossless_roundtrip.
    header = bytearray(256)
    header[:29] = b"Fatek Resource File Format 1\x16"
    header[128:134] = b"FB-RES"
    header[144:156] = b"WinProladder"
    header[160:168] = b"FBs-20MC"
    header[176:178] = b"@@"
    header[192:194] = b"H\x01"
    return bytes(header)


class Service:
    def __init__(self, root: Path, output_dir: Path | None = None):
        self.root = root.resolve(strict=True)
        self.output = (output_dir or self.root / "artifacts").resolve()
        if not self.output.is_relative_to(self.root) or self.output == self.root:
            raise ValueError("Output directory must be a subdirectory of workspace")
        if self.output.relative_to(self.root).parts[0].lower() in {
            "samples",
            "src",
            "tests",
            "docs",
        } or any(p.startswith(".") for p in self.output.relative_to(self.root).parts):
            raise ValueError("Output directory must not be a source, sample, or hidden directory")

    def source(self, path: str) -> Path:
        target = (self.root / path).resolve(strict=True)
        if not target.is_relative_to(self.root) or target.suffix.lower() != ".ldr":
            raise ValueError("Read path must be an .ldr file inside workspace")
        if not target.is_file() or target.stat().st_size > MAX_SIZE:
            raise ValueError("Not a file or exceeds 16 MiB limit")
        return target

    def load(self, path: str, *, strict_crc: bool = True) -> Document:
        with self.source(path).open("rb") as stream:
            return parse(stream.read(MAX_SIZE + 1), strict_crc=strict_crc)

    def write(self, name: str, document: Document) -> dict[str, Any]:
        # Basename only: no caller-controlled directory traversal or overwrites.
        if (
            not name
            or Path(name).name != name
            or any(c in name for c in "/\\:")
            or any(c in name for c in '<>"|?*')
            or Path(name).is_reserved()
            or not name.lower().endswith(".ldr")
            or name.startswith(".")
        ):
            raise ValueError("Output must be a plain .ldr filename")
        self.output.mkdir(parents=True, exist_ok=True)
        if self.output.resolve() != self.output:
            raise ValueError("Output directory changed through a symlink")
        target = self.output / name
        data = document.encode()
        # Re-parse before touching the output; opaque data is preserved.
        parse(data, strict_crc=False)
        with target.open("xb") as stream:
            stream.write(data)
        return {"path": str(target), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def inspect(self, path: str) -> dict[str, Any]:
        document = self.load(path, strict_crc=False)
        known_order = document.tail == FOOTER
        return {
            "path": str(self.source(path)),
            "size": len(document.encode()),
            "header_hex": document.header.hex(" "),
            "record_count": len(document.records),
            "editable": document.editable,
            "network_order": "reverse" if known_order else "unknown",
            "tail_hex": document.tail.hex(" "),
            "opaque_tail": not known_order,
            "records": [
                {
                    "file_index": i,
                    "network_index": len(document.records) - 1 - i if known_order else None,
                    "offset": r.offset,
                    "payload_length": len(r.payload),
                    "record_length": len(r.payload) + 5,
                    "payload_hex": r.payload.hex(" "),
                    "trailer_hex": r.trailer.hex(" "),
                    "crc": r.crc,
                    "crc_valid": r.crc_valid,
                }
                for i, r in enumerate(document.records)
            ],
        }

    def read(self, path: str) -> dict[str, Any]:
        document = self.load(path)
        if document.tail != FOOTER:
            raise LdrError(
                "Unknown framing: use inspect_ldr/export_ldr; network order cannot be assigned"
            )
        networks = []
        for index, record in enumerate(reversed(document.records)):
            decoded = (
                decode_network(record.payload)
                if record.trailer == b"\x01\x00\x00" and document.header == default_header()
                else None
            )
            networks.append(
                {
                    "index": index,
                    "offset": record.offset + 6,
                    "status": "decoded_subset" if decoded else "opaque",
                    "logic": decoded.model_dump() if decoded else None,
                    "raw_payload_hex": record.payload.hex(" "),
                }
            )
        return {
            "networks": networks,
            "editable": document.editable,
            "note": "Decoded semantics use the documented subset; opaque networks are preserved.",
        }

    def create(self, name: str, ladder: Ladder, allow_unverified: bool = False) -> dict[str, Any]:
        result = validation(ladder)
        if not result["valid"]:
            raise ValueError(str(result["errors"]))
        if not result["import_verified"] and not allow_unverified:
            raise ValueError(
                "Composition not import-verified; validate_ladder first "
                "and explicitly set allow_unverified=true for a candidate"
            )
        records = tuple(Record.create(compile_network(n)) for n in reversed(ladder.networks))
        return {
            **self.write(name, Document(default_header(), records, FOOTER)),
            "validation": result,
        }

    def export(self, path: str, name: str) -> dict[str, Any]:
        document = self.load(path, strict_crc=False)
        return {
            **self.write(name, document),
            "byte_identical": True,
            "warnings": []
            if document.editable
            else ["Unknown framing/trailer or invalid CRC; preserved exactly, not repaired."],
        }

    def edit(
        self,
        path: str,
        name: str,
        operation: str,
        index: int,
        network: Network | None,
        allow_unverified: bool,
    ) -> dict[str, Any]:
        document = self.load(path)
        if not document.editable:
            raise LdrError("Cannot edit unknown framing/trailers or invalid CRC")
        if document.header != default_header():
            raise LdrError("Editing is limited to the sampled v3.28 FBs-20MC header")
        if not allow_unverified:
            raise ValueError(
                "Edited program requires import verification; explicitly set allow_unverified=true"
            )
        records = list(reversed(document.records))
        if operation not in {"replace", "insert", "delete"}:
            raise ValueError("Unknown edit operation")
        limit = len(records) + (operation == "insert")
        if isinstance(index, bool) or not 0 <= index < limit:
            raise ValueError("Network index out of range")
        if operation == "delete":
            if network is not None or len(records) == 1:
                raise ValueError("Delete requires no network and must leave at least one network")
            records.pop(index)
        else:
            if network is None:
                raise ValueError("Replacement/insertion requires a network")
            record = Record.create(compile_network(network))
            if operation == "insert":
                records.insert(index, record)
            else:
                records[index] = record
        if len(records) > 1000:
            raise ValueError("Network limit is 1000")
        return {
            **self.write(name, Document(document.header, tuple(reversed(records)), document.tail)),
            "import_verified": False,
            "unchanged_networks_preserved": True,
        }


def capabilities() -> dict[str, Any]:
    return {
        "version": "0.1.0",
        "profile": "WinProLadder v3.28 / FBs-20MC sampled header",
        "transport": "stdio",
        "simulation": "Boolean IR only; max 256 scans, no timing/edge/PLC emulation",
        "file_operations": ["inspect", "read", "create", "export", "replace", "insert", "delete"],
        "ir": "Left-fold: first load, then and/or; coils at end. No implicit precedence.",
        "address_subset": {"X": "0..10", "Y": "0..9", "M": [0, 2, 6], "T": [1], "C": [1]},
        "generation": "Simple contacts and Y/M coils; OR only X NO. Use validate_ladder.",
        "opaque_only": [
            "Timer",
            "Counter blocks",
            "edge contacts",
            "inverted coils",
            "nested branches",
            "unknown instructions",
        ],
        "verified_template": "start_stop: X1=1 stops; user reported import success",
        "no_plc_connection": True,
        "writes": "new .ldr files only in configured output directory; never overwrite",
        "start_stop_example": start_stop().model_dump(),
        "schema": Ladder.model_json_schema(),
    }
