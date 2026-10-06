"""Build explicit, unverified FUN15/16 hypotheses for manual WinProLadder import.

This is a research utility, not a production compiler extension. The normal MCP
must keep these instruction payloads opaque until independent evidence arrives.
"""

import argparse
import hashlib
import json
from pathlib import Path

from winproladder_mcp.ir import decode_network
from winproladder_mcp.ldr import FOOTER, Document, Record, parse

ROOT = Path(__file__).resolve().parents[1]
SOURCE_HASH = "cb7085f33a059f0eda2034ae9a18974249a49617b879b224cce0ab28057aed3c"
PAYLOADS = {
    "FUN15": bytes.fromhex("4fe8f46a40c8"),
    "FUN16": bytes.fromhex("4fe8f46c40ca"),
}


def build(output: Path) -> dict[str, object]:
    if (ROOT / "samples/test8.ldr").exists():
        raise ValueError(
            "Probe A was disproved by test8: FUN15=F496, FUN16=F498; "
            "F46A is CMP. Use native increment/decrement actions instead."
        )
    source = (ROOT / "samples/test7.ldr").read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_HASH:
        raise ValueError("test7 source differs from the supplied reference")
    header = parse(source).header
    specifications = [
        ("FUN15_INC_D100_guess_A.ldr", ["FUN15"]),
        ("FUN16_DEC_D101_guess_A.ldr", ["FUN16"]),
        ("FUN15_16_combined_guess_A.ldr", ["FUN15", "FUN16"]),
    ]
    prepared = []
    evidence = []
    for name, functions in specifications:
        display = [PAYLOADS[function] for function in functions]
        if any(decode_network(payload) is not None for payload in display):
            raise ValueError("A probe is now decoded by production code; review its evidence first")
        document = Document(header, tuple(Record.create(p) for p in reversed(display)), FOOTER)
        binary = document.encode()
        checked = parse(binary)
        assert checked.editable and checked.encode() == binary
        assert checked.header == header
        assert [r.payload for r in reversed(checked.records)] == display
        prepared.append((name, binary))
        evidence.append(
            {
                "file": name,
                "bytes": len(binary),
                "sha256": hashlib.sha256(binary).hexdigest(),
                "crc_valid": True,
                "framing_roundtrip": True,
                "gui_import_verified": False,
                "plc_runtime_verified": False,
                "production_semantic_decode": "opaque",
                "expected_networks": [
                    {
                        "index": i,
                        "function": function,
                        "expected_symbol": "15.(+1)" if function == "FUN15" else "16.(-1)",
                        "destination": "D100" if function == "FUN15" else "D101",
                        "enable": "TRUE (direct rail)",
                        "status_output_connected": False,
                        "payload_hex": PAYLOADS[function].hex(" "),
                    }
                    for i, function in enumerate(functions)
                ],
            }
        )
    manifest = {
        "status": "experimental_hypothesis_A_not_import_verified",
        "source": "samples/test7.ldr",
        "source_sha256": SOURCE_HASH,
        "header_profile": "FBs-24MA-test7",
        "physical_io": [],
        "helper_memory": [],
        "hypothesis": "FUN15=F46A; FUN16=F46C; EN + opcode + one direct destination word",
        "files": evidence,
    }
    # Refuse an existing directory before writing anything; originals are never overwritten.
    output.mkdir(parents=True, exist_ok=False)
    for name, binary in prepared:
        with (output / name).open("xb") as stream:
            stream.write(binary)
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
    with (output / "README.md").open("x", encoding="utf-8") as stream:
        stream.write((ROOT / "docs/fun15-16-probe.md").read_text(encoding="utf-8"))
    assert (ROOT / "samples/test7.ldr").read_bytes() == source
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/fun15_16_probe_A")
    options = parser.parse_args()
    report = build(options.output_dir.resolve())
    print(json.dumps({"directory": str(options.output_dir.resolve()), **report}, indent=2))
