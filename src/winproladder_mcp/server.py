"""WinProLadder MCP stdio entry point. Logs belong on stderr."""

import argparse
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .acceptance import AcceptanceCase
from .control import ControlSpec, control_ladder
from .design import design_guide
from .ir import Ladder, Network, simulate, start_stop, validation
from .layout import lower_ladder
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
            "use generate_sequence_ldr. Resolve missing I/O/timing with disclosed defaults. "
            "Do not block a draft because its control table is incomplete. "
            "Never hide external-clock requirements or claim safety commissioning. "
            "Use get_design_guide to turn requirements into conditions and blocks. "
            "Call generate_ldr for an actual file; inferred encodings are enabled. "
            "Do not ask the user for JSON or samples for supported expressions/parameters. "
            "Use simulation for Boolean requirements. Return file links and validation warnings. "
            "Stop polarity is the PLC input logic, not physical button wiring. No PLC operations."
        ),
    )
    read = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
    write = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

    @mcp.tool(annotations=read)
    def get_capabilities() -> dict[str, Any]:
        """Get supported operations, instruction/address limits, JSON schema and an example."""
        return {
            **capabilities(),
            "workspace": str(service.root),
            "output_directory": str(service.output),
        }

    @mcp.tool(annotations=read)
    def get_design_guide() -> dict[str, Any]:
        """Get the natural-language-to-LDR workflow and complete runnable design examples."""
        return {**design_guide(), "ladder_schema": Ladder.model_json_schema()}

    @mcp.tool(annotations=write)
    def generate_system_ldr(
        output_name: str, spec: SystemSpec, acceptance: list[AcceptanceCase] | None = None
    ) -> dict[str, Any]:
        """Generate multiple independent controls in one LDR with automatic Y/M/T/C allocation.
        Explicit overlapping resources are rejected, not silently reassigned. Inputs can be shared.
        """
        ladder, design = system_ladder(spec)
        return service.generate_design(output_name, ladder, design, acceptance)

    @mcp.tool(annotations=write)
    def generate_control_ldr(
        output_name: str, spec: ControlSpec, acceptance: list[AcceptanceCase] | None = None
    ) -> dict[str, Any]:
        """Generate common control functions from customer requirements translated by the host.
        Missing values get explicit draft defaults. Supports latch, toggle, edges, delays,
        pulse, counter, interlocked direction and star/delta; returns actual .ldr + assumptions.
        """
        ladder, design = control_ladder(spec)
        return service.generate_design(output_name, ladder, design, acceptance)

    @mcp.tool(annotations=write)
    def generate_sequence_ldr(
        output_name: str, spec: SequenceSpec, acceptance: list[AcceptanceCase] | None = None
    ) -> dict[str, Any]:
        """Generate a pause/resume multi-step candidate. Host agent translates customer text
        into steps and fills missing values with disclosed defaults, not blocking questions.
        Requires external clock input (default X4, 100ms); retains whole ticks, not fractions.
        Return design assumptions and actual .ldr. Not safety-certified or GUI-verified.
        """
        ladder, design = sequence_ladder(spec)
        return service.generate_design(output_name, ladder, design, acceptance)

    @mcp.tool(annotations=write)
    def generate_ldr(
        output_name: str, ladder: Ladder, acceptance: list[AcceptanceCase] | None = None
    ) -> dict[str, Any]:
        """Preferred generation tool: compile conditions/blocks to an actual .ldr file.

        Inferred encodings are enabled without a separate flag. Return design summary,
        CRC-backed file hash and verification warnings. Never overwrite existing files.
        """
        return service.generate(output_name, ladder, acceptance)

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
        return {**validation(lowered), "layout": layout, "optimized_ladder": lowered.model_dump()}

    @mcp.tool(annotations=write)
    def create_ldr(
        output_name: str, ladder: Ladder, allow_unverified: bool = False
    ) -> dict[str, Any]:
        """Create a new file from IR with sampled header and fresh CRC. Never overwrite files."""
        return service.create(output_name, ladder, allow_unverified)

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
    ) -> dict[str, Any]:
        """Create X0/Y0 self-hold. True: X1=1 stops (verified). False: X1=0 stops (candidate)."""
        return service.create(output_name, start_stop(stop_input_active_high), allow_unverified)

    @mcp.tool(annotations=write)
    def export_ldr(path: str, output_name: str) -> dict[str, Any]:
        """Re-encode to a NEW file, preserving opaque bytes and any original invalid CRC."""
        return service.export(path, output_name)

    @mcp.tool(annotations=write)
    def modify_network(
        path: str,
        output_name: str,
        operation: Literal["replace", "insert", "delete"],
        index: int,
        network: Network | None = None,
        allow_unverified: bool = False,
    ) -> dict[str, Any]:
        """Edit in a NEW file; index 0 is N000. Preserve untouched raw records."""
        return service.edit(path, output_name, operation, index, network, allow_unverified)

    @mcp.resource("winproladder://capabilities")
    def capability_resource() -> str:
        import json

        return json.dumps(capabilities(), ensure_ascii=False)

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
