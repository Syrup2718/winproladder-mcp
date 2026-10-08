"""WinProLadder MCP stdio entry point. Logs belong on stderr."""

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote, unquote

from mcp.server.fastmcp import FastMCP
from mcp.types import (
    BlobResourceContents,
    CallToolResult,
    EmbeddedResource,
    ResourceLink,
    TextContent,
    ToolAnnotations,
)
from pydantic import AnyUrl, StrictInt

from .acceptance import AcceptanceCase
from .control import ControlSpec, control_ladder
from .design import design_guide
from .io_contract import IOContract
from .ir import Ladder, Network, simulate, start_stop, validation
from .layout import lower_ladder
from .ldr import MAX_SIZE
from .manual_reference import analyze_rtc_snapshot, manual_reference
from .sequence import SequenceSpec, sequence_ladder
from .service import Service, capabilities
from .system import SystemSpec, system_ladder
from .timing import timed_simulate


def build_server(root: Path, output_dir: Path | None = None) -> FastMCP:
    service = Service(root, output_dir)
    mcp = FastMCP(
        "WinProLadder",
        instructions=(
            "For common functions prefer generate_control_ldr; for sequential pause/resume "
            "use generate_sequence_ldr. Copy only user-specified X/Y into io_contract. "
            "Never invent physical I/O or external clocks. Require signal and output addresses. "
            "Ordinary T timers are supported; native retentive timing encoding is unsupported. "
            "Use get_design_guide to turn requirements into conditions and blocks. "
            "Honor its workspace architecture policy; forbidden M-to-M chains must be "
            "redesigned using native instructions, not renamed or hidden in helpers. "
            "Call generate_ldr for an actual file; inferred encodings are enabled. "
            "Do not ask the user for JSON or samples for supported expressions/parameters. "
            "Use simulation for Boolean requirements. Return file links and validation warnings. "
            "Generation results include an MCP resource link to the actual binary .ldr. "
            "Use resources/read or get_ldr_artifact to deliver its bytes to clients without "
            "access to the server filesystem. "
            "Stop polarity is the PLC input logic, not physical button wiring. No PLC operations."
        ),
    )
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

    def artifact_path(name: str) -> Path:
        if not name or Path(name).name != name or any(c in name for c in "/\\:"):
            raise ValueError("Artifact name must be a plain .ldr filename")
        target = service.source(str(service.output / name))
        if target.parent != service.output:
            raise ValueError("Artifact must be directly inside the configured output directory")
        return target

    def artifact_bytes(name: str) -> bytes:
        with artifact_path(name).open("rb") as stream:
            data = stream.read(MAX_SIZE + 1)
        if len(data) > MAX_SIZE:
            raise ValueError("Artifact exceeds 16 MiB limit")
        return data

    def artifact_result(result: dict[str, Any], data: bytes | None = None) -> CallToolResult:
        name = Path(result["path"]).name
        uri = AnyUrl(f"winproladder://artifacts/{quote(name, safe='')}")
        metadata = {
            **result,
            "artifact": {
                "uri": str(uri),
                "name": name,
                "mime_type": "application/octet-stream",
                "size": result["size"],
                "sha256": result["sha256"],
            },
        }
        response = CallToolResult(
            content=[
                TextContent(type="text", text=json.dumps(metadata, ensure_ascii=False)),
                ResourceLink(
                    type="resource_link",
                    uri=uri,
                    name=name,
                    title=name,
                    description="Download the generated WinProLadder ladder resource file.",
                    mimeType="application/octet-stream",
                    size=result["size"],
                ),
            ],
            structuredContent=metadata,
        )
        if data is not None:
            response.content.append(
                EmbeddedResource(
                    type="resource",
                    resource=BlobResourceContents(
                        uri=uri,
                        mimeType="application/octet-stream",
                        blob=base64.b64encode(data).decode("ascii"),
                    ),
                )
            )
        return response

    @mcp.tool(annotations=read)
    def get_capabilities() -> dict[str, Any]:
        """Get supported operations, instruction/address limits, JSON schema and an example."""
        return {
            **capabilities(),
            "workspace": str(service.root),
            "architecture_policy": service.architecture_policy(),
            "output_directory": str(service.output),
            "artifact_delivery": {
                "resource_template": "winproladder://artifacts/{name}",
                "tool": "get_ldr_artifact",
                "format": "MCP binary resource (base64 on the wire), application/octet-stream",
            },
        }

    @mcp.tool(annotations=read)
    def get_manual_reference() -> dict[str, Any]:
        """Get manual operand maxima, edition differences and RTC register/control procedures."""
        return manual_reference()

    @mcp.tool(annotations=read)
    def inspect_rtc_snapshot(registers: dict[str, StrictInt]) -> dict[str, Any]:
        """Validate supplied R4128..R4134 values and optional packed R4135; no PLC access."""
        return analyze_rtc_snapshot(registers)

    @mcp.tool(annotations=read)
    def get_design_guide() -> dict[str, Any]:
        """Get the natural-language-to-LDR workflow and complete runnable design examples."""
        return {
            **design_guide(),
            "architecture_policy": service.architecture_policy(),
            "ladder_schema": Ladder.model_json_schema(),
        }

    @mcp.tool(annotations=write)
    def generate_system_ldr(
        output_name: str,
        spec: SystemSpec,
        io_contract: IOContract,
        acceptance: list[AcceptanceCase] | None = None,
    ) -> CallToolResult:
        """Generate independent controls with automatic internal M/T/C allocation.
        Explicit overlapping resources are rejected, not silently reassigned. Inputs can be shared.
        """
        ladder, design = system_ladder(spec)
        return artifact_result(
            service.generate_design(
                output_name, ladder, design, acceptance, io_contract=io_contract
            )
        )

    @mcp.tool(annotations=write)
    def generate_control_ldr(
        output_name: str,
        spec: ControlSpec,
        io_contract: IOContract,
        acceptance: list[AcceptanceCase] | None = None,
    ) -> CallToolResult:
        """Generate common control functions from customer requirements translated by the host.
        Physical I/O must be explicit and within io_contract. Supports latch, toggle, edges, delays,
        pulse, counter, interlocked direction and star/delta; returns actual .ldr + assumptions.
        """
        ladder, design = control_ladder(spec)
        return artifact_result(
            service.generate_design(
                output_name, ladder, design, acceptance, io_contract=io_contract
            )
        )

    @mcp.tool(annotations=write)
    def generate_sequence_ldr(
        output_name: str,
        spec: SequenceSpec,
        io_contract: IOContract,
        acceptance: list[AcceptanceCase] | None = None,
    ) -> CallToolResult:
        """Generate ordered steps using native T timers, with no automatic X/Y additions.
        Native retentive pause/resume is not yet encoded and is rejected explicitly.
        External pulse counting is only for requirements explicitly specifying a clock input.
        Return symbols and actual .ldr; not GUI or PLC verified.
        """
        ladder, design = sequence_ladder(spec)
        return artifact_result(
            service.generate_design(
                output_name, ladder, design, acceptance, io_contract=io_contract
            )
        )

    @mcp.tool(annotations=write)
    def generate_ldr(
        output_name: str,
        ladder: Ladder,
        io_contract: IOContract,
        acceptance: list[AcceptanceCase] | None = None,
    ) -> CallToolResult:
        """Preferred generation tool: compile conditions/blocks to an actual .ldr file.

        Inferred encodings are enabled without a separate flag. Return design summary,
        SHA-256, binary resource link and verification warnings. Never overwrite existing files.
        """
        return artifact_result(
            service.generate(output_name, ladder, acceptance, io_contract=io_contract)
        )

    @mcp.tool(annotations=read)
    def get_ldr_artifact(output_name: str) -> CallToolResult:
        """Retrieve a generated .ldr as an embedded MCP binary resource and download link.

        Use the original output_name, including .ldr. Returns exact file bytes as base64
        with SHA-256; only reads the configured output directory. Useful when the client
        cannot access local server paths or cannot invoke resources/read directly.
        """
        target = artifact_path(output_name)
        data = artifact_bytes(output_name)
        return artifact_result(
            {"path": str(target), "size": len(data), "sha256": hashlib.sha256(data).hexdigest()},
            data,
        )

    @mcp.tool(annotations=read)
    def inspect_ldr(path: str) -> dict[str, Any]:
        """Inspect framing, raw bytes, offsets and CRC validity. Read paths are workspace-scoped."""
        return service.inspect(path)

    @mcp.tool(annotations=read)
    def read_ldr(path: str) -> dict[str, Any]:
        """Read logic in display order; unknown payloads stay opaque. Reject bad CRC."""
        return service.read(path)

    @mcp.tool(annotations=read)
    def analyze_ldr(path: str) -> dict[str, Any]:
        """Explain networks and device reads/writes. Opaque networks mark analysis incomplete."""
        return service.analyze(path)

    @mcp.tool(annotations=read)
    def compare_ldr(left_path: str, right_path: str) -> dict[str, Any]:
        """Align display-order networks and report insert/delete/replace, including CRC changes."""
        return service.compare(left_path, right_path)

    @mcp.tool(annotations=read)
    def validate_ladder(ladder: Ladder) -> dict[str, Any]:
        """Preview simplified connected IR and resource costs; not PLC syntax validation."""
        lowered, layout = lower_ladder(ladder)
        source_architecture = service.architecture(ladder, enforce=False)
        architecture = service.architecture(lowered, enforce=False)
        result: dict[str, Any] = dict(validation(lowered))
        if not source_architecture["valid"] or not architecture["valid"]:
            result["valid"] = False
            result["errors"].append("Workspace architecture forbids M-to-M networks")
        return {
            **result,
            "architecture": architecture,
            "source_architecture": source_architecture,
            "layout": layout,
            "optimized_ladder": lowered.model_dump(),
        }

    @mcp.tool(annotations=write)
    def create_ldr(
        output_name: str, ladder: Ladder, io_contract: IOContract, allow_unverified: bool = False
    ) -> CallToolResult:
        """Create a new file from IR with sampled header and fresh CRC. Never overwrite files."""
        return artifact_result(
            service.create(output_name, ladder, allow_unverified, io_contract=io_contract)
        )

    @mcp.tool(annotations=read)
    def simulate_ladder(
        ladder: Ladder,
        inputs: list[dict[str, bool]],
        initial: dict[str, bool] | None = None,
        scan_ms: int | None = None,
    ) -> dict[str, Any]:
        """Boolean IR scan model, not PLC emulation. Missing X inputs reset false each scan.

        Missing initial devices default false. T/C contacts are fixed initial states;
        Without scan_ms, timers/counters are not executed. With scan_ms, use the
        reset-start T/C model for default .01s T0..T49; no register/loop execution.
        Networks evaluate in display order, inputs apply for one scan duration.
        """
        return {
            "trace": (
                simulate(ladder, inputs, initial or {})
                if scan_ms is None
                else timed_simulate(ladder, inputs, initial or {}, scan_ms)
            ),
            "scope": "Offline scan model only; scan_ms enables reset-start T/C model, "
            "default T0..T49 .01s configuration. No PLC runtime validation.",
        }

    @mcp.tool(annotations=write)
    def create_start_stop(
        output_name: str, stop_input_active_high: bool = True, allow_unverified: bool = False
    ) -> CallToolResult:
        """Create X0/Y0 self-hold. True: X1=1 stops (verified). False: X1=0 stops (candidate)."""
        return artifact_result(
            service.create(output_name, start_stop(stop_input_active_high), allow_unverified)
        )

    @mcp.tool(annotations=write)
    def export_ldr(path: str, output_name: str) -> CallToolResult:
        """Re-encode to a NEW file, preserving opaque bytes and any original invalid CRC."""
        return artifact_result(service.export(path, output_name))

    @mcp.tool(annotations=write)
    def modify_network(
        path: str,
        output_name: str,
        operation: Literal["replace", "insert", "delete"],
        index: int,
        network: Network | None = None,
        allow_unverified: bool = False,
    ) -> CallToolResult:
        """Edit in a NEW file; index 0 is N000. Preserve untouched raw records."""
        return artifact_result(
            service.edit(path, output_name, operation, index, network, allow_unverified)
        )

    @mcp.resource(
        "winproladder://artifacts/{name}",
        name="generated_ldr",
        title="Generated WinProLadder file",
        mime_type="application/octet-stream",
    )
    def artifact_resource(name: str) -> bytes:
        """Read a generated .ldr file. The URI name is percent-encoded UTF-8."""
        return artifact_bytes(unquote(name, errors="strict"))

    @mcp.resource("winproladder://capabilities")
    def capability_resource() -> str:
        return json.dumps(get_capabilities(), ensure_ascii=False)

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Workspace allowed for reads")
    parser.add_argument(
        "--output-dir", type=Path, help="Absolute output subdirectory (default ROOT/artifacts)"
    )
    args = parser.parse_args()
    build_server(args.root, args.output_dir).run(transport="stdio")


if __name__ == "__main__":
    main()
