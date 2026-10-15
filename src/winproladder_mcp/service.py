"""File-scoped application service shared by MCP and tests."""

import hashlib
import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .acceptance import AcceptanceCase, check_acceptance
from .analysis import describe, device_references, timer_settings
from .architecture import architecture_report, enforce_architecture, load_policy
from .capabilities import capabilities as capabilities
from .io_contract import IOContract, check_io
from .ir import (
    Ladder,
    Network,
    compile_network,
    decode_network,
    validation,
)
from .layout import expressions, lower_ladder, memory_used, needs_lowering
from .ldr import FOOTER, MAX_SIZE, Document, LdrError, Record, parse
from .profiles import default_header as default_header
from .profiles import header_profile as header_profile


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

    def architecture_policy(self) -> dict[str, Any]:
        return load_policy(self.root).model_dump()

    def architecture(self, ladder: Ladder, *, enforce: bool = True) -> dict[str, Any]:
        policy = load_policy(self.root)
        return (
            enforce_architecture(ladder, policy) if enforce else architecture_report(ladder, policy)
        )

    def check_layout(self, layout: dict[str, Any]) -> None:
        if load_policy(self.root).forbid_m_to_m and layout["helper_devices"]:
            raise ValueError(
                "Workspace architecture forbids automatically lowered relay helpers; no "
                "file written. "
                "This condition requires an unsampled connected branch encoding; simplify the "
                "condition or use supported native instructions, never disguised relay chains."
            )

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
        # Final gate covers create/generate/edit/export and direct service writes.
        # Read/inspect remain available for old or opaque files.
        policy = load_policy(self.root)
        if policy.forbid_m_to_m:
            if document.tail != FOOTER or header_profile(document.header) is None:
                raise ValueError("Cannot enforce architecture on unknown framing; no file written")
            decoded = [
                decode_network(r.payload) if r.trailer == b"\x01\x00\x00" else None
                for r in reversed(document.records)
            ]
            if not decoded or any(n is None for n in decoded):
                raise ValueError("Cannot enforce architecture on opaque networks; no file written")
            enforce_architecture(Ladder(networks=[n for n in decoded if n is not None]), policy)
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
            "editable": document.editable and header_profile(document.header) is not None,
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
                if record.trailer == b"\x01\x00\x00" and header_profile(document.header) is not None
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
            "timer_settings": timer_settings(
                [
                    (
                        index,
                        Network.model_validate(item["logic"]) if item["logic"] else None,
                    )
                    for index, item in enumerate(networks)
                ]
            ),
            "ladder": {
                "profile": header_profile(document.header),
                "networks": [item["logic"] for item in networks],
            }
            if networks and all(item["logic"] is not None for item in networks)
            else None,
            "sha256": hashlib.sha256(document.encode()).hexdigest(),
            "editable": document.editable and header_profile(document.header) is not None,
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
            "timer_settings": result["timer_settings"],
            "warnings": [
                "Analysis is incomplete: opaque networks or unresolved runtime references "
                "may contain additional devices; see reference_uncertainties."
            ]
            if not references["complete"]
            else [],
        }

    def compare(self, left_path: str, right_path: str) -> dict[str, Any]:
        left = self.load(left_path, strict_crc=False)
        right = self.load(right_path, strict_crc=False)
        for doc in (left, right):
            if doc.tail != FOOTER or header_profile(doc.header) is None:
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

    def create(
        self,
        name: str,
        ladder: Ladder,
        allow_unverified: bool = False,
        *,
        acceptance: list[AcceptanceCase] | None = None,
        io_contract: IOContract | None = None,
    ) -> dict[str, Any]:
        self.architecture(ladder)
        source_devices = set(device_references(list(enumerate(ladder.networks)))["devices"])
        # Low-level callers explicitly provide their ladder; enforce that lowering cannot
        # extend its physical I/O even when there is no separate customer contract.
        contract = io_contract or IOContract(
            inputs=sorted(d for d in source_devices if d.startswith("X")),
            outputs=sorted(d for d in source_devices if d.startswith("Y")),
        )
        check_io(source_devices, contract)
        lowered, layout = lower_ladder(ladder)
        self.architecture(lowered)
        self.check_layout(layout)
        ladder = lowered
        result = validation(ladder)
        if not result["valid"]:
            raise ValueError(str(result["errors"]))
        if not result["import_verified"] and not allow_unverified:
            raise ValueError(
                "Composition not import-verified; validate_ladder first "
                "and explicitly set allow_unverified=true for a candidate"
            )
        records = tuple(Record.create(compile_network(n)) for n in reversed(ladder.networks))
        document = Document(default_header(ladder.profile), records, FOOTER)
        # Validate the exact emitted bytes, including network order and decoding,
        # before creating a deliverable. Source-only simulation misses compiler bugs.
        parsed = parse(document.encode())
        decoded = [decode_network(r.payload) for r in reversed(parsed.records)]
        if any(n is None for n in decoded):
            raise ValueError("Generated network failed semantic decode; no file written")
        emitted = Ladder(profile=ladder.profile, networks=[n for n in decoded if n is not None])
        architecture = self.architecture(emitted)
        io_report = check_io(
            set(device_references(list(enumerate(emitted.networks)))["devices"]), contract
        )
        emitted_report = check_acceptance(emitted, acceptance) if acceptance is not None else None
        if emitted_report is not None and not emitted_report["passed"]:
            raise ValueError(f"Compiled acceptance failed; no file written: {emitted_report}")
        return {
            **self.write(name, document),
            "validation": result,
            "architecture": architecture,
            "profile": ladder.profile,
            "layout_normalized_networks": layout["normalized_networks"],
            "layout": layout,
            "io_contract": io_report,
            "timer_settings": timer_settings(list(enumerate(emitted.networks))),
            "symbols": ladder.symbols,
            "network_notes": [
                {"index": i, "comment": n.comment, "logic": describe(n)}
                for i, n in enumerate(ladder.networks)
            ],
            "annotation_scope": "Symbols/comments are metadata, not embedded LDR comments",
            "compiled_acceptance": emitted_report,
            "artifact_validation": {
                "crc_valid": True,
                "decoded_networks": len(emitted.networks),
                "scope": "Exact emitted LDR bytes; offline model, not GUI or PLC validation",
            },
        }

    def generate(
        self,
        name: str,
        ladder: Ladder,
        acceptance: list[AcceptanceCase] | None = None,
        *,
        io_contract: IOContract | None = None,
    ) -> dict[str, Any]:
        report = check_acceptance(ladder, acceptance) if acceptance is not None else None
        if report is not None and not report["passed"]:
            raise ValueError(f"Acceptance failed; no file written: {report}")
        result = self.create(
            name, ladder, allow_unverified=True, acceptance=acceptance, io_contract=io_contract
        )
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
        *,
        io_contract: IOContract | None = None,
    ) -> dict[str, Any]:
        result = {
            **self.generate(name, ladder, acceptance, io_contract=io_contract),
            "design": design,
        }
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
        if header_profile(document.header) is None:
            raise LdrError(
                "Editing requires an exact sampled FBs-20MC, FBs-24MA or FBs-32MA header"
            )
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
            context = [decode_network(r.payload) for r in records]
            if any(n is None for n in context) and any(
                needs_lowering(network, i, e) for i, e in enumerate(expressions(network))
            ):
                raise ValueError("Cannot allocate helpers safely with opaque networks")
            known = [n for n in context if n is not None]
            reserved = memory_used(Ladder(networks=known)) if known else set()
            self.architecture(Ladder(networks=[network]))
            lowered, edit_layout = lower_ladder(Ladder(networks=[network]), reserved)
            self.architecture(lowered)
            self.check_layout(edit_layout)
            replacement = [Record.create(compile_network(n)) for n in lowered.networks]
            records[index : index + (operation == "replace")] = replacement
        if len(records) > 1000:
            raise ValueError("Network limit is 1000")
        decoded = [decode_network(r.payload) for r in records]
        if any(n is not None and n.action is not None for n in decoded):
            if any(n is None for n in decoded):
                raise ValueError("Cannot validate loop edits with opaque networks")
            profile = header_profile(document.header)
            assert profile is not None  # Rejected before any edit when the header is unknown.
            check = validation(
                Ladder(profile=profile, networks=[n for n in decoded if n is not None])
            )
            if not check["valid"]:
                raise ValueError(str(check["errors"]))
        return {
            **self.write(name, Document(document.header, tuple(reversed(records)), document.tail)),
            "import_verified": False,
            "unchanged_networks_preserved": True,
        }
