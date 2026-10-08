"""File-scoped application service shared by MCP and tests."""

import hashlib
import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .acceptance import AcceptanceCase, check_acceptance
from .analysis import describe, device_references, timer_settings
from .architecture import architecture_report, enforce_architecture, load_policy
from .design import design_guide
from .io_contract import IOContract, check_io
from .ir import (
    HeaderProfile,
    Ladder,
    Network,
    block_catalog,
    compile_network,
    decode_network,
    start_stop,
    validation,
)
from .layout import expressions, lower_ladder, memory_used, needs_lowering
from .ldr import FOOTER, MAX_SIZE, Document, LdrError, Record, parse


def default_header(profile: HeaderProfile = "FBs-20MC") -> bytes:
    # Exact shared header from all five v3.28 FBs-20MC exports; no unknown
    # metadata is inferred. See test_lossless_roundtrip.
    header = bytearray(256)
    header[:29] = b"Fatek Resource File Format 1\x16"
    header[128:134] = b"FB-RES"
    header[144:156] = b"WinProladder"
    if profile not in {
        "FBs-20MC",
        "FBs-24MA",
        "FBs-24MA-test7",
        "FBs-32MA-test11",
        "FBs-40MA-test12",
        "FBs-44MN-test13",
    }:
        raise ValueError("Unsupported header profile")
    header[160:168] = (
        {
            "FBs-24MA-test7": "FBs-24MA",
            "FBs-32MA-test11": "FBs-32MA",
            "FBs-40MA-test12": "FBs-40MA",
            "FBs-44MN-test13": "FBs-44MN",
        }.get(profile, profile)
    ).encode("ascii")
    # Preserve exact sampled metadata, including unknown profile-specific fields.
    header[176:178] = b"@@" if profile == "FBs-20MC" else bytes.fromhex("1045")
    if profile in {"FBs-24MA-test7", "FBs-32MA-test11", "FBs-40MA-test12"}:
        header[176:178] = bytes.fromhex("1040")
    if profile == "FBs-44MN-test13":
        header[176:178] = b"@@"
    header[192:194] = b"H\x01"
    return bytes(header)


def header_profile(header: bytes) -> HeaderProfile | None:
    if header == default_header("FBs-44MN-test13"):
        return "FBs-44MN-test13"
    if header == default_header("FBs-40MA-test12"):
        return "FBs-40MA-test12"
    if header == default_header("FBs-32MA-test11"):
        return "FBs-32MA-test11"
    if header == default_header():
        return "FBs-20MC"
    if header == default_header("FBs-24MA"):
        return "FBs-24MA"
    if header == default_header("FBs-24MA-test7"):
        return "FBs-24MA-test7"
    return None


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
            "warnings": ["Analysis is incomplete: opaque networks may contain additional devices."]
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
            lowered, _ = lower_ladder(Ladder(networks=[network]), reserved)
            replacement = [Record.create(compile_network(n)) for n in lowered.networks]
            records[index : index + (operation == "replace")] = replacement
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
        "version": "0.10.0",
        "profile": "Exact sampled headers: FBs-20MC, FBs-24MA (test6), FBs-24MA-test7, "
        "FBs-32MA-test11, FBs-40MA-test12, FBs-44MN-test13; "
        "the two 24MA variants retain differing unknown metadata",
        "transport": "stdio",
        "simulation": "Boolean or scan_ms T/C model; max 256 scans, not a PLC emulator",
        "file_operations": ["inspect", "read", "create", "export", "replace", "insert", "delete"],
        "ir": "Prefer condition Boolean expressions; legacy steps use left-fold semantics.",
        "address_subset": {
            "X": "0..255",
            "Y": "0..255",
            "M": "0..1911 (manual range, inferred encoding); helpers remain 0..255",
            "T": "0..255",
            "LCNV_registers": "R0..3839, input R3840..3903, R5000..8071, D0..4095 (CPU-dependent)",
            "C": "0..255",
        },
        "generation": "generate_control_ldr: 11 recipes; generate_sequence_ldr: up to 16 steps, "
        "native T timing (retentive timing unsupported), optional explicit pulse counting; "
        "generate_system_ldr: independent controls with "
        "internal allocation; generate_ldr: Boolean, native X edges, T/C, register, "
        "arithmetic, LCNV and loop IR.",
        "inference_notice": "Unseen combinations/ranges are inferred, not PLC-validated.",
        "manual_reference_tool": "get_manual_reference",
        "rtc_snapshot_tool": "inspect_rtc_snapshot (no PLC connection)",
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
        "native_functions": {
            "test14_functions": {
                "release_status": "unreleased, version unchanged",
                "float_operations": "log (base 10), pow, asin, acos, atan (FUN216..220)",
                "power_order": "pow: sa=Sy exponent, sb=Sx base; result=sb**sa",
                "inverse_angles": "binary32 source and result in radians; asin/acos input -1..1",
                "D_bank": "FUN216..220 D0..3999; two-word start at most D3998",
                "error_coils": "float_operation.error: normal Y/M coils on ERR (6FFC); "
                "FLOG observed, other eligible float operations inferred; M-to-M policy applies",
                "constant_flags": "F6 second-operand constant observed in FPOW; F7 still inferred",
                "imdio": "action imdio: start X/Y, count 1..36, enable; all points in io_contract. "
                "X0,N10 observed; other X/Y spans inferred. Main-unit I/O only; table maxima "
                "X35/Y23 do not confirm capacity of the selected CPU",
                "unsupported": "No P/indirect, runtime simulation, GUI or PLC verification",
            },
            "test13_functions": {
                "release_status": "unreleased source; version unchanged",
                "operations": "float_operation sin/cos/tan/neg/abs/ln/exp (FUN209..215)",
                "angles": "Sa is one signed 16-bit word or integral constant -18000..18000; "
                "unit=0.01 degrees, not radians or binary32. D is two words.",
                "in_place": "neg/abs require only destination; read and write its two words",
                "ln_exp": "Float source and result; manual D0..3999 bank, max pair start D3998; "
                "ln literal must be positive",
                "header": "Exact FBs-44MN-test13 header including 4040 metadata",
                "evidence": "Seven exact test13 payloads observed; other operands, negative "
                "angle constants and float constant ln/exp forms inferred",
                "unsupported": "P, indirect, ERR wiring and runtime simulation; "
                "no generated-file GUI/PLC check; ERR support added in test14",
            },
            "test12_functions": {
                "release_status": "Unreleased source update; package version unchanged",
                "float_arithmetic": "FUN205 FDIV and FUN208 FSQR: float_operation div/sqrt. "
                "Arithmetic accepts register or finite binary32 immediate sources; "
                "I->F/F->I still require register source",
                "float_compare": "FUN206 FCMP: float_compare sa/sb, "
                "equal/greater/less normal coils",
                "float_zone_compare": "FUN207 FZCP: float_zone_compare register source, "
                "upper/lower register or immediate, within/above/below normal coils; no ERR wiring",
                "banks": "Float-only R0..3839, R5000..8071, D0..4095; full two-word spans checked. "
                "R8000 and D4094 sampled; other newly available offsets inferred",
                "constants": "IEEE-754 binary32, big-endian; F5 first-source constant observed. "
                "F6/F7 second/both-source markers inferred from flag pattern, not GUI verified",
                "outputs": "M0..1911 including sampled M999; M-to-M policy covers compare outputs",
                "header": "Exact FBs-40MA-test12 header",
                "verification": "Sample bytes observed; new outputs not GUI/PLC verified. "
                "No execution simulation; reject NaN/Inf, overflow, bank crossings, unknown forms",
            },
            "test11_functions": {
                "position_probe_gui_confirmation": {
                    "artifact": "FUN170_175_all_positions_probe.ldr",
                    "sha256": "252622c9cc544eeac82d525200a40c084b4aceb06f9978803ccfc7513db3781a",
                    "evidence": "User reported all positions correct on 2026-10-07",
                    "scope": "Exact six-rung R600/R700 probe; "
                    "first and series forms of six relations",
                    "reexport_received": False,
                    "plc_verified": False,
                },
                "comparison_contacts": "FUN170..175 via network.comparison_chain. "
                "All six relations at first and subsequent series positions; "
                "all 12 positions user GUI-confirmed in the exact R600/R700 probe; "
                "other operand combinations remain inferred; "
                "coil outputs including SET/RESET. No OR, mixed Boolean contacts, "
                "D form or runtime model",
                "comparison_operands": "Direct existing word banks plus exact WS0, WM0, C2, R5111. "
                "Only chained le permits constant Sb=0..32767. WM0 expands to M0..15 for policy. "
                "Other WS/WM/C/high-R addresses and constant forms are not inferred",
                "float": "FUN200 I->F, 201 F->I, 202 FADD, 203 FSUB, 204 FMUL; "
                "float_operation action with operation i_to_f/f_to_i/add/sub/mul, "
                "sa, sb, destination, EN. "
                "Conversions forbid sb; arithmetic requires it",
                "float_width": "I->F reads 1 word and writes 2; F->I reads 2 and writes 1; "
                "FADD/FSUB/FMUL read 2 per source and write 2. "
                "test12 extends float banks and immediate operands; no D/P modifiers, "
                "ERR wiring or runtime model",
                "evidence": "Exact test11 bytes observed; operand/enable changes inferred. "
                "F47F extension subcodes and unknown zero fields preserved. "
                "FBs-32MA-test11 exact header, not a generic conversion between CPUs",
            },
            "test10_functions": {
                "xor_xnr": "FUN35 XOR F4CA / FUN36 XNR F4CC; exclusive_logic action, "
                "sa/sb word sources and writable destination; no D=0 output wiring",
                "zncmp": "FUN37 F7DA; zone_compare source R/D, signed constant upper/lower; "
                "within/above/below normal coils. No register bounds or ERR wiring",
                "to_bcd": "FUN20 F5A6; word_conversion operation to_bcd; "
                "constant source 0..9999 only, writable word destination",
                "to_bin": "FUN21 F4A4; word_conversion operation to_bin; word source/destination",
                "words": "R/D banks; T0..255 read-only numeric values; exact WX0 and WY0 only. "
                "WX0/WY0 expand to X0..15/Y0..15 for I/O contract and overlap checks",
                "limitations": "Only sampled 16-bit opcode forms; parameter changes inferred. "
                "No D/P variants, indirect addressing, runtime simulation or GUI verification",
            },
            "test8_functions": {
                "increment": "FUN15 F496; action type increment, direct R/D destination, EN",
                "decrement": "FUN16 F498; action type decrement, direct R/D destination, EN",
                "compare": "FUN17 F46A; register Sa/Sb, EN/U/S, normal equal/greater/less coils; "
                "preserve unknown 0000 field; no register runtime simulation",
                "bitwise": "FUN18 AND F4C6 / FUN19 OR F4C8; direct R/D Sa, Sb, destination",
                "coil_modes": "normal (optionally inverted), set, reset; test8 establishes Y forms",
            },
            "test9_functions": {
                "mc": "FC88 + number; MCE FC89 + number; unique 0..127 inferred from manual. "
                "Generation requires matched non-overlapping regions; no MC runtime simulation",
                "difu_difd": "DIFU F8F6 / DIFD FCF7; trigger expression, Y/M bit destination; "
                "M control dependencies, including implicit MC gates, cannot drive M destinations",
                "udctr": "07P.UDCTR F100; pulse/up/clear Boolean inputs, constant preset 0..32767, "
                "writable R/D cv; no 32-bit, register preset, CUP wiring or runtime simulation",
                "branch_encoding": "test9_or preserves E422 two branches of two contacts; "
                "no helpers",
                "sample_status": "test9 decodes but MC2 lacks MCE2 and M1 implicitly drives "
                "M100/M101: full generation rejected under this workspace policy",
            },
            "arithmetic": {
                "fun": [11, 12, 13, 14],
                "action_type": "arithmetic",
                "operations": ["add", "sub", "mul", "div"],
                "source": "test7.ldr + screenshot",
                "observed": "16-bit, register Sa, positive immediate Sb, EN=TRUE, U/S=FALSE",
                "inferred": "Direct R/D operands; Sb=0..32767; Boolean EN/unsigned_when",
                "unsigned_when": "FALSE=signed (sampled); TRUE=unsigned (inferred wiring)",
                "destination_words": {"add": 1, "sub": 1, "mul": 2, "div": 2},
                "unsupported": [
                    "register Sb",
                    "constant Sa",
                    "negative Sb",
                    "32-bit D form",
                    "P form",
                    "indirect operands",
                    "connected status flags",
                    "runtime simulation",
                ],
                "import_verified": False,
            },
            "LCNV": {
                "fun": 33,
                "action_type": "lcnv",
                "source": "test6.ldr",
                "observed": "Md=0, L=1, sources R3840..3844, tables R2001+5*n, D1000..1004",
                "inferred": "Md=0..3, L=1..64, direct R/D banks, Boolean EN",
                "unsupported": [
                    "33P",
                    "indirect addressing",
                    "register-valued L",
                    "table initialization",
                    "runtime simulation",
                ],
                "import_verified": False,
            },
            "other_FUN_numbers": "Cannot derive opcodes by incrementing FUN numbers",
        },
        "native_edge_contacts": {
            "schema": "edge: {kind: rising|falling, input: X0..X255}, plus coils",
            "observed": "test4 N005 rising X0 -> Y1; N006 falling X1 -> Y3; test7 N000 rising",
            "inferred": "Other X addresses and Y/M coils; isolated edge network only",
            "simulation": "One-scan pulse; previous input starts from initial or FALSE; "
            "software model only, PLC startup behavior not verified",
            "helper_memory": "None",
        },
        "further_inference": {
            "usable_compositions": "Increment/decrement via ADD/SUB with Sb=1; "
            "constant offset, integer scaling, quotient and remainder via FUN11..14. "
            "Arithmetic status/overflow semantics remain those of FUN11..14, not FUN15/16.",
            "candidates_not_enabled": [
                "Register Sb might change F6 to F4; needs same-operation exported comparison",
                "MOV and D/P modifiers still need independent exported evidence",
            ],
            "corrected_hypothesis": "test8 disproves FUN15=F46A/FUN16=F46C; actual F496/F498. "
            "F46A is CMP. Do not increment FUN numbers to guess opcode families.",
            "policy": "Unconfirmed native opcodes remain opaque; never emitted as supported",
        },
        "opaque_only": [
            "compound edge rungs and non-X edge operands",
            "unknown instructions",
        ],
        "verified_template": "start_stop: X1=1 stops; user reported import success",
        "layout_optimization": {
            "automatic": True,
            "rules": [
                "identities",
                "deduplication",
                "absorption",
                "common-factor extraction",
                "CH01 section 1.7 compound-first ordering",
            ],
            "scope": "Pure Boolean conditions only; network/output order unchanged",
            "preview_tool": "validate_ladder",
            "user_confirmed_import_sha256": (
                "a4694aa8db73737ada925742ebc6ba164aee52e56137bd5ae201017c203b3b94"
            ),
            "verification_scope": "Exact connected traffic-light baseline only; "
            "new optimized files still need GUI import verification",
        },
        "no_plc_connection": True,
        "writes": "new .ldr files only in configured output directory; never overwrite",
        "start_stop_example": start_stop().model_dump(),
        "schema": Ladder.model_json_schema(),
    }
