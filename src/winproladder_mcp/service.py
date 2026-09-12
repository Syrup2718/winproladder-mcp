"""File-scoped application service shared by MCP and tests."""

import hashlib
import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .acceptance import AcceptanceCase, check_acceptance
from .analysis import describe, device_references
from .design import design_guide
from .ir import (
    Ladder,
    Network,
    block_catalog,
    compile_network,
    decode_network,
    start_stop,
    validation,
)
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
            "sha256": hashlib.sha256(document.encode()).hexdigest(),
            "header_hex": document.header.hex(" "),
            "record_count": len(document.records),
            "editable": document.editable and document.header == default_header(),
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
                    "description": describe(decoded)
                    if decoded
                    else "Opaque: unsupported instruction or framing",
                    "raw_payload_hex": record.payload.hex(" "),
                }
            )
        return {
            "networks": networks,
            "ladder": {"networks": [item["logic"] for item in networks]}
            if networks and all(item["logic"] is not None for item in networks)
            else None,
            "sha256": hashlib.sha256(document.encode()).hexdigest(),
            "editable": document.editable and document.header == default_header(),
            "note": "Decoded semantics use the documented subset; opaque networks are preserved.",
        }

    def analyze(self, path: str) -> dict[str, Any]:
        result = self.read(path)
        references = device_references(
            [
                (item["index"], Network.model_validate(item["logic"]) if item["logic"] else None)
                for item in result["networks"]
            ]
        )
        return {
            "sha256": result["sha256"],
            "network_count": len(result["networks"]),
            "decoded_count": sum(item["logic"] is not None for item in result["networks"]),
            "networks": [
                {
                    "index": item["index"],
                    "status": item["status"],
                    "description": item["description"],
                }
                for item in result["networks"]
            ],
            "references": references,
            "warnings": ["Analysis is incomplete: opaque networks may contain additional devices."]
            if not references["complete"]
            else [],
        }

    def compare(self, left_path: str, right_path: str) -> dict[str, Any]:
        left = self.load(left_path, strict_crc=False)
        right = self.load(right_path, strict_crc=False)
        for doc in (left, right):
            if doc.tail != FOOTER or doc.header != default_header():
                raise LdrError("Network comparison requires sampled header and known footer")
            if len(doc.records) > 2000:
                raise LdrError("Comparison is limited to 2000 networks per file")
        lrecords, rrecords = list(reversed(left.records)), list(reversed(right.records))
        matcher = SequenceMatcher(
            a=[r.encode() for r in lrecords], b=[r.encode() for r in rrecords], autojunk=False
        )
        changes = []
        for tag, i, j, k, end in matcher.get_opcodes():
            if tag != "equal":
                changes.append(
                    {
                        "operation": tag,
                        "left_range": [i, j],
                        "right_range": [k, end],
                        "left": [
                            {
                                "index": n,
                                "payload_hex": lrecords[n].payload.hex(" "),
                                "trailer_hex": lrecords[n].trailer.hex(" "),
                                "crc": lrecords[n].crc,
                                "crc_valid": lrecords[n].crc_valid,
                            }
                            for n in range(i, j)
                        ],
                        "right": [
                            {
                                "index": n,
                                "payload_hex": rrecords[n].payload.hex(" "),
                                "trailer_hex": rrecords[n].trailer.hex(" "),
                                "crc": rrecords[n].crc,
                                "crc_valid": rrecords[n].crc_valid,
                            }
                            for n in range(k, end)
                        ],
                    }
                )
        return {
            "byte_identical": left.encode() == right.encode(),
            "left_sha256": hashlib.sha256(left.encode()).hexdigest(),
            "right_sha256": hashlib.sha256(right.encode()).hexdigest(),
            "left_count": len(lrecords),
            "right_count": len(rrecords),
            "changes": changes,
            "note": (
                "Display-order ranges are [start, end). Exact-record alignment; "
                "duplicate networks may align ambiguously. No semantic equivalence claim."
            ),
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

    def generate(
        self, name: str, ladder: Ladder, acceptance: list[AcceptanceCase] | None = None
    ) -> dict[str, Any]:
        report = check_acceptance(ladder, acceptance) if acceptance is not None else None
        if report is not None and not report["passed"]:
            raise ValueError(f"Acceptance failed; no file written: {report}")
        result = self.create(name, ladder, allow_unverified=True)
        return {
            **result,
            "acceptance": report,
            "design_summary": [describe(n) for n in ladder.networks],
            "encoding_policy": "Inferred compiler enabled; see validation warnings.",
            "next_step": "Import the file into WinProLadder; no physical PLC operation performed.",
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

    def generate_design(
        self,
        name: str,
        ladder: Ladder,
        design: dict[str, Any],
        acceptance: list[AcceptanceCase] | None = None,
    ) -> dict[str, Any]:
        result = {**self.generate(name, ladder, acceptance), "design": design}
        report = Path(result["path"] + ".design.json")
        try:
            with report.open("x", encoding="utf-8") as stream:
                json.dump(result, stream, ensure_ascii=False, indent=2)
        except OSError as error:
            # The LDR already exists and must remain accessible even if report writing fails.
            result["design_report_warning"] = f"LDR created; companion report not saved: {error}"
        else:
            result["design_report"] = str(report)
        return result

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
        decoded = [decode_network(r.payload) for r in records]
        if any(n is not None and n.action is not None for n in decoded):
            if any(n is None for n in decoded):
                raise ValueError("Cannot validate loop edits with opaque networks")
            check = validation(Ladder(networks=[n for n in decoded if n is not None]))
            if not check["valid"]:
                raise ValueError(str(check["errors"]))
        return {
            **self.write(name, Document(document.header, tuple(reversed(records)), document.tail)),
            "import_verified": False,
            "unchanged_networks_preserved": True,
        }


def capabilities() -> dict[str, Any]:
    return {
        "version": "0.4.0",
        "profile": "WinProLadder v3.28 / FBs-20MC sampled header",
        "transport": "stdio",
        "simulation": "Boolean or scan_ms T/C model; max 256 scans, not a PLC emulator",
        "file_operations": ["inspect", "read", "create", "export", "replace", "insert", "delete"],
        "ir": "Prefer condition Boolean expressions; legacy steps use left-fold semantics.",
        "address_subset": {
            "X": "0..255",
            "Y": "0..255",
            "M": "0..255",
            "T": "0..255",
            "C": "0..255",
        },
        "generation": "generate_control_ldr: 11 recipes; generate_sequence_ldr: up to 16 steps, "
        "pause/resume whole ticks and timeout; generate_system_ldr: independent controls with "
        "automatic resource allocation; generate_ldr: custom Boolean/T/C/register/loop IR.",
        "inference_notice": "Unseen combinations/ranges are inferred, not PLC-validated.",
        "design_guide": design_guide(),
        "block_templates": [
            {
                "network": network.model_dump(),
                "payload_hex": payload.hex(" "),
                "source": source,
                "status": "observed_export; generated file needs import validation",
            }
            for network, payload, source in block_catalog()
        ],
        "analysis": [
            "analyze_ldr: descriptions and device cross-references",
            "compare_ldr: aligned record changes",
        ],
        "opaque_only": [
            "edge contacts",
            "unknown instructions",
        ],
        "verified_template": "start_stop: X1=1 stops; user reported import success",
        "no_plc_connection": True,
        "writes": "new .ldr files only in configured output directory; never overwrite",
        "start_stop_example": start_stop().model_dump(),
        "schema": Ladder.model_json_schema(),
    }
