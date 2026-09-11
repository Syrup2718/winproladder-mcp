"""WinProLadder MCP stdio entry point. Logs belong on stderr."""

import argparse
from pathlib import Path
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .ir import Ladder, Network, simulate, start_stop, validation
from .service import Service, capabilities


def build_server(root: Path, output_dir: Path | None = None) -> FastMCP:
    service = Service(root, output_dir)
    mcp = FastMCP(
        "WinProLadder",
        instructions=(
            "Call get_capabilities first. Work with structured Ladder IR, not guessed binary. "
            "Use validate_ladder before generation. Unknown instructions remain opaque. "
            "Only the exact start_stop template is import-verified. Other supported compositions "
            "require explicit allow_unverified and WinProLadder import checking. "
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
    def inspect_ldr(path: str) -> dict[str, Any]:
        """Inspect framing, raw bytes, offsets and CRC validity. Read paths are workspace-scoped."""
        return service.inspect(path)

    @mcp.tool(annotations=read)
    def read_ldr(path: str) -> dict[str, Any]:
        """Read logic in display order; unknown payloads stay opaque. Reject bad CRC."""
        return service.read(path)

    @mcp.tool(annotations=read)
    def validate_ladder(ladder: Ladder) -> dict[str, Any]:
        """Check IR encoding and report import verification. Not PLC syntax validation."""
        return validation(ladder)

    @mcp.tool(annotations=write)
    def create_ldr(
        output_name: str, ladder: Ladder, allow_unverified: bool = False
    ) -> dict[str, Any]:
        """Create a new file from IR with sampled header and fresh CRC. Never overwrite files."""
        return service.create(output_name, ladder, allow_unverified)

    @mcp.tool(annotations=read)
    def simulate_ladder(
        ladder: Ladder, inputs: list[dict[str, bool]], initial: dict[str, bool] | None = None
    ) -> dict[str, Any]:
        """Boolean IR scan model, not PLC emulation. Missing X inputs reset false each scan.

        Missing initial devices default false. T/C contacts are fixed initial states;
        timers/counters are not executed. Networks evaluate in display order.
        """
        return {
            "trace": simulate(ladder, inputs, initial or {}),
            "scope": "Boolean IR only; no timing, hardware, edge or PLC runtime validation.",
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
